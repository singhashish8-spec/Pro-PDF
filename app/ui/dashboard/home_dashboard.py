"""Home Dashboard: recent files and quick actions (Blueprint v2, Section 7 / Phase 1)."""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.persistence.recent_files import get_recent_files


class HomeDashboard(QWidget):
    open_file_requested = pyqtSignal(str)
    new_file_requested = pyqtSignal()
    browse_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Dashboard")
        self._build_ui()
        self.refresh_recent_files()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(16)

        title = QLabel("PDF Pro")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        subtitle = QLabel("AEC markup, measurement, and takeoff")
        subtitle.setObjectName("Secondary")
        root.addWidget(title)
        root.addWidget(subtitle)

        actions = QHBoxLayout()
        open_btn = QPushButton("Open PDF…")
        open_btn.setObjectName("Primary")
        open_btn.clicked.connect(self.browse_requested.emit)
        new_btn = QPushButton("New Project")
        new_btn.clicked.connect(self.new_file_requested.emit)
        actions.addWidget(open_btn)
        actions.addWidget(new_btn)
        actions.addStretch(1)
        root.addLayout(actions)

        recent_label = QLabel("Recent files")
        recent_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        root.addWidget(recent_label)

        self._recent_list = QListWidget()
        self._recent_list.itemActivated.connect(self._on_recent_activated)
        root.addWidget(self._recent_list, 1)

    def refresh_recent_files(self) -> None:
        self._recent_list.clear()
        for path in get_recent_files():
            label = f"{os.path.basename(path)}  —  {path}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self._recent_list.addItem(item)
        if self._recent_list.count() == 0:
            placeholder = QListWidgetItem("No recent files yet")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self._recent_list.addItem(placeholder)

    def _on_recent_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.open_file_requested.emit(path)
