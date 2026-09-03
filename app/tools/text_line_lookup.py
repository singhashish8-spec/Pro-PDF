"""Finds text lines under a drag rectangle, for text-tied markup tools
(highlighter with baseline snapping, underline/strikeout/squiggly — Section 7.1)."""

from __future__ import annotations

from app.core.pdf_document import PDFDocument
from app.tools.geometry import rect_intersection


def lines_in_drag_rect(
    pdf: PDFDocument, page_index: int, rect: tuple[float, float, float, float]
) -> list[tuple[float, float, float, float]]:
    """Returns text-line bboxes clipped to the drag rect's x-range, in drag order."""
    lines = pdf.get_text_lines(page_index)
    hits = []
    for line in lines:
        overlap = rect_intersection(line, rect)
        if overlap is not None:
            x0, _, x1, _ = overlap
            hits.append((x0, line[1], x1, line[3]))
    hits.sort(key=lambda b: b[1])
    return hits
