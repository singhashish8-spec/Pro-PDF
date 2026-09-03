"""The Glass Layer: a transparent QGraphicsScene rendered on top of the
static page image (Blueprint v2, Section 6.1). Nothing is drawn directly
onto the PDF here — this is the working document until save/export.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene

from app.core.coordinates import pdf_to_scene
from app.models.markup import MarkupObject
from app.ui.canvas.markup_items import build_graphics_item


class GlassScene(QGraphicsScene):
    def __init__(self) -> None:
        super().__init__()
        self._background_item = QGraphicsPixmapItem()
        self._background_item.setZValue(-1000)
        self.addItem(self._background_item)
        self._markup_items: dict[str, object] = {}
        self.page_height: float = 0.0
        self.scale_factor: float = 1.0

    def set_page_image(self, image, page_height: float, scale_factor: float) -> None:
        self.page_height = page_height
        self.scale_factor = scale_factor
        pixmap = QPixmap.fromImage(image)
        self._background_item.setPixmap(pixmap)
        self.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))

    def rebuild_markups(self, objects: list[MarkupObject]) -> None:
        for item in list(self._markup_items.values()):
            self.removeItem(item)
        self._markup_items.clear()
        for obj in objects:
            item = build_graphics_item(obj, self.page_height, self.scale_factor)
            if item is not None:
                self.addItem(item)
                self._markup_items[obj.id] = item

    def scene_point_to_pdf(self, x: float, y: float):
        from app.core.coordinates import scene_to_pdf

        return scene_to_pdf((x, y), self.page_height, self.scale_factor)

    def pdf_point_to_scene(self, x: float, y: float):
        return pdf_to_scene((x, y), self.page_height, self.scale_factor)
