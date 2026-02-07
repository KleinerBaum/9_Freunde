from __future__ import annotations

import json
import uuid
from datetime import date, datetime, time, timedelta
from typing import Any

from config import DEFAULT_TIMEZONE, get_app_config

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:  # pragma: no cover - depends on optional runtime package
    service_account = None
    build = None


class CalendarAgent:
    def __init__(self) -> None:
        app_config = get_app_config()
        self.storage_mode = app_config.storage_mode
        self.timezone = DEFAULT_TIMEZONE
        self.local_calendar_file = app_config.local.calendar_file

        if self.storage_mode == "google":
            if service_account is None or build is None:
                raise RuntimeError(
                    "Google API-Pakete fehlen. Bitte requirements installieren."
                )
            if app_config.google is None:
                raise RuntimeError("Google-Konfiguration fehlt.")
            scopes = ["https://www.googleapis.com/auth/calendar"]
            credentials = service_account.Credentials.from_service_account_info(
                app_config.google.service_account,
                scopes=scopes,
            )
            self.service = build("calendar", "v3", credentials=credentials)
            self.calendar_id = app_config.google.calendar_id
        else:
            self.service = None
            self.calendar_id = "local-calendar"
            self.local_calendar_file.parent.mkdir(parents=True, exist_ok=True)
            if not self.local_calendar_file.exists():
                self.local_calendar_file.write_text("[]", encoding="utf-8")

    def _read_local_events(self) -> list[dict[str, Any]]:
        if not self.local_calendar_file.exists():
            return []
        data = json.loads(self.local_calendar_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _write_local_events(self, events: list[dict[str, Any]]) -> None:
        self.local_calendar_file.write_text(
            json.dumps(events, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_event(
        self,
        title: str,
        date: date,
        time: time | None = None,
        description: str = "",
        all_day: bool = False,
    ) -> None:
        """Fügt einen neuen Termin ein."""
        if all_day or time is None:
            start_date = date.strftime("%Y-%m-%d")
            end_date = (date + timedelta(days=1)).strftime("%Y-%m-%d")
            event = {
                "summary": title,
                "description": description,
                "start": {"date": start_date},
                "end": {"date": end_date},
            }
        else:
            start_dt = datetime.combine(date, time)
            end_dt = start_dt + timedelta(hours=1)
            event = {
                "summary": title,
                "description": description,
                "start": {
                    "dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "timeZone": self.timezone,
                },
                "end": {
                    "dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "timeZone": self.timezone,
                },
            }

        if self.storage_mode == "google":
            self.service.events().insert(
                calendarId=self.calendar_id, body=event
            ).execute()
            return

        local_event = {"id": uuid.uuid4().hex, **event}
        events = self._read_local_events()
        events.append(local_event)
        self._write_local_events(events)

    def list_events(self, max_results: int = 10) -> list[str]:
        """Liefert eine Liste der nächsten Termine (als formatierte Strings)."""
        if self.storage_mode == "google":
            now = f"{datetime.utcnow().isoformat()}Z"
            results = (
                self.service.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = results.get("items", [])
        else:
            now_date = datetime.utcnow().date().isoformat()
            all_events = self._read_local_events()
            events = [
                event
                for event in all_events
                if event.get("start", {}).get("date", now_date) >= now_date
                or event.get("start", {}).get("dateTime", "")
                >= datetime.utcnow().isoformat()
            ]

            events.sort(
                key=lambda event: event.get("start", {}).get("dateTime")
                or event.get("start", {}).get("date", "9999-12-31")
            )
            events = events[:max_results]

        event_strings: list[str] = []
        for evt in events:
            start = evt.get("start", {})
            summary = evt.get("summary", "")
            if "date" in start:
                date_obj = datetime.fromisoformat(start["date"])
                date_str = date_obj.strftime("%d.%m.%Y")
                event_strings.append(f"{date_str} (ganztägig) – {summary}")
            elif "dateTime" in start:
                dt = start["dateTime"]
                try:
                    dt_obj = datetime.fromisoformat(dt)
                except ValueError:
                    if dt.endswith("Z"):
                        dt_obj = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                    else:
                        dt_obj = datetime.fromisoformat(dt[:19])
                date_str = dt_obj.strftime("%d.%m.%Y %H:%M")
                event_strings.append(f"{date_str} – {summary}")
            else:
                event_strings.append(summary)
        return event_strings
