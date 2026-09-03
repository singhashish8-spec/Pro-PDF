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

    def search_page(self, page_index: int, query: str) -> list[tuple[float, float, float, float]]:
        """Literal text search on one page; returns match rects in PDF page space."""
        if not query:
            return []
        page = self._require_doc()[page_index]
        return [tuple(r) for r in page.search_for(query)]

    # -- OCR (Blueprint v2, Section 7.6) -------------------------------------
    def get_ocr_text(self, page_index: int, language: str = "eng") -> str:
        """OCRs a page in memory (for searching image-only/scanned pages) without
        modifying the document. Entirely local (bundled Tesseract via MuPDF) —
        no document content is ever sent to a cloud OCR service (Section 3)."""
        page = self._require_doc()[page_index]
        textpage = page.get_textpage_ocr(flags=0, language=language, full=True)
        return page.get_text(textpage=textpage)

    def ocr_document(self, output_path: str, language: str = "eng", dpi: int = 300) -> None:
        """OCRs every page and saves a new, text-searchable PDF (an invisible
        text layer over the original raster content) — makes scanned pages
        findable by Search without altering how the page looks."""
        doc = self._require_doc()
        out_doc = fitz.open()
        try:
            for page in doc:
                pixmap = page.get_pixmap(dpi=dpi)
                ocr_bytes = pixmap.pdfocr_tobytes(language=language)
                with fitz.open("pdf", ocr_bytes) as page_doc:
                    out_doc.insert_pdf(page_doc)
            out_doc.save(output_path)
        finally:
            out_doc.close()

    # -- find & replace (Section 7.6) -----------------------------------------
    def replace_text_on_page(self, page_index: int, old: str, new: str, fontsize: float = 11) -> int:
        """Redacts every occurrence of `old` and inserts `new` in its place.

        Not a content-stream text edit (PDF text isn't reflowable that way
        without a real layout engine — see the blueprint's Open Decisions Log
        on paragraph reflow); this destroys the old glyphs via redaction and
        draws the replacement, which is how most PDF tools implement "replace"
        short of full in-place text editing. Returns the number of replacements.
        """
        page = self._require_doc()[page_index]
        rects = page.search_for(old)
        for rect in rects:
            page.add_redact_annot(rect, fill=(1, 1, 1))
        if rects:
            page.apply_redactions()
            for rect in rects:
                page.insert_text((rect.x0, rect.y1 - 2), new, fontsize=fontsize, color=(0, 0, 0))
        return len(rects)

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
    def export(
        self,
        output_path: str,
        markup_objects: list[MarkupObject],
        user_password: str | None = None,
        owner_password: str | None = None,
        permissions: int | None = None,
    ) -> None:
        """Bakes every markup object into a copy of the currently open document
        and saves it — including any in-place structural edits from this
        session (page insert/delete/rotate/reorder, watermark, Bates,
        header/footer, TOC) that haven't been written to disk yet.

        The document open for editing itself is untouched — the Glass Layer
        stays the working document until this is called.

        Password protection (Section 7.5): pass `user_password` to require a
        password to open the file, and/or `owner_password` + `permissions`
        (an OR of `fitz.PDF_PERM_*` flags) to restrict what an opener can do.
        """
        doc = self._require_doc()
        by_page: dict[int, list[MarkupObject]] = defaultdict(list)
        for obj in markup_objects:
            by_page[obj.page_index].append(obj)

        export_doc = fitz.open(stream=doc.write(), filetype="pdf")
        try:
            for page_index, objects in by_page.items():
                if 0 <= page_index < export_doc.page_count:
                    bake_page(export_doc[page_index], objects)
            if user_password or owner_password:
                export_doc.save(
                    output_path,
                    encryption=fitz.PDF_ENCRYPT_AES_256,
                    user_pw=user_password or "",
                    owner_pw=owner_password or user_password or "",
                    permissions=permissions if permissions is not None else fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY,
                )
            else:
                export_doc.save(output_path)
        finally:
            export_doc.close()

    # -- page management (Blueprint v2, Section 7.4) -------------------------
    def insert_blank_page(self, index: int) -> None:
        doc = self._require_doc()
        width, height = self.page_size(max(0, min(index, doc.page_count - 1))) if doc.page_count else (612, 792)
        doc.new_page(pno=index, width=width, height=height)

    def delete_page(self, index: int) -> None:
        self._require_doc().delete_page(index)

    def rotate_page(self, index: int, degrees: int) -> None:
        page = self._require_doc()[index]
        page.set_rotation((page.rotation + degrees) % 360)

    def move_page(self, from_index: int, to_index: int) -> None:
        """Moves the page at `from_index` so it ends up at `to_index`.

        fitz's own `Document.move_page(pno, to)` takes `to` as "insert before
        this position in the array as it stood *before* the move" (and -1 for
        "append at the end"), which is not the same number as the page's final
        index once `from_index` has been removed. This translates our
        intuitive (from, to) into the argument fitz actually expects.
        """
        doc = self._require_doc()
        page_count = doc.page_count
        if to_index >= page_count - 1:
            fitz_to = -1
        elif to_index <= from_index:
            fitz_to = to_index
        else:
            fitz_to = to_index + 1
        doc.move_page(from_index, fitz_to)

    def extract_pages(self, indices: list[int], output_path: str) -> None:
        doc = self._require_doc()
        new_doc = fitz.open()
        try:
            for i in indices:
                new_doc.insert_pdf(doc, from_page=i, to_page=i)
            new_doc.save(output_path)
        finally:
            new_doc.close()

    # -- bookmarks / table of contents ----------------------------------------
    def get_toc(self) -> list[list]:
        return self._require_doc().get_toc(simple=True)

    def set_toc(self, toc: list[list]) -> None:
        self._require_doc().set_toc(toc)

    # -- watermark / Bates numbering / headers & footers ------------------------
    def add_watermark(self, text: str, opacity: float = 0.3, rotate: int = 0) -> None:
        """`rotate` must be a multiple of 90 — that's the only rotation
        `Page.insert_text` supports; fitz raises ValueError otherwise."""
        doc = self._require_doc()
        rotate = round(rotate / 90) * 90 % 360
        color = (0.5, 0.5, 0.5)
        for page in doc:
            rect = page.rect
            page.insert_text(
                (rect.width / 4, rect.height / 2),
                text,
                fontsize=40,
                color=color,
                rotate=rotate,
                fill_opacity=opacity,
                overlay=True,
            )

    def add_bates_numbers(self, prefix: str = "", start: int = 1, digits: int = 6) -> None:
        doc = self._require_doc()
        for i, page in enumerate(doc):
            number = str(start + i).zfill(digits)
            rect = page.rect
            page.insert_text(
                (rect.width - 150, rect.height - 20),
                f"{prefix}{number}",
                fontsize=9,
                color=(0, 0, 0),
            )

    def add_header_footer(self, header: str = "", footer: str = "") -> None:
        doc = self._require_doc()
        for page in doc:
            rect = page.rect
            if header:
                page.insert_text((rect.width / 2 - 50, 30), header, fontsize=9, color=(0, 0, 0))
            if footer:
                page.insert_text((rect.width / 2 - 50, rect.height - 20), footer, fontsize=9, color=(0, 0, 0))

    # -- security (Section 7.5, used starting Phase 7) ------------------------
    def get_metadata(self) -> dict:
        return dict(self._require_doc().metadata or {})

    def scrub_metadata(self) -> None:
        self._require_doc().set_metadata({})


def merge_pdfs(paths: list[str], output_path: str) -> None:
    merged = fitz.open()
    try:
        for path in paths:
            with fitz.open(path) as doc:
                merged.insert_pdf(doc)
        merged.save(output_path)
    finally:
        merged.close()


def split_pdf(path: str, output_dir: str, pages_per_file: int = 1) -> list[str]:
    import os

    output_paths = []
    with fitz.open(path) as doc:
        base_name = os.path.splitext(os.path.basename(path))[0]
        for start in range(0, doc.page_count, pages_per_file):
            end = min(start + pages_per_file, doc.page_count) - 1
            chunk = fitz.open()
            try:
                chunk.insert_pdf(doc, from_page=start, to_page=end)
                out_path = os.path.join(output_dir, f"{base_name}_p{start + 1}-{end + 1}.pdf")
                chunk.save(out_path)
                output_paths.append(out_path)
            finally:
                chunk.close()
    return output_paths
