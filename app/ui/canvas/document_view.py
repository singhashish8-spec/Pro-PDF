"""Composite widget wiring PDFDocument + MarkupDocument + CommandStack to the
Glass Layer canvas (Blueprint v2, Phase 2)."""

from __future__ import annotations

from PyQt6.QtCore import QFileSystemWatcher, Qt, pyqtSignal
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
from app.models.markup import MarkupObject, Style
from app.models.project import MarkupDocument
from app.persistence import autosave, markups_db
from app.tools.arrow import ArrowTool
from app.tools.base import Tool, ToolContext
from app.tools.calibration_tool import CalibrationTool
from app.tools.callout import CalloutTool
from app.tools.cloud import CloudTool
from app.tools.ellipse import EllipseTool
from app.tools.eraser import EraserTool
from app.tools.highlighter import HighlighterTool
from app.tools.measure_area import MeasureAreaTool
from app.tools.measure_count import MeasureCountTool
from app.tools.measure_diameter import MeasureDiameterTool
from app.tools.measure_linear import MeasureLinearTool
from app.tools.measure_perimeter import MeasurePerimeterTool
from app.tools.measure_radius import MeasureRadiusTool
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
from app.ui.panels.command_palette import CommandPalette, PaletteCommand
from app.ui.panels.floating_style_panel import FloatingStylePanel
from app.ui.panels.tool_chest_panel import ToolChestPanel

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

_MEASUREMENT_TOOLS = [
    ("Calibrate", CalibrationTool, "Shift+C"),
    ("Distance", MeasureLinearTool, "D"),
    ("Area", MeasureAreaTool, "Shift+A"),
    ("Perimeter", MeasurePerimeterTool, "Shift+P"),
    ("Diameter", MeasureDiameterTool, "Shift+D"),
    ("Radius", MeasureRadiusTool, "Shift+R"),
    ("Count", MeasureCountTool, "Shift+N"),
]

#: Tools that build up a shape across several clicks, finished with Return/Enter
#: or discarded with Escape (DocumentView._on_finish_key / _on_escape).
_CLICK_TO_BUILD_TOOLS = (CloudTool, MeasureAreaTool, MeasurePerimeterTool)


