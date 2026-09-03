"""PDF user-space <-> scene/screen-space transforms (Blueprint v2, Section 6.1 / ADR 0001).

PDF user space: origin bottom-left, y-up, unaffected by zoom.
Scene space: origin top-left, y-down, in scene pixels.

`scale` is scene pixels per PDF point — i.e. `user_zoom * PDFDocument.BASE_DPI_SCALE`,
the same factor `PDFDocument.render_page`/`scene_size` use to rasterize the page. Callers
must derive `scale` that way so markup geometry lines up with the rendered background
pixel-for-pixel; passing a bare UI zoom level here will misalign the two layers.

These functions are the ONLY place this math is allowed to live; every tool
and panel must import them rather than recompute the transform.
"""

from __future__ import annotations


def pdf_to_scene(point: tuple[float, float], page_height: float, scale: float) -> tuple[float, float]:
    x, y = point
    return (x * scale, (page_height - y) * scale)


def scene_to_pdf(point: tuple[float, float], page_height: float, scale: float) -> tuple[float, float]:
    x, y = point
    return (x / scale, page_height - (y / scale))


def pdf_rect_to_scene(
    rect: tuple[float, float, float, float], page_height: float, scale: float
) -> tuple[float, float, float, float]:
    """rect is (x0, y0, x1, y1) in PDF space with y0 < y1 (bottom to top)."""
    x0, y0, x1, y1 = rect
    sx0, sy0 = pdf_to_scene((x0, y1), page_height, scale)
    sx1, sy1 = pdf_to_scene((x1, y0), page_height, scale)
    return (sx0, sy0, sx1, sy1)


def scene_rect_to_pdf(
    rect: tuple[float, float, float, float], page_height: float, scale: float
) -> tuple[float, float, float, float]:
    """rect is (x0, y0, x1, y1) in scene space (top to bottom)."""
    x0, y0, x1, y1 = rect
    px0, py0 = scene_to_pdf((x0, y1), page_height, scale)
    px1, py1 = scene_to_pdf((x1, y0), page_height, scale)
    return (px0, py0, px1, py1)
