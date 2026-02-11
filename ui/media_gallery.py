from __future__ import annotations

from math import ceil

import streamlit as st

from domain.models import MediaItem
from ui.layout import card
from ui.state_keys import UIKeys, ensure_defaults, ss_get, ss_set


def _filtered_items(items: list[MediaItem], kind_filter: str) -> list[MediaItem]:
    if kind_filter == "all":
        return items
    return [item for item in items if item.kind == kind_filter]


def render_media_gallery(
    items: list[MediaItem], *, page_size: int = 24
) -> MediaItem | None:
    ensure_defaults(
        {
            UIKeys.MEDIA_PAGE: 0,
            UIKeys.MEDIA_SELECTED: None,
            UIKeys.MEDIA_KIND_FILTER: "all",
        }
    )

    kind_filter = st.segmented_control(
        "Typ / Type",
        options=["all", "image", "video"],
        format_func=lambda value: {
            "all": "Alle / All",
            "image": "Bilder / Images",
            "video": "Videos / Videos",
        }[value],
        key=UIKeys.MEDIA_KIND_FILTER,
    )

    visible_items = _filtered_items(items, kind_filter or "all")
    if not visible_items:
        st.caption("Keine Medien für den aktuellen Filter. / No media for this filter.")
        ss_set(UIKeys.MEDIA_SELECTED, None)
        return None

    max_pages = max(1, ceil(len(visible_items) / page_size))
    current_page = min(max(0, int(ss_get(UIKeys.MEDIA_PAGE, 0))), max_pages - 1)
    ss_set(UIKeys.MEDIA_PAGE, current_page)

    prev_col, page_col, next_col = st.columns([1, 2, 1])
    with prev_col:
        if st.button("⬅️ Zurück / Previous", use_container_width=True):
            ss_set(UIKeys.MEDIA_PAGE, max(0, current_page - 1))
            st.rerun()
    with page_col:
        st.caption(f"Seite / Page {current_page + 1} von / of {max_pages}")
    with next_col:
        if st.button("Weiter / Next ➡️", use_container_width=True):
            ss_set(UIKeys.MEDIA_PAGE, min(max_pages - 1, current_page + 1))
            st.rerun()

    page_items = visible_items[
        current_page * page_size : (current_page + 1) * page_size
    ]

    grid_cols = st.columns(4)
    for index, item in enumerate(page_items):
        with grid_cols[index % 4]:
            with card(key=f"media_tile_{item.id}"):
                if item.thumb_bytes and item.is_image:
                    st.image(item.thumb_bytes, use_container_width=True)
                elif item.is_video:
                    st.caption("🎬 Video")
                else:
                    st.caption("🖼️ Bild / Image")
                st.caption(item.name)
                if st.button(
                    "Ansehen / Preview",
                    key=f"select_{item.id}",
                    use_container_width=True,
                ):
                    ss_set(UIKeys.MEDIA_SELECTED, item.id)

    selected_id = str(ss_get(UIKeys.MEDIA_SELECTED, "") or "").strip()
    selected_item = next(
        (item for item in visible_items if item.id == selected_id), None
    )
    if not selected_item:
        st.caption(
            "Bitte ein Medium auswählen, um die Vorschau zu sehen. / "
            "Select media to show preview."
        )
        return None

    with card("Vorschau / Preview"):
        if selected_item.is_video:
            if selected_item.preview_bytes:
                st.video(selected_item.preview_bytes)
            elif selected_item.preview_url:
                st.video(selected_item.preview_url)
            else:
                st.warning(
                    "Keine Videovorschau verfügbar. / No video preview available."
                )
        else:
            if selected_item.preview_bytes:
                st.image(selected_item.preview_bytes, use_container_width=True)
            elif selected_item.preview_url:
                st.image(selected_item.preview_url, use_container_width=True)
            else:
                st.warning(
                    "Keine Bildvorschau verfügbar. / No image preview available."
                )

    return selected_item
