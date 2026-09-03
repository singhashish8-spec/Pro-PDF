"""Floating context menu / live style editor for the selected object
(Blueprint v2, Section 7.7, the "Figma feel" — Phase 4)."""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QToolButton,
    QWidget,
)

from app.commands.base import CommandStack
from app.commands.object_commands import DeleteObjectCommand, StyleChangeCommand
from app.models.markup import MarkupObject
from app.models.project import MarkupDocument


def _swatch_style(hex_color: str | None) -> str:
    color = hex_color or "transparent"
    return f"background-color: {color}; border: 1px solid #888;"


class FloatingStylePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FloatingPanel")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self._document: MarkupDocument | None = None
        self._command_stack: CommandStack | None = None
        self._obj_id: str | None = None
        self._on_delete: Callable[[], None] | None = None
        self._build_ui()
        self.hide()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        self._stroke_btn = QPushButton()
        self._stroke_btn.setFixedSize(22, 22)
        self._stroke_btn.setToolTip("Stroke color")
        self._stroke_btn.clicked.connect(self._pick_stroke_color)
        layout.addWidget(self._stroke_btn)

        self._fill_btn = QPushButton()
        self._fill_btn.setFixedSize(22, 22)
        self._fill_btn.setToolTip("Fill color (click to set, right-click to clear)")
        self._fill_btn.clicked.connect(self._pick_fill_color)
        layout.addWidget(self._fill_btn)

        self._clear_fill_btn = QToolButton()
        self._clear_fill_btn.setText("⌀")
        self._clear_fill_btn.setToolTip("Clear fill")
        self._clear_fill_btn.clicked.connect(self._clear_fill_color)
        layout.addWidget(self._clear_fill_btn)

        self._width_spin = QDoubleSpinBox()
        self._width_spin.setRange(0.5, 20.0)
        self._width_spin.setSingleStep(0.5)
        self._width_spin.setToolTip("Line width")
        self._width_spin.valueChanged.connect(self._on_width_changed)
        layout.addWidget(self._width_spin)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(10, 100)
        self._opacity_slider.setFixedWidth(80)
        self._opacity_slider.setToolTip("Opacity")
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        layout.addWidget(self._opacity_slider)

        self._delete_btn = QToolButton()
        self._delete_btn.setText("🗑")
        self._delete_btn.setToolTip("Delete")
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self._delete_btn)

    # -- wiring -----------------------------------------------------------
    def bind(self, document: MarkupDocument, command_stack: CommandStack) -> None:
        self._document = document
        self._command_stack = command_stack

    def show_for(self, obj: MarkupObject, global_pos) -> None:
        self._obj_id = obj.id
        for widget in (self._stroke_btn, self._fill_btn, self._width_spin, self._opacity_slider):
            widget.blockSignals(True)
        self._stroke_btn.setStyleSheet(_swatch_style(obj.style.stroke_color))
        self._fill_btn.setStyleSheet(_swatch_style(obj.style.fill_color))
        self._width_spin.setValue(obj.style.line_width)
        self._opacity_slider.setValue(round(obj.style.opacity * 100))
        for widget in (self._stroke_btn, self._fill_btn, self._width_spin, self._opacity_slider):
            widget.blockSignals(False)
        self.move(global_pos)
        self.show()
        self.raise_()

    def hide_panel(self) -> None:
        self._obj_id = None
        self.hide()

    # -- style changes -----------------------------------------------------
    def _current_obj(self) -> MarkupObject | None:
        if self._document is None or self._obj_id is None:
            return None
        return self._document.get(self._obj_id)

    def _push_style_change(self, field: str, new_value) -> None:
        obj = self._current_obj()
        if obj is None or self._command_stack is None:
            return
        old_value = getattr(obj.style, field)
        if old_value == new_value:
            return
        self._command_stack.push(
            StyleChangeCommand(self._document, obj.id, {field: old_value}, {field: new_value})
        )

    def _pick_stroke_color(self) -> None:
        obj = self._current_obj()
        if obj is None:
            return
        initial = QColor(obj.style.stroke_color or "#000000")
        color = QColorDialog.getColor(initial, self, "Stroke color")
        if color.isValid():
            self._push_style_change("stroke_color", color.name())
            self._stroke_btn.setStyleSheet(_swatch_style(color.name()))

    def _pick_fill_color(self) -> None:
        obj = self._current_obj()
        if obj is None:
            return
        initial = QColor(obj.style.fill_color or "#FFFFFF")
        color = QColorDialog.getColor(initial, self, "Fill color")
        if color.isValid():
            self._push_style_change("fill_color", color.name())
            self._fill_btn.setStyleSheet(_swatch_style(color.name()))

    def _clear_fill_color(self) -> None:
        self._push_style_change("fill_color", None)
        self._fill_btn.setStyleSheet(_swatch_style(None))

    def _on_width_changed(self, value: float) -> None:
        self._push_style_change("line_width", value)

    def _on_opacity_changed(self, value: int) -> None:
        self._push_style_change("opacity", value / 100.0)

    def _on_delete_clicked(self) -> None:
        obj = self._current_obj()
        if obj is not None and self._command_stack is not None:
            self._command_stack.push(DeleteObjectCommand(self._document, obj))
        self.hide_panel()
        if self._on_delete is not None:
            self._on_delete()

    def set_on_delete(self, callback: Callable[[], None]) -> None:
        self._on_delete = callback
