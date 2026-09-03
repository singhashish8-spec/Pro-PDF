"""Select/move tool — the default tool (Blueprint v2, Phase 3)."""

from __future__ import annotations

from app.commands.object_commands import DeleteObjectCommand, MoveObjectCommand
from app.tools.base import Tool, ToolContext
from app.tools.geometry import bbox_of, point_in_bbox, translate_points


class SelectTool(Tool):
    tool_id = "select"
    cursor = "arrow"

    def __init__(self, context: ToolContext) -> None:
        super().__init__(context)
        self.selected_id: str | None = None
        self._drag_start: tuple[float, float] | None = None
        self._orig_points: list[tuple[float, float]] = []

    def _hit_test(self, pdf_point: tuple[float, float]) -> str | None:
        objects = self.context.document.objects_on_page(self.context.page_index)
        for obj in reversed(objects):  # topmost (most recently added) first
            if len(obj.points) >= 2 and point_in_bbox(pdf_point, bbox_of(obj.points)):
                return obj.id
        return None

    def select(self, obj_id: str | None) -> None:
        self.selected_id = obj_id
        self.context.selection_callback(obj_id)

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        hit_id = self._hit_test(pdf_point)
        self.select(hit_id)
        if hit_id is not None:
            obj = self.context.document.get(hit_id)
            self._drag_start = pdf_point
            self._orig_points = list(obj.points)
        else:
            self._drag_start = None

    def on_move(self, pdf_point: tuple[float, float]) -> None:
        if self._drag_start is None or self.selected_id is None:
            return
        dx = pdf_point[0] - self._drag_start[0]
        dy = pdf_point[1] - self._drag_start[1]
        obj = self.context.document.get(self.selected_id)
        if obj is None:
            return
        draft = obj.clone(points=translate_points(self._orig_points, dx, dy))
        self.context.preview_callback(draft)

    def on_release(self, pdf_point: tuple[float, float]) -> None:
        self.context.preview_callback(None)
        if self._drag_start is None or self.selected_id is None:
            return
        dx = pdf_point[0] - self._drag_start[0]
        dy = pdf_point[1] - self._drag_start[1]
        if dx == 0 and dy == 0:
            self._drag_start = None
            return
        new_points = translate_points(self._orig_points, dx, dy)
        self.context.command_stack.push(
            MoveObjectCommand(self.context.document, self.selected_id, self._orig_points, new_points)
        )
        self._drag_start = None

    def delete_selected(self) -> None:
        if self.selected_id is None:
            return
        obj = self.context.document.get(self.selected_id)
        if obj is not None:
            self.context.command_stack.push(DeleteObjectCommand(self.context.document, obj))
        self.select(None)

    def deactivate(self) -> None:
        super().deactivate()
        self.select(None)
        self._drag_start = None
