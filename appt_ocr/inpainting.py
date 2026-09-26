"""Text inpainting engines.

Two ways of erasing detected text from an image:
- **OpenCV**: Navier-Stokes inpainting over pixel-level text masks. Always
  available.
- **LaMa**: the Large Mask Inpainting model (Fast Fourier Convolutions),
  better on complex backgrounds. Needs the ``lama`` extra
  (``pip install "appt-ocr[lama]"``); without it the OpenCV engine is used.
"""

from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np
from PIL import Image

from appt_ocr.boxes import AnalyzedBox
from appt_ocr.image import ImageInput, as_array, encode_image

logger = logging.getLogger(__name__)

INPAINT_ENGINES = ("lama", "opencv")

_lama_model: Any | None = None
# Set after one failed load, so a process without the model does not retry
# the import (and repeat the warning) on every slide.
_lama_unavailable = False

# LaMa inference resolution cap: larger images are scaled down for inference
# and the result scaled back, to keep the model within memory.
LAMA_MAX_DIM = 2048
# Mask growth around each box, as a share of its height (minimum in px).
LAMA_PAD_DIVISOR = 8
LAMA_PAD_MIN_PX = 3
OPENCV_DILATE_DIVISOR = 10
OPENCV_DILATE_MIN_PX = 2
OPENCV_RADIUS_DIVISOR = 8
OPENCV_RADIUS_MIN_PX = 3


def get_lama_model() -> Any | None:
    """Retrieve or initialize the LaMa model (lazy load).

    The first call downloads the weights (~174 MB) from HuggingFace into
    ``~/.cache/huggingface/``. A failed load is remembered: later calls return
    ``None`` at once instead of failing again per slide.
    """
    global _lama_model, _lama_unavailable
    if _lama_model is None and not _lama_unavailable:
        try:
            from simple_lama_inpainting import SimpleLama  # type: ignore

            _lama_model = SimpleLama()
        except Exception as e:
            _lama_unavailable = True
            logger.warning(
                "LaMa is not available (%s); the OpenCV engine will be used. "
                'Install it with: pip install "appt-ocr[lama]"',
                e,
            )
    return _lama_model


def reset_lama() -> None:
    """Forget the cached model and any remembered failure (tests)."""
    global _lama_model, _lama_unavailable
    _lama_model = None
    _lama_unavailable = False


