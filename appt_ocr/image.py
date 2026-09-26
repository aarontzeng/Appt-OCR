"""Image utilities.

Decoding and encoding in one place, text feature analysis (color, boldness,
mask), and what a python-pptx Picture shape actually shows of its image.
"""

from __future__ import annotations

import io
import logging
from typing import Union

import cv2
import numpy as np
from PIL import Image
from pptx.shapes.picture import Picture

from appt_ocr.boxes import OcrBox

logger = logging.getLogger(__name__)

ImageInput = Union[bytes, np.ndarray]

# A region whose text pixels cover more than this share of its area is bold.
BOLD_PIXEL_DENSITY = 0.25
# Adaptive threshold: block size is a quarter of the shorter side, at least 11
# (and odd, as OpenCV requires); C is the constant subtracted from the mean.
ADAPTIVE_MIN_BLOCK = 11
ADAPTIVE_C = 5
# Morphological closing kernel: a 25th of the text height, at least 2 px.
CLOSE_KERNEL_DIVISOR = 25
# A border this bright (0-255 gray) means dark text on a light background.
LIGHT_BACKGROUND_THRESHOLD = 127
JPEG_QUALITY = 92


def decode_image(image_bytes: bytes) -> np.ndarray | None:
    """Decode PNG/JPEG/BMP/TIFF bytes to a BGR array, or None if OpenCV cannot.

    This is the only decode in the package: until 3.1.0 every stage decoded
    the same image again, once per text box in ``analyze_text_features``.
    """
    arr = np.frombuffer(image_bytes, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def as_array(image: ImageInput) -> np.ndarray | None:
    """The BGR array for bytes or an array already decoded."""
    if isinstance(image, np.ndarray):
        return image
    return decode_image(image)


def encode_image(img: np.ndarray, encoding: str = "png") -> bytes:
    """Encode a BGR array as PNG, or as JPEG when ``encoding`` is jpg/jpeg.

    Keeping a JPEG source as JPEG matters for PDF pages rendered at 300 DPI:
    the same page as PNG is several times the size, and the output deck
    carries one per slide.
    """
    if encoding.lower() in ("jpg", "jpeg"):
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    else:
        ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ValueError(f"could not encode image as {encoding}")
    return buf.tobytes()


def analyze_text_features(
    image: ImageInput, box: OcrBox
) -> tuple[tuple[int, int, int], bool, np.ndarray]:
    """Analyze the text color and thickness inside one box.

    Uses Adaptive Thresholding unioned with Otsu to build a text mask, fills
    broken strokes with a morphological closing, and takes the average color
    of the foreground pixels and their density (the boldness cue).

    Args:
        image: The whole image the box was detected on: encoded bytes, or the
            BGR array from ``decode_image`` (preferred, so the image is
            decoded once per slide rather than once per box).
        box: OCR bounding box with left_px, top_px, width_px, height_px.

    Returns:
        ``((R, G, B), is_bold, text_mask)`` where the mask has the cropped
        region's shape, 255 = text foreground, 0 = background.
    """
    default_color = (0, 0, 0)
    default_bold = False

    x, y = max(0, int(box["left_px"])), max(0, int(box["top_px"]))
    w, h = int(box["width_px"]), int(box["height_px"])
    empty_mask = np.zeros((max(1, h), max(1, w)), dtype=np.uint8)

    try:
        img = as_array(image)
        if img is None:
            return default_color, default_bold, empty_mask

        roi = img[y : y + h, x : x + w]
        if roi.size == 0:
            return default_color, default_bold, empty_mask

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # Text is whatever differs from the border; the border says which way.
        border_mask = np.ones_like(gray, dtype=np.uint8)
        border_mask[1:-1, 1:-1] = 0
        edge_brightness = cv2.mean(gray, mask=border_mask)[0]
        is_dark_bg = edge_brightness < LIGHT_BACKGROUND_THRESHOLD
        binary = cv2.THRESH_BINARY if is_dark_bg else cv2.THRESH_BINARY_INV

        # Strategy 1: Otsu, global. Strategy 2: adaptive, local. Union both.
        _, thresh_otsu = cv2.threshold(gray, 0, 255, binary + cv2.THRESH_OTSU)
        block_size = max(ADAPTIVE_MIN_BLOCK, (min(w, h) // 4) | 1)
        thresh_adaptive = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            binary,
            block_size,
            -ADAPTIVE_C if is_dark_bg else ADAPTIVE_C,
        )
        combined = cv2.bitwise_or(thresh_otsu, thresh_adaptive)

        close_size = max(2, h // CLOSE_KERNEL_DIVISOR)
        close_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (close_size, close_size)
        )
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, close_kernel)

        # Color and boldness come from the cleaner Otsu mask.
        text_pixels = roi[thresh_otsu == 255]
        avg_color = default_color
        if len(text_pixels) > 0:
            avg_bgr = np.mean(text_pixels, axis=0)  # type: ignore[call-overload]
            avg_color = (int(avg_bgr[2]), int(avg_bgr[1]), int(avg_bgr[0]))
        area = roi.shape[0] * roi.shape[1]
        is_bold = (len(text_pixels) / area if area else 0) > BOLD_PIXEL_DENSITY

        return avg_color, is_bold, combined

    except Exception as e:
        logger.warning("Failed to extract text features: %s", e)
        return default_color, default_bold, empty_mask


def extract_image_from_shape(shape: Picture) -> tuple[bytes, int, int]:
    """The image data of a python-pptx Picture shape and its pixel size.

    Raises:
        PIL.UnidentifiedImageError: for a format Pillow cannot read (WMF,
            EMF, SVG); the pipeline skips such pictures with a warning.
    """
    image_blob = shape.image.blob
    with Image.open(io.BytesIO(image_blob)) as img:
        width_px, height_px = img.size
    return image_blob, width_px, height_px


def visible_region(
    shape: Picture, width_px: int, height_px: int
) -> tuple[int, int, int, int]:
    """The part of the image the shape actually shows, as ``(x0, y0, x1, y1)``.

    A cropped picture in a deck keeps its full image and shows a window of
    it (python-pptx ``crop_left`` etc., fractions of the full size). OCR has
    to run on that window and its coordinates map onto the shape's rectangle;
    until 3.1.0 the whole image was used, so every text box on a cropped
    picture landed in the wrong place and the crop was lost on replacement.
    A negative crop (space around the image) is treated as zero.
    """
    left = min(max(shape.crop_left or 0.0, 0.0), 1.0)
    right = min(max(shape.crop_right or 0.0, 0.0), 1.0)
    top = min(max(shape.crop_top or 0.0, 0.0), 1.0)
    bottom = min(max(shape.crop_bottom or 0.0, 0.0), 1.0)
    x0 = int(round(width_px * left))
    x1 = int(round(width_px * (1.0 - right)))
    y0 = int(round(height_px * top))
    y1 = int(round(height_px * (1.0 - bottom)))
    return x0, y0, max(x0, x1), max(y0, y1)
