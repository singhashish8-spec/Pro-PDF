"""Callout tool: leader line + text (Blueprint v2, Section 7.1).

Click once to place the leader tip (pointing at the thing being annotated),
click again to place the text anchor, then enter the text.
"""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.tools.base import Tool


class CalloutTool(Tool):
    tool_id = "callout"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._leader_tip: tuple[float, float] | None = None

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        if self._leader_tip is None:
            self._leader_tip = pdf_point
            return

        text = self.context.text_provider("Callout text")
        leader_tip = self._leader_tip
        self._leader_tip = None
        if not text:
            return
        style = self.context.default_style
        obj = MarkupObject(
            type="callout",
            page_index=self.context.page_index,
            points=[leader_tip, pdf_point],
            text=text,
            style=style.__class__(**style.to_dict()),
            author=self.context.author,
        )
        self.context.command_stack.push(AddObjectCommand(self.context.document, obj))

    def deactivate(self) -> None:
        super().deactivate()
        self._leader_tip = None
