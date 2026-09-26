"""Coordinate system conversion utilities.

Conversions between pixel coordinates, EMU (English Metric Units) and
typographic points, for placing text boxes where the image had the text.
"""

EMU_PER_INCH = 914400
POINTS_PER_INCH = 72
# An OCR box includes the line's ascender and descender space; the glyphs
# themselves take about this share of its height.
GLYPH_HEIGHT_RATIO = 0.72
MIN_FONT_PT = 6.0
MAX_FONT_PT = 72.0


def px_to_emu(px: float, dpi: int = 96) -> int:
    """Convert pixels to EMU: 1 inch = 914400 EMU, so EMU = px * 914400 / dpi."""
    return int(px * EMU_PER_INCH / dpi)


def compute_scale_factors(
    img_width_px: int,
    img_height_px: int,
    shape_width_emu: int,
    shape_height_emu: int,
    dpi: int = 96,
) -> tuple[float, float]:
    """Scale factors from image pixels (as EMU at ``dpi``) to the shape's size.

    The image's displayed size on the slide usually differs from its pixel
    size, so a coordinate converted with ``px_to_emu`` is scaled by these.

    Returns:
        ``(scale_x, scale_y)``; 1.0 for a zero-sized image.
    """
    img_width_emu = px_to_emu(img_width_px, dpi)
    img_height_emu = px_to_emu(img_height_px, dpi)
    scale_x = shape_width_emu / img_width_emu if img_width_emu > 0 else 1.0
    scale_y = shape_height_emu / img_height_emu if img_height_emu > 0 else 1.0
    return scale_x, scale_y


def estimate_font_size(
    height_px: float,
    scale_y: float = 1.0,
    dpi: int = 96,
) -> float:
    """Estimate the font size (pt) from a box height.

    ``pt = height_px * (72 / dpi) * scale_y * GLYPH_HEIGHT_RATIO``, clamped
    to 6-72 pt so a stray box cannot produce an unreadable size.
    """
    pt = height_px * (POINTS_PER_INCH / dpi) * scale_y * GLYPH_HEIGHT_RATIO
    return max(MIN_FONT_PT, min(MAX_FONT_PT, pt))
