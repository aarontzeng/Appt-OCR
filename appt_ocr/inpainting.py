"""Text inpainting engines.

Provides two engines for erasing detected text from images:
- **OpenCV**: Lightweight Navier-Stokes inpainting with pixel-level masks.
- **LaMa**: Deep learning model (Large Mask Inpainting) using Fast Fourier
  Convolutions for superior quality on complex backgrounds.
"""

import io
import logging
from typing import Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Lazily initialized LaMa Inpainting model
_lama_model: Optional[object] = None

# LaMa inference resolution cap — automatically scales down if exceeded
LAMA_MAX_DIM = 2048


def get_lama_model() -> Optional[object]:
    """Retrieve or initialize the LaMa Inpainting model (lazy load).

    On first call, downloads the LaMa model weights automatically from
    HuggingFace (~174 MB, cached in ``~/.cache/huggingface/``).

    Returns:
        SimpleLama instance, or ``None`` if the model fails to load.
    """
    global _lama_model
    if _lama_model is None:
        try:
            from simple_lama_inpainting import SimpleLama

            _lama_model = SimpleLama()
        except Exception as e:
            logger.warning(
                "Failed to load LaMa model: %s, falling back to OpenCV engine", e
            )
            return None
    return _lama_model


def erase_text_using_masks(
    image_bytes: bytes,
    boxes: list[dict],
    engine: str = "opencv",
) -> bytes:
    """Erase text from the image using the designated inpainting engine.

    Uses pixel-level text masks (from ``analyze_text_features``) with dynamic
    dilation and Navier-Stokes inpainting for smooth recovery.

    Args:
        image_bytes: Original image binary content.
        boxes: List of OCR text boxes (must include ``text_mask`` from
               ``analyze_text_features``).
        engine: Inpainting engine — ``"opencv"`` or ``"lama"``.

    Returns:
        Processed image binary content (PNG format).
    """
    if not boxes:
        return image_bytes

    # If LaMa engine is selected, route to the LaMa codepath
    if engine == "lama":
        return erase_text_using_lama(image_bytes, boxes)

    try:
        # Decode original image
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes

        # Create an all-black mask matching the size of the original image
        full_mask = np.zeros(img.shape[:2], dtype=np.uint8)

        max_text_height = 0

        # Paste the precise mask of each box back to the full image mask
        for box in boxes:
            if "text_mask" not in box:
                continue

            x, y = int(box["left_px"]), int(box["top_px"])
            _w, h = int(box["width_px"]), int(box["height_px"])
            x = max(0, x)
            y = max(0, y)
            max_text_height = max(max_text_height, h)

            roi_mask = box["text_mask"]

            # Safety check to prevent shape mismatch
            roi_h, roi_w = roi_mask.shape

            end_y = min(y + roi_h, full_mask.shape[0])
            end_x = min(x + roi_w, full_mask.shape[1])

            actual_h = end_y - y
            actual_w = end_x - x

            if actual_h <= 0 or actual_w <= 0:
                continue

            # Dynamic dilation based on text height
            expand_px = max(2, h // 10)
            kernel = np.ones((expand_px * 2 + 1, expand_px * 2 + 1), np.uint8)

            # Dilate to cover residual anti-aliasing edges
            roi_mask_dilated = cv2.dilate(
                roi_mask[:actual_h, :actual_w], kernel, iterations=1
            )

            # Union the dilated mask with the full image mask
            full_mask[y:end_y, x:end_x] = cv2.bitwise_or(
                full_mask[y:end_y, x:end_x], roi_mask_dilated
            )

        # Dynamic inpaint radius based on max text height
        inpaint_radius = max(3, max_text_height // 8)

        # Use Navier-Stokes algorithm for smoother large-area recovery
        inpainted = cv2.inpaint(
            img, full_mask, inpaintRadius=inpaint_radius, flags=cv2.INPAINT_NS
        )

        # Encode back to PNG
        success, encoded = cv2.imencode(".png", inpainted)
        if success:
            return encoded.tobytes()
        return image_bytes

    except Exception as e:
        logger.warning("Failed to precisely erase text: %s", e)
        return image_bytes


def erase_text_using_lama(image_bytes: bytes, boxes: list[dict]) -> bytes:
    """Use the LaMa deep learning model to erase text from the image.

    LaMa (Large Mask Inpainting) uses Fast Fourier Convolutions to understand
    large-scale structure and textures, excelling at erasing large areas of text.

    If the image dimensions exceed ``LAMA_MAX_DIM``, it scales down before
    inference and then upscales back to avoid Out-of-Memory exceptions.

    Args:
        image_bytes: Original image binary content.
        boxes: List of OCR text boxes.

    Returns:
        Processed image binary content (PNG format).
    """
    if not boxes:
        return image_bytes

    try:
        lama = get_lama_model()
        if lama is None:
            return erase_text_using_masks(image_bytes, boxes, engine="opencv")

        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes

        img_h, img_w = img.shape[:2]

        # Calculate scale factor
        scale = 1.0
        if max(img_h, img_w) > LAMA_MAX_DIM:
            scale = LAMA_MAX_DIM / max(img_h, img_w)

        # Create mask at original resolution
        full_mask = np.zeros((img_h, img_w), dtype=np.uint8)

        # Use full rectangular mask with padding
        for box in boxes:
            x, y = int(box["left_px"]), int(box["top_px"])
            w, h = int(box["width_px"]), int(box["height_px"])

            # Dynamic padding: expand proportionally to box height
            pad = max(3, h // 8)
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(img_w, x + w + pad)
            y2 = min(img_h, y + h + pad)
            full_mask[y1:y2, x1:x2] = 255

        # Scale down if needed
        if scale < 1.0:
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            mask_resized = cv2.resize(
                full_mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST
            )
        else:
            img_resized = img
            mask_resized = full_mask

        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(img_rgb)
        pil_mask = Image.fromarray(mask_resized).convert("L")

        result = lama(pil_image, pil_mask)

        # Scale back up if needed
        if scale < 1.0:
            result = result.resize((img_w, img_h), Image.LANCZOS)

        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return buf.getvalue()

    except Exception as e:
        logger.warning("Failed to erase text using LaMa: %s, falling back to OpenCV", e)
        return erase_text_using_masks(image_bytes, boxes, engine="opencv")
