from app.persistence import tool_chest


def test_add_load_delete_roundtrip(tmp_path):
    path = tmp_path / "chest.json"
    assert tool_chest.load_entries(path) == []

    entry = tool_chest.add_entry("Red Cloud", "cloud", {"stroke_color": "#FF0000"}, path)
    entries = tool_chest.load_entries(path)
    assert len(entries) == 1
    assert entries[0]["id"] == entry["id"]
    assert entries[0]["name"] == "Red Cloud"
    assert entries[0]["style"]["stroke_color"] == "#FF0000"

    tool_chest.delete_entry(entry["id"], path)
    assert tool_chest.load_entries(path) == []


def test_multiple_entries_persist_independently(tmp_path):
    path = tmp_path / "chest.json"
    tool_chest.add_entry("A", "rectangle", {"stroke_color": "#111111"}, path)
    tool_chest.add_entry("B", "ellipse", {"stroke_color": "#222222"}, path)
    entries = tool_chest.load_entries(path)
    assert {e["name"] for e in entries} == {"A", "B"}
