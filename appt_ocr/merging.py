"""OCR text box merging (kerning fix).

PaddleOCR sometimes splits words into multiple bounding boxes.
This module detects and merges horizontally adjacent boxes on the same line.
"""


def merge_nearby_boxes(
    ocr_results: list[dict],
    merge_threshold: float = 0.5,
) -> list[dict]:
    """Merge horizontally adjacent OCR text boxes.

    PaddleOCR sometimes splits an English word into multiple Bounding Boxes,
    for example, "Hello" might be split into "Hel" + "lo".
    This function detects boxes with a horizontal distance less than the threshold
    and merges them.

    Merge criteria:
      1. Vertical center Y coordinate difference of the two boxes < 50% of the
         box height (same line).
      2. Horizontal distance < Box height × merge_threshold.

    Args:
        ocr_results: List of OCR recognition results, each element containing:
            - left_px, top_px, width_px, height_px: box coordinates
            - text: recognized text
            - confidence: recognition confidence score
        merge_threshold: Merge threshold coefficient (default 0.5).

    Returns:
        List of merged text boxes.
    """
    if not ocr_results:
        return []

    # Sort by top_px (Y coordinate) then by left_px (X coordinate)
    sorted_results = sorted(ocr_results, key=lambda r: (r["top_px"], r["left_px"]))

    merged: list[dict] = []
    current = sorted_results[0].copy()

    for i in range(1, len(sorted_results)):
        next_box = sorted_results[i]

        # Calculate vertical center difference
        current_center_y = current["top_px"] + current["height_px"] / 2
        next_center_y = next_box["top_px"] + next_box["height_px"] / 2
        y_diff = abs(current_center_y - next_center_y)

        # Calculate horizontal distance (next box left - current box right)
        current_right = current["left_px"] + current["width_px"]
        h_gap = next_box["left_px"] - current_right

        # Use the taller box height as the reference
        ref_height = max(current["height_px"], next_box["height_px"])

        # Determine if they are on the same line and close enough
        is_same_line = y_diff < ref_height * 0.5
        is_close = h_gap < ref_height * merge_threshold

        if is_same_line and is_close and h_gap >= 0:
            # Merge: expand box coordinates and concatenate text
            new_right = next_box["left_px"] + next_box["width_px"]
            new_bottom = max(
                current["top_px"] + current["height_px"],
                next_box["top_px"] + next_box["height_px"],
            )
            new_top = min(current["top_px"], next_box["top_px"])

            current["width_px"] = new_right - current["left_px"]
            current["top_px"] = new_top
            current["height_px"] = new_bottom - new_top
            current["text"] += next_box["text"]
            current["confidence"] = min(current["confidence"], next_box["confidence"])
        else:
            merged.append(current)
            current = next_box.copy()

    merged.append(current)
    return merged
