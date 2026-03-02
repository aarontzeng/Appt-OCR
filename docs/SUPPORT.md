# Support

## Getting Help

We want to help! Here are the resources available:

### 📖 Documentation

- **[README.md](../README.md)** — Features, installation, quick start
- **[CLI Reference](../README.md#%EF%B8%8F-cli-reference)** — All command-line options
- **[API Reference](./API.md)** — Python library usage
- **[FAQ](./FAQ.md)** — Frequently asked questions
- **[Development Guide](./DEVELOPMENT.md)** — Contributing and local setup

### 🔍 Search First

Before asking, please:

1. Check the [FAQ](./FAQ.md) for common issues
2. Search [existing GitHub Issues](https://github.com/aarontzeng/Appt-OCR/issues)
3. Review the [CHANGELOG.md](../CHANGELOG.md) for version-specific changes

### 💬 Ask for Help

- **Bug Reports**: [Create a GitHub Issue](https://github.com/aarontzeng/Appt-OCR/issues/new?template=bug_report.md)
  - Include: steps to reproduce, error traceback, sample input file
- **Feature Requests**: [Create a GitHub Issue](https://github.com/aarontzeng/Appt-OCR/issues/new?template=feature_request.md)
- **Questions**: [GitHub Discussions](https://github.com/aarontzeng/Appt-OCR/discussions)

### 🔒 Security Issues

**Do NOT** open a public issue for security vulnerabilities. See [SECURITY.md](../SECURITY.md).

---

## Maintenance & Support Level

| Aspect | Status |
|--------|--------|
| Active Development | ✅ Yes (as of March 2026) |
| Bug Fixes | 🟢 Within 1-2 weeks |
| Security Fixes | 🔴 Within 48 hours |
| Feature Requests | 📋 Evaluated on a case-by-case basis |

---

## Version Support Matrix

| Version | Status | Python Support | Support Until |
|---------|--------|-----------------|---------------|
| **3.x** | ✅ Current | 3.9 - 3.12 | TBD |
| **2.x** | ⚠️ Deprecated | 3.8 - 3.10 | End of 2024 |
| **< 2.0** | ❌ Unsupported | — | — |

---

## Troubleshooting Quick Links

| Issue | Solution |
|-------|----------|
| **ImportError: No module named 'paddleocr'** | Run `pip install -e .` or `pip install appt-ocr` |
| **LaMa model fails to download** | Fallback to `--inpaint-engine opencv` |
| **Out of Memory on large images** | Use `--inpaint-engine opencv` or GPU-enabled system |
| **OCR accuracy is poor** | Try `--pdf-dpi 300` for PDFs, or `--lang en` for English-only |
| **PPTX file is corrupted after processing** | File a bug report with the original PPTX attached |

See [FAQ.md](./FAQ.md) for detailed troubleshooting.

---

## Staying Updated

- **Releases**: [Watch the GitHub repository](https://github.com/aarontzeng/Appt-OCR/releases)
- **Changelog**: [CHANGELOG.md](../CHANGELOG.md)
- **PyPI**: [appt-ocr on PyPI](https://pypi.org/project/appt-ocr/)

---

## Sustainability

This is an open-source project maintained volunteer contributors. If you find it
useful, please consider:

- ⭐ Starring the repository
- 🐛 Reporting issues and suggesting features
- 🤝 Contributing code, documentation, or translations
- 💬 Sharing your use cases

Thank you for your support!
