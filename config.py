"""Zentrale Konfiguration und Secret-Validierung für die 9 Freunde App."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

DEFAULT_TIMEZONE = "Europe/Berlin"
DEFAULT_OPENAI_MODEL_FAST = "gpt-4o-mini"
DEFAULT_OPENAI_MODEL_PRECISE = "o3-mini"
DEFAULT_OPENAI_TIMEOUT_SECONDS = 30.0
DEFAULT_OPENAI_MAX_RETRIES = 3
DEFAULT_OPENAI_REASONING_EFFORT: Literal["low", "medium", "high"] = "medium"
DEFAULT_STORAGE_MODE: Literal["local", "google"] = "local"
DEFAULT_DATA_DIR = "./data"
DEFAULT_STAMMDATEN_SHEET_ID = "1ZuehceuiGnqpwhMxynfCulpSuCg0M2WE-nsQoTEJx-A"


class ConfigError(RuntimeError):
    """Fehler bei fehlender oder ungültiger Konfiguration."""


@dataclass(frozen=True)
class GoogleConfig:
    """Google-bezogene Konfigurationswerte aus ``st.secrets``."""

    service_account: dict[str, Any]
    drive_photos_root_folder_id: str
    drive_contracts_folder_id: str
    stammdaten_sheet_id: str
    stammdaten_sheet_tab: str
    children_tab: str
    parents_tab: str
    consents_tab: str
    pickup_authorizations_tab: str
    medications_tab: str
    content_pages_tab: str
    calendar_id: str | None

    @property
    def photos_folder_id(self) -> str:
        """Rückwärtskompatibler Alias für bestehenden Code."""
        return self.drive_photos_root_folder_id


@dataclass(frozen=True)
class LocalConfig:
    """Lokale Speicherorte für den Prototyp-Modus."""

    data_dir: Path
    children_file: Path
    pickup_authorizations_file: Path
    medications_file: Path
    content_pages_file: Path
    calendar_file: Path
    drive_root: Path


@dataclass(frozen=True)
class AppConfig:
    """App-weite Konfigurationswerte."""

    storage_mode: Literal["local", "google"]
    google: GoogleConfig | None
    local: LocalConfig
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

DEFAULT_CHILDREN_TAB = "children"
DEFAULT_PARENTS_TAB = "parents"
DEFAULT_CONSENTS_TAB = "consents"
DEFAULT_PICKUP_AUTHORIZATIONS_TAB = "pickup_authorizations"
DEFAULT_MEDICATIONS_TAB = "medications"
DEFAULT_CONTENT_PAGES_TAB = "content_pages"


def _strip_outer_quotes(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "'"}:
        return stripped[1:-1].strip()
    return stripped


def _normalize_private_key(private_key: str) -> str:
    normalized_key = _strip_outer_quotes(private_key)
    normalized_key = normalized_key.replace("\\n", "\n")

    begin_marker = "-----BEGIN PRIVATE KEY-----"
    end_marker = "-----END PRIVATE KEY-----"

    trimmed_key = normalized_key.strip()
    if not trimmed_key.startswith(begin_marker) or not trimmed_key.endswith(end_marker):
        raise ConfigError(
            "Ungültiger gcp_service_account.private_key. Der Key muss mit "
            "'-----BEGIN PRIVATE KEY-----' beginnen und mit "
            "'-----END PRIVATE KEY-----' enden."
        )
    return trimmed_key + "\n"


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


def _read_tab_name(config: Mapping[str, Any], key: str, default: str) -> str:
    raw_value = config.get(key)
    if raw_value is None:
        return default

    if not isinstance(raw_value, str):
        raise ConfigError(
            f"Ungültiger Wert für gcp.{key}. Erwartet wird ein nicht-leerer String."
        )

    normalized = raw_value.strip()
    if not normalized:
        raise ConfigError(
            f"Ungültiger Wert für gcp.{key}. Der Tab-Name darf nicht leer sein."
        )

    invalid_chars = {":", "\\", "/", "?", "*", "[", "]"}
    invalid_found = sorted(char for char in invalid_chars if char in normalized)
    if invalid_found:
        invalid_joined = " ".join(invalid_found)
        raise ConfigError(
            f"Ungültiger Wert für gcp.{key}. Der Tab-Name enthält nicht erlaubte "
            f"Zeichen ({invalid_joined})."
        )

    if len(normalized) > 100:
        raise ConfigError(
            f"Ungültiger Wert für gcp.{key}. Der Tab-Name darf maximal 100 Zeichen "
            "lang sein."
        )
    return normalized


def _load_local_config(secrets: Mapping[str, Any]) -> LocalConfig:
    local_section_raw = secrets.get("local", {})
    local_section = local_section_raw if isinstance(local_section_raw, Mapping) else {}

    data_dir_raw = local_section.get("data_dir")
    data_dir = (
        Path(data_dir_raw)
        if isinstance(data_dir_raw, str) and data_dir_raw.strip()
        else Path(DEFAULT_DATA_DIR)
    )

    children_file = data_dir / "children.json"
    pickup_authorizations_file = data_dir / "pickup_authorizations.json"
    medications_file = data_dir / "medications.json"
    content_pages_file = data_dir / "content_pages.json"
    calendar_file = data_dir / "calendar_events.json"
    drive_root = data_dir / "drive"

    data_dir.mkdir(parents=True, exist_ok=True)
    drive_root.mkdir(parents=True, exist_ok=True)

    return LocalConfig(
        data_dir=data_dir,
        children_file=children_file,
        pickup_authorizations_file=pickup_authorizations_file,
        medications_file=medications_file,
        content_pages_file=content_pages_file,
        calendar_file=calendar_file,
        drive_root=drive_root,
    )


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

    gcp_service_account["private_key"] = _normalize_private_key(
        str(gcp_service_account["private_key"])
    )

    gcp = _require_mapping(secrets.get("gcp"), "gcp")

    required_keys = ("drive_photos_root_folder_id", "drive_contracts_folder_id")
    missing_gcp_keys = [
        f"gcp.{key}"
        for key in required_keys
        if not isinstance(gcp.get(key), str) or not str(gcp.get(key)).strip()
    ]
    if missing_gcp_keys:
        missing_joined = ", ".join(missing_gcp_keys)
        raise ConfigError(
            "Folgende Pflicht-Keys fehlen in .streamlit/secrets.toml: "
            f"{missing_joined}."
        )

    drive_photos_root_folder_id = str(gcp["drive_photos_root_folder_id"]).strip()
    drive_contracts_folder_id = str(gcp["drive_contracts_folder_id"]).strip()
    sheet_id_raw = gcp.get("stammdaten_sheet_id")
    stammdaten_sheet_id = (
        str(sheet_id_raw).strip()
        if isinstance(sheet_id_raw, str) and str(sheet_id_raw).strip()
        else DEFAULT_STAMMDATEN_SHEET_ID
    )
    sheet_tab_raw = gcp.get("stammdaten_sheet_tab")
    stammdaten_sheet_tab = (
        str(sheet_tab_raw).strip()
        if isinstance(sheet_tab_raw, str) and str(sheet_tab_raw).strip()
        else "Stammdaten_Eltern_2026"
    )
    children_tab = _read_tab_name(gcp, "children_tab", DEFAULT_CHILDREN_TAB)
    parents_tab = _read_tab_name(gcp, "parents_tab", DEFAULT_PARENTS_TAB)
    consents_tab = _read_tab_name(gcp, "consents_tab", DEFAULT_CONSENTS_TAB)
    pickup_authorizations_tab = _read_tab_name(
        gcp,
        "pickup_authorizations_tab",
        DEFAULT_PICKUP_AUTHORIZATIONS_TAB,
    )
    medications_tab = _read_tab_name(gcp, "medications_tab", DEFAULT_MEDICATIONS_TAB)
    content_pages_tab = _read_tab_name(
        gcp,
        "content_pages_tab",
        DEFAULT_CONTENT_PAGES_TAB,
    )
    calendar_raw = gcp.get("calendar_id")
    calendar_id = (
        str(calendar_raw).strip()
        if isinstance(calendar_raw, str) and str(calendar_raw).strip()
        else None
    )

    _validate_admin_emails_optional(secrets)

    return GoogleConfig(
        service_account=gcp_service_account,
        drive_photos_root_folder_id=drive_photos_root_folder_id,
        drive_contracts_folder_id=drive_contracts_folder_id,
        stammdaten_sheet_id=stammdaten_sheet_id,
        stammdaten_sheet_tab=stammdaten_sheet_tab,
        children_tab=children_tab,
        parents_tab=parents_tab,
        consents_tab=consents_tab,
        pickup_authorizations_tab=pickup_authorizations_tab,
        medications_tab=medications_tab,
        content_pages_tab=content_pages_tab,
        calendar_id=calendar_id,
    )


def _validate_admin_emails_optional(secrets: Mapping[str, Any]) -> None:
    """Validiert optionales Admin-E-Mail-Array in [app] oder [auth]."""
    app_section = secrets.get("app", {})
    auth_section = secrets.get("auth", {})

    app_admin_emails = (
        app_section.get("admin_emails") if isinstance(app_section, Mapping) else None
    )
    auth_admin_emails = (
        auth_section.get("admin_emails") if isinstance(auth_section, Mapping) else None
    )

    if app_admin_emails is None and auth_admin_emails is None:
        return

    for path, values in (
        ("app.admin_emails", app_admin_emails),
        ("auth.admin_emails", auth_admin_emails),
    ):
        if values is None:
            continue
        if not isinstance(values, list) or not all(
            isinstance(item, str) and item.strip() for item in values
        ):
            raise ConfigError(
                f"Optionaler Key '{path}' muss eine Liste nicht-leerer E-Mail-Strings sein."
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
    storage_section_raw = st.secrets.get("storage", {})
    storage_section = (
        storage_section_raw if isinstance(storage_section_raw, Mapping) else {}
    )
    storage_mode_raw = _read_secret_or_env(
        storage_section,
        "mode",
        "APP_STORAGE_MODE",
    )
    storage_mode = (
        storage_mode_raw.strip().lower()
        if isinstance(storage_mode_raw, str)
        else DEFAULT_STORAGE_MODE
    )
    if storage_mode not in {"local", "google"}:
        raise ConfigError("storage.mode muss 'local' oder 'google' sein.")

    local = _load_local_config(st.secrets)
    google = _load_google_config(st.secrets) if storage_mode == "google" else None
    openai = _load_openai_config(st.secrets)

    return AppConfig(
        storage_mode=storage_mode,
        google=google,
        local=local,
        openai=openai,
    )


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
    except StreamlitSecretNotFoundError as exc:
        st.error(
            "Secrets-Datei ist ungültig oder fehlt. "
            "Bitte prüfen Sie .streamlit/secrets.toml auf TOML-Syntaxfehler "
            "(z. B. fehlende Werte nach '=' oder ungültige Inline-Tabellen)."
        )
        st.error(
            "Secrets file is missing or invalid. "
            "Please check .streamlit/secrets.toml for TOML syntax errors "
            "(for example missing values after '=' or invalid inline tables)."
        )
        st.caption(str(exc))
        st.stop()
