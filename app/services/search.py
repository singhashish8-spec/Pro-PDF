"""Document-wide search, find & replace, and search-and-redact
(Blueprint v2, Section 7.6 / 7.5). Orchestrates PDFDocument methods only —
no direct fitz calls here, keeping the fitz-only-in-app/core rule intact.
"""

from __future__ import annotations

import re

from app.commands.base import CommandStack
from app.commands.object_commands import AddObjectCommand, CompositeCommand
from app.core.pdf_document import PDFDocument
from app.models.markup import MarkupObject
from app.models.project import MarkupDocument

SearchHit = tuple[int, tuple[float, float, float, float]]  # (page_index, rect)


def _matches_for_page(pdf: PDFDocument, page_index: int, query: str, use_regex: bool) -> set[str]:
    if not query:
        return set()
    if not use_regex:
        return {query}
    text = pdf.get_page_text(page_index)
    return {m.group(0) for m in re.finditer(query, text) if m.group(0)}


def search_document(
    pdf: PDFDocument, query: str, use_regex: bool = False, page_range: range | None = None
) -> list[SearchHit]:
    """Finds every occurrence of `query` (literal or regex) across the document."""
    pages = page_range if page_range is not None else range(pdf.page_count)
    hits: list[SearchHit] = []
    for page_index in pages:
        for substring in _matches_for_page(pdf, page_index, query, use_regex):
            for rect in pdf.search_page(page_index, substring):
                hits.append((page_index, rect))
    return hits


def find_and_replace_document(pdf: PDFDocument, old: str, new: str, fontsize: float = 11) -> int:
    """Replaces every occurrence of `old` with `new`, page by page. Returns the count replaced."""
    total = 0
    for page_index in range(pdf.page_count):
        total += pdf.replace_text_on_page(page_index, old, new, fontsize=fontsize)
    return total


def search_and_redact(
    pdf: PDFDocument,
    markup_document: MarkupDocument,
    command_stack: CommandStack,
    pattern: str,
    use_regex: bool = True,
    author: str = "user",
) -> int:
    """Stages a redaction MarkupObject over every match (e.g. every SSN pattern
    in the document — Section 7.5). Nothing is destroyed until Save/Export
    bakes these redactions, same as a manually drawn one. One undo step."""
    from app.tools.redaction_tool import REDACTION_STYLE

    commands = []
    for page_index, rect in search_document(pdf, pattern, use_regex=use_regex):
        x0, y0, x1, y1 = rect
        obj = MarkupObject(
            type="redaction",
            page_index=page_index,
            points=[(x0, y0), (x1, y1)],
            style=REDACTION_STYLE.__class__(**REDACTION_STYLE.to_dict()),
            author=author,
        )
        commands.append(AddObjectCommand(markup_document, obj))
    if commands:
        command_stack.push(CompositeCommand(commands, label="Search & Redact"))
    return len(commands)
