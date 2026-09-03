from app.models.markup import MarkupObject, Measurement
from app.persistence import markups_db


def test_sync_and_list_roundtrip(tmp_path):
    pdf_path = str(tmp_path / "doc.pdf")
    obj1 = MarkupObject(type="rectangle", page_index=1, points=[(0, 0), (1, 1)], author="alice")
    obj2 = MarkupObject(
        type="measure_linear",
        page_index=0,
        points=[(0, 0), (10, 0)],
        author="bob",
        measurement=Measurement(value=5.0, unit="ft"),
    )

    markups_db.sync_all(pdf_path, [obj1, obj2])
    rows = markups_db.list_markups(pdf_path)

    assert len(rows) == 2
    by_id = {r["id"]: r for r in rows}
    assert by_id[obj1.id]["author"] == "alice"
    assert by_id[obj2.id]["value"] == 5.0
    assert by_id[obj2.id]["unit"] == "ft"


def test_sync_all_replaces_previous_contents(tmp_path):
    pdf_path = str(tmp_path / "doc.pdf")
    obj1 = MarkupObject(type="rectangle", page_index=0, points=[(0, 0), (1, 1)])
    markups_db.sync_all(pdf_path, [obj1])
    assert len(markups_db.list_markups(pdf_path)) == 1

    markups_db.sync_all(pdf_path, [])
    assert markups_db.list_markups(pdf_path) == []


def test_list_markups_sorts_by_requested_column(tmp_path):
    pdf_path = str(tmp_path / "doc.pdf")
    objs = [
        MarkupObject(type="rectangle", page_index=2, points=[(0, 0), (1, 1)]),
        MarkupObject(type="ellipse", page_index=0, points=[(0, 0), (1, 1)]),
        MarkupObject(type="arrow", page_index=1, points=[(0, 0), (1, 1)]),
    ]
    markups_db.sync_all(pdf_path, objs)

    rows = markups_db.list_markups(pdf_path, order_by="page_index")
    assert [r["page_index"] for r in rows] == [0, 1, 2]

    rows_desc = markups_db.list_markups(pdf_path, order_by="page_index", descending=True)
    assert [r["page_index"] for r in rows_desc] == [2, 1, 0]
