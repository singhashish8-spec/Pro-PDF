"""Core application shell (Blueprint v2, Phase 1)."""

from __future__ import annotations

from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QStackedWidget

from app.persistence.recent_files import add_recent_file
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

        self._document_view = None  # populated on first open_document() call
        self._current_path: str | None = None

        self._build_menu()

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
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menu.addMenu("&View")
        toggle_theme_action = QAction("Toggle &Dark Mode", self)
        toggle_theme_action.setShortcut("Ctrl+Shift+D")
        toggle_theme_action.triggered.connect(self._theme_manager.toggle)
        view_menu.addAction(toggle_theme_action)

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
            self._open_document_impl(path)
        except Exception as exc:  # surfaced to the user, not swallowed
            QMessageBox.critical(self, "Could not open file", str(exc))
            return
        add_recent_file(path)
        self._current_path = path

    def _open_document_impl(self, path: str) -> None:
        """Overridden/extended once the Glass Layer canvas exists (Phase 2)."""
        raise NotImplementedError(
            "Document rendering is wired in app.ui.canvas as of Phase 2"
        )
