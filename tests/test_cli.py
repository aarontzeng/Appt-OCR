"""Tests for cli.py: the parser, file resolution, exit codes."""

import os

import pytest

from appt_ocr import cli
from appt_ocr.cli import build_parser, main, options_from_args, resolve_input_files
from tests.conftest import make_deck, paddle_line, text_image

INCH = 914400


class TestBuildParser:
    def test_parser_requires_input(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args([])

    def test_defaults(self):
        args = build_parser().parse_args(["a.pptx"])
        assert (args.output_dir, args.dpi, args.lang, args.merge_threshold) == (
            "output",
            96,
            "ch",
            0.5,
        )
        assert args.inpaint_engine == "lama" and args.pdf_dpi == 300
        assert args.ignore_re == "" and args.remove_re == ""
        assert not (args.keep_images or args.watermark_only or args.no_s2t)

    def test_multiple_inputs_and_flags(self):
        args = build_parser().parse_args(
            [
                "a.pptx",
                "b.pdf",
                "--output-dir",
                "out",
                "--dpi",
                "150",
                "--keep-images",
                "--merge-threshold",
                "0.7",
                "--inpaint-engine",
                "opencv",
                "--watermark-only",
                "--no-s2t",
            ]
        )
        assert args.input == ["a.pptx", "b.pdf"] and args.output_dir == "out"
        assert args.dpi == 150 and args.merge_threshold == 0.7
        assert args.keep_images and args.watermark_only and args.no_s2t
        assert args.inpaint_engine == "opencv"

    def test_choices_are_enforced(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["a.pptx", "--lang", "fr"])
        with pytest.raises(SystemExit):
            build_parser().parse_args(["a.pptx", "--inpaint-engine", "magic"])

    def test_help_exits_zero(self):
        with pytest.raises(SystemExit) as exc_info:
            build_parser().parse_args(["--help"])
        assert exc_info.value.code == 0


class TestOptionsFromArgs:
    def test_s2t_follows_lang_and_flag(self):
        assert options_from_args(build_parser().parse_args(["a.pptx"])).s2t is True
        assert (
            options_from_args(build_parser().parse_args(["a.pptx", "--lang", "en"])).s2t
            is False
        )
        assert (
            options_from_args(build_parser().parse_args(["a.pptx", "--no-s2t"])).s2t
            is False
        )


class TestResolveInputFiles:
    def test_expands_filters_and_deduplicates(self, temp_dir, capsys):
        for name in ("b.pptx", "a.pdf", "c.txt"):
            open(os.path.join(temp_dir, name), "w").close()
        files = resolve_input_files(
            [os.path.join(temp_dir, "*"), os.path.join(temp_dir, "a.pdf")]
        )
        assert [os.path.basename(f) for f in files] == ["a.pdf", "b.pptx"]
        assert "c.txt" in capsys.readouterr().out

    def test_missing_pattern_warns(self, temp_dir, capsys):
        assert resolve_input_files([os.path.join(temp_dir, "nothing-*.pptx")]) == []
        assert "Could not find files" in capsys.readouterr().out


class TestMain:
    def test_no_input_files_exits_1(self, temp_dir, capsys):
        assert main([os.path.join(temp_dir, "none.pptx")]) == 1
        assert "No valid" in capsys.readouterr().out

    def test_an_invalid_regex_is_a_usage_error_before_any_model_loads(
        self, monkeypatch, temp_dir
    ):
        # Until 3.1.0 the regex was first used inside the per-file loop: the
        # OCR engine had been loaded and the first image OCRed before it failed.
        monkeypatch.setattr(
            cli, "get_ocr_engine", lambda lang: pytest.fail("engine loaded")
        )
        with pytest.raises(SystemExit) as exc_info:
            main([os.path.join(temp_dir, "x.pptx"), "--remove-re", "("])
        assert exc_info.value.code == 2

    def test_a_processed_batch_exits_0_and_a_failure_exits_1(
        self, fake_paddle, no_lama, temp_dir, capsys
    ):
        image, box = text_image("Hello")
        good = os.path.join(temp_dir, "good.pptx")
        make_deck(good, image, width=3 * INCH)
        fake_paddle.returns(paddle_line(box, "Hello"))
        out_dir = os.path.join(temp_dir, "out")

        assert main([good, "--output-dir", out_dir]) == 0
        out = capsys.readouterr().out
        assert os.path.exists(os.path.join(out_dir, "good_ocr.pptx"))
        assert "downgrading to OpenCV" in out and "Success: 1 files" in out

        bad = os.path.join(temp_dir, "bad.pptx")
        with open(bad, "wb") as fh:
            fh.write(b"not a pptx")
        assert (
            main([good, bad, "--output-dir", out_dir, "--inpaint-engine", "opencv"])
            == 1
        )
        out = capsys.readouterr().out
        assert "Failed:  1 files" in out and "Success: 1 files" in out

    def test_a_pdf_is_converted_and_its_temp_file_removed(
        self, fake_paddle, sample_pdf_path, temp_dir, monkeypatch
    ):
        temps = []
        real = cli.convert_pdf_to_pptx

        def recording(path, dpi):
            temps.append(real(path, dpi))
            return temps[-1]

        monkeypatch.setattr(cli, "convert_pdf_to_pptx", recording)
        out_dir = os.path.join(temp_dir, "out")
        assert (
            main(
                [
                    sample_pdf_path,
                    "--output-dir",
                    out_dir,
                    "--inpaint-engine",
                    "opencv",
                    "--pdf-dpi",
                    "72",
                ]
            )
            == 0
        )
        assert os.path.exists(os.path.join(out_dir, "test_ocr.pptx"))
        assert temps and not os.path.exists(temps[0])
