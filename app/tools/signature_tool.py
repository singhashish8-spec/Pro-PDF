"""Real signature tool: draw freehand or type a name (Blueprint v2,
Section 7.1 — "distinct from freehand pen": semantically a signature,
not a generic pen stroke, even though a drawn one shares the mechanics).
"""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.tools.base import Tool

#: A drag shorter than this (in PDF points) is treated as a click, not a draw.
_CLICK_THRESHOLD = 3.0


class SignatureTool(Tool):
    tool_id = "signature"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._points: list[tuple[float, float]] = []

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        self._points = [pdf_point]

    def on_move(self, pdf_point: tuple[float, float]) -> None:
        if not self._points:
            return
        self._points.append(pdf_point)
        draft = MarkupObject(
            type="signature",
            page_index=self.context.page_index,
            points=list(self._points),
            style=self.context.default_style,
        )
        self.context.preview_callback(draft)

    def on_release(self, pdf_point: tuple[float, float]) -> None:
        self.context.preview_callback(None)
        if not self._points:
            return
        start = self._points[0]
        self._points.append(pdf_point)
        drag_distance = max(abs(p[0] - start[0]) + abs(p[1] - start[1]) for p in self._points)
        style = self.context.default_style

        if drag_distance < _CLICK_THRESHOLD:
            # A click, not a drag: type a signature instead of drawing one.
            text = self.context.text_provider("Type your signature")
            self._points = []
            if not text:
                return
            obj = MarkupObject(
                type="signature",
                page_index=self.context.page_index,
                points=[start],
                text=text,
                style=style.__class__(**style.to_dict()),
                author=self.context.author,
            )
        else:
            obj = MarkupObject(
                type="signature",
                page_index=self.context.page_index,
                points=list(self._points),
                style=style.__class__(**style.to_dict()),
                author=self.context.author,
            )
            self._points = []

        self.context.command_stack.push(AddObjectCommand(self.context.document, obj))

    def deactivate(self) -> None:
        super().deactivate()
        self._points = []
