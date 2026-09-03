"""Bakes MarkupObjects into `fitz` drawing calls (Blueprint v2, Section 6.4).

Still part of app/core — the fitz-only-here rule (Section 5) is about the
module boundary, not a single file. New markup types get a bake function
here as their tool is implemented (Phases 3, 5, 7).
"""

from __future__ import annotations

import pymupdf as fitz

from app.models.markup import MarkupObject


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


def _bake_highlight(shape: "fitz.Shape", obj: MarkupObject) -> None:
    (x0, y0), (x1, y1) = obj.points[0], obj.points[1]
    rect = fitz.Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    shape.draw_rect(rect)
    color = _color_to_rgb(obj.style.stroke_color) or (1, 0.9, 0.3)
    shape.finish(color=None, fill=color, fill_opacity=0.4)


def _bake_text(shape: "fitz.Shape", obj: MarkupObject) -> None:
    if not obj.points or not obj.text:
        return
    point = fitz.Point(*obj.points[0])
    color = _color_to_rgb(obj.style.stroke_color) or (0, 0, 0)
    shape.insert_text(point, obj.text, fontsize=obj.style.font_size, color=color)


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
    "arrow": _bake_polyline,
    "pen": _bake_polyline,
    "highlight": _bake_highlight,
    "underline": _bake_polyline,
    "strikeout": _bake_polyline,
    "squiggly": _bake_polyline,
    "cloud": _bake_polyline,
    "textbox": _bake_text,
    "callout": _bake_text,
    "note": _bake_text,
}


def bake_page(page: "fitz.Page", objects: list[MarkupObject]) -> None:
    shape = page.new_shape()
    for obj in objects:
        baker = _BAKERS.get(obj.type)
        if baker is not None:
            baker(shape, obj)
    shape.commit()
