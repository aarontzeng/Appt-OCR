"""Command-line interface for Appt-OCR.

Provides the CLI argument parser, file resolution, and main entry point.
"""

import argparse
import glob
import os
import sys
from pathlib import Path

from appt_ocr.inpainting import get_lama_model
from appt_ocr.ocr import get_ocr_engine
from appt_ocr.pdf import convert_pdf_to_pptx
from appt_ocr.processing import process_pptx


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
            '  appt-ocr *.pptx --output-dir output/\n'
            "  appt-ocr slides.pptx --keep-images --lang en\n"
            "  appt-ocr report.pdf --inpaint-engine lama\n"
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
        default="(?i)notebooklm",
        help=(
            "Regex: Text matching this pattern will be erased silently "
            "(no text box created). Defaults to '(?i)notebooklm' to "
            "remove watermarks."
        ),
    )
    parser.add_argument(
        "--inpaint-engine",
        choices=["lama", "opencv"],
        default="lama",
        help=(
            "Text erasing engine: lama=LaMa deep learning model (high quality), "
            "opencv=OpenCV traditional algorithm (lightweight). Default: lama"
        ),
    )
    parser.add_argument(
        "--pdf-dpi",
        type=int,
        default=300,
        help=(
            "PDF rendering resolution (DPI). Default 300. "
            "Suggested range: 150~300."
        ),
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
    """Expand wildcards and validate input files.

    Args:
        patterns: List of file paths (may contain glob wildcards).

    Returns:
        List of validated PPTX/PDF file paths.
    """
    files: list[str] = []
    supported = (".pptx", ".pdf")
    for pattern in patterns:
        expanded = glob.glob(pattern)
        if not expanded:
            print(f"⚠ Warning: Could not find files matching '{pattern}', skipped")
            continue
        for f in expanded:
            if f.lower().endswith(supported):
                files.append(f)
            else:
                print(f"⚠ Warning: '{f}' is not a .pptx or .pdf file, skipped")
    return files


def main() -> None:
    """CLI main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    # Expand and validate input files
    input_files = resolve_input_files(args.input)
    if not input_files:
        print("❌ Error: No valid .pptx/.pdf input files found")
        sys.exit(1)

    print("=" * 60)
    print("  Appt-OCR — Batch PPTX/PDF OCR Processing Tool")
    print("=" * 60)
    print(f"  Input Files:   {len(input_files)}")
    print(f"  Output Dir:    {args.output_dir}")
    print(
        f"  OCR Language:  {'Bilingual' if args.lang == 'ch' else 'English Only'}"
    )
    print(f"  Keep Images:   {'Yes' if args.keep_images else 'No'}")
    print(f"  DPI:           {args.dpi}")
    print(f"  Merge Thresh:  {args.merge_threshold}")
    engine_label = (
        "LaMa Deep Learning"
        if args.inpaint_engine == "lama"
        else "OpenCV Traditional"
    )
    print(f"  Erase Engine:  {engine_label}")
    print(f"  PDF DPI:       {args.pdf_dpi}")

    # Determine whether to enable OpenCC s2t conversion
    enable_s2t = not args.no_s2t and args.lang != "en"
    if enable_s2t:
        print("  S2T Convert:   Enabled (OpenCC s2t)")
    else:
        print("  S2T Convert:   Disabled")
    if args.watermark_only:
        print("  Mode:          Watermark-only Erase")
    if args.ignore_re:
        print(f"  Ignore Regex:  {args.ignore_re}")
    if args.remove_re:
        print(f"  Remove Regex:  {args.remove_re}")
    print("=" * 60)

    # Initialize OCR Engine (load early to avoid repeating per file)
    print("\n⏳ Loading OCR Engine...")
    get_ocr_engine(args.lang)
    print("✅ OCR Engine Ready")

    # If LaMa is selected, preload the model
    if args.inpaint_engine == "lama":
        print("⏳ Loading LaMa Inpainting Model...")
        lama = get_lama_model()
        if lama is None:
            print("⚠ LaMa unavailable, automatically downgrading to OpenCV engine")
            args.inpaint_engine = "opencv"
        else:
            print("✅ LaMa Model Ready")
    print()

    # Batch Process
    results: list[dict] = []
    tmp_files: list[str] = []  # Track temp files needing cleanup

    for input_file in input_files:
        output_name = Path(input_file).stem + "_ocr.pptx"
        output_path = os.path.join(args.output_dir, output_name)

        print(f"📄 Processing: {input_file}")

        # PDF Preprocessing: Convert to temporary PPTX
        actual_input = input_file
        if input_file.lower().endswith(".pdf"):
            try:
                actual_input = convert_pdf_to_pptx(
                    input_file, dpi=args.pdf_dpi
                )
                tmp_files.append(actual_input)
            except Exception as e:
                print(f"   ❌ PDF Conversion Failed: {e}")
                results.append({"input": input_file, "error": str(e)})
                continue

        try:
            stats = process_pptx(
                input_path=actual_input,
                output_path=output_path,
                dpi=args.dpi,
                lang=args.lang,
                keep_images=args.keep_images,
                merge_threshold=args.merge_threshold,
                ignore_re=args.ignore_re,
                remove_re=args.remove_re,
                inpaint_engine=args.inpaint_engine,
                watermark_only=args.watermark_only,
                s2t=enable_s2t,
            )
            results.append(stats)
            # Display original filename instead of temp path
            stats["input"] = input_file
            print(f"   ✅ Complete -> {output_path}")
            print(
                f"      Slides: {stats['total_slides']} | "
                f"Contains Img: {stats['processed_slides']} | "
                f"Text Boxes: {stats['total_textboxes']}"
            )
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results.append({"input": input_file, "error": str(e)})

    # Cleanup temporary PDF->PPTX files
    for tmp in tmp_files:
        try:
            os.unlink(tmp)
        except OSError:
            pass

    # Summary
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


if __name__ == "__main__":
    main()
