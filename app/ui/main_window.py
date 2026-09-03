"""Core application shell (Blueprint v2, Phases 1-2)."""

from __future__ import annotations

from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QStackedWidget

from app.persistence.recent_files import add_recent_file
from app.ui.canvas.document_view import DocumentView
from app.ui.dashboard.home_dashboard import HomeDashboard
from app.ui.theme.manager import ThemeManager


class MainWindow(QMainWindow):
    def __init__(self, theme_manager: ThemeManager) -> None:
        super().__init__()
        self._theme_manager = theme_manager
        self.setWindowTitle("PDF Pro")
        self.resize(1280, 800)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._dashboard = HomeDashboard()
        self._dashboard.browse_requested.connect(self._browse_for_file)
        self._dashboard.open_file_requested.connect(self.open_document)
        self._dashboard.new_file_requested.connect(self._browse_for_file)
        self._stack.addWidget(self._dashboard)

        self._document_view = DocumentView()
        self._document_view.undo_state_changed.connect(self._on_undo_state_changed)
        self._stack.addWidget(self._document_view)

        self._current_path: str | None = None

        self._build_menu()

    @property
    def document_view(self) -> DocumentView:
        return self._document_view

    # -- menu -----------------------------------------------------------
    def _build_menu(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        open_action = QAction("&Open…", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._browse_for_file)
        file_menu.addAction(open_action)

        home_action = QAction("&Home Dashboard", self)
        home_action.triggered.connect(self.show_dashboard)
        file_menu.addAction(home_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As…", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._save_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menu.addMenu("&Edit")
        self._undo_action = QAction("&Undo", self)
        self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self._undo_action.setEnabled(False)
        self._undo_action.triggered.connect(self._document_view.command_stack.undo)
        edit_menu.addAction(self._undo_action)

        self._redo_action = QAction("&Redo", self)
        self._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self._redo_action.setEnabled(False)
        self._redo_action.triggered.connect(self._document_view.command_stack.redo)
        edit_menu.addAction(self._redo_action)

        view_menu = menu.addMenu("&View")
        toggle_theme_action = QAction("Toggle &Dark Mode", self)
        toggle_theme_action.setShortcut("Ctrl+Shift+D")
        toggle_theme_action.triggered.connect(self._theme_manager.toggle)
        view_menu.addAction(toggle_theme_action)

        palette_action = QAction("Command &Palette…", self)
        palette_action.setShortcut("Ctrl+K")
        palette_action.triggered.connect(self._document_view.open_command_palette)
        view_menu.addAction(palette_action)

    def _on_undo_state_changed(self, can_undo: bool, can_redo: bool) -> None:
        self._undo_action.setEnabled(can_undo)
        self._redo_action.setEnabled(can_redo)

    # -- navigation -------------------------------------------------------
    def show_dashboard(self) -> None:
        self._dashboard.refresh_recent_files()
        self._stack.setCurrentWidget(self._dashboard)

    def _browse_for_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF files (*.pdf)")
        if path:
            self.open_document(path)

    def open_document(self, path: str) -> None:
        try:
            has_journal = self._document_view.load(path)
        except Exception as exc:  # surfaced to the user, not swallowed
            QMessageBox.critical(self, "Could not open file", str(exc))
            return
        add_recent_file(path)
        self._current_path = path
        self._stack.setCurrentWidget(self._document_view)

        if has_journal:
            answer = QMessageBox.question(
                self,
                "Recover unsaved work?",
                "PDF Pro found unsaved changes from a previous session for this file. Recover them?",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._document_view.recover_from_journal()
            else:
                self._document_view.discard_journal()

    def _save(self) -> None:
        if not self._current_path:
            return
        self._export_to(self._current_path)

    def _save_as(self) -> None:
        if not self._current_path:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF As", self._current_path, "PDF files (*.pdf)")
        if path:
            self._export_to(path)

    def _export_to(self, path: str) -> None:
        try:
            self._document_view.pdf.export(path, self._document_view.markup_document.all_objects())
        except Exception as exc:
            QMessageBox.critical(self, "Could not save file", str(exc))
            return
        self._document_view.discard_journal()
        QMessageBox.information(self, "Saved", f"Saved to {path}")
