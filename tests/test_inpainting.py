"""Tests for inpainting.py"""

import io

import numpy as np
from PIL import Image

from appt_ocr.inpainting import (
    erase_text_using_masks,
    get_lama_model,
)


class TestGetLamaModel:
    """Test LaMa model initialization."""

    def test_get_lama_model_returns_object_or_none(self):
        """Test that LaMa model is available or returns None gracefully."""
        model = get_lama_model()
        # Could be None if not installed, or a callable object if installed
        assert model is None or callable(model)

    def test_get_lama_model_caches_result(self):
        """Test that subsequent calls return cached instance."""
        model1 = get_lama_model()
        model2 = get_lama_model()
        assert model1 is model2


class TestEraseTextUsingMasks:
    """Test text erasing functionality."""

    def test_erase_text_empty_boxes(self, sample_image_bytes):
        """Test erasing with empty box list."""
        result = erase_text_using_masks(sample_image_bytes, [], engine="opencv")
        # Should return original or processed image
        assert isinstance(result, bytes)

    def test_erase_text_opencv_engine(self, sample_image_bytes):
        """Test text erasing with OpenCV engine."""
        boxes = [
            {
                "left_px": 10.0,
                "top_px": 10.0,
                "width_px": 30.0,
                "height_px": 20.0,
                "text": "Test",
                "confidence": 0.95,
                "text_mask": np.zeros((20, 30), dtype=np.uint8),
            }
        ]
        result = erase_text_using_masks(sample_image_bytes, boxes, engine="opencv")
        assert isinstance(result, bytes)

    def test_erase_text_lama_not_available(self, sample_image_bytes):
        """Test text erasing with LaMa engine when not available."""
        boxes = [
            {
                "left_px": 10.0,
                "top_px": 10.0,
                "width_px": 30.0,
                "height_px": 20.0,
                "text": "Test",
                "confidence": 0.95,
                "text_mask": np.zeros((20, 30), dtype=np.uint8),
            }
        ]
        # Should handle gracefully if LaMa is not installed
        result = erase_text_using_masks(sample_image_bytes, boxes, engine="lama")
        assert isinstance(result, bytes)

    def test_erase_text_invalid_image(self):
        """Test text erasing with invalid image."""
        boxes = [
            {
                "left_px": 10.0,
                "top_px": 10.0,
                "width_px": 30.0,
                "height_px": 20.0,
                "text": "Test",
                "confidence": 0.95,
                "text_mask": np.zeros((20, 30), dtype=np.uint8),
            }
        ]
        invalid_bytes = b"not an image"
        # Should return original bytes or handle gracefully
        result = erase_text_using_masks(invalid_bytes, boxes, engine="opencv")
        assert isinstance(result, bytes)

    def test_erase_text_multiple_boxes(self, sample_image_bytes):
        """Test text erasing with multiple boxes."""
        boxes = [
            {
                "left_px": 10.0,
                "top_px": 10.0,
                "width_px": 30.0,
                "height_px": 20.0,
                "text": "Hello",
                "confidence": 0.95,
                "text_mask": np.ones((20, 30), dtype=np.uint8) * 100,
            },
            {
                "left_px": 50.0,
                "top_px": 10.0,
                "width_px": 30.0,
                "height_px": 20.0,
                "text": "World",
                "confidence": 0.92,
                "text_mask": np.ones((20, 30), dtype=np.uint8) * 100,
            },
        ]
        result = erase_text_using_masks(sample_image_bytes, boxes, engine="opencv")
        assert isinstance(result, bytes)

    def test_erase_text_box_outside_image(self, sample_image_bytes):
        """Test text erasing when box is outside image bounds."""
        boxes = [
            {
                "left_px": 1000.0,
                "top_px": 1000.0,
                "width_px": 30.0,
                "height_px": 20.0,
                "text": "Outside",
                "confidence": 0.95,
                "text_mask": np.zeros((20, 30), dtype=np.uint8),
            }
        ]
        # Should handle gracefully without crashing
        result = erase_text_using_masks(sample_image_bytes, boxes, engine="opencv")
        assert isinstance(result, bytes)

    def test_erase_text_returns_bytes(self, sample_image_bytes):
        """Test that result is always bytes."""
        boxes = [
            {
                "left_px": 10.0,
                "top_px": 10.0,
                "width_px": 30.0,
                "height_px": 20.0,
                "text": "Test",
                "confidence": 0.95,
                "text_mask": np.zeros((20, 30), dtype=np.uint8),
            }
        ]
        result = erase_text_using_masks(sample_image_bytes, boxes, engine="opencv")
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestInpaintingIntegration:
    """Integration tests for inpainting."""

    def test_inpainting_png_output_format(self, sample_image_bytes):
        """Test that output is PNG format."""
        boxes = []
        result = erase_text_using_masks(sample_image_bytes, boxes, engine="opencv")
        # Should be valid PNG
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_inpainting_preserves_dimensions(self, sample_image_bytes):
        """Test that inpainting preserves image dimensions."""
        boxes = []
        result = erase_text_using_masks(sample_image_bytes, boxes, engine="opencv")

        # Decode result and check dimensions
        with Image.open(io.BytesIO(result)) as img:
            assert img.size == (100, 100)
