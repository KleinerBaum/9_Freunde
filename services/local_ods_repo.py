from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from odf.opendocument import OpenDocumentSpreadsheet, load
from odf.table import Table, TableCell, TableRow
from odf.text import P

from services.sheets_repo import (
    CHILDREN_REQUIRED_COLUMNS,
    MEDICATIONS_REQUIRED_COLUMNS,
    PARENTS_REQUIRED_COLUMNS,
    PHOTO_META_REQUIRED_COLUMNS,
    PICKUP_AUTHORIZATIONS_REQUIRED_COLUMNS,
)


CONSENTS_REQUIRED_COLUMNS = ["consent_id", "child_id", "consent_type", "status"]

REQUIRED_COLUMNS_BY_SHEET: dict[str, list[str]] = {
    "children": CHILDREN_REQUIRED_COLUMNS,
    "parents": PARENTS_REQUIRED_COLUMNS,
    "consents": CONSENTS_REQUIRED_COLUMNS,
    "pickup_authorizations": PICKUP_AUTHORIZATIONS_REQUIRED_COLUMNS,
    "medications": MEDICATIONS_REQUIRED_COLUMNS,
    "photo_meta": PHOTO_META_REQUIRED_COLUMNS,
}


class LocalODSRepository:
    """Liest und schreibt lokale Stammdaten in einer ODS-Datei."""

    def __init__(self, stammdaten_file: Path) -> None:
        self.stammdaten_file = stammdaten_file

    def ensure_workbook(self) -> None:
        if self.stammdaten_file.exists():
            existing_sheets = self._list_sheet_names()
            missing_sheets = [
                sheet_name
                for sheet_name in REQUIRED_COLUMNS_BY_SHEET
                if sheet_name not in existing_sheets
            ]
            missing_columns = any(
                self._sheet_has_missing_columns(sheet_name, required_columns)
                for sheet_name, required_columns in REQUIRED_COLUMNS_BY_SHEET.items()
                if sheet_name in existing_sheets
            )
            if not missing_sheets and not missing_columns:
                return

            sheet_records = {
                sheet_name: self.read_sheet(sheet_name)
                for sheet_name in REQUIRED_COLUMNS_BY_SHEET
            }
            self._write_all_sheets(sheet_records)
            return

        self.stammdaten_file.parent.mkdir(parents=True, exist_ok=True)
        self._write_all_sheets(
            {sheet_name: [] for sheet_name in REQUIRED_COLUMNS_BY_SHEET}
        )

    def read_sheet(self, sheet_name: str) -> list[dict[str, str]]:
        required_columns = REQUIRED_COLUMNS_BY_SHEET[sheet_name]

        if not self.stammdaten_file.exists():
            return []

        try:
            dataframe = pd.read_excel(
                self.stammdaten_file,
                sheet_name=sheet_name,
                engine="odf",
                dtype=str,
            )
        except ValueError:
            return []

        if dataframe.empty and len(dataframe.columns) == 0:
            return []

        dataframe = dataframe.fillna("")
        missing_columns = [
            column for column in required_columns if column not in dataframe.columns
        ]
        for column in missing_columns:
            dataframe[column] = ""

        ordered_columns = required_columns + [
            column for column in dataframe.columns if column not in required_columns
        ]
        records = dataframe[ordered_columns].to_dict(orient="records")
        return [
            {key: str(value) for key, value in record.items()} for record in records
        ]

    def write_sheet(self, sheet_name: str, records: list[dict[str, Any]]) -> None:
        all_records = {
            existing_sheet: self.read_sheet(existing_sheet)
            for existing_sheet in REQUIRED_COLUMNS_BY_SHEET
        }
        all_records[sheet_name] = [
            {key: "" if value is None else str(value) for key, value in record.items()}
            for record in records
        ]
        self._write_all_sheets(all_records)

    def _sheet_has_missing_columns(
        self,
        sheet_name: str,
        required_columns: list[str],
    ) -> bool:
        try:
            dataframe = pd.read_excel(
                self.stammdaten_file,
                sheet_name=sheet_name,
                engine="odf",
                dtype=str,
            )
        except ValueError:
            return True

        return any(column not in dataframe.columns for column in required_columns)

    def _list_sheet_names(self) -> list[str]:
        document = load(str(self.stammdaten_file))
        return [
            str(table.getAttribute("name"))
            for table in document.spreadsheet.getElementsByType(Table)
        ]

    def _write_all_sheets(
        self, records_by_sheet: dict[str, list[dict[str, Any]]]
    ) -> None:
        document = OpenDocumentSpreadsheet()
        for sheet_name, required_columns in REQUIRED_COLUMNS_BY_SHEET.items():
            sheet_records = records_by_sheet.get(sheet_name, [])
            headers = self._build_headers(required_columns, sheet_records)

            table = Table(name=sheet_name)
            table.addElement(self._build_row(headers))
            for record in sheet_records:
                row_values = [
                    "" if record.get(column) is None else str(record.get(column, ""))
                    for column in headers
                ]
                table.addElement(self._build_row(row_values))

            document.spreadsheet.addElement(table)

        document.save(str(self.stammdaten_file))

    @staticmethod
    def _build_headers(
        required_columns: list[str],
        records: list[dict[str, Any]],
    ) -> list[str]:
        dynamic_columns: list[str] = []
        for record in records:
            for key in record:
                if key not in required_columns and key not in dynamic_columns:
                    dynamic_columns.append(key)
        return [*required_columns, *dynamic_columns]

    @staticmethod
    def _build_row(values: list[str]) -> TableRow:
        row = TableRow()
        for value in values:
            cell = TableCell(valuetype="string")
            cell.addElement(P(text=str(value)))
            row.addElement(cell)
        return row
