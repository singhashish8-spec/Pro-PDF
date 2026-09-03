from app.models.markup import MarkupObject


def test_markup_object_json_round_trip():
    obj = MarkupObject(
        type="rectangle",
        page_index=2,
        points=[(1.5, 2.5), (10.0, 20.0)],
        text="",
    )
    obj.style.stroke_color = "#123456"

    restored = MarkupObject.from_dict(obj.to_dict())

    assert restored.id == obj.id
    assert restored.type == obj.type
    assert restored.page_index == obj.page_index
    assert restored.points == obj.points
    assert restored.style.stroke_color == "#123456"


def test_unknown_type_rejected():
    import pytest

    with pytest.raises(ValueError):
        MarkupObject(type="not-a-real-type", page_index=0)
