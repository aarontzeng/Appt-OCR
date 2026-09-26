"""Tests for inpainting.py"""

import sys
import types

import numpy as np
import pytest
from PIL import Image

from appt_ocr import inpainting
from appt_ocr.image import decode_image
from appt_ocr.inpainting import (
    LAMA_MAX_DIM,
    erase_text_using_lama,
    erase_text_using_masks,
    get_lama_model,
)
from tests.conftest import png_bytes, text_image


def masked_box(left=10.0, top=10.0, width=30.0, height=20.0):
    return {
        "left_px": left,
        "top_px": top,
        "width_px": width,
        "height_px": height,
        "text": "Test",
        "confidence": 0.95,
        "text_mask": np.full((int(height), int(width)), 255, dtype=np.uint8),
    }


@pytest.fixture
def fake_lama(monkeypatch):
    """A stand-in simple_lama_inpainting whose model paints the mask white."""
    calls = []

    class SimpleLama:
        def __call__(self, image, mask):
            calls.append((image.size, mask.size))
            arr = np.array(image)
            arr[np.array(mask) > 0] = 255
            return Image.fromarray(arr)

    module = types.ModuleType("simple_lama_inpainting")
    module.SimpleLama = SimpleLama  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "simple_lama_inpainting", module)
    inpainting.reset_lama()
    yield calls
    inpainting.reset_lama()


class TestGetLamaModel:
    def test_unavailable_is_none_and_tried_once(self, no_lama, caplog):
        assert get_lama_model() is None
        assert get_lama_model() is None
        assert caplog.text.count("LaMa is not available") == 1

    def test_available_is_cached(self, fake_lama):
        m1 = get_lama_model()
        assert m1 is not None and get_lama_model() is m1


class TestEraseTextUsingMasks:
    def test_empty_boxes_return_the_input(self, sample_image_bytes):
        assert (
            erase_text_using_masks(sample_image_bytes, [], engine="opencv")
            == sample_image_bytes
        )

    def test_unknown_engine_is_refused(self, sample_image_bytes):
        with pytest.raises(ValueError, match="unknown inpaint engine"):
            erase_text_using_masks(sample_image_bytes, [masked_box()], engine="magic")

    def test_opencv_erases_the_masked_text(self):
        image, box = text_image("Hello")
        arr = decode_image(image)
        x, y, w, h = (
            int(box[k]) for k in ("left_px", "top_px", "width_px", "height_px")
        )
        assert arr[y : y + h, x : x + w].mean() < 240  # there is ink
        mask = (255 - arr[y : y + h, x : x + w].mean(axis=2)).astype(np.uint8)
        mask[mask > 0] = 255
        result = erase_text_using_masks(
            image, [dict(box, text_mask=mask)], engine="opencv"
        )
        out = decode_image(result)
        assert out.shape == arr.shape
        assert out[y : y + h, x : x + w].mean() > 240

    def test_accepts_an_array(self, sample_image_bytes):
        arr = decode_image(sample_image_bytes)
        result = erase_text_using_masks(arr, [masked_box()], engine="opencv")
        assert isinstance(result, bytes) and decode_image(result).shape == arr.shape

    def test_a_box_without_a_mask_is_skipped(self, sample_image_bytes):
        box = masked_box()
        del box["text_mask"]
        assert isinstance(
            erase_text_using_masks(sample_image_bytes, [box], engine="opencv"), bytes
        )

    def test_a_box_outside_the_image_is_skipped(self, sample_image_bytes):
        result = erase_text_using_masks(
            sample_image_bytes, [masked_box(left=500.0, top=500.0)], engine="opencv"
        )
        assert decode_image(result).shape == (100, 100, 3)

    def test_undecodable_input_is_returned_unchanged(self):
        assert (
            erase_text_using_masks(b"garbage", [masked_box()], engine="opencv")
            == b"garbage"
        )

    def test_jpeg_encoding(self, sample_image_bytes):
        result = erase_text_using_masks(
            sample_image_bytes, [masked_box()], engine="opencv", encoding="jpg"
        )
        assert result[:3] == b"\xff\xd8\xff"
        png = erase_text_using_masks(
            sample_image_bytes, [masked_box()], engine="opencv"
        )
        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_lama_engine_falls_back_to_opencv_when_unavailable(
        self, no_lama, sample_image_bytes
    ):
        result = erase_text_using_masks(
            sample_image_bytes, [masked_box()], engine="lama"
        )
        assert isinstance(result, bytes) and decode_image(result).shape == (100, 100, 3)


class TestEraseTextUsingLama:
    def test_the_model_paints_the_padded_box(self, fake_lama):
        image, box = text_image("Hello")
        result = erase_text_using_lama(image, [box])
        out = decode_image(result)
        x, y, w, h = (
            int(box[k]) for k in ("left_px", "top_px", "width_px", "height_px")
        )
        assert out[y : y + h, x : x + w].min() == 255
        assert fake_lama == [((300, 100), (300, 100))]

    def test_large_images_are_scaled_for_inference_and_back(
        self, fake_lama, monkeypatch
    ):
        monkeypatch.setattr(inpainting, "LAMA_MAX_DIM", 150)
        image, box = text_image("Hello")
        result = erase_text_using_lama(image, [box])
        assert fake_lama[0][0] == (150, 50)  # inference at the cap
        assert decode_image(result).shape == (100, 300, 3)  # output at full size
        assert LAMA_MAX_DIM == 2048

    def test_a_failing_model_falls_back_to_opencv(self, fake_lama, monkeypatch):
        monkeypatch.setattr(inpainting, "_lama_model", lambda image, mask: 1 / 0)
        png = png_bytes()
        result = erase_text_using_lama(png, [masked_box()])
        assert isinstance(result, bytes) and result != png

    def test_lama_encodes_jpeg_when_asked(self, fake_lama):
        image, box = text_image("Hello")
        assert (
            erase_text_using_lama(image, [box], encoding="jpeg")[:3] == b"\xff\xd8\xff"
        )
