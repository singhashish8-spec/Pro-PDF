"""Concrete Command implementations for markup-object mutations."""

from __future__ import annotations

from typing import Any

from app.commands.base import Command
from app.models.markup import MarkupObject
from app.models.project import Calibration, MarkupDocument


class AddObjectCommand(Command):
    label = "Add object"

    def __init__(self, document: MarkupDocument, obj: MarkupObject) -> None:
        self._document = document
        self._obj = obj

    def do(self) -> None:
        self._document.add(self._obj)

    def undo(self) -> None:
        self._document.remove(self._obj.id)


class DeleteObjectCommand(Command):
    label = "Delete object"

    def __init__(self, document: MarkupDocument, obj: MarkupObject) -> None:
        self._document = document
        self._obj = obj

    def do(self) -> None:
        self._document.remove(self._obj.id)

    def undo(self) -> None:
        self._document.add(self._obj)


class MoveObjectCommand(Command):
    label = "Move object"

    def __init__(
        self,
        document: MarkupDocument,
        obj_id: str,
        old_points: list[tuple[float, float]],
        new_points: list[tuple[float, float]],
    ) -> None:
        self._document = document
        self._obj_id = obj_id
        self._old_points = old_points
        self._new_points = new_points

    def do(self) -> None:
        obj = self._document.get(self._obj_id)
        if obj is not None:
            obj.points = list(self._new_points)
            obj.touch()
            self._document.notify_object_changed()

    def undo(self) -> None:
        obj = self._document.get(self._obj_id)
        if obj is not None:
            obj.points = list(self._old_points)
            obj.touch()
            self._document.notify_object_changed()


class StyleChangeCommand(Command):
    label = "Change style"

    def __init__(
        self,
        document: MarkupDocument,
        obj_id: str,
        old_style: dict[str, Any],
        new_style: dict[str, Any],
    ) -> None:
        self._document = document
        self._obj_id = obj_id
        self._old_style = old_style
        self._new_style = new_style

    def _apply(self, style_dict: dict[str, Any]) -> None:
        obj = self._document.get(self._obj_id)
        if obj is None:
            return
        for key, value in style_dict.items():
            setattr(obj.style, key, value)
        obj.touch()
        self._document.notify_object_changed()

    def do(self) -> None:
        self._apply(self._new_style)

    def undo(self) -> None:
        self._apply(self._old_style)


class CompositeCommand(Command):
    """Groups several commands into a single undo step (e.g. a text-selection
    based markup that produces one object per intersected line)."""

    def __init__(self, commands: list[Command], label: str = "Add objects") -> None:
        self._commands = commands
        self.label = label

    def do(self) -> None:
        for command in self._commands:
            command.do()

    def undo(self) -> None:
        for command in reversed(self._commands):
            command.undo()


class CalibrateCommand(Command):
    label = "Calibrate scale"

    def __init__(self, document: MarkupDocument, calibration: Calibration) -> None:
        self._document = document
        self._calibration = calibration

    def do(self) -> None:
        self._document.add_calibration(self._calibration)

    def undo(self) -> None:
        self._document.remove_calibration(self._calibration.id)
