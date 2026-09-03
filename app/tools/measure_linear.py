"""Linear distance measurement with a live-updating dimension label
(Blueprint v2, Section 7.2)."""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject, Measurement
from app.tools.base import Tool
from app.tools.measurement_math import format_measurement, path_length, to_real_length


class MeasureLinearTool(Tool):
    tool_id = "measure_linear"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._start: tuple[float, float] | None = None

    def _label(self, points: list[tuple[float, float]]) -> str:
        value, unit = to_real_length(path_length(points), self.context.active_calibration)
        return format_measurement(value, unit)

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        self._start = pdf_point

    def on_move(self, pdf_point: tuple[float, float]) -> None:
        if self._start is None:
            return
        points = [self._start, pdf_point]
        draft = MarkupObject(
            type="measure_linear",
            page_index=self.context.page_index,
            points=points,
            text=self._label(points),
            style=self.context.default_style,
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
        calibration = self.context.active_calibration
        value, unit = to_real_length(path_length(points), calibration)
        style = self.context.default_style
        obj = MarkupObject(
            type="measure_linear",
            page_index=self.context.page_index,
            points=points,
            text=format_measurement(value, unit),
            style=style.__class__(**style.to_dict()),
            measurement=Measurement(
                calibration_id=calibration.id if calibration else None, value=value, unit=unit
            ),
            author=self.context.author,
        )
        self.context.command_stack.push(AddObjectCommand(self.context.document, obj))

    def deactivate(self) -> None:
        super().deactivate()
        self._start = None
