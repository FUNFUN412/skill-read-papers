"""Synthetic fixtures test annotation geometry, note semantics, and preservation."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "extract_annotations.py"
SPEC = importlib.util.spec_from_file_location("extract_annotations", SCRIPT)
importer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(importer)

try:
    pdf = importer.load_pymupdf()
except RuntimeError:
    pdf = None


class NoteParsingTests(unittest.TestCase):
    def test_stars_comment_individual_lines_only(self):
        text = "  * move this explanation\nWhat is q?\n\t* keep it short\nWhy x* is used?"
        result = importer.parse_note_lines(text)
        self.assertEqual(result["question_text"], "What is q?\nWhy x* is used?")
        self.assertEqual([item["line"] for item in result["operation_lines"]], [1, 3])
        self.assertEqual(result["operation_lines"][0]["raw"], "  * move this explanation")

    def test_empty_quad_does_not_match_the_entire_page(self):
        self.assertFalse(importer._point_in_quad(100, 200, [[0, 0]] * 4))


@unittest.skipIf(pdf is None, "Install PyMuPDF to run PDF integration tests")
class PDFAnnotationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "synthetic.pdf"
        with pdf.open() as document:
            page = document.new_page(width=600, height=800)
            page.insert_text((40, 70), "first TARGET unselected tail", fontsize=12)
            page.insert_text((40, 100), "second OTHER not selected", fontsize=12)
            page.insert_text((40, 130), "third SINGLE only", fontsize=12)
            multi = page.add_highlight_annot(
                page.search_for("TARGET", quads=True) + page.search_for("OTHER", quads=True)
            )
            multi.set_info(
                content="* do not display this line\nWhy these two words?\n* use a numeric example",
                title="Synthetic reader",
            )
            multi.update()
            single = page.add_underline_annot(page.search_for("SINGLE", quads=True))
            single.update()
            note = page.add_text_annot((300, 160), "A plain note")
            note.set_info(title="Synthetic reader")
            note.update()
            page.insert_link(
                {"kind": pdf.LINK_URI, "from": pdf.Rect(40, 200, 150, 220), "uri": "https://example.org"}
            )
            page2 = document.new_page(width=600, height=800)
            page2.insert_text((40, 70), "A note on an unnumbered page", fontsize=12)
            page2.add_freetext_annot(pdf.Rect(40, 100, 220, 140), "* comment only")
            document.set_page_labels(
                [{"startpage": 0, "prefix": "body-", "style": "D", "firstpagenum": 9},
                 {"startpage": 1, "prefix": "", "style": ""}]
            )
            document.save(self.source)
        self.original = self.source.read_bytes()

    def tearDown(self):
        self.temporary.cleanup()

    def test_quad_text_excludes_between_line_union_rectangle(self):
        result = importer.extract_annotations(self.source)
        self.assertEqual(len(result["annotations"]), 4)
        highlight = next(item for item in result["annotations"] if item["subtype"] == "Highlight")
        self.assertEqual(highlight["selected_text"], "TARGET\nOTHER")
        self.assertEqual(highlight["quad_texts"], ["TARGET", "OTHER"])
        self.assertEqual(highlight["selection_method"], "quadrilaterals")
        self.assertEqual(highlight["question_text"], "Why these two words?")
        self.assertEqual(len(highlight["operation_lines"]), 2)
        self.assertEqual(highlight["author"], "Synthetic reader")
        self.assertEqual(highlight["physical_page"], 1)
        self.assertEqual(highlight["page_label"], "body-9")
        self.assertTrue(highlight["pdf_annotation_id"])
        underline = next(item for item in result["annotations"] if item["subtype"] == "Underline")
        self.assertEqual(underline["selected_text"], "SINGLE")
        self.assertEqual(underline["presentation_hint"], "highlight_only")
        self.assertEqual(underline["question_text"], "")
        free_text = next(item for item in result["annotations"] if item["subtype"] == "FreeText")
        self.assertEqual(free_text["physical_page"], 2)
        self.assertEqual(free_text["page_label"], "")
        self.assertEqual(free_text["presentation_hint"], "instruction_only")
        self.assertEqual(free_text["selected_text"], "")

    def test_snapshot_and_repeat_are_byte_preserving_and_deterministic(self):
        snapshots = self.root / "snapshots"
        first = importer.extract_annotations(self.source, snapshots)
        second = importer.extract_annotations(self.source, snapshots)
        self.assertEqual(first, second)
        self.assertEqual(first["source"]["sha256"], hashlib.sha256(self.original).hexdigest())
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(Path(first["source"]["snapshot_path"]).read_bytes(), self.original)
        self.assertEqual(len(list(snapshots.iterdir())), 1)
        ids = [item["id"] for item in first["annotations"]]
        self.assertEqual(len(ids), len(set(ids)))
        Path(first["source"]["snapshot_path"]).write_bytes(b"existing different data")
        with self.assertRaisesRegex(ValueError, "Refusing to replace"):
            importer.extract_annotations(self.source, snapshots)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_cli_refuses_to_overwrite_input_pdf(self):
        with contextlib.redirect_stderr(io.StringIO()):
            status = importer.main([str(self.source), "--output", str(self.source)])
        self.assertEqual(status, 1)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_cli_outputs_json_and_preserves_source(self):
        output = self.root / "export" / "annotations.json"
        with contextlib.redirect_stdout(io.StringIO()):
            status = importer.main(
                [str(self.source), "--output", str(output), "--snapshot-dir", str(self.root / "snapshots")]
            )
        self.assertEqual(status, 0)
        import json

        result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(len(result["annotations"]), 4)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_cjk_selection_and_original_unicode_note_are_preserved(self):
        unicode_source = self.root / "unicode.pdf"
        with pdf.open() as document:
            page = document.new_page()
            page.insert_text((40, 70), "前文概率后文", fontname="china-s", fontsize=14)
            mark = page.add_highlight_annot(page.search_for("概率", quads=True))
            mark.set_info(content="*这一行作为指令\n这里的概率是什么意思？")
            mark.update()
            document.save(unicode_source)
        result = importer.extract_annotations(unicode_source)
        record = result["annotations"][0]
        self.assertEqual(record["selected_text"], "概率")
        self.assertEqual(record["contents"], "*这一行作为指令\n这里的概率是什么意思？")
        self.assertEqual(record["question_text"], "这里的概率是什么意思？")


if __name__ == "__main__":
    unittest.main()
