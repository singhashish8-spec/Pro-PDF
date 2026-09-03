from app.commands.base import CommandStack
from app.commands.object_commands import (
    AddObjectCommand,
    DeleteObjectCommand,
    MoveObjectCommand,
    StyleChangeCommand,
)
from app.models.markup import MarkupObject
from app.models.project import MarkupDocument


def _rect(page_index: int = 0) -> MarkupObject:
    return MarkupObject(type="rectangle", page_index=page_index, points=[(0, 0), (10, 10)])


def test_add_object_do_and_undo():
    doc = MarkupDocument()
    stack = CommandStack()
    obj = _rect()

    stack.push(AddObjectCommand(doc, obj))
    assert doc.get(obj.id) is not None
    assert stack.can_undo and not stack.can_redo

    stack.undo()
    assert doc.get(obj.id) is None
    assert stack.can_redo

    stack.redo()
    assert doc.get(obj.id) is not None


def test_delete_object_do_and_undo():
    doc = MarkupDocument()
    stack = CommandStack()
    obj = _rect()
    doc.add(obj)

    stack.push(DeleteObjectCommand(doc, obj))
    assert doc.get(obj.id) is None

    stack.undo()
    assert doc.get(obj.id) is not None


def test_move_object_do_and_undo():
    doc = MarkupDocument()
    stack = CommandStack()
    obj = _rect()
    doc.add(obj)

    cmd = MoveObjectCommand(doc, obj.id, old_points=obj.points, new_points=[(5, 5), (15, 15)])
    stack.push(cmd)
    assert doc.get(obj.id).points == [(5, 5), (15, 15)]

    stack.undo()
    assert doc.get(obj.id).points == [(0, 0), (10, 10)]


def test_style_change_do_and_undo():
    doc = MarkupDocument()
    stack = CommandStack()
    obj = _rect()
    doc.add(obj)
    old = {"stroke_color": obj.style.stroke_color}

    stack.push(StyleChangeCommand(doc, obj.id, old_style=old, new_style={"stroke_color": "#FF0000"}))
    assert doc.get(obj.id).style.stroke_color == "#FF0000"

    stack.undo()
    assert doc.get(obj.id).style.stroke_color == old["stroke_color"]


def test_redo_cleared_on_new_push():
    doc = MarkupDocument()
    stack = CommandStack()
    obj1, obj2 = _rect(), _rect()

    stack.push(AddObjectCommand(doc, obj1))
    stack.undo()
    assert stack.can_redo

    stack.push(AddObjectCommand(doc, obj2))
    assert not stack.can_redo


def test_command_stack_notifies_listeners():
    doc = MarkupDocument()
    stack = CommandStack()
    calls = []
    stack.add_listener(lambda: calls.append(1))

    stack.push(AddObjectCommand(doc, _rect()))
    assert len(calls) == 1

    stack.undo()
    assert len(calls) == 2
