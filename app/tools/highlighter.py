"""Highlighter with text-baseline snapping (Blueprint v2, Section 7.1)."""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand, CompositeCommand
from app.models.markup import MarkupObject
from app.tools.base import Tool
from app.tools.geometry import bbox_of
from app.tools.text_line_lookup import lines_in_drag_rect


class HighlighterTool(Tool):
    tool_id = "highlight"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._start: tuple[float, float] | None = None

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        self._start = pdf_point

    def on_move(self, pdf_point: tuple[float, float]) -> None:
        if self._start is None:
            return
        draft = MarkupObject(
            type="highlight",
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

        boxes = lines if lines else [rect]
        commands = []
        for x0, y0, x1, y1 in boxes:
            obj = MarkupObject(
                type="highlight",
                page_index=self.context.page_index,
                points=[(x0, y0), (x1, y1)],
                style=style.__class__(**style.to_dict()),
                author=self.context.author,
            )
            commands.append(AddObjectCommand(self.context.document, obj))
        if commands:
            self.context.command_stack.push(CompositeCommand(commands, label="Highlight"))
        self._start = None

    def deactivate(self) -> None:
        super().deactivate()
        self._start = None
