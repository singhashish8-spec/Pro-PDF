import sys

import pymupdf as fitz
import pytest

from app.ui.canvas.document_view import DocumentView

# On Windows, fitz's open handle on a path blocks a *different* process (or a
# different handle in this same process) from replacing that file via the
# standard write-temp-then-rename pattern nearly every editor/sync tool uses
# — a real OS file-sharing difference, not a bug in the detection logic below
# (which is exercised end-to-end on Linux/macOS). PDFDocument.export() works
# around this for our *own* saves by closing and reopening its own handle
# (see its docstring); an external process doing the same replace has no such
# workaround available to it, so this specific simulation isn't meaningful
# on Windows and is skipped there rather than asserting a false negative.
skip_on_windows = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows file-sharing blocks another handle from replacing an open file; not this code's bug — see comment above",
)


@skip_on_windows
def test_external_change_is_detected(qtbot, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    def touch_file():
        import os

        doc = fitz.open(path)
        doc.new_page(width=200, height=200)
        doc.save(path + ".tmp")
        doc.close()
        os.replace(path + ".tmp", path)

    with qtbot.waitSignal(view.external_change_detected, timeout=5000, raising=True):
        touch_file()

    view.pdf.close()


def test_own_save_does_not_trigger_external_change_notice(qtbot, make_pdf):
    path = make_pdf(page_count=1)
    view = DocumentView()
    view.load(path)

    signals = []
    view.external_change_detected.connect(lambda p: signals.append(p))

    view.notify_saving()
    view.pdf.export(path, [])

    # Give the filesystem watcher a moment; it should NOT have fired because
    # notify_saving() flagged the next change as our own.
    qtbot.wait(500)
    assert signals == []
    view.pdf.close()
