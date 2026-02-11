from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from math import ceil
from typing import Any, Callable

import streamlit as st
from st_clickable_images import clickable_images

from services.drive_service import DriveServiceError
from storage import DriveAgent

PHOTO_STATUS_OPTIONS: tuple[str, ...] = ("draft", "published", "archived")
DEFAULT_PARENT_VISIBILITY_STATUS = "draft"
_IMAGE_EXTENSIONS = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
_VIDEO_EXTENSIONS = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".m4v": "video/x-m4v",
}


@dataclass(slots=True)
class MediaPageContext:
    app_config: Any
    user_email: str
    children: list[dict[str, Any]]
    stammdaten_manager: Any
    drive_agent: DriveAgent
    ensure_child_photo_folder: Callable[[str], str]
    trigger_rerun: Callable[[], None]


@dataclass(slots=True)
class MediaItem:
    file_id: str
    name: str
    mime_type: str

    @property
    def is_video(self) -> bool:
        return self.mime_type.startswith("video/")


class PhotoAgent:
    def upload_photo(self, image_file: Any, folder_id: str) -> str:
        """Speichert ein hochgeladenes Medium im zugewiesenen Kind-Ordner."""
        media_bytes = image_file.getvalue()
        file_name = image_file.name or "media.jpg"
        lower_name = file_name.lower()

        mime_type = "application/octet-stream"
        for extension, candidate_mime_type in {
            **_IMAGE_EXTENSIONS,
            **_VIDEO_EXTENSIONS,
        }.items():
            if lower_name.endswith(extension):
                mime_type = candidate_mime_type
                break

        drive_agent = DriveAgent()
        file_id = drive_agent.upload_file(file_name, media_bytes, mime_type, folder_id)
        if not file_id:
            raise RuntimeError("Upload fehlgeschlagen: keine file_id erhalten.")
        return str(file_id)

    def face_detection_enabled(self) -> bool:
        """Face-Recognition ist im MVP deaktiviert."""
        return False


def render_media_page(ctx: MediaPageContext) -> None:
    tab_gallery, tab_upload, tab_status = st.tabs(
        ["Galerie / Gallery", "Upload", "Status"]
    )
    with tab_gallery:
        render_gallery(ctx)
    with tab_upload:
        render_upload(ctx)
    with tab_status:
        render_photo_status(ctx)


