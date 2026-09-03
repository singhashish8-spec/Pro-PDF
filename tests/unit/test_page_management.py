import os

import pymupdf as fitz
import pytest

from app.core.pdf_document import PDFDocument, merge_pdfs, split_pdf


def test_insert_blank_page(make_pdf):
    path = make_pdf(page_count=2)
    doc = PDFDocument()
    doc.open(path)
    doc.insert_blank_page(1)
    assert doc.page_count == 3
    doc.close()


def test_delete_page(make_pdf):
    path = make_pdf(page_count=3)
    doc = PDFDocument()
    doc.open(path)
    doc.delete_page(1)
    assert doc.page_count == 2
    doc.close()


def test_rotate_page(make_pdf):
    path = make_pdf(page_count=1)
    doc = PDFDocument()
    doc.open(path)
    doc.rotate_page(0, 90)
    assert doc._doc[0].rotation == 90
    doc.rotate_page(0, 90)
    assert doc._doc[0].rotation == 180
    doc.close()


def test_move_page_reorders(make_pdf, tmp_path):
    # Build a doc with distinguishable page text so we can verify order.
    src = fitz.open()
    for label in ("A", "B", "C"):
        page = src.new_page(width=200, height=200)
        page.insert_text((10, 10), label)
    path = str(tmp_path / "labeled.pdf")
    src.save(path)
    src.close()

    doc = PDFDocument()
    doc.open(path)
    doc.move_page(0, 2)  # A moves to the end: B, C, A
    texts = [doc.get_page_text(i).strip() for i in range(3)]
    assert texts == ["B", "C", "A"]
    doc.close()


def test_extract_pages(make_pdf, tmp_path):
    path = make_pdf(page_count=5)
    doc = PDFDocument()
    doc.open(path)
    out = str(tmp_path / "extracted.pdf")
    doc.extract_pages([0, 2, 4], out)
    doc.close()

    check = PDFDocument()
    check.open(out)
    assert check.page_count == 3
    check.close()


def test_merge_pdfs(make_pdf, tmp_path):
    a = make_pdf(page_count=2, name="a.pdf")
    b = make_pdf(page_count=3, name="b.pdf")
    out = str(tmp_path / "merged.pdf")
    merge_pdfs([a, b], out)

    check = PDFDocument()
    check.open(out)
    assert check.page_count == 5
    check.close()


def test_split_pdf(make_pdf, tmp_path):
    path = make_pdf(page_count=5, name="src.pdf")
    out_dir = str(tmp_path / "split_out")
    os.makedirs(out_dir, exist_ok=True)
    outputs = split_pdf(path, out_dir, pages_per_file=2)
    assert len(outputs) == 3  # 2+2+1
    total_pages = 0
    for out_path in outputs:
        d = PDFDocument()
        d.open(out_path)
        total_pages += d.page_count
        d.close()
    assert total_pages == 5


def test_watermark_bates_header_footer_dont_crash_and_render(make_pdf):
    path = make_pdf(page_count=2)
    doc = PDFDocument()
    doc.open(path)
    doc.add_watermark("CONFIDENTIAL")
    doc.add_bates_numbers("ABC-", start=100, digits=4)
    doc.add_header_footer(header="Project X", footer="Page footer")
    image = doc.render_page(0, zoom=1.0)
    assert image.width() > 0
    doc.close()


def test_toc_get_set_roundtrip(make_pdf):
    path = make_pdf(page_count=3)
    doc = PDFDocument()
    doc.open(path)
    assert doc.get_toc() == []
    doc.set_toc([[1, "Intro", 1], [2, "Details", 2]])
    toc = doc.get_toc()
    assert toc == [[1, "Intro", 1], [2, "Details", 2]]
    doc.close()


def test_metadata_scrub(make_pdf):
    path = make_pdf(page_count=1)
    doc = PDFDocument()
    doc.open(path)
    doc._doc.set_metadata({"title": "Secret Project", "author": "Someone"})
    assert doc.get_metadata()["title"] == "Secret Project"
    doc.scrub_metadata()
    meta = doc.get_metadata()
    assert not meta.get("title")
    assert not meta.get("author")
    doc.close()


def test_export_includes_in_memory_structural_edits(make_pdf, tmp_path):
    """export() must reflect page ops applied this session, not just what's on disk."""
    path = make_pdf(page_count=2)
    doc = PDFDocument()
    doc.open(path)
    doc.delete_page(1)  # not saved to disk yet
    out = str(tmp_path / "out.pdf")
    doc.export(out, [])
    doc.close()

    check = PDFDocument()
    check.open(out)
    assert check.page_count == 1
    check.close()
