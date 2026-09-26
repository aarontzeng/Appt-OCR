"""PDF to PPTX preprocessing.

Renders each PDF page with PyMuPDF and wraps the images into a temporary
PPTX, one full-page picture per slide, for the OCR pipeline.
"""

from __future__ import annotations

import io
import logging
import tempfile

import fitz  # PyMuPDF
from pptx import Presentation
from pptx.util import Emu

from appt_ocr.coordinates import EMU_PER_INCH, POINTS_PER_INCH

logger = logging.getLogger(__name__)


def _points_to_emu(points: float) -> int:
    return int(points * EMU_PER_INCH / POINTS_PER_INCH)


def convert_pdf_to_pptx(pdf_path: str, dpi: int = 300) -> str:
    """Convert a PDF file to a temporary PPTX, one page per slide.

    The slide size is the first page's (a presentation has one size); each
    page's picture is placed at its own size from the top-left corner.

    Args:
        pdf_path: Path to the PDF file.
        dpi: Rendering resolution (default 300).

    Returns:
        Path of the generated temporary PPTX (the caller deletes it).

    Raises:
        ValueError: for a PDF with no pages.
    """
    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            raise ValueError(f"{pdf_path}: the PDF has no pages")

        prs = Presentation()
        first_rect = doc[0].rect
        prs.slide_width = _points_to_emu(first_rect.width)  # type: ignore[assignment]
        prs.slide_height = _points_to_emu(first_rect.height)  # type: ignore[assignment]
        blank_layout = prs.slide_layouts[6]

        mat = fitz.Matrix(dpi / POINTS_PER_INCH, dpi / POINTS_PER_INCH)
        for page in doc:
            img_bytes = page.get_pixmap(matrix=mat).tobytes("png")
            slide = prs.slides.add_slide(blank_layout)
            slide.shapes.add_picture(
                io.BytesIO(img_bytes),
                Emu(0),
                Emu(0),
                Emu(_points_to_emu(page.rect.width)),
                Emu(_points_to_emu(page.rect.height)),
            )
        total_pages = doc.page_count

    with tempfile.NamedTemporaryFile(
        suffix=".pptx", delete=False, prefix="pdf2pptx_"
    ) as tmp:
        tmp_path = tmp.name
    prs.save(tmp_path)

    logger.info("PDF conversion complete: %d pages -> %s", total_pages, tmp_path)
    return tmp_path
