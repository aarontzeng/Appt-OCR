"""OCR text box merging (kerning fix).

PaddleOCR sometimes splits a word into several bounding boxes. This module
groups boxes into lines, then joins horizontally adjacent boxes of a line.
"""

from __future__ import annotations

from appt_ocr.boxes import OcrBox

# Two boxes are on one line when their vertical centres differ by less than
# this share of the taller box's height.
SAME_LINE_RATIO = 0.5
# A gap at least this share of the line height is a word space, not a split
# inside a word: "Hel"+"lo" arrive 0-2 px apart on a 25 px line, two words
# 6-9 px apart. Until 3.1.0 both were joined without a space, so "Hello"
# and "World" became "HelloWorld".
WORD_GAP_RATIO = 0.15


def _is_cjk(ch: str) -> bool:
    """Whether a character belongs to a script written without word spaces."""
    if not ch:
        return False
    code = ord(ch)
    return (
        0x3000 <= code <= 0x9FFF  # CJK punctuation, kana, CJK unified
        or 0xF900 <= code <= 0xFAFF  # CJK compatibility
        or 0xFF00 <= code <= 0xFFEF  # full-width forms
    )


def _group_into_lines(boxes: list[OcrBox]) -> list[list[OcrBox]]:
    """Boxes bucketed by line, lines in reading order.

    Comparing only neighbours in one (top, left) sort, as before 3.1.0, let a
    second column's box fall between two halves of a word (tops 20 and 22,
    the other column's 21) and stop them merging. Grouping first means a
    line's boxes are compared with each other whatever else is on the page.
    """
    lines: list[list[OcrBox]] = []
    for box in sorted(boxes, key=lambda r: (r["top_px"], r["left_px"])):
        center = box["top_px"] + box["height_px"] / 2
        for line in lines:
            first = line[0]
            line_center = first["top_px"] + first["height_px"] / 2
            ref = max(first["height_px"], box["height_px"])
            if abs(center - line_center) < ref * SAME_LINE_RATIO:
                line.append(box)
                break
        else:
            lines.append([box])
    return lines


def _absorb(current: OcrBox, nxt: OcrBox, gap: float, ref_height: float) -> None:
    """Grow ``current`` to cover ``nxt`` and append its text."""
    new_right = nxt["left_px"] + nxt["width_px"]
    new_bottom = max(
        current["top_px"] + current["height_px"], nxt["top_px"] + nxt["height_px"]
    )
    new_top = min(current["top_px"], nxt["top_px"])
    current["width_px"] = new_right - current["left_px"]
    current["top_px"] = new_top
    current["height_px"] = new_bottom - new_top
    left_text, right_text = current["text"], nxt["text"]
    word_gap = gap >= ref_height * WORD_GAP_RATIO
    scripted = _is_cjk(left_text[-1:]) or _is_cjk(right_text[:1])
    spaced = left_text.endswith(" ") or right_text.startswith(" ")
    sep = " " if word_gap and not scripted and not spaced else ""
    current["text"] = left_text + sep + right_text
    current["confidence"] = min(current["confidence"], nxt["confidence"])


def merge_nearby_boxes(
    ocr_results: list[OcrBox],
    merge_threshold: float = 0.5,
) -> list[OcrBox]:
    """Merge horizontally adjacent OCR text boxes on the same line.

    Merge criteria:
      1. Same line: vertical centre difference < 50% of the taller height.
      2. Close: horizontal gap >= 0 and < height * merge_threshold.

    A gap of at least 15% of the line height is joined with a space (unless
    either side is CJK); a smaller one is a split inside a word and is joined
    directly.

    Args:
        ocr_results: OCR results (left_px, top_px, width_px, height_px, text,
            confidence). The input dicts are not modified.
        merge_threshold: Merge threshold coefficient (default 0.5).

    Returns:
        Merged boxes in reading order (line by line, left to right).
    """
    if not ocr_results:
        return []

    merged: list[OcrBox] = []
    for line in _group_into_lines(ocr_results):
        line.sort(key=lambda r: r["left_px"])
        current: OcrBox = dict(line[0])  # type: ignore[assignment]
        for nxt in line[1:]:
            ref_height = max(current["height_px"], nxt["height_px"])
            gap = nxt["left_px"] - (current["left_px"] + current["width_px"])
            if 0 <= gap < ref_height * merge_threshold:
                _absorb(current, nxt, gap, ref_height)
            else:
                merged.append(current)
                current = dict(nxt)  # type: ignore[assignment]
        merged.append(current)
    return merged
