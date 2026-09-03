"""Markups List: sortable spreadsheet view of every object, backed by
SQLite (Blueprint v2, Section 7.6)."""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

_COLUMNS = ["Type", "Page", "Author", "Created", "Text / Value", "Unit"]


class MarkupsListPanel(QWidget):
    def __init__(self, on_row_activated: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RightPanel")
        self._on_row_activated = on_row_activated

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setSortingEnabled(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self._table)

    def set_rows(self, rows: list[dict]) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [
                row["type"],
                str(row["page_index"] + 1),
                row["author"] or "",
                (row["created_at"] or "")[:19],
                row["text"] or (f"{row['value']:.2f}" if row["value"] is not None else ""),
                row["unit"] or "",
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, row["id"])
                self._table.setItem(r, c, item)
        self._table.setSortingEnabled(True)

    def _on_item_activated(self, item: QTableWidgetItem) -> None:
        obj_id = item.data(Qt.ItemDataRole.UserRole)
        if obj_id:
            self._on_row_activated(obj_id)

    @property
    def row_count(self) -> int:
        return self._table.rowCount()
