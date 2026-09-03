from app.core.pdf_document import PDFDocument
from app.models.markup import MarkupObject


def test_open_render_and_page_size(make_pdf):
    path = make_pdf(page_count=3)
    doc = PDFDocument()
    doc.open(path)

    assert doc.page_count == 3
    w, h = doc.page_size(0)
    assert w == 612
    assert h == 792

    image = doc.render_page(0, zoom=1.0)
    assert image.width() > 0
    assert image.height() > 0
    doc.close()


def test_export_bakes_rectangle_and_preserves_page_count(make_pdf, tmp_path):
    path = make_pdf(page_count=2)
    doc = PDFDocument()
    doc.open(path)

    markup = MarkupObject(type="rectangle", page_index=0, points=[(50, 50), (150, 150)])
    output_path = str(tmp_path / "out.pdf")
    doc.export(output_path, [markup])

    exported = PDFDocument()
    exported.open(output_path)
    assert exported.page_count == 2
    exported.close()
    doc.close()


def test_export_over_the_currently_open_path_keeps_the_document_usable(make_pdf):
    """Regression test: saving "Save" (not "Save As") writes to self.path
    while self._doc still has it open. On Windows this requires closing and
    reopening the handle around the write (see export()'s docstring/comments)
    or the OS refuses to let the write replace the file at all."""
    path = make_pdf(page_count=2)
    doc = PDFDocument()
    doc.open(path)

    markup = MarkupObject(type="rectangle", page_index=0, points=[(50, 50), (150, 150)])
    doc.export(path, [markup])  # same path as currently open

    assert doc.is_open
    assert doc.path == path
    assert doc.page_count == 2
    # The live document must still be the unbaked structural state (Section
    # 6.4) — re-exporting again from it must not double-bake or error.
    doc.export(path, [markup])
    assert doc.page_count == 2

    reread = PDFDocument()
    reread.open(path)
    assert reread.page_count == 2
    reread.close()
    doc.close()


def test_export_over_open_path_preserves_structural_edits(make_pdf):
    path = make_pdf(page_count=3)
    doc = PDFDocument()
    doc.open(path)
    doc.delete_page(1)  # structural edit, not yet on disk

    doc.export(path, [])  # Save

    assert doc.page_count == 2  # the live doc still reflects the edit
    reread = PDFDocument()
    reread.open(path)
    assert reread.page_count == 2  # and so does the file on disk
    reread.close()
    doc.close()
