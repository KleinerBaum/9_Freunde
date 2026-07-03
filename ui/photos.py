from __future__ import annotations

from typing import Any

import streamlit as st

from services.photo_share_service import (
    PhotoShareError,
    child_id_from_record,
    list_child_photos,
    upload_child_photo,
)


def _child_label(child_record: dict[str, Any]) -> str:
    name = str(child_record.get("name") or "").strip() or "Unbenannt / Untitled"
    child_id = child_id_from_record(child_record) or "-"
    return f"{name} ({child_id})"


def _selected_child(
    *,
    user_role: str,
    children: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if user_role == "admin":
        if not children:
            st.info("Keine Kinder vorhanden. / No children available.")
            return None
        return st.selectbox(
            "Kind auswählen / Select child",
            options=children,
            format_func=_child_label,
            key="photos.child_select",
        )

    if not children:
        st.info(
            "Für dieses Elternkonto wurde kein Kind gefunden. / "
            "No child was found for this parent account."
        )
        return None

    return children[0]


def _show_unexpected_error(message: str, exc: Exception) -> None:
    st.error(f"{message} ({type(exc).__name__})")


def _render_upload_form(
    *,
    selected_child: dict[str, Any],
    user_email: str,
    drive_agent: Any,
) -> None:
    with st.form(key="photos.upload_form", border=True):
        uploaded_files = st.file_uploader(
            "Fotos auswählen / Select photos",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="photos.upload_files",
        )
        submitted = st.form_submit_button("Fotos speichern / Save photos")

    if not submitted:
        return

    files_to_upload = uploaded_files or []
    if not files_to_upload:
        st.info("Bitte mindestens ein Foto auswählen. / Please select at least one photo.")
        return

    saved_count = 0
    for uploaded_file in files_to_upload:
        try:
            upload_child_photo(
                drive_agent=drive_agent,
                child_record=selected_child,
                uploaded_file=uploaded_file,
                uploaded_by_email=user_email,
            )
            saved_count += 1
        except PhotoShareError as exc:
            st.error(f"Foto konnte nicht gespeichert werden. / Photo could not be saved: {exc}")
        except Exception as exc:  # pragma: no cover - runtime integration guard
            _show_unexpected_error(
                "Unerwarteter Fehler beim Speichern. / Unexpected error while saving.",
                exc,
            )

    if saved_count:
        st.success(f"{saved_count} Foto(s) gespeichert. / {saved_count} photo(s) saved.")


def _render_gallery(*, selected_child: dict[str, Any], drive_agent: Any) -> None:
    try:
        photos = list_child_photos(drive_agent, selected_child)
    except PhotoShareError as exc:
        st.error(f"Fotos konnten nicht geladen werden. / Photos could not be loaded: {exc}")
        return
    except Exception as exc:  # pragma: no cover - runtime integration guard
        _show_unexpected_error(
            "Unerwarteter Fehler beim Laden. / Unexpected error while loading.",
            exc,
        )
        return

    if not photos:
        st.info("Keine Fotos vorhanden. / No photos available.")
        return

    for photo in photos[:30]:
        file_id = str(photo.get("id") or "").strip()
        file_name = str(photo.get("name") or "").strip() or "photo"
        mime_type = str(photo.get("mimeType") or "").strip() or "application/octet-stream"

        if not file_id:
            st.warning(
                f"Foto ohne Datei-ID übersprungen: {file_name} / "
                f"Skipped photo without file id: {file_name}"
            )
            continue

        st.markdown(f"**{file_name}**")
        try:
            photo_bytes = drive_agent.download_file(file_id)
        except PhotoShareError as exc:
            st.error(f"Foto konnte nicht geladen werden. / Photo could not be loaded: {exc}")
            continue
        except Exception as exc:  # pragma: no cover - runtime integration guard
            _show_unexpected_error(
                "Unerwarteter Fehler beim Download. / Unexpected error while downloading.",
                exc,
            )
            continue

        st.image(photo_bytes)
        st.download_button(
            "Herunterladen / Download",
            data=photo_bytes,
            file_name=file_name,
            mime=mime_type,
            key=f"photos.download.{file_id}",
        )


def render_photo_share_page(
    *,
    user_role: str,
    user_email: str,
    children: list[dict[str, Any]],
    drive_agent: Any,
) -> None:
    st.title("Fotos & Medien / Photos & media")

    selected_child = _selected_child(user_role=user_role, children=children)
    if selected_child is None:
        return

    folder_id = str(selected_child.get("folder_id") or "").strip()
    if not folder_id:
        st.warning(
            "Für dieses Kind fehlt der Drive-Ordner. / "
            "The Drive folder is missing for this child."
        )
        return

    _render_upload_form(
        selected_child=selected_child,
        user_email=user_email,
        drive_agent=drive_agent,
    )
    _render_gallery(selected_child=selected_child, drive_agent=drive_agent)
