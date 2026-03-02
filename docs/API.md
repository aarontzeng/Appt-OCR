# API Reference

Complete API documentation for using Appt-OCR as a Python library.

## Core Functions

### `process_pptx()`

Process a PPTX file: extract images, run OCR, and reconstruct editable text boxes.

```python
def process_pptx(
    input_path: str,
    output_path: str,
    dpi: int = 96,
    lang: str = "ch",
    keep_images: bool = False,
    merge_threshold: float = 0.5,
    ignore_re: str = "",
    remove_re: str = "(?i)notebooklm",
    inpaint_engine: str = "lama",
    watermark_only: bool = False,
    s2t: bool = True,
) -> dict[str, Any]
```

**Parameters:**

- `input_path` (str): Path to input `.pptx` file
- `output_path` (str): Path to save output `.pptx` file
- `dpi` (int, default=96): Image DPI for coordinate conversion
- `lang` (str, default="ch"): OCR language:
  - `"ch"` - Bilingual (Chinese + English)
  - `"en"` - English only
- `keep_images` (bool, default=False): If `True`, keep original images without erasing text
- `merge_threshold` (float, default=0.5): Text box merging aggressiveness:
  - Lower values (0.1-0.3): Only merge very close boxes
  - Higher values (0.7-0.9): Merge more aggressively
- `ignore_re` (str, default=""): Regex pattern for text to ignore (keep in background, no text box)
  - Example: `r"P\s*=|∑"` to keep math formulas
- `remove_re` (str, default="(?i)notebooklm"): Regex pattern for text to erase silently
  - Example: `r"watermark|logo"` to remove watermarks
- `inpaint_engine` (str, default="lama"): Text erasing engine:
  - `"lama"` - Deep learning model (high quality, requires PyTorch)
  - `"opencv"` - Traditional algorithm (lightweight, fast)
- `watermark_only` (bool, default=False): If `True`, only erase text matching `remove_re`, skip OCR
- `s2t` (bool, default=True): If `True`, convert simplified Chinese to traditional Chinese

**Returns:**

Dictionary with the following keys:

```python
{
    "total_slides": int,        # Total number of slides
    "processed_slides": int,    # Slides containing images
    "total_textboxes": int,     # Total text boxes created
    "input": str,               # Input file path
    "output": str               # Output file path (optional, if provided)
}
```

**Raises:**

- `FileNotFoundError`: If input file doesn't exist
- `ValueError`: If parameters are invalid
- `Exception`: If processing fails (corrupted PPTX, etc.)

**Example:**

```python
from appt_ocr import process_pptx

stats = process_pptx(
    input_path="presentation.pptx",
    output_path="presentation_ocr.pptx",
    lang="ch",
    inpaint_engine="lama"
)

print(f"Processed {stats['processed_slides']} slides")
print(f"Created {stats['total_textboxes']} text boxes")
```

---

### `process_slide()`

Process a single slide: extract images, run OCR, add text boxes.

```python
def process_slide(
    slide,
    dpi: int = 96,
    lang: str = "ch",
    keep_images: bool = False,
    merge_threshold: float = 0.5,
    ignore_re: str = "",
    remove_re: str = "",
    inpaint_engine: str = "lama",
    watermark_only: bool = False,
    s2t: bool = False,
) -> int
```

**Parameters:**

Same as `process_pptx()` for common parameters, plus:

- `slide`: python-pptx Slide object

**Returns:**

Integer: Total number of text boxes created on this slide.

**Example:**

```python
from pptx import Presentation
from appt_ocr import process_slide

prs = Presentation("input.pptx")
for i, slide in enumerate(prs.slides):
    boxes_created = process_slide(
        slide,
        lang="en",
        inpaint_engine="opencv"
    )
    print(f"Slide {i}: {boxes_created} text boxes")
```

---

### `run_ocr_on_image()`

Run OCR on image bytes and return detection results.

```python
def run_ocr_on_image(
    image_bytes: bytes,
    lang: str = "ch",
    s2t: bool = False,
) -> dict[str, Any]
```

**Parameters:**

- `image_bytes` (bytes): Image binary content (PNG, JPEG, etc.)
- `lang` (str, default="ch"): OCR language ("ch" or "en")
- `s2t` (bool, default=False): Convert simplified Chinese to traditional

**Returns:**

Dictionary with OCR results:

