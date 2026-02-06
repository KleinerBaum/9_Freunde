import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def _sa_info() -> dict:
    return dict(st.secrets["gcp_service_account"])

@st.cache_resource
def get_drive_client():
    creds = service_account.Credentials.from_service_account_info(
        _sa_info(), scopes=DRIVE_SCOPES
    )
    return build("drive", "v3", credentials=creds)

@st.cache_resource
def get_sheets_client():
    creds = service_account.Credentials.from_service_account_info(
        _sa_info(), scopes=SHEETS_SCOPES
    )
    return build("sheets", "v4", credentials=creds)
