"""QGraphicsView with pan/zoom for the Glass Layer (Blueprint v2, Phase 2)."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QPainter, QWheelEvent
from PyQt6.QtWidgets import QGraphicsView

MIN_ZOOM = 0.1
MAX_ZOOM = 8.0


class PdfGraphicsView(QGraphicsView):
    zoom_requested = pyqtSignal(float)  # emits the new absolute zoom level
    scene_pressed = pyqtSignal(float, float)
    scene_moved = pyqtSignal(float, float)
    scene_released = pyqtSignal(float, float)

    def __init__(self) -> None:
        super().__init__()
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._zoom = 1.0
        self.drawing_mode = False

    @property
    def zoom(self) -> float:
        return self._zoom

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))

    def set_drawing_mode(self, enabled: bool) -> None:
        self.drawing_mode = enabled
        self.setDragMode(
            QGraphicsView.DragMode.NoDrag if enabled else QGraphicsView.DragMode.ScrollHandDrag
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.drawing_mode and event.button() == Qt.MouseButton.LeftButton:
            pt = self.mapToScene(event.position().toPoint())
            self.scene_pressed.emit(pt.x(), pt.y())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.drawing_mode:
            pt = self.mapToScene(event.position().toPoint())
            self.scene_moved.emit(pt.x(), pt.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.drawing_mode and event.button() == Qt.MouseButton.LeftButton:
            pt = self.mapToScene(event.position().toPoint())
            self.scene_released.emit(pt.x(), pt.y())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.15 if delta > 0 else 1 / 1.15
            new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, self._zoom * factor))
            if new_zoom != self._zoom:
                self.zoom_requested.emit(new_zoom)
            event.accept()
        else:
            super().wheelEvent(event)
