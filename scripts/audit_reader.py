#!/usr/bin/env python3
"""Run machine checks on a compiled reading PDF; this is not visual review.

Usage:
    python audit_reader.py main.pdf --plan pages.json --output qa_report.json \
        [--positions positions.json] [--log main.log] [--tolerance 0.5]

Requires PyMuPDF (``python -m pip install pymupdf``).
Plan schema (all fields except each listed page's physical_page are optional):
    {"expected_physical_pages": 3, "header_band_fraction": 0.2,
     "pages": [{"physical_page": 1, "kind": "body", "printed_label": "1",
                "header_text": "Paper title"},
               {"physical_page": 2, "kind": "detail", "printed_label": null,
                "header_text": "Detailed explanation page"}]}
Physical pages are one-based. A null printed_label means the empty PDF label;
detail pages default to that requirement. An omitted label on a body page is
unchecked. A header must match one whitespace-normalized text line in the top
header_band_fraction of the page. Page label checks concern PDF labels, not
the visual presence/absence of a footer; inspect that separately.

Optional positions schema:
    {"rows": [{"id": "P001", "english": {"page": 1, "y": 100.0},
               "chinese": {"page": 1, "y": 100.1}}]}
y is a baseline in PDF points measured from the top of the physical page.
These coordinates are supplied metadata, not remeasured by this helper.
Tolerance applies to baseline alignment and page-boundary checks.

The report records exact checks and errors. Exit 0 means the specified machine
checks passed, 1 means a check failed, and 2 means an input/dependency error.
No source files, input PDFs, or plans are changed.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys


SCOPE = (
    "Machine checks only: PDF page labels, specified header lines, extracted "
    "text bounds/glyphs, supplied baseline coordinates, and optional LaTeX log. "
    "This does not establish visual quality, source completeness, mathematical "
    "correctness, footer numbering, or annotation alignment."
)


def finite_number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def positive_integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def normalized(text):
    return " ".join(text.split())


def load_object(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def validate_plan(plan, page_count):
    errors = []
    expected = plan.get("expected_physical_pages")
    if expected is not None and not positive_integer(expected):
        errors.append("expected_physical_pages must be a positive integer")
    fraction = plan.get("header_band_fraction", 0.2)
    if not finite_number(fraction) or not 0 < fraction <= 1:
        errors.append("header_band_fraction must be greater than 0 and at most 1")
    entries = plan.get("pages", [])
    if not isinstance(entries, list):
        return errors + ["pages must be a list"]
    seen = set()
    for index, entry in enumerate(entries):
        prefix = f"pages[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        page = entry.get("physical_page")
        if not positive_integer(page) or page > page_count:
            errors.append(f"{prefix}.physical_page must identify an existing one-based page")
        elif page in seen:
            errors.append(f"{prefix}.physical_page duplicates page {page}")
        else:
            seen.add(page)
        if entry.get("kind", "body") not in ("body", "detail"):
            errors.append(f"{prefix}.kind must be body or detail")
        if "printed_label" in entry and not (
                entry["printed_label"] is None or isinstance(entry["printed_label"], str)):
            errors.append(f"{prefix}.printed_label must be a string or null")
        if "header_text" in entry and not (
                isinstance(entry["header_text"], str) and normalized(entry["header_text"])):
            errors.append(f"{prefix}.header_text must be a nonempty string")
    return errors


def check_spans(spans_by_page, page_rectangles, tolerance):
    bounds_errors, glyph_errors, hints = [], [], []
    pages_without_text, span_count = [], 0
    for page_number, spans in spans_by_page.items():
        nonempty = [span for span in spans if span.get("text", "").strip()]
        if not nonempty:
            pages_without_text.append(page_number)
        page_box = page_rectangles[page_number]
        for span in nonempty:
            span_count += 1
            text = span["text"]
            box = list(span["bbox"])
            item = {"physical_page": page_number, "text": text,
                    "bbox": box, "font": span.get("font", "")}
            if (not all(finite_number(v) for v in box)
                    or box[0] < page_box[0] - tolerance
                    or box[1] < page_box[1] - tolerance
                    or box[2] > page_box[2] + tolerance
                    or box[3] > page_box[3] + tolerance):
                bounds_errors.append(item)
            if "\ufffd" in text:
                glyph_errors.append({**item, "reason": "Unicode replacement character"})
            if "\x00" in text:
                if re.fullmatch(r"(?:[A-Z]{6}\+)?CMEX\d+", span.get("font", "")):
                    hints.append({**item, "reason": "Known CMEX NUL extraction mapping; visually inspect glyph"})
                else:
                    glyph_errors.append({**item, "reason": "NUL outside known CMEX math font"})
    return {
        "text_bounds": {"passed": not bounds_errors, "violations": bounds_errors},
        "glyphs": {"passed": not glyph_errors, "violations": glyph_errors,
                   "extraction_hints": hints},
        "text_extraction": {"nonempty_spans": span_count,
                            "pages_without_text": pages_without_text},
    }


def check_positions(positions, page_rectangles, tolerance):
    errors, details, seen = [], [], set()
    rows = positions.get("rows")
    if not isinstance(rows, list):
        return {"passed": False, "checked_rows": 0, "errors": ["rows must be a list"],
                "details": [], "source": "supplied baseline metadata"}
    for index, row in enumerate(rows):
        prefix = f"rows[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        ident = row.get("id")
        if not isinstance(ident, str) or not ident.strip():
            errors.append(f"{prefix}.id must be a nonempty string")
        elif ident in seen:
            errors.append(f"{prefix}.id duplicates {ident}")
        else:
            seen.add(ident)
        valid = True
        for language in ("english", "chinese"):
            location = row.get(language)
            if not isinstance(location, dict):
                errors.append(f"{prefix}.{language} must be an object")
                valid = False
                continue
            page, y = location.get("page"), location.get("y")
            if not positive_integer(page) or page not in page_rectangles:
                errors.append(f"{prefix}.{language}.page must identify an existing physical page")
                valid = False
            if not finite_number(y):
                errors.append(f"{prefix}.{language}.y must be a finite baseline coordinate")
                valid = False
            elif positive_integer(page) and page in page_rectangles:
                rectangle = page_rectangles[page]
                if not rectangle[1] - tolerance <= y <= rectangle[3] + tolerance:
                    errors.append(f"{prefix}.{language}.y is outside the page")
                    valid = False
        if not valid:
            continue
        english, chinese = row["english"], row["chinese"]
        difference = abs(english["y"] - chinese["y"])
        passed = english["page"] == chinese["page"] and difference <= tolerance
        details.append({"id": ident, "english": english, "chinese": chinese,
                        "baseline_difference_pt": difference, "passed": passed})
    return {"passed": not errors and all(item["passed"] for item in details),
            "checked_rows": len(details), "errors": errors, "details": details,
            "source": "supplied baseline metadata"}


def check_latex_log(path):
    patterns = {
        "missing_character": re.compile(r"Missing character", re.I),
        "undefined_reference": re.compile(
            r"(?:Reference|Citation).{0,1000}\bundefined\b|undefined references", re.I),
        "overfull_box": re.compile(r"Overfull\s+\\[hv]box", re.I),
        "fatal_error": re.compile(r"Undefined control sequence|Emergency stop|Fatal error occurred", re.I),
    }
    diagnostics = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for kind, pattern in patterns.items():
            if pattern.search(line):
                diagnostics.append({"kind": kind, "line": number, "text": line})
    return {"checked": True, "passed": not diagnostics, "diagnostics": diagnostics}


def audit(pdf_path, plan, positions=None, log_path=None, tolerance=0.5):
    try:
        import pymupdf as fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required; install it with python -m pip install pymupdf") from exc
    with fitz.open(pdf_path) as pdf:
        if not pdf.is_pdf:
            raise ValueError("The input must be a PDF")
        if pdf.needs_pass:
            raise ValueError("The PDF is encrypted and requires a password")
        errors = validate_plan(plan, len(pdf))
        if errors:
            raise ValueError("Invalid plan: " + "; ".join(errors))
        expected = plan.get("expected_physical_pages")
        checks = {"page_count": {"actual": len(pdf), "expected": expected,
                                 "passed": expected is None or expected == len(pdf)}}
        spans_by_page, lines_by_page, rectangles = {}, {}, {}
        for number, page in enumerate(pdf, 1):
            spans, lines = [], []
            # Infinite clip makes overflow outside the page detectable when the
            # PDF extractor exposes those text objects.
            for block in page.get_text("dict", clip=fitz.INFINITE_RECT())["blocks"]:
                if block["type"] != 0:
                    continue
                for line in block["lines"]:
                    spans.extend(line["spans"])
                    lines.append({"text": "".join(span["text"] for span in line["spans"]),
                                  "bbox": list(line["bbox"])})
            spans_by_page[number], lines_by_page[number] = spans, lines
            rectangles[number] = list(page.rect)
        checks.update(check_spans(spans_by_page, rectangles, tolerance))
        labels, headers = [], []
        fraction = plan.get("header_band_fraction", 0.2)
        for entry in plan.get("pages", []):
            number = entry["physical_page"]
            page = pdf[number - 1]
            if "printed_label" in entry or entry.get("kind") == "detail":
                expected_label = entry.get("printed_label") or ""
                actual = page.get_label()
                labels.append({"physical_page": number, "expected": expected_label,
                               "actual": actual, "passed": actual == expected_label})
            if "header_text" in entry:
                wanted = normalized(entry["header_text"])
                cutoff = page.rect.y0 + page.rect.height * fraction
                matches = [line for line in lines_by_page[number]
                           if normalized(line["text"]) == wanted
                           and line["bbox"][1] >= page.rect.y0 - tolerance
                           and line["bbox"][3] <= cutoff + tolerance]
                headers.append({"physical_page": number, "expected": entry["header_text"],
                                "header_band_bottom_pt": cutoff, "matches": matches,
                                "passed": bool(matches)})
        checks["page_labels"] = {"passed": all(item["passed"] for item in labels), "details": labels}
        checks["headers"] = {"passed": all(item["passed"] for item in headers), "details": headers}
        checks["paragraph_alignment"] = (
            check_positions(positions, rectangles, tolerance) if positions is not None
            else {"checked": False, "passed": True, "reason": "No positions file supplied"})
        checks["latex_log"] = (check_latex_log(log_path) if log_path is not None
                               else {"checked": False, "passed": True, "reason": "No log supplied"})
        passed = all(check.get("passed", True) for check in checks.values())
        warnings = []
        if checks["text_extraction"]["pages_without_text"]:
            warnings.append("Some pages have no extracted text; text/glyph checks cannot inspect image-only content.")
        if checks["glyphs"]["extraction_hints"]:
            warnings.append("Known CMEX extraction hints require visual confirmation of rendered math glyphs.")
        return {"schema_version": "1.0", "scope": SCOPE, "pdf": str(pdf_path),
                "tolerance_pt": tolerance, "passed": passed, "checks": checks,
                "warnings": warnings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--positions", type=Path)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--tolerance", type=float, default=0.5, help="PDF points; default 0.5")
    args = parser.parse_args(argv)
    if not math.isfinite(args.tolerance) or args.tolerance < 0:
        parser.error("--tolerance must be finite and nonnegative")
    protected = [args.pdf, args.plan, args.positions, args.log]
    if any(path is not None and path.resolve() == args.output.resolve() for path in protected):
        parser.error("--output must not overwrite an input file")
    try:
        plan = load_object(args.plan)
        positions = load_object(args.positions) if args.positions else None
        report = audit(args.pdf, plan, positions, args.log, args.tolerance)
        code = 0 if report["passed"] else 1
    except (OSError, ValueError, RuntimeError) as exc:
        report = {"schema_version": "1.0", "scope": SCOPE, "pdf": str(args.pdf),
                  "passed": False, "input_error": str(exc)}
        code = 2
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"Cannot write report: {exc}", file=sys.stderr)
        return 2
    print(f"{'PASS' if code == 0 else 'FAIL'}: machine checks; report: {args.output}")
    return code


if __name__ == "__main__":
    sys.exit(main())
