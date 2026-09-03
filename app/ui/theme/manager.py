"""Applies theme.qss token sets to the running QApplication and persists the choice."""

from __future__ import annotations

from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtWidgets import QApplication

from .tokens import DARK, LIGHT, ThemeTokens, build_qss

_SETTINGS_KEY = "appearance/theme"


class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)

    def __init__(self, app: QApplication, settings: QSettings | None = None) -> None:
        super().__init__()
        self._app = app
        self._settings = settings or QSettings("PDF Pro", "PDF Pro")
        self._current: ThemeTokens = LIGHT

    @property
    def current(self) -> ThemeTokens:
        return self._current

    def load_saved(self) -> None:
        name = self._settings.value(_SETTINGS_KEY, "light")
        self.set_theme(name if name in ("light", "dark") else "light")

    def set_theme(self, name: str) -> None:
        self._current = DARK if name == "dark" else LIGHT
        self._app.setStyleSheet(build_qss(self._current))
        self._settings.setValue(_SETTINGS_KEY, self._current.name)
        self.theme_changed.emit(self._current.name)

    def toggle(self) -> None:
        self.set_theme("light" if self._current.name == "dark" else "dark")
