"""MainWindow-level integration tests. Notably: Save must never block on a
modal dialog waiting for a click — see docs/progress.md's Windows-installer
notes for two real bugs of exactly this shape caught by manual smoke runs.
pyproject.toml's pytest timeout turns a reintroduced one into a fast, loud
failure instead of a hang.
"""

import pymupdf as fitz

from app.commands.object_commands import AddObjectCommand
from app.models.markup import MarkupObject
from app.ui.main_window import MainWindow
from app.ui.theme.manager import ThemeManager


def test_save_does_not_block_and_writes_to_disk(qapp, qtbot, make_pdf):
    path = make_pdf(page_count=1)
    window = MainWindow(ThemeManager(qapp))
    qtbot.addWidget(window)
    window.open_document(path)

    dv = window.document_view
    obj = MarkupObject(type="rectangle", page_index=0, points=[(10, 10), (50, 50)])
    dv.command_stack.push(AddObjectCommand(dv.markup_document, obj))

    window._save()  # would hang here if this regressed to a blocking dialog

    check = fitz.open(path)
    assert check.page_count == 1
    check.close()
    dv.pdf.close()


def test_repeated_saves_keep_the_document_open(qapp, qtbot, make_pdf):
    path = make_pdf(page_count=1)
    window = MainWindow(ThemeManager(qapp))
    qtbot.addWidget(window)
    window.open_document(path)

    dv = window.document_view
    for _ in range(3):
        window._save()
        assert dv.pdf.is_open
        assert dv.pdf.page_count == 1

    dv.pdf.close()


def test_save_shows_status_bar_confirmation_not_a_dialog(qapp, qtbot, make_pdf):
    path = make_pdf(page_count=1)
    window = MainWindow(ThemeManager(qapp))
    qtbot.addWidget(window)
    window.open_document(path)

    window._save()

    assert "Saved" in window.statusBar().currentMessage()
    window.document_view.pdf.close()
