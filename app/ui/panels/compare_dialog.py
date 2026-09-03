"""Document Compare: visual diff between two PDF versions (Blueprint v2,
Section 7.6)."""

from __future__ import annotations

from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout

from app.core.pdf_document import PDFDocument
from app.services.compare import compare_page


class CompareDialog(QDialog):
    def __init__(self, pdf_a: PDFDocument, pdf_b_path: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Compare Documents")
        self.resize(800, 700)
        self._pdf_a = pdf_a
        self._pdf_b = PDFDocument()
        self._pdf_b.open(pdf_b_path)
        self._page_index = 0

        layout = QVBoxLayout(self)

        nav = QHBoxLayout()
        prev_btn = QPushButton("‹ Prev")
        prev_btn.clicked.connect(lambda: self._go_to(self._page_index - 1))
        nav.addWidget(prev_btn)
        self._page_label = QLabel("")
        nav.addWidget(self._page_label)
        next_btn = QPushButton("Next ›")
        next_btn.clicked.connect(lambda: self._go_to(self._page_index + 1))
        nav.addWidget(next_btn)
        nav.addStretch(1)
        self._ratio_label = QLabel("")
        nav.addWidget(self._ratio_label)
        layout.addLayout(nav)

        self._image_label = QLabel()
        scroll = QScrollArea()
        scroll.setWidget(self._image_label)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, 1)

        self._page_count = max(pdf_a.page_count, self._pdf_b.page_count)
        self._go_to(0)

    def _go_to(self, index: int) -> None:
        if not (0 <= index < self._page_count):
            return
        self._page_index = index
        self._page_label.setText(f"Page {index + 1} / {self._page_count}")
        try:
            image, ratio = compare_page(self._pdf_a, self._pdf_b, index)
            self._image_label.setPixmap(QPixmap.fromImage(image))
            self._ratio_label.setText(f"{ratio * 100:.1f}% of pixels differ")
        except IndexError:
            self._image_label.setText("This page doesn't exist in one of the documents.")
            self._ratio_label.setText("")

    def closeEvent(self, event) -> None:
        self._pdf_b.close()
        super().closeEvent(event)
