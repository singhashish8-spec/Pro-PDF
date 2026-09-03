"""Eraser tool: click or drag over objects to delete them (Blueprint v2, Section 7.1)."""

from __future__ import annotations

from app.commands.object_commands import DeleteObjectCommand
from app.tools.base import Tool
from app.tools.geometry import bbox_of, point_in_bbox


class EraserTool(Tool):
    tool_id = "eraser"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._erasing = False

    def _erase_at(self, pdf_point: tuple[float, float]) -> None:
        for obj in self.context.document.objects_on_page(self.context.page_index):
            if len(obj.points) >= 2 and point_in_bbox(pdf_point, bbox_of(obj.points)):
                self.context.command_stack.push(DeleteObjectCommand(self.context.document, obj))
                return  # one object per hit-test; drag continues to catch more

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        self._erasing = True
        self._erase_at(pdf_point)

    def on_move(self, pdf_point: tuple[float, float]) -> None:
        if self._erasing:
            self._erase_at(pdf_point)

    def on_release(self, pdf_point: tuple[float, float]) -> None:
        self._erasing = False
