"""Text box / Typewriter tool (Blueprint v2, Section 7.1)."""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.tools.base import Tool


class TextBoxTool(Tool):
    tool_id = "textbox"

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        text = self.context.text_provider("Insert text")
        if not text:
            return
        style = self.context.default_style
        obj = MarkupObject(
            type="textbox",
            page_index=self.context.page_index,
            points=[pdf_point],
            text=text,
            style=style.__class__(**style.to_dict()),
            author=self.context.author,
        )
        self.context.command_stack.push(AddObjectCommand(self.context.document, obj))
