import pytest

from app.core.coordinates import pdf_to_scene, scene_to_pdf


@pytest.mark.parametrize(
    "point,scale",
    [
        ((0, 0), 1.0),
        ((100, 200), 1.5),
        ((300.5, 400.25), 0.33),
    ],
)
def test_round_trip(point, scale):
    scene_pt = pdf_to_scene(point, scale)
    back = scene_to_pdf(scene_pt, scale)
    assert back[0] == pytest.approx(point[0])
    assert back[1] == pytest.approx(point[1])


def test_pdf_and_scene_share_top_left_origin():
    # Both spaces are top-left origin, y-down (PyMuPDF's page-space convention,
    # see app/core/coordinates.py docstring) — only a scale factor separates them.
    x, y = pdf_to_scene((0, 0), scale=1.0)
    assert (x, y) == (0, 0)


def test_scale_only_affects_magnitude_not_orientation():
    x, y = pdf_to_scene((10, 20), scale=2.0)
    assert (x, y) == pytest.approx((20, 40))
