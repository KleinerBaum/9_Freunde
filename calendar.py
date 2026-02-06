from __future__ import annotations

from datetime import datetime, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import get_app_config


class CalendarAgent:
    def __init__(self) -> None:
        app_config = get_app_config()
        scopes = ["https://www.googleapis.com/auth/calendar"]
        credentials = service_account.Credentials.from_service_account_info(
            app_config.google.service_account,
            scopes=scopes,
        )
        self.service = build("calendar", "v3", credentials=credentials)
        self.calendar_id = app_config.google.calendar_id
        self.timezone = "Europe/Berlin"

    def add_event(
        self, title: str, date, time=None, description: str = "", all_day: bool = False
    ) -> None:
        """Fügt einen neuen Termin im Google Kalender ein."""
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
        self.service.events().insert(calendarId=self.calendar_id, body=event).execute()

    def list_events(self, max_results: int = 10) -> list[str]:
        """Liefert eine Liste der nächsten Termine (als formatierte Strings)."""
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
