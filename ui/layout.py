from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

import streamlit as st

_PAGE_CONFIG_DONE_KEY = "_ui.page_config_done"


def bootstrap_page(title: str, icon_path: str | None = None) -> None:
    if st.session_state.get(_PAGE_CONFIG_DONE_KEY):
        return

    icon_value: str = "🤱"
    if icon_path:
        path = Path(icon_path)
        if path.exists():
            icon_value = str(path)

    st.set_page_config(page_title=title, page_icon=icon_value, layout="wide")
    st.session_state[_PAGE_CONFIG_DONE_KEY] = True


def page_header(
    title: str, subtitle: str | None = None, right: str | None = None
) -> None:
    header_col, right_col = st.columns([5, 1])
    with header_col:
        st.title(title)
        if subtitle:
            st.caption(subtitle)
    with right_col:
        if right:
            st.caption(right)


@contextmanager
def card(title: str | None = None, *, key: str | None = None) -> Iterator[None]:
    with st.container(border=True, key=key):
        if title:
            st.markdown(f"### {title}")
        yield


def action_bar(actions: list[tuple[str, Callable[[], None]]]) -> None:
    if not actions:
        return
    columns = st.columns(len(actions))
    for index, (label, callback) in enumerate(actions):
        with columns[index]:
            if st.button(
                label, use_container_width=True, key=f"action_bar_{index}_{label}"
            ):
                callback()


def info_banner(msg_de: str, msg_en: str) -> None:
    st.info(f"{msg_de} / {msg_en}")


def error_banner(msg_de: str, msg_en: str, details: str | None = None) -> None:
    st.error(f"{msg_de} / {msg_en}")
    if details:
        st.caption(details)
