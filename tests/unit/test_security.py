import pymupdf as fitz
import pytest

from app.core.pdf_document import PDFDocument


def test_export_with_user_password_requires_it_to_open(make_pdf, tmp_path):
    path = make_pdf(page_count=1)
    doc = PDFDocument()
    doc.open(path)

    out = str(tmp_path / "protected.pdf")
    doc.export(out, [], user_password="secret123")
    doc.close()

    check = fitz.open(out)
    assert check.needs_pass  # fitz returns an int, not a real bool
    assert check.authenticate("wrong") == 0
    assert check.authenticate("secret123") != 0
    check.close()


def test_export_without_password_opens_freely(make_pdf, tmp_path):
    path = make_pdf(page_count=1)
    doc = PDFDocument()
    doc.open(path)

    out = str(tmp_path / "plain.pdf")
    doc.export(out, [])
    doc.close()

    check = fitz.open(out)
    assert not check.needs_pass
    check.close()


def test_reopening_a_password_protected_file_via_pdfdocument(make_pdf, tmp_path):
    path = make_pdf(page_count=1)
    doc = PDFDocument()
    doc.open(path)
    out = str(tmp_path / "protected.pdf")
    doc.export(out, [], user_password="hunter2")
    doc.close()

    reopened = PDFDocument()
    with pytest.raises(ValueError):
        reopened.open(out)  # no password supplied

    reopened.open(out, password="hunter2")
    assert reopened.page_count == 1
    reopened.close()


def test_permissions_restrict_printing(make_pdf, tmp_path):
    path = make_pdf(page_count=1)
    doc = PDFDocument()
    doc.open(path)
    out = str(tmp_path / "restricted.pdf")
    doc.export(out, [], user_password="", owner_password="owner-secret", permissions=fitz.PDF_PERM_COPY)
    doc.close()

    check = fitz.open(out)
    check.authenticate("")
    assert not (check.permissions & fitz.PDF_PERM_PRINT)
    check.close()
