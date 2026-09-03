"""Maps a MarkupObject to a QGraphicsItem for display in the Glass Layer.

Each markup type gets its own small builder function, following the
"one file/function per tool" spirit of Blueprint v2 Section 5 while sharing
the plumbing (coordinate conversion, pen/brush construction) below. New
types are added here as their tool is implemented (Phases 3, 5, 7).
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)

from app.core.coordinates import pdf_to_scene
from app.models.markup import MarkupObject

_DASH_STYLES = {"cloud", "measure_area", "measure_linear", "measure_perimeter"}


def _pen(obj: MarkupObject) -> QPen:
    color = QColor(obj.style.stroke_color)
    pen = QPen(color, max(obj.style.line_width, 0.5))
    pen.setCosmetic(True)
    if obj.type in _DASH_STYLES:
        pen.setStyle(Qt.PenStyle.DashLine)
    return pen


def _brush(obj: MarkupObject) -> QBrush:
    if obj.style.fill_color:
        color = QColor(obj.style.fill_color)
        color.setAlphaF(max(0.0, min(obj.style.opacity, 1.0)))
        return QBrush(color)
    return QBrush(Qt.BrushStyle.NoBrush)


def _scene_points(obj: MarkupObject, scale: float) -> list[QPointF]:
    return [QPointF(*pdf_to_scene(p, scale)) for p in obj.points]


def _bounds_rect(pts: list[QPointF]):
    xs = [p.x() for p in pts]
    ys = [p.y() for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _build_rectangle(obj, scale) -> QGraphicsItem | None:
    pts = _scene_points(obj, scale)
    if len(pts) < 2:
        return None
    x0, y0, x1, y1 = _bounds_rect(pts)
    item = QGraphicsRectItem(x0, y0, x1 - x0, y1 - y0)
    item.setPen(_pen(obj))
    item.setBrush(_brush(obj))
    item.setOpacity(obj.style.opacity)
    return item


def _build_ellipse(obj, scale) -> QGraphicsItem | None:
    pts = _scene_points(obj, scale)
    if len(pts) < 2:
        return None
    x0, y0, x1, y1 = _bounds_rect(pts)
    item = QGraphicsEllipseItem(x0, y0, x1 - x0, y1 - y0)
    item.setPen(_pen(obj))
    item.setBrush(_brush(obj))
    item.setOpacity(obj.style.opacity)
    return item


def _build_line_like(obj, scale) -> QGraphicsItem | None:
    pts = _scene_points(obj, scale)
    if len(pts) < 2:
        return None
    if len(pts) == 2:
        item = QGraphicsLineItem(pts[0].x(), pts[0].y(), pts[1].x(), pts[1].y())
    else:
        path = QPainterPath(pts[0])
        for p in pts[1:]:
            path.lineTo(p)
        item = QGraphicsPathItem(path)
    item.setPen(_pen(obj))
    item.setOpacity(obj.style.opacity)
    return item


def _build_polygon(obj, scale) -> QGraphicsItem | None:
    pts = _scene_points(obj, scale)
    if len(pts) < 3:
        return _build_line_like(obj, scale)
    item = QGraphicsPolygonItem(QPolygonF(pts))
    item.setPen(_pen(obj))
    item.setBrush(_brush(obj))
    item.setOpacity(obj.style.opacity)
    return item


def _build_highlight(obj, scale) -> QGraphicsItem | None:
    pts = _scene_points(obj, scale)
    if len(pts) < 2:
        return None
    x0, y0, x1, y1 = _bounds_rect(pts)
    item = QGraphicsRectItem(x0, y0, x1 - x0, y1 - y0)
    color = QColor(obj.style.stroke_color or "#FFE066")
    color.setAlphaF(0.4)
    item.setBrush(QBrush(color))
    item.setPen(QPen(Qt.PenStyle.NoPen))
    return item


def _build_text(obj, scale) -> QGraphicsItem | None:
    if not obj.points:
        return None
    x, y = pdf_to_scene(obj.points[0], scale)
    item = QGraphicsSimpleTextItem(obj.text or "")
    item.setPos(x, y)
    item.setBrush(QBrush(QColor(obj.style.stroke_color)))
    font = QFont()
    font.setPointSizeF(max(obj.style.font_size, 1.0) * scale / 1.33)
    item.setFont(font)
    return item


_BUILDERS = {
    "rectangle": _build_rectangle,
    "ellipse": _build_ellipse,
    "arrow": _build_line_like,
    "pen": _build_line_like,
    "highlight": _build_highlight,
    "underline": _build_line_like,
    "strikeout": _build_line_like,
    "squiggly": _build_line_like,
    "cloud": _build_polygon,
    "measure_linear": _build_line_like,
    "measure_perimeter": _build_polygon,
    "measure_area": _build_polygon,
    "redaction": _build_rectangle,
    "textbox": _build_text,
    "callout": _build_text,
    "note": _build_text,
}


def build_graphics_item(obj: MarkupObject, scale: float) -> QGraphicsItem | None:
    builder = _BUILDERS.get(obj.type)
    if builder is None:
        return _build_line_like(obj, scale)
    item = builder(obj, scale)
    if item is not None:
        item.setData(0, obj.id)
    return item
