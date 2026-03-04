from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
import streamlit as st
import streamlit.components.v1 as components

from domain.models import MediaItem
from onedrive_auth import OneDriveAuthError, get_graph_client, get_onedrive_folder
from services.drive_service import DriveServiceError
from storage import DriveAgent
from ui.layout import card, error_banner, page_header
from ui.media_gallery import render_media_gallery
from ui.state_keys import UIKeys, ensure_defaults, ss_get, ss_set

PHOTO_STATUS_OPTIONS: tuple[str, ...] = ("draft", "published", "archived")
DEFAULT_PARENT_VISIBILITY_STATUS = "draft"
_IMAGE_EXTENSIONS = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
_VIDEO_EXTENSIONS = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".m4v": "video/x-m4v",
}
DEFAULT_ONEDRIVE_SHARED_FOLDER_URL = (
    "https://1drv.ms/f/c/497745699E449E1E/"
    "IgC_uwMf-CvWTZZYgmWwxgTVAX2YNBIlVHHu2jTvxO3xOmA?e=sYtDLw"
)
DEFAULT_ONEDRIVE_FOLDER_PATH = "Documents/9 Freunde"
ONEDRIVE_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_memo_decorator = getattr(st, "experimental_memo", st.cache_data)


@dataclass(slots=True)
class MediaPageContext:
    app_config: Any
    user_email: str
    children: list[dict[str, Any]]
    stammdaten_manager: Any
    drive_agent: DriveAgent
    photos_folder_id: str
    trigger_rerun: Callable[[], None]


class PhotoAgent:
    def upload_photo(self, image_file: Any, folder_id: str) -> str:
        """Speichert ein hochgeladenes Medium im zentralen Medien-Ordner."""
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


def _resolve_onedrive_folder_url() -> str:
    """Liest den konfigurierten OneDrive-Freigabelink (Fallback: Standard-Link)."""
    onedrive_config = st.secrets.get("onedrive", {})
    if isinstance(onedrive_config, dict):
        configured_url = str(onedrive_config.get("shared_folder_url", "")).strip()
        if configured_url:
            return configured_url
    return DEFAULT_ONEDRIVE_SHARED_FOLDER_URL


def _is_onedrive_enabled() -> bool:
    onedrive_config = st.secrets.get("onedrive", {})
    return bool(
        isinstance(onedrive_config, dict) and onedrive_config.get("enabled", False)
    )


def _onedrive_folder_path() -> str:
    onedrive_config = st.secrets.get("onedrive", {})
    if isinstance(onedrive_config, dict):
        configured_path = str(onedrive_config.get("folder_path", "")).strip()
        if configured_path:
            return configured_path
    return DEFAULT_ONEDRIVE_FOLDER_PATH


def list_photos_from_onedrive() -> list[dict[str, str]]:
    folder = get_onedrive_folder(_onedrive_folder_path())
    client = get_graph_client()
    response = client.request(
        "GET", f"{client.drive_base_path}/items/{folder.id}/children"
    )

    payload = response.json().get("value", [])
    if not isinstance(payload, list):
        return []

    photos: list[dict[str, str]] = []
    for raw_item in payload:
        if not isinstance(raw_item, dict):
            continue
        name = str(raw_item.get("name", "")).strip()
        if Path(name.lower()).suffix not in ONEDRIVE_IMAGE_EXTENSIONS:
            continue
        photos.append({"id": str(raw_item.get("id", "")).strip(), "name": name})
    return photos


def upload_photo_to_onedrive(file_bytes: bytes, file_name: str) -> dict[str, str]:
    normalized_name = Path(file_name).name
    if not normalized_name:
        raise ValueError("Dateiname darf nicht leer sein.")

    folder_path = _onedrive_folder_path().strip("/")
    client = get_graph_client()
    response = client.request(
        "PUT",
        f"{client.drive_base_path}/root:/{folder_path}/{normalized_name}:/content",
        headers={"Content-Type": "application/octet-stream"},
        data=file_bytes,
    )
    payload = response.json()
    return {
        "id": str(payload.get("id", "")).strip(),
        "name": str(payload.get("name", normalized_name)).strip(),
    }


@_memo_decorator(show_spinner=False, ttl=120)
def download_photo_from_onedrive(item_id: str) -> bytes:
    client = get_graph_client()
    response = client.request(
        "GET", f"{client.drive_base_path}/items/{item_id}/content"
    )
    return response.content


