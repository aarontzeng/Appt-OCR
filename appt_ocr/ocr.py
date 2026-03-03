"""OCR engine wrapper.

Manages PaddleOCR initialization, OpenCC simplified-to-traditional conversion,
and OCR text detection/recognition.
"""

import logging
import math
import os
import tempfile
from typing import Any, Optional

# Disable PaddlePaddle connectivity checks which causes startup delay
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

logger = logging.getLogger(__name__)

# Lazily initialized OCR engine instance
_ocr_engine: Optional[Any] = None

# Lazily initialized OpenCC simplified-to-traditional converter
_opencc_converter: Optional[Any] = None


def get_ocr_engine(lang: str = "ch") -> Any:
    """Retrieve or initialize the PaddleOCR engine (lazy load).

    Args:
        lang: OCR language model. ``'ch'`` includes both Chinese and English,
              ``'en'`` is English only.

    Returns:
        PaddleOCR instance.
    """
    global _ocr_engine
    if _ocr_engine is None:
        logging.getLogger("ppocr").setLevel(logging.ERROR)

        from paddleocr import PaddleOCR

        _ocr_engine = PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            show_log=False,
            # Disable MKLDNN to prevent ConvertPirAttribute2RuntimeAttribute
            # crash on CPU with paddlepaddle >= 3.0.0
            enable_mkldnn=False,
        )
    return _ocr_engine


def get_opencc_converter() -> Optional[Any]:
    """Retrieve or initialize the OpenCC converter (lazy load).

    Uses ``s2t`` (Simplified to Traditional) configuration.

    Returns:
        OpenCC converter instance, or ``None`` if not installed.
    """
    global _opencc_converter
    if _opencc_converter is None:
        try:
            from opencc import OpenCC

            _opencc_converter = OpenCC("s2t")
        except ImportError:
            logger.warning(
                "opencc-python-reimplemented is not installed, "
                "unable to convert simplified to traditional Chinese. "
                "Install with: pip install opencc-python-reimplemented"
            )
            return None
        except Exception as e:
            logger.warning("OpenCC initialization failed: %s", e)
            return None
    return _opencc_converter


def run_ocr_on_image(
    image_bytes: bytes,
    lang: str = "ch",
) -> list[dict]:
    """Run OCR recognition on an image, returning text and coordinate info.

    Args:
        image_bytes: Binary content of the image.
        lang: OCR language.

    Returns:
        List of OCR results, where each element is a dict::

            {
                "left_px": float,   # Top-left X (pixels)
                "top_px": float,    # Top-left Y (pixels)
                "width_px": float,  # Width (pixels)
                "height_px": float, # Height (pixels)
                "text": str,        # Recognized text
                "confidence": float # Confidence score (0~1)
            }
    """
    ocr = get_ocr_engine(lang)

    # PaddleOCR requires a file path or numpy array
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        result = ocr.ocr(tmp_path, cls=True)
    finally:
        os.unlink(tmp_path)

    # Parse OCR results
    parsed: list[dict] = []
    if not result or not result[0]:
        return parsed

    for line in result[0]:
        box = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        text = line[1][0]
        confidence = line[1][1]

        # Calculate rotation angle from four corner coordinates
        # PaddleOCR polygon order: top-left, top-right, bottom-right, bottom-left
        dx = box[1][0] - box[0][0]
        dy = box[1][1] - box[0][1]
        angle = abs(math.degrees(math.atan2(dy, dx)))
        # Text angled closer to 90° or 270° is considered rotated — skip
        if angle > 15 and angle < 165:
            continue

        # Calculate Bounding Box from the four corner coordinates
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        left_px = min(xs)
        top_px = min(ys)
        width_px = max(xs) - left_px
        height_px = max(ys) - top_px

        parsed.append(
            {
                "left_px": float(left_px),
                "top_px": float(top_px),
                "width_px": float(width_px),
                "height_px": float(height_px),
                "text": str(text),
                "confidence": float(confidence),
            }
        )

    return parsed
