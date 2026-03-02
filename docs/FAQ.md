# Frequently Asked Questions (FAQ)

## Installation & Setup

### Q: Why do I get `ModuleNotFoundError: No module named 'paddleocr'`?

**A:** You need to install Appt-OCR properly. Run:

```bash
pip install -e .
# or from PyPI (when published)
pip install appt-ocr
```

If you cloned from GitHub, make sure you're in the project directory.

---

### Q: What Python versions are supported?

**A:** Python **3.9+**. Specifically tested on:
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12

To check your Python version:
```bash
python --version
```

---

### Q: Can I install Appt-OCR on Windows/macOS/Linux?

**A:** Yes! The project is OS-independent. The only platform-specific consideration is:

- **Windows**: Some dependencies (OpenCV) may require Visual C++ build tools
- **macOS**: May require Xcode command-line tools
- **Linux**: Usually works out-of-the-box

---

### Q: What's the difference between installing with `pip install appt-ocr` vs `pip install -e ".[lama]"`?

**A:**

| Method | LaMa Support | Development |
|--------|--------------|-------------|
| `pip install appt-ocr` | ❌ No (falls back to OpenCV) | ❌ No |
| `pip install -e .` | ❌ No | ✅ Yes (editable) |
| `pip install -e ".[lama]"` | ✅ Yes (PyTorch ~174MB) | ✅ Yes |
| `pip install -e ".[dev]"` | ❌ No | ✅ Yes (includes testing tools) |

---

### Q: The LaMa model is huge (~174MB). Do I have to download it?

**A:** Only if you use `--inpaint-engine lama`. If not installed, Appt-OCR automatically falls back to OpenCV (lightweight, built-in).

To skip LaMa entirely:
```bash
appt-ocr input.pptx --inpaint-engine opencv
```

---

## Usage

### Q: How do I process multiple files at once?

**A:** Use wildcards:

```bash
# Process all PPTX files in current directory
appt-ocr *.pptx --output-dir results/

# Process multiple specific files
appt-ocr slide1.pptx slide2.pptx slide3.pdf
```

---

### Q: What's the difference between `--ignore-re` and `--remove-re`?

**A:**

| Flag | Behavior |
|------|----------|
| `--ignore-re` | Matching text stays in the background image (no text box created) |
| `--remove-re` | Matching text is erased from the image (silently, no text box) |

**Example:**

```bash
# Keep math formulas in background (for reference)
appt-ocr presentation.pptx --ignore-re "P\s*=|∑|∫"

# Erase watermarks (silent removal)
appt-ocr presentation.pptx --remove-re "(?i)confidential|draft"
```

---

### Q: How do I keep the original images without text erasure?

**A:** Use `--keep-images`:

```bash
appt-ocr presentation.pptx --keep-images
```

This adds text boxes on top of the original image without erasing the text.

---

### Q: Should I process PPTX or convert PDF to PPTX first?

**A:** Use PPTX directly if possible. However:

- **PDF input**: Automatically converted to temporary PPTX for processing
- **Better precision**: Use `--pdf-dpi 300` or higher for PDFs with small text

```bash
# Good for documents with large text (~100 DPI is often enough)
appt-ocr document.pdf

# Better for technical papers with small text
appt-ocr document.pdf --pdf-dpi 300
```

---

### Q: How do I handle mixed Chinese and English text?

**A:** Use `--lang ch` (default):

```bash
appt-ocr mixed_content.pptx --lang ch
```

This enables bilingual support. For English-only, use `--lang en`.

---

### Q: My OCR accuracy is poor. How can I improve it?

**A:** Try these steps:

1. **Increase image resolution:**
   ```bash
   appt-ocr slides.pptx --dpi 150  # Default 96
   ```

2. **For PDFs, increase rendering DPI:**
   ```bash
   appt-ocr document.pdf --pdf-dpi 300
   ```

3. **Use English-only OCR if applicable:**
   ```bash
   appt-ocr slides.pptx --lang en
   ```

4. **Check if text is actually in the image** (not embedded as text in PPTX)
   - Appt-OCR only processes images, not native PPTX text

---

### Q: How do I disable Simplified → Traditional Chinese conversion?

**A:** Use `--no-s2t`:

```bash
appt-ocr presentation.pptx --no-s2t
```

---

### Q: What happens to font styling (bold, italic)?

**A:**

