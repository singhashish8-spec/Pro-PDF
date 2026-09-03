import pymupdf as fitz
import pytest

from app.core.pdf_document import PDFDocument


@pytest.fixture
def scanned_pdf(tmp_path):
    """A page that's ONLY a raster image of text — no real text objects,
    so get_text() returns nothing and OCR is the only way to read it."""
    text_doc = fitz.open()
    text_page = text_doc.new_page(width=300, height=150)
    text_page.insert_text((20, 80), "Scanned Invoice 42", fontsize=20)
    pix = text_page.get_pixmap(dpi=200)

    scan_doc = fitz.open()
    scan_page = scan_doc.new_page(width=pix.width, height=pix.height)
    scan_page.insert_image(scan_page.rect, pixmap=pix)
    path = str(tmp_path / "scanned.pdf")
    scan_doc.save(path)
    scan_doc.close()
    text_doc.close()
    return path


def test_page_has_no_extractable_text(scanned_pdf):
    doc = PDFDocument()
    doc.open(scanned_pdf)
    assert doc.get_page_text(0).strip() == ""
    doc.close()


def test_ocr_recovers_text_in_memory(scanned_pdf):
    doc = PDFDocument()
    doc.open(scanned_pdf)
    text = doc.get_ocr_text(0)
    assert "Scanned" in text
    assert "Invoice" in text
    doc.close()


def test_ocr_document_produces_searchable_output(scanned_pdf, tmp_path):
    doc = PDFDocument()
    doc.open(scanned_pdf)
    out = str(tmp_path / "searchable.pdf")
    doc.ocr_document(out)
    doc.close()

    check = PDFDocument()
    check.open(out)
    text = check.get_page_text(0)
    assert "Scanned" in text
    assert "Invoice" in text
    hits = check.search_page(0, "Invoice")
    assert len(hits) >= 1
    check.close()


def test_ocr_document_preserves_page_count(scanned_pdf, tmp_path):
    doc = PDFDocument()
    doc.open(scanned_pdf)
    out = str(tmp_path / "searchable.pdf")
    doc.ocr_document(out)
    page_count_before = doc.page_count
    doc.close()

    check = PDFDocument()
    check.open(out)
    assert check.page_count == page_count_before
    check.close()
