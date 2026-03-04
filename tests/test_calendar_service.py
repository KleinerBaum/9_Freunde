from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import date, time
from pathlib import Path
import sys
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services import calendar_service  # noqa: E402


class MappingLikeGcpSection(Mapping[str, str]):
    """Mapping-ähnliche Secrets-Sektion ohne dict-Vererbung."""

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = values

    def __getitem__(self, key: str) -> str:
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)


class _FakeEventsResource:
    def __init__(self) -> None:
        self.insert_kwargs: dict[str, Any] | None = None

    def insert(self, **kwargs: Any) -> "_FakeEventsResource":
        self.insert_kwargs = kwargs
        return self

    def execute(self) -> dict[str, str]:
        return {"id": "evt_1"}


class _FakeCalendarClient:
    def __init__(self) -> None:
        self.events_resource = _FakeEventsResource()

    def events(self) -> _FakeEventsResource:
        return self.events_resource


class _GoogleConfig:
    def __init__(self) -> None:
        self.service_account: dict[str, str] = {}


class _AppConfig:
    def __init__(self) -> None:
        self.storage_mode = "google"
        self.google = _GoogleConfig()


def test_get_calendar_id_accepts_mapping_like_gcp_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping_like_gcp = MappingLikeGcpSection({"calendar_id": "  kita@example.com  "})
    monkeypatch.setattr(
        calendar_service.st, "secrets", {"gcp": mapping_like_gcp}, raising=False
    )

    calendar_id = calendar_service._get_calendar_id()

    assert calendar_id == "kita@example.com"


def test_add_event_sends_attendees_and_updates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeCalendarClient()

    monkeypatch.setattr(calendar_service, "get_app_config", lambda: _AppConfig())
    monkeypatch.setattr(calendar_service, "_get_calendar_client", lambda: fake_client)
    monkeypatch.setattr(calendar_service, "_get_calendar_id", lambda: "calendar@test")

    calendar_service.add_event(
        title="Elternabend",
        event_date=date(2026, 1, 14),
        event_time=time(18, 0),
        description="Monatliches Update",
        notification_emails=["Admin@Example.com", "parent@example.com", ""],
    )

    assert fake_client.events_resource.insert_kwargs is not None
    assert fake_client.events_resource.insert_kwargs["calendarId"] == "calendar@test"
    assert fake_client.events_resource.insert_kwargs["sendUpdates"] == "all"
    assert fake_client.events_resource.insert_kwargs["body"]["attendees"] == [
        {"email": "admin@example.com"},
        {"email": "parent@example.com"},
    ]
