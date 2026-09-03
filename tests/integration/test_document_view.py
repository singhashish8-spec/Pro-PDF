import pytest

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.persistence import autosave, markups_db
from app.tools.calibration_tool import CalibrationTool
from app.tools.cloud import CloudTool
from app.tools.measure_area import MeasureAreaTool
from app.tools.measure_linear import MeasureLinearTool
from app.tools.rectangle import RectangleTool
from app.tools.select_tool import SelectTool
from app.ui.canvas.document_view import DocumentView


def test_load_renders_first_page(qapp, make_pdf):
    path = make_pdf(page_count=3)
    autosave.clear_journal(path)  # tmp_path dirs can be reused across local test runs
    view = DocumentView()
    has_journal = view.load(path)

    assert has_journal is False
    assert view.current_page == 0
    assert not view.scene._background_item.pixmap().isNull()
    view.pdf.close()


def test_page_navigation_clamped(qapp, make_pdf):
    path = make_pdf(page_count=3)
    view = DocumentView()
    view.load(path)

    view.go_to_page(10)
    assert view.current_page == 2

    view.go_to_page(-5)
    assert view.current_page == 0
    view.pdf.close()


def test_add_object_via_command_stack_rebuilds_scene(qapp, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    obj = MarkupObject(type="rectangle", page_index=0, points=[(50, 50), (150, 150)])
    view.command_stack.push(AddObjectCommand(view.markup_document, obj))

    assert obj.id in view.scene._markup_items
    view.pdf.close()


def test_autosave_journal_written_and_recovered(qapp, make_pdf, tmp_path):
    path = make_pdf(page_count=1)
    autosave.clear_journal(path)  # tmp_path dirs can be reused across local test runs
    view = DocumentView()
    view.load(path)

    obj = MarkupObject(type="rectangle", page_index=0, points=[(1, 1), (2, 2)])
    view.command_stack.push(AddObjectCommand(view.markup_document, obj))

    assert autosave.journal_exists(path)
    view.pdf.close()

    # Simulate reopening after a crash.
    recovered_view = DocumentView()
    has_journal = recovered_view.load(path)
    assert has_journal is True
    recovered_view.recover_from_journal()
    assert recovered_view.markup_document.get(obj.id) is not None

    recovered_view.discard_journal()
    assert not autosave.journal_exists(path)
    recovered_view.pdf.close()


def test_select_tool_is_default_after_load(qapp, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)
    assert isinstance(view.active_tool, SelectTool)
    assert view._tool_buttons[SelectTool].isChecked()
    view.pdf.close()


def test_select_tool_via_toolbar_button(qapp, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    view.select_tool(RectangleTool)
    assert isinstance(view.active_tool, RectangleTool)
    assert view._tool_buttons[RectangleTool].isChecked()
    assert not view._tool_buttons[SelectTool].isChecked()
    view.pdf.close()


def test_delete_shortcut_removes_selected_object(qapp, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    obj = MarkupObject(type="rectangle", page_index=0, points=[(10, 10), (50, 50)])
    view.command_stack.push(AddObjectCommand(view.markup_document, obj))

    view.select_tool(SelectTool)
    view.active_tool.on_press((20, 20))
    assert view.active_tool.selected_id == obj.id

    view._on_delete_key()
    assert view.markup_document.get(obj.id) is None
    view.pdf.close()


def test_finish_and_escape_shortcuts_drive_cloud_tool(qapp, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    view.select_tool(CloudTool)
    view.active_tool.on_press((0, 0))
    view.active_tool.on_press((10, 10))
    view.active_tool.on_press((5, 20))
    view._on_finish_key()
    assert len(view.markup_document.all_objects()) == 1
    assert view.markup_document.all_objects()[0].type == "cloud"

    # Escape always returns to the Select tool.
    view._on_escape()
    assert isinstance(view.active_tool, SelectTool)
    view.pdf.close()


def test_selecting_object_shows_floating_panel(qapp, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    obj = MarkupObject(type="rectangle", page_index=0, points=[(50, 50), (150, 150)])
    view.command_stack.push(AddObjectCommand(view.markup_document, obj))

    view.select_tool(SelectTool)
    view.active_tool.on_press((60, 60))
    assert view._floating_panel._obj_id == obj.id

    view.active_tool.on_press((999, 999))  # click empty space clears selection
    assert view._floating_panel._obj_id is None


def test_switching_away_from_select_hides_floating_panel(qapp, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    obj = MarkupObject(type="rectangle", page_index=0, points=[(50, 50), (150, 150)])
    view.command_stack.push(AddObjectCommand(view.markup_document, obj))
    view.select_tool(SelectTool)
    view.active_tool.on_press((60, 60))
    assert view._floating_panel._obj_id == obj.id

    view.select_tool(RectangleTool)
    assert view._floating_panel._obj_id is None


def test_command_palette_opens_and_lists_tools(qapp, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    commands = view.build_palette_commands()
    labels = {c.label for c in commands}
    assert "Rectangle" in labels
    assert "Undo" in labels
    assert "Zoom In" in labels
    assert "Distance" in labels
    assert "Calibrate" in labels


def test_calibration_flows_into_measurement_tools(qapp, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    # "No scale" is the only entry before any calibration is set.
    assert view._scale_combo.count() == 1

    view.prompt_for_text = lambda title: "10 ft"
    view.select_tool(CalibrationTool)
    view.active_tool.on_press((0, 0))
    view.active_tool.on_release((100, 0))  # 100 pdf pts = 10 ft -> scale_factor 0.1

    # New calibration is picked up automatically and offered in the combo.
    assert view._scale_combo.count() == 2
    assert view._active_calibration_by_page[0] is not None

    view.select_tool(MeasureLinearTool)
    view.active_tool.on_press((0, 0))
    view.active_tool.on_release((50, 0))  # 50 pdf pts * 0.1 = 5 ft
    obj = [o for o in view.markup_document.all_objects() if o.type == "measure_linear"][0]
    assert obj.measurement.value == pytest.approx(5.0)
    assert obj.measurement.unit == "ft"
    view.pdf.close()


def test_finish_key_also_drives_measure_area_tool(qapp, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    view.select_tool(MeasureAreaTool)
    view.active_tool.on_press((0, 0))
    view.active_tool.on_press((10, 0))
    view.active_tool.on_press((10, 10))
    view.active_tool.on_press((0, 10))
    view._on_finish_key()

    obj = view.markup_document.all_objects()[0]
    assert obj.type == "measure_area"
    assert obj.measurement.value == pytest.approx(100.0)
    view.pdf.close()


def test_deleting_page_removes_its_markups_and_shifts_later_ones(qapp, make_pdf):
    path = make_pdf(page_count=3)
    view = DocumentView()
    view.load(path)

    on_deleted_page = MarkupObject(type="rectangle", page_index=1, points=[(0, 0), (1, 1)])
    on_later_page = MarkupObject(type="rectangle", page_index=2, points=[(0, 0), (1, 1)])
    view.command_stack.push(AddObjectCommand(view.markup_document, on_deleted_page))
    view.command_stack.push(AddObjectCommand(view.markup_document, on_later_page))

    view.go_to_page(1)
    view.delete_current_page()

    assert view.pdf.page_count == 2
    assert view.markup_document.get(on_deleted_page.id) is None
    assert view.markup_document.get(on_later_page.id).page_index == 1
    view.pdf.close()


def test_insert_page_shifts_later_markups(qapp, make_pdf):
    path = make_pdf(page_count=2)
    view = DocumentView()
    view.load(path)

    obj = MarkupObject(type="rectangle", page_index=1, points=[(0, 0), (1, 1)])
    view.command_stack.push(AddObjectCommand(view.markup_document, obj))

    view.insert_page(0)

    assert view.pdf.page_count == 3
    assert view.markup_document.get(obj.id).page_index == 2
    view.pdf.close()


def test_move_page_remaps_markups(qapp, make_pdf):
    path = make_pdf(page_count=3)
    view = DocumentView()
    view.load(path)

    obj = MarkupObject(type="rectangle", page_index=0, points=[(0, 0), (1, 1)])
    view.command_stack.push(AddObjectCommand(view.markup_document, obj))

    view.move_page(0, 2)  # page 0 moves to the end

    assert view.markup_document.get(obj.id).page_index == 2
    view.pdf.close()


def test_stack_change_syncs_markups_db(qapp, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    signals = []
    view.markups_changed.connect(lambda: signals.append(True))

    obj = MarkupObject(type="rectangle", page_index=0, points=[(0, 0), (1, 1)])
    view.command_stack.push(AddObjectCommand(view.markup_document, obj))

    assert signals  # markups_changed fired
    rows = markups_db.list_markups(path)
    assert len(rows) == 1
    assert rows[0]["id"] == obj.id
    view.pdf.close()


def test_select_object_navigates_and_selects(qapp, make_pdf):
    path = make_pdf(page_count=2)
    view = DocumentView()
    view.load(path)

    obj = MarkupObject(type="rectangle", page_index=1, points=[(10, 10), (50, 50)])
    view.command_stack.push(AddObjectCommand(view.markup_document, obj))

    view.go_to_page(0)
    view.select_object(obj.id)

    assert view.current_page == 1
    assert isinstance(view.active_tool, SelectTool)
    assert view.active_tool.selected_id == obj.id
    view.pdf.close()


def test_watermark_bates_header_footer_apply_without_error(qapp, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    view.apply_watermark("DRAFT")
    view.apply_bates_numbers("XYZ-", 1)
    view.apply_header_footer("Header", "Footer")
    # A subsequent export should succeed and reflect the in-memory changes.
    view.pdf.close()


def test_redaction_tool_via_palette_and_shortcuts(qapp, make_pdf):
    from app.tools.redaction_tool import RedactionTool

    path = make_pdf(page_count=1, text="TOP SECRET")
    view = DocumentView()
    view.load(path)

    view.select_tool(RedactionTool)
    assert isinstance(view.active_tool, RedactionTool)
    assert view._tool_buttons[RedactionTool].isChecked()

    view.active_tool.on_press((50, 55))
    view.active_tool.on_release((250, 90))
    obj = view.markup_document.all_objects()[0]
    assert obj.type == "redaction"

    out = str(view.pdf.path) + ".redacted.pdf"
    view.pdf.export(out, view.markup_document.all_objects())

    import pymupdf as fitz

    check = fitz.open(out)
    assert "TOP SECRET" not in check[0].get_text()
    check.close()
    view.pdf.close()


def test_signature_and_form_field_tools_reachable_from_palette(qapp, make_pdf):
    from app.tools.signature_tool import SignatureTool
    from app.tools.text_field import TextFieldTool

    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    view.prompt_for_text = lambda title: "field_name"
    view.select_tool(TextFieldTool)
    view.active_tool.on_press((10, 10))
    view.active_tool.on_release((150, 30))
    assert view.markup_document.all_objects()[0].type == "text_field"

    view.prompt_for_text = lambda title: "Signed"
    view.select_tool(SignatureTool)
    view.active_tool.on_press((10, 100))
    view.active_tool.on_release((10, 100))
    assert any(o.type == "signature" for o in view.markup_document.all_objects())
    view.pdf.close()