def render_onedrive_embed_panel() -> None:
    """Zeigt OneDrive-Freigabe mit optionaler iFrame-Einbettung."""
    if not _is_onedrive_enabled():
        return

    folder_url = _resolve_onedrive_folder_url()

    with card("OneDrive-Ordner / OneDrive folder"):
        st.info(
            "Für Upload und Download den freigegebenen OneDrive-Ordner öffnen und "
            "das hinterlegte Passwort eingeben. / To upload and download, open the "
            "shared OneDrive folder and enter the configured password."
        )
        st.link_button(
            "📂 OneDrive öffnen (Upload & Download) / Open OneDrive (upload & download)",
            folder_url,
            use_container_width=True,
        )
        st.caption(
            "Wenn iFrame blockiert ist, OneDrive über Button im neuen Tab öffnen. / "
            "If the iFrame is blocked, open OneDrive in a new tab using the button."
        )
        try:
            folder_ref = get_onedrive_folder(_onedrive_folder_path())
            st.success(
                "OneDrive-Authentifizierung aktiv. Ordner gefunden: "
                f"{folder_ref.name} ({folder_ref.id}). / "
                "OneDrive authentication active."
            )
        except OneDriveAuthError as exc:
            if exc.reason == "auth":
                st.error(
                    "OneDrive-Authentifizierung fehlgeschlagen. Bitte App-Registrierung "
                    "und Secrets prüfen. / OneDrive authentication failed. Please "
                    "verify app registration and secrets."
                )
            elif exc.reason == "path":
                st.error(
                    "OneDrive-Ordnerpfad nicht gefunden. Bitte [onedrive].folder_path "
                    "korrigieren. / OneDrive folder path not found. Please check "
                    "[onedrive].folder_path."
                )
            elif exc.reason == "permission":
                st.error(
                    "OneDrive-Berechtigung fehlt. Bitte Graph-Rechte/Consent für den "
                    "Ziel-Drive prüfen. / OneDrive permission denied. Please verify "
                    "Graph permissions/consent for the target drive."
                )
            else:
                st.error(
                    "OneDrive-Fehler beim Ordnercheck. / OneDrive folder validation "
                    f"failed: {exc}"
                )

        show_embed = st.toggle(
            "Einbettung anzeigen / Show embed",
            value=False,
            key=UIKeys.ONEDRIVE_SHOW_EMBED,
        )
        if show_embed:
            components.iframe(folder_url, height=520, scrolling=True)


def render_media_page(ctx: MediaPageContext) -> None:
    ensure_defaults(
        {
            UIKeys.MEDIA_CHILD: None,
            UIKeys.MEDIA_PAGE: 0,
            UIKeys.MEDIA_SELECTED: None,
        }
    )
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


def _to_media_items(
    raw_items: list[dict[str, Any]], *, child_id: str, source: str
) -> list[MediaItem]:
    media_items: list[MediaItem] = []
    for raw_item in raw_items:
        mime_type = str(raw_item.get("mimeType", "")).strip()
        if not mime_type.startswith(("image/", "video/")):
            continue
        media_items.append(
            MediaItem(
                id=str(raw_item.get("id", "")).strip(),
                child_id=child_id,
                name=str(raw_item.get("name", "media")).strip() or "media",
                mime_type=mime_type,
                kind="video" if mime_type.startswith("video/") else "image",
                source="local" if source == "local" else "google",
                created_time=str(raw_item.get("createdTime", "")).strip() or None,
                modified_time=str(raw_item.get("modifiedTime", "")).strip() or None,
            )
        )
    return media_items


def _get_media_folder_id(ctx: MediaPageContext) -> str:
    return str(ctx.photos_folder_id).strip()


def _format_drive_error_details(exc: DriveServiceError) -> str:
    details = str(exc)
    if exc.status_code is not None:
        details += f" (status_code={exc.status_code})"
    if exc.cause:
        details += f" (cause={exc.cause})"
    return details


def _filter_media_items_for_child(
    ctx: MediaPageContext,
    media_items: list[MediaItem],
    child_id: str,
) -> list[MediaItem]:
    normalized_child_id = child_id.strip()
    if not normalized_child_id:
        return []

    filtered_media_items: list[MediaItem] = []
    for media_item in media_items:
        metadata = ctx.stammdaten_manager.get_photo_meta_by_file_id(media_item.id)
        if not metadata:
            continue
        if str(metadata.get("child_id", "")).strip() != normalized_child_id:
            continue
        filtered_media_items.append(media_item)
    return filtered_media_items


