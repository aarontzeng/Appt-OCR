# Copilot Instructions for Appt-OCR

## Quick Commands

### Build & Install
```bash
# Install in development mode (includes type checking, linting, testing)
pip install -e ".[dev,lama]"

# Install without LaMa (lighter alternative)
pip install -e ".[dev]"
```

### Testing
```bash
# Run full test suite with coverage
pytest

# Run a single test file
pytest tests/test_ocr.py -v

# Run specific test function
pytest tests/test_ocr.py::test_function_name -v

# Run with verbose output
pytest -vv

# Run tests matching a pattern
pytest -k "merge" -v
```

### Code Quality
```bash
# Lint the codebase (ruff)
ruff check appt_ocr/

# Auto-fix linting issues
ruff check --fix appt_ocr/

# Type check
pyright appt_ocr/

# Security scan
bandit -ll -r appt_ocr/

# Pre-commit hooks (if you've run `pre-commit install`)
pre-commit run --all-files
```

### Local Testing
```bash
# Test the CLI directly
python -m appt_ocr.cli --help

# Process a file manually
python -m appt_ocr.cli test.pptx --output-dir output/
```

## Architecture Overview

**Purpose:** Batch PPTX/PDF → editable text conversion. Extracts images, performs OCR via PaddleOCR, reconstructs text as editable boxes, optionally erases detected text using AI inpainting.

### Core Data Flow
```
Input File → PDF Preprocessing (if PDF) → Per-slide Processing → Output PPTX

For Each Slide:
1. Image Extraction (from picture shape)
2. PaddleOCR Detection (bounding boxes + recognized text)
3. Box Merging (fix fragmented characters via kerning threshold)
4. Regex Filtering (ignore math, remove watermarks)
5. Text Feature Analysis (color, font weight, mask generation)
6. Inpainting (LaMa or OpenCV to erase detected text from image)
7. TextBox Creation (PPTX object with matched font/color/position)
```

### Module Responsibility Map
| Module | Role |
|--------|------|
| `cli.py` | Argument parsing, CLI entry point (`appt-ocr` command) |
| `processing.py` | Orchestrates slide/PPTX processing, coordinates all steps |
| `ocr.py` | PaddleOCR wrapper, OpenCC Chinese S→T conversion |
| `image.py` | Text feature extraction: color analysis, bold detection, mask generation |
| `inpainting.py` | LaMa and OpenCV inpainting engines (text erasure) |
| `merging.py` | Kerning logic: merges fragmented OCR boxes based on threshold |
| `coordinates.py` | Unit conversion: pixels ↔ EMU (English Metric Units) ↔ Points |
| `pdf.py` | PDF → PPTX conversion via PyMuPDF |
| `__init__.py` | Public API exports (`process_pptx`, `process_slide`, `run_ocr_on_image`) |

### Key Design Patterns
- **Public API in `__init__.py`** — Users import from `appt_ocr`, not submodules
- **Type Hints Required** — All function signatures must include full type annotations (enforced by pyright)
- **Google-style Docstrings** — Standard format for all public functions
- **PEP 8 + Ruff Config** — Line length 88, select rules: E, F, W, I, UP, B (ignore E501)

## Important Implementation Details

### OCR Box Merging
The `merging.py` module has a `merge_threshold` parameter (default 0.5). This controls aggressiveness of combining nearby detected boxes:
- Boxes within `merge_threshold * box_height` pixels are merged
- Useful for fixing fragmented character detection (e.g., "Hel" + "lo" → "Hello")
- Regex filtering (`--ignore-re`, `--remove-re`) happens **after** merging

### Inpainting Engines
- **LaMa** (default): High quality, requires PyTorch (~174 MB model), optional dependency
- **OpenCV**: Lightweight fallback (Navier-Stokes), always available
- Graceful fallback if LaMa unavailable

