"""Core slide and PPTX processing orchestration.

The pipeline per picture: decode once -> OCR -> merge boxes -> classify by
regex -> analyze appearance -> inpaint and replace the picture -> add text
boxes. ``ProcessingOptions`` carries the settings; the public functions keep
their keyword arguments and build one.
"""

from __future__ import annotations

import io
import logging
import os
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
from PIL import UnidentifiedImageError
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.shapes.picture import Picture
from pptx.slide import Slide
from pptx.util import Emu, Pt
from tqdm import tqdm

from appt_ocr.boxes import AnalyzedBox, OcrBox
from appt_ocr.coordinates import (
    GLYPH_HEIGHT_RATIO,
    compute_scale_factors,
    estimate_font_size,
    px_to_emu,
)
from appt_ocr.image import (
    analyze_text_features,
    decode_image,
    extract_image_from_shape,
    visible_region,
)
from appt_ocr.inpainting import INPAINT_ENGINES, erase_text_using_masks
from appt_ocr.merging import merge_nearby_boxes
from appt_ocr.ocr import get_opencc_converter, run_ocr_on_image

logger = logging.getLogger(__name__)

# A box of two or more characters that is much taller than wide, and tall
# enough to matter, is vertical text: a horizontal text box cannot hold it.
# A single glyph is exempt: "1", "I" and "l" are narrower than 1/1.5 of
# their height and were dropped until 3.1.0.
VERTICAL_ASPECT_RATIO = 1.5
VERTICAL_MIN_HEIGHT_PX = 50
# Text that would need more than this multiple of the box's width to be laid
# out at the box's height is a mis-merge, not a line.
MAX_TEXT_DENSITY = 2.5
AVG_GLYPH_WIDTH_RATIO = 0.55
# A watermark box is erased with this much margin, as a share of its size.
WATERMARK_PAD_X = 0.2
WATERMARK_PAD_Y = 0.15
# A text box is made wider than the OCR box so PowerPoint does not wrap it.
TEXTBOX_WIDTH_PAD = 1.15
JPEG_EXTENSIONS = ("jpg", "jpeg")


@dataclass
class ProcessingOptions:
    """Everything the pipeline needs, validated once.

    Raises ``ValueError`` on construction for an unknown ``inpaint_engine``,
    a non-positive ``dpi`` or an invalid regular expression, so a bad option
    is reported before any model is loaded or any file opened.
    """

    dpi: int = 96
    lang: str = "ch"
    keep_images: bool = False
    merge_threshold: float = 0.5
    ignore_re: str = ""
    remove_re: str = ""
    inpaint_engine: str = "lama"
    watermark_only: bool = False
    s2t: bool = False
    ignore_pattern: re.Pattern[str] | None = field(init=False, repr=False, default=None)
    remove_pattern: re.Pattern[str] | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        if self.inpaint_engine not in INPAINT_ENGINES:
            raise ValueError(
                f"inpaint_engine must be one of {INPAINT_ENGINES}, got {self.inpaint_engine!r}"
            )
        if self.dpi <= 0:
            raise ValueError(f"dpi must be positive, got {self.dpi}")
        self.ignore_pattern = _compile(self.ignore_re, "ignore_re")
        self.remove_pattern = _compile(self.remove_re, "remove_re")

    def with_engine(self, engine: str) -> ProcessingOptions:
        """A copy using another inpainting engine (the CLI's LaMa fallback)."""
        return replace(self, inpaint_engine=engine)


def _compile(pattern: str, name: str) -> re.Pattern[str] | None:
    if not pattern:
        return None
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise ValueError(
            f"{name}: invalid regular expression {pattern!r}: {exc}"
        ) from None


def process_slide(
    slide: Slide,
    dpi: int = 96,
    lang: str = "ch",
    keep_images: bool = False,
    merge_threshold: float = 0.5,
    ignore_re: str = "",
    remove_re: str = "",
    inpaint_engine: str = "lama",
    watermark_only: bool = False,
    s2t: bool = False,
    options: ProcessingOptions | None = None,
) -> int:
    """Process a single slide: for every picture, OCR its text into text boxes.

    Args:
        slide: python-pptx Slide object.
        dpi: Image DPI setting.
        lang: OCR language.
        keep_images: Whether to keep the original image.
        merge_threshold: Text box merging threshold.
        ignore_re: Regex for text to keep in background (no text box).
        remove_re: Regex for text to erase silently (no text box).
        inpaint_engine: ``"lama"`` or ``"opencv"``.
        watermark_only: If True, only erase text matching ``remove_re``.
        s2t: If True, convert simplified to traditional Chinese.
        options: A prepared ``ProcessingOptions``; when given, the keyword
            arguments above are ignored.

    Returns:
        Number of text boxes created on this slide.

    Raises:
        ValueError: for an invalid option (see ``ProcessingOptions``).
    """
    opts = options or ProcessingOptions(
        dpi=dpi,
        lang=lang,
        keep_images=keep_images,
        merge_threshold=merge_threshold,
        ignore_re=ignore_re,
        remove_re=remove_re,
        inpaint_engine=inpaint_engine,
        watermark_only=watermark_only,
        s2t=s2t,
    )
    # Collect first: processing replaces pictures while iterating would not do.
    pictures = [shape for shape in slide.shapes if isinstance(shape, Picture)]
    total = 0
    for picture in pictures:
        total += _process_picture(slide, picture, opts)
    return total


