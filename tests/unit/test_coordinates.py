import pytest

from app.core.coordinates import pdf_to_scene, scene_to_pdf


@pytest.mark.parametrize(
    "point,page_height,scale",
    [
        ((0, 0), 792, 1.0),
        ((100, 200), 792, 1.5),
        ((300.5, 400.25), 1000, 0.33),
    ],
)
def test_round_trip(point, page_height, scale):
    scene_pt = pdf_to_scene(point, page_height, scale)
    back = scene_to_pdf(scene_pt, page_height, scale)
    assert back[0] == pytest.approx(point[0])
    assert back[1] == pytest.approx(point[1])


def test_origin_maps_to_bottom_left():
    # PDF origin (0,0) is bottom-left; scene origin (0,0) is top-left.
    x, y = pdf_to_scene((0, 0), page_height=792, scale=1.0)
    assert x == pytest.approx(0)
    assert y == pytest.approx(792)


def test_top_left_pdf_point_maps_to_scene_origin():
    x, y = pdf_to_scene((0, 792), page_height=792, scale=1.0)
    assert x == pytest.approx(0)
    assert y == pytest.approx(0)
