from __future__ import annotations

from config import get_app_config
from services.google_clients import get_sheets_client


class SheetsServiceError(RuntimeError):
    """Fehler beim Zugriff auf Google Sheets."""


def read_sheet_values(sheet_id: str, range_a1: str) -> list[list[str]]:
    """Liest Werte aus einem Google Sheet als Matrix von String-Zellen."""
    app_config = get_app_config()
    if app_config.storage_mode != "google" or app_config.google is None:
        raise SheetsServiceError(
            "Google-Sheets-Zugriff ist nur im Google-Modus verfügbar."
        )

    if not sheet_id.strip():
        raise SheetsServiceError("Die Sheet-ID darf nicht leer sein.")

    if not range_a1.strip():
        raise SheetsServiceError("Der A1-Range darf nicht leer sein.")

    service = get_sheets_client()
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=range_a1)
        .execute()
    )

    values = response.get("values", [])
    if not isinstance(values, list):
        return []

    normalized_values: list[list[str]] = []
    for row in values:
        if not isinstance(row, list):
            continue
        normalized_values.append([str(cell) for cell in row])
    return normalized_values
