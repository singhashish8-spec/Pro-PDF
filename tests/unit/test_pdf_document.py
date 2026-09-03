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
