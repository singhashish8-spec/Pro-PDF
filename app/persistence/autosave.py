"""Autosave/crash-recovery sidecar journal (Blueprint v2, Section 6.5 / ADR 0004)."""

from __future__ import annotations

import json
import os

JOURNAL_SUFFIX = ".pdfpro-journal"


def journal_path(pdf_path: str) -> str:
    return pdf_path + JOURNAL_SUFFIX


def journal_exists(pdf_path: str) -> bool:
    return os.path.exists(journal_path(pdf_path))


def write_journal(pdf_path: str, markup_objects_json: list[dict]) -> None:
    path = journal_path(pdf_path)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(markup_objects_json, f)
    os.replace(tmp_path, path)


def read_journal(pdf_path: str) -> list[dict] | None:
    path = journal_path(pdf_path)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clear_journal(pdf_path: str) -> None:
    path = journal_path(pdf_path)
    if os.path.exists(path):
        os.remove(path)
