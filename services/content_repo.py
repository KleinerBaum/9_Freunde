from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from googleapiclient.errors import HttpError

from config import get_app_config
from services.google_clients import get_sheets_client

CONTENT_REQUIRED_COLUMNS = [
    "slug",
    "title_de",
    "title_en",
    "body_md_de",
    "body_md_en",
    "audience",
    "published",
    "updated_at",
]


@dataclass(frozen=True)
class ContentPage:
    slug: str
    title_de: str
    title_en: str
    body_md_de: str
    body_md_en: str
    audience: Literal["parent", "admin", "both"]
    published: bool
    updated_at: str


class ContentRepositoryError(RuntimeError):
    """Fehler beim Zugriff auf Content-Seiten."""


class ContentRepository:
    def __init__(self) -> None:
        self._app_config = get_app_config()
        self._storage_mode = self._app_config.storage_mode
        self._sheet_id = (
            self._app_config.google.stammdaten_sheet_id
            if self._app_config.google is not None
            else ""
        )
        self._tab_name = (
            self._app_config.google.content_pages_tab
            if self._app_config.google is not None
            else "content_pages"
        )
        self._local_file = self._app_config.local.content_pages_file
        self._ensure_local_file()

    def _ensure_local_file(self) -> None:
        if self._storage_mode == "google":
            return

        self._local_file.parent.mkdir(parents=True, exist_ok=True)
        if not self._local_file.exists():
            self._local_file.write_text("[]", encoding="utf-8")

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _normalize_slug(slug: str) -> str:
        normalized = str(slug).strip().lower().replace(" ", "_")
        if not normalized:
            raise ContentRepositoryError("Slug darf nicht leer sein.")
        return normalized

    @staticmethod
    def _normalize_audience(audience: str) -> Literal["parent", "admin", "both"]:
        normalized = str(audience).strip().lower()
        if normalized not in {"parent", "admin", "both"}:
            return "both"
        return normalized  # type: ignore[return-value]

    @staticmethod
    def _to_bool(value: Any) -> bool:
        normalized = str(value).strip().lower()
        return normalized in {"1", "true", "yes", "y", "ja"}

    def _normalize_record(self, record: dict[str, Any]) -> ContentPage:
        slug = self._normalize_slug(str(record.get("slug", "")))
        return ContentPage(
            slug=slug,
            title_de=str(record.get("title_de", "")).strip(),
            title_en=str(record.get("title_en", "")).strip(),
            body_md_de=str(record.get("body_md_de", "")).strip(),
            body_md_en=str(record.get("body_md_en", "")).strip(),
            audience=self._normalize_audience(str(record.get("audience", "both"))),
            published=self._to_bool(record.get("published", "false")),
            updated_at=str(record.get("updated_at", "")).strip() or self._now_iso(),
        )

    def _to_dict(self, page: ContentPage) -> dict[str, str]:
        return {
            "slug": page.slug,
            "title_de": page.title_de,
            "title_en": page.title_en,
            "body_md_de": page.body_md_de,
            "body_md_en": page.body_md_en,
            "audience": page.audience,
            "published": "true" if page.published else "false",
            "updated_at": page.updated_at,
        }

    def _read_local(self) -> list[ContentPage]:
        raw_data = json.loads(self._local_file.read_text(encoding="utf-8"))
        if not isinstance(raw_data, list):
            return []

        pages: list[ContentPage] = []
        for item in raw_data:
            if not isinstance(item, dict):
                continue
            try:
                pages.append(self._normalize_record(item))
            except ContentRepositoryError:
                continue

        return pages

    def _write_local(self, pages: list[ContentPage]) -> None:
        raw_pages = [self._to_dict(page) for page in pages]
        self._local_file.write_text(
            json.dumps(raw_pages, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _quote_tab(self) -> str:
        escaped = self._tab_name.replace("'", "''")
        return f"'{escaped}'"

    def _values_get(self, range_name: str) -> list[list[str]]:
        service = get_sheets_client()
        try:
            response = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=self._sheet_id, range=range_name)
                .execute()
            )
        except HttpError as exc:
            raise ContentRepositoryError(
                "Google-Sheets-Abfrage für Inhalte fehlgeschlagen."
            ) from exc
        return response.get("values", [])

    def _values_update(self, range_name: str, values: list[list[str]]) -> None:
        service = get_sheets_client()
        try:
            (
                service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=self._sheet_id,
                    range=range_name,
                    valueInputOption="RAW",
                    body={"values": values},
                )
                .execute()
            )
        except HttpError as exc:
            raise ContentRepositoryError(
                "Google-Sheets-Schreibzugriff für Inhalte fehlgeschlagen."
            ) from exc

    def _values_append(self, range_name: str, values: list[list[str]]) -> None:
        service = get_sheets_client()
        try:
            (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=self._sheet_id,
                    range=range_name,
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"values": values},
                )
                .execute()
            )
        except HttpError as exc:
            raise ContentRepositoryError(
                "Google-Sheets-Anfügen für Inhalte fehlgeschlagen."
            ) from exc

    def _ensure_google_header(self) -> list[str]:
        tab_ref = self._quote_tab()
        rows = self._values_get(f"{tab_ref}!A:ZZ")
        if not rows:
            self._values_update(f"{tab_ref}!A1", [CONTENT_REQUIRED_COLUMNS])
            return [*CONTENT_REQUIRED_COLUMNS]

        header = [str(col).strip() for col in rows[0]]
        changed = False
        for required in CONTENT_REQUIRED_COLUMNS:
            if required not in header:
                header.append(required)
                changed = True

        if changed:
            self._values_update(f"{tab_ref}!A1:ZZ1", [header])

        return header

    def _read_google(self) -> list[ContentPage]:
        header = self._ensure_google_header()
        rows = self._values_get(f"{self._quote_tab()}!A:ZZ")
        if len(rows) <= 1:
            return []

        pages: list[ContentPage] = []
        for row in rows[1:]:
            if not any(str(cell).strip() for cell in row):
                continue
            as_dict: dict[str, str] = {}
            for index, column in enumerate(header):
                as_dict[column] = str(row[index]).strip() if index < len(row) else ""
            try:
                pages.append(self._normalize_record(as_dict))
            except ContentRepositoryError:
                continue

        return pages

    def list_pages(self) -> list[ContentPage]:
        pages = (
            self._read_google()
            if self._storage_mode == "google"
            else self._read_local()
        )
        return sorted(pages, key=lambda page: page.slug)

    def get_page(self, slug: str) -> ContentPage | None:
        normalized_slug = self._normalize_slug(slug)
        for page in self.list_pages():
            if page.slug == normalized_slug:
                return page
        return None

    def upsert_page(self, page_data: dict[str, Any]) -> ContentPage:
        slug = self._normalize_slug(str(page_data.get("slug", "")))
        page = self._normalize_record(
            {
                **page_data,
                "slug": slug,
                "updated_at": self._now_iso(),
            }
        )

        if self._storage_mode == "google":
            header = self._ensure_google_header()
            tab_ref = self._quote_tab()
            rows = self._values_get(f"{tab_ref}!A:ZZ")
            slug_index = header.index("slug")
            row_values = [self._to_dict(page).get(column, "") for column in header]

            for row_offset, row in enumerate(rows[1:], start=2):
                current = str(row[slug_index]).strip() if slug_index < len(row) else ""
                if current.lower() == slug:
                    self._values_update(
                        f"{tab_ref}!A{row_offset}:ZZ{row_offset}", [row_values]
                    )
                    return page

            self._values_append(f"{tab_ref}!A:ZZ", [row_values])
            return page

        pages = self._read_local()
        updated_pages: list[ContentPage] = [
            existing for existing in pages if existing.slug != slug
        ]
        updated_pages.append(page)
        self._write_local(updated_pages)
        return page

    def delete_page(self, slug: str) -> None:
        normalized_slug = self._normalize_slug(slug)
        if self._storage_mode == "google":
            header = self._ensure_google_header()
            rows = self._values_get(f"{self._quote_tab()}!A:ZZ")
            slug_index = header.index("slug")
            remaining_rows = [header]
            for row in rows[1:]:
                current = (
                    str(row[slug_index]).strip().lower()
                    if slug_index < len(row)
                    else ""
                )
                if current != normalized_slug:
                    padded = row + [""] * max(0, len(header) - len(row))
                    remaining_rows.append(padded[: len(header)])
            self._values_update(f"{self._quote_tab()}!A:ZZ", remaining_rows)
            return

        pages = self._read_local()
        filtered = [page for page in pages if page.slug != normalized_slug]
        self._write_local(filtered)
