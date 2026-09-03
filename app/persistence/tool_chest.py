"""Tool Chest: saved, reusable custom markup styles, shared across projects
(Blueprint v2, Section 7.2 — "the single most important Bluebeam-parity
feature to get right"). Persisted per-user, not per-document.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from PyQt6.QtCore import QStandardPaths


def default_chest_path() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    directory = Path(base) if base else Path.home() / ".pdfpro"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "tool_chest.json"


def load_entries(path: Path | None = None) -> list[dict]:
    path = path or default_chest_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_entries(entries: list[dict], path: Path | None = None) -> None:
    path = path or default_chest_path()
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def add_entry(name: str, markup_type: str, style: dict, path: Path | None = None) -> dict:
    entries = load_entries(path)
    entry = {"id": str(uuid.uuid4()), "name": name, "markup_type": markup_type, "style": style}
    entries.append(entry)
    save_entries(entries, path)
    return entry


def delete_entry(entry_id: str, path: Path | None = None) -> None:
    entries = [e for e in load_entries(path) if e["id"] != entry_id]
    save_entries(entries, path)
