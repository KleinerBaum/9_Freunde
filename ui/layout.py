from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

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


@contextmanager
def section_card(
    title: str,
    *,
    description: str | None = None,
    icon: str | None = None,
    key: str | None = None,
) -> Iterator[None]:
    with st.container(border=True, key=key):
        title_prefix = f"{icon} " if icon else ""
        st.markdown(f"### {title_prefix}{title}")
        if description:
            st.caption(description)
        yield


def render_kpi_widgets(items: list[dict[str, Any]]) -> None:
    if not items:
        return
    columns = st.columns(len(items))
    for index, item in enumerate(items):
        label = str(item.get("label", "—"))
        value = item.get("value", "—")
        delta = item.get("delta")
        help_text = item.get("help")
        with columns[index]:
            st.metric(label=label, value=value, delta=delta, help=help_text)


def table_toolbar(
    *,
    search_key: str,
    refresh_label: str,
    search_label: str = "Suchen / Search",
) -> tuple[str, bool]:
    search_col, action_col = st.columns([4, 1])
    with search_col:
        search_value = st.text_input(search_label, key=search_key)
    with action_col:
        refresh_clicked = st.button(refresh_label, use_container_width=True)
    return search_value.strip(), refresh_clicked


def empty_state(title: str, description: str, *, icon: str = "📭") -> None:
    st.info(f"{icon} **{title}**\n\n{description}")


def form_feedback(
    success_message: str | None = None, error_message: str | None = None
) -> None:
    if success_message:
        st.success(success_message)
    if error_message:
        st.error(error_message)


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
