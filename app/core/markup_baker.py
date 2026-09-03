"""Bakes MarkupObjects into `fitz` drawing calls (Blueprint v2, Section 6.4).

Still part of app/core — the fitz-only-here rule (Section 5) is about the
module boundary, not a single file. New markup types get a bake function
here as their tool is implemented (Phases 3, 5, 7).
"""

from __future__ import annotations

import pymupdf as fitz

from app.models.markup import MarkupObject
from app.tools.geometry import arrowhead_wings


def _color_to_rgb(hex_color: str | None) -> tuple[float, float, float] | None:
    if not hex_color:
        return None
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return None
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return (r, g, b)


def _bake_rectangle(shape: "fitz.Shape", obj: MarkupObject) -> None:
    (x0, y0), (x1, y1) = obj.points[0], obj.points[1]
    rect = fitz.Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    shape.draw_rect(rect)
    _finish(shape, obj)


def _bake_ellipse(shape: "fitz.Shape", obj: MarkupObject) -> None:
    (x0, y0), (x1, y1) = obj.points[0], obj.points[1]
    rect = fitz.Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    shape.draw_oval(rect)
    _finish(shape, obj)


def _bake_polyline(shape: "fitz.Shape", obj: MarkupObject) -> None:
    points = [fitz.Point(x, y) for x, y in obj.points]
    if len(points) >= 2:
        shape.draw_polyline(points)
    _finish(shape, obj, fill=False)


def _bake_arrow(shape: "fitz.Shape", obj: MarkupObject) -> None:
    if len(obj.points) < 2:
        return
    start, end = obj.points[0], obj.points[1]
    wing1, wing2 = arrowhead_wings(start, end, size=10.0)
    shape.draw_polyline([fitz.Point(*start), fitz.Point(*end)])
    shape.draw_polyline([fitz.Point(*wing1), fitz.Point(*end), fitz.Point(*wing2)])
    _finish(shape, obj, fill=False)


def _bake_highlight(shape: "fitz.Shape", obj: MarkupObject) -> None:
    (x0, y0), (x1, y1) = obj.points[0], obj.points[1]
    rect = fitz.Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    shape.draw_rect(rect)
    color = _color_to_rgb(obj.style.stroke_color) or (1, 0.9, 0.3)
    shape.finish(color=None, fill=color, fill_opacity=0.4)


def _bake_callout(shape: "fitz.Shape", obj: MarkupObject) -> None:
    if len(obj.points) < 2:
        return
    shape.draw_polyline([fitz.Point(*obj.points[0]), fitz.Point(*obj.points[1])])
    _finish(shape, obj, fill=False)
    if obj.text:
        color = _color_to_rgb(obj.style.stroke_color) or (0, 0, 0)
        shape.insert_text(fitz.Point(*obj.points[1]), obj.text, fontsize=obj.style.font_size, color=color)


def _bake_measurement_line(shape: "fitz.Shape", obj: MarkupObject) -> None:
    _bake_polyline(shape, obj)
    if obj.text and len(obj.points) >= 2:
        mid = ((obj.points[0][0] + obj.points[-1][0]) / 2, (obj.points[0][1] + obj.points[-1][1]) / 2)
        color = _color_to_rgb(obj.style.stroke_color) or (0, 0, 0)
        shape.insert_text(fitz.Point(*mid), obj.text, fontsize=obj.style.font_size, color=color)


def _bake_measurement_polygon(shape: "fitz.Shape", obj: MarkupObject) -> None:
    if len(obj.points) < 3:
        return
    points = [fitz.Point(x, y) for x, y in obj.points] + [fitz.Point(*obj.points[0])]
    shape.draw_polyline(points)
    _finish(shape, obj, fill=obj.type == "measure_area")
    if obj.text:
        cx = sum(p[0] for p in obj.points) / len(obj.points)
        cy = sum(p[1] for p in obj.points) / len(obj.points)
        color = _color_to_rgb(obj.style.stroke_color) or (0, 0, 0)
        shape.insert_text(fitz.Point(cx, cy), obj.text, fontsize=obj.style.font_size, color=color)


def _bake_count_marker(shape: "fitz.Shape", obj: MarkupObject) -> None:
    if not obj.points:
        return
    x, y = obj.points[0]
    radius = 9.0
    color = _color_to_rgb(obj.style.stroke_color) or (0.91, 0.35, 0.05)
    shape.draw_circle(fitz.Point(x, y), radius)
    shape.finish(color=color, fill=color, fill_opacity=0.35, width=1.5)
    if obj.text:
        shape.insert_text(fitz.Point(x - radius / 2, y + radius / 3), obj.text, fontsize=9, color=color)


def _bake_text(shape: "fitz.Shape", obj: MarkupObject) -> None:
    if not obj.points or not obj.text:
        return
    point = fitz.Point(*obj.points[0])
    color = _color_to_rgb(obj.style.stroke_color) or (0, 0, 0)
    shape.insert_text(point, obj.text, fontsize=obj.style.font_size, color=color)


def _bake_stamp(shape: "fitz.Shape", obj: MarkupObject) -> None:
    if not obj.points:
        return
    x, y = obj.points[0]
    lines = (obj.text or "STAMP").split("\n")
    width = max((len(line) for line in lines), default=6) * obj.style.font_size * 0.6 + 12
    height = len(lines) * (obj.style.font_size + 4) + 8
    rect = fitz.Rect(x, y, x + width, y + height)
    color = _color_to_rgb(obj.style.stroke_color) or (0.8, 0, 0)
    shape.draw_rect(rect)
    shape.finish(color=color, width=1.5)
    for i, line in enumerate(lines):
        shape.insert_text(
            fitz.Point(x + 6, y + 6 + (i + 1) * (obj.style.font_size + 2)),
            line,
            fontsize=obj.style.font_size,
            color=color,
        )


def _finish(shape: "fitz.Shape", obj: MarkupObject, fill: bool = True) -> None:
    color = _color_to_rgb(obj.style.stroke_color) or (0, 0, 0)
    fill_color = _color_to_rgb(obj.style.fill_color) if fill else None
    shape.finish(
        color=color,
        fill=fill_color,
        width=obj.style.line_width,
        fill_opacity=obj.style.opacity,
        stroke_opacity=obj.style.opacity,
    )


_BAKERS = {
    "rectangle": _bake_rectangle,
    "ellipse": _bake_ellipse,
    "arrow": _bake_arrow,
    "pen": _bake_polyline,
    "highlight": _bake_highlight,
    "underline": _bake_polyline,
    "strikeout": _bake_polyline,
    "squiggly": _bake_polyline,
    "cloud": _bake_polyline,
    "measure_linear": _bake_measurement_line,
    "measure_perimeter": _bake_measurement_polygon,
    "measure_area": _bake_measurement_polygon,
    "measure_diameter": _bake_measurement_line,
    "measure_radius": _bake_measurement_line,
    "measure_count": _bake_count_marker,
    "textbox": _bake_text,
    "callout": _bake_callout,
    "note": _bake_text,
    "stamp": _bake_stamp,
}


def bake_page(page: "fitz.Page", objects: list[MarkupObject]) -> None:
    shape = page.new_shape()
    for obj in objects:
        baker = _BAKERS.get(obj.type)
        if baker is not None:
            baker(shape, obj)
    shape.commit()
