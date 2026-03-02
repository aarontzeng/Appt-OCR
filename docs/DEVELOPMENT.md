# Development Guide

This guide helps you set up a development environment and contribute to Appt-OCR.

## Prerequisites

- Python 3.9 or later
- Git
- pip and venv (included with Python 3.9+)

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/aarontzeng/Appt-OCR.git
cd Appt-OCR
```

### 2. Create a Virtual Environment

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install in Development Mode

Install the package with all development dependencies:

```bash
pip install -e ".[dev,lama]"
```

This installs:
- Core dependencies (paddleocr, opencv, python-pptx, etc.)
- Development tools (pytest, ruff, pyright, bandit)
- Optional LaMa model support

### 4. Verify Installation

```bash
# Check imports
python -c "from appt_ocr import process_pptx; print('✅ Imports OK')"

# Run CLI help
appt-ocr --help

# Run tests
pytest tests/ -v
```

---

## Development Workflow

### File Structure

```
appt_ocr/
├── __init__.py           # Package exports
├── cli.py                # CLI argument parsing & entry point
├── coordinates.py        # Pixel ↔ EMU coordinate conversions
├── image.py              # Text feature analysis & extraction
├── inpainting.py         # LaMa & OpenCV text erasure engines
├── merging.py            # OCR box merging (kerning fix)
├── ocr.py                # PaddleOCR & OpenCC wrapper
├── pdf.py                # PDF → PPTX conversion
└── processing.py         # Main processing pipeline

tests/
├── conftest.py           # pytest fixtures
├── test_cli.py           # CLI tests
├── test_coordinates.py   # Coordinate conversion tests
├── test_image.py         # Image processing tests
├── test_inpainting.py    # Inpainting tests
├── test_merging.py       # Box merging tests
├── test_ocr.py           # OCR tests
├── test_pdf.py           # PDF conversion tests
└── test_processing.py    # Processing pipeline tests

docs/
├── API.md                # API reference
├── FAQ.md                # Frequently asked questions
└── DEVELOPMENT.md        # This file
```

### Code Style

All code must follow these standards:

#### 1. **PEP 8 Style Guidelines**

```bash
# Check for style violations
ruff check appt_ocr/

# Auto-fix issues
ruff check --fix appt_ocr/
```

#### 2. **Type Hints**

All function signatures must include type hints:

```python
# ✅ Good
def process_image(
    image_bytes: bytes,
    dpi: int = 96,
    lang: str = "ch",
) -> dict[str, Any]:
    """Process image and return OCR results."""
    pass

# ❌ Bad (missing type hints)
def process_image(image_bytes, dpi=96, lang="ch"):
    pass
```

#### 3. **Docstrings**

Use [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings):

```python
def merge_nearby_boxes(
    ocr_results: list[dict],
    merge_threshold: float = 0.5,
) -> list[dict]:
    """Merge horizontally adjacent OCR text boxes.

    PaddleOCR sometimes splits words across multiple boxes.
    This function detects and merges nearby boxes.

    Args:
        ocr_results: List of OCR detection results.
        merge_threshold: Merge threshold coefficient (0.0-1.0).

    Returns:
        List of merged text boxes.

    Raises:
        ValueError: If merge_threshold is invalid.
    """
```

#### 4. **Imports**

Keep imports organized and sorted:

```python
# Standard library
import os
import tempfile
from pathlib import Path

# Third-party
import cv2
import numpy as np
from PIL import Image

# Local
from appt_ocr.coordinates import px_to_emu
from appt_ocr.image import extract_image_from_shape
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_cli.py -v

# Run specific test
pytest tests/test_cli.py::TestBuildParser::test_parser_requires_input -v

# Run with coverage
pytest tests/ --cov=appt_ocr --cov-report=html

# Run with output to file
pytest tests/ -v > test_results.txt
```

### Writing Tests

Add tests in `tests/test_*.py` files. Use pytest fixtures from `conftest.py`:

```python
def test_process_pptx_basic(sample_pptx_path, temp_dir):
    """Test basic PPTX processing."""
    import os
    from appt_ocr import process_pptx

    output_path = os.path.join(temp_dir, "output.pptx")
    result = process_pptx(sample_pptx_path, output_path)

    assert isinstance(result, dict)
    assert os.path.exists(output_path)
```

### Test Coverage

Target coverage should be **≥ 70%**:

```bash
# Generate coverage report
pytest tests/ --cov=appt_ocr --cov-report=term-missing

# View HTML report
pytest tests/ --cov=appt_ocr --cov-report=html
open htmlcov/index.html
```

---

## Quality Checks

### 1. Linting

```bash
# Check for style issues
ruff check appt_ocr/

