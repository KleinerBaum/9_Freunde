from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
from typing import Any

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import DEFAULT_TIMEZONE, get_app_config

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarServiceError(RuntimeError):
    """Domänenspezifischer Fehler für Kalenderzugriffe."""


@st.cache_resource(show_spinner=False)
def _get_calendar_client():
    app_config = get_app_config()
    if app_config.google is None:
        raise CalendarServiceError(
            "Google-Konfiguration fehlt. / Google configuration is missing."
        )

    credentials = service_account.Credentials.from_service_account_info(
        app_config.google.service_account,
        scopes=CALENDAR_SCOPES,
    )
    return build("calendar", "v3", credentials=credentials)


def _get_calendar_id() -> str:
    gcp_section = st.secrets.get("gcp")
    calendar_id = ""
    if isinstance(gcp_section, Mapping):
        calendar_id = str(gcp_section.get("calendar_id", "")).strip()
    if not calendar_id:
        raise CalendarServiceError(
            "`gcp.calendar_id` fehlt in den Streamlit-Secrets. / Missing `gcp.calendar_id` in Streamlit secrets."
        )
    return calendar_id


def _read_local_events() -> list[dict[str, Any]]:
    local_file = get_app_config().local.calendar_file
    if not local_file.exists():
        return []
    payload = json.loads(local_file.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _write_local_events(events: list[dict[str, Any]]) -> None:
    local_file = get_app_config().local.calendar_file
    local_file.parent.mkdir(parents=True, exist_ok=True)
    local_file.write_text(
        json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_event(
    *,
    title: str,
    event_date: date,
    event_time: time | None,
    description: str,
) -> None:
    """Erstellt einen Termin im konfigurierten Kalender."""
    normalized_title = title.strip()
    if not normalized_title:
        raise CalendarServiceError(
            "Titel darf nicht leer sein. / Title must not be empty."
        )

    app_config = get_app_config()
    start_dt = datetime.combine(event_date, event_time or time(hour=9, minute=0))
    end_dt = start_dt + timedelta(hours=1)

    event_body: dict[str, Any] = {
        "summary": normalized_title,
        "description": description.strip(),
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": DEFAULT_TIMEZONE,
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": DEFAULT_TIMEZONE,
        },
    }

    if app_config.storage_mode == "google":
        calendar = _get_calendar_client()
        calendar_id = _get_calendar_id()
        try:
            calendar.events().insert(calendarId=calendar_id, body=event_body).execute()
        except HttpError as exc:
            raise CalendarServiceError(
                f"Google Calendar API Fehler. / Google Calendar API error: {exc}"
            ) from exc
    else:
        local_event = {"id": uuid.uuid4().hex, **event_body}
        events = _read_local_events()
        events.append(local_event)
        _write_local_events(events)

    list_events.clear()


@st.cache_data(show_spinner=False, ttl=60)
def list_events(max_results: int = 10) -> list[dict[str, str]]:
    """Liefert kommende Termine (cached für 60 Sekunden)."""
    app_config = get_app_config()

    if app_config.storage_mode == "google":
        calendar = _get_calendar_client()
        calendar_id = _get_calendar_id()
        now = f"{datetime.utcnow().isoformat()}Z"
        try:
            response = (
                calendar.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
        except HttpError as exc:
            raise CalendarServiceError(
                f"Google Calendar API Fehler. / Google Calendar API error: {exc}"
            ) from exc
        raw_events = response.get("items", [])
    else:
        now_iso = datetime.utcnow().isoformat()
        raw_events = [
            item
            for item in _read_local_events()
            if item.get("start", {}).get("dateTime", "") >= now_iso
        ]
        raw_events.sort(key=lambda item: item.get("start", {}).get("dateTime", ""))
        raw_events = raw_events[:max_results]

    formatted: list[dict[str, str]] = []
    for item in raw_events:
        start_info = item.get("start", {})
        start_value = str(start_info.get("dateTime") or start_info.get("date") or "")
        summary = str(item.get("summary") or "(ohne Titel) / (untitled)")
        description = str(item.get("description") or "")
        formatted.append(
            {
                "summary": summary,
                "start": start_value,
                "description": description,
            }
        )
    return formatted
