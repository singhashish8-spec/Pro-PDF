import pymupdf as fitz
import pytest

from app.commands.base import CommandStack
from app.core.pdf_document import PDFDocument
from app.models.markup import Style
from app.models.project import MarkupDocument
from app.tools.base import ToolContext
from app.tools.checkbox import CheckboxTool
from app.tools.date_field import DateFieldTool
from app.tools.dropdown import DropdownTool
from app.tools.radio_button import RadioButtonTool
from app.tools.signature_field import SignatureFieldTool
from app.tools.text_field import TextFieldTool


@pytest.fixture
def context(make_pdf):
    path = make_pdf(page_count=1)
    pdf = PDFDocument()
    pdf.open(path)
    document = MarkupDocument()
    stack = CommandStack()
    return document, stack, pdf


def _context(document, stack, pdf, responses):
    it = iter(responses)
    return ToolContext(
        document=document,
        command_stack=stack,
        page_index=0,
        default_style=Style(),
        pdf=pdf,
        text_provider=lambda title: next(it, None),
        preview_callback=lambda obj: None,
    )


def test_text_field_tool_creates_object_with_name_and_default(context):
    document, stack, pdf = context
    ctx = _context(document, stack, pdf, ["first_name", "Jane"])
    tool = TextFieldTool(ctx)
    tool.on_press((10, 10))
    tool.on_release((200, 30))
    obj = document.all_objects()[0]
    assert obj.type == "text_field"
    assert obj.text == "first_name\nJane"


def test_checkbox_tool_only_needs_a_name(context):
    document, stack, pdf = context
    ctx = _context(document, stack, pdf, ["agree_to_terms"])
    tool = CheckboxTool(ctx)
    tool.on_press((10, 10))
    tool.on_release((30, 30))
    obj = document.all_objects()[0]
    assert obj.type == "checkbox"
    assert obj.text == "agree_to_terms"


def test_radio_button_tool(context):
    document, stack, pdf = context
    ctx = _context(document, stack, pdf, ["choice_a"])
    tool = RadioButtonTool(ctx)
    tool.on_press((10, 10))
    tool.on_release((30, 30))
    assert any(o.type == "radio_button" for o in document.all_objects())


def test_dropdown_tool_stores_options(context):
    document, stack, pdf = context
    ctx = _context(document, stack, pdf, ["country", "US, UK, IN"])
    tool = DropdownTool(ctx)
    tool.on_press((10, 10))
    tool.on_release((200, 30))
    obj = document.all_objects()[0]
    assert obj.text == "country\nUS, UK, IN"


def test_date_field_tool_rejects_bad_date_then_accepts(context):
    document, stack, pdf = context
    ctx = _context(document, stack, pdf, ["signed_on", "not-a-date", "2024-01-15"])
    tool = DateFieldTool(ctx)
    tool.on_press((10, 10))
    tool.on_release((200, 30))
    obj = document.all_objects()[0]
    assert obj.text == "signed_on\n2024-01-15"


def test_date_field_tool_blank_is_accepted(context):
    document, stack, pdf = context
    ctx = _context(document, stack, pdf, ["signed_on", ""])
    tool = DateFieldTool(ctx)
    tool.on_press((10, 10))
    tool.on_release((200, 30))
    obj = document.all_objects()[0]
    assert obj.text == "signed_on\n"


def test_signature_field_tool(context):
    document, stack, pdf = context
    ctx = _context(document, stack, pdf, ["client_signature"])
    tool = SignatureFieldTool(ctx)
    tool.on_press((10, 10))
    tool.on_release((200, 40))
    obj = document.all_objects()[0]
    assert obj.type == "signature_field"


def test_form_fields_bake_as_real_acroform_widgets(context, tmp_path):
    document, stack, pdf = context
    ctx = _context(document, stack, pdf, ["name", "default value", "agree", "opt_name", "Red,Green,Blue"])

    text_tool = TextFieldTool(ctx)
    text_tool.on_press((10, 10))
    text_tool.on_release((200, 30))

    checkbox_tool = CheckboxTool(ctx)
    checkbox_tool.on_press((10, 40))
    checkbox_tool.on_release((30, 60))

    dropdown_tool = DropdownTool(ctx)
    dropdown_tool.on_press((10, 70))
    dropdown_tool.on_release((200, 90))

    out = str(tmp_path / "form.pdf")
    pdf.export(out, document.all_objects())

    check = fitz.open(out)
    widgets = {w.field_name: w for w in check[0].widgets()}
    assert widgets["name"].field_value == "default value"
    assert widgets["agree"].field_type_string == "CheckBox"
    assert widgets["opt_name"].choice_values == ["Red", "Green", "Blue"]
    check.close()
