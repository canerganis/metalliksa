"""Portable source extraction guards; no external PDFs needed for these tests."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "thermal_source_check", Path(__file__).with_name("engine_est_thermal_check.py"))
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)

RAW = """Latent heat of melting 2.86×105
Vaporization point 3560 2792 3122
Latent heat of vaporization
Lv (J/kg)
9.255×106
1.053×107
6.336×106
Minimal absorptivity 0.26 0.01 0.33
Molar mass 48 27 56
"""


class VaporizationColumns(unittest.TestCase):
    def test_only_three_vaporization_values_with_exponents(self):
        self.assertEqual(checker.vaporization_latents(RAW), [9255000., 10530000., 6336000.])

    def test_whitespace_between_base_and_exponent(self):
        self.assertEqual(checker.vaporization_latents(RAW.replace("×106", "×10\n6")),
                         [9255000., 10530000., 6336000.])

    def test_missing_extra_or_unreadable_column_fails(self):
        for raw in (RAW.replace("6.336×106\n", ""),
                    RAW.replace("Minimal absorptivity", "1.0×106\nMinimal absorptivity"),
                    RAW.replace("9.255×106", "9.255×10?"),
                    RAW.replace("Minimal absorptivity", "Unknown row")):
            with self.subTest(raw=raw), self.assertRaises(AssertionError):
                checker.vaporization_latents(raw)


class ExtractionGuards(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        (root / "papers").mkdir()
        self.path = root / "papers/source.pdf"
        self.path.write_bytes(b"source fixture")
        for target, value in (("ROOT", root), ("SOURCES", {
                "source.pdf": hashlib.sha256(self.path.read_bytes()).hexdigest()})):
            mock = patch.object(checker, target, value)
            mock.start()
            self.addCleanup(mock.stop)

    def test_poppler_compatible_layout_default(self):
        def extract(args, **kwargs):
            if "-table" in args:
                raise subprocess.CalledProcessError(99, args)
            self.assertIn("-layout", args)
            return subprocess.CompletedProcess(args, 0, stdout=b"physical rows")
        with patch.object(checker.shutil, "which", return_value="pdftotext"), \
                patch.object(checker.subprocess, "run", side_effect=extract):
            self.assertEqual(checker.source_text("source.pdf", 20), "physical rows")

    def test_missing_or_changed_source_never_extracts(self):
        with patch.object(checker.subprocess, "run") as run:
            self.path.write_bytes(b"changed source")
            with self.assertRaises(AssertionError):
                checker.source_text("source.pdf", 20)
            self.path.unlink()
            with self.assertRaises(AssertionError):
                checker.source_text("source.pdf", 20)
            run.assert_not_called()

    def test_missing_executable_fails(self):
        with patch.object(checker.shutil, "which", return_value=None), \
                self.assertRaisesRegex(AssertionError, "pdftotext"):
            checker.source_text("source.pdf", 20)

    def test_extraction_failure_is_not_a_pass(self):
        with patch.object(checker.shutil, "which", return_value="pdftotext"), \
                patch.object(checker.subprocess, "run", side_effect=subprocess.CalledProcessError(1, [])), \
                self.assertRaises(subprocess.CalledProcessError):
            checker.source_text("source.pdf", 20)


if __name__ == "__main__":
    unittest.main()
