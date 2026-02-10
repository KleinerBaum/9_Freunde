from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path
import sys

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


def test_get_calendar_id_accepts_mapping_like_gcp_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping_like_gcp = MappingLikeGcpSection({"calendar_id": "  kita@example.com  "})
    monkeypatch.setattr(
        calendar_service.st, "secrets", {"gcp": mapping_like_gcp}, raising=False
    )

    calendar_id = calendar_service._get_calendar_id()

    assert calendar_id == "kita@example.com"
