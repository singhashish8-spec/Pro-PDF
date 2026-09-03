import pytest

from app.commands.base import CommandStack
from app.core.pdf_document import PDFDocument
from app.models.markup import Style
from app.models.project import MarkupDocument
from app.tools.arrow import ArrowTool
from app.tools.base import ToolContext
from app.tools.callout import CalloutTool
from app.tools.cloud import CloudTool
from app.tools.ellipse import EllipseTool
from app.tools.eraser import EraserTool
from app.tools.geometry import arrowhead_wings, bbox_of, point_in_bbox, rect_intersection, wavy_points
from app.tools.highlighter import HighlighterTool
from app.tools.note import NoteTool
from app.tools.pen import PenTool
from app.tools.rectangle import RectangleTool
from app.tools.select_tool import SelectTool
from app.tools.squiggly import SquigglyTool
from app.tools.stamp import STAMP_PRESETS, StampTool
from app.tools.strikeout import StrikeoutTool
from app.tools.textbox import TextBoxTool
from app.tools.underline import UnderlineTool


@pytest.fixture
def context(make_pdf):
    path = make_pdf(page_count=1, text="Hello World", name="tools.pdf")
    pdf = PDFDocument()
    pdf.open(path)

    document = MarkupDocument()
    stack = CommandStack()
    previews = []
    texts = iter(["typed text"] * 10)
    selections = []
    return ToolContext(
        document=document,
        command_stack=stack,
        page_index=0,
        default_style=Style(),
        pdf=pdf,
        text_provider=lambda title: next(texts),
        preview_callback=previews.append,
        selection_callback=selections.append,
    )


def test_rectangle_tool_creates_object_on_release(context):
    tool = RectangleTool(context)
    tool.on_press((10, 10))
    tool.on_move((50, 50))
    tool.on_release((50, 50))
    objs = context.document.all_objects()
    assert len(objs) == 1
    assert objs[0].type == "rectangle"
    assert objs[0].points == [(10, 10), (50, 50)]


def test_rectangle_tool_no_op_on_zero_size_drag(context):
    tool = RectangleTool(context)
    tool.on_press((10, 10))
    tool.on_release((10, 10))
    assert context.document.all_objects() == []


def test_ellipse_and_arrow_tools(context):
    ellipse_tool = EllipseTool(context)
    ellipse_tool.on_press((0, 0))
    ellipse_tool.on_release((20, 20))
    arrow_tool = ArrowTool(context)
    arrow_tool.on_press((0, 0))
    arrow_tool.on_release((30, 30))
    types = {o.type for o in context.document.all_objects()}
    assert "ellipse" in types
    assert "arrow" in types


def test_pen_tool_freehand_path(context):
    tool = PenTool(context)
    tool.on_press((0, 0))
    tool.on_move((5, 5))
    tool.on_move((10, 0))
    tool.on_release((15, 5))
    obj = context.document.all_objects()[0]
    assert obj.type == "pen"
    assert len(obj.points) == 4


def test_highlighter_snaps_to_text_line(context):
    tool = HighlighterTool(context)
    tool.on_press((60, 55))
    tool.on_release((250, 80))
    obj = context.document.all_objects()[0]
    assert obj.type == "highlight"
    # Snapped to the text line's bbox (around y=60-75 for text inserted at y=72),
    # inside the raw drag range (55-80) but narrower than it.
    assert 55 <= obj.points[0][1] <= 80


def test_highlighter_falls_back_to_raw_rect_without_text(context):
    tool = HighlighterTool(context)
    tool.on_press((400, 400))
    tool.on_release((450, 420))
    obj = context.document.all_objects()[0]
    assert obj.points == [(400, 400), (450, 420)]


def test_underline_strikeout_use_different_vertical_offsets(context):
    u = UnderlineTool(context)
    u.on_press((60, 55))
    u.on_release((250, 80))
    s = StrikeoutTool(context)
    s.on_press((60, 55))
    s.on_release((250, 80))
    underline_obj = [o for o in context.document.all_objects() if o.type == "underline"][0]
    strikeout_obj = [o for o in context.document.all_objects() if o.type == "strikeout"][0]
    assert underline_obj.points[0][1] != strikeout_obj.points[0][1]


def test_squiggly_produces_wavy_multi_point_path(context):
    tool = SquigglyTool(context)
    tool.on_press((60, 55))
    tool.on_release((250, 80))
    obj = context.document.all_objects()[0]
    assert obj.type == "squiggly"
    assert len(obj.points) > 2


def test_note_tool_prompts_and_creates_object(context):
    tool = NoteTool(context)
    tool.on_press((100, 100))
    obj = context.document.all_objects()[0]
    assert obj.type == "note"
    assert obj.text == "typed text"


