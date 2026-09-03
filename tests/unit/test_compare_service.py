import pymupdf as fitz
import pytest

from app.core.pdf_document import PDFDocument
from app.services.compare import compare_documents, compare_page


def _make(tmp_path, name, text):
    doc = fitz.open()
    page = doc.new_page(width=300, height=300)
    if text:
        page.insert_text((50, 50), text, fontsize=20)
    path = str(tmp_path / name)
    doc.save(path)
    doc.close()
    return path


def test_identical_pages_have_near_zero_diff(tmp_path):
    path_a = _make(tmp_path, "a.pdf", "Revision 1")
    path_b = _make(tmp_path, "b.pdf", "Revision 1")
    doc_a, doc_b = PDFDocument(), PDFDocument()
    doc_a.open(path_a)
    doc_b.open(path_b)

    _, ratio = compare_page(doc_a, doc_b, 0)
    assert ratio < 0.01
    doc_a.close()
    doc_b.close()


def test_changed_pages_have_meaningful_diff(tmp_path):
    path_a = _make(tmp_path, "a.pdf", "Revision 1")
    path_b = _make(tmp_path, "b.pdf", "Revision 2 - totally different content here")
    doc_a, doc_b = PDFDocument(), PDFDocument()
    doc_a.open(path_a)
    doc_b.open(path_b)

    image, ratio = compare_page(doc_a, doc_b, 0)
    assert ratio > 0.001
    assert image.width() > 0 and image.height() > 0
    doc_a.close()
    doc_b.close()


def test_blank_vs_text_page_differs(tmp_path):
    path_a = _make(tmp_path, "a.pdf", "")
    path_b = _make(tmp_path, "b.pdf", "New content added")
    doc_a, doc_b = PDFDocument(), PDFDocument()
    doc_a.open(path_a)
    doc_b.open(path_b)

    _, ratio = compare_page(doc_a, doc_b, 0)
    assert ratio > 0
    doc_a.close()
    doc_b.close()


def test_compare_documents_handles_different_page_counts(tmp_path):
    doc_a_doc = fitz.open()
    doc_a_doc.new_page(width=200, height=200)
    doc_a_doc.new_page(width=200, height=200)
    path_a = str(tmp_path / "a.pdf")
    doc_a_doc.save(path_a)
    doc_a_doc.close()

    path_b = _make(tmp_path, "b.pdf", "Only one page")

    doc_a, doc_b = PDFDocument(), PDFDocument()
    doc_a.open(path_a)
    doc_b.open(path_b)

    ratios = compare_documents(doc_a, doc_b)
    assert len(ratios) == 2
    assert ratios[1] == (1, 1.0)  # page 1 doesn't exist in doc_b
    doc_a.close()
    doc_b.close()


def test_compare_page_different_sizes_does_not_crash(tmp_path):
    doc_a_doc = fitz.open()
    doc_a_doc.new_page(width=200, height=200)
    path_a = str(tmp_path / "a.pdf")
    doc_a_doc.save(path_a)
    doc_a_doc.close()

    doc_b_doc = fitz.open()
    doc_b_doc.new_page(width=400, height=600)
    path_b = str(tmp_path / "b.pdf")
    doc_b_doc.save(path_b)
    doc_b_doc.close()

    doc_a, doc_b = PDFDocument(), PDFDocument()
    doc_a.open(path_a)
    doc_b.open(path_b)
    image, ratio = compare_page(doc_a, doc_b, 0)
    assert image.width() > 0
    doc_a.close()
    doc_b.close()
