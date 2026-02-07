"""Zentrale Konfiguration und Secret-Validierung für die 9 Freunde App."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal, Mapping

import streamlit as st

DEFAULT_TIMEZONE = "Europe/Berlin"
DEFAULT_OPENAI_MODEL_FAST = "gpt-4o-mini"
DEFAULT_OPENAI_MODEL_PRECISE = "o3-mini"
DEFAULT_OPENAI_TIMEOUT_SECONDS = 30.0
DEFAULT_OPENAI_MAX_RETRIES = 3
DEFAULT_OPENAI_REASONING_EFFORT: Literal["low", "medium", "high"] = "medium"


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
    openai: "OpenAIConfig"


@dataclass(frozen=True)
class OpenAIConfig:
    """OpenAI-Konfiguration für Responses API."""

    api_key: str | None
    model_fast: str
    model_precise: str
    precision_mode: Literal["fast", "precise"]
    timeout_seconds: float
    max_retries: int
    reasoning_effort: Literal["low", "medium", "high"]
    base_url: str | None
    vector_store_id: str | None
    enable_web_search: bool


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


def _read_secret_or_env(
    secrets_section: Mapping[str, Any],
    key: str,
    env_key: str,
) -> str | None:
    secret_value = secrets_section.get(key)
    if isinstance(secret_value, str) and secret_value.strip():
        return secret_value.strip()

    env_value = os.getenv(env_key)
    if isinstance(env_value, str) and env_value.strip():
        return env_value.strip()
    return None


def _read_bool(
    secrets_section: Mapping[str, Any],
    key: str,
    env_key: str,
    *,
    default: bool,
) -> bool:
    secret_value = secrets_section.get(key)
    if isinstance(secret_value, bool):
        return secret_value

    env_value = os.getenv(env_key)
    if isinstance(env_value, str):
        normalized = env_value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _load_openai_config(secrets: Mapping[str, Any]) -> OpenAIConfig:
    openai_section_raw = secrets.get("openai", {})
    openai_section = (
        openai_section_raw if isinstance(openai_section_raw, Mapping) else {}
    )

    precision_mode = _read_secret_or_env(
        openai_section,
        "precision_mode",
        "OPENAI_PRECISION_MODE",
    )
    normalized_precision_mode = (
        (precision_mode or "fast").strip().lower()
        if isinstance(precision_mode, str)
        else "fast"
    )
    if normalized_precision_mode not in {"fast", "precise"}:
        raise ConfigError(
            "Ungültiger OpenAI-Präzisionsmodus. Erlaubte Werte: 'fast' oder 'precise'."
        )

    reasoning_effort = _read_secret_or_env(
        openai_section,
        "reasoning_effort",
        "OPENAI_REASONING_EFFORT",
    )
    normalized_reasoning_effort = (
        (reasoning_effort or DEFAULT_OPENAI_REASONING_EFFORT).strip().lower()
    )
    if normalized_reasoning_effort not in {"low", "medium", "high"}:
        raise ConfigError(
            "Ungültiger OpenAI-Reasoning-Wert. Erlaubte Werte: 'low', 'medium', 'high'."
        )

    timeout_raw = _read_secret_or_env(
        openai_section,
        "timeout_seconds",
        "OPENAI_TIMEOUT_SECONDS",
    )
    timeout_seconds = (
        float(timeout_raw)
        if isinstance(timeout_raw, str)
        else DEFAULT_OPENAI_TIMEOUT_SECONDS
    )
    if timeout_seconds <= 0:
        raise ConfigError("OPENAI timeout_seconds muss größer als 0 sein.")

    retries_raw = _read_secret_or_env(
        openai_section,
        "max_retries",
        "OPENAI_MAX_RETRIES",
    )
    max_retries = (
        int(retries_raw) if isinstance(retries_raw, str) else DEFAULT_OPENAI_MAX_RETRIES
    )
    if max_retries < 0:
        raise ConfigError("OPENAI max_retries darf nicht negativ sein.")

    api_key = _read_secret_or_env(openai_section, "api_key", "OPENAI_API_KEY")
    base_url = _read_secret_or_env(openai_section, "base_url", "OPENAI_BASE_URL")
    vector_store_id = _read_secret_or_env(
        openai_section,
        "vector_store_id",
        "VECTOR_STORE_ID",
    )
    model_fast = (
        _read_secret_or_env(openai_section, "model_fast", "OPENAI_MODEL_FAST")
        or DEFAULT_OPENAI_MODEL_FAST
    )
    model_precise = (
        _read_secret_or_env(openai_section, "model_precise", "OPENAI_MODEL_PRECISE")
        or DEFAULT_OPENAI_MODEL_PRECISE
    )
    enable_web_search = _read_bool(
        openai_section,
        "enable_web_search",
        "OPENAI_ENABLE_WEB_SEARCH",
        default=True,
    )

    return OpenAIConfig(
        api_key=api_key,
        model_fast=model_fast,
        model_precise=model_precise,
        precision_mode=normalized_precision_mode,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        reasoning_effort=normalized_reasoning_effort,
        base_url=base_url,
        vector_store_id=vector_store_id,
        enable_web_search=enable_web_search,
    )


@st.cache_resource(show_spinner=False)
def get_app_config() -> AppConfig:
    """Lädt und validiert die zentrale App-Konfiguration aus ``st.secrets``."""
    google = _load_google_config(st.secrets)
    openai = _load_openai_config(st.secrets)
    return AppConfig(google=google, openai=openai)


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
