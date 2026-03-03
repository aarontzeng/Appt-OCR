"""Tests for coordinates.py"""


from appt_ocr.coordinates import compute_scale_factors, estimate_font_size, px_to_emu


class TestPxToEmu:
    """Test pixel to EMU conversion."""

    def test_px_to_emu_basic(self):
        """Test basic conversion: 96 px at 96 DPI = 914400 EMU (1 inch)."""
        result = px_to_emu(96, dpi=96)
        assert result == 914400

    def test_px_to_emu_zero(self):
        """Test conversion with zero pixels."""
        result = px_to_emu(0, dpi=96)
        assert result == 0

    def test_px_to_emu_different_dpi(self):
        """Test conversion with different DPI."""
        # 100 px at 72 DPI
        result = px_to_emu(100, dpi=72)
        expected = int(100 * 914400 / 72)
        assert result == expected

    def test_px_to_emu_returns_int(self):
        """Test that result is always an integer."""
        result = px_to_emu(50.5, dpi=96)
        assert isinstance(result, int)


class TestComputeScaleFactors:
    """Test scale factor computation."""

    def test_compute_scale_factors_identity(self):
        """Test scale factors when image and display sizes match."""
        img_width_px, img_height_px = 100, 100
        # Convert to EMU for 1:1 match
        expected_width_emu = px_to_emu(100, dpi=96)
        expected_height_emu = px_to_emu(100, dpi=96)

        scale_x, scale_y = compute_scale_factors(
            img_width_px,
            img_height_px,
            expected_width_emu,
            expected_height_emu,
            dpi=96,
        )

        assert abs(scale_x - 1.0) < 0.01
        assert abs(scale_y - 1.0) < 0.01

    def test_compute_scale_factors_scaling_up(self):
        """Test scale factors when display size is larger than image."""
        img_width_px, img_height_px = 100, 100
        img_width_emu = px_to_emu(100, dpi=96)
        img_height_emu = px_to_emu(100, dpi=96)

        # Display size is 2x the image size
        scale_x, scale_y = compute_scale_factors(
            img_width_px,
            img_height_px,
            img_width_emu * 2,
            img_height_emu * 2,
            dpi=96,
        )

        assert abs(scale_x - 2.0) < 0.01
        assert abs(scale_y - 2.0) < 0.01

    def test_compute_scale_factors_zero_image_size(self):
        """Test scale factors when image size is zero (edge case)."""
        scale_x, scale_y = compute_scale_factors(0, 0, 1000, 1000, dpi=96)
        assert scale_x == 1.0
        assert scale_y == 1.0

    def test_compute_scale_factors_asymmetric(self):
        """Test scale factors with different X and Y scaling."""
        img_width_px, img_height_px = 200, 100
        shape_width_emu = px_to_emu(200, dpi=96)
        shape_height_emu = px_to_emu(200, dpi=96)  # 2x height

        scale_x, scale_y = compute_scale_factors(
            img_width_px,
            img_height_px,
            shape_width_emu,
            shape_height_emu,
            dpi=96,
        )

        assert abs(scale_x - 1.0) < 0.01
        assert abs(scale_y - 2.0) < 0.01


class TestEstimateFontSize:
    """Test font size estimation."""

    def test_estimate_font_size_basic(self):
        """Test basic font size estimation."""
        # 24 px at 96 DPI with scale_y=1.0 should be ~18pt
        result = estimate_font_size(24, scale_y=1.0, dpi=96)
        assert 10 < result < 25  # Should be in reasonable range

    def test_estimate_font_size_scaled(self):
        """Test font size with scaling factor."""
        # With scale_y=2.0, font size should roughly double
        result_1x = estimate_font_size(24, scale_y=1.0, dpi=96)
        result_2x = estimate_font_size(24, scale_y=2.0, dpi=96)
        assert result_2x > result_1x

    def test_estimate_font_size_constraints(self):
        """Test that font size is constrained between 6 and 72 pt."""
        # Very small box
        result_small = estimate_font_size(1, scale_y=1.0, dpi=96)
        assert result_small >= 6.0

        # Very large box
        result_large = estimate_font_size(1000, scale_y=1.0, dpi=96)
        assert result_large <= 72.0

    def test_estimate_font_size_zero_height(self):
        """Test font size estimation with zero height."""
        result = estimate_font_size(0, scale_y=1.0, dpi=96)
        # Should return minimum (6pt)
        assert result >= 6.0
        assert result <= 72.0

    def test_estimate_font_size_different_dpi(self):
        """Test font size with different DPI."""
        result_96dpi = estimate_font_size(24, scale_y=1.0, dpi=96)
        result_72dpi = estimate_font_size(24, scale_y=1.0, dpi=72)
        # 72 DPI should result in larger font size than 96 DPI for same pixel height
        assert result_72dpi > result_96dpi
