"""Tests for ocr.py, against the stand-in PaddleOCR from conftest."""

import numpy as np

from appt_ocr import ocr
from appt_ocr.image import decode_image
from appt_ocr.ocr import get_ocr_engine, get_opencc_converter, run_ocr_on_image
from tests.conftest import paddle_line


class TestGetOcrEngine:
    def test_one_engine_per_language(self, fake_paddle):
        ch1 = get_ocr_engine("ch")
        en = get_ocr_engine("en")
        ch2 = get_ocr_engine("ch")
        assert ch1 is ch2 and ch1 is not en
        assert en.lang == "en"
        assert fake_paddle.constructed == ["ch", "en"]

    def test_reset_forgets_the_engines(self, fake_paddle):
        first = get_ocr_engine("ch")
        ocr.reset_engines()
        assert get_ocr_engine("ch") is not first

    def test_importing_the_package_sets_no_environment_variable(self, monkeypatch):
        monkeypatch.delenv("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", raising=False)
        import importlib

        importlib.reload(ocr)
        import os

        assert "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK" not in os.environ


class TestGetOpenccConverter:
    def test_returns_converter_or_none_and_caches(self):
        c1 = get_opencc_converter()
        c2 = get_opencc_converter()
        assert c1 is c2
        assert c1 is None or hasattr(c1, "convert")

    def test_a_missing_opencc_is_warned_once(self, monkeypatch, caplog):
        import sys

        monkeypatch.setitem(sys.modules, "opencc", None)
        ocr.reset_engines()
        try:
            assert get_opencc_converter() is None
            assert get_opencc_converter() is None
            assert caplog.text.count("not installed") == 1
        finally:
            ocr.reset_engines()


class TestRunOcrOnImage:
    def test_parses_lines_into_boxes(self, fake_paddle, sample_image_bytes):
        fake_paddle.returns(
            [[[10, 20], [90, 20], [90, 45], [10, 45]], ("Hello", 0.95)],
        )
        (box,) = run_ocr_on_image(sample_image_bytes, "ch")
        assert box == {
            "left_px": 10.0,
            "top_px": 20.0,
            "width_px": 80.0,
            "height_px": 25.0,
            "text": "Hello",
            "confidence": 0.95,
        }

    def test_accepts_a_decoded_array_and_hands_it_over(
        self, fake_paddle, sample_image_bytes
    ):
        arr = decode_image(sample_image_bytes)
        run_ocr_on_image(arr, "en")
        assert fake_paddle.seen == [("en", arr.shape)]

    def test_rotated_lines_are_dropped(self, fake_paddle, sample_image_bytes):
        fake_paddle.returns(
            [[[10, 10], [20, 60], [10, 62], [0, 12]], ("vertical", 0.9)],
            paddle_line(
                {"left_px": 0.0, "top_px": 0.0, "width_px": 50.0, "height_px": 20.0},
                "flat",
            ),
        )
        assert [b["text"] for b in run_ocr_on_image(sample_image_bytes)] == ["flat"]

    def test_no_detections_is_an_empty_list(self, fake_paddle, sample_image_bytes):
        assert run_ocr_on_image(sample_image_bytes) == []

    def test_undecodable_bytes_are_an_empty_list_without_calling_the_engine(
        self, fake_paddle
    ):
        assert run_ocr_on_image(b"not an image") == []
        assert fake_paddle.seen == []

    def test_the_engine_gets_the_array_not_a_file(
        self, fake_paddle, sample_image_bytes, monkeypatch
    ):
        import tempfile

        monkeypatch.setattr(
            tempfile, "NamedTemporaryFile", lambda *a, **k: pytest_fail()
        )
        run_ocr_on_image(sample_image_bytes)
        assert isinstance(fake_paddle.seen[0][1], tuple)


def pytest_fail():
    raise AssertionError("a temp file was written")


def test_numpy_arrays_are_what_the_engine_sees(fake_paddle, sample_image_bytes):
    run_ocr_on_image(sample_image_bytes)
    assert fake_paddle.seen[0][1] == (100, 100, 3)
    assert isinstance(decode_image(sample_image_bytes), np.ndarray)
