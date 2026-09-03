"""Small geometry helpers shared by tools (hit-testing, bounding boxes)."""

from __future__ import annotations

import math


def bbox_of(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def point_in_bbox(point: tuple[float, float], bbox: tuple[float, float, float, float], margin: float = 4.0) -> bool:
    x, y = point
    x0, y0, x1, y1 = bbox
    return (x0 - margin) <= x <= (x1 + margin) and (y0 - margin) <= y <= (y1 + margin)


def translate_points(
    points: list[tuple[float, float]], dx: float, dy: float
) -> list[tuple[float, float]]:
    return [(x + dx, y + dy) for x, y in points]


def arrowhead_wings(
    from_pt: tuple[float, float], to_pt: tuple[float, float], size: float = 10.0, angle_deg: float = 25.0
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Two points forming the arrowhead's wings at `to_pt`, pointing back toward `from_pt`."""
    dx, dy = to_pt[0] - from_pt[0], to_pt[1] - from_pt[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    angle = math.radians(angle_deg)

    def _wing(rot: float) -> tuple[float, float]:
        rx = ux * math.cos(rot) - uy * math.sin(rot)
        ry = ux * math.sin(rot) + uy * math.cos(rot)
        return (to_pt[0] - rx * size, to_pt[1] - ry * size)

    return _wing(angle), _wing(-angle)


def wavy_points(x0: float, x1: float, y: float, amplitude: float = 2.0, wavelength: float = 6.0) -> list[tuple[float, float]]:
    """A squiggly-underline polyline between x0 and x1 at height y."""
    if x1 < x0:
        x0, x1 = x1, x0
    span = max(x1 - x0, 0.01)
    steps = max(int(span / (wavelength / 2)), 2)
    points = []
    for i in range(steps + 1):
        x = x0 + span * i / steps
        y_off = amplitude if i % 2 == 0 else -amplitude
        points.append((x, y + y_off))
    return points


def rect_intersection(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> tuple[float, float, float, float] | None:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x0 >= x1 or y0 >= y1:
        return None
    return (x0, y0, x1, y1)
