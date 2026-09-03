from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.persistence import autosave
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
