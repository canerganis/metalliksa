"""R-ISO: structural isolation of the P8 research route (integration contract 2026-10-15, 1.2, 1.4, 3.3, 10.3).

R-ISO-1 AST import guard over python/**/*.py: importers of lpbf_research_* are only research modules and
test_lpbf_research_* files; research modules never reference calculate_meltpool_physics; no research file is in
IMPLEMENTATION_SOURCE_FILES; every research test class runs with calculate_meltpool_physics patched to raise.
R-ISO-3 lane configuration in a subprocess with METALLIX_IPC_AFFINITY=0 and unset: research always has its own lane,
which is never prestarted. The former R-ISO-2 diff guard is the branch-scoped phase G tool
python/tools/p8_isolation_diff_check.py, not a permanent test.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lpbf_simulation  # noqa: E402
from test_lpbf_research_harness import ResearchTestCase  # noqa: E402

HERE = Path(__file__).resolve().parent
RESEARCH_PREFIX = "lpbf_research_"
RESEARCH_TEST_PREFIX = "test_lpbf_research_"
FORBIDDEN_NAME = "calculate_meltpool_physics"


def _python_files():
    return sorted(p for p in HERE.rglob("*.py") if "__pycache__" not in p.parts)


def _imported_modules(tree: ast.AST) -> list:
    """Static imports plus __import__/importlib.import_module calls with a literal module name."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
            found.extend(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
            if name in ("__import__", "import_module"):
                found.append(node.args[0].value)
    return found


def _is_research_module(module: str) -> bool:
    return any(part.startswith(RESEARCH_PREFIX) for part in module.split("."))


class ImportGuard(ResearchTestCase):  # R-ISO-1
    def test_only_research_modules_and_research_tests_import_research_code(self):
        offenders = []
        scanned = 0
        for path in _python_files():
            scanned += 1
            name = path.name
            if name.startswith(RESEARCH_PREFIX) or name.startswith(RESEARCH_TEST_PREFIX):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for module in _imported_modules(tree):
                if _is_research_module(module):
                    offenders.append((str(path.relative_to(HERE)), module))
        self.assertGreater(scanned, 100)  # the scan saw the real tree
        self.assertEqual(offenders, [])

    def test_research_modules_never_reference_the_served_solver_entry(self):
        research = sorted(HERE.glob(f"{RESEARCH_PREFIX}*.py"))
        self.assertIn("lpbf_research_models.py", [p.name for p in research])
        offenders = []
        for path in research:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == FORBIDDEN_NAME \
                        or isinstance(node, ast.Attribute) and node.attr == FORBIDDEN_NAME \
                        or isinstance(node, ast.alias) and FORBIDDEN_NAME in (node.name, node.asname):
                    offenders.append((path.name, getattr(node, "lineno", None)))
        self.assertEqual(offenders, [])

    def test_no_research_file_is_in_the_frozen_manifest(self):
        for name in lpbf_simulation.IMPLEMENTATION_SOURCE_FILES:
            self.assertFalse(Path(name).name.startswith(RESEARCH_PREFIX), name)
        self.assertEqual(len(lpbf_simulation.IMPLEMENTATION_SOURCE_FILES), 36)

    def test_guard_detects_a_planted_import(self):
        tree = ast.parse("import lpbf_research_cache\nfrom lpbf_research_models import run\n"
                         "x = __import__('lpbf_research_context')\nimport importlib\n"
                         "importlib.import_module('lpbf_research_codes')\n")
        found = [m for m in _imported_modules(tree) if _is_research_module(m)]
        self.assertEqual(sorted(set(m.split(".")[0] for m in found)),
                         ["lpbf_research_cache", "lpbf_research_codes", "lpbf_research_context", "lpbf_research_models"])

    def test_every_research_test_class_runs_with_the_served_solver_refused(self):
        """Minor note 10: a transitive call (for example lpbf_calibration_layer._default_solver) must fail."""
        missing = []
        for path in sorted(HERE.glob(f"{RESEARCH_TEST_PREFIX}*.py")):
            if path.name == "test_lpbf_research_harness.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    bases = [b.id if isinstance(b, ast.Name) else getattr(b, "attr", "") for b in node.bases]
                    if "ResearchTestCase" not in bases:
                        missing.append((path.name, node.name))
        self.assertEqual(missing, [])

    def test_the_patch_reaches_a_transitive_served_call(self):
        import lpbf_calibration_layer
        with self.assertRaises(AssertionError):
            lpbf_calibration_layer._default_solver()("Ti-6Al-4V", 200.0, 800.0, 80.0, 20.0)


_LANE_PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import persistent_ipc_service as ipc
reg = ipc.ConcurrentModuleRegistry.__new__(ipc.ConcurrentModuleRegistry)
reg.script_dir = ipc.SCRIPT_DIR
started = []
reg._affinity_lane = lambda name: type("L", (), {"prestart": lambda self: started.append(name)})()
reg.start_affinity_pools()
import os
print(json.dumps({
    "isolated": sorted(ipc.ISOLATED_SCRIPT_NAMES),
    "affinity": sorted(ipc.AFFINITY_SCRIPT_NAMES),
    "allowed": "lpbf_research_models" in ipc.ALLOWED_SCRIPT_NAMES,
    "routed": reg._affinity_name(os.path.join(ipc.SCRIPT_DIR, "lpbf_research_models.py")),
    "prestarted": sorted(started),
}))
"""


class LaneConfiguration(ResearchTestCase):  # R-ISO-3
    def _probe(self, affinity):
        env = {k: v for k, v in os.environ.items() if k != "METALLIX_IPC_AFFINITY"}
        if affinity is not None:
            env["METALLIX_IPC_AFFINITY"] = affinity
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run([sys.executable, "-B", "-c", _LANE_PROBE, str(HERE)], capture_output=True, text=True,
                              env=env, timeout=180)
        self.assertEqual(proc.returncode, 0, proc.stderr[-800:])
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def test_research_has_its_own_lane_with_affinity_unset(self):
        out = self._probe(None)
        self.assertEqual(out["isolated"], ["lpbf_research_models"])
        self.assertEqual(out["affinity"], ["calphad_solver", "lpbf_research_models"])
        self.assertTrue(out["allowed"])
        self.assertEqual(out["routed"], "lpbf_research_models")
        self.assertEqual(out["prestarted"], ["calphad_solver"])  # the research lane is never prestarted

    def test_research_is_still_isolated_with_affinity_off(self):
        out = self._probe("0")
        self.assertEqual(out["affinity"], ["lpbf_research_models"])  # calphad goes to the shared pool
        self.assertEqual(out["routed"], "lpbf_research_models")
        self.assertEqual(out["prestarted"], [])


if __name__ == "__main__":
    unittest.main()
