"""The PDF engine wrapper. Every direct call to `fitz` (PyMuPDF) in the
whole app lives in this module and its siblings under app/core/
(Blueprint v2, Section 5 rule; ADR 0005 for why this boundary matters)."""

from __future__ import annotations

from collections import defaultdict

import pymupdf as fitz
from PyQt6.QtGui import QImage

from app.core.markup_baker import bake_page
from app.models.markup import MarkupObject

#: Screen pixels per PDF point at zoom=1.0 (matches a 96 DPI PDF point).
BASE_DPI_SCALE = 96 / 72


class PDFDocument:
    def __init__(self) -> None:
        self._doc: fitz.Document | None = None
        self.path: str | None = None

    # -- lifecycle -------------------------------------------------------
    def open(self, path: str, password: str | None = None) -> None:
        doc = fitz.open(path)
        if doc.needs_pass:
            if not password or not doc.authenticate(password):
                doc.close()
                raise ValueError("This PDF is password protected and the password was incorrect or missing.")
        self._doc = doc
        self.path = path

    def close(self) -> None:
        if self._doc is not None:
            self._doc.close()
            self._doc = None
            self.path = None

    @property
    def is_open(self) -> bool:
        return self._doc is not None

    def _require_doc(self) -> fitz.Document:
        if self._doc is None:
            raise RuntimeError("No PDF is currently open.")
        return self._doc

    # -- page metadata -----------------------------------------------------
    @property
    def page_count(self) -> int:
        return self._require_doc().page_count

    def page_size(self, page_index: int) -> tuple[float, float]:
        page = self._require_doc()[page_index]
        rect = page.rect
        return (rect.width, rect.height)

    def get_page_text(self, page_index: int) -> str:
        return self._require_doc()[page_index].get_text()

    def get_text_lines(self, page_index: int) -> list[tuple[float, float, float, float]]:
        """Line-level bounding boxes in PDF page space, for text-baseline
        snapping (highlighter) and text-tied markup (underline/strikeout/squiggly)."""
        page = self._require_doc()[page_index]
        lines: list[tuple[float, float, float, float]] = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                lines.append(tuple(line["bbox"]))
        return lines

    # -- rendering -----------------------------------------------------------
    def render_page(self, page_index: int, zoom: float) -> QImage:
        """Render a page to a raster QImage; this is the Glass Layer's background."""
        page = self._require_doc()[page_index]
        matrix = fitz.Matrix(zoom * BASE_DPI_SCALE, zoom * BASE_DPI_SCALE)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        fmt = QImage.Format.Format_RGB888
        image = QImage(pixmap.samples, pixmap.width, pixmap.height, pixmap.stride, fmt)
        return image.copy()

    def scene_size(self, page_index: int, zoom: float) -> tuple[float, float]:
        w, h = self.page_size(page_index)
        scale = zoom * BASE_DPI_SCALE
        return (w * scale, h * scale)

    # -- save/export pipeline (Section 6.4) ---------------------------------
    def export(self, output_path: str, markup_objects: list[MarkupObject]) -> None:
        """Bakes every markup object into a fresh copy of the PDF and saves it.

        The document currently open for editing is untouched — the Glass
        Layer stays the working document until this is called.
        """
        if self.path is None:
            raise RuntimeError("No PDF is currently open.")
        by_page: dict[int, list[MarkupObject]] = defaultdict(list)
        for obj in markup_objects:
            by_page[obj.page_index].append(obj)

        export_doc = fitz.open(self.path)
        try:
            for page_index, objects in by_page.items():
                if 0 <= page_index < export_doc.page_count:
                    bake_page(export_doc[page_index], objects)
            export_doc.save(output_path)
        finally:
            export_doc.close()
