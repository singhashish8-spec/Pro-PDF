"""Design tokens shared by light and dark themes (Blueprint v2, Section 7.7)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeTokens:
    name: str
    bg_base: str
    bg_surface: str
    bg_elevated: str
    bg_hover: str
    border: str
    text_primary: str
    text_secondary: str
    accent: str
    accent_hover: str
    danger: str
    radius_sm: str = "4px"
    radius_md: str = "8px"
    radius_lg: str = "12px"
    spacing_xs: str = "4px"
    spacing_sm: str = "8px"
    spacing_md: str = "16px"
    spacing_lg: str = "24px"


LIGHT = ThemeTokens(
    name="light",
    bg_base="#F5F6F8",
    bg_surface="#FFFFFF",
    bg_elevated="#FFFFFF",
    bg_hover="#EEF1F5",
    border="#DCE0E6",
    text_primary="#1A1D21",
    text_secondary="#5C6470",
    accent="#339AF0",
    accent_hover="#1C7ED6",
    danger="#E03131",
)

DARK = ThemeTokens(
    name="dark",
    bg_base="#1A1D21",
    bg_surface="#212429",
    bg_elevated="#2B2F36",
    bg_hover="#31353D",
    border="#3A3F47",
    text_primary="#F1F3F5",
    text_secondary="#ADB5BD",
    accent="#4DABF7",
    accent_hover="#74C0FC",
    danger="#FF6B6B",
)


def build_qss(tokens: ThemeTokens) -> str:
    return f"""
QWidget {{
    background-color: {tokens.bg_base};
    color: {tokens.text_primary};
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}}
QMainWindow, #Dashboard {{
    background-color: {tokens.bg_base};
}}
QToolBar, #RightPanel, #TopBar {{
    background-color: {tokens.bg_surface};
    border: none;
    border-bottom: 1px solid {tokens.border};
}}
QPushButton, QToolButton {{
    background-color: {tokens.bg_surface};
    border: 1px solid {tokens.border};
    border-radius: {tokens.radius_sm};
    padding: 6px 10px;
}}
QPushButton:hover, QToolButton:hover {{
    background-color: {tokens.bg_hover};
}}
QPushButton#Primary {{
    background-color: {tokens.accent};
    color: white;
    border: none;
}}
QPushButton#Primary:hover {{
    background-color: {tokens.accent_hover};
}}
QListWidget, QTableView, QTreeView {{
    background-color: {tokens.bg_surface};
    border: 1px solid {tokens.border};
    border-radius: {tokens.radius_md};
}}
QLineEdit, QComboBox, QSpinBox {{
    background-color: {tokens.bg_surface};
    border: 1px solid {tokens.border};
    border-radius: {tokens.radius_sm};
    padding: 4px 8px;
}}
QLabel#Secondary {{
    color: {tokens.text_secondary};
}}
QSplitter::handle {{
    background-color: {tokens.border};
}}
"""
