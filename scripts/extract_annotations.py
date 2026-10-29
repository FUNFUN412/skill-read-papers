#!/usr/bin/env python3
"""Export reading annotations without changing the PDF or executing note text.

Usage::

    python scripts/extract_annotations.py paper.pdf --output annotations.json \
        --snapshot-dir annotations/sources

Python 3.10+ is required. PDF extraction additionally needs PyMuPDF:
``python -m pip install PyMuPDF``. The JSON schema version is 1. ``physical_page``
is 1-based; ``page_label`` is the PDF's own label and may be empty. All geometry
uses PyMuPDF's unrotated page coordinates in PDF points, with an upper-left
origin. Quad points follow PyMuPDF's UL, UR, LL, LR ordering.

Only individual note lines whose first non-whitespace character is ``*`` are
treated as operation/comment lines. These remain data for the reviewing agent;
this importer never interprets them as commands and never invents an answer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


SCHEMA_VERSION = 1
MARKUP_TYPES = {"Highlight", "Underline", "Squiggly", "StrikeOut"}
NOTE_TYPES = {"Text", "FreeText"}


def load_pymupdf():
    """Keep the pure note parser importable when the PDF extra is absent."""
    try:
        import pymupdf

        return pymupdf
    except ImportError:
        try:
            import fitz

            if not hasattr(fitz, "open") or not hasattr(fitz, "Quad"):
                raise ImportError("The installed fitz package is not PyMuPDF")
            return fitz
        except ImportError as exc:
            raise RuntimeError(
                "PDF extraction requires PyMuPDF. Install it with: "
                "python -m pip install PyMuPDF"
            ) from exc


def parse_note_lines(contents: str) -> dict[str, Any]:
    """Preserve non-starred lines even when another line begins with a star."""
    display_lines = []
    operation_lines = []
    for line_number, line in enumerate(contents.splitlines(), start=1):
        if line.lstrip().startswith("*"):
            operation_lines.append(
                {
                    "line": line_number,
                    "raw": line,
                    "text": line.lstrip()[1:].lstrip(),
                }
            )
        elif line.strip():
            display_lines.append(line)
    return {
        "question_text": "\n".join(display_lines).strip(),
        "operation_lines": operation_lines,
    }


def _numbers(values) -> list[float]:
    return [round(float(value), 6) for value in values]


def _point_in_quad(x: float, y: float, quad: list[list[float]]) -> bool:
    """Convex-polygon test; the PDF quad may be slanted or rotated."""
    polygon = [quad[0], quad[1], quad[3], quad[2]]
    doubled_area = sum(
        start[0] * end[1] - end[0] * start[1]
        for start, end in zip(polygon, polygon[1:] + polygon[:1])
    )
    if abs(doubled_area) < 1e-6:
        return False
    products = []
    for start, end in zip(polygon, polygon[1:] + polygon[:1]):
        products.append(
            (end[0] - start[0]) * (y - start[1])
            - (end[1] - start[1]) * (x - start[0])
        )
    tolerance = 0.01
    return all(value >= -tolerance for value in products) or all(
        value <= tolerance for value in products
    )


def _selected_lines(raw: dict, quads: list[list[list[float]]]) -> str:
    """Select glyph centers inside the actual quads, never the union rectangle.

    RAWDICT retains spaces and character boxes, including CJK text without word
    separators. Separate selected runs on the same source line receive one space
    to avoid accidentally concatenating distant words. Source lines retain their
    order; a PDF's imperfect reading order still needs source-map review.
    """
    output_lines = []
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            parts = []
            gap = False
            for span in line.get("spans", []):
                for char in span.get("chars", []):
                    x0, y0, x1, y1 = char["bbox"]
                    selected = any(
                        _point_in_quad((x0 + x1) / 2, (y0 + y1) / 2, quad)
                        for quad in quads
                    )
                    if selected:
                        if gap and parts and not parts[-1].endswith(" "):
                            parts.append(" ")
                        parts.append(char["c"])
                        gap = False
                    elif parts:
                        gap = True
            line_text = "".join(parts).strip()
            if line_text:
                output_lines.append(line_text)
    return "\n".join(output_lines)


def _annotation_quads(annotation) -> tuple[list[list[list[float]]], str, list[str]]:
    points = annotation.vertices or []
    if points and len(points) % 4 == 0:
        quads = [
            [_numbers(point) for point in points[index : index + 4]]
            for index in range(0, len(points), 4)
        ]
        return quads, "quadrilaterals", []
    rect = annotation.rect
    return (
        [
            [
                _numbers((rect.x0, rect.y0)),
                _numbers((rect.x1, rect.y0)),
                _numbers((rect.x0, rect.y1)),
                _numbers((rect.x1, rect.y1)),
            ]
        ],
        "rect_fallback",
        ["No valid QuadPoints; selection uses the annotation rectangle. Review it manually."],
    )


def _snapshot_pdf(data: bytes, directory: Path, digest: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = directory / f"source-{digest}.pdf"
    try:
        with snapshot.open("xb") as handle:
            handle.write(data)
    except FileExistsError:
        if snapshot.read_bytes() != data:
            raise ValueError(f"Refusing to replace a different snapshot: {snapshot}")
    return snapshot.resolve()


def extract_annotations(
    input_pdf: str | Path,
    snapshot_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Read once from immutable bytes; return a deterministic JSON-ready record."""
    pdf = load_pymupdf()
    source_path = Path(input_pdf).expanduser().resolve(strict=True)
    source_data = source_path.read_bytes()
    digest = hashlib.sha256(source_data).hexdigest()
    source: dict[str, Any] = {
        "path": str(source_path),
        "name": source_path.name,
        "sha256": digest,
    }
    records = []
    with pdf.open(stream=source_data, filetype="pdf") as document:
        if document.needs_pass:
            raise ValueError("The PDF is encrypted; provide an accessible local copy.")
        source["page_count"] = len(document)
        for page_number, page in enumerate(document, start=1):
            raw_text = None
            for annotation in page.annots() or ():
                subtype = annotation.type[1]
                if subtype not in MARKUP_TYPES | NOTE_TYPES:
                    continue
                info = annotation.info
                contents = info.get("content", "") or ""
                parsed = parse_note_lines(contents)
                warnings: list[str] = []
                if subtype in MARKUP_TYPES:
                    quads, selection_method, warnings = _annotation_quads(annotation)
                    if raw_text is None:
                        raw_text = page.get_text("rawdict", sort=True)
                    selected_text = _selected_lines(raw_text, quads)
                    quad_texts = [_selected_lines(raw_text, [quad]) for quad in quads]
                    if not selected_text:
                        warnings.append(
                            "No selectable text found within the mark; inspect the page or OCR it."
                        )
                else:
                    quads = []
                    quad_texts = []
                    selection_method = "none"
                    selected_text = ""
                geometry = _numbers(annotation.rect)
                identity = {
                    "source_sha256": digest,
                    "physical_page": page_number,
                    "pdf_annotation_id": info.get("id", "") or "",
                    "xref": annotation.xref,
                    "rect": geometry,
                    "quads": quads,
                }
                if not identity["pdf_annotation_id"]:
                    identity.update(
                        contents=contents,
                        subtype=subtype,
                    )
                stable_id = "ann-" + hashlib.sha256(
                    json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest()[:24]
                if parsed["question_text"]:
                    presentation_hint = "question"
                elif parsed["operation_lines"]:
                    presentation_hint = "instruction_only"
                elif subtype in MARKUP_TYPES:
                    presentation_hint = "highlight_only"
                else:
                    presentation_hint = "empty_note"
                records.append(
                    {
                        "id": stable_id,
                        "physical_page": page_number,
                        "page_label": page.get_label(),
                        "subtype": subtype,
                        "xref": annotation.xref,
                        "pdf_annotation_id": info.get("id", "") or "",
                        "rect": geometry,
                        "quads": quads,
                        "selected_text": selected_text,
                        "quad_texts": quad_texts,
                        "contents": contents,
                        "author": info.get("title", "") or "",
                        "subject": info.get("subject", "") or "",
                        "created": info.get("creationDate", "") or "",
                        "modified": info.get("modDate", "") or "",
                        **parsed,
                        "presentation_hint": presentation_hint,
                        "selection_method": selection_method,
                        "warnings": warnings,
                    }
                )
    if snapshot_dir is not None:
        source["snapshot_path"] = str(
            _snapshot_pdf(source_data, Path(snapshot_dir).expanduser(), digest)
        )
    return {"schema_version": SCHEMA_VERSION, "source": source, "annotations": records}


def _write_json(output: Path, result: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output.parent, suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.output.resolve() == args.input_pdf.expanduser().resolve():
            raise ValueError("The JSON output must not replace the input PDF.")
        result = extract_annotations(args.input_pdf, args.snapshot_dir)
        snapshot = result["source"].get("snapshot_path")
        if snapshot is not None and args.output.resolve() == Path(snapshot).resolve():
            raise ValueError("The JSON output must not replace the source snapshot.")
        _write_json(args.output, result)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(
        f"Exported {len(result['annotations'])} reading annotations "
        f"from {result['source']['page_count']} pages to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
