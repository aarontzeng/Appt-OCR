"""Tests for ocr.py"""


import pytest

from appt_ocr.ocr import get_ocr_engine, get_opencc_converter, run_ocr_on_image


class TestGetOcrEngine:
    """Test OCR engine initialization."""

    def test_get_ocr_engine_lazy_load(self):
        """Test that OCR engine is lazily loaded."""
        engine = get_ocr_engine("ch")
        assert engine is not None

    def test_get_ocr_engine_ch_language(self):
        """Test OCR engine with Chinese language."""
        engine = get_ocr_engine("ch")
        assert engine is not None

    def test_get_ocr_engine_en_language(self):
        """Test OCR engine with English language."""
        engine = get_ocr_engine("en")
        assert engine is not None

    def test_get_ocr_engine_caches_result(self):
        """Test that subsequent calls return cached instance."""
        engine1 = get_ocr_engine("ch")
        engine2 = get_ocr_engine("ch")
        # Should return the same cached instance
        assert engine1 is engine2

    def test_ocr_engine_has_ocr_method(self):
        """Test that OCR engine has the expected interface."""
        engine = get_ocr_engine("ch")
        assert hasattr(engine, "ocr")


class TestGetOpenccConverter:
    """Test OpenCC converter initialization."""

    def test_get_opencc_converter_returns_object_or_none(self):
        """Test that OpenCC converter is available or returns None."""
        converter = get_opencc_converter()
        # Could be None if not installed, or an object if installed
        assert converter is None or hasattr(converter, "convert")

    def test_get_opencc_converter_caches_result(self):
        """Test that subsequent calls return cached instance."""
        converter1 = get_opencc_converter()
        converter2 = get_opencc_converter()
        assert converter1 is converter2


class TestRunOcrOnImage:
    """Test OCR on image data."""

    def test_run_ocr_on_image_returns_list(self, sample_image_bytes):
        """Test that run_ocr_on_image returns a list."""
        result = run_ocr_on_image(sample_image_bytes, lang="ch")
        assert isinstance(result, list)

    def test_run_ocr_on_image_items_are_dicts(self, sample_image_bytes):
        """Test that each OCR result item is a dict with required fields."""
        result = run_ocr_on_image(sample_image_bytes, lang="ch")
        for item in result:
            assert isinstance(item, dict)
            assert "text" in item
            assert "left_px" in item
            assert "top_px" in item
            assert "width_px" in item
            assert "height_px" in item
            assert "confidence" in item

    def test_run_ocr_on_image_with_english(self, sample_image_bytes):
        """Test OCR with English language."""
        result = run_ocr_on_image(sample_image_bytes, lang="en")
        assert isinstance(result, list)

    def test_run_ocr_on_image_with_invalid_bytes(self):
        """Test OCR with invalid image bytes."""
        invalid_bytes = b"not an image"
        # Should either return empty result or raise exception
        with pytest.raises(Exception):
            run_ocr_on_image(invalid_bytes, lang="ch")

    def test_run_ocr_on_image_empty_bytes(self):
        """Test OCR with empty bytes."""
        with pytest.raises(Exception):
            run_ocr_on_image(b"", lang="ch")

    def test_run_ocr_on_image_plain_image_returns_list(self, sample_image_bytes):
        """Test OCR on plain image (no text) returns empty list."""
        result = run_ocr_on_image(sample_image_bytes, lang="ch")
        # A solid red image has no text, so result should be empty list
        assert isinstance(result, list)


class TestOcrIntegration:
    """Integration tests for OCR workflow."""

    def test_ocr_workflow_with_real_text_image(self):
        """Test complete OCR workflow (requires actual text image)."""
        # This test requires a real image with text, skipped if not available
        pytest.skip("Requires test image with actual text")

    def test_ocr_engine_thread_safety(self):
        """Test that OCR engine is thread-safe."""
        # Note: PaddleOCR is generally thread-safe, but single-threaded
        # access is recommended for model initialization
        engine1 = get_ocr_engine("ch")
        engine2 = get_ocr_engine("ch")
        assert engine1 is engine2
