from __future__ import annotations

from typing import Any

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import get_app_config

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _sa_info() -> dict[str, Any]:
    return get_app_config().google.service_account


@st.cache_resource
def get_drive_client():
    creds = service_account.Credentials.from_service_account_info(
        _sa_info(),
        scopes=DRIVE_SCOPES,
    )
    return build("drive", "v3", credentials=creds)


@st.cache_resource
def get_sheets_client():
    creds = service_account.Credentials.from_service_account_info(
        _sa_info(),
        scopes=SHEETS_SCOPES,
    )
    return build("sheets", "v4", credentials=creds)
