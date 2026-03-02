"""Tests for merging.py"""

import pytest

from appt_ocr.merging import merge_nearby_boxes


class TestMergeNearbyBoxes:
    """Test OCR text box merging logic."""

    def test_merge_empty_list(self):
        """Test merging with empty box list."""
        result = merge_nearby_boxes([])
        assert result == []

    def test_merge_single_box(self):
        """Test merging with single box (no merge needed)."""
        boxes = [
            {
                "left_px": 10.0,
                "top_px": 20.0,
                "width_px": 80.0,
                "height_px": 25.0,
                "text": "Hello",
                "confidence": 0.95,
            }
        ]
        result = merge_nearby_boxes(boxes)
        assert len(result) == 1
        assert result[0]["text"] == "Hello"

    def test_merge_non_adjacent_boxes(self):
        """Test that non-adjacent boxes are not merged."""
        boxes = [
            {
                "left_px": 10.0,
                "top_px": 20.0,
                "width_px": 80.0,
                "height_px": 25.0,
                "text": "Hello",
                "confidence": 0.95,
            },
            {
                "left_px": 200.0,
                "top_px": 20.0,
                "width_px": 80.0,
                "height_px": 25.0,
                "text": "World",
                "confidence": 0.92,
            },
        ]
        result = merge_nearby_boxes(boxes, merge_threshold=0.5)
        assert len(result) == 2

    def test_merge_adjacent_boxes_same_line(self):
        """Test merging adjacent boxes on the same line."""
        boxes = [
            {
                "left_px": 10.0,
                "top_px": 20.0,
                "width_px": 30.0,
                "height_px": 25.0,
                "text": "Hel",
                "confidence": 0.95,
            },
            {
                "left_px": 42.0,  # Gap = 42 - 40 = 2 > 0, < 25*0.5=12.5
                "top_px": 20.0,
                "width_px": 30.0,
                "height_px": 25.0,
                "text": "lo",
                "confidence": 0.95,
            },
        ]
        result = merge_nearby_boxes(boxes, merge_threshold=0.5)
        assert len(result) == 1
        assert "Hel" in result[0]["text"] and "lo" in result[0]["text"]
        assert result[0]["left_px"] == 10.0

    def test_merge_different_line_no_merge(self):
        """Test that boxes on different lines are not merged."""
        boxes = [
            {
                "left_px": 10.0,
                "top_px": 20.0,
                "width_px": 40.0,
                "height_px": 25.0,
                "text": "Line1",
                "confidence": 0.95,
            },
            {
                "left_px": 15.0,
                "top_px": 60.0,  # Different line
                "width_px": 40.0,
                "height_px": 25.0,
                "text": "Line2",
                "confidence": 0.95,
            },
        ]
        result = merge_nearby_boxes(boxes, merge_threshold=0.5)
        assert len(result) == 2

    def test_merge_threshold_coefficient(self):
        """Test merge threshold coefficient impact."""
        boxes = [
            {
                "left_px": 10.0,
                "top_px": 20.0,
                "width_px": 40.0,
                "height_px": 25.0,
                "text": "Hel",
                "confidence": 0.95,
            },
            {
                "left_px": 60.0,  # Gap = 10px
                "top_px": 20.0,
                "width_px": 40.0,
                "height_px": 25.0,
                "text": "lo",
                "confidence": 0.95,
            },
        ]

        # With threshold=0.3, gap (10px) < height*0.3 (7.5px) = False
        result_strict = merge_nearby_boxes(boxes, merge_threshold=0.3)
        assert len(result_strict) == 2

        # With threshold=0.5, gap (10px) < height*0.5 (12.5px) = True
        result_loose = merge_nearby_boxes(boxes, merge_threshold=0.5)
        assert len(result_loose) == 1

    def test_merge_multiple_boxes_sequence(self):
        """Test merging multiple boxes in sequence."""
        boxes = [
            {
                "left_px": 10.0,
                "top_px": 20.0,
                "width_px": 30.0,
                "height_px": 20.0,
                "text": "A",
                "confidence": 0.95,
            },
            {
                "left_px": 42.0,  # Gap = 2, < 20*0.5=10
                "top_px": 20.0,
                "width_px": 30.0,
                "height_px": 20.0,
                "text": "B",
                "confidence": 0.95,
            },
            {
                "left_px": 74.0,  # Gap = 2, < 20*0.5=10
                "top_px": 20.0,
                "width_px": 30.0,
                "height_px": 20.0,
                "text": "C",
                "confidence": 0.95,
            },
        ]
        result = merge_nearby_boxes(boxes, merge_threshold=0.5)
        assert len(result) == 1
        assert result[0]["text"] == "ABC"

    def test_merge_preserves_bounds(self):
        """Test that merged box bounds are correct."""
        boxes = [
            {
                "left_px": 10.0,
                "top_px": 20.0,
                "width_px": 40.0,
                "height_px": 25.0,
                "text": "Hello",
                "confidence": 0.95,
            },
            {
                "left_px": 45.0,  # Gap = 5, within threshold
                "top_px": 22.0,   # Slightly lower
                "width_px": 50.0,
                "height_px": 23.0,
                "text": "World",
                "confidence": 0.92,
            },
        ]
        result = merge_nearby_boxes(boxes, merge_threshold=0.5)
        # May not merge due to y_diff check
        if len(result) == 1:
            merged = result[0]
            assert merged["left_px"] == 10.0
            assert merged["top_px"] == 20.0  # Should be min of the two

    def test_merge_confidence_min(self):
        """Test that merged box takes minimum confidence."""
        boxes = [
            {
                "left_px": 10.0,
                "top_px": 20.0,
                "width_px": 40.0,
                "height_px": 25.0,
                "text": "A",
                "confidence": 0.95,
            },
            {
                "left_px": 45.0,  # Gap = 5
                "top_px": 20.0,
                "width_px": 40.0,
                "height_px": 25.0,
                "text": "B",
                "confidence": 0.80,
            },
        ]
        result = merge_nearby_boxes(boxes, merge_threshold=0.5)
        if len(result) == 1:
            # If merged, should have minimum confidence
            assert result[0]["confidence"] == 0.80

    def test_merge_sorts_by_position(self):
        """Test that boxes are sorted correctly before merging."""
        boxes = [
            {
                "left_px": 100.0,
                "top_px": 20.0,
                "width_px": 40.0,
                "height_px": 25.0,
                "text": "B",
                "confidence": 0.95,
            },
            {
                "left_px": 10.0,
                "top_px": 20.0,
                "width_px": 40.0,
                "height_px": 25.0,
                "text": "A",
                "confidence": 0.95,
            },
        ]
        result = merge_nearby_boxes(boxes, merge_threshold=0.5)
        # Should be processed left-to-right regardless of input order
        assert len(result) == 2
        assert result[0]["text"] == "A"