def erase_text_using_masks(
    image: ImageInput,
    boxes: list[AnalyzedBox],
    engine: str = "opencv",
    encoding: str = "png",
) -> bytes:
    """Erase the boxes' text from the image with the chosen engine.

    Args:
        image: Encoded bytes, or the BGR array from ``decode_image``.
        boxes: Text boxes; the OpenCV engine needs each one's ``text_mask``
            from ``analyze_text_features`` (a box without one is skipped).
        engine: ``"opencv"`` or ``"lama"`` (falls back to OpenCV when the
            model is unavailable or fails).
        encoding: ``"png"`` (default) or ``"jpg"``/``"jpeg"`` for the output.

    Returns:
        The processed image, encoded; the input bytes unchanged when there is
        nothing to erase or the image cannot be decoded.
    """
    if engine not in INPAINT_ENGINES:
        raise ValueError(
            f"unknown inpaint engine {engine!r}; use one of {INPAINT_ENGINES}"
        )
    if not boxes:
        return _unchanged(image, encoding)

    if engine == "lama":
        return erase_text_using_lama(image, boxes, encoding=encoding)

    img = as_array(image)
    if img is None:
        return _unchanged(image, encoding)
    try:
        full_mask = np.zeros(img.shape[:2], dtype=np.uint8)
        max_text_height = 0

        for box in boxes:
            if "text_mask" not in box:
                continue
            x, y = max(0, int(box["left_px"])), max(0, int(box["top_px"]))
            h = int(box["height_px"])
            max_text_height = max(max_text_height, h)

            roi_mask = box["text_mask"]
            roi_h, roi_w = roi_mask.shape
            end_y = min(y + roi_h, full_mask.shape[0])
            end_x = min(x + roi_w, full_mask.shape[1])
            actual_h, actual_w = end_y - y, end_x - x
            if actual_h <= 0 or actual_w <= 0:
                continue

            # Dilate to cover residual anti-aliasing edges around the strokes.
            expand_px = max(OPENCV_DILATE_MIN_PX, h // OPENCV_DILATE_DIVISOR)
            kernel = np.ones((expand_px * 2 + 1, expand_px * 2 + 1), np.uint8)
            dilated = cv2.dilate(roi_mask[:actual_h, :actual_w], kernel, iterations=1)
            full_mask[y:end_y, x:end_x] = cv2.bitwise_or(
                full_mask[y:end_y, x:end_x], dilated
            )

        radius = max(OPENCV_RADIUS_MIN_PX, max_text_height // OPENCV_RADIUS_DIVISOR)
        inpainted = cv2.inpaint(
            img, full_mask, inpaintRadius=radius, flags=cv2.INPAINT_NS
        )
        return encode_image(inpainted, encoding)

    except Exception as e:
        logger.warning("Failed to erase text with OpenCV: %s", e)
        return _unchanged(image, encoding)


def erase_text_using_lama(
    image: ImageInput, boxes: list[AnalyzedBox], encoding: str = "png"
) -> bytes:
    """Erase the boxes' text with LaMa, falling back to OpenCV on any failure.

    Images larger than ``LAMA_MAX_DIM`` on a side are scaled down for
    inference and the result scaled back up.
    """
    if not boxes:
        return _unchanged(image, encoding)

    lama = get_lama_model()
    if lama is None:
        return erase_text_using_masks(image, boxes, engine="opencv", encoding=encoding)

    img = as_array(image)
    if img is None:
        return _unchanged(image, encoding)
    try:
        img_h, img_w = img.shape[:2]
        scale = 1.0
        if max(img_h, img_w) > LAMA_MAX_DIM:
            scale = LAMA_MAX_DIM / max(img_h, img_w)

        # A rectangle per box, padded: LaMa wants generous masks.
        full_mask = np.zeros((img_h, img_w), dtype=np.uint8)
        for box in boxes:
            x, y = int(box["left_px"]), int(box["top_px"])
            w, h = int(box["width_px"]), int(box["height_px"])
            pad = max(LAMA_PAD_MIN_PX, h // LAMA_PAD_DIVISOR)
            full_mask[
                max(0, y - pad) : min(img_h, y + h + pad),
                max(0, x - pad) : min(img_w, x + w + pad),
            ] = 255

        if scale < 1.0:
            size = (int(img_w * scale), int(img_h * scale))
            img_resized = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
            mask_resized = cv2.resize(full_mask, size, interpolation=cv2.INTER_NEAREST)
        else:
            img_resized, mask_resized = img, full_mask

        pil_image = Image.fromarray(cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB))
        pil_mask = Image.fromarray(mask_resized).convert("L")
        result = lama(pil_image, pil_mask)
        if scale < 1.0:
            result = result.resize((img_w, img_h), Image.Resampling.LANCZOS)

        result_bgr = cv2.cvtColor(np.asarray(result.convert("RGB")), cv2.COLOR_RGB2BGR)
        return encode_image(result_bgr, encoding)

    except Exception as e:
        logger.warning("Failed to erase text using LaMa: %s, falling back to OpenCV", e)
        return erase_text_using_masks(img, boxes, engine="opencv", encoding=encoding)


def _unchanged(image: ImageInput, encoding: str) -> bytes:
    """The input as bytes: as given, or encoded when it arrived as an array."""
    if isinstance(image, np.ndarray):
        return encode_image(image, encoding)
    return image


__all__ = [
    "INPAINT_ENGINES",
    "LAMA_MAX_DIM",
    "erase_text_using_lama",
    "erase_text_using_masks",
    "get_lama_model",
    "reset_lama",
]
