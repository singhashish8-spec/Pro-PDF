"""Document Compare: visual diff between two PDF versions (Blueprint v2,
Section 7.6). Works purely off rendered page images (PDFDocument.render_page)
via PIL/numpy — no direct fitz calls, keeping the fitz-only-in-app/core rule.
"""

from __future__ import annotations

import numpy as np
from PIL import Image
from PyQt6.QtGui import QImage

from app.core.pdf_document import PDFDocument

#: Per-channel intensity difference above which a pixel counts as "changed".
_DIFF_THRESHOLD = 24


def _qimage_to_pil(image: QImage) -> Image.Image:
    image = image.convertToFormat(QImage.Format.Format_RGB888)
    width, height = image.width(), image.height()
    ptr = image.bits()
    ptr.setsize(image.sizeInBytes())
    buf = bytes(ptr)
    stride = image.bytesPerLine()
    arr = np.frombuffer(buf, dtype=np.uint8).reshape((height, stride))[:, : width * 3].reshape((height, width, 3))
    return Image.fromarray(arr, mode="RGB")


def _pil_to_qimage(img: Image.Image) -> QImage:
    arr = np.array(img.convert("RGB"))
    height, width, _ = arr.shape
    qimage = QImage(arr.tobytes(), width, height, width * 3, QImage.Format.Format_RGB888)
    return qimage.copy()


def _pad_to_common_size(a: Image.Image, b: Image.Image) -> tuple[Image.Image, Image.Image]:
    width = max(a.width, b.width)
    height = max(a.height, b.height)
    if a.size != (width, height):
        canvas = Image.new("RGB", (width, height), "white")
        canvas.paste(a, (0, 0))
        a = canvas
    if b.size != (width, height):
        canvas = Image.new("RGB", (width, height), "white")
        canvas.paste(b, (0, 0))
        b = canvas
    return a, b


def compare_page(pdf_a: PDFDocument, pdf_b: PDFDocument, page_index: int, zoom: float = 1.0) -> tuple[QImage, float]:
    """Renders `page_index` from both documents and returns (diff-highlighted
    image, fraction of pixels that changed). Highlights are drawn in red over
    pdf_b's rendering. Raises IndexError if either document lacks that page."""
    img_a = _qimage_to_pil(pdf_a.render_page(page_index, zoom))
    img_b = _qimage_to_pil(pdf_b.render_page(page_index, zoom))
    img_a, img_b = _pad_to_common_size(img_a, img_b)

    arr_a = np.asarray(img_a, dtype=np.int16)
    arr_b = np.asarray(img_b, dtype=np.int16)
    diff = np.abs(arr_a - arr_b).sum(axis=2)
    mask = diff > _DIFF_THRESHOLD

    out = np.asarray(img_b, dtype=np.uint8).copy()
    out[mask] = [255, 0, 0]

    diff_ratio = float(mask.mean())
    return _pil_to_qimage(Image.fromarray(out, mode="RGB")), diff_ratio


def compare_documents(pdf_a: PDFDocument, pdf_b: PDFDocument, zoom: float = 1.0) -> list[tuple[int, float]]:
    """Per-page diff ratios for every page index present in either document
    (0.0 for a page that renders identically, 1.0 for a page missing from
    one side and padded entirely white against real content)."""
    page_count = max(pdf_a.page_count, pdf_b.page_count)
    ratios = []
    for i in range(page_count):
        if i >= pdf_a.page_count or i >= pdf_b.page_count:
            ratios.append((i, 1.0))
            continue
        _, ratio = compare_page(pdf_a, pdf_b, i, zoom)
        ratios.append((i, ratio))
    return ratios