```python
{
    "text": str,                    # Recognized text
    "boxes": list[dict],            # Bounding boxes with coordinates
    "confidences": list[float],     # Confidence scores
    # Additional PaddleOCR fields...
}
```

**Example:**

```python
from appt_ocr import run_ocr_on_image

# Read image
with open("slide_image.png", "rb") as f:
    img_bytes = f.read()

result = run_ocr_on_image(img_bytes, lang="ch")
print(f"Recognized: {result['text']}")
print(f"Confidence: {result['confidences']}")
```

---

## Utility Functions

### Coordinate Conversion

```python
from appt_ocr.coordinates import px_to_emu, estimate_font_size

# Convert pixels to EMU (PowerPoint units)
emu_value = px_to_emu(96, dpi=96)  # 1 inch = 914400 EMU

# Estimate font size from bounding box height
font_pt = estimate_font_size(24, scale_y=1.0, dpi=96)  # ~18 pt
```

### Text Feature Analysis

```python
from appt_ocr.image import analyze_text_features

# Analyze text color and boldness
color_rgb, is_bold, text_mask = analyze_text_features(
    image_bytes,
    box={
        "left_px": 10,
        "top_px": 20,
        "width_px": 100,
        "height_px": 30,
    }
)

print(f"Text color (RGB): {color_rgb}")
print(f"Is bold: {is_bold}")
```

### Text Box Merging

```python
from appt_ocr.merging import merge_nearby_boxes

# Merge horizontally adjacent OCR boxes
boxes = [
    {"left_px": 10, "top_px": 20, "width_px": 40, "height_px": 25,
     "text": "Hel", "confidence": 0.95},
    {"left_px": 45, "top_px": 20, "width_px": 40, "height_px": 25,
     "text": "lo", "confidence": 0.95},
]

merged = merge_nearby_boxes(boxes, merge_threshold=0.5)
# Result: Single box with text "Hello"
```

---

## Environment Variables

### `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK`

Set to `"True"` to disable PaddlePaddle connectivity checks (faster startup).

```bash
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
```

---

## Advanced Configuration

### Custom OCR Engine Options

The OCR engine is lazily initialized. To customize:

```python
from appt_ocr.ocr import get_ocr_engine

engine = get_ocr_engine("ch")
# Engine is cached globally for subsequent calls
```

### Inpainting Engines

**OpenCV (Default):**
- Lightweight, CPU-based
- Uses Navier-Stokes inpainting
- Fast but lower quality on complex backgrounds

**LaMa (Higher Quality):**
- Deep learning model (Fast Fourier Convolutions)
- Requires PyTorch (~174 MB download)
- Best results on complex backgrounds

```bash
# Install with LaMa support
pip install -e ".[lama]"

# Use in code
process_pptx("input.pptx", "output.pptx", inpaint_engine="lama")
```

---

## Error Handling

```python
from appt_ocr import process_pptx

try:
    stats = process_pptx("input.pptx", "output.pptx")
except FileNotFoundError:
    print("Input file not found")
except ValueError as e:
    print(f"Invalid parameter: {e}")
except Exception as e:
    print(f"Processing error: {e}")
```

---

## Performance Tips

1. **Use OpenCV engine for speed:**
   ```python
   process_pptx(..., inpaint_engine="opencv")
   ```

2. **Adjust merge threshold based on content:**
   ```python
   # For clean, well-separated text
   process_pptx(..., merge_threshold=0.3)
   
   # For tightly packed text
   process_pptx(..., merge_threshold=0.7)
   ```

3. **Pre-filter with regex for large files:**
   ```python
   # Skip processing of watermarks
   process_pptx(..., remove_re=r"confidential|proprietary")
   ```

4. **Use English-only OCR if Chinese support not needed:**
   ```python
   process_pptx(..., lang="en")
   ```

---

## Thread Safety

The OCR engine is globally cached. While generally thread-safe, it's recommended to:

1. Initialize the engine once in the main thread
2. Use thread pools for processing multiple files
3. Avoid concurrent OCR engine re-initialization

```python
from concurrent.futures import ThreadPoolExecutor
from appt_ocr import process_pptx

# Pre-initialize engine
from appt_ocr.ocr import get_ocr_engine
get_ocr_engine("ch")

# Then use thread pool
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(process_pptx, f"input_{i}.pptx", f"output_{i}.pptx")
        for i in range(4)
    ]
    results = [f.result() for f in futures]
```

---

## Version Info

```python
from appt_ocr import __version__
print(__version__)  # "3.0.0"
```
