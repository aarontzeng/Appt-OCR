"""Image processing utilities.

Handles text feature analysis (color, boldness, masks) and image extraction
from python-pptx Picture shapes.
"""

import io
import logging

import cv2
import numpy as np
from PIL import Image
from pptx.shapes.picture import Picture

logger = logging.getLogger(__name__)


def analyze_text_features(
    image_bytes: bytes, box: dict
) -> tuple[tuple[int, int, int], bool, np.ndarray]:
    """Analyze the text color and thickness from a specific area of the image.

    Uses Adaptive Thresholding + union with Otsu to generate a more complete
    text mask, and fills broken strokes using Morphological Closing.
    Calculates the average color based on foreground pixels and density ratio
    (used to determine if bold).

    Args:
        image_bytes: Image binary content.
        box: OCR Bounding Box dictionary containing left_px, top_px,
             width_px, height_px.

    Returns:
        Tuple of:
            - (R, G, B) text color
            - is_bold boolean (whether it is considered bold)
            - text_mask (binary mask with the same dimensions as the cropped
              area, 255 = text foreground, 0 = background)
    """
    default_color = (0, 0, 0)
    default_bold = False

    # Parse Bounding Box coordinates
    x, y = int(box["left_px"]), int(box["top_px"])
    w, h = int(box["width_px"]), int(box["height_px"])
    x = max(0, x)
    y = max(0, y)

    # Create an empty black mask by default
    empty_mask = np.zeros((max(1, h), max(1, w)), dtype=np.uint8)

    try:
        # Decode the image
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return default_color, default_bold, empty_mask

        # Ensure no out-of-bounds array access
        roi = img[y : y + h, x : x + w]
        if roi.size == 0:
            return default_color, default_bold, empty_mask

        # Convert to grayscale
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # Determine the brightness relationship between text and background
        border_mask = np.ones_like(gray, dtype=np.uint8)
        border_mask[1:-1, 1:-1] = 0
        edge_brightness = cv2.mean(gray, mask=border_mask)[0]
        is_dark_bg = edge_brightness < 127

        # Strategy 1: Otsu Global Threshold
        if is_dark_bg:
            _, thresh_otsu = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
        else:
            _, thresh_otsu = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

        # Strategy 2: Adaptive Thresholding (Local Adaptive)
        block_size = max(11, (min(w, h) // 4) | 1)  # Must be odd, at least 11
        if is_dark_bg:
            thresh_adaptive = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                block_size,
                -5,
            )
        else:
            thresh_adaptive = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                block_size,
                5,
            )

        # Merge the two strategies (Union)
        combined = cv2.bitwise_or(thresh_otsu, thresh_adaptive)

        # Morphological Closing: Fill small holes and broken strokes
        close_size = max(2, h // 25)
        close_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (close_size, close_size)
        )
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, close_kernel)

        # Extract text color (use cleaner Otsu mask)
        text_pixels = roi[thresh_otsu == 255]

        avg_color = default_color
        if len(text_pixels) > 0:
            avg_bgr = np.mean(text_pixels, axis=0)
            avg_color = (int(avg_bgr[2]), int(avg_bgr[1]), int(avg_bgr[0]))

        # Calculate boldness (based on Otsu mask as it is more stable)
        pixel_density = len(text_pixels) / (w * h) if (w * h) > 0 else 0
        is_bold = pixel_density > 0.25

        return avg_color, is_bold, combined

    except Exception as e:
        logger.warning("Failed to extract text features: %s", e)
        return default_color, default_bold, empty_mask


def extract_image_from_shape(shape: Picture) -> tuple[bytes, int, int]:
    """Extract image data from a python-pptx Picture Shape.

    Args:
        shape: python-pptx Picture Shape object.

    Returns:
        (image_bytes, width_px, height_px) Image binary data and pixel
        dimensions.
    """
    image_blob = shape.image.blob
    with Image.open(io.BytesIO(image_blob)) as img:
        width_px, height_px = img.size
    return image_blob, width_px, height_px
