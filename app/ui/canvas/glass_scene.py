"""The Glass Layer: a transparent QGraphicsScene rendered on top of the
static page image (Blueprint v2, Section 6.1). Nothing is drawn directly
onto the PDF here — this is the working document until save/export.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene

from app.core.coordinates import pdf_to_scene, scene_to_pdf
from app.models.markup import MarkupObject
from app.ui.canvas.markup_items import build_graphics_item


class GlassScene(QGraphicsScene):
    def __init__(self) -> None:
        super().__init__()
        self._background_item = QGraphicsPixmapItem()
        self._background_item.setZValue(-1000)
        self.addItem(self._background_item)
        self._markup_items: dict[str, object] = {}
        self._preview_item = None
        self.scale_factor: float = 1.0

    def set_page_image(self, image, scale_factor: float) -> None:
        self.scale_factor = scale_factor
        pixmap = QPixmap.fromImage(image)
        self._background_item.setPixmap(pixmap)
        self.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))

    def rebuild_markups(self, objects: list[MarkupObject]) -> None:
        for item in list(self._markup_items.values()):
            self.removeItem(item)
        self._markup_items.clear()
        for obj in objects:
            item = build_graphics_item(obj, self.scale_factor)
            if item is not None:
                self.addItem(item)
                self._markup_items[obj.id] = item

    def set_preview(self, obj: MarkupObject | None) -> None:
        if self._preview_item is not None:
            self.removeItem(self._preview_item)
            self._preview_item = None
        if obj is not None:
            item = build_graphics_item(obj, self.scale_factor)
            if item is not None:
                item.setOpacity(max(item.opacity(), 0.6))
                self.addItem(item)
                self._preview_item = item

    def scene_point_to_pdf(self, x: float, y: float):
        return scene_to_pdf((x, y), self.scale_factor)

    def pdf_point_to_scene(self, x: float, y: float):
        return pdf_to_scene((x, y), self.scale_factor)
