"""Coordinate system conversion utilities.

Handles conversions between pixel coordinates, EMU (English Metric Units),
and typographic points for accurate PPTX layout reconstruction.
"""


def px_to_emu(px: float, dpi: int = 96) -> int:
    """Convert pixel values to EMU (English Metric Units).

    PPT internally uses EMU as the base unit for all lengths.
    1 inch = 914400 EMU, therefore: EMU = px * (914400 / dpi)

    Args:
        px: Pixel value.
        dpi: Image pixels per inch, default 96.

    Returns:
        Corresponding EMU integer value.
    """
    return int(px * 914400 / dpi)


def compute_scale_factors(
    img_width_px: int,
    img_height_px: int,
    shape_width_emu: int,
    shape_height_emu: int,
    dpi: int = 96,
) -> tuple[float, float]:
    """Calculate scaling factors from image pixel coordinates to slide EMU coordinates.

    The displayed size of the image on the slide (Shape width/height)
    is usually different from the original image pixel dimensions, requiring scale factors.

    Args:
        img_width_px: Original image width (pixels).
        img_height_px: Original image height (pixels).
        shape_width_emu: Width of the image Shape on the slide (EMU).
        shape_height_emu: Height of the image Shape on the slide (EMU).
        dpi: Image DPI.

    Returns:
        (scale_x, scale_y) Horizontal and vertical scale factors.
    """
    # Convert original image size to EMU
    img_width_emu = px_to_emu(img_width_px, dpi)
    img_height_emu = px_to_emu(img_height_px, dpi)

    # Scale factor = Shape size on slide / Original image EMU size
    scale_x = shape_width_emu / img_width_emu if img_width_emu > 0 else 1.0
    scale_y = shape_height_emu / img_height_emu if img_height_emu > 0 else 1.0

    return scale_x, scale_y


def estimate_font_size(
    height_px: float,
    scale_y: float = 1.0,
    dpi: int = 96,
) -> float:
    """Dynamically estimate the font size (Pt) based on the Bounding Box height.

    Relationship between font size (Points) and pixels:
      Pt = px * (72 / DPI)

    Taking into account the slide scaling ratio, the final formula is:
      Pt = height_px * (72 / DPI) * scale_y

    To avoid excessively small or large font sizes, limit it to 6pt ~ 72pt.

    Args:
        height_px: Bounding Box height (pixels).
        scale_y: Vertical scaling ratio.
        dpi: Image DPI.

    Returns:
        Estimated font size (Pt), constrained between 6 and 72.
    """
    # OCR bounding box height includes upper and lower padding,
    # the actual text glyph occupies about 72%
    pt = height_px * (72 / dpi) * scale_y * 0.72
    return max(6.0, min(72.0, pt))
