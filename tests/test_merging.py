"""Tests for merging.py"""

from appt_ocr.merging import merge_nearby_boxes


def box(left, top, width, height, text, confidence=0.95):
    return {
        "left_px": float(left),
        "top_px": float(top),
        "width_px": float(width),
        "height_px": float(height),
        "text": text,
        "confidence": confidence,
    }


class TestMergeNearbyBoxes:
    def test_merge_empty_list(self):
        assert merge_nearby_boxes([]) == []

    def test_merge_single_box(self, sample_ocr_result):
        result = merge_nearby_boxes([sample_ocr_result])
        assert len(result) == 1
        assert result[0]["text"] == "Hello World"

    def test_input_is_not_modified(self):
        boxes = [box(10, 20, 30, 25, "Hel"), box(42, 20, 30, 25, "lo")]
        merge_nearby_boxes(boxes)
        assert boxes[0]["text"] == "Hel" and boxes[0]["width_px"] == 30.0

    def test_merge_non_adjacent_boxes(self):
        boxes = [box(10, 20, 40, 25, "A"), box(200, 20, 40, 25, "B")]
        assert [b["text"] for b in merge_nearby_boxes(boxes)] == ["A", "B"]

    def test_split_word_is_joined_without_a_space(self):
        # PaddleOCR's kerning split: 2 px apart on a 25 px line.
        boxes = [box(10, 20, 30, 25, "Hel"), box(42, 20, 30, 25, "lo")]
        result = merge_nearby_boxes(boxes, merge_threshold=0.5)
        assert len(result) == 1
        assert result[0]["text"] == "Hello"
        assert result[0]["left_px"] == 10.0
        assert result[0]["width_px"] == 62.0

    def test_two_words_are_joined_with_a_space(self):
        # A word space is 6-9 px on a 25 px line; until 3.1.0 this became "HelloWorld".
        boxes = [box(10, 20, 80, 25, "Hello"), box(100, 20, 80, 25, "World")]
        result = merge_nearby_boxes(boxes, merge_threshold=0.5)
        assert [b["text"] for b in result] == ["Hello World"]

    def test_no_double_space(self):
        boxes = [box(10, 20, 80, 25, "Hello "), box(100, 20, 80, 25, "World")]
        assert merge_nearby_boxes(boxes)[0]["text"] == "Hello World"

    def test_cjk_is_joined_without_a_space(self):
        boxes = [box(10, 20, 50, 25, "你好"), box(68, 20, 50, 25, "世界")]
        assert merge_nearby_boxes(boxes)[0]["text"] == "你好世界"
        mixed = [box(10, 20, 50, 25, "版本"), box(68, 20, 30, 25, "3.1")]
        assert merge_nearby_boxes(mixed)[0]["text"] == "版本3.1"

    def test_merge_different_line_no_merge(self):
        boxes = [box(10, 20, 40, 25, "Line1"), box(15, 60, 40, 25, "Line2")]
        assert len(merge_nearby_boxes(boxes)) == 2

    def test_merge_threshold_coefficient(self):
        boxes = [box(10, 20, 40, 25, "Hel"), box(60, 20, 40, 25, "lo")]  # gap 10
        assert (
            len(merge_nearby_boxes(boxes, merge_threshold=0.3)) == 2
        )  # 10 < 7.5 is False
        assert len(merge_nearby_boxes(boxes, merge_threshold=0.5)) == 1  # 10 < 12.5

    def test_overlapping_boxes_are_not_merged(self):
        boxes = [box(10, 20, 40, 25, "A"), box(30, 20, 40, 25, "B")]  # gap -20
        assert len(merge_nearby_boxes(boxes)) == 2

    def test_merge_multiple_boxes_sequence(self):
        boxes = [
            box(10, 20, 20, 25, "A"),
            box(32, 20, 20, 25, "B"),
            box(54, 20, 20, 25, "C"),
        ]
        result = merge_nearby_boxes(boxes)
        assert len(result) == 1
        assert result[0]["text"] == "ABC"
        assert result[0]["width_px"] == 64.0

    def test_merge_preserves_bounds(self):
        boxes = [box(10, 20, 30, 25, "a"), box(42, 18, 30, 30, "b")]
        result = merge_nearby_boxes(boxes)[0]
        assert result["top_px"] == 18.0
        assert result["height_px"] == 30.0

    def test_merge_confidence_min(self):
        boxes = [box(10, 20, 40, 25, "A", 0.95), box(52, 20, 40, 25, "B", 0.80)]
        assert merge_nearby_boxes(boxes)[0]["confidence"] == 0.80

    def test_merge_sorts_by_position(self):
        boxes = [box(100, 20, 40, 25, "B"), box(10, 20, 40, 25, "A")]
        result = merge_nearby_boxes(boxes)
        assert [b["text"] for b in result] == ["A", "B"]

    def test_lines_come_out_in_reading_order(self):
        boxes = [box(10, 60, 40, 25, "second"), box(10, 20, 40, 25, "first")]
        assert [b["text"] for b in merge_nearby_boxes(boxes)] == ["first", "second"]

    def test_another_column_between_two_halves_does_not_block_the_merge(self):
        # Sorted by (top, left) the other column's box (top 21) fell between the
        # halves (tops 20 and 22), and neighbour-only comparison never joined them.
        boxes = [
            box(10, 20, 30, 25, "Hel"),
            box(42, 22, 30, 25, "lo"),
            box(400, 21, 60, 25, "Other"),
        ]
        assert [b["text"] for b in merge_nearby_boxes(boxes)] == ["Hello", "Other"]
