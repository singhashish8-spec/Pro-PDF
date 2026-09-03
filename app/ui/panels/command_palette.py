"""Command palette (Cmd/Ctrl+K) — Blueprint v2, Section 7.7 / Phase 4."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget


@dataclass
class PaletteCommand:
    label: str
    callback: Callable[[], None]
    category: str = ""

    @property
    def display(self) -> str:
        return f"{self.category}: {self.label}" if self.category else self.label


class CommandPalette(QDialog):
    def __init__(self, commands: list[PaletteCommand], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.setModal(True)
        self.resize(480, 360)
        self._commands = commands

        layout = QVBoxLayout(self)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Type a command…")
        self._search.textChanged.connect(self._refilter)
        layout.addWidget(self._search)

        self._list = QListWidget()
        self._list.itemActivated.connect(self._on_activated)
        layout.addWidget(self._list, 1)

        self._search.installEventFilter(self)
        self._populate(commands)
        self._search.setFocus()

    def _populate(self, commands: list[PaletteCommand]) -> None:
        self._list.clear()
        for command in commands:
            item = QListWidgetItem(command.display)
            item.setData(Qt.ItemDataRole.UserRole, command)
            self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _refilter(self, text: str) -> None:
        text = text.lower().strip()
        matches = [c for c in self._commands if text in c.display.lower()] if text else list(self._commands)
        self._populate(matches)

    def _on_activated(self, item: QListWidgetItem) -> None:
        command: PaletteCommand = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
        command.callback()

    def eventFilter(self, obj, event) -> bool:
        from PyQt6.QtCore import QEvent

        if obj is self._search and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                row = self._list.currentRow()
                row = row + 1 if key == Qt.Key.Key_Down else row - 1
                row = max(0, min(row, self._list.count() - 1))
                self._list.setCurrentRow(row)
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                item = self._list.currentItem()
                if item is not None:
                    self._on_activated(item)
                return True
        return super().eventFilter(obj, event)