def _process_picture(slide: Slide, picture: Picture, opts: ProcessingOptions) -> int:
    """OCR one picture into text boxes; returns how many were created."""
    if picture.rotation:
        logger.warning(
            "%s: skipped, rotated by %.1f degrees (text boxes would not follow)",
            picture.name,
            picture.rotation,
        )
        return 0
    try:
        image_blob, img_w, img_h = extract_image_from_shape(picture)
    except UnidentifiedImageError:
        logger.warning(
            "%s: skipped, image format not supported (%s)",
            picture.name,
            picture.image.ext,
        )
        return 0
    img = decode_image(image_blob)
    if img is None:
        logger.warning(
            "%s: skipped, OpenCV cannot decode a %s", picture.name, picture.image.ext
        )
        return 0

    # OCR the part the shape shows; coordinates then map onto the shape's box.
    x0, y0, x1, y1 = visible_region(picture, img_w, img_h)
    if x1 - x0 <= 0 or y1 - y0 <= 0:
        return 0
    if (x0, y0, x1, y1) != (0, 0, img_w, img_h):
        img = np.ascontiguousarray(img[y0:y1, x0:x1])
    shape_left, shape_top = picture.left, picture.top
    scale_x, scale_y = compute_scale_factors(
        x1 - x0, y1 - y0, picture.width, picture.height, opts.dpi
    )

    ocr_results = run_ocr_on_image(img, opts.lang)
    if not ocr_results:
        return 0
    kept, erase = _classify_boxes(
        merge_nearby_boxes(ocr_results, opts.merge_threshold), opts
    )

    for box in _unique(kept + erase):
        color, is_bold, mask = analyze_text_features(img, box)
        box["color"] = color
        box["is_bold"] = is_bold
        box["text_mask"] = mask

    if erase and not opts.keep_images:
        encoding = "jpeg" if picture.image.ext.lower() in JPEG_EXTENSIONS else "png"
        new_bytes = erase_text_using_masks(
            img, erase, engine=opts.inpaint_engine, encoding=encoding
        )
        _replace_picture(slide, picture, new_bytes)

    for box in kept:
        _add_text_box(slide, box, shape_left, shape_top, scale_x, scale_y, opts)
    return len(kept)


def _looks_unusable(box: OcrBox, text: str) -> bool:
    """Vertical text, or a box whose text cannot fit it (a mis-merge)."""
    w, h = box["width_px"], box["height_px"]
    if len(text) >= 2 and h > w * VERTICAL_ASPECT_RATIO and h > VERTICAL_MIN_HEIGHT_PX:
        return True
    needed_width = len(text) * h * AVG_GLYPH_WIDTH_RATIO * GLYPH_HEIGHT_RATIO
    return w > 0 and needed_width / w > MAX_TEXT_DENSITY


def _classify_boxes(
    merged: list[OcrBox], opts: ProcessingOptions
) -> tuple[list[AnalyzedBox], list[AnalyzedBox]]:
    """Split merged boxes into those that become text boxes and those erased.

    A regular box is in both lists (same dict). A ``remove_re`` match is
    erased with a margin and gets no text box; an ``ignore_re`` match, and
    everything else in watermark-only mode, is left in the image untouched.
    """
    kept: list[AnalyzedBox] = []
    erase: list[AnalyzedBox] = []
    for item in merged:
        text = item["text"].strip()
        if not text or _looks_unusable(item, text):
            continue
        box: AnalyzedBox = item  # type: ignore[assignment]
        if opts.remove_pattern and opts.remove_pattern.search(text):
            pad_x = int(box["width_px"] * WATERMARK_PAD_X)
            pad_y = int(box["height_px"] * WATERMARK_PAD_Y)
            box["left_px"] = max(0, box["left_px"] - pad_x)
            box["top_px"] = max(0, box["top_px"] - pad_y)
            box["width_px"] += pad_x * 2
            box["height_px"] += pad_y * 2
            erase.append(box)
        elif opts.watermark_only:
            continue
        elif opts.ignore_pattern and opts.ignore_pattern.search(text):
            continue
        else:
            kept.append(box)
            erase.append(box)
    return kept, erase


