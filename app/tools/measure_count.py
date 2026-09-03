"""Count tool: click-to-tally, e.g. door/window counts (Blueprint v2, Section 7.2).

Each click places a sequentially numbered marker on the page; the running
total is just the number of measure_count objects on that page.
"""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.tools.base import Tool


class MeasureCountTool(Tool):
    tool_id = "measure_count"

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        existing = [o for o in self.context.document.objects_on_page(self.context.page_index) if o.type == "measure_count"]
        next_number = len(existing) + 1
        style = self.context.default_style
        obj = MarkupObject(
            type="measure_count",
            page_index=self.context.page_index,
            points=[pdf_point],
            text=str(next_number),
            style=style.__class__(**style.to_dict()),
            author=self.context.author,
        )
        self.context.command_stack.push(AddObjectCommand(self.context.document, obj))

    @staticmethod
    def count_on_page(document, page_index: int) -> int:
        return len([o for o in document.objects_on_page(page_index) if o.type == "measure_count"])
