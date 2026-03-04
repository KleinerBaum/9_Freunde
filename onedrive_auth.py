from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import msal
import requests
import streamlit as st

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]


class OneDriveAuthError(RuntimeError):
    """Fehler bei OneDrive/Graph-Authentifizierung."""


@dataclass(frozen=True)
class OneDriveAuthConfig:
    client_id: str
    client_secret: str
    tenant_id: str


@dataclass(frozen=True)
class OneDriveFolderRef:
    id: str
    name: str
    web_url: str | None


class GraphClient:
    """Kleiner Graph-Client für OneDrive-Zugriffe."""

    def __init__(self, config: OneDriveAuthConfig) -> None:
        authority = f"https://login.microsoftonline.com/{config.tenant_id}"
        self._app = msal.ConfidentialClientApplication(
            client_id=config.client_id,
            client_credential=config.client_secret,
            authority=authority,
        )

    def _access_token(self) -> str:
        token_result = self._app.acquire_token_silent(GRAPH_SCOPE, account=None)
        if not token_result:
            token_result = self._app.acquire_token_for_client(scopes=GRAPH_SCOPE)

        access_token = str(token_result.get("access_token", "")).strip()
        if not access_token:
            error_description = str(token_result.get("error_description", "")).strip()
            raise OneDriveAuthError(
                "Microsoft Graph Token konnte nicht geladen werden. "
                f"Details: {error_description or 'unbekannt'}"
            )
        return access_token

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> requests.Response:
        request_headers = {
            "Authorization": f"Bearer {self._access_token()}",
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)

        response = requests.request(
            method=method,
            url=f"{GRAPH_BASE_URL}{path}",
            params=params,
            headers=request_headers,
            data=data,
            timeout=30,
        )
        if response.status_code >= 400:
            message = response.text[:400]
            raise OneDriveAuthError(
                f"Graph-Request fehlgeschlagen ({response.status_code}): {message}"
            )
        return response


def _load_onedrive_config() -> OneDriveAuthConfig:
    raw = st.secrets.get("onedrive")
    if not isinstance(raw, dict):
        raise OneDriveAuthError(
            "Fehlender Abschnitt [onedrive] in den Streamlit-Secrets."
        )

    client_id = str(raw.get("client_id", "")).strip()
    client_secret = str(raw.get("client_secret", "")).strip()
    tenant_id = str(raw.get("tenant_id", "")).strip()

    if not client_id or not client_secret or not tenant_id:
        raise OneDriveAuthError(
            "OneDrive-Secrets unvollständig. Benötigt: client_id, client_secret, tenant_id."
        )

    return OneDriveAuthConfig(
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
    )


def get_graph_client() -> GraphClient:
    return GraphClient(_load_onedrive_config())


def get_onedrive_folder(path: str) -> OneDriveFolderRef:
    normalized_path = path.strip().lstrip("/")
    if not normalized_path:
        raise OneDriveAuthError("OneDrive-Ordnerpfad darf nicht leer sein.")

    client = get_graph_client()
    response = client.request("GET", f"/me/drive/root:/{normalized_path}")
    payload = response.json()
    return OneDriveFolderRef(
        id=str(payload.get("id", "")),
        name=str(payload.get("name", normalized_path)),
        web_url=str(payload.get("webUrl", "")).strip() or None,
    )
