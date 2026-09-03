"""Real-world unit conversion and formatting for the measurement tools
(Blueprint v2, Section 7.2). A Calibration's scale_factor is real-world
units per PDF point (see app/models/project.py)."""

from __future__ import annotations

import math

from app.models.project import Calibration

#: Fallback when no calibration has been set for the page: 1 PDF point = 1 unit.
UNCALIBRATED_UNIT = "pt"


def path_length(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        total += math.hypot(x1 - x0, y1 - y0)
    return total


def polygon_area(points: list[tuple[float, float]]) -> float:
    """Shoelace formula; points need not be closed explicitly."""
    if len(points) < 3:
        return 0.0
    total = 0.0
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        total += x0 * y1 - x1 * y0
    return abs(total) / 2.0


def polygon_perimeter(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    closed = points + [points[0]]
    return path_length(closed)


def to_real_length(pdf_length: float, calibration: Calibration | None) -> tuple[float, str]:
    if calibration is None:
        return pdf_length, UNCALIBRATED_UNIT
    return pdf_length * calibration.scale_factor, calibration.unit


def to_real_area(pdf_area: float, calibration: Calibration | None) -> tuple[float, str]:
    if calibration is None:
        return pdf_area, f"{UNCALIBRATED_UNIT}²"
    return pdf_area * (calibration.scale_factor**2), f"{calibration.unit}²"


def format_measurement(value: float, unit: str) -> str:
    return f"{value:,.2f} {unit}"
