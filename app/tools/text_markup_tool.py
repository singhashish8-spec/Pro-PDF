"""Shared base for underline/strikeout/squiggly — tied to actual text lines
under the drag, not freehand (Blueprint v2, Section 7.1)."""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand, CompositeCommand
from app.models.markup import MarkupObject
from app.tools.base import Tool
from app.tools.geometry import bbox_of
from app.tools.text_line_lookup import lines_in_drag_rect


class TextLineMarkupTool(Tool):
    markup_type: str = "underline"
    #: Fraction of line height from the top where the mark is drawn (0=top, 1=bottom).
    vertical_fraction: float = 0.9

    def __init__(self, context) -> None:
        super().__init__(context)
        self._start: tuple[float, float] | None = None

    def _line_points(self, x0: float, y0: float, x1: float, y1: float) -> list[tuple[float, float]]:
        y = y0 + (y1 - y0) * self.vertical_fraction
        return [(x0, y), (x1, y)]

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
        rect = bbox_of([self._start, pdf_point])
        style = self.context.default_style
        lines = lines_in_drag_rect(self.context.pdf, self.context.page_index, rect)

        segments = [self._line_points(*line) for line in lines] if lines else [[self._start, pdf_point]]
        commands = []
        for points in segments:
            obj = MarkupObject(
                type=self.markup_type,
                page_index=self.context.page_index,
                points=points,
                style=style.__class__(**style.to_dict()),
                author=self.context.author,
            )
            commands.append(AddObjectCommand(self.context.document, obj))
        if commands:
            self.context.command_stack.push(CompositeCommand(commands, label=self.markup_type.title()))
        self._start = None

    def deactivate(self) -> None:
        super().deactivate()
        self._start = None
