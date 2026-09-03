import os
from pathlib import Path

import pymupdf as fitz
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def make_pdf(tmp_path):
    """Generates a throwaway PDF fixture; real corpus files still need
    sourcing per tests/fixtures/README.md (Section 11.2)."""

    def _make(name: str = "doc.pdf", page_count: int = 2, text: str = "Hello PDF Pro") -> str:
        doc = fitz.open()
        for _ in range(page_count):
            page = doc.new_page(width=612, height=792)  # US Letter
            page.insert_text((72, 72), text)
        path = str(tmp_path / name)
        doc.save(path)
        doc.close()
        return path

    return _make