# Auto-fix common issues
ruff check --fix appt_ocr/
```

### 2. Type Checking

```bash
# Run pyright
pyright appt_ocr/

# Check specific file
pyright appt_ocr/ocr.py
```

### 3. Security Scanning

```bash
# Scan for security issues
bandit -r appt_ocr/ -f txt
```

### 4. Pre-commit Check

Run all checks before committing:

```bash
# Lint
ruff check --fix appt_ocr/

# Type check
pyright appt_ocr/

# Security scan
bandit -r appt_ocr/ -ll

# Tests
pytest tests/ -v --tb=short
```

---

## Making Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix-name
```

### 2. Make Your Changes

- Modify relevant `.py` files
- Add/update docstrings
- Ensure type hints are present
- Write or update tests

### 3. Run Quality Checks

```bash
# Auto-fix style
ruff check --fix appt_ocr/

# Run tests
pytest tests/ -v

# Type check
pyright appt_ocr/

# Security scan
bandit -r appt_ocr/ -ll
```

### 4. Commit with Conventional Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git commit -m "feat: add support for DOCX input"
git commit -m "fix: prevent crash on empty slides"
git commit -m "docs: update API reference"
git commit -m "test: add OCR engine tests"
git commit -m "refactor: simplify coordinate conversion"
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation updates
- `test` - Tests
- `refactor` - Code refactoring (no functional change)
- `perf` - Performance improvements
- `chore` - Dependencies, CI configuration, etc.

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a PR on GitHub with a clear description.

---

## Debugging

### Using pdb Debugger

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or (Python 3.7+)
breakpoint()
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### Verbose Test Output

```bash
pytest tests/test_ocr.py -vv -s

# -vv : Very verbose
# -s  : Show print statements
```

---

## Building and Distribution

### Local Build

```bash
pip install build
python -m build
```

This creates wheels in `dist/`.

### Testing PyPI Upload (testpypi)

```bash
pip install twine

# Build
python -m build

# Upload to test PyPI
twine upload -r testpypi dist/*

# Install from test PyPI
pip install -i https://test.pypi.org/simple/ appt-ocr
```

### Production PyPI Upload

```bash
# Only for maintainers
twine upload dist/*
```

---

## Documentation

### Updating Docs

Documentation files are in `docs/`:
- `API.md` - API reference (auto-generated content)
- `FAQ.md` - Frequently asked questions
- `DEVELOPMENT.md` - This file

Update them when:
- Adding new public functions
- Changing function signatures
- Fixing documentation bugs

### Generating API Docs (Future)

Currently, API docs are manually maintained. In the future, consider:
- Using `sphinx` for auto-generated docs
- Publishing on ReadTheDocs
- Auto-generating from docstrings

---

## Release Process (Maintainers)

### 1. Update Version

Edit `pyproject.toml`:
```toml
version = "3.1.0"  # Bump version
```

### 2. Update CHANGELOG.md

```markdown
## [3.1.0] - 2026-03-10

### Added
- New feature X

### Fixed
- Bug fix Y

### Changed
- Breaking change Z
```

### 3. Commit and Tag

```bash
git commit -am "chore: release v3.1.0"
git tag v3.1.0
git push origin main --tags
```

### 4. Build and Upload

```bash
python -m build
twine upload dist/*
```

---

## Getting Help

- 📖 Read [API.md](./API.md) for API details
- 🐛 Check [existing issues](https://github.com/aarontzeng/Appt-OCR/issues)
- 💬 Join [GitHub Discussions](https://github.com/aarontzeng/Appt-OCR/discussions)
- 📧 Email the maintainers

---

## Code Review Guidelines

When reviewing PRs, check:

- [ ] Code follows PEP 8 (`ruff check` passes)
- [ ] Type hints present on all functions
- [ ] Docstrings written (Google style)
- [ ] Tests added for new functionality
- [ ] No breaking changes (or documented)
- [ ] CHANGELOG updated
- [ ] Commit messages follow Conventional Commits
- [ ] No security issues (`bandit` passes)

---

## Tips & Tricks

### Quick Test During Development

```bash
# Test single module quickly
python -m pytest tests/test_cli.py -xvs

# -x  : Stop on first failure
# -v  : Verbose
# -s  : Show print output
```

### Building Wheel for Distribution

```bash
python -m build --wheel
ls dist/*.whl
```

### Installing Local Changes

```bash
# Already installed? This reinstalls
pip install -e . --force-reinstall --no-deps
```

### Cleaning Build Artifacts

```bash
rm -rf build/ dist/ *.egg-info/ .pytest_cache/ htmlcov/
rm -rf __pycache__ appt_ocr/__pycache__ tests/__pycache__
```

---

Happy coding! 🚀
