"""The one record every stage passes along: an OCR text box, as a dict.

The public API (``run_ocr_on_image``, ``merge_nearby_boxes``) has always
returned plain dicts with these keys, so the shape stays a dict; the
``TypedDict`` gives pyright the key names, which a bare ``dict`` never did.
"""

from __future__ import annotations

from typing import TypedDict

import numpy as np


class OcrBox(TypedDict):
    """A detected text region, in pixels of the image it was detected on."""

    left_px: float
    top_px: float
    width_px: float
    height_px: float
    text: str
    confidence: float


class AnalyzedBox(OcrBox, total=False):
    """An ``OcrBox`` after ``analyze_text_features`` added its appearance."""

    color: tuple[int, int, int]
    is_bold: bool
    text_mask: np.ndarray
