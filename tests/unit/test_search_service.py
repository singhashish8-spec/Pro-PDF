import pymupdf as fitz
import pytest

from app.commands.base import CommandStack
from app.core.pdf_document import PDFDocument
from app.models.project import MarkupDocument
from app.services.search import find_and_replace_document, search_and_redact, search_document


@pytest.fixture
def multi_page_pdf(tmp_path):
    doc = fitz.open()
    page0 = doc.new_page(width=400, height=200)
    page0.insert_text((20, 50), "Contact SSN 123-45-6789 for account A")
    page1 = doc.new_page(width=400, height=200)
    page1.insert_text((20, 50), "Second SSN 987-65-4321 belongs to account B")
    page1.insert_text((20, 100), "No sensitive data on this second line")
    path = str(tmp_path / "multi.pdf")
    doc.save(path)
    doc.close()
    return path


def test_search_document_literal(multi_page_pdf):
    doc = PDFDocument()
    doc.open(multi_page_pdf)
    hits = search_document(doc, "SSN")
    assert len(hits) == 2
    assert {h[0] for h in hits} == {0, 1}
    doc.close()


def test_search_document_regex(multi_page_pdf):
    doc = PDFDocument()
    doc.open(multi_page_pdf)
    hits = search_document(doc, r"\d{3}-\d{2}-\d{4}", use_regex=True)
    assert len(hits) == 2
    doc.close()


def test_search_document_no_matches(multi_page_pdf):
    doc = PDFDocument()
    doc.open(multi_page_pdf)
    hits = search_document(doc, "nonexistent-string")
    assert hits == []
    doc.close()


def test_find_and_replace_across_document(multi_page_pdf, tmp_path):
    doc = PDFDocument()
    doc.open(multi_page_pdf)
    count = find_and_replace_document(doc, "account", "acct")
    assert count == 2

    out = str(tmp_path / "replaced.pdf")
    doc.export(out, [])
    doc.close()

    check = fitz.open(out)
    full_text = check[0].get_text() + check[1].get_text()
    assert "account" not in full_text
    assert "acct" in full_text
    check.close()


def test_search_and_redact_ssn_pattern(multi_page_pdf, tmp_path):
    doc = PDFDocument()
    doc.open(multi_page_pdf)
    markup_document = MarkupDocument()
    stack = CommandStack()

    count = search_and_redact(doc, markup_document, stack, r"\d{3}-\d{2}-\d{4}", use_regex=True)
    assert count == 2
    assert stack.can_undo  # one composite undo step
    assert len(markup_document.all_objects()) == 2
    assert all(o.type == "redaction" for o in markup_document.all_objects())

    out = str(tmp_path / "redacted.pdf")
    doc.export(out, markup_document.all_objects())
    doc.close()

    check = fitz.open(out)
    full_text = check[0].get_text() + check[1].get_text()
    assert "123-45-6789" not in full_text
    assert "987-65-4321" not in full_text
    assert "No sensitive data on this second line" in full_text
    check.close()


def test_search_and_redact_is_one_undo_step(multi_page_pdf):
    doc = PDFDocument()
    doc.open(multi_page_pdf)
    markup_document = MarkupDocument()
    stack = CommandStack()

    search_and_redact(doc, markup_document, stack, r"\d{3}-\d{2}-\d{4}", use_regex=True)
    assert len(markup_document.all_objects()) == 2

    stack.undo()
    assert markup_document.all_objects() == []
    doc.close()


def test_search_and_redact_no_matches_pushes_nothing(multi_page_pdf):
    doc = PDFDocument()
    doc.open(multi_page_pdf)
    markup_document = MarkupDocument()
    stack = CommandStack()

    count = search_and_redact(doc, markup_document, stack, "nonexistent-pattern", use_regex=False)
    assert count == 0
    assert not stack.can_undo
    doc.close()
