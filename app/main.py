"""PDF Pro application entry point."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme.manager import ThemeManager


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PDF Pro")
    app.setOrganizationName("PDF Pro")

    theme_manager = ThemeManager(app)
    theme_manager.load_saved()

    window = MainWindow(theme_manager)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
