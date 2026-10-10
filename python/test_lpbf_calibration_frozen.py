"""Frozen-physics guards of the calibration work: the implementation fingerprint does not move, no frozen file imports
the calibration modules, no frozen file is in the diff against an explicitly named base, and the default thermal-solver
response is unchanged. SCREENING ONLY, NOT VALIDATION."""

import ast
import hashlib
import json
import os
import platform
import subprocess
import sys
import unittest
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parent
REPO_ROOT = PYTHON_DIR.parent
sys.path.insert(0, str(PYTHON_DIR))

import lpbf_simulation  # noqa: E402

FORBIDDEN_IMPORT_PREFIXES = ("lpbf_calibration", "lpbf_calibrated_meltpool", "calibration_synth_support", "lpbf_error_bands")
# Explicit base: the frozen files are compared against the merge-base of HEAD with this ref, never against an implicit
# HEAD^. A calibration branch must not change frozen files relative to where it branched off main. Candidates are tried
# in order: an explicit override, then the PR base on CI, then local main, then origin/main. No hardcoded feature branch:
# a stale local integration branch would compare against an old commit and flag changes that are not the branch's own.
BASE_REF_CANDIDATES = [r for r in (
    os.environ.get("LPBF_FROZEN_BASE_REF"),
    f"origin/{os.environ['GITHUB_BASE_REF']}" if os.environ.get("GITHUB_BASE_REF") else None,
    "main",
    "origin/main",
) if r]
BASE_REF = BASE_REF_CANDIDATES[0]
# sha256 of the canonical thermal-solver JSON (computeTimeMs removed) for one fixed input per kernel, recorded on the
# reference machine (Windows, CPU flat-plate path) at base c406b4a9 before any calibration code existed; re-pinned at the
# keyhole-regime bump (only label/basis text keys changed: keyholePorosityRisk text, regimeBasis, regimeMaterialNote,
# depthBenchmarkNote); re-pinned at the la6-gusarov bump (only text keys changed: geometricDefectScreen.modelId v2 and
# the balling screen sources/basis in geometricDefectScreen and defectDiagnostics); re-pinned again after the exported
# provenance title fix (only the defectDiagnostics provenance title text changed); re-pinned at the in625-regime bump
# (316L input: only the regimeBasis text and the new regimeKeyholeThreshold key changed, in both blocks; undoing them
# reproduces the previous digests).
HTTP_GOLDEN = {
    "eagar-tsai": "8d4c51c1b905db43cc1422b713960649b982934a5a111bf4c217ba1111b746a0",
    "goldak": "f64e8c67c5dbd5a989cb69d9aee33c16f5f55a57f8143d3b49a1ec246506bae6",
    "rosenthal": "170f9d4a3b7f144fc1f3606b1235f54f1733f4cfc019a9f03463b063640ed011",
}
HTTP_INPUT = {"material": "316L Stainless Steel", "laserPower_W": 200, "scanSpeed_mm_s": 900, "beamDiameter_um": 80,
              "preheatTemp_C": 20, "layerThickness_um": 30, "hatchSpacing_um": 100}


def _git(*args):
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60)


class FrozenGuards(unittest.TestCase):
    def test_fingerprint_equals_the_pin(self):  # T-FRZ-1
        expected = (PYTHON_DIR / "lpbf_implementation_fingerprint.expected").read_text(encoding="utf-8").strip()
        self.assertEqual(lpbf_simulation.implementation_fingerprint(), expected)

    def test_no_frozen_file_imports_the_calibration_modules(self):  # T-FRZ-2
        offenders = []
        for name in lpbf_simulation.IMPLEMENTATION_SOURCE_FILES:
            path = PYTHON_DIR / name
            if path.suffix != ".py" or not path.is_file():
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
                for m in mods:
                    if m.split(".")[-1].startswith(FORBIDDEN_IMPORT_PREFIXES) or m.startswith(FORBIDDEN_IMPORT_PREFIXES):
                        offenders.append((name, m))
        self.assertEqual(offenders, [])

    def test_calibration_modules_are_not_in_the_frozen_manifest(self):
        for name in lpbf_simulation.IMPLEMENTATION_SOURCE_FILES:
            self.assertFalse(Path(name).name.startswith(FORBIDDEN_IMPORT_PREFIXES), name)

    def test_diff_against_the_named_base_has_no_frozen_file(self):  # T-FRZ-3
        base = None
        for ref in BASE_REF_CANDIDATES:
            base = _git("merge-base", "HEAD", ref)
            if base.returncode == 0:
                break
        if base is None or base.returncode != 0:
            if os.environ.get("CI"):
                # No named base exists in this checkout (e.g. only origin/main): the content pin is the guard, asserted
                # explicitly here instead of skipping, so a missing base can never turn the guard into a no-op.
                expected = (PYTHON_DIR / "lpbf_implementation_fingerprint.expected").read_text(encoding="utf-8").strip()
                self.assertEqual(lpbf_simulation.implementation_fingerprint(), expected)
                return
            self.skipTest(f"no base ref of {BASE_REF_CANDIDATES} resolvable here")
        sha = base.stdout.strip()
        changed = set(_git("diff", "--name-only", sha, "HEAD").stdout.split())
        frozen = {f"python/{n}" for n in lpbf_simulation.IMPLEMENTATION_SOURCE_FILES}
        self.assertEqual(sorted(changed & frozen), [], f"frozen files changed since merge-base {sha[:12]} with {ref}")
        # the route that serves the default thermal-solver response is untouched as well
        old = _git("show", f"{sha}:routes/physics.ts").stdout
        new = (REPO_ROOT / "routes" / "physics.ts").read_text(encoding="utf-8")
        route = 'physicsRouter.post("/api/python/lpbf-thermal-solver"'
        norm = lambda t: t.replace("\r\n", "\n")  # noqa: E731
        block = lambda t: norm(t)[norm(t).index(route):norm(t).index(route) + 150]  # noqa: E731
        self.assertEqual(block(old), block(new))


class DefaultResponseUnchanged(unittest.TestCase):
    @unittest.skipUnless(platform.system() == "Windows",
                         "reference-machine golden (like the parity goldens); other platforms rely on the frozen-file diff guard")
    def test_default_thermal_solver_response_is_byte_identical(self):  # T-HTTP-1
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for kernel, want in HTTP_GOLDEN.items():
            proc = subprocess.run([sys.executable, "-B", str(PYTHON_DIR / "lpbf_thermal_solver.py")],
                                  input=json.dumps({**HTTP_INPUT, "heatSource": kernel}), capture_output=True, text=True,
                                  env=env, timeout=300)
            self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
            data = json.loads(proc.stdout)
            data.pop("computeTimeMs", None)
            got = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            self.assertEqual(got, want, kernel)


if __name__ == "__main__":
    unittest.main()
