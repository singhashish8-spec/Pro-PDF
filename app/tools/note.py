"""Sticky note / comment tool (Blueprint v2, Section 7.1)."""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.tools.base import Tool


class NoteTool(Tool):
    tool_id = "note"

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        text = self.context.text_provider("Add note")
        if not text:
            return
        obj = MarkupObject(
            type="note",
            page_index=self.context.page_index,
            points=[pdf_point],
            text=text,
            style=self.context.default_style.__class__(**self.context.default_style.to_dict()),
            author=self.context.author,
        )
        self.context.command_stack.push(AddObjectCommand(self.context.document, obj))
