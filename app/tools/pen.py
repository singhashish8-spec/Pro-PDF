"""Freehand pen tool (Blueprint v2, Section 7.1)."""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.tools.base import Tool


class PenTool(Tool):
    tool_id = "pen"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._points: list[tuple[float, float]] = []

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        self._points = [pdf_point]

    def on_move(self, pdf_point: tuple[float, float]) -> None:
        if not self._points:
            return
        self._points.append(pdf_point)
        draft = MarkupObject(
            type="pen",
            page_index=self.context.page_index,
            points=list(self._points),
            style=self.context.default_style,
        )
        self.context.preview_callback(draft)

    def on_release(self, pdf_point: tuple[float, float]) -> None:
        self.context.preview_callback(None)
        if not self._points:
            return
        self._points.append(pdf_point)
        if len(self._points) >= 2:
            style = self.context.default_style
            obj = MarkupObject(
                type="pen",
                page_index=self.context.page_index,
                points=list(self._points),
                style=style.__class__(**style.to_dict()),
                author=self.context.author,
            )
            self.context.command_stack.push(AddObjectCommand(self.context.document, obj))
        self._points = []

    def deactivate(self) -> None:
        super().deactivate()
        self._points = []
