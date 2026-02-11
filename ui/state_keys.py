from __future__ import annotations

from typing import Any

import streamlit as st


class UIKeys:
    NAV_MAIN = "nav.main"
    MEDIA_CHILD = "media.child_id"
    MEDIA_PAGE = "media.page"
    MEDIA_SELECTED = "media.selected"
    MEDIA_KIND_FILTER = "media.kind_filter"
    MEDIA_GALLERY_CHILD_SELECT = "media.gallery_child_select"
    MEDIA_UPLOAD_CHILD_SELECT = "media.upload_child_select"
    MEDIA_STATUS_CHILD_SELECT = "media.status_child_select"


def ss_get(key: str, default: Any = None) -> Any:
    return st.session_state.get(key, default)


def ss_set(key: str, value: Any) -> None:
    st.session_state[key] = value


def ensure_defaults(defaults: dict[str, Any]) -> None:
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def reset_keys(prefix: str) -> None:
    keys = [key for key in st.session_state.keys() if key.startswith(prefix)]
    for key in keys:
        del st.session_state[key]
