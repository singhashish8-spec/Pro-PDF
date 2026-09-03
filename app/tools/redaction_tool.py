"""Redaction: draw a box to permanently erase the content beneath it
(Blueprint v2, Section 7.5). Drawing here only stages a MarkupObject —
the actual destruction happens at bake/export time via
app.core.markup_baker._bake_redaction + Page.apply_redactions(), verified
non-negotiably by tests/unit/test_redaction.py (Section 11.3).
"""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject, Style
from app.tools.base import Tool

#: Redaction boxes are opaque black by default, not the tool's ambient default style.
REDACTION_STYLE = Style(stroke_color="#000000", fill_color="#000000", line_width=0.0, opacity=1.0)


class RedactionTool(Tool):
    tool_id = "redaction"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._start: tuple[float, float] | None = None

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        self._start = pdf_point

    def on_move(self, pdf_point: tuple[float, float]) -> None:
        if self._start is None:
            return
        draft = MarkupObject(
            type="redaction",
            page_index=self.context.page_index,
            points=[self._start, pdf_point],
            style=REDACTION_STYLE,
        )
        self.context.preview_callback(draft)

    def on_release(self, pdf_point: tuple[float, float]) -> None:
        self.context.preview_callback(None)
        if self._start is None:
            return
        points = [self._start, pdf_point]
        self._start = None
        if points[0] == points[1]:
            return
        obj = MarkupObject(
            type="redaction",
            page_index=self.context.page_index,
            points=points,
            style=Style(**REDACTION_STYLE.to_dict()),
            author=self.context.author,
        )
        self.context.command_stack.push(AddObjectCommand(self.context.document, obj))

    def deactivate(self) -> None:
        super().deactivate()
        self._start = None
