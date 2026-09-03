"""Cloud/polygon markup — the AEC-standard redline shape (Blueprint v2, Section 7.1).

Click to add vertices; call finish() (bound to Enter/Return in the canvas) to
close the polygon and commit it, or cancel() (Escape) to discard it.
"""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.tools.base import Tool


class CloudTool(Tool):
    tool_id = "cloud"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._points: list[tuple[float, float]] = []

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        self._points.append(pdf_point)
        self._update_preview()

    def on_move(self, pdf_point: tuple[float, float]) -> None:
        if not self._points:
            return
        self._update_preview(extra_point=pdf_point)

    def _update_preview(self, extra_point: tuple[float, float] | None = None) -> None:
        points = list(self._points)
        if extra_point is not None:
            points = points + [extra_point]
        if len(points) < 2:
            return
        draft = MarkupObject(
            type="cloud",
            page_index=self.context.page_index,
            points=points,
            style=self.context.default_style,
        )
        self.context.preview_callback(draft)

    def finish(self) -> None:
        self.context.preview_callback(None)
        if len(self._points) >= 3:
            style = self.context.default_style
            obj = MarkupObject(
                type="cloud",
                page_index=self.context.page_index,
                points=list(self._points),
                style=style.__class__(**style.to_dict()),
                author=self.context.author,
            )
            self.context.command_stack.push(AddObjectCommand(self.context.document, obj))
        self._points = []

    def cancel(self) -> None:
        self.context.preview_callback(None)
        self._points = []

    def deactivate(self) -> None:
        super().deactivate()
        self._points = []
