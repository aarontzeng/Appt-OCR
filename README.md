# Appt-OCR

**Batch PPTX/PDF → Editable Text Conversion via OCR + AI Inpainting**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/aarontzeng/Appt-OCR/actions/workflows/ci.yml/badge.svg)](https://github.com/aarontzeng/Appt-OCR/actions)
[![codecov](https://codecov.io/gh/aarontzeng/Appt-OCR/branch/main/graph/badge.svg)](https://codecov.io/gh/aarontzeng/Appt-OCR)
[![PyPI](https://img.shields.io/pypi/v/appt-ocr.svg)](https://pypi.org/project/appt-ocr/)
[![PaddleOCR](https://img.shields.io/badge/OCR-PaddleOCR-orange)](https://github.com/PaddlePaddle/PaddleOCR)

Appt-OCR extracts images from PowerPoint (`.pptx`) and PDF presentations, performs high-accuracy OCR using [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), and reconstructs the recognized text as **editable text boxes** — all while optionally erasing the original text from background images using AI-powered inpainting.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **High-Accuracy OCR** | PaddleOCR-powered text detection with Chinese + English bilingual support |
| 🎨 **AI Inpainting** | LaMa deep learning model or OpenCV Navier-Stokes for seamless text erasure |
| 📄 **PDF Support** | Automatic PDF → PPTX conversion via PyMuPDF at configurable DPI |
| 🔤 **Smart Kerning** | Merges fragmented OCR boxes (e.g. "Hel" + "lo" → "Hello") |
| 🎯 **Font Detection** | Extracts text color, estimates font size, detects bold weight from pixels |
| 🈶 **S2T Conversion** | Auto-converts simplified Chinese OCR output to traditional Chinese |
| 🚫 **Regex Filtering** | Ignore math formulas (`--ignore-re`) or erase watermarks (`--remove-re`) |
| 📦 **Batch Processing** | Process multiple files with wildcards in one command |

## 📋 Requirements

- Python **3.9+**
- [PaddlePaddle](https://www.paddlepaddle.org.cn/) ≥ 2.6.0

## 🚀 Installation

### From Source (Recommended)

```bash
git clone https://github.com/aarontzeng/Appt-OCR.git
cd Appt-OCR
pip install -e .
```

> **Note**: On first run with `--inpaint-engine lama` (the default), the LaMa model weights (~174 MB) are downloaded automatically from HuggingFace and cached in `~/.cache/huggingface/`. Subsequent runs load from cache.

## 📖 Quick Start

### Basic Usage

```bash
# Process a PPTX file
appt-ocr presentation.pptx

# Process a PDF file
appt-ocr report.pdf

# Batch process multiple files
appt-ocr *.pptx --output-dir output/
```

### Advanced Examples

```bash
# Use LaMa inpainting for high-quality text erasure
appt-ocr slides.pptx --inpaint-engine lama

# Keep original images (add text boxes on top without erasing)
appt-ocr slides.pptx --keep-images

# English-only OCR
appt-ocr slides.pptx --lang en

# Remove watermarks only (no OCR text boxes)
appt-ocr slides.pptx --watermark-only --remove-re "(?i)notebooklm"

# Remove NotebookLM watermarks AND reconstruct all other text boxes
appt-ocr slides.pptx --remove-re "(?i)notebooklm"

# Ignore math formulas in the background
appt-ocr lecture.pptx --ignore-re "P\\s*=|∑|∫"

# High-resolution PDF rendering
appt-ocr paper.pdf --pdf-dpi 300
```

### As a Python Library

```python
from appt_ocr import process_pptx

stats = process_pptx(
    input_path="input.pptx",
    output_path="output.pptx",
    inpaint_engine="lama",
    lang="ch",
)
print(f"Created {stats['total_textboxes']} text boxes across {stats['total_slides']} slides")
```

## ⚙️ CLI Reference

| Argument | Default | Description |
|---|---|---|
| `input` | *(required)* | Input `.pptx` / `.pdf` files (supports wildcards) |
| `--output-dir` | `output/` | Output directory |
| `--dpi` | `96` | Image DPI for coordinate conversion |
| `--lang` | `ch` | OCR language: `ch` (bilingual) or `en` (English only) |
| `--keep-images` | `False` | Keep original images (don't erase text) |
| `--merge-threshold` | `0.5` | Box merging aggressiveness (higher = more merging) |
| `--inpaint-engine` | `lama` | `lama` (AI, high quality) or `opencv` (lightweight) |
| `--pdf-dpi` | `300` | PDF rendering resolution |
| `--ignore-re` | `""` | Regex: keep matching text in background |
| `--remove-re` | `""` | Regex: silently erase matching text |
| `--watermark-only` | `False` | Only erase watermarks, skip text box creation |
| `--no-s2t` | `False` | Disable Simplified → Traditional Chinese conversion |

## 🏗️ Architecture

```
appt_ocr/
├── __init__.py       # Package metadata & public API
├── cli.py            # CLI argument parsing & entry point
├── coordinates.py    # Pixel ↔ EMU ↔ Point conversions
├── image.py          # Text feature analysis (color, bold, masks)
├── inpainting.py     # OpenCV & LaMa text erasure engines
├── merging.py        # OCR box kerning/merge logic
├── ocr.py            # PaddleOCR wrapper & OpenCC converter
├── pdf.py            # PDF → PPTX preprocessing (PyMuPDF)
└── processing.py     # Slide & PPTX processing orchestration
```

### Processing Pipeline

```
Input (PPTX/PDF)
  │
  ├─ [PDF?] ──→ PyMuPDF render pages → Temp PPTX
  │
  ▼
  For each slide:
    1. Extract image from Picture Shape
    2. PaddleOCR detection → bounding boxes + text
    3. Merge nearby boxes (kerning fix)
    4. Regex filter (ignore / remove / keep)
    5. Analyze text features (color, bold, mask)
    6. Inpaint: erase text from image (LaMa or OpenCV)
    7. Create PPTX TextBox with matching font/color/position
  │
  ▼
Output PPTX (editable text boxes + clean backgrounds)
```

---

## 📚 Documentation

- **[API Reference](docs/API.md)** — Complete API documentation
- **[FAQ](docs/FAQ.md)** — Frequently asked questions
- **[Development Guide](docs/DEVELOPMENT.md)** — Contributing and testing
- **[SUPPORT.md](docs/SUPPORT.md)** — Support and maintenance policy
- **[SECURITY.md](SECURITY.md)** — Security vulnerability reporting
- **[CODE_OF_CONDUCT.md](.github/CODE_OF_CONDUCT.md)** — Community guidelines

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

To get started:

```bash
git clone https://github.com/aarontzeng/Appt-OCR.git
cd Appt-OCR
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

See [Development Guide](docs/DEVELOPMENT.md) for more details.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

### Third-Party Licenses

| Dependency | License | Notes |
|------------|---------|-------|
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) | **AGPL-3.0** | Used for PDF rendering only. PyMuPDF is built on MuPDF which is AGPL-3.0. If you distribute software that includes PDF functionality, be aware of the AGPL terms. |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | Apache-2.0 | |
| [PaddlePaddle](https://github.com/PaddlePaddle/Paddle) | Apache-2.0 | |
| [LaMa](https://github.com/advimman/lama) (via simple-lama-inpainting) | Apache-2.0 | Model weights (~174 MB) are auto-downloaded from HuggingFace on first run |
| [opencv-python-headless](https://github.com/opencv/opencv-python) | Apache-2.0 | |
| [opencc-python-reimplemented](https://github.com/yichen0831/opencc-python) | Apache-2.0 | |
| [python-pptx](https://github.com/scanny/python-pptx) | MIT | |
| [Pillow](https://github.com/python-pillow/Pillow) | HPND | |
| [NumPy](https://numpy.org) | BSD-3-Clause | |

> **Note on PyMuPDF / AGPL-3.0**: This project uses PyMuPDF solely for PDF-to-image conversion. The AGPL-3.0 license of PyMuPDF applies to that component. If you need to avoid AGPL dependencies in your own distribution, you can disable PDF support by not calling the PDF conversion path, or replace PyMuPDF with an MIT/Apache-licensed alternative.

---

## 🙏 Acknowledgments

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — Multilingual OCR engine
- [LaMa](https://github.com/advimman/lama) — Large Mask Inpainting model
- [python-pptx](https://github.com/scanny/python-pptx) — PPTX manipulation library
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — PDF rendering engine
- [OpenCC](https://github.com/BYVoid/OpenCC) — Chinese character conversion