def _with_preview_payload(media_items: list[MediaItem]) -> list[MediaItem]:
    enriched_items: list[MediaItem] = []
    for media_item in media_items:
        payload = (
            download_photo_from_onedrive(media_item.id)
            if media_item.source == "onedrive"
            else _get_media_bytes(media_item.id)
        )
        enriched_items.append(
            MediaItem(
                id=media_item.id,
                child_id=media_item.child_id,
                name=media_item.name,
                mime_type=media_item.mime_type,
                kind=media_item.kind,
                source=media_item.source,
                created_time=media_item.created_time,
                modified_time=media_item.modified_time,
                thumb_bytes=payload if media_item.is_image else None,
                preview_bytes=payload,
                preview_url=media_item.preview_url,
            )
        )
    return enriched_items


def render_gallery(ctx: MediaPageContext) -> None:
    page_header("Galerie / Gallery")
    render_onedrive_embed_panel()
    selected_child = st.selectbox(
        "Kind auswählen / Select child",
        options=ctx.children,
        format_func=lambda child: str(child.get("name", "")),
        key=UIKeys.MEDIA_GALLERY_CHILD_SELECT,
    )

    child_id = str(selected_child.get("id", "")).strip()
    if child_id != ss_get(UIKeys.MEDIA_CHILD):
        ss_set(UIKeys.MEDIA_CHILD, child_id)
        ss_set(UIKeys.MEDIA_PAGE, 0)
        ss_set(UIKeys.MEDIA_SELECTED, None)

    if not child_id:
        st.warning("Kein Kind ausgewählt. / No child selected.")
        return

    try:
        if _is_onedrive_enabled():
            media_items = [
                MediaItem(
                    id=item["id"],
                    child_id=child_id,
                    name=item["name"],
                    mime_type="image/jpeg",
                    kind="image",
                    source="onedrive",
                )
                for item in list_photos_from_onedrive()
            ]
        else:
            folder_id = _get_media_folder_id(ctx)
            if not folder_id:
                st.warning(
                    "Kein zentraler Medien-Ordner vorhanden. / No central media folder configured."
                )
                return

            raw_media_items = _list_media(folder_id)
            media_items = _filter_media_items_for_child(
                ctx,
                _to_media_items(
                    raw_media_items,
                    child_id=child_id,
                    source=str(getattr(ctx.app_config, "storage_mode", "google")),
                ),
                child_id,
            )
    except DriveServiceError as exc:
        error_banner(
            "Medien konnten nicht geladen werden. Bitte Drive-Freigaben prüfen.",
            "Could not load media. Please verify Drive sharing.",
            details=_format_drive_error_details(exc),
        )
        return
    except OneDriveAuthError as exc:
        error_banner(
            "OneDrive-Bilder konnten nicht geladen werden.",
            "Could not load OneDrive photos.",
            details=str(exc),
        )
        return

    if not media_items:
        st.caption("Keine Medien gefunden. / No media found.")
        return

    selected_item = render_media_gallery(
        _with_preview_payload(media_items), page_size=24
    )
    if not selected_item:
        return

    with card("Aktionen / Actions"):
        st.write(f"**Datei / File:** {selected_item.name}")
        st.caption(f"ID: {selected_item.id}")
        st.caption(f"MIME: {selected_item.mime_type}")
        st.download_button(
            "Download / Download",
            data=selected_item.preview_bytes
            or (
                download_photo_from_onedrive(selected_item.id)
                if selected_item.source == "onedrive"
                else _get_media_bytes(selected_item.id)
            ),
            file_name=selected_item.name,
            mime=selected_item.mime_type,
            key=f"gallery_download_{selected_item.id}",
        )

        meta = ctx.stammdaten_manager.get_photo_meta_by_file_id(selected_item.id) or {}
        current_status = _normalize_photo_status(str(meta.get("status", "")))
        st.write(f"Status: **{current_status}**")


