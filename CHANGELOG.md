# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] - 2026-09-26

A read of the whole pipeline with every finding reproduced first, then fixed
with a test that fails on the old code.

### Fixed

- **Words were glued together**: two boxes a word space apart on one line
  merged as `"HelloWorld"`. A gap of at least 15% of the line height now
  joins with a space (never for CJK); a smaller gap is still a split inside
  a word. Boxes are grouped into lines before merging, so a second column's
  box can no longer keep two halves of a word apart.
- **Z-order after erasing**: the inpainted picture was appended on top of the
  slide, covering every shape that used to sit above the original. It now
  takes the original's place in the shape tree.
- **Cropped pictures**: OCR ran on the full image while the shape showed a
  crop, so text boxes landed in the wrong place and the crop was lost on
  replacement. OCR now runs on the visible part; the replacement keeps that
  view. Rotated pictures are skipped with a warning instead of getting
  misplaced text boxes.
- **One OCR engine per language**: the first call's `lang` used to win for
  the life of the process, so `process_pptx(lang="en")` after a `"ch"` run
  silently used the Chinese engine.
- **Single glyphs were dropped**: the vertical-text filter (height > 1.5 ×
  width) removed a lone `1`, `I` or `l` taller than 50 px. It now applies to
  two or more characters only.
- **Exit status**: the CLI exits 1 when any file failed (it always exited 0),
  and 2 for an invalid `--ignore-re`/`--remove-re`, reported before any model
  is loaded rather than after the first image was OCRed.
- **Empty PDF**: `ValueError` naming the file instead of an `IndexError`.
- **LaMa unavailable**: the failed load is remembered; it used to be retried,
  with a warning, on every slide.
- **`Pillow>=9.1.0`**: `Image.Resampling` (LaMa's rescale) does not exist in 9.0.

### Changed

- The image is decoded once per picture and handed to OCR, feature analysis
  and inpainting as an array (it was decoded once per text box, and written
  to a temporary PNG for PaddleOCR). A JPEG picture is written back as JPEG.
- `ProcessingOptions` validates the settings once; `process_pptx` and
  `process_slide` accept `options=` beside their keyword arguments, which are
  unchanged. `run_ocr_on_image`, `analyze_text_features` and
  `erase_text_using_masks` accept a decoded array as well as bytes.
- `processing.py` is one function per step; the tuning constants are named.
- The OCR box shape is `appt_ocr.boxes.OcrBox` (a TypedDict; still a dict).
- **The LaMa engine is the `lama` extra** (`pip install "appt-ocr[lama]"`).
  `simple-lama-inpainting` brings PyTorch, torchvision and `opencv-python`
  beside the headless build; a base install is now OpenCV-only and
  `--inpaint-engine lama` falls back with one notice.
- The version is declared once, in `appt_ocr/__init__.py`; `pyproject.toml`
  reads it. `requirements.txt` (a hand-kept mirror) is gone.
- Importing the package no longer sets `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK`;
  it is set when the engine is built.

### Tests

- PaddleOCR and LaMa are stand-ins (`tests/conftest.py`), so the pipeline
  runs end to end on rendered images and every case asserts a result. The
  `try/except Exception: pytest.skip` wrappers, which turned any failure
  into a skip, are gone; the coverage gate is 90% (was 50%).

### Docs

- `docs/API.md` no longer claims a `remove_re` default of `(?i)notebooklm`
  or exceptions the code never raised; the install extras are described the
  same way everywhere; the PyPI badge is removed until the package is
  published.

## [3.0.0] - 2026-03-02

First public open-source release.

### Added

- **Dual inpainting engines**: LaMa deep learning model (high quality) and OpenCV Navier-Stokes (lightweight) for text erasure
- **PDF support**: Automatic PDF → PPTX conversion via PyMuPDF with configurable DPI
- **Regex filtering**: `--ignore-re` to keep text in background (e.g. math formulas), `--remove-re` to silently erase text (e.g. watermarks)
- **Watermark-only mode**: `--watermark-only` flag to skip OCR text box reconstruction
- **Smart box merging**: Fixes PaddleOCR kerning issues where English words get split across multiple boxes
- **Text feature analysis**: Extracts text color, estimates font size, detects bold weight from pixel density analysis
- **Simplified → Traditional Chinese**: Auto-conversion via OpenCC (enabled by default for `--lang ch`)
- **Batch processing**: Process multiple PPTX/PDF files with wildcard support
- **LaMa resolution cap**: Auto-downscale images exceeding 2048px to prevent OOM

### Technical Details

- Package restructured into modular architecture (`appt_ocr/` with 8 sub-modules)
- PaddlePaddle ≥ 3.0.0 compatibility with MKLDNN disabled to prevent CPU crashes
- numpy pinned to < 2.0.0 for ABI compatibility with PaddleOCR
