import pymupdf as fitz
import pytest

from app.commands.base import CommandStack
from app.core.pdf_document import PDFDocument
from app.models.markup import Style
from app.models.project import MarkupDocument
from app.tools.base import ToolContext
from app.tools.signature_tool import SignatureTool


@pytest.fixture
def context(make_pdf):
    path = make_pdf(page_count=1)
    pdf = PDFDocument()
    pdf.open(path)
    document = MarkupDocument()
    texts = iter(["Jane Doe"])
    ctx = ToolContext(
        document=document,
        command_stack=CommandStack(),
        page_index=0,
        default_style=Style(),
        pdf=pdf,
        text_provider=lambda title: next(texts, None),
        preview_callback=lambda obj: None,
    )
    return ctx, pdf


def test_click_produces_typed_signature(context):
    ctx, pdf = context
    tool = SignatureTool(ctx)
    tool.on_press((100, 100))
    tool.on_release((100, 100))  # no movement -> click -> typed
    obj = ctx.document.all_objects()[0]
    assert obj.type == "signature"
    assert obj.text == "Jane Doe"
    assert len(obj.points) == 1
    pdf.close()


def test_drag_produces_drawn_signature(context):
    ctx, pdf = context
    tool = SignatureTool(ctx)
    tool.on_press((100, 100))
    tool.on_move((110, 110))
    tool.on_move((120, 95))
    tool.on_release((130, 105))
    obj = ctx.document.all_objects()[0]
    assert obj.type == "signature"
    assert obj.text == ""
    assert len(obj.points) >= 3
    pdf.close()


def test_typed_signature_bakes_as_italic_text(context, tmp_path):
    ctx, pdf = context
    tool = SignatureTool(ctx)
    tool.on_press((100, 100))
    tool.on_release((100, 100))

    out = str(tmp_path / "signed.pdf")
    pdf.export(out, ctx.document.all_objects())

    check = fitz.open(out)
    assert "Jane Doe" in check[0].get_text()
    check.close()


def test_drawn_signature_bakes_as_stroke(context, tmp_path):
    ctx, pdf = context
    tool = SignatureTool(ctx)
    tool.on_press((50, 50))
    tool.on_move((60, 40))
    tool.on_release((70, 55))

    out = str(tmp_path / "signed.pdf")
    pdf.export(out, ctx.document.all_objects())

    check = fitz.open(out)
    pix = check[0].get_pixmap()

    def px(x, y):
        off = (y * pix.width + x) * pix.n
        return tuple(pix.samples[off : off + 3])

    check.close()
    # Some pixel along the drawn path should no longer be pure white.
    assert any(px(x, y) != (255, 255, 255) for x in range(45, 75) for y in range(35, 60))