def _unique(boxes: list[AnalyzedBox]) -> list[AnalyzedBox]:
    seen: set[int] = set()
    unique: list[AnalyzedBox] = []
    for box in boxes:
        if id(box) not in seen:
            seen.add(id(box))
            unique.append(box)
    return unique


def _replace_picture(slide: Slide, old: Picture, new_bytes: bytes) -> None:
    """Put the inpainted image where the old picture was, at the same depth.

    ``add_picture`` appends at the top of the z-order; until 3.1.0 the new
    picture therefore covered every shape that used to sit above the old one
    (a logo, a title box). The new element is moved in front of the old one
    in the shape tree, then the old one is removed.
    """
    new = slide.shapes.add_picture(
        io.BytesIO(new_bytes), old.left, old.top, old.width, old.height
    )
    new.name = old.name
    old_element = old._element
    old_element.addprevious(new._element)
    old_element.getparent().remove(old_element)


def _add_text_box(
    slide: Slide,
    box: AnalyzedBox,
    shape_left: int,
    shape_top: int,
    scale_x: float,
    scale_y: float,
    opts: ProcessingOptions,
) -> None:
    left_emu = int(px_to_emu(box["left_px"], opts.dpi) * scale_x) + shape_left
    top_emu = int(px_to_emu(box["top_px"], opts.dpi) * scale_y) + shape_top
    width_emu = max(
        int(px_to_emu(box["width_px"], opts.dpi) * scale_x * TEXTBOX_WIDTH_PAD), 1
    )
    height_emu = max(int(px_to_emu(box["height_px"], opts.dpi) * scale_y), 1)

    txbox = slide.shapes.add_textbox(
        Emu(left_emu), Emu(top_emu), Emu(width_emu), Emu(height_emu)
    )
    tf = txbox.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Emu(0)

    text = box["text"]
    if opts.s2t:
        converter = get_opencc_converter()
        if converter:
            text = converter.convert(text)
    paragraph = tf.paragraphs[0]
    paragraph.text = text
    paragraph.alignment = PP_ALIGN.LEFT

    font_pt = estimate_font_size(box["height_px"], scale_y, opts.dpi)
    r, g, b = box.get("color", (0, 0, 0))
    for run in paragraph.runs:
        run.font.size = Pt(font_pt)
        run.font.color.rgb = RGBColor(r, g, b)
        run.font.bold = box.get("is_bold", False)


def process_pptx(
    input_path: str,
    output_path: str,
    dpi: int = 96,
    lang: str = "ch",
    keep_images: bool = False,
    merge_threshold: float = 0.5,
    ignore_re: str = "",
    remove_re: str = "",
    inpaint_engine: str = "lama",
    watermark_only: bool = False,
    s2t: bool = False,
    options: ProcessingOptions | None = None,
) -> dict:
    """Process a PPTX file: OCR every picture on every slide into text boxes.

    Args:
        input_path: Input PPTX file path.
        output_path: Output PPTX file path (its directory is created).
        dpi: Image DPI.
        lang: OCR language (``'ch'`` bilingual / ``'en'`` English only).
        keep_images: Whether to keep original image Shapes.
        merge_threshold: Text box merging threshold.
        ignore_re: Regex for text to keep in background.
        remove_re: Regex for text to erase silently.
        inpaint_engine: ``"lama"`` or ``"opencv"``.
        watermark_only: If True, only erase text matching ``remove_re``.
        s2t: If True, convert simplified to traditional Chinese.
        options: A prepared ``ProcessingOptions``; when given, the keyword
            arguments above are ignored.

    Returns:
        Statistics: ``input``, ``output``, ``total_slides``,
        ``processed_slides`` (slides that got at least one text box) and
        ``total_textboxes``.

    Raises:
        ValueError: for an invalid option (see ``ProcessingOptions``).
        pptx.exc.PackageNotFoundError: when ``input_path`` is not a PPTX.
    """
    opts = options or ProcessingOptions(
        dpi=dpi,
        lang=lang,
        keep_images=keep_images,
        merge_threshold=merge_threshold,
        ignore_re=ignore_re,
        remove_re=remove_re,
        inpaint_engine=inpaint_engine,
        watermark_only=watermark_only,
        s2t=s2t,
    )
    prs = Presentation(input_path)

    total_slides = len(prs.slides)
    processed_slides = 0
    total_textboxes = 0

    for slide in tqdm(
        prs.slides, desc=f"  Processing {Path(input_path).name}", unit="page"
    ):
        num_boxes = process_slide(slide, options=opts)
        if num_boxes > 0:
            processed_slides += 1
        total_textboxes += num_boxes

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    prs.save(output_path)

    return {
        "input": input_path,
        "output": output_path,
        "total_slides": total_slides,
        "processed_slides": processed_slides,
        "total_textboxes": total_textboxes,
    }