class DocumentView(QWidget):
    undo_state_changed = pyqtSignal(bool, bool)  # can_undo, can_redo
    page_changed = pyqtSignal(int, int)  # 0-based index, page_count
    markups_changed = pyqtSignal()  # for the Markups List panel
    external_change_detected = pyqtSignal(str)  # file path changed on disk while open

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pdf = PDFDocument()
        self.markup_document = MarkupDocument()
        self.command_stack = CommandStack()
        self._page_index = 0
        self._active_tool: Tool | None = None
        self._suspend_autosave = False
        self._default_style = Style()
        #: Per-page id of the calibration measurement tools should use (Section 7.2).
        self._active_calibration_by_page: dict[int, str] = {}
        self._file_watcher = QFileSystemWatcher(self)
        self._file_watcher.fileChanged.connect(self._on_file_changed_on_disk)
        self._ignore_next_external_change = False

        self.scene = GlassScene()
        self.view = PdfGraphicsView()
        self.view.setScene(self.scene)
        self.view.zoom_requested.connect(self._on_zoom_requested)
        self.view.scene_pressed.connect(self._on_scene_pressed)
        self.view.scene_moved.connect(self._on_scene_moved)
        self.view.scene_released.connect(self._on_scene_released)

        self._floating_panel = FloatingStylePanel(self)
        self._floating_panel.bind(self.markup_document, self.command_stack)
        self._floating_panel.set_on_delete(lambda: self.select_tool(SelectTool))

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

        self.markup_document.add_listener(self._on_markup_document_changed)
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
        self._palette_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self._palette_shortcut.activated.connect(self.open_command_palette)

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

        self._scale_combo = QComboBox()
        self._scale_combo.setToolTip("Active scale for measurement tools on this page")
        self._scale_combo.currentIndexChanged.connect(self._on_scale_combo_changed)
        bar.addWidget(self._scale_combo)

        tool_chest_btn = QToolButton()
        tool_chest_btn.setText("Tool Chest")
        tool_chest_btn.clicked.connect(self.open_tool_chest)
        bar.addWidget(tool_chest_btn)

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
        for label, tool_cls, shortcut in _DRAFTING_TOOLS + _MEASUREMENT_TOOLS:
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
        if tool_cls is not SelectTool:
            self._floating_panel.hide_panel()
        kwargs = {}
        if tool_cls is StampTool:
            kwargs["preset"] = self._stamp_preset_combo.currentText()
        self.activate_tool(tool_cls, **kwargs)

    def _on_escape(self) -> None:
        if isinstance(self._active_tool, _CLICK_TO_BUILD_TOOLS):
            self._active_tool.cancel()
        self.select_tool(SelectTool)

    def _on_finish_key(self) -> None:
        if isinstance(self._active_tool, _CLICK_TO_BUILD_TOOLS):
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
            if self._file_watcher.files():
                self._file_watcher.removePaths(self._file_watcher.files())
            self.pdf.open(path, password=password)
            self._file_watcher.addPath(path)
            self.command_stack.clear()
            self.markup_document.replace_all([])
            self._page_spin.blockSignals(True)
            self._page_spin.setMaximum(max(self.pdf.page_count, 1))
            self._page_spin.blockSignals(False)
            self._page_count_label.setText(f"/ {self.pdf.page_count}")
            self.go_to_page(0)
            self.select_tool(SelectTool)
            self._sync_markups_db()
        finally:
            self._suspend_autosave = False
        return has_journal

    def _on_file_changed_on_disk(self, path: str) -> None:
        if self._ignore_next_external_change:
            self._ignore_next_external_change = False
            return
        self.external_change_detected.emit(path)
        # Some editors replace the file (new inode) rather than writing in place,
        # which drops it from the watch list; re-add it so we keep watching.
        if path not in self._file_watcher.files() and self.pdf.path == path:
            import os

            if os.path.exists(path):
                self._file_watcher.addPath(path)

    def notify_saving(self) -> None:
        """Call right before writing to the open file ourselves, so the
        file-watcher doesn't mistake our own save for an external change."""
        self._ignore_next_external_change = True

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
        self._rebuild_scene_markups()

    def _rebuild_scene_markups(self) -> None:
        if not self.pdf.is_open:
            return
        objects = self.markup_document.objects_on_page(self._page_index)
        self.scene.rebuild_markups(objects)

    def _on_markup_document_changed(self) -> None:
        """Fires for every MarkupDocument state change, whether pushed through
        the CommandStack (undo/redo-able) or applied directly by page
        management (insert/delete/rotate/reorder shifting or dropping
        objects, which isn't itself undoable — see docs/progress.md)."""
        self._rebuild_scene_markups()
        self._write_autosave()
        self.refresh_floating_panel()
        self._refresh_scale_combo()
        self._sync_markups_db()

    def _on_stack_changed(self) -> None:
        self.undo_state_changed.emit(self.command_stack.can_undo, self.command_stack.can_redo)

    def _sync_markups_db(self) -> None:
        if self.pdf.path:
            markups_db.sync_all(self.pdf.path, self.markup_document.all_objects())
            self.markups_changed.emit()

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
        calibration_id = self._active_calibration_by_page.get(self._page_index)
        calibration = self.markup_document.get_calibration(calibration_id) if calibration_id else None
        return ToolContext(
            document=self.markup_document,
            command_stack=self.command_stack,
            page_index=self._page_index,
            default_style=self._default_style,
            pdf=self.pdf,
            text_provider=self.prompt_for_text,
            preview_callback=self.scene.set_preview,
            selection_callback=self._on_selection_changed,
            active_calibration=calibration,
        )

    # -- scale calibration ---------------------------------------------------
    def _refresh_scale_combo(self) -> None:
        calibrations = self.markup_document.calibrations_for_page(self._page_index)
        self._scale_combo.blockSignals(True)
        self._scale_combo.clear()
        self._scale_combo.addItem("No scale", None)
        current_id = self._active_calibration_by_page.get(self._page_index)
        current_row = 0
        for i, cal in enumerate(calibrations, start=1):
            self._scale_combo.addItem(f"{cal.real_distance:g} {cal.unit} = {cal.pdf_distance:.1f} pt", cal.id)
            if cal.id == current_id:
                current_row = i
        if current_row == 0 and calibrations:
            # Newest calibration becomes active automatically.
            current_row = len(calibrations)
            self._active_calibration_by_page[self._page_index] = calibrations[-1].id
        self._scale_combo.setCurrentIndex(current_row)
        self._scale_combo.blockSignals(False)

    def _on_scale_combo_changed(self, index: int) -> None:
        calibration_id = self._scale_combo.itemData(index)
        if calibration_id:
            self._active_calibration_by_page[self._page_index] = calibration_id
        else:
            self._active_calibration_by_page.pop(self._page_index, None)

    # -- tool chest -----------------------------------------------------------
    def open_tool_chest(self) -> None:
        def on_apply(entry: dict) -> None:
            style = entry.get("style") or {}
            for key, value in style.items():
                if hasattr(self._default_style, key):
                    setattr(self._default_style, key, value)
            markup_type = entry.get("markup_type")
            tool_cls = next((tc for label, tc, _ in _DRAFTING_TOOLS + _MEASUREMENT_TOOLS if tc.tool_id == markup_type), None)
            if tool_cls is not None:
                self.select_tool(tool_cls)

        def current_style_provider() -> tuple[str, dict]:
            tool_id = getattr(self._active_tool, "tool_id", "rectangle")
            return tool_id, self._default_style.to_dict()

        panel = ToolChestPanel(on_apply, current_style_provider, self)
        panel.exec()

    def _on_selection_changed(self, obj_id: str | None) -> None:
        if obj_id is None:
            self._floating_panel.hide_panel()
            return
        self._position_floating_panel(obj_id)

    def _position_floating_panel(self, obj_id: str) -> None:
        obj = self.markup_document.get(obj_id)
        if obj is None or len(obj.points) < 1:
            self._floating_panel.hide_panel()
            return
        from app.tools.geometry import bbox_of

        points = obj.points if len(obj.points) >= 2 else [obj.points[0], obj.points[0]]
        x0, y0, x1, y1 = bbox_of(points)
        top_right_scene = self.scene.pdf_point_to_scene(x1, y0)
        view_point = self.view.mapFromScene(*top_right_scene)
        global_point = self.view.viewport().mapToGlobal(view_point)
        self._floating_panel.show_for(obj, global_point)

    def refresh_floating_panel(self) -> None:
        """Re-syncs the floating panel's position/values after a move or style change."""
        if isinstance(self._active_tool, SelectTool) and self._active_tool.selected_id:
            self._position_floating_panel(self._active_tool.selected_id)

    # -- command palette -----------------------------------------------------
    def build_palette_commands(self) -> list[PaletteCommand]:
        commands = [
            PaletteCommand("Select", lambda: self.select_tool(SelectTool), "Tool"),
        ]
        for label, tool_cls, _shortcut in _DRAFTING_TOOLS[1:] + _MEASUREMENT_TOOLS:
            commands.append(PaletteCommand(label, lambda tc=tool_cls: self.select_tool(tc), "Tool"))
        commands += [
            PaletteCommand("Undo", self.command_stack.undo, "Edit"),
            PaletteCommand("Redo", self.command_stack.redo, "Edit"),
            PaletteCommand("Zoom In", lambda: self._on_zoom_requested(self.view.zoom * 1.15), "View"),
            PaletteCommand("Zoom Out", lambda: self._on_zoom_requested(self.view.zoom / 1.15), "View"),
            PaletteCommand("Next Page", lambda: self.go_to_page(self._page_index + 1), "Navigate"),
            PaletteCommand("Previous Page", lambda: self.go_to_page(self._page_index - 1), "Navigate"),
        ]
        return commands

    def open_command_palette(self) -> None:
        palette = CommandPalette(self.build_palette_commands(), self)
        palette.exec()

    # -- page management (Blueprint v2, Section 7.4) -------------------------
    def insert_page(self, index: int) -> None:
        self.pdf.insert_blank_page(index)
        self.markup_document.shift_pages(index, +1)
        self._page_spin.blockSignals(True)
        self._page_spin.setMaximum(max(self.pdf.page_count, 1))
        self._page_spin.blockSignals(False)
        self._page_count_label.setText(f"/ {self.pdf.page_count}")
        self.go_to_page(index)

    def delete_current_page(self) -> None:
        if self.pdf.page_count <= 1:
            return
        index = self._page_index
        self.markup_document.remove_objects_on_page(index)
        self.pdf.delete_page(index)
        self.markup_document.shift_pages(index + 1, -1)
        self._page_spin.blockSignals(True)
        self._page_spin.setMaximum(max(self.pdf.page_count, 1))
        self._page_spin.blockSignals(False)
        self._page_count_label.setText(f"/ {self.pdf.page_count}")
        self.go_to_page(min(index, self.pdf.page_count - 1))

    def rotate_current_page(self, degrees: int) -> None:
        self.pdf.rotate_page(self._page_index, degrees)
        self._render_current_page()

    def move_page(self, from_index: int, to_index: int) -> None:
        n = self.pdf.page_count
        if not (0 <= from_index < n) or not (0 <= to_index < n) or from_index == to_index:
            return
        order = list(range(n))
        item = order.pop(from_index)
        order.insert(to_index, item)
        self.pdf.move_page(from_index, to_index)
        self.markup_document.remap_pages(order)
        self.go_to_page(to_index)

    def apply_watermark(self, text: str) -> None:
        self.pdf.add_watermark(text)
        self._render_current_page()

    def apply_bates_numbers(self, prefix: str, start: int, digits: int = 6) -> None:
        self.pdf.add_bates_numbers(prefix, start, digits)
        self._render_current_page()

    def apply_header_footer(self, header: str, footer: str) -> None:
        self.pdf.add_header_footer(header, footer)
        self._render_current_page()

    # -- markups list ------------------------------------------------------
    def select_object(self, obj_id: str) -> None:
        obj = self.markup_document.get(obj_id)
        if obj is None:
            return
        if obj.page_index != self._page_index:
            self.go_to_page(obj.page_index)
        self.select_tool(SelectTool)
        self._active_tool.select(obj_id)
        self._position_floating_panel(obj_id)

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
