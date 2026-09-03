"""Bookmarks / table-of-contents editor (Blueprint v2, Section 7.4).

A plain-text editor: one bookmark per line as "<indent-level tabs><title>\t<page>".
Simple, but a real, working editor for fitz's [[level, title, page], ...] TOC format.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QVBoxLayout


class TocEditorDialog(QDialog):
    def __init__(self, toc: list[list], page_count: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Bookmarks (Table of Contents)")
        self.resize(480, 420)
        self._page_count = page_count

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "One bookmark per line: tab-indent for nesting level, then "
                "\"Title<TAB>PageNumber\". Example:\n"
                "Chapter 1\\t1\\n\\tSection 1.1\\t2"
            )
        )
        self._editor = QPlainTextEdit()
        self._editor.setPlainText(self._toc_to_text(toc))
        layout.addWidget(self._editor, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _toc_to_text(toc: list[list]) -> str:
        lines = []
        for entry in toc:
            level, title, page = entry[0], entry[1], entry[2]
            indent = "\t" * max(level - 1, 0)
            lines.append(f"{indent}{title}\t{page}")
        return "\n".join(lines)

    def result_toc(self) -> list[list]:
        toc = []
        for raw_line in self._editor.toPlainText().splitlines():
            if not raw_line.strip():
                continue
            indent = len(raw_line) - len(raw_line.lstrip("\t"))
            rest = raw_line.strip()
            if "\t" in rest:
                title, page_str = rest.rsplit("\t", 1)
            else:
                parts = rest.rsplit(" ", 1)
                title, page_str = (parts[0], parts[1]) if len(parts) == 2 else (rest, "1")
            try:
                page = max(1, min(int(page_str.strip()), self._page_count))
            except ValueError:
                page = 1
            toc.append([indent + 1, title.strip(), page])
        return toc
