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
    QGraphicsItemGroup,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)

from app.core.coordinates import pdf_to_scene
from app.models.markup import MarkupObject
from app.tools.geometry import arrowhead_wings

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


def _build_arrow(obj, scale) -> QGraphicsItem | None:
    if len(obj.points) < 2:
        return None
    wing1, wing2 = arrowhead_wings(obj.points[0], obj.points[1], size=10.0 / max(scale, 0.01))
    path_points = [obj.points[0], obj.points[1], wing1, obj.points[1], wing2]
    scene_pts = [QPointF(*pdf_to_scene(p, scale)) for p in path_points]
    path = QPainterPath(scene_pts[0])
    for p in scene_pts[1:]:
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


def _build_callout(obj, scale) -> QGraphicsItem | None:
    if len(obj.points) < 2:
        return _build_text(obj, scale)
    line_item = _build_line_like(obj, scale)
    text_item = QGraphicsSimpleTextItem(obj.text or "")
    tx, ty = pdf_to_scene(obj.points[1], scale)
    text_item.setPos(tx, ty)
    text_item.setBrush(QBrush(QColor(obj.style.stroke_color)))
    font = QFont()
    font.setPointSizeF(max(obj.style.font_size, 1.0) * scale / 1.33)
    text_item.setFont(font)
    group = QGraphicsItemGroup()
    if line_item is not None:
        group.addToGroup(line_item)
    group.addToGroup(text_item)
    return group


def _label_item(text: str, pos: QPointF, obj: MarkupObject, scale: float) -> QGraphicsSimpleTextItem:
    item = QGraphicsSimpleTextItem(text)
    item.setPos(pos)
    item.setBrush(QBrush(QColor(obj.style.stroke_color)))
    font = QFont()
    font.setPointSizeF(max(obj.style.font_size, 1.0) * scale / 1.33)
    item.setFont(font)
    return item


def _build_measurement_line(obj, scale) -> QGraphicsItem | None:
    line_item = _build_line_like(obj, scale)
    if line_item is None or not obj.text:
        return line_item
    mid = ((obj.points[0][0] + obj.points[-1][0]) / 2, (obj.points[0][1] + obj.points[-1][1]) / 2)
    label = _label_item(obj.text, QPointF(*pdf_to_scene(mid, scale)), obj, scale)
    group = QGraphicsItemGroup()
    group.addToGroup(line_item)
    group.addToGroup(label)
    return group


def _build_measurement_polygon(obj, scale) -> QGraphicsItem | None:
    poly_item = _build_polygon(obj, scale)
    if poly_item is None or not obj.text or len(obj.points) < 3:
        return poly_item
    cx = sum(p[0] for p in obj.points) / len(obj.points)
    cy = sum(p[1] for p in obj.points) / len(obj.points)
    label = _label_item(obj.text, QPointF(*pdf_to_scene((cx, cy), scale)), obj, scale)
    group = QGraphicsItemGroup()
    group.addToGroup(poly_item)
    group.addToGroup(label)
    return group


def _build_count_marker(obj, scale) -> QGraphicsItem | None:
    if not obj.points:
        return None
    x, y = pdf_to_scene(obj.points[0], scale)
    radius = 9.0
    circle = QGraphicsEllipseItem(x - radius, y - radius, radius * 2, radius * 2)
    color = QColor(obj.style.stroke_color or "#E8590C")
    circle.setPen(QPen(color, 1.5))
    circle.setBrush(QBrush(color.lighter(160)))
    label = QGraphicsSimpleTextItem(obj.text or "")
    label.setPos(x - radius / 2, y - radius / 1.5)
    label.setBrush(QBrush(color.darker(150)))
    font = QFont()
    font.setPointSizeF(9)
    label.setFont(font)
    group = QGraphicsItemGroup()
    group.addToGroup(circle)
    group.addToGroup(label)
    return group


def _build_stamp(obj, scale) -> QGraphicsItem | None:
    if not obj.points:
        return None
    lines = (obj.text or "STAMP").split("\n")
    font_size = max(obj.style.font_size, 1.0)
    width_chars = max((len(line) for line in lines), default=6)
    width_pdf = width_chars * font_size * 0.6 + 12
    height_pdf = len(lines) * (font_size + 4) + 8
    x, y = obj.points[0]
    x0, y0 = pdf_to_scene((x, y), scale)
    x1, y1 = pdf_to_scene((x + width_pdf, y + height_pdf), scale)

    group = QGraphicsItemGroup()
    rect_item = QGraphicsRectItem(x0, y0, x1 - x0, y1 - y0)
    color = QColor(obj.style.stroke_color or "#CC0000")
    rect_item.setPen(QPen(color, 1.5))
    group.addToGroup(rect_item)

    text_item = QGraphicsSimpleTextItem("\n".join(lines))
    text_item.setPos(x0 + 4 * scale, y0 + 2 * scale)
    text_item.setBrush(QBrush(color))
    font = QFont()
    font.setPointSizeF(font_size * scale / 1.33)
    text_item.setFont(font)
    group.addToGroup(text_item)
    return group


_BUILDERS = {
    "rectangle": _build_rectangle,
    "ellipse": _build_ellipse,
    "arrow": _build_arrow,
    "pen": _build_line_like,
    "highlight": _build_highlight,
    "underline": _build_line_like,
    "strikeout": _build_line_like,
    "squiggly": _build_line_like,
    "cloud": _build_polygon,
    "measure_linear": _build_measurement_line,
    "measure_perimeter": _build_measurement_polygon,
    "measure_area": _build_measurement_polygon,
    "measure_diameter": _build_measurement_line,
    "measure_radius": _build_measurement_line,
    "measure_count": _build_count_marker,
    "redaction": _build_rectangle,
    "textbox": _build_text,
    "callout": _build_callout,
    "note": _build_text,
    "stamp": _build_stamp,
}


def build_graphics_item(obj: MarkupObject, scale: float) -> QGraphicsItem | None:
    builder = _BUILDERS.get(obj.type)
    if builder is None:
        return _build_line_like(obj, scale)
    item = builder(obj, scale)
    if item is not None:
        item.setData(0, obj.id)
    return item
