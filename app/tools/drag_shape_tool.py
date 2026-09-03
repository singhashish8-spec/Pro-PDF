"""Shared base for two-point drag-to-draw shapes (rectangle, ellipse, arrow)."""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.tools.base import Tool


class DragShapeTool(Tool):
    markup_type: str = "rectangle"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._start: tuple[float, float] | None = None

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        self._start = pdf_point

    def on_move(self, pdf_point: tuple[float, float]) -> None:
        if self._start is None:
            return
        draft = MarkupObject(
            type=self.markup_type,
            page_index=self.context.page_index,
            points=[self._start, pdf_point],
            style=self.context.default_style,
        )
        self.context.preview_callback(draft)

    def on_release(self, pdf_point: tuple[float, float]) -> None:
        self.context.preview_callback(None)
        if self._start is None:
            return
        if self._start != pdf_point:
            obj = MarkupObject(
                type=self.markup_type,
                page_index=self.context.page_index,
                points=[self._start, pdf_point],
                style=self.context.default_style.__class__(**self.context.default_style.to_dict()),
                author=self.context.author,
            )
            self.context.command_stack.push(AddObjectCommand(self.context.document, obj))
        self._start = None

    def deactivate(self) -> None:
        super().deactivate()
        self._start = None
