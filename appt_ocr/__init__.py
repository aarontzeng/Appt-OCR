"""
Appt-OCR — Batch PPTX/PDF OCR Processing Tool
===============================================

Extracts images from presentations, performs OCR via PaddleOCR,
reconstructs editable text boxes, and optionally erases detected text
using OpenCV or LaMa inpainting.

Usage as a library::

    from appt_ocr import process_pptx

    stats = process_pptx("input.pptx", "output.pptx")
    print(f"Created {stats['total_textboxes']} text boxes")

Usage as a CLI::

    appt-ocr input.pptx --output-dir output/
    appt-ocr report.pdf --inpaint-engine lama

"""

__version__ = "3.0.0"
__author__ = "Aaron Tzeng"
__license__ = "MIT"

from appt_ocr.ocr import run_ocr_on_image
from appt_ocr.processing import process_pptx, process_slide

__all__ = [
    "process_pptx",
    "process_slide",
    "run_ocr_on_image",
    "__version__",
]
