"""Observable checks for the portable reader auditor, using synthetic PDFs."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pymupdf as fitz


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_reader.py"
SPEC = importlib.util.spec_from_file_location("audit_reader", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AuditReaderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="reading-audit-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.pdf = self.root / "reader.pdf"
        with fitz.open() as doc:
            first = doc.new_page(width=300, height=400)
            first.insert_text((20, 20), "Paper title", fontsize=10)
            first.insert_text((20, 90), "English example.", fontsize=10)
            first.insert_text((160, 90), "Translation example.", fontsize=10)
            second = doc.new_page(width=300, height=400)
            second.insert_text((20, 20), "Detailed explanation page", fontsize=10)
            second.insert_text((20, 90), "Supplementary derivation.", fontsize=10)
            doc.set_page_labels([{"startpage": 0, "style": "D", "firstpagenum": 1},
                                 {"startpage": 1, "style": "", "prefix": ""}])
            doc.save(self.pdf)
        self.plan = {"expected_physical_pages": 2, "pages": [
            {"physical_page": 1, "kind": "body", "printed_label": "1", "header_text": "Paper title"},
            {"physical_page": 2, "kind": "detail", "printed_label": None,
             "header_text": "Detailed explanation page"}]}
        self.positions = {"rows": [{"id": "P001", "english": {"page": 1, "y": 90},
                                    "chinese": {"page": 1, "y": 90.2}}]}

    def test_valid_pdf_plan_and_baselines(self):
        result = MODULE.audit(self.pdf, self.plan, self.positions)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["checks"]["page_labels"]["details"][1]["actual"], "")
        self.assertEqual(result["checks"]["paragraph_alignment"]["checked_rows"], 1)

    def test_wrong_count_label_and_header_fail(self):
        self.plan["expected_physical_pages"] = 3
        self.plan["pages"][0]["printed_label"] = "9"
        self.plan["pages"][1]["header_text"] = "Absent header"
        result = MODULE.audit(self.pdf, self.plan)
        self.assertFalse(result["passed"])
        for name in ("page_count", "page_labels", "headers"):
            self.assertFalse(result["checks"][name]["passed"])

    def test_header_must_be_in_header_band(self):
        self.plan["pages"][0]["header_text"] = "English example."
        result = MODULE.audit(self.pdf, self.plan)
        self.assertFalse(result["checks"]["headers"]["passed"])

    def test_page_mismatch_and_tolerance(self):
        self.positions["rows"][0]["chinese"] = {"page": 1, "y": 91}
        self.assertFalse(MODULE.audit(self.pdf, self.plan, self.positions)["passed"])
        self.assertTrue(MODULE.audit(self.pdf, self.plan, self.positions, tolerance=1)["passed"])
        self.positions["rows"][0]["chinese"] = {"page": 2, "y": 90}
        self.assertFalse(MODULE.audit(self.pdf, self.plan, self.positions)["passed"])

    def test_invalid_inputs_are_not_silent_passes(self):
        with self.assertRaises(ValueError):
            MODULE.audit(self.pdf, {"pages": [{"physical_page": True}]})
        self.positions["rows"][0]["english"]["y"] = float("nan")
        self.assertFalse(MODULE.audit(self.pdf, self.plan, self.positions)["passed"])

    def test_real_extracted_text_overflow_is_reported(self):
        overflow = self.root / "overflow.pdf"
        with fitz.open() as doc:
            page = doc.new_page(width=300, height=400)
            page.insert_text((295, 150), "Overflow outside page", fontsize=10)
            doc.save(overflow)
        result = MODULE.audit(overflow, {})
        self.assertFalse(result["checks"]["text_bounds"]["passed"], result)

    def test_missing_glyph_and_known_cmex_hint(self):
        spans = {1: [
            {"text": "\ufffd", "bbox": [1, 1, 10, 10], "font": "Helvetica"},
            {"text": "\x00", "bbox": [1, 20, 10, 30], "font": "CMEX8"},
            {"text": "\x00", "bbox": [1, 40, 10, 50], "font": "OtherFont"}]}
        checked = MODULE.check_spans(spans, {1: [0, 0, 300, 400]}, 0.5)
        self.assertEqual(len(checked["glyphs"]["violations"]), 2)
        self.assertEqual(len(checked["glyphs"]["extraction_hints"]), 1)
        self.assertFalse(checked["glyphs"]["passed"])

    def test_latex_log_problems_fail(self):
        log = self.root / "main.log"
        log.write_text("Missing character: There is no X in font Y!\n"
                       "LaTeX Warning: Reference `x' on page 1 undefined.\n"
                       "Overfull \\hbox (3.0pt too wide) in paragraph\n", encoding="utf-8")
        result = MODULE.audit(self.pdf, self.plan, log_path=log)
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["checks"]["latex_log"]["diagnostics"]), 3)

    def test_cli_report_and_nonzero_exit(self):
        plan = self.root / "plan.json"
        report = self.root / "report.json"
        self.plan["expected_physical_pages"] = 9
        plan.write_text(json.dumps(self.plan), encoding="utf-8")
        completed = subprocess.run([sys.executable, str(SCRIPT), str(self.pdf), "--plan", str(plan),
                                    "--output", str(report)], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertFalse(json.loads(report.read_text(encoding="utf-8"))["passed"])

    def test_cli_rejects_overwriting_input(self):
        plan = self.root / "plan.json"
        plan.write_text(json.dumps(self.plan), encoding="utf-8")
        before = self.pdf.read_bytes()
        completed = subprocess.run([sys.executable, str(SCRIPT), str(self.pdf), "--plan", str(plan),
                                    "--output", str(self.pdf)], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(before, self.pdf.read_bytes())


if __name__ == "__main__":
    unittest.main()
