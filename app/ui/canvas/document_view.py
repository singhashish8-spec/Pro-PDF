"""Composite widget wiring PDFDocument + MarkupDocument + CommandStack to the
Glass Layer canvas (Blueprint v2, Phase 2)."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
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
from app.tools.arrow import ArrowTool
from app.tools.base import Tool, ToolContext
from app.tools.callout import CalloutTool
from app.tools.cloud import CloudTool
from app.tools.ellipse import EllipseTool
from app.tools.eraser import EraserTool
from app.tools.highlighter import HighlighterTool
from app.tools.note import NoteTool
from app.tools.pen import PenTool
from app.tools.rectangle import RectangleTool
from app.tools.select_tool import SelectTool
from app.tools.squiggly import SquigglyTool
from app.tools.stamp import STAMP_PRESETS, StampTool
from app.tools.strikeout import StrikeoutTool
from app.tools.textbox import TextBoxTool
from app.tools.underline import UnderlineTool
from app.ui.canvas.glass_scene import GlassScene
from app.ui.canvas.pdf_view import PdfGraphicsView

_DRAFTING_TOOLS = [
    ("Select", SelectTool, "S"),
    ("Rectangle", RectangleTool, "R"),
    ("Ellipse", EllipseTool, "O"),
    ("Arrow", ArrowTool, "A"),
    ("Pen", PenTool, "P"),
    ("Highlight", HighlighterTool, "H"),
    ("Underline", UnderlineTool, "U"),
    ("Strikeout", StrikeoutTool, "K"),
    ("Squiggly", SquigglyTool, "G"),
    ("Note", NoteTool, "N"),
    ("Stamp", StampTool, "M"),
    ("Text", TextBoxTool, "T"),
    ("Callout", CalloutTool, "C"),
    ("Cloud", CloudTool, "L"),
    ("Eraser", EraserTool, "E"),
]


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
        self._build_tool_palette()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._toolbar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._tool_palette)
        body.addWidget(self.view, 1)
        layout.addLayout(body, 1)

        self.markup_document.add_listener(self._refresh_markups)
        self.command_stack.add_listener(self._on_stack_changed)

        self._select_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._select_shortcut.activated.connect(self._on_escape)
        self._delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        self._delete_shortcut.activated.connect(self._on_delete_key)
        self._backspace_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self)
        self._backspace_shortcut.activated.connect(self._on_delete_key)
        self._finish_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        self._finish_shortcut.activated.connect(self._on_finish_key)
        self._finish_shortcut2 = QShortcut(QKeySequence(Qt.Key.Key_Enter), self)
        self._finish_shortcut2.activated.connect(self._on_finish_key)

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

    def _build_tool_palette(self) -> None:
        self._tool_palette = QWidget()
        self._tool_palette.setObjectName("RightPanel")
        self._tool_palette.setFixedWidth(56)
        column = QVBoxLayout(self._tool_palette)
        column.setContentsMargins(4, 4, 4, 4)
        column.setSpacing(2)

        self._tool_buttons: dict[type, QToolButton] = {}
        group = QButtonGroup(self._tool_palette)
        group.setExclusive(True)
        for label, tool_cls, shortcut in _DRAFTING_TOOLS:
            btn = QToolButton()
            btn.setText(label[:2])
            btn.setToolTip(f"{label} ({shortcut})")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked, tc=tool_cls: self.select_tool(tc))
            column.addWidget(btn)
            group.addButton(btn)
            self._tool_buttons[tool_cls] = btn
        column.addStretch(1)

        self._stamp_preset_combo = QComboBox()
        self._stamp_preset_combo.addItems(STAMP_PRESETS)
        self._stamp_preset_combo.setToolTip("Stamp preset")
        column.addWidget(self._stamp_preset_combo)

    def select_tool(self, tool_cls: type[Tool]) -> None:
        btn = self._tool_buttons.get(tool_cls)
        if btn is not None:
            btn.setChecked(True)
        kwargs = {}
        if tool_cls is StampTool:
            kwargs["preset"] = self._stamp_preset_combo.currentText()
        self.activate_tool(tool_cls, **kwargs)

    def _on_escape(self) -> None:
        if isinstance(self._active_tool, CloudTool):
            self._active_tool.cancel()
        self.select_tool(SelectTool)

    def _on_finish_key(self) -> None:
        if isinstance(self._active_tool, CloudTool):
            self._active_tool.finish()

    def _on_delete_key(self) -> None:
        if isinstance(self._active_tool, SelectTool):
            self._active_tool.delete_selected()

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
            self.select_tool(SelectTool)
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
        from app.core.pdf_document import BASE_DPI_SCALE

        effective_scale = self.view.zoom * BASE_DPI_SCALE
        self.scene.set_page_image(image, effective_scale)
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

    def activate_tool(self, tool_cls: type[Tool], **kwargs) -> Tool:
        """Constructs `tool_cls` with a fresh ToolContext (current page) and activates it."""
        tool = tool_cls(self.make_tool_context(), **kwargs)
        self.set_active_tool(tool)
        return tool

    @property
    def active_tool(self) -> Tool | None:
        return self._active_tool

    def make_tool_context(self) -> ToolContext:
        from app.models.markup import Style

        return ToolContext(
            document=self.markup_document,
            command_stack=self.command_stack,
            page_index=self._page_index,
            default_style=Style(),
            pdf=self.pdf,
            text_provider=self.prompt_for_text,
            preview_callback=self.scene.set_preview,
        )

    def prompt_for_text(self, title: str) -> str | None:
        from PyQt6.QtWidgets import QInputDialog

        text, ok = QInputDialog.getMultiLineText(self, title, "Text:")
        return text if ok else None

    def _on_scene_pressed(self, x: float, y: float) -> None:
        if self._active_tool:
            self._active_tool.on_press(self.scene.scene_point_to_pdf(x, y))

    def _on_scene_moved(self, x: float, y: float) -> None:
        if self._active_tool:
            self._active_tool.on_move(self.scene.scene_point_to_pdf(x, y))

    def _on_scene_released(self, x: float, y: float) -> None:
        if self._active_tool:
            self._active_tool.on_release(self.scene.scene_point_to_pdf(x, y))
