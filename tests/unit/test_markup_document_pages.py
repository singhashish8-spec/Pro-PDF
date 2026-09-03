from app.models.markup import MarkupObject
from app.models.project import Calibration, MarkupDocument


def _obj(page_index: int) -> MarkupObject:
    return MarkupObject(type="rectangle", page_index=page_index, points=[(0, 0), (10, 10)])


def test_shift_pages_moves_objects_after_insert_point():
    doc = MarkupDocument()
    a, b, c = _obj(0), _obj(1), _obj(2)
    doc.add(a)
    doc.add(b)
    doc.add(c)

    doc.shift_pages(1, +1)  # simulate inserting a blank page at index 1

    assert doc.get(a.id).page_index == 0
    assert doc.get(b.id).page_index == 2
    assert doc.get(c.id).page_index == 3
    assert doc.objects_on_page(2) == [doc.get(b.id)]


def test_remove_objects_on_page():
    doc = MarkupDocument()
    a, b = _obj(0), _obj(1)
    doc.add(a)
    doc.add(b)

    doc.remove_objects_on_page(0)

    assert doc.get(a.id) is None
    assert doc.get(b.id) is not None


def test_shift_pages_after_delete():
    doc = MarkupDocument()
    a, b, c = _obj(0), _obj(1), _obj(2)
    doc.add(a)
    doc.add(b)
    doc.add(c)

    doc.remove_objects_on_page(1)
    doc.shift_pages(2, -1)  # pages after the deleted one shift down

    assert doc.get(a.id).page_index == 0
    assert doc.get(b.id) is None
    assert doc.get(c.id).page_index == 1


def test_remap_pages_after_reorder():
    doc = MarkupDocument()
    a, b, c = _obj(0), _obj(1), _obj(2)
    doc.add(a)
    doc.add(b)
    doc.add(c)

    # Page 0 moved to the end: new order is [old-1, old-2, old-0]
    doc.remap_pages([1, 2, 0])

    assert doc.get(a.id).page_index == 2
    assert doc.get(b.id).page_index == 0
    assert doc.get(c.id).page_index == 1


def test_shift_pages_moves_calibrations_too():
    doc = MarkupDocument()
    cal = Calibration(id="c1", page_index=1, pdf_distance=10, real_distance=1, unit="ft")
    doc.add_calibration(cal)

    doc.shift_pages(1, +1)

    assert doc.get_calibration("c1").page_index == 2
