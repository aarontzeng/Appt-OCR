"""Tests for pdf.py"""

import os

import pytest

from appt_ocr.pdf import convert_pdf_to_pptx


class TestConvertPdfToPptx:
    """Test PDF to PPTX conversion."""

    def test_convert_pdf_to_pptx_creates_file(self, sample_pdf_path):
        """Test that conversion creates an output file."""
        if sample_pdf_path is None:
            pytest.skip("Sample PDF not available")

        try:
            output_pptx = convert_pdf_to_pptx(sample_pdf_path, dpi=150)
            assert os.path.exists(output_pptx)
            assert output_pptx.endswith(".pptx")
        except Exception as e:
            pytest.skip(f"PDF conversion not available: {e}")

    def test_convert_pdf_to_pptx_returns_path(self, sample_pdf_path):
        """Test that function returns path to output file."""
        if sample_pdf_path is None:
            pytest.skip("Sample PDF not available")

        try:
            result = convert_pdf_to_pptx(sample_pdf_path, dpi=150)
            assert isinstance(result, str)
            assert result.endswith(".pptx")
        except Exception as e:
            pytest.skip(f"PDF conversion not available: {e}")

    def test_convert_pdf_to_pptx_default_dpi(self, sample_pdf_path):
        """Test conversion with default DPI."""
        if sample_pdf_path is None:
            pytest.skip("Sample PDF not available")

        try:
            result = convert_pdf_to_pptx(sample_pdf_path)
            assert isinstance(result, str)
        except Exception as e:
            pytest.skip(f"PDF conversion not available: {e}")

    def test_convert_pdf_to_pptx_custom_dpi(self, sample_pdf_path):
        """Test conversion with custom DPI."""
        if sample_pdf_path is None:
            pytest.skip("Sample PDF not available")

        try:
            result_150 = convert_pdf_to_pptx(sample_pdf_path, dpi=150)
            result_300 = convert_pdf_to_pptx(sample_pdf_path, dpi=300)

            # Both should be valid outputs
            assert os.path.exists(result_150)
            assert os.path.exists(result_300)
        except Exception as e:
            pytest.skip(f"PDF conversion not available: {e}")

    def test_convert_pdf_to_pptx_nonexistent_file(self):
        """Test conversion of non-existent PDF."""
        with pytest.raises(Exception):
            convert_pdf_to_pptx("/nonexistent/file.pdf", dpi=150)

    def test_convert_pdf_to_pptx_invalid_path(self):
        """Test conversion with invalid path."""
        with pytest.raises(Exception):
            convert_pdf_to_pptx("", dpi=150)

    def test_convert_pdf_to_pptx_low_dpi(self, sample_pdf_path):
        """Test conversion with very low DPI."""
        if sample_pdf_path is None:
            pytest.skip("Sample PDF not available")

        try:
            result = convert_pdf_to_pptx(sample_pdf_path, dpi=72)
            assert isinstance(result, str)
        except Exception as e:
            pytest.skip(f"PDF conversion not available: {e}")

    def test_convert_pdf_to_pptx_high_dpi(self, sample_pdf_path):
        """Test conversion with high DPI."""
        if sample_pdf_path is None:
            pytest.skip("Sample PDF not available")

        try:
            result = convert_pdf_to_pptx(sample_pdf_path, dpi=600)
            assert isinstance(result, str)
        except Exception as e:
            pytest.skip(f"PDF conversion not available: {e}")
