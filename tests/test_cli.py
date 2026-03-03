"""Tests for CLI module."""


import pytest

from appt_ocr.cli import build_parser


class TestBuildParser:
    """Test CLI argument parser."""

    def test_parser_builds_successfully(self):
        """Test that parser can be built."""
        parser = build_parser()
        assert parser is not None

    def test_parser_requires_input(self):
        """Test that parser requires input argument."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_parser_accepts_single_file(self):
        """Test parser with single input file."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx"])
        assert args.input == ["test.pptx"]

    def test_parser_accepts_multiple_files(self):
        """Test parser with multiple input files."""
        parser = build_parser()
        args = parser.parse_args(["test1.pptx", "test2.pptx"])
        assert args.input == ["test1.pptx", "test2.pptx"]

    def test_parser_default_output_dir(self):
        """Test default output directory."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx"])
        assert args.output_dir == "output"

    def test_parser_custom_output_dir(self):
        """Test custom output directory."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx", "--output-dir", "custom/output"])
        assert args.output_dir == "custom/output"

    def test_parser_keep_images_flag(self):
        """Test --keep-images flag."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx", "--keep-images"])
        assert args.keep_images is True

    def test_parser_keep_images_default(self):
        """Test --keep-images default is False."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx"])
        assert args.keep_images is False

    def test_parser_dpi_default(self):
        """Test default DPI."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx"])
        assert args.dpi == 96

    def test_parser_custom_dpi(self):
        """Test custom DPI."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx", "--dpi", "150"])
        assert args.dpi == 150

    def test_parser_dpi_int_conversion(self):
        """Test that DPI is converted to integer."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx", "--dpi", "100"])
        assert isinstance(args.dpi, int)

    def test_parser_lang_default(self):
        """Test default language."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx"])
        assert args.lang == "ch"

    def test_parser_lang_choices(self):
        """Test that lang only accepts valid choices."""
        parser = build_parser()
        args_ch = parser.parse_args(["test.pptx", "--lang", "ch"])
        assert args_ch.lang == "ch"

        args_en = parser.parse_args(["test.pptx", "--lang", "en"])
        assert args_en.lang == "en"

        with pytest.raises(SystemExit):
            parser.parse_args(["test.pptx", "--lang", "invalid"])

    def test_parser_merge_threshold_default(self):
        """Test default merge threshold."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx"])
        assert args.merge_threshold == 0.5

    def test_parser_merge_threshold_custom(self):
        """Test custom merge threshold."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx", "--merge-threshold", "0.7"])
        assert args.merge_threshold == 0.7

    def test_parser_merge_threshold_float_conversion(self):
        """Test that merge threshold is converted to float."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx", "--merge-threshold", "0.5"])
        assert isinstance(args.merge_threshold, float)

    def test_parser_inpaint_engine_default(self):
        """Test default inpaint engine."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx"])
        assert args.inpaint_engine == "lama"

    def test_parser_inpaint_engine_choices(self):
        """Test that inpaint_engine accepts valid choices."""
        parser = build_parser()
        args_lama = parser.parse_args(["test.pptx", "--inpaint-engine", "lama"])
        assert args_lama.inpaint_engine == "lama"

        args_opencv = parser.parse_args(
            ["test.pptx", "--inpaint-engine", "opencv"]
        )
        assert args_opencv.inpaint_engine == "opencv"

    def test_parser_pdf_dpi_default(self):
        """Test default PDF DPI."""
        parser = build_parser()
        args = parser.parse_args(["test.pdf"])
        assert args.pdf_dpi == 300

    def test_parser_pdf_dpi_custom(self):
        """Test custom PDF DPI."""
        parser = build_parser()
        args = parser.parse_args(["test.pdf", "--pdf-dpi", "150"])
        assert args.pdf_dpi == 150

    def test_parser_ignore_re_default(self):
        """Test default ignore regex."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx"])
        assert args.ignore_re == ""

    def test_parser_ignore_re_custom(self):
        """Test custom ignore regex."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx", "--ignore-re", r"P\s*="])
        assert args.ignore_re == r"P\s*="

    def test_parser_remove_re_default(self):
        """Test default remove regex."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx"])
        assert args.remove_re == "(?i)notebooklm"

    def test_parser_watermark_only_flag(self):
        """Test --watermark-only flag."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx", "--watermark-only"])
        assert args.watermark_only is True

    def test_parser_no_s2t_flag(self):
        """Test --no-s2t flag."""
        parser = build_parser()
        args = parser.parse_args(["test.pptx", "--no-s2t"])
        assert args.no_s2t is True

    def test_parser_help_option(self):
        """Test that --help works."""
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
        # --help should exit with code 0
        assert exc_info.value.code == 0

    def test_parser_combined_options(self):
        """Test parser with multiple options."""
        parser = build_parser()
        args = parser.parse_args(
            [
                "test.pptx",
                "--output-dir",
                "results/",
                "--lang",
                "en",
                "--inpaint-engine",
                "opencv",
                "--keep-images",
                "--merge-threshold",
                "0.8",
            ]
        )
        assert args.input == ["test.pptx"]
        assert args.output_dir == "results/"
        assert args.lang == "en"
        assert args.inpaint_engine == "opencv"
        assert args.keep_images is True
        assert args.merge_threshold == 0.8
