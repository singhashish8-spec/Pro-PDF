from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.persistence import autosave
from app.tools.cloud import CloudTool
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
