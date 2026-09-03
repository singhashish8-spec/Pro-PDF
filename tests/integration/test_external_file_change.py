import pymupdf as fitz

from app.ui.canvas.document_view import DocumentView


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
