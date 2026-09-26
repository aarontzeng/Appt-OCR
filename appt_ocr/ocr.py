"""OCR engine wrapper.

Manages PaddleOCR initialization (one engine per language), the OpenCC
simplified-to-traditional converter, and text detection on an image.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any

from appt_ocr.boxes import OcrBox
from appt_ocr.image import ImageInput, as_array

logger = logging.getLogger(__name__)

# One engine per language. A single slot, as before 3.1.0, meant the first
# call's language won for the life of the process: process_pptx(lang="en")
# after a "ch" run silently used the Chinese engine.
_ocr_engines: dict[str, Any] = {}

_opencc_converter: Any | None = None
_opencc_unavailable = False

# A line whose top edge is tilted more than this is rotated or vertical text
# and is skipped: a horizontal text box cannot represent it.
ROTATED_MIN_DEGREES = 15
ROTATED_MAX_DEGREES = 165


def get_ocr_engine(lang: str = "ch") -> Any:
    """Retrieve or initialize the PaddleOCR engine for ``lang`` (lazy load).

    Args:
        lang: OCR language model. ``'ch'`` includes both Chinese and English,
              ``'en'`` is English only.

    Returns:
        PaddleOCR instance for that language, created once per process.
    """
    engine = _ocr_engines.get(lang)
    if engine is None:
        # Skip PaddlePaddle's model-source connectivity check, a startup delay
        # with no benefit here. Set only when the engine is first built, not
        # at import time, so importing the package changes nothing.
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        logging.getLogger("ppocr").setLevel(logging.ERROR)

        from paddleocr import PaddleOCR

        engine = PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            show_log=False,
            # Disable MKLDNN to prevent ConvertPirAttribute2RuntimeAttribute
            # crash on CPU with paddlepaddle >= 3.0.0
            enable_mkldnn=False,
        )
        _ocr_engines[lang] = engine
    return engine


def reset_engines() -> None:
    """Drop every cached engine and converter (tests, long-lived processes)."""
    global _opencc_converter, _opencc_unavailable
    _ocr_engines.clear()
    _opencc_converter = None
    _opencc_unavailable = False


def get_opencc_converter() -> Any | None:
    """Retrieve or initialize the OpenCC ``s2t`` converter (lazy load).

    Returns:
        OpenCC converter instance, or ``None`` if it is not installed or
        failed to initialize (warned once, not once per text box).
    """
    global _opencc_converter, _opencc_unavailable
    if _opencc_converter is None and not _opencc_unavailable:
        try:
            from opencc import OpenCC

            _opencc_converter = OpenCC("s2t")
        except ImportError:
            _opencc_unavailable = True
            logger.warning(
                "opencc-python-reimplemented is not installed, "
                "unable to convert simplified to traditional Chinese. "
                "Install with: pip install opencc-python-reimplemented"
            )
        except Exception as e:
            _opencc_unavailable = True
            logger.warning("OpenCC initialization failed: %s", e)
    return _opencc_converter


def run_ocr_on_image(image: ImageInput, lang: str = "ch") -> list[OcrBox]:
    """Run OCR on an image, returning text and pixel coordinates.

    Args:
        image: Encoded image bytes, or a BGR array from ``decode_image``
            (the array is handed to PaddleOCR directly; nothing is written
            to disk).
        lang: OCR language.

    Returns:
        One dict per horizontal text line::

            {
                "left_px": float,   # Top-left X (pixels)
                "top_px": float,    # Top-left Y (pixels)
                "width_px": float,  # Width (pixels)
                "height_px": float, # Height (pixels)
                "text": str,        # Recognized text
                "confidence": float # Confidence score (0~1)
            }

        Rotated and vertical lines are left out.
    """
    img = as_array(image)
    if img is None:
        return []

    ocr = get_ocr_engine(lang)
    result = ocr.ocr(img, cls=True)

    parsed: list[OcrBox] = []
    if not result or not result[0]:
        return parsed

    for line in result[0]:
        box = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        text = line[1][0]
        confidence = line[1][1]

        # PaddleOCR polygon order: top-left, top-right, bottom-right, bottom-left
        dx = box[1][0] - box[0][0]
        dy = box[1][1] - box[0][1]
        angle = abs(math.degrees(math.atan2(dy, dx)))
        if ROTATED_MIN_DEGREES < angle < ROTATED_MAX_DEGREES:
            continue

        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        left_px = min(xs)
        top_px = min(ys)

        parsed.append(
            {
                "left_px": float(left_px),
                "top_px": float(top_px),
                "width_px": float(max(xs) - left_px),
                "height_px": float(max(ys) - top_px),
                "text": str(text),
                "confidence": float(confidence),
            }
        )

    return parsed
