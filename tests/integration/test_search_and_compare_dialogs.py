import pymupdf as fitz
import pytest

from app.core.pdf_document import PDFDocument
from app.ui.panels.compare_dialog import CompareDialog
from app.ui.panels.search_dialog import SearchDialog


@pytest.fixture
def pdf_with_text(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=300, height=300)
    page.insert_text((20, 50), "The invoice total is 4200 dollars")
    path = str(tmp_path / "doc.pdf")
    doc.save(path)
    doc.close()
    return path


def test_search_dialog_finds_and_navigates(qapp, pdf_with_text):
    pdf = PDFDocument()
    pdf.open(pdf_with_text)

    navigated = []
    dialog = SearchDialog(pdf, navigated.append)
    dialog._query.setText("invoice")
    dialog._run_search()

    assert dialog._results.count() == 1
    dialog._on_result_activated(dialog._results.item(0))
    assert navigated == [0]
    pdf.close()


def test_search_dialog_replace_all(qapp, pdf_with_text):
    pdf = PDFDocument()
    pdf.open(pdf_with_text)

    dialog = SearchDialog(pdf, lambda i: None)
    dialog._query.setText("invoice")
    dialog._replacement.setText("receipt")
    dialog._run_replace_all()

    assert "receipt" in pdf.get_page_text(0)
    assert "invoice" not in pdf.get_page_text(0)
    pdf.close()


def test_compare_dialog_shows_diff(qapp, pdf_with_text, tmp_path):
    doc_b = fitz.open()
    page = doc_b.new_page(width=300, height=300)
    page.insert_text((20, 50), "Completely different content")
    path_b = str(tmp_path / "b.pdf")
    doc_b.save(path_b)
    doc_b.close()

    pdf_a = PDFDocument()
    pdf_a.open(pdf_with_text)

    dialog = CompareDialog(pdf_a, path_b)
    assert not dialog._image_label.pixmap().isNull()
    assert "% of pixels differ" in dialog._ratio_label.text()

    dialog._pdf_b.close()
    pdf_a.close()