def render_upload(ctx: MediaPageContext) -> None:
    page_header("Upload")
    render_onedrive_embed_panel()
    selected_child = st.selectbox(
        "Medium hochladen für Kind / Upload media for child",
        options=ctx.children,
        format_func=lambda child: str(child.get("name", "")),
        key=UIKeys.MEDIA_UPLOAD_CHILD_SELECT,
    )

    with st.form("photo_upload_form", border=True):
        upload_file = st.file_uploader(
            "Datei auswählen / Select media",
            type=["jpg", "jpeg", "png"]
            if _is_onedrive_enabled()
            else ["jpg", "jpeg", "png", "mp4", "mov", "webm"],
        )
        upload_submitted = st.form_submit_button("Upload / Upload")

    if not upload_submitted:
        return

    if upload_file is None:
        st.warning("Bitte zuerst eine Datei auswählen. / Please select a file first.")
        return

    child_id = str(selected_child.get("id", "")).strip()
    try:
        if _is_onedrive_enabled():
            upload_result = upload_photo_to_onedrive(
                upload_file.getvalue(), upload_file.name
            )
            file_id = str(upload_result.get("id", "")).strip()
            if not file_id:
                raise ValueError("OneDrive hat keine Datei-ID zurückgegeben.")
        else:
            folder_id = _get_media_folder_id(ctx)
            if not folder_id:
                raise ValueError(
                    "Kein zentraler Medien-Ordner vorhanden. / No central media folder configured."
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
        download_photo_from_onedrive.clear()
        st.success(
            "Upload erfolgreich (Status: draft). / Upload successful (status: draft)."
        )
        if str(upload_file.type or "").startswith("video/"):
            st.video(upload_file)
        else:
            st.image(upload_file, use_container_width=True)
    except DriveServiceError as exc:
        error_banner(
            "Upload fehlgeschlagen. Prüfen Sie die Ordnerfreigabe und Drive-ID.",
            "Upload failed. Verify folder sharing and Drive ID.",
            details=_format_drive_error_details(exc),
        )
    except ValueError as exc:
        st.error(f"Fehler beim Upload / Upload failed: {exc}")
    except OneDriveAuthError as exc:
        if exc.reason == "auth":
            st.error(
                "OneDrive-Upload fehlgeschlagen: Authentifizierung ungültig. Bitte "
                "Azure-Secrets prüfen. / OneDrive upload failed: authentication "
                "invalid. Please verify Azure secrets."
            )
        elif exc.reason == "path":
            st.error(
                "OneDrive-Upload fehlgeschlagen: Zielordner nicht gefunden. Bitte "
                "[onedrive].folder_path prüfen. / OneDrive upload failed: target "
                "folder not found. Please verify [onedrive].folder_path."
            )
        elif exc.reason == "permission":
            st.error(
                "OneDrive-Upload fehlgeschlagen: Fehlende Berechtigung auf dem Ziel-"
                "Drive. / OneDrive upload failed: missing permission on target drive."
            )
        else:
            st.error(f"OneDrive-Upload fehlgeschlagen. / OneDrive upload failed: {exc}")


def render_photo_status(ctx: MediaPageContext) -> None:
    page_header("Status")
    selected_child = st.selectbox(
        "Status verwalten für Kind / Manage status for child",
        options=ctx.children,
        format_func=lambda child: str(child.get("name", "")),
        key=UIKeys.MEDIA_STATUS_CHILD_SELECT,
    )
    child_id = str(selected_child.get("id", "")).strip()

    try:
        folder_id = _get_media_folder_id(ctx)
    except DriveServiceError as exc:
        error_banner(
            "Foto-Ordner konnte nicht geladen werden.",
            "Could not load media folder.",
            details=_format_drive_error_details(exc),
        )
        return

    if not folder_id:
        st.warning(
            "Kein zentraler Medien-Ordner vorhanden. / No central media folder configured."
        )
        return

    drive_url = f"https://drive.google.com/drive/folders/{folder_id}"
    st.markdown(
        f"[📂 Ordner auf Google Drive öffnen / Open folder on Google Drive]({drive_url})"
    )

    raw_media_items = _list_media(folder_id)
    media_items = _filter_media_items_for_child(
        ctx,
        _to_media_items(
            raw_media_items,
            child_id=child_id,
            source=str(getattr(ctx.app_config, "storage_mode", "google")),
        ),
        child_id,
    )
    if not media_items:
        st.caption(
            "Keine Medien für das ausgewählte Kind gefunden. / "
            "No media found for the selected child."
        )
        return

    for media_item in media_items:
        meta = ctx.stammdaten_manager.get_photo_meta_by_file_id(media_item.id) or {}
        current_status = _normalize_photo_status(meta.get("status"))
        with st.expander(
            f"{media_item.name} · Status verwalten / Manage status",
            expanded=False,
        ):
            selected_status = st.selectbox(
                "Status / Status",
                options=list(PHOTO_STATUS_OPTIONS),
                index=list(PHOTO_STATUS_OPTIONS).index(current_status),
                key=f"admin_media_status_{media_item.id}",
            )

            media_bytes = _get_media_bytes(media_item.id)
            if media_item.is_video:
                st.video(media_bytes)
            else:
                st.image(media_bytes, width=320)

            if selected_status == current_status:
                continue

            ctx.stammdaten_manager.upsert_photo_meta(
                media_item.id,
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