### Chinese Text Processing
- PaddleOCR can output Simplified Chinese
- OpenCC converter auto-detects and converts to Traditional if needed
- `--no-s2t` flag disables conversion
- Language option: `--lang ch` (bilingual, default) or `--lang en` (English only)

### PDF Handling
- Converted to PPTX via PyMuPDF at configurable `--pdf-dpi` (default 300)
- Temporary PPTX created, then processed like normal PPTX
- Cleanup handled automatically

### Type Checking (PEP 561)
- `appt_ocr/py.typed` marker file signals to type checkers that the package is typed
- `pyproject.toml` includes `py.typed` in package data
- Run `pyright appt_ocr/` locally before committing

## Testing Conventions

- Tests live in `tests/` (enforced by pytest config)
- Use pytest with coverage: `pytest --cov=appt_ocr`
- Coverage report includes branch coverage
- Mark flaky or slow tests with `@pytest.mark.` decorators
- Test files named `test_*.py`

## Commits & Releases

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Version follows [Semantic Versioning](https://semver.org/)
- Version declared in `pyproject.toml` → `__init__.py` reads it
- Release automation: Push version tag matching `v*.*.*` → GitHub Actions publishes to PyPI (OIDC Trusted Publishing)

## Pre-commit Hooks

If you have `.pre-commit-config.yaml` installed locally:
```bash
pre-commit install  # One-time setup
# Runs automatically on `git commit`
# Or manually: pre-commit run --all-files
```

Hooks check: ruff (lint/format), trailing whitespace, merge conflict markers.

## CI/CD Pipeline

**On every push/PR:**
1. **Lint** — `ruff check appt_ocr/` (must pass)
2. **Type Check** — `pyright appt_ocr/` (basic mode, py39 target)
3. **Security** — `bandit -ll -r appt_ocr/` (medium severity and above)
4. **Tests** — `pytest` with coverage reports to Codecov
5. **Imports** — isort check (in CI workflow)

All jobs cache pip dependencies for speed.

## Dependency Notes

### Core Dependencies
- `paddleocr`, `paddlepaddle` — OCR engine
- `python-pptx` — PPTX manipulation
- `PyMuPDF` — PDF rendering
- `opencv-python-headless` — Image processing (no GUI)
- `Pillow` — Image format support
- `numpy<2.0.0` — Constraint due to paddle compatibility
- `opencc-python-reimplemented` — Chinese character conversion

### Optional: LaMa Inpainting
- `simple-lama-inpainting` — High-quality text erasure (optional install)
- Enable: `pip install -e ".[lama]"`

### Development Dependencies
- `ruff` — Linting/formatting
- `pytest`, `pytest-cov` — Testing
- `pyright` — Type checking
- `bandit` — Security scanning

## Future Considerations

- No Makefile needed (pure Python + modern tooling)
- Type checking baseline is "basic" mode (not "strict") — consider upgrading if expanding type coverage
- LaMa model downloads on first run (~174 MB) — mentioned in docs for user awareness

## MCP Server Configuration

To enhance Copilot's capabilities for this project, you can configure MCP servers using the `/mcp` command in the Copilot CLI.

### Recommended Configuration
For this OCR/image processing project, consider enabling:

**GitHub MCP Server** (already built-in, provides filesystem and Git access):
- Filesystem context for understanding module relationships
- Git history exploration to see how OCR/inpainting logic evolved
- Branch and commit analysis

**To enable in your session:**
```bash
copilot
/mcp  # Manage MCP server configuration
```

Then explore:
- `repo:// filesystem` context for code navigation
- Git logs to understand changes to `ocr.py`, `inpainting.py`, `merging.py` modules
- Commit history to see dependency version changes

---

**For detailed API documentation, see:** [docs/API.md](../../docs/API.md)  
**For development guide, see:** [docs/DEVELOPMENT.md](../../docs/DEVELOPMENT.md)  
**For contribution guidelines, see:** [CONTRIBUTING.md](../../CONTRIBUTING.md)
