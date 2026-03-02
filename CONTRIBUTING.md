# Contributing to Appt-OCR

Thank you for your interest in contributing to Appt-OCR! This document provides guidelines for contributing to the project.

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/aarontzeng/Appt-OCR.git
   cd Appt-OCR
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or: venv\Scripts\activate  # Windows
   ```

3. **Install in development mode**:
   ```bash
   pip install -e ".[dev,lama]"
   ```

## Code Style

- **Python**: Follow [PEP 8](https://peps.python.org/pep-0008/).
- **Type Hints**: All function signatures must include type annotations.
- **Docstrings**: Use [Google-style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) docstrings.
- **Linter**: We use [Ruff](https://docs.astral.sh/ruff/) for linting.

```bash
# Run the linter
ruff check appt_ocr/

# Auto-fix issues
ruff check --fix appt_ocr/
```

## Making Changes

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and ensure:
   - Code passes `ruff check`
   - New functions have type hints and docstrings
   - The CLI still works: `python -m appt_ocr.cli --help`

3. **Commit** using [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat: add support for DOCX input
   fix: prevent crash on empty slides
   docs: update CLI reference table
   ```

4. **Open a Pull Request** against `main`.

## Reporting Issues

When filing a bug report, please include:

- Python version (`python --version`)
- OS and version
- PaddleOCR / PaddlePaddle versions (`pip show paddleocr paddlepaddle`)
- Full error traceback
- A minimal reproduction case (if possible, a small `.pptx` file demonstrating the issue)

## Feature Requests

Feature requests are welcome! Please use the GitHub Issue template and describe:

- The problem you're trying to solve
- Your proposed solution (if any)
- Any alternatives you've considered

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
