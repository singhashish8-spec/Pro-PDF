"""Scale calibration: draw a line of known real-world length to set the
page's scale (Blueprint v2, Section 7.2). Savable, multiple per document."""

from __future__ import annotations

import math
import uuid

from app.commands.object_commands import CalibrateCommand
from app.models.project import Calibration
from app.tools.base import Tool


def parse_distance_input(text: str) -> tuple[float, str] | None:
    """Parses input like "20 ft", "3.5m", "12" (defaults to ft) into (value, unit)."""
    text = text.strip()
    if not text:
        return None
    parts = text.split()
    try:
        if len(parts) >= 2:
            return float(parts[0]), parts[1]
        # No space: split trailing letters from the leading number.
        i = len(text)
        while i > 0 and not (text[i - 1].isdigit() or text[i - 1] == "."):
            i -= 1
        value = float(text[:i])
        unit = text[i:].strip() or "ft"
        return value, unit
    except ValueError:
        return None


class CalibrationTool(Tool):
    tool_id = "calibrate"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._start: tuple[float, float] | None = None

    def on_press(self, pdf_point: tuple[float, float]) -> None:
        self._start = pdf_point

    def on_move(self, pdf_point: tuple[float, float]) -> None:
        if self._start is None:
            return
        from app.models.markup import MarkupObject

        draft = MarkupObject(
            type="measure_linear",
            page_index=self.context.page_index,
            points=[self._start, pdf_point],
            style=self.context.default_style,
        )
        self.context.preview_callback(draft)

    def on_release(self, pdf_point: tuple[float, float]) -> None:
        self.context.preview_callback(None)
        if self._start is None:
            return
        start = self._start
        self._start = None
        pdf_distance = math.hypot(pdf_point[0] - start[0], pdf_point[1] - start[1])
        if pdf_distance <= 0:
            return

        response = self.context.text_provider("Known real-world distance (e.g. 20 ft)")
        parsed = parse_distance_input(response or "")
        if parsed is None:
            return
        real_distance, unit = parsed

        calibration = Calibration(
            id=str(uuid.uuid4()),
            page_index=self.context.page_index,
            pdf_distance=pdf_distance,
            real_distance=real_distance,
            unit=unit,
        )
        self.context.command_stack.push(CalibrateCommand(self.context.document, calibration))

    def deactivate(self) -> None:
        super().deactivate()
        self._start = None
