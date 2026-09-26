"""Tests for processing.py: the pipeline end to end on a scripted OCR engine."""

import os

import cv2
import pytest
from pptx import Presentation
from pptx.util import Emu

from appt_ocr.processing import ProcessingOptions, process_pptx, process_slide
from tests.conftest import (
    make_deck,
    paddle_line,
    picture_shapes,
    png_bytes,
    text_image,
    text_shapes,
)

INCH = 914400


class TestProcessingOptions:
    def test_defaults(self):
        opts = ProcessingOptions()
        assert opts.inpaint_engine == "lama" and opts.ignore_pattern is None

    def test_invalid_regex_is_a_value_error_at_construction(self):
        with pytest.raises(ValueError, match="remove_re: invalid regular expression"):
            ProcessingOptions(remove_re="(")
        with pytest.raises(ValueError, match="ignore_re"):
            ProcessingOptions(ignore_re="[")

    def test_unknown_engine_is_refused(self):
        with pytest.raises(ValueError, match="inpaint_engine"):
            ProcessingOptions(inpaint_engine="magic")

    def test_non_positive_dpi_is_refused(self):
        with pytest.raises(ValueError, match="dpi"):
            ProcessingOptions(dpi=0)

    def test_with_engine_copies(self):
        opts = ProcessingOptions(remove_re="x")
        other = opts.with_engine("opencv")
        assert other.inpaint_engine == "opencv" and opts.inpaint_engine == "lama"
        assert other.remove_pattern is not None


