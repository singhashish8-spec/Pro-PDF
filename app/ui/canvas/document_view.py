"""Composite widget wiring PDFDocument + MarkupDocument + CommandStack to the
Glass Layer canvas (Blueprint v2, Phase 2)."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.commands.base import CommandStack
from app.core.pdf_document import PDFDocument
from app.models.markup import MarkupObject
from app.models.project import MarkupDocument
from app.persistence import autosave
from app.tools.base import Tool, ToolContext
from app.ui.canvas.glass_scene import GlassScene
from app.ui.canvas.pdf_view import PdfGraphicsView


class DocumentView(QWidget):
    undo_state_changed = pyqtSignal(bool, bool)  # can_undo, can_redo
    page_changed = pyqtSignal(int, int)  # 0-based index, page_count

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pdf = PDFDocument()
        self.markup_document = MarkupDocument()
        self.command_stack = CommandStack()
        self._page_index = 0
        self._active_tool: Tool | None = None
        self._suspend_autosave = False

        self.scene = GlassScene()
        self.view = PdfGraphicsView()
        self.view.setScene(self.scene)
        self.view.zoom_requested.connect(self._on_zoom_requested)
        self.view.scene_pressed.connect(self._on_scene_pressed)
        self.view.scene_moved.connect(self._on_scene_moved)
        self.view.scene_released.connect(self._on_scene_released)

        self._build_toolbar()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._toolbar)
        layout.addWidget(self.view, 1)

        self.markup_document.add_listener(self._refresh_markups)
        self.command_stack.add_listener(self._on_stack_changed)

    def _build_toolbar(self) -> None:
        self._toolbar = QWidget()
        self._toolbar.setObjectName("TopBar")
        bar = QHBoxLayout(self._toolbar)
        bar.setContentsMargins(8, 4, 8, 4)

        prev_btn = QToolButton()
        prev_btn.setText("‹")
        prev_btn.clicked.connect(lambda: self.go_to_page(self._page_index - 1))
        bar.addWidget(prev_btn)

        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(1)
        self._page_spin.valueChanged.connect(lambda v: self.go_to_page(v - 1))
        bar.addWidget(self._page_spin)

        self._page_count_label = QLabel("/ 0")
        bar.addWidget(self._page_count_label)

        next_btn = QToolButton()
        next_btn.setText("›")
        next_btn.clicked.connect(lambda: self.go_to_page(self._page_index + 1))
        bar.addWidget(next_btn)

        bar.addStretch(1)

        zoom_out = QToolButton()
        zoom_out.setText("−")
        zoom_out.clicked.connect(lambda: self._on_zoom_requested(self.view.zoom / 1.15))
        bar.addWidget(zoom_out)

        self._zoom_label = QLabel("100%")
        bar.addWidget(self._zoom_label)

        zoom_in = QToolButton()
        zoom_in.setText("+")
        zoom_in.clicked.connect(lambda: self._on_zoom_requested(self.view.zoom * 1.15))
        bar.addWidget(zoom_in)

    # -- loading -----------------------------------------------------------
    def load(self, path: str, password: str | None = None) -> bool:
        """Opens the PDF. Returns True if a crash-recovery journal exists and
        wasn't auto-applied; caller (MainWindow) should prompt the user."""
        has_journal = autosave.journal_exists(path)
        self._suspend_autosave = True
        try:
            self.pdf.open(path, password=password)
            self.command_stack.clear()
            self.markup_document.replace_all([])
            self._page_spin.blockSignals(True)
            self._page_spin.setMaximum(max(self.pdf.page_count, 1))
            self._page_spin.blockSignals(False)
            self._page_count_label.setText(f"/ {self.pdf.page_count}")
            self.go_to_page(0)
        finally:
            self._suspend_autosave = False
        return has_journal

    def recover_from_journal(self) -> None:
        if not self.pdf.path:
            return
        data = autosave.read_journal(self.pdf.path)
        if data is not None:
            self.markup_document.replace_all([MarkupObject.from_dict(d) for d in data])

    def discard_journal(self) -> None:
        if self.pdf.path:
            autosave.clear_journal(self.pdf.path)

    def _write_autosave(self) -> None:
        if self.pdf.path and not self._suspend_autosave:
            autosave.write_journal(self.pdf.path, self.markup_document.to_journal())

    def go_to_page(self, index: int) -> None:
        if not self.pdf.is_open:
            return
        index = max(0, min(index, self.pdf.page_count - 1))
        self._page_index = index
        self._page_spin.blockSignals(True)
        self._page_spin.setValue(index + 1)
        self._page_spin.blockSignals(False)
        self._render_current_page()
        self.page_changed.emit(index, self.pdf.page_count)

    @property
    def current_page(self) -> int:
        return self._page_index

    # -- zoom -----------------------------------------------------------
    def _on_zoom_requested(self, zoom: float) -> None:
        self.view.set_zoom(zoom)
        self._zoom_label.setText(f"{round(zoom * 100)}%")
        self._render_current_page()

    def _render_current_page(self) -> None:
        if not self.pdf.is_open:
            return
        image = self.pdf.render_page(self._page_index, self.view.zoom)
        page_height = self.pdf.page_size(self._page_index)[1]
        from app.core.pdf_document import BASE_DPI_SCALE

        effective_scale = self.view.zoom * BASE_DPI_SCALE
        self.scene.set_page_image(image, page_height, effective_scale)
        self._refresh_markups()

    def _refresh_markups(self) -> None:
        if not self.pdf.is_open:
            return
        objects = self.markup_document.objects_on_page(self._page_index)
        self.scene.rebuild_markups(objects)

    def _on_stack_changed(self) -> None:
        self.undo_state_changed.emit(self.command_stack.can_undo, self.command_stack.can_redo)
        self._write_autosave()

    # -- tools -----------------------------------------------------------
    def set_active_tool(self, tool: Tool | None) -> None:
        if self._active_tool is not None:
            self._active_tool.deactivate()
        self._active_tool = tool
        self.view.set_drawing_mode(tool is not None)
        if tool is not None:
            tool.activate()

    def make_tool_context(self) -> ToolContext:
        from app.models.markup import Style

        return ToolContext(
            document=self.markup_document,
            command_stack=self.command_stack,
            page_index=self._page_index,
            default_style=Style(),
        )

    def _on_scene_pressed(self, x: float, y: float) -> None:
        if self._active_tool:
            self._active_tool.on_press(self.scene.scene_point_to_pdf(x, y))

    def _on_scene_moved(self, x: float, y: float) -> None:
        if self._active_tool:
            self._active_tool.on_move(self.scene.scene_point_to_pdf(x, y))

    def _on_scene_released(self, x: float, y: float) -> None:
        if self._active_tool:
            self._active_tool.on_release(self.scene.scene_point_to_pdf(x, y))
