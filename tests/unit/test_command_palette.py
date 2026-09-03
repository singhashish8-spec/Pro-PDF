from app.ui.panels.command_palette import CommandPalette, PaletteCommand


def test_palette_lists_all_commands_by_default(qapp):
    calls = []
    commands = [
        PaletteCommand("Undo", lambda: calls.append("undo"), "Edit"),
        PaletteCommand("Redo", lambda: calls.append("redo"), "Edit"),
    ]
    palette = CommandPalette(commands)
    assert palette._list.count() == 2


def test_palette_filters_by_text(qapp):
    commands = [
        PaletteCommand("Undo", lambda: None, "Edit"),
        PaletteCommand("Rectangle", lambda: None, "Tool"),
    ]
    palette = CommandPalette(commands)
    palette._search.setText("rect")
    assert palette._list.count() == 1
    assert "Rectangle" in palette._list.item(0).text()


def test_activating_a_command_invokes_its_callback_and_closes(qapp):
    calls = []
    commands = [PaletteCommand("Undo", lambda: calls.append("undo"), "Edit")]
    palette = CommandPalette(commands)
    palette._on_activated(palette._list.item(0))
    assert calls == ["undo"]
    assert not palette.isVisible()
