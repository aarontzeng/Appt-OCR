"""Command-line interface for Appt-OCR.

Argument parsing, input file resolution, the batch loop and the summary.
Exit status: 0 when every file was processed, 1 when any file failed or no
input file was found, 2 for a usage error (argparse, an invalid regex).
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

from appt_ocr.inpainting import get_lama_model
from appt_ocr.ocr import get_ocr_engine
from appt_ocr.pdf import convert_pdf_to_pptx
from appt_ocr.processing import ProcessingOptions, process_pptx

SUPPORTED_SUFFIXES = (".pptx", ".pdf")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="appt-ocr",
        description=(
            "Appt-OCR: Batch PPTX/PDF OCR Processing Tool — "
            "Converts images in presentations to editable text boxes"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  appt-ocr presentation.pptx\n"
            "  appt-ocr *.pptx --output-dir output/\n"
            "  appt-ocr slides.pptx --keep-images --lang en\n"
            "  appt-ocr report.pdf --inpaint-engine lama\n"
            "\n"
            "Exit status: 0 all files processed, 1 any file failed, 2 usage error.\n"
        ),
    )
    parser.add_argument(
        "input",
        nargs="+",
        help="Input PPTX/PDF file path (supports multiple files and wildcards)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory (default: output/)",
    )
    parser.add_argument(
        "--keep-images",
        action="store_true",
        default=False,
        help="Keep original image Shapes (default: delete original images)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=96,
        help="Image DPI (default: 96)",
    )
    parser.add_argument(
        "--lang",
        choices=["ch", "en"],
        default="ch",
        help="OCR Language: ch=bilingual, en=English only (default: ch)",
    )
    parser.add_argument(
        "--merge-threshold",
        type=float,
        default=0.5,
        help=(
            "Text box merge threshold coefficient (default: 0.5, "
            "higher values merge more aggressively)"
        ),
    )
    parser.add_argument(
        "--ignore-re",
        type=str,
        default="",
        help=(
            "Regex: Text matching this pattern will be kept on the original "
            "image (not erased, no text box created). "
            "Example: 'P\\\\s*=|Ploss' to keep math formulas."
        ),
    )
    parser.add_argument(
        "--remove-re",
        type=str,
        default="",
        help=(
            "Regex: Text matching this pattern will be erased silently "
            "(no text box created). Useful for removing watermarks. "
            "Example: '(?i)notebooklm' to erase NotebookLM watermarks, "
            "'(?i)confidential|draft' to erase draft watermarks."
        ),
    )
    parser.add_argument(
        "--inpaint-engine",
        choices=["lama", "opencv"],
        default="lama",
        help=(
            "Text erasing engine: lama=LaMa deep learning model (high quality, "
            'needs `pip install "appt-ocr[lama]"`; falls back to opencv when '
            "missing), opencv=OpenCV traditional algorithm (lightweight). "
            "Default: lama"
        ),
    )
    parser.add_argument(
        "--pdf-dpi",
        type=int,
        default=300,
        help="PDF rendering resolution (DPI). Default 300. Suggested range: 150~300.",
    )
    parser.add_argument(
        "--watermark-only",
        action="store_true",
        default=False,
        help=(
            "Watermark-only mode: Only erases text matching --remove-re, "
            "skips full OCR text box reconstruction."
        ),
    )
    parser.add_argument(
        "--no-s2t",
        action="store_true",
        default=False,
        help=(
            "Disable Simplified-to-Traditional Chinese conversion. "
            "By default, PaddleOCR's simplified output is converted to "
            "traditional (automatically skipped when --lang en)."
        ),
    )
    return parser


def resolve_input_files(patterns: list[str]) -> list[str]:
    """Expand wildcards and keep the .pptx/.pdf files, in order, once each."""
    files: list[str] = []
    for pattern in patterns:
        expanded = sorted(glob.glob(pattern))
        if not expanded:
            print(f"⚠ Warning: Could not find files matching '{pattern}', skipped")
            continue
        for f in expanded:
            if not f.lower().endswith(SUPPORTED_SUFFIXES):
                print(f"⚠ Warning: '{f}' is not a .pptx or .pdf file, skipped")
            elif f not in files:
                files.append(f)
    return files


def options_from_args(args: argparse.Namespace) -> ProcessingOptions:
    """The pipeline options for parsed arguments (raises ValueError on a bad one)."""
    return ProcessingOptions(
        dpi=args.dpi,
        lang=args.lang,
        keep_images=args.keep_images,
        merge_threshold=args.merge_threshold,
        ignore_re=args.ignore_re,
        remove_re=args.remove_re,
        inpaint_engine=args.inpaint_engine,
        watermark_only=args.watermark_only,
        s2t=not args.no_s2t and args.lang != "en",
    )


def _print_banner(
    args: argparse.Namespace, opts: ProcessingOptions, n_files: int
) -> None:
    print("=" * 60)
    print("  Appt-OCR — Batch PPTX/PDF OCR Processing Tool")
    print("=" * 60)
    print(f"  Input Files:   {n_files}")
    print(f"  Output Dir:    {args.output_dir}")
    print(f"  OCR Language:  {'Bilingual' if opts.lang == 'ch' else 'English Only'}")
    print(f"  Keep Images:   {'Yes' if opts.keep_images else 'No'}")
    print(f"  DPI:           {opts.dpi}")
    print(f"  Merge Thresh:  {opts.merge_threshold}")
    engine_label = (
        "LaMa Deep Learning" if opts.inpaint_engine == "lama" else "OpenCV Traditional"
    )
    print(f"  Erase Engine:  {engine_label}")
    print(f"  PDF DPI:       {args.pdf_dpi}")
    print(f"  S2T Convert:   {'Enabled (OpenCC s2t)' if opts.s2t else 'Disabled'}")
    if opts.watermark_only:
        print("  Mode:          Watermark-only Erase")
    if opts.ignore_re:
        print(f"  Ignore Regex:  {opts.ignore_re}")
    if opts.remove_re:
        print(f"  Remove Regex:  {opts.remove_re}")
    print("=" * 60)


def _preload_engines(opts: ProcessingOptions) -> ProcessingOptions:
    """Load the OCR engine (and LaMa) once, before the first file.

    Returns the options to run with: the OpenCV engine when LaMa was asked
    for but is not available.
    """
    print("\n⏳ Loading OCR Engine...")
    get_ocr_engine(opts.lang)
    print("✅ OCR Engine Ready")
    if opts.inpaint_engine == "lama":
        print("⏳ Loading LaMa Inpainting Model...")
        if get_lama_model() is None:
            print("⚠ LaMa unavailable, automatically downgrading to OpenCV engine")
            opts = opts.with_engine("opencv")
        else:
            print("✅ LaMa Model Ready")
    print()
    return opts


def _process_file(
    input_file: str, output_dir: str, pdf_dpi: int, opts: ProcessingOptions
) -> dict:
    """Process one input file; a failure is a result with an ``error`` key."""
    output_path = os.path.join(output_dir, Path(input_file).stem + "_ocr.pptx")
    print(f"📄 Processing: {input_file}")

    tmp_pptx: str | None = None
    try:
        actual_input = input_file
        if input_file.lower().endswith(".pdf"):
            try:
                tmp_pptx = actual_input = convert_pdf_to_pptx(input_file, dpi=pdf_dpi)
            except Exception as e:
                print(f"   ❌ PDF Conversion Failed: {e}")
                return {"input": input_file, "error": str(e)}
        try:
            stats = process_pptx(actual_input, output_path, options=opts)
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return {"input": input_file, "error": str(e)}
    finally:
        if tmp_pptx:
            try:
                os.unlink(tmp_pptx)
            except OSError:
                pass

    stats["input"] = input_file  # the original name, not the temp PPTX
    print(f"   ✅ Complete -> {output_path}")
    print(
        f"      Slides: {stats['total_slides']} | "
        f"Contains Img: {stats['processed_slides']} | "
        f"Text Boxes: {stats['total_textboxes']}"
    )
    return stats


def _print_summary(results: list[dict]) -> None:
    print("\n" + "=" * 60)
    print("  Processing Complete! Summary")
    print("=" * 60)
    success_count = sum(1 for r in results if "error" not in r)
    fail_count = len(results) - success_count
    total_boxes = sum(r.get("total_textboxes", 0) for r in results)
    print(f"  Success: {success_count} files")
    if fail_count:
        print(f"  Failed:  {fail_count} files")
    print(f"  Total Text Boxes: {total_boxes}")
    print("=" * 60)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the exit status (see the module docstring)."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        opts = options_from_args(args)
    except ValueError as exc:
        parser.error(str(exc))  # exits 2, before any model is loaded

    input_files = resolve_input_files(args.input)
    if not input_files:
        print("❌ Error: No valid .pptx/.pdf input files found")
        return 1

    _print_banner(args, opts, len(input_files))
    opts = _preload_engines(opts)
    results = [
        _process_file(f, args.output_dir, args.pdf_dpi, opts) for f in input_files
    ]
    _print_summary(results)
    return 1 if any("error" in r for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
