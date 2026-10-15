"""R-ID: the P8 research pin (integration contract 2026-10-15, 3.6 "Research pin", 10.3).

R-ID-1: python/lpbf_research_identity.expected equals researchImplementationSha256 of the research runtime files. A
research code change regenerates the pin deliberately (python -B lpbf_research_identity_pin.py --write).
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lpbf_research_cache as research_cache  # noqa: E402
from lpbf_research_identity_pin import read_pinned_research_identity  # noqa: E402
from lpbf_simulation import IMPLEMENTATION_SOURCE_FILES  # noqa: E402
from lpbf_source_identity import fingerprint_sources  # noqa: E402
from test_lpbf_research_harness import ResearchTestCase  # noqa: E402

HERE = Path(__file__).resolve().parent


class ResearchPin(ResearchTestCase):
    def test_pin_equals_the_research_implementation_hash(self):  # R-ID-1
        self.assertEqual(research_cache.research_implementation_sha256(), read_pinned_research_identity(),
                         "research code changed: regenerate with python -B lpbf_research_identity_pin.py --write")

    def test_the_import_time_identity_is_the_pinned_one(self):
        self.assertEqual(research_cache.IDENTITY.research_sha256, read_pinned_research_identity())

    def test_pinned_files_are_the_research_runtime_modules_only(self):
        files = research_cache.RESEARCH_SOURCE_FILES
        self.assertEqual(len(files), len(set(files)))
        for name in files:
            self.assertTrue(name.startswith("lpbf_research_") and name.endswith(".py"), name)
            self.assertTrue((HERE / name).is_file(), name)
            self.assertNotIn(name, IMPLEMENTATION_SOURCE_FILES)
        self.assertNotIn("lpbf_research_identity_pin.py", files)  # tooling, not runtime
        self.assertIn("lpbf_research_models.py", files)

    def test_reader_is_strict(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        good = "a" * 64
        for content, ok in ((good + "\n", True), (good + "\r\n", True), (good, False), (good.upper() + "\n", False),
                            (good + "\n\n", False), ("a" * 63 + "\n", False), (" " + good + "\n", False)):
            path = tmp / "pin.expected"
            path.write_bytes(content.encode("ascii"))
            if ok:
                self.assertEqual(read_pinned_research_identity(path), good)
            else:
                with self.assertRaises(ValueError):
                    read_pinned_research_identity(path)

    def test_a_byte_change_moves_the_hash_and_a_newline_change_does_not(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for name in research_cache.RESEARCH_SOURCE_FILES:
            shutil.copyfile(HERE / name, tmp / name)
        base = fingerprint_sources(tmp, research_cache.RESEARCH_SOURCE_FILES, research_cache.RESEARCH_VERSION)
        self.assertEqual(base, research_cache.research_implementation_sha256())
        target = tmp / "lpbf_research_codes.py"
        text = target.read_bytes().replace(b"\r\n", b"\n")
        target.write_bytes(text.replace(b"\n", b"\r\n"))
        self.assertEqual(fingerprint_sources(tmp, research_cache.RESEARCH_SOURCE_FILES,
                                             research_cache.RESEARCH_VERSION), base)
        target.write_bytes(text + b"# edit\n")
        self.assertNotEqual(fingerprint_sources(tmp, research_cache.RESEARCH_SOURCE_FILES,
                                                research_cache.RESEARCH_VERSION), base)


if __name__ == "__main__":
    unittest.main()