class TestProcessSlide:
    def test_a_text_line_becomes_a_text_box_where_the_image_had_it(
        self, fake_paddle, temp_dir
    ):
        image, box = text_image("Hello")
        path = os.path.join(temp_dir, "deck.pptx")
        # 300 px wide picture shown 3 inches wide: 100 px per inch
        make_deck(path, image, left=INCH, top=2 * INCH, width=3 * INCH)
        fake_paddle.returns(paddle_line(box, "Hello"))
        prs = Presentation(path)
        slide = prs.slides[0]

        assert process_slide(slide, inpaint_engine="opencv") == 1

        (tb,) = text_shapes(slide)
        assert tb.text_frame.text == "Hello"
        expected_left = INCH + int(box["left_px"] / 100 * INCH)
        assert abs(tb.left - expected_left) <= INCH // 100
        assert abs(tb.top - (2 * INCH + int(box["top_px"] / 100 * INCH))) <= INCH // 100
        assert fake_paddle.seen[0][0] == "ch"

    def test_no_text_means_no_change(self, fake_paddle, temp_dir):
        path = os.path.join(temp_dir, "deck.pptx")
        make_deck(path, png_bytes((200, 150)), width=4 * INCH)
        prs = Presentation(path)
        slide = prs.slides[0]
        before = picture_shapes(slide)[0].image.blob
        assert process_slide(slide, inpaint_engine="opencv") == 0
        assert picture_shapes(slide)[0].image.blob == before
        assert text_shapes(slide) == []

    def test_the_picture_is_replaced_and_erased(self, fake_paddle, temp_dir):
        image, box = text_image("Hello")
        path = os.path.join(temp_dir, "deck.pptx")
        make_deck(path, image, width=3 * INCH)
        fake_paddle.returns(paddle_line(box, "Hello"))
        prs = Presentation(path)
        slide = prs.slides[0]
        process_slide(slide, inpaint_engine="opencv")
        (pic,) = picture_shapes(slide)
        assert pic.image.blob != image
        # the glyph pixels are gone: the box region is (nearly) white now
        import numpy as np

        arr = cv2.imdecode(np.frombuffer(pic.image.blob, np.uint8), cv2.IMREAD_COLOR)
        x, y, w, h = (
            int(box[k]) for k in ("left_px", "top_px", "width_px", "height_px")
        )
        assert arr[y : y + h, x : x + w].mean() > 240

    def test_keep_images_leaves_the_picture_alone(self, fake_paddle, temp_dir):
        image, box = text_image("Hello")
        path = os.path.join(temp_dir, "deck.pptx")
        make_deck(path, image, width=3 * INCH)
        fake_paddle.returns(paddle_line(box, "Hello"))
        prs = Presentation(path)
        slide = prs.slides[0]
        assert process_slide(slide, keep_images=True, inpaint_engine="opencv") == 1
        assert picture_shapes(slide)[0].image.blob == image
        assert len(text_shapes(slide)) == 1

    def test_shapes_above_the_picture_stay_above_it(self, fake_paddle, temp_dir):
        # add_picture appends at the top of the z-order; until 3.1.0 the
        # replacement covered every shape that used to sit on the picture.
        image, box = text_image("Hello")
        path = os.path.join(temp_dir, "deck.pptx")
        prs = make_deck(path, image, width=3 * INCH)
        slide = prs.slides[0]
        logo = slide.shapes.add_textbox(Emu(INCH), Emu(INCH), Emu(INCH), Emu(INCH // 2))
        logo.text_frame.text = "logo"
        fake_paddle.returns(paddle_line(box, "Hello"))

        process_slide(slide, inpaint_engine="opencv")

        names = [s.name for s in slide.shapes]
        (pic,) = picture_shapes(slide)
        assert names.index(pic.name) < names.index(logo.name)
        assert (
            names[-1] != logo.name
        )  # the new text box is on top, the logo is not last

    def test_a_cropped_picture_is_ocred_on_its_visible_part(
        self, fake_paddle, temp_dir
    ):
        # Text in the RIGHT half of a 300 px image; the shape shows only that
        # half (crop_left = 0.5), 3 inches wide -> 200 px per inch.
        image, box = text_image("Hello", at=(180, 30))
        path = os.path.join(temp_dir, "deck.pptx")
        make_deck(
            path, image, left=INCH, top=INCH, width=3 * INCH, crop={"crop_left": 0.5}
        )
        prs = Presentation(path)
        slide = prs.slides[0]
        visible_box = dict(box, left_px=box["left_px"] - 150)
        fake_paddle.returns(paddle_line(visible_box, "Hello"))

        assert process_slide(slide, inpaint_engine="opencv") == 1

        assert fake_paddle.seen[0][1][1] == 150  # the engine saw the visible width
        (tb,) = text_shapes(slide)
        expected_left = INCH + int(visible_box["left_px"] / 50 * INCH)
        assert abs(tb.left - expected_left) <= INCH // 50
        (pic,) = picture_shapes(slide)
        assert pic.crop_left == 0  # the crop is baked into the replacement
        assert pic.width == 3 * INCH

    def test_a_rotated_picture_is_skipped(self, fake_paddle, temp_dir, caplog):
        image, box = text_image("Hello")
        path = os.path.join(temp_dir, "deck.pptx")
        prs = make_deck(path, image, width=3 * INCH)
        slide = prs.slides[0]
        picture_shapes(slide)[0].rotation = 90.0
        fake_paddle.returns(paddle_line(box, "Hello"))
        assert process_slide(slide, inpaint_engine="opencv") == 0
        assert "rotated" in caplog.text
        assert fake_paddle.seen == []

    def test_a_single_glyph_is_kept(self, fake_paddle, temp_dir):
        # "1" is narrower than 1/1.5 of its height; the vertical-text filter
        # dropped it until 3.1.0. Two such glyphs stacked are still vertical.
        image, _ = text_image("1")
        path = os.path.join(temp_dir, "deck.pptx")
        make_deck(path, image, width=3 * INCH)
        tall = {"left_px": 20.0, "top_px": 10.0, "width_px": 24.0, "height_px": 60.0}
        fake_paddle.returns(
            paddle_line(tall, "1"), paddle_line(dict(tall, left_px=120.0), "ab")
        )
        prs = Presentation(path)
        slide = prs.slides[0]
        assert process_slide(slide, inpaint_engine="opencv") == 1
        assert text_shapes(slide)[0].text_frame.text == "1"

    def test_remove_re_erases_without_a_text_box(self, fake_paddle, temp_dir):
        image, box = text_image("NotebookLM")
        path = os.path.join(temp_dir, "deck.pptx")
        make_deck(path, image, width=3 * INCH)
        fake_paddle.returns(paddle_line(box, "NotebookLM"))
        prs = Presentation(path)
        slide = prs.slides[0]
        assert (
            process_slide(slide, remove_re="(?i)notebooklm", inpaint_engine="opencv")
            == 0
        )
        assert text_shapes(slide) == []
        assert picture_shapes(slide)[0].image.blob != image  # erased

    def test_ignore_re_leaves_the_text_in_the_image(self, fake_paddle, temp_dir):
        image, box = text_image("P = 3")
        path = os.path.join(temp_dir, "deck.pptx")
        make_deck(path, image, width=3 * INCH)
        fake_paddle.returns(paddle_line(box, "P = 3"))
        prs = Presentation(path)
        slide = prs.slides[0]
        assert process_slide(slide, ignore_re=r"P\s*=", inpaint_engine="opencv") == 0
        assert text_shapes(slide) == []
        assert picture_shapes(slide)[0].image.blob == image  # untouched

    def test_watermark_only_touches_only_the_watermark(self, fake_paddle, temp_dir):
        image, box = text_image("Hello")
        path = os.path.join(temp_dir, "deck.pptx")
        make_deck(path, image, width=3 * INCH)
        fake_paddle.returns(paddle_line(box, "Hello"))
        prs = Presentation(path)
        slide = prs.slides[0]
        n = process_slide(
            slide, remove_re="draft", watermark_only=True, inpaint_engine="opencv"
        )
        assert n == 0 and text_shapes(slide) == []
        assert picture_shapes(slide)[0].image.blob == image

    def test_s2t_converts_the_text_box(self, fake_paddle, temp_dir):
        pytest.importorskip("opencc")
        image, box = text_image("Hello")
        path = os.path.join(temp_dir, "deck.pptx")
        make_deck(path, image, width=3 * INCH)
        fake_paddle.returns(paddle_line(box, "简体"))
        prs = Presentation(path)
        slide = prs.slides[0]
        process_slide(slide, s2t=True, inpaint_engine="opencv")
        assert text_shapes(slide)[0].text_frame.text == "簡體"

    def test_the_image_is_decoded_once_per_slide(
        self, fake_paddle, temp_dir, monkeypatch
    ):
        image, box = text_image("Hello World and more")
        path = os.path.join(temp_dir, "deck.pptx")
        make_deck(path, image, width=3 * INCH)
        lines = [
            paddle_line(
                dict(box, left_px=box["left_px"] + 40 * i, width_px=30.0), f"w{i}"
            )
            for i in range(6)
        ]
        fake_paddle.returns(*lines)
        calls = []
        real = cv2.imdecode
        monkeypatch.setattr(
            cv2, "imdecode", lambda *a, **k: (calls.append(1), real(*a, **k))[1]
        )
        prs = Presentation(path)
        process_slide(prs.slides[0], inpaint_engine="opencv")
        assert len(calls) == 1

    def test_a_jpeg_picture_stays_jpeg(self, fake_paddle, temp_dir):
        import io

        from PIL import Image

        image, box = text_image("Hello")
        jpeg = io.BytesIO()
        Image.open(io.BytesIO(image)).save(jpeg, format="JPEG", quality=95)
        path = os.path.join(temp_dir, "deck.pptx")
        make_deck(path, jpeg.getvalue(), width=3 * INCH)
        fake_paddle.returns(paddle_line(box, "Hello"))
        prs = Presentation(path)
        slide = prs.slides[0]
        process_slide(slide, inpaint_engine="opencv")
        assert picture_shapes(slide)[0].image.ext in ("jpg", "jpeg")

    def test_options_object_wins_over_keywords(self, fake_paddle, temp_dir):
        image, box = text_image("Hello")
        path = os.path.join(temp_dir, "deck.pptx")
        make_deck(path, image, width=3 * INCH)
        fake_paddle.returns(paddle_line(box, "Hello"))
        prs = Presentation(path)
        opts = ProcessingOptions(inpaint_engine="opencv", lang="en")
        process_slide(prs.slides[0], lang="ch", options=opts)
        assert fake_paddle.constructed == ["en"]


class TestProcessPptx:
    def test_creates_output_and_reports_stats(self, fake_paddle, temp_dir):
        image, box = text_image("Hello")
        path = os.path.join(temp_dir, "in.pptx")
        make_deck(path, image, width=3 * INCH)
        fake_paddle.returns(paddle_line(box, "Hello"))
        out = os.path.join(temp_dir, "nested", "out.pptx")

        stats = process_pptx(path, out, inpaint_engine="opencv")

        assert os.path.exists(out)
        assert stats == {
            "input": path,
            "output": out,
            "total_slides": 1,
            "processed_slides": 1,
            "total_textboxes": 1,
        }
        assert text_shapes(Presentation(out).slides[0])[0].text_frame.text == "Hello"

    def test_slides_without_text_are_not_counted_as_processed(
        self, fake_paddle, sample_pptx_path, temp_dir
    ):
        out = os.path.join(temp_dir, "out.pptx")
        stats = process_pptx(sample_pptx_path, out, inpaint_engine="opencv")
        assert stats["processed_slides"] == 0 and stats["total_textboxes"] == 0

    def test_nonexistent_input_raises(self, fake_paddle, temp_dir):
        from pptx.exc import PackageNotFoundError

        with pytest.raises(PackageNotFoundError):
            process_pptx("/nonexistent/file.pptx", os.path.join(temp_dir, "o.pptx"))

    def test_invalid_regex_is_refused_before_the_file_is_opened(
        self, fake_paddle, temp_dir
    ):
        with pytest.raises(ValueError, match="invalid regular expression"):
            process_pptx(
                "/nonexistent/file.pptx",
                os.path.join(temp_dir, "o.pptx"),
                remove_re="(",
            )

    def test_the_engine_follows_lang_across_calls(
        self, fake_paddle, sample_pptx_path, temp_dir
    ):
        # One cached engine, as before 3.1.0, made the second call run "ch".
        fake_paddle.returns(
            paddle_line(
                {"left_px": 1.0, "top_px": 1.0, "width_px": 50.0, "height_px": 20.0},
                "x",
            )
        )
        out = os.path.join(temp_dir, "out.pptx")
        process_pptx(sample_pptx_path, out, lang="ch", inpaint_engine="opencv")
        process_pptx(sample_pptx_path, out, lang="en", inpaint_engine="opencv")
        assert fake_paddle.constructed == ["ch", "en"]
        assert [lang for lang, _ in fake_paddle.seen] == ["ch", "en"]
