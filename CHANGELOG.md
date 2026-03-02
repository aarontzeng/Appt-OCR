# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
