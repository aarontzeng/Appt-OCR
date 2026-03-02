# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 3.x     | ✅ Active  |
| < 3.0   | ❌ No longer supported |

## Reporting a Vulnerability

**Please DO NOT open a public GitHub issue to report security vulnerabilities.**

If you discover a security vulnerability, please disclose it responsibly by opening a **[GitHub Security Advisory](https://github.com/aarontzeng/Appt-OCR/security/advisories/new)** (private report).

### What to include

- A clear description of the vulnerability and its potential impact
- Steps to reproduce (with a minimal example if possible)
- Affected versions
- Suggested fix (if any)

### Response Timeline

| Milestone | Target |
|-----------|--------|
| Acknowledge receipt | Within 48 hours |
| Confirm/deny vulnerability | Within 5 business days |
| Publish patch (if confirmed) | Within 14 days |
| Public disclosure | After patch is released |

## Scope

This project processes local files (PPTX/PDF) using PaddleOCR and optionally
downloads a LaMa model on first run. The relevant attack surfaces are:

- **Malicious PPTX/PDF files** — crafted files that exploit parsing libraries
  (python-pptx, PyMuPDF). Please report any crash or unexpected code execution
  triggered by a specific input file.
- **Model download integrity** — if you observe the LaMa model download being
  tampered with or served from an unexpected source, please report immediately.
- **Dependency vulnerabilities** — if a new CVE affects a direct dependency
  (`paddleocr`, `Pillow`, `opencv-python-headless`, etc.), we will update the
  pinned version within 14 days of the CVE being published.

## Out of Scope

- Vulnerabilities in upstream projects (PaddleOCR, LaMa, PyMuPDF). Please
  report those directly to the respective maintainers.
- Issues requiring physical access to the machine running the tool.
