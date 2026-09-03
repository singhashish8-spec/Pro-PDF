"""Stamp tool, including dynamic stamps with auto-filled date/user (Blueprint v2, Section 7.1)."""

from __future__ import annotations

from datetime import date

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.tools.base import Tool

STAMP_PRESETS = ("APPROVED", "REVIEWED", "DRAFT", "REJECTED", "FOR REVIEW", "AS BUILT")


class StampTool(Tool):
    tool_id = "stamp"

    def __init__(self, context, preset: str = "REVIEWED") -> None:
        super().__init__(context)
        self.preset = preset if preset in STAMP_PRESETS else STAMP_PRESETS[0]

    def _stamp_text(self) -> str:
        today = date.today().isoformat()
        return f"{self.preset}\n{self.context.author} — {today}"

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        style = self.context.default_style
        obj = MarkupObject(
            type="stamp",
            page_index=self.context.page_index,
            points=[pdf_point],
            text=self._stamp_text(),
            style=style.__class__(**style.to_dict()),
            author=self.context.author,
        )
        self.context.command_stack.push(AddObjectCommand(self.context.document, obj))
