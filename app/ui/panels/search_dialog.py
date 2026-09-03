"""Search within document + find & replace (Blueprint v2, Section 7.6)."""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from app.core.pdf_document import PDFDocument
from app.services.search import find_and_replace_document, search_document


class SearchDialog(QDialog):
    def __init__(self, pdf: PDFDocument, on_navigate: Callable[[int], None], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Search")
        self.resize(420, 420)
        self._pdf = pdf
        self._on_navigate = on_navigate
        self._hits: list[tuple[int, tuple]] = []

        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        self._query = QLineEdit()
        self._query.setPlaceholderText("Search text or regex…")
        self._query.returnPressed.connect(self._run_search)
        search_row.addWidget(self._query, 1)
        self._regex_check = QCheckBox("Regex")
        search_row.addWidget(self._regex_check)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._run_search)
        search_row.addWidget(search_btn)
        layout.addLayout(search_row)

        self._results_label = QLabel("")
        layout.addWidget(self._results_label)

        self._results = QListWidget()
        self._results.itemActivated.connect(self._on_result_activated)
        layout.addWidget(self._results, 1)

        layout.addWidget(QLabel("Replace with:"))
        replace_row = QHBoxLayout()
        self._replacement = QLineEdit()
        replace_row.addWidget(self._replacement, 1)
        replace_btn = QPushButton("Replace All")
        replace_btn.clicked.connect(self._run_replace_all)
        replace_row.addWidget(replace_btn)
        layout.addLayout(replace_row)

    def _run_search(self) -> None:
        query = self._query.text()
        if not query:
            return
        self._hits = search_document(self._pdf, query, use_regex=self._regex_check.isChecked())
        self._results.clear()
        for page_index, rect in self._hits:
            item = QListWidgetItem(f"Page {page_index + 1} — {rect}")
            item.setData(Qt.ItemDataRole.UserRole, page_index)
            self._results.addItem(item)
        self._results_label.setText(f"{len(self._hits)} match(es)")

    def _on_result_activated(self, item: QListWidgetItem) -> None:
        page_index = item.data(Qt.ItemDataRole.UserRole)
        self._on_navigate(page_index)

    def _run_replace_all(self) -> None:
        query = self._query.text()
        replacement = self._replacement.text()
        if not query:
            return
        count = find_and_replace_document(self._pdf, query, replacement)
        self._results_label.setText(f'Replaced {count} occurrence(s) of "{query}".')
        self._run_search()
