"""Redaction verification (Blueprint v2, Section 11.3 — NON-NEGOTIABLE).

An automated test that redacts text in a fixture PDF, saves it, then
attempts to extract text and images from the redacted region
programmatically, and asserts nothing is recoverable. Must pass before
redaction is considered done, not just visually reviewed.
"""

from __future__ import annotations

import pymupdf as fitz
import pytest

from app.core.pdf_document import PDFDocument
from app.models.markup import MarkupObject
from app.tools.redaction_tool import RedactionTool


@pytest.fixture
def secret_pdf(tmp_path):
    """A page with a known secret string at a known location, plus an image."""
    doc = fitz.open()
    page = doc.new_page(width=400, height=400)
    page.insert_text((50, 50), "SECRET: 123-45-6789")
    page.insert_text((50, 300), "This text is NOT redacted and must survive.")

    # An image inside the redaction zone too — redaction must destroy images, not just text.
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 10, 10))
    pix.set_rect(pix.irect, (255, 0, 0))
    page.insert_image(fitz.Rect(60, 20, 160, 70), pixmap=pix)

    path = str(tmp_path / "secret.pdf")
    doc.save(path)
    doc.close()
    return path


def _redaction_bbox_for_text() -> tuple:
    # Generously covers the "SECRET: 123-45-6789" text and the embedded image.
    return (40, 10, 250, 80)


def test_redacted_text_is_not_extractable(secret_pdf, tmp_path):
    doc = PDFDocument()
    doc.open(secret_pdf)

    x0, y0, x1, y1 = _redaction_bbox_for_text()
    redaction = MarkupObject(type="redaction", page_index=0, points=[(x0, y0), (x1, y1)])

    output_path = str(tmp_path / "redacted.pdf")
    doc.export(output_path, [redaction])
    doc.close()

    check = fitz.open(output_path)
    page_text = check[0].get_text()
    check.close()

    assert "SECRET" not in page_text
    assert "123-45-6789" not in page_text
    assert "This text is NOT redacted and must survive." in page_text


def test_redacted_region_search_finds_nothing(secret_pdf, tmp_path):
    """search_for must not locate the redacted string anywhere in the output."""
    doc = PDFDocument()
    doc.open(secret_pdf)

    x0, y0, x1, y1 = _redaction_bbox_for_text()
    redaction = MarkupObject(type="redaction", page_index=0, points=[(x0, y0), (x1, y1)])

    output_path = str(tmp_path / "redacted.pdf")
    doc.export(output_path, [redaction])
    doc.close()

    check = fitz.open(output_path)
    hits = check[0].search_for("123-45-6789")
    check.close()
    assert hits == []


def test_redacted_image_is_removed(secret_pdf, tmp_path):
    doc = PDFDocument()
    doc.open(secret_pdf)

    original = fitz.open(secret_pdf)
    images_before = original[0].get_images()
    original.close()
    assert len(images_before) == 1  # sanity: the fixture really has an image there

    x0, y0, x1, y1 = _redaction_bbox_for_text()
    redaction = MarkupObject(type="redaction", page_index=0, points=[(x0, y0), (x1, y1)])
    output_path = str(tmp_path / "redacted.pdf")
    doc.export(output_path, [redaction])
    doc.close()

    check = fitz.open(output_path)
    images_after = check[0].get_images()
    check.close()
    assert images_after == []


def test_redaction_box_is_visually_opaque_over_the_area(secret_pdf, tmp_path):
    """Belt-and-suspenders: the redacted area must also be visually covered,
    not just textually empty (in case of e.g. non-text content missed by
    extraction), matching how redaction tools are expected to behave."""
    doc = PDFDocument()
    doc.open(secret_pdf)

    x0, y0, x1, y1 = _redaction_bbox_for_text()
    redaction = MarkupObject(type="redaction", page_index=0, points=[(x0, y0), (x1, y1)])
    output_path = str(tmp_path / "redacted.pdf")
    doc.export(output_path, [redaction])
    doc.close()

    check = fitz.open(output_path)
    pix = check[0].get_pixmap()

    def px(x, y):
        off = (y * pix.width + x) * pix.n
        return tuple(pix.samples[off : off + 3])

    # Sample near the center of the redacted rect: should be black (the fill).
    cx, cy = int((x0 + x1) / 2), int((y0 + y1) / 2)
    check.close()
    assert px(cx, cy) == (0, 0, 0)


def test_unredacted_areas_are_untouched(secret_pdf, tmp_path):
    doc = PDFDocument()
    doc.open(secret_pdf)

    x0, y0, x1, y1 = _redaction_bbox_for_text()
    redaction = MarkupObject(type="redaction", page_index=0, points=[(x0, y0), (x1, y1)])
    output_path = str(tmp_path / "redacted.pdf")
    doc.export(output_path, [redaction])
    doc.close()

    check = fitz.open(output_path)
    hits = check[0].search_for("This text is NOT redacted and must survive.")
    check.close()
    assert len(hits) == 1


def test_redaction_tool_produces_opaque_black_style_by_default(secret_pdf):
    doc = PDFDocument()
    doc.open(secret_pdf)

    from app.commands.base import CommandStack
    from app.models.markup import Style
    from app.models.project import MarkupDocument
    from app.tools.base import ToolContext

    document = MarkupDocument()
    context = ToolContext(
        document=document,
        command_stack=CommandStack(),
        page_index=0,
        default_style=Style(stroke_color="#FF0000"),  # tool must NOT use the ambient default style
        pdf=doc,
        text_provider=lambda title: None,
        preview_callback=lambda obj: None,
    )
    tool = RedactionTool(context)
    tool.on_press((0, 0))
    tool.on_release((50, 50))

    obj = document.all_objects()[0]
    assert obj.style.fill_color == "#000000"
    assert obj.style.stroke_color == "#000000"
    assert obj.style.opacity == 1.0
    doc.close()