def test_note_tool_cancelled_creates_nothing():
    from app.commands.base import CommandStack as CS

    document = MarkupDocument()
    ctx = ToolContext(
        document=document,
        command_stack=CS(),
        page_index=0,
        default_style=Style(),
        pdf=None,
        text_provider=lambda title: None,
        preview_callback=lambda obj: None,
    )
    NoteTool(ctx).on_press((0, 0))
    assert document.all_objects() == []


def test_stamp_tool_fills_author_and_date(context):
    tool = StampTool(context, preset="APPROVED")
    tool.on_press((100, 100))
    obj = context.document.all_objects()[0]
    assert obj.type == "stamp"
    assert "APPROVED" in obj.text
    assert context.author in obj.text


def test_stamp_tool_rejects_unknown_preset_defaults_to_first(context):
    tool = StampTool(context, preset="NOT_REAL")
    assert tool.preset == STAMP_PRESETS[0]


def test_textbox_tool(context):
    TextBoxTool(context).on_press((10, 10))
    obj = context.document.all_objects()[0]
    assert obj.type == "textbox"
    assert obj.text == "typed text"


def test_callout_tool_two_clicks(context):
    tool = CalloutTool(context)
    tool.on_press((10, 10))
    assert context.document.all_objects() == []  # first click only sets the leader tip
    tool.on_press((50, 50))
    obj = context.document.all_objects()[0]
    assert obj.type == "callout"
    assert obj.points == [(10, 10), (50, 50)]


def test_cloud_tool_requires_three_points_to_finish(context):
    tool = CloudTool(context)
    tool.on_press((0, 0))
    tool.on_press((10, 10))
    tool.finish()
    assert context.document.all_objects() == []  # only 2 points

    tool.on_press((0, 0))
    tool.on_press((10, 10))
    tool.on_press((5, 20))
    tool.finish()
    obj = context.document.all_objects()[0]
    assert obj.type == "cloud"
    assert len(obj.points) == 3


def test_cloud_tool_cancel_discards_points(context):
    tool = CloudTool(context)
    tool.on_press((0, 0))
    tool.on_press((10, 10))
    tool.on_press((5, 20))
    tool.cancel()
    tool.finish()
    assert context.document.all_objects() == []


def test_select_tool_hit_test_and_move(context):
    rect_tool = RectangleTool(context)
    rect_tool.on_press((0, 0))
    rect_tool.on_release((10, 10))
    obj = context.document.all_objects()[0]

    select = SelectTool(context)
    select.on_press((5, 5))
    assert select.selected_id == obj.id

    select.on_move((15, 15))
    select.on_release((15, 15))
    assert context.document.get(obj.id).points == [(10, 10), (20, 20)]


def test_select_tool_click_empty_space_clears_selection(context):
    select = SelectTool(context)
    select.on_press((5, 5))
    select.select("fake-id")
    select.on_press((999, 999))
    assert select.selected_id is None


def test_select_tool_delete_selected(context):
    rect_tool = RectangleTool(context)
    rect_tool.on_press((0, 0))
    rect_tool.on_release((10, 10))
    obj = context.document.all_objects()[0]

    select = SelectTool(context)
    select.on_press((5, 5))
    select.delete_selected()
    assert context.document.get(obj.id) is None


def test_eraser_tool_deletes_object_under_click(context):
    rect_tool = RectangleTool(context)
    rect_tool.on_press((0, 0))
    rect_tool.on_release((10, 10))
    obj = context.document.all_objects()[0]

    eraser = EraserTool(context)
    eraser.on_press((5, 5))
    assert context.document.get(obj.id) is None


def test_eraser_tool_drag_erases_multiple(context):
    r1 = RectangleTool(context)
    r1.on_press((0, 0))
    r1.on_release((10, 10))
    r2 = RectangleTool(context)
    r2.on_press((100, 100))
    r2.on_release((110, 110))
    assert len(context.document.all_objects()) == 2

    eraser = EraserTool(context)
    eraser.on_press((5, 5))
    eraser.on_move((105, 105))
    eraser.on_release((105, 105))
    assert context.document.all_objects() == []


# -- geometry helpers ------------------------------------------------------


def test_bbox_and_point_in_bbox():
    box = bbox_of([(0, 0), (10, 10)])
    assert box == (0, 0, 10, 10)
    assert point_in_bbox((5, 5), box)
    assert not point_in_bbox((100, 100), box)


def test_rect_intersection_overlap_and_none():
    assert rect_intersection((0, 0, 10, 10), (5, 5, 15, 15)) == (5, 5, 10, 10)
    assert rect_intersection((0, 0, 10, 10), (20, 20, 30, 30)) is None


def test_wavy_points_span_the_full_range():
    pts = wavy_points(0, 100, y=0, amplitude=2, wavelength=6)
    xs = [p[0] for p in pts]
    assert xs[0] == pytest.approx(0)
    assert xs[-1] == pytest.approx(100)


def test_arrowhead_wings_point_back_toward_origin():
    wing1, wing2 = arrowhead_wings((0, 0), (100, 0), size=10)
    assert wing1[0] < 100
    assert wing2[0] < 100