def _normalize_photo_status(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in PHOTO_STATUS_OPTIONS:
        return normalized
    return DEFAULT_PARENT_VISIBILITY_STATUS


@st.cache_data(show_spinner=False, ttl=60)
def _list_media(folder_id: str) -> list[dict[str, Any]]:
    drive_agent = DriveAgent()
    return drive_agent.list_files(folder_id)


@st.cache_data(show_spinner=False, ttl=120)
def _get_media_bytes(file_id: str) -> bytes:
    drive_agent = DriveAgent()
    return drive_agent.download_file(file_id)


def _to_media_items(raw_items: list[dict[str, Any]]) -> list[MediaItem]:
    media_items: list[MediaItem] = []
    for raw_item in raw_items:
        mime_type = str(raw_item.get("mimeType", "")).strip()
        if not mime_type.startswith(("image/", "video/")):
            continue
        media_items.append(
            MediaItem(
                file_id=str(raw_item.get("id", "")).strip(),
                name=str(raw_item.get("name", "media")).strip() or "media",
                mime_type=mime_type,
            )
        )
    return media_items


def _video_placeholder_data_url(file_name: str) -> str:
    safe_name = file_name.replace("&", "und")
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='420' height='280'>"
        "<rect width='100%' height='100%' fill='#2f2f2f'/>"
        "<text x='50%' y='45%' dominant-baseline='middle' text-anchor='middle' "
        "fill='white' font-size='28'>▶ Video</text>"
        f"<text x='50%' y='66%' dominant-baseline='middle' text-anchor='middle' "
        f"fill='#d6d6d6' font-size='16'>{safe_name}</text>"
        "</svg>"
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _image_data_url(media_item: MediaItem) -> str:
    media_bytes = _get_media_bytes(media_item.file_id)
    encoded = base64.b64encode(media_bytes).decode("ascii")
    return f"data:{media_item.mime_type};base64,{encoded}"


def _get_child_folder_id(ctx: MediaPageContext, child: dict[str, Any]) -> str:
    child_id = str(child.get("id", "")).strip()
    if not child_id:
        return ""

    if ctx.app_config.storage_mode == "google":
        return ctx.ensure_child_photo_folder(child_id)

    return str(child.get("photo_folder_id") or child.get("folder_id") or "").strip()


def _paginate_media(
    media_items: list[MediaItem], page: int, page_size: int
) -> list[MediaItem]:
    start_index = page * page_size
    end_index = start_index + page_size
    return media_items[start_index:end_index]


def render_gallery(ctx: MediaPageContext) -> None:
    st.markdown("### Galerie / Gallery")
    selected_child = st.selectbox(
        "Kind auswählen / Select child",
        options=ctx.children,
        format_func=lambda child: str(child.get("name", "")),
        key="gallery_child_select",
    )

    child_id = str(selected_child.get("id", "")).strip()
    if not child_id:
        st.warning("Kein Kind ausgewählt. / No child selected.")
        return

    try:
        folder_id = _get_child_folder_id(ctx, selected_child)
        if not folder_id:
            st.warning(
                "Kein Medien-Ordner für dieses Kind vorhanden. / No media folder configured for this child."
            )
            return

        raw_media_items = _list_media(folder_id)
        media_items = _to_media_items(raw_media_items)
    except DriveServiceError as exc:
        st.error(
            "Medien konnten nicht geladen werden. Bitte Drive-Freigaben prüfen. / "
            "Could not load media. Please verify Drive sharing."
        )
        st.info(str(exc))
        return

    if not media_items:
        st.caption("Keine Medien gefunden. / No media found.")
        return

    page_size = 24
    page_key = f"gallery_page_{child_id}"
    max_pages = max(1, ceil(len(media_items) / page_size))
    current_page = int(st.session_state.get(page_key, 0))
    current_page = min(max(current_page, 0), max_pages - 1)
    st.session_state[page_key] = current_page

    col_prev, col_page, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("⬅️ Zurück / Previous", key=f"gallery_prev_{child_id}"):
            st.session_state[page_key] = max(0, current_page - 1)
            st.rerun()
    with col_page:
        st.caption(f"Seite / Page {current_page + 1} von / of {max_pages}")
    with col_next:
        if st.button("Weiter / Next ➡️", key=f"gallery_next_{child_id}"):
            st.session_state[page_key] = min(max_pages - 1, current_page + 1)
            st.rerun()

    page_items = _paginate_media(media_items, current_page, page_size)
    thumbnails: list[str] = []
    titles: list[str] = []

    for media_item in page_items:
        if media_item.is_video:
            thumbnails.append(_video_placeholder_data_url(media_item.name))
        else:
            thumbnails.append(_image_data_url(media_item))
        titles.append(f"{media_item.name} ({media_item.mime_type})")

    clicked_idx = clickable_images(
        thumbnails,
        titles=titles,
        div_style={
            "display": "flex",
            "justify-content": "flex-start",
            "flex-wrap": "wrap",
        },
        img_style={"margin": "4px", "height": "130px"},
        key=f"gallery_click_{child_id}_{current_page}",
    )

    if clicked_idx < 0 or clicked_idx >= len(page_items):
        st.caption(
            "Bitte ein Medium anklicken, um die Vorschau und Aktionen zu sehen. / "
            "Click a media tile to open preview and actions."
        )
        return

    selected_item = page_items[clicked_idx]
    preview_col, meta_col = st.columns([3, 2])
    with preview_col:
        if selected_item.is_video:
            st.video(_get_media_bytes(selected_item.file_id))
        else:
            st.image(_get_media_bytes(selected_item.file_id), use_container_width=True)
    with meta_col:
        st.markdown("#### Aktionen / Actions")
        st.write(f"**Datei / File:** {selected_item.name}")
        st.caption(f"ID: {selected_item.file_id}")
        st.caption(f"MIME: {selected_item.mime_type}")
        st.download_button(
            "Download / Download",
            data=_get_media_bytes(selected_item.file_id),
            file_name=selected_item.name,
            mime=selected_item.mime_type,
            key=f"gallery_download_{selected_item.file_id}",
        )

        meta = (
            ctx.stammdaten_manager.get_photo_meta_by_file_id(selected_item.file_id)
            or {}
        )
        current_status = _normalize_photo_status(str(meta.get("status", "")))
        st.write(f"Status: **{current_status}**")


def render_upload(ctx: MediaPageContext) -> None:
    st.markdown("### Upload")
    selected_child = st.selectbox(
        "Medium hochladen für Kind / Upload media for child",
        options=ctx.children,
        format_func=lambda child: str(child.get("name", "")),
        key="upload_child_select",
    )

    with st.form("photo_upload_form", border=True):
        upload_file = st.file_uploader(
            "Datei auswählen / Select media",
            type=["jpg", "jpeg", "png", "mp4", "mov", "webm"],
        )
        upload_submitted = st.form_submit_button("Upload / Upload")

    if not upload_submitted:
        return

    if upload_file is None:
        st.warning("Bitte zuerst eine Datei auswählen. / Please select a file first.")
        return

    child_id = str(selected_child.get("id", "")).strip()
    try:
        folder_id = _get_child_folder_id(ctx, selected_child)
        if not folder_id:
            raise ValueError(
                "Kein Medien-Ordner für dieses Kind vorhanden. / No media folder configured for this child."
            )

        file_id = PhotoAgent().upload_photo(upload_file, folder_id)
        ctx.stammdaten_manager.upsert_photo_meta(
            file_id,
            {
                "child_id": child_id,
                "album": "",
                "status": "draft",
                "uploaded_at": datetime.now().isoformat(),
                "uploaded_by": ctx.user_email,
                "retention_until": "",
            },
        )

        _list_media.clear()
        _get_media_bytes.clear()
        st.success(
            "Upload erfolgreich (Status: draft). / Upload successful (status: draft)."
        )
        if str(upload_file.type or "").startswith("video/"):
            st.video(upload_file)
        else:
            st.image(upload_file, use_container_width=True)
    except DriveServiceError as exc:
        st.error(
            "Upload fehlgeschlagen. Prüfen Sie die Ordnerfreigabe und Drive-ID. / "
            "Upload failed. Verify folder sharing and Drive ID."
        )
        st.info(str(exc))
    except ValueError as exc:
        st.error(f"Fehler beim Upload / Upload failed: {exc}")


def render_photo_status(ctx: MediaPageContext) -> None:
    st.markdown("### Status")
    selected_child = st.selectbox(
        "Status verwalten für Kind / Manage status for child",
        options=ctx.children,
        format_func=lambda child: str(child.get("name", "")),
        key="status_child_select",
    )
    child_id = str(selected_child.get("id", "")).strip()

    try:
        folder_id = _get_child_folder_id(ctx, selected_child)
    except DriveServiceError as exc:
        st.error(
            "Foto-Ordner konnte nicht geladen werden. / Could not load media folder."
        )
        st.info(str(exc))
        return

    if not folder_id:
        st.warning(
            "Kein Medien-Ordner für dieses Kind vorhanden. / No media folder configured for this child."
        )
        return

    drive_url = f"https://drive.google.com/drive/folders/{folder_id}"
    st.markdown(
        f"[📂 Ordner auf Google Drive öffnen / Open folder on Google Drive]({drive_url})"
    )

    raw_media_items = _list_media(folder_id)
    media_items = _to_media_items(raw_media_items)
    if not media_items:
        st.caption(
            "Keine Medien für dieses Kind gefunden. / No media found for this child."
        )
        return

    for media_item in media_items:
        meta = (
            ctx.stammdaten_manager.get_photo_meta_by_file_id(media_item.file_id) or {}
        )
        current_status = _normalize_photo_status(meta.get("status"))
        with st.expander(
            f"{media_item.name} · Status verwalten / Manage status",
            expanded=False,
        ):
            selected_status = st.selectbox(
                "Status / Status",
                options=list(PHOTO_STATUS_OPTIONS),
                index=list(PHOTO_STATUS_OPTIONS).index(current_status),
                key=f"admin_media_status_{media_item.file_id}",
            )

            media_bytes = _get_media_bytes(media_item.file_id)
            if media_item.is_video:
                st.video(media_bytes)
            else:
                st.image(media_bytes, width=320)

            if selected_status == current_status:
                continue

            ctx.stammdaten_manager.upsert_photo_meta(
                media_item.file_id,
                {
                    "child_id": child_id,
                    "status": selected_status,
                    "uploaded_by": str(meta.get("uploaded_by", "")) or ctx.user_email,
                    "uploaded_at": str(meta.get("uploaded_at", ""))
                    or datetime.now().isoformat(),
                    "album": str(meta.get("album", "")),
                    "retention_until": str(meta.get("retention_until", "")),
                },
            )
            st.success("Status aktualisiert. / Status updated.")
            ctx.trigger_rerun()