- **Bold**: Automatically detected from pixel density (may not be 100% accurate)
- **Italic**: Not detected (limitation of pixel analysis)
- **Color**: Extracted from the image
- **Underline**: Lost (existing in original image only)

---

## Troubleshooting

### Q: I get `OutOfMemoryError` when processing large PDFs or images.

**A:** The LaMa model is memory-intensive. Try:

1. **Use OpenCV engine (lightweight):**
   ```bash
   appt-ocr large_file.pdf --inpaint-engine opencv
   ```

2. **Reduce image DPI:**
   ```bash
   appt-ocr large_file.pdf --pdf-dpi 150  # Default 300
   ```

3. **Process on a machine with more RAM** (16GB+ recommended for complex PDFs)

---

### Q: The output PPTX file is corrupted, how do I fix it?

**A:** This is rare. If it happens:

1. **Check the original file** — try a different PPTX/PDF
2. **Use OpenCV engine** instead of LaMa:
   ```bash
   appt-ocr input.pptx --inpaint-engine opencv
   ```
3. **Report the issue** with the original file (if you can share it)

---

### Q: The CLI help is cut off or displays incorrectly.

**A:** Run:

```bash
appt-ocr --help | less  # Use pager
# or
appt-ocr -h | cat
```

---

### Q: How do I use Appt-OCR programmatically in my Python code?

**A:** See [API.md](./API.md) for full documentation. Quick example:

```python
from appt_ocr import process_pptx

stats = process_pptx(
    input_path="input.pptx",
    output_path="output.pptx",
    lang="ch",
    inpaint_engine="lama"
)

print(f"Created {stats['total_textboxes']} text boxes")
```

---

### Q: Does Appt-OCR work with encrypted/password-protected PPTX files?

**A:** No, not currently. You'll need to:

1. Remove the password protection in Microsoft PowerPoint
2. Save it as a regular PPTX
3. Then process with Appt-OCR

---

### Q: Can I process slides selectively (only certain slides)?

**A:** Not directly, but you can:

1. Open the output PPTX in PowerPoint
2. Delete the slides you don't want to keep
3. Or: Create a temporary PPTX with only desired slides, then process it

---

### Q: How long does processing take?

**A:** Depends on:

- **File size**: A 10-slide PPTX typically takes 30-60 seconds
- **Image complexity**: Complex backgrounds take longer with LaMa
- **Engine**: OpenCV is ~10x faster than LaMa
- **Machine specs**: More CPU cores = faster

**Example timings (2-core CPU):**
- OpenCV engine: ~5-10 sec per slide
- LaMa engine: ~30-60 sec per slide

---

## Advanced Questions

### Q: Can I use Appt-OCR with GPU acceleration?

**A:** PaddleOCR and LaMa both support GPU, but Appt-OCR doesn't expose GPU controls directly. To enable GPU:

1. **Install GPU-enabled PaddlePaddle:**
   ```bash
   pip install paddlepaddle-gpu
   ```

2. **For LaMa GPU acceleration**, modify your code:
   ```python
   from simple_lama_inpainting import SimpleLama
   model = SimpleLama(device="cuda")  # Requires PyTorch GPU
   ```

---

### Q: How do I contribute or report bugs?

**A:** See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

---

### Q: Is there a GUI version?

**A:** Not yet. Currently Appt-OCR is CLI + Python library only. If you'd like to contribute a GUI, see [CONTRIBUTING.md](../CONTRIBUTING.md).

---

### Q: How is Appt-OCR different from other OCR tools?

**A:**

| Feature | Appt-OCR | Tesseract | EasyOCR |
|---------|----------|-----------|---------|
| **Bilingual (CH+EN)** | ✅ | ✅ | ✅ |
| **PPTX/PDF input** | ✅ | ❌ | ❌ |
| **Text inpainting** | ✅ | ❌ | ❌ |
| **Editable textbox output** | ✅ | ❌ | ❌ |
| **Easy installation** | ✅ | ⚠️ | ✅ |

---

## Still Have Questions?

- 📖 Check [API.md](./API.md) for detailed API reference
- 🐛 Search [GitHub Issues](https://github.com/aarontzeng/Appt-OCR/issues)
- 💬 Open a [GitHub Discussion](https://github.com/aarontzeng/Appt-OCR/discussions)
- 📧 File a [Bug Report](https://github.com/aarontzeng/Appt-OCR/issues/new?template=bug_report.md)
