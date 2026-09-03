"""Tool Chest UI: browse, apply, save, and delete reusable markup style
presets (Blueprint v2, Section 7.2)."""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.persistence import tool_chest


class ToolChestPanel(QDialog):
    def __init__(
        self,
        on_apply: Callable[[dict], None],
        current_style_provider: Callable[[], tuple[str, dict]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tool Chest")
        self.resize(360, 400)
        self._on_apply = on_apply
        self._current_style_provider = current_style_provider

        layout = QVBoxLayout(self)
        self._list = QListWidget()
        self._list.itemActivated.connect(self._apply_selected)
        layout.addWidget(self._list, 1)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save Current Style…")
        save_btn.clicked.connect(self._save_current)
        buttons.addWidget(save_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(lambda: self._apply_selected(self._list.currentItem()))
        buttons.addWidget(apply_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_selected)
        buttons.addWidget(delete_btn)
        layout.addLayout(buttons)

        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        for entry in tool_chest.load_entries():
            item = QListWidgetItem(f"{entry['name']}  ({entry['markup_type']})")
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self._list.addItem(item)

    def _apply_selected(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        self._on_apply(entry)

    def _save_current(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Current Style", "Name:")
        if not ok or not name.strip():
            return
        markup_type, style = self._current_style_provider()
        tool_chest.add_entry(name.strip(), markup_type, style)
        self.refresh()

    def _delete_selected(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(self, "Delete", f"Delete '{entry['name']}' from the Tool Chest?")
        if confirm == QMessageBox.StandardButton.Yes:
            tool_chest.delete_entry(entry["id"])
            self.refresh()
