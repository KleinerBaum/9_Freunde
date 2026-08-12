from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource, build  # type: ignore[import-untyped]

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"


def _service_account_info() -> dict[str, Any]:
    """Return service account info from Streamlit secrets.

    Raises:
        RuntimeError: If the required `gcp_service_account` secret is missing.
    """
    service_account_info = st.secrets.get("gcp_service_account")
    if not service_account_info:
        raise RuntimeError(
            "Missing Streamlit secret 'gcp_service_account'. "
            "Please configure service account credentials in secrets.toml."
        )
    return dict(service_account_info)


def _build_google_client(*, api: str, version: str, scopes: Sequence[str]) -> Resource:
    credentials = Credentials.from_service_account_info(
        _service_account_info(),
        scopes=list(scopes),
    )
    return build(api, version, credentials=credentials, cache_discovery=False)


@st.cache_resource
def get_drive_client() -> Resource:
    """Create and cache a Google Drive API client."""
    return _build_google_client(api="drive", version="v3", scopes=[DRIVE_SCOPE])


@st.cache_resource
def get_sheets_client() -> Resource:
    """Create and cache a Google Sheets API client."""
    return _build_google_client(api="sheets", version="v4", scopes=[SHEETS_SCOPE])


@st.cache_resource
def get_calendar_client() -> Resource:
    """Create and cache a Google Calendar API client."""
    return _build_google_client(api="calendar", version="v3", scopes=[CALENDAR_SCOPE])
