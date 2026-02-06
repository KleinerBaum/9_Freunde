"""Zentrale Konfiguration und Secret-Validierung für die 9 Freunde App."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

import streamlit as st

DEFAULT_TIMEZONE = "Europe/Berlin"
DEFAULT_OPENAI_MODEL = "text-davinci-003"


class ConfigError(RuntimeError):
    """Fehler bei fehlender oder ungültiger Konfiguration."""


@dataclass(frozen=True)
class GoogleConfig:
    """Google-bezogene Konfigurationswerte aus ``st.secrets``."""

    service_account: dict[str, Any]
    calendar_id: str
    photos_folder_id: str


@dataclass(frozen=True)
class AppConfig:
    """App-weite Konfigurationswerte."""

    google: GoogleConfig
    openai_api_key: str | None


REQUIRED_GCP_SERVICE_ACCOUNT_KEYS = (
    "type",
    "project_id",
    "private_key_id",
    "private_key",
    "client_email",
    "client_id",
    "token_uri",
)


def _require_mapping(raw_value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(raw_value, Mapping):
        raise ConfigError(
            f"Konfigurationsbereich '{path}' fehlt oder ist ungültig. "
            "Bitte prüfen Sie Ihr secrets.toml."
        )
    return raw_value


def _require_string(config: Mapping[str, Any], key: str, path: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(
            f"Fehlender Schlüssel '{path}.{key}'. "
            "Bitte ergänzen Sie den Wert in .streamlit/secrets.toml."
        )
    return value.strip()


def _load_google_config(secrets: Mapping[str, Any]) -> GoogleConfig:
    gcp_service_account_raw = _require_mapping(
        secrets.get("gcp_service_account"),
        "gcp_service_account",
    )
    gcp_service_account = dict(gcp_service_account_raw)

    missing_sa_keys = [
        key
        for key in REQUIRED_GCP_SERVICE_ACCOUNT_KEYS
        if not isinstance(gcp_service_account.get(key), str)
        or not str(gcp_service_account[key]).strip()
    ]
    if missing_sa_keys:
        missing_joined = ", ".join(missing_sa_keys)
        raise ConfigError(
            "Der Service-Account in 'gcp_service_account' ist unvollständig. "
            f"Fehlende Felder: {missing_joined}."
        )

    gcp = _require_mapping(secrets.get("gcp"), "gcp")
    calendar_id = _require_string(gcp, "calendar_id", "gcp")
    photos_folder_id = _require_string(gcp, "photos_folder_id", "gcp")

    return GoogleConfig(
        service_account=gcp_service_account,
        calendar_id=calendar_id,
        photos_folder_id=photos_folder_id,
    )


@st.cache_resource(show_spinner=False)
def get_app_config() -> AppConfig:
    """Lädt und validiert die zentrale App-Konfiguration aus ``st.secrets``."""
    google = _load_google_config(st.secrets)
    openai_api_key = st.secrets.get("openai", {}).get(
        "api_key",
        os.getenv("OPENAI_API_KEY"),
    )
    return AppConfig(google=google, openai_api_key=openai_api_key)


def validate_config_or_stop() -> AppConfig:
    """Validiert die Konfiguration und stoppt die UI mit klarer Fehlermeldung bei Fehlern."""
    try:
        return get_app_config()
    except ConfigError as exc:
        st.error(
            f"Konfigurationsfehler: {exc}\n\nBitte secrets.toml gemäß README ergänzen."
        )
        st.error(
            "Configuration error: "
            f"{exc}\n\n"
            "Please update secrets.toml as documented in the README."
        )
        st.stop()
