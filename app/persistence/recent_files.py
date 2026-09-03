"""Recent files list, persisted via QSettings (Blueprint v2, Section 5)."""

from __future__ import annotations

from PyQt6.QtCore import QSettings

_KEY = "recent_files/paths"
_MAX_ENTRIES = 15


def _settings() -> QSettings:
    return QSettings("PDF Pro", "PDF Pro")


def get_recent_files() -> list[str]:
    settings = _settings()
    paths = settings.value(_KEY, [])
    if isinstance(paths, str):
        paths = [paths]
    return list(paths or [])


def add_recent_file(path: str) -> None:
    settings = _settings()
    paths = get_recent_files()
    paths = [p for p in paths if p != path]
    paths.insert(0, path)
    paths = paths[:_MAX_ENTRIES]
    settings.setValue(_KEY, paths)


def remove_recent_file(path: str) -> None:
    settings = _settings()
    paths = [p for p in get_recent_files() if p != path]
    settings.setValue(_KEY, paths)


def clear_recent_files() -> None:
    _settings().setValue(_KEY, [])
