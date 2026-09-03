from PyQt6.QtCore import QPoint

from app.commands.base import CommandStack
from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.models.project import MarkupDocument
from app.ui.panels.floating_style_panel import FloatingStylePanel


def _make_object(document: MarkupDocument, stack: CommandStack) -> MarkupObject:
    obj = MarkupObject(type="rectangle", page_index=0, points=[(0, 0), (10, 10)])
    stack.push(AddObjectCommand(document, obj))
    return obj


def test_show_for_populates_controls_without_emitting_changes(qapp):
    document = MarkupDocument()
    stack = CommandStack()
    obj = _make_object(document, stack)
    obj.style.stroke_color = "#00FF00"
    obj.style.line_width = 3.0

    panel = FloatingStylePanel()
    panel.bind(document, stack)
    before_undo_len = len(stack._undo_stack)

    panel.show_for(obj, QPoint(10, 10))

    assert panel._width_spin.value() == 3.0
    assert len(stack._undo_stack) == before_undo_len  # showing the panel must not push a command


def test_width_change_pushes_style_command(qapp):
    document = MarkupDocument()
    stack = CommandStack()
    obj = _make_object(document, stack)
    original_width = obj.style.line_width

    panel = FloatingStylePanel()
    panel.bind(document, stack)
    panel.show_for(obj, QPoint(0, 0))

    panel._width_spin.setValue(7.5)
    assert document.get(obj.id).style.line_width == 7.5
    assert stack.can_undo

    stack.undo()
    assert document.get(obj.id).style.line_width == original_width


def test_clear_fill_sets_none(qapp):
    document = MarkupDocument()
    stack = CommandStack()
    obj = _make_object(document, stack)
    document.get(obj.id).style.fill_color = "#FF0000"

    panel = FloatingStylePanel()
    panel.bind(document, stack)
    panel.show_for(obj, QPoint(0, 0))

    panel._clear_fill_color()
    assert document.get(obj.id).style.fill_color is None


def test_delete_button_removes_object_and_calls_hook(qapp):
    document = MarkupDocument()
    stack = CommandStack()
    obj = _make_object(document, stack)

    panel = FloatingStylePanel()
    panel.bind(document, stack)
    panel.show_for(obj, QPoint(0, 0))

    called = []
    panel.set_on_delete(lambda: called.append(True))
    panel._on_delete_clicked()

    assert document.get(obj.id) is None
    assert called == [True]
