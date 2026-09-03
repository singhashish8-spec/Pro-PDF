from app.ui.panels.toc_editor_dialog import TocEditorDialog


def test_toc_roundtrip_through_text(qapp):
    toc = [[1, "Intro", 1], [2, "Details", 2], [1, "Appendix", 5]]
    dialog = TocEditorDialog(toc, page_count=10)
    assert dialog.result_toc() == toc


def test_empty_toc(qapp):
    dialog = TocEditorDialog([], page_count=5)
    assert dialog.result_toc() == []


def test_page_number_clamped_to_page_count(qapp):
    dialog = TocEditorDialog([], page_count=3)
    dialog._editor.setPlainText("Overflow\t99")
    toc = dialog.result_toc()
    assert toc == [[1, "Overflow", 3]]
