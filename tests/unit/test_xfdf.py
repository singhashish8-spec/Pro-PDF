from app.models.markup import MarkupObject
from app.persistence import xfdf


def test_export_writes_only_form_fields(tmp_path):
    objects = [
        MarkupObject(type="text_field", page_index=0, points=[(0, 0), (1, 1)], text="name\nJane"),
        MarkupObject(type="checkbox", page_index=0, points=[(0, 0), (1, 1)], text="agree"),
        MarkupObject(type="rectangle", page_index=0, points=[(0, 0), (1, 1)]),  # not a form field
    ]
    out = str(tmp_path / "data.xfdf")
    count = xfdf.export_xfdf(objects, "doc.pdf", out)
    assert count == 2

    content = open(out, encoding="utf-8").read()
    assert "name" in content
    assert "Jane" in content
    assert "agree" in content


def test_export_skips_unnamed_fields(tmp_path):
    objects = [MarkupObject(type="text_field", page_index=0, points=[(0, 0), (1, 1)], text="")]
    out = str(tmp_path / "data.xfdf")
    count = xfdf.export_xfdf(objects, "doc.pdf", out)
    assert count == 0


def test_import_roundtrip(tmp_path):
    objects = [
        MarkupObject(type="text_field", page_index=0, points=[(0, 0), (1, 1)], text="first_name\nJane"),
        MarkupObject(type="text_field", page_index=0, points=[(0, 0), (1, 1)], text="last_name\nDoe"),
    ]
    out = str(tmp_path / "data.xfdf")
    xfdf.export_xfdf(objects, "doc.pdf", out)

    imported = xfdf.import_xfdf(out, page_index=2)
    assert len(imported) == 2
    names_values = {tuple(o.text.split("\n")) for o in imported}
    assert names_values == {("first_name", "Jane"), ("last_name", "Doe")}
    assert all(o.page_index == 2 for o in imported)
    assert all(o.type == "text_field" for o in imported)


def test_imported_fields_have_distinct_ids(tmp_path):
    objects = [
        MarkupObject(type="text_field", page_index=0, points=[(0, 0), (1, 1)], text="a\n1"),
        MarkupObject(type="text_field", page_index=0, points=[(0, 0), (1, 1)], text="b\n2"),
    ]
    out = str(tmp_path / "data.xfdf")
    xfdf.export_xfdf(objects, "doc.pdf", out)
    imported = xfdf.import_xfdf(out)
    assert imported[0].id != imported[1].id
