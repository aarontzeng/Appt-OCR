"""pytest fixtures.

The heavy engines are never loaded in tests. ``fake_paddle`` installs a stand-in
``paddleocr`` module whose engine returns whatever lines a test scripts, so the
whole pipeline runs for real on small rendered images and every assertion is
about this package's own behaviour.
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import types
from dataclasses import dataclass, field
from typing import Any

import pytest
from PIL import Image, ImageDraw

from appt_ocr import inpainting, ocr


def png_bytes(size=(100, 100), color=(255, 0, 0)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def text_image(
    text: str, size=(300, 100), fg=(0, 0, 0), bg=(255, 255, 255), at=(20, 30)
):
    """A white image with ``text`` drawn on it, and the box the glyphs occupy.

    Returns ``(png_bytes, box)`` where the box is in the OcrBox dict shape.
    """
    img = Image.new("RGB", size, color=bg)
    draw = ImageDraw.Draw(img)
    draw.text(at, text, fill=fg)
    left, top, right, bottom = draw.textbbox(at, text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    box = {
        "left_px": float(left),
        "top_px": float(top),
        "width_px": float(right - left),
        "height_px": float(bottom - top),
        "text": text,
        "confidence": 0.99,
    }
    return buf.getvalue(), box


def paddle_line(box, text, confidence=0.99):
    """One PaddleOCR result line for a box: four corners, then (text, score)."""
    x, y = box["left_px"], box["top_px"]
    w, h = box["width_px"], box["height_px"]
    return [[[x, y], [x + w, y], [x + w, y + h], [x, y + h]], (text, confidence)]


@dataclass
class FakePaddle:
    """Controller for the stand-in engine: what it returns and what it saw."""

    lines: list = field(default_factory=list)
    constructed: list = field(default_factory=list)  # langs an engine was built for
    seen: list = field(default_factory=list)  # (lang, image shape) per ocr() call

    def returns(self, *lines) -> None:
        self.lines = list(lines)


@pytest.fixture
def fake_paddle(monkeypatch):
    controller = FakePaddle()

    class PaddleOCR:
        def __init__(self, lang="ch", **kwargs):
            self.lang = lang
            controller.constructed.append(lang)

        def ocr(self, img, cls=True):
            controller.seen.append((self.lang, getattr(img, "shape", None)))
            return [list(controller.lines)] if controller.lines else [None]

    module = types.ModuleType("paddleocr")
    module.PaddleOCR = PaddleOCR  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "paddleocr", module)
    ocr.reset_engines()
    inpainting.reset_lama()
    yield controller
    ocr.reset_engines()
    inpainting.reset_lama()


@pytest.fixture
def no_lama(monkeypatch):
    """Make ``import simple_lama_inpainting`` fail, whatever is installed."""
    monkeypatch.setitem(sys.modules, "simple_lama_inpainting", None)
    inpainting.reset_lama()
    yield
    inpainting.reset_lama()


@pytest.fixture
def sample_image_bytes():
    """A plain red 100x100 PNG."""
    return png_bytes()


@pytest.fixture
def sample_ocr_result():
    return {
        "left_px": 10.0,
        "top_px": 20.0,
        "width_px": 80.0,
        "height_px": 25.0,
        "text": "Hello World",
        "confidence": 0.95,
    }


@pytest.fixture
def sample_ocr_results():
    return [
        {
            "left_px": 10.0,
            "top_px": 20.0,
            "width_px": 80.0,
            "height_px": 25.0,
            "text": "Hello",
            "confidence": 0.95,
        },
        {
            "left_px": 100.0,
            "top_px": 20.0,
            "width_px": 80.0,
            "height_px": 25.0,
            "text": "World",
            "confidence": 0.92,
        },
    ]


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def make_deck(
    path: str,
    image_bytes: bytes,
    *,
    left=914400,
    top=914400,
    width=None,
    height=None,
    crop=None,
):
    """A one-slide deck with one picture; returns the python-pptx Presentation."""
    from pptx import Presentation
    from pptx.util import Emu

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    pic = slide.shapes.add_picture(
        io.BytesIO(image_bytes),
        Emu(left),
        Emu(top),
        Emu(width) if width else None,
        Emu(height) if height else None,
    )
    for name, value in (crop or {}).items():
        setattr(pic, name, value)
    prs.save(path)
    return prs


@pytest.fixture
def sample_pptx_path(temp_dir):
    """A deck whose one picture is a 200x150 blue image at 4 inches wide."""
    path = os.path.join(temp_dir, "test.pptx")
    make_deck(path, png_bytes((200, 150), (100, 150, 200)), width=4 * 914400)
    return path


@pytest.fixture
def sample_pdf_path(temp_dir):
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=200, height=150)
    page.insert_text((10, 10), "Test PDF Content", fontsize=12)
    pdf_path = os.path.join(temp_dir, "test.pdf")
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def picture_shapes(slide) -> list[Any]:
    from pptx.shapes.picture import Picture

    return [s for s in slide.shapes if isinstance(s, Picture)]


def text_shapes(slide) -> list[Any]:
    return [s for s in slide.shapes if s.has_text_frame]
