"""Shared base for area/perimeter measurement: click to add vertices,
finish() (Return/Enter) closes the shape and computes the measurement
(Blueprint v2, Section 7.2)."""

from __future__ import annotations

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject, Measurement
from app.tools.base import Tool
from app.tools.measurement_math import format_measurement, polygon_area, polygon_perimeter, to_real_area, to_real_length


class MeasurePolygonTool(Tool):
    markup_type: str = "measure_area"
    mode: str = "area"  # "area" | "perimeter"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._points: list[tuple[float, float]] = []

    def _compute(self, points: list[tuple[float, float]]) -> tuple[float, str]:
        calibration = self.context.active_calibration
        if self.mode == "area":
            return to_real_area(polygon_area(points), calibration)
        return to_real_length(polygon_perimeter(points), calibration)

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
        value, unit = self._compute(points)
        draft = MarkupObject(
            type=self.markup_type,
            page_index=self.context.page_index,
            points=points,
            text=format_measurement(value, unit),
            style=self.context.default_style,
        )
        self.context.preview_callback(draft)

    def finish(self) -> None:
        self.context.preview_callback(None)
        if len(self._points) >= 3:
            calibration = self.context.active_calibration
            value, unit = self._compute(self._points)
            style = self.context.default_style
            obj = MarkupObject(
                type=self.markup_type,
                page_index=self.context.page_index,
                points=list(self._points),
                text=format_measurement(value, unit),
                style=style.__class__(**style.to_dict()),
                measurement=Measurement(
                    calibration_id=calibration.id if calibration else None, value=value, unit=unit
                ),
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
