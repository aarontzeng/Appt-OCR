"""Tests for image.py"""

import numpy as np
import pytest
from pptx import Presentation

from appt_ocr.image import (
    analyze_text_features,
    as_array,
    decode_image,
    encode_image,
    extract_image_from_shape,
    visible_region,
)
from tests.conftest import make_deck, picture_shapes, png_bytes, text_image


class TestDecodeEncode:
    def test_round_trip(self, sample_image_bytes):
        arr = decode_image(sample_image_bytes)
        assert arr.shape == (100, 100, 3) and tuple(arr[0, 0]) == (0, 0, 255)  # BGR
        again = decode_image(encode_image(arr))
        assert np.array_equal(arr, again)

    def test_garbage_is_none(self):
        assert decode_image(b"not an image") is None
        assert as_array(b"nope") is None

    def test_as_array_passes_arrays_through(self, sample_image_bytes):
        arr = decode_image(sample_image_bytes)
        assert as_array(arr) is arr

    def test_jpeg(self, sample_image_bytes):
        out = encode_image(decode_image(sample_image_bytes), "JPEG")
        assert out[:3] == b"\xff\xd8\xff"


class TestAnalyzeTextFeatures:
    def test_dark_text_on_white(self):
        image, box = text_image("Hello", fg=(0, 0, 0))
        color, is_bold, mask = analyze_text_features(image, box)
        assert max(color) < 100
        assert isinstance(is_bold, bool)
        assert mask.dtype == np.uint8 and mask.shape == (
            int(box["height_px"]),
            int(box["width_px"]),
        )
        assert (mask == 255).any()

    def test_colored_text_keeps_its_hue(self):
        image, box = text_image("Hello", fg=(200, 30, 30))
        color, _, _ = analyze_text_features(image, box)
        assert color[0] > color[1] + 60 and color[0] > color[2] + 60

    def test_light_text_on_dark(self):
        image, box = text_image("Hello", fg=(255, 255, 255), bg=(10, 10, 10))
        color, _, mask = analyze_text_features(image, box)
        assert min(color) > 150
        assert (mask == 255).any()

    def test_accepts_the_decoded_array(self):
        image, box = text_image("Hello")
        assert (
            analyze_text_features(decode_image(image), box)[0]
            == analyze_text_features(image, box)[0]
        )

    def test_box_outside_the_image_gives_defaults(self, sample_image_bytes):
        color, is_bold, mask = analyze_text_features(
            sample_image_bytes,
            {"left_px": 500.0, "top_px": 500.0, "width_px": 50.0, "height_px": 20.0},
        )
        assert (color, is_bold) == ((0, 0, 0), False)
        assert mask.shape == (20, 50) and not mask.any()

    def test_garbage_image_gives_defaults(self):
        color, is_bold, mask = analyze_text_features(
            b"garbage",
            {"left_px": 0.0, "top_px": 0.0, "width_px": 10.0, "height_px": 5.0},
        )
        assert (color, is_bold, mask.shape) == ((0, 0, 0), False, (5, 10))


class TestExtractImageFromShape:
    def test_returns_blob_and_pixel_size(self, sample_pptx_path):
        (pic,) = picture_shapes(Presentation(sample_pptx_path).slides[0])
        blob, w, h = extract_image_from_shape(pic)
        assert isinstance(blob, bytes) and (w, h) == (200, 150)


class TestVisibleRegion:
    def test_no_crop_is_the_whole_image(self, sample_pptx_path):
        (pic,) = picture_shapes(Presentation(sample_pptx_path).slides[0])
        assert visible_region(pic, 200, 150) == (0, 0, 200, 150)

    @pytest.mark.parametrize(
        "crop, expected",
        [
            ({"crop_left": 0.5}, (100, 0, 200, 150)),
            ({"crop_right": 0.25, "crop_bottom": 0.2}, (0, 0, 150, 120)),
            ({"crop_top": 0.1}, (0, 15, 200, 150)),
            (
                {"crop_left": -0.3},
                (0, 0, 200, 150),
            ),  # space around the image: not a crop
        ],
    )
    def test_crops(self, temp_dir, crop, expected):
        import os

        path = os.path.join(temp_dir, "c.pptx")
        prs = make_deck(path, png_bytes((200, 150)), crop=crop)
        (pic,) = picture_shapes(prs.slides[0])
        assert visible_region(pic, 200, 150) == expected
