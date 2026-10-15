"""Phase 6a tranche 2b structural migration: kinetics, fatigue, phase9.

- outputs equal the pre-migration code, compared in-process against the base blob
  (git show 7f3f803:...) with key ORDER included (json.dumps without sort_keys),
  for every alloy / base metal, not only the five golden cases per solver;
- an unknown kinetics/fatigue alloy is a ValidationError exactly where the old code
  silently substituted AISI 4140 / Ti-6Al-4V;
- kinetics stdout envelope + exit 2, also through persistent_ipc_service;
- source guard against re-introduced constant literals / silent table fallbacks.
"""

import ast
import json
import os
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import alloy_registry as reg
import input_validation as iv
import kinetics_ttt_cct_solver as kin
import lpbf_fatigue_fracture as ff
import physical_constants as pc
from phase6a_test_support import require_git_revision

sys.path.insert(0, str(Path(__file__).parent / "tools"))  # drift_report

HERE = Path(__file__).parent
BASE = "7f3f803"
MIGRATED = ("kinetics_ttt_cct_solver.py", "lpbf_fatigue_fracture.py")


def _base_module(name):
    """Execute the pre-migration blob of python/<name>.py as a throwaway module."""
    try:
        src = subprocess.run(["git", "-C", str(HERE), "show", f"{BASE}:python/{name}.py"],
                             capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    module = types.ModuleType(f"_t2b_base_{name}")
    sys.modules[module.__name__] = module
    try:
        exec(compile(src, f"{name}.py@{BASE}", "exec"), module.__dict__)
    finally:
        sys.modules.pop(module.__name__, None)
    return module


def _strip(doc):
    if isinstance(doc, dict):
        return {k: _strip(v) for k, v in doc.items() if k != "computeTimeMs"}
    if isinstance(doc, list):
        return [_strip(v) for v in doc]
    return doc


def _run(script, payload):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run([sys.executable, "-B", script], input=json.dumps(payload).encode(),
                          capture_output=True, cwd=str(HERE), env=env, timeout=300)
    return proc.returncode, json.loads(proc.stdout.decode("utf-8"))


OLD_KIN = _base_module("kinetics_ttt_cct_solver")
OLD_FF = _base_module("lpbf_fatigue_fracture")


@require_git_revision(OLD_KIN is not None, f"git revision {BASE} unavailable")
class KineticsTest(unittest.TestCase):
    LEGACY = ("AISI 4140", "AISI 4340", "AISI D2", "Inconel 718", "Ti-6Al-4V", "Al 7075")

    ARGS = ((), (0.3, 40.0, 900.0, 4.0, 650.0), (2000.0,))

    SOLVER = "kinetics_ttt_cct_solver"

    @staticmethod
    def _order_preserved(old, new):
        """Every dict of ``old`` keeps its key order inside ``new`` (documented additions may interleave)."""
        if isinstance(old, dict) and isinstance(new, dict):
            if [k for k in new if k in old] != list(old):
                return False
            return all(KineticsTest._order_preserved(v, new[k]) for k, v in old.items())
        if isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
            return all(KineticsTest._order_preserved(a, b) for a, b in zip(old, new))
        return True

    def _undocumented_rows(self, new, old, new_r_gas=None):
        """Drift rows (old blob -> new) that are NOT a documented change, after verifying the documented ones.

        Documented changes: predictedHardness_HV -> ASTM E140 (golden.documented_change_violation) and the
        fx-kinetics / SOL-K changes (steel-only model, registry placeholders, TTT floor flags, LSW rows unavailable
        for every alloy; kinetics_documented_changes.row_violation). Each documented row is checked exactly against ``new``;
        the rows returned are the rest, for the caller to bound or to require empty.
        """
        import capture_phase6a_golden as golden
        import drift_report
        import kinetics_documented_changes as kdc
        self.assertEqual(kdc.document_violations(new, new_r_gas), [])
        self.assertTrue(self._order_preserved(old, new), "key order of the old document is not preserved")
        undocumented = []
        for row in drift_report.diff(old, new):
            if golden._KINETICS_HV_ROW.fullmatch(row["key"]):
                problem = golden.documented_change_violation(self.SOLVER, row, new)
            elif kdc.is_documented_row(row["key"], row["kind"]):
                problem = kdc.row_violation(row, new, new_r_gas)
            else:
                undocumented.append(row)
                continue
            self.assertIsNone(problem)
        return undocumented

    def test_every_alloy_equals_the_base_blob_with_the_legacy_r_including_key_order(self):
        # Design step (b) changed only R (8.314 -> exact). With R_GAS put back to 8.314 the migrated
        # solver must reproduce the base blob bit for bit, key order included, apart from the documented
        # changes (HV -> E140, fx-kinetics steel-only/placeholder/TTT-floor, SOL-K LSW unavailable; each checked
        # exactly in _undocumented_rows).
        import drift_report
        with mock.patch.object(kin, "R_GAS", 8.314):
            for name in self.LEGACY:
                for extra in self.ARGS:
                    args = (name,) + extra
                    with self.subTest(args=args):
                        new = _strip(kin.solve_phase_transformation_kinetics(*args))
                        old = _strip(OLD_KIN.solve_phase_transformation_kinetics(*args))
                        rest = self._undocumented_rows(new, old, new_r_gas=8.314)
                        self.assertEqual(rest, [], drift_report.render(name, rest, 10))

    def test_exact_r_drift_is_numeric_and_bounded(self):
        import drift_report
        self.assertEqual(kin.R_GAS, pc.GAS_CONSTANT_R.value)
        for name in self.LEGACY:
            for extra in self.ARGS:
                args = (name,) + extra
                with self.subTest(args=args):
                    new = _strip(kin.solve_phase_transformation_kinetics(*args))
                    old = _strip(OLD_KIN.solve_phase_transformation_kinetics(*args))
                    rows = self._undocumented_rows(new, old)
                    self.assertTrue(all(r["kind"] == "numeric" for r in rows), drift_report.render(name, rows, 10))
                    # Last printed digit of rounded Arrhenius outputs (largest seen: 6.7e-3,
                    # AISI 4340 tStart_s 0.0149 -> 0.0148); unrounded change ~ (Q/RT)*5.6e-5.
                    self.assertLessEqual(max([abs(r["rel"]) for r in rows if r["rel"] is not None] or [0.0]), 1e-2)

    def test_unknown_alloy_raises_instead_of_aisi4140(self):
        for name in ("Unobtainium XYZ", "", None, 4140, "4140", "Inconel"):
            with self.subTest(name=name):
                with self.assertRaises(iv.ValidationError) as ctx:
                    kin.solve_phase_transformation_kinetics(name)
                self.assertEqual(ctx.exception.code, iv.UNKNOWN_ALLOY)
                self.assertEqual(ctx.exception.field, "alloy")
        # Old behaviour for the record: a silent AISI 4140 solve.
        old = OLD_KIN.solve_phase_transformation_kinetics("Unobtainium XYZ")
        self.assertEqual(old["alloyMetadata"]["Ae3_C"], 780.0)

    def test_registry_alloy_without_kinetics_data_is_refused(self):
        with self.assertRaises(iv.ValidationError) as ctx:
            kin.solve_phase_transformation_kinetics("316L SS")
        self.assertEqual(ctx.exception.detail["reason"], "no-domain-data")

    def test_aliases_resolve_to_their_own_alloy(self):
        # Behaviour change: before, "IN718" silently got AISI 4140 data.
        res = kin.solve_phase_transformation_kinetics("IN718")
        self.assertEqual(res["alloy"], "IN718")
        self.assertEqual(res["alloyMetadata"]["Ae3_C"], 1020.0)
        ref = kin.solve_phase_transformation_kinetics("Inconel 718")
        self.assertEqual(json.dumps(_strip({**res, "alloy": None})), json.dumps(_strip({**ref, "alloy": None})))

    def test_build_job_names_still_resolve(self):
        # lpbf_build_job_solver.py:641 maps alloy ids to these names in-process.
        for name in ("Inconel 718", "Ti-6Al-4V", "AISI 4140"):
            self.assertTrue(kin.solve_phase_transformation_kinetics(name, 1e5)["success"])

    def test_envelope_internal_error_and_provenance(self):
        code, out = _run("kinetics_ttt_cct_solver.py", {"alloy": "Unobtainium"})
        self.assertEqual(code, 2)
        self.assertEqual(set(out), {"success", "error", "errorKind"})
        self.assertEqual(out["errorKind"], "validation")
        self.assertEqual(out["error"]["code"], "UNKNOWN_ALLOY")
        # SOL-K: an aging temperature that is not a number is a validation envelope with the reason code (was an
        # internal error, exit 1); NaN and absolute zero are refused the same way
        for aging in (None, float("nan"), -273.15):
            code, out = _run("kinetics_ttt_cct_solver.py", {"alloy": "Inconel 718", "agingTemp_C": aging})
            self.assertEqual((code, out["errorKind"]), (2, "validation"), aging)
            self.assertEqual((out["error"]["field"], out["error"]["detail"]["reasonCode"]),
                             ("agingTemp_C", "nonphysical-input"))
        # the internal-error envelope itself is unchanged: a payload that is not an object
        code, out = _run("kinetics_ttt_cct_solver.py", [])
        self.assertEqual(code, 1)
        self.assertEqual(out["errorKind"], "internal")
        # kin-li fix round: a non-number cooling rate is a validation envelope for every alloy (was internal)
        code, out = _run("kinetics_ttt_cct_solver.py", {"alloy": "Inconel 718", "coolingRate_C_s": "fast"})
        self.assertEqual((code, out["errorKind"], out["error"]["code"]), (2, "validation", "NON_FINITE"))
        # lane kin-li: the Li-model steels validate the cooling rate (NOT_A_NUMBER envelope, exit 2)
        code, out = _run("kinetics_ttt_cct_solver.py", {"alloy": "AISI 4140", "coolingRate_C_s": "fast"})
        self.assertEqual((code, out["errorKind"], out["error"]["field"]), (2, "validation", "coolingRate_C_s"))
        code, out = _run("kinetics_ttt_cct_solver.py", {"alloy": "AISI 4340"})
        self.assertEqual(code, 0)
        prov = out["provenance"]
        self.assertEqual(prov["registryAlloyId"], "aisi4340")
        self.assertEqual(prov["registryVersion"], reg.REGISTRY_VERSION)
        self.assertEqual(prov["constantsVersion"], pc.CONSTANTS_VERSION)
        self.assertEqual(prov["gasConstantR_J_molK"], pc.GAS_CONSTANT_R.value)  # design step (b)


@require_git_revision(OLD_FF is not None, f"git revision {BASE} unavailable")
class FatigueTest(unittest.TestCase):
    def test_database_view_equals_the_old_table(self):
        self.assertEqual(list(ff.ALLOY_FATIGUE_DATABASE), list(OLD_FF.ALLOY_FATIGUE_DATABASE))
        for name, old in OLD_FF.ALLOY_FATIGUE_DATABASE.items():
            self.assertEqual(repr(vars(ff.ALLOY_FATIGUE_DATABASE[name])), repr(vars(old)), name)

    def test_engine_outputs_equal_the_base_blob_except_the_documented_ks2_ks3_fixes(self):
        # Physics audit KS-2 / KS-3 changed the El-Haddad branch and the Paris integration on purpose.
        # The Murakami branch is unchanged; the old a0 is the Y = 1 formula; the new outputs must pass
        # the independent oracle (tools/fatigue_documented_changes, d33b6f5 table snapshot).
        import fatigue_documented_changes as fdc  # noqa: E402 (python/tools module)
        for name in OLD_FF.ALLOY_FATIGUE_DATABASE:
            new, old = ff.MurakamiFatigueEngine(name), OLD_FF.MurakamiFatigueEngine(name)
            for d, loc, r, amp in ((33.0, "surface", 0.1, 250.0), (60.0, "internal", -1.0, 250.0),
                                   (80.0, "sub-surface", -0.5, 400.0)):
                with self.subTest(alloy=name, location=loc, R=r):
                    n, o = new.calculate_fatigue_limit(d, loc, r), old.calculate_fatigue_limit(d, loc, r)
                    self.assertEqual(n["murakami_raw_MPa"], o["murakami_raw_MPa"])
                    self.assertEqual(o["el_haddad_a0_um"], fdc.old_a0_um(vars(old.alloy)))
                    doc = {"fatigue_limit": n,
                           "kitagawa_takahashi_curve": new.generate_kitagawa_takahashi_curve(loc, r, n_points=30),
                           "paris_crack_growth": new.simulate_paris_crack_growth(d, amp, r, location=loc)}
                    payload = {"alloyName": name, "sqrtArea_um": d, "location": loc, "stressRatio_R": r,
                               "stressAmplitude_MPa": amp}
                    self.assertEqual(fdc.document_problems(doc, payload), [])

    def test_unknown_alloy_raises_instead_of_ti64(self):
        for name in ("X", "Unobtanium-X", "AISI 4140", None):
            with self.subTest(name=name):
                with self.assertRaises(iv.ValidationError) as ctx:
                    ff.MurakamiFatigueEngine(name)
                self.assertEqual(ctx.exception.code, iv.UNKNOWN_ALLOY)
                self.assertEqual(ctx.exception.field, "alloyName")
        self.assertEqual(OLD_FF.MurakamiFatigueEngine("X").alloy.name, "Ti-6Al-4V")

    def test_custom_alloy_needs_no_known_name(self):
        custom = ff.AlloyFatigueConstants("custom", 300.0, 400.0, 3.0, 50.0, 1e-11, 3.0)
        self.assertIs(ff.MurakamiFatigueEngine("anything", custom_alloy=custom).alloy, custom)

    def test_alias_resolves_to_own_constants(self):
        # Behaviour change: before, "IN718" silently got the Ti-6Al-4V constants.
        self.assertEqual(ff.MurakamiFatigueEngine("IN718").alloy.name, "Inconel 718")


class PersistentIpcRelayTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        ipc = sys.modules.get("persistent_ipc_service")
        if ipc is not None:
            ipc.registry.shutdown()

    def test_kinetics_envelope_relayed(self):
        import persistent_ipc_service as ipc
        res = ipc._worker_run_script(str(HERE / "kinetics_ttt_cct_solver.py"),
                                     json.dumps({"alloy": "Unobtainium"}), [])
        self.assertEqual(res["exitCode"], 2, res.get("stderr"))
        out = json.loads(res["stdout"])
        self.assertEqual(out["errorKind"], "validation")
        self.assertEqual(out["error"]["code"], "UNKNOWN_ALLOY")
        # The ProcessPoolExecutor path submits this same _worker_run_script; it is
        # exercised by the removed tafel migration test (the module-global pool is shut down by
        # that test's tearDownClass, so it is not re-used here).


class SourceGuardTest(unittest.TestCase):
    FORBIDDEN_FLOATS = (8.314, 8.3145, 8.31446, 8.314462618, 96485.33212, 96485.33, 96485.0, 273.15,
                        265000.0)

    def test_no_constant_literals(self):
        for name in MIGRATED:
            tree = ast.parse((HERE / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, float):
                    self.assertNotIn(node.value, self.FORBIDDEN_FLOATS, f"{name}:{node.lineno}")

    def test_no_silent_table_fallback(self):
        for name in MIGRATED:
            src = (HERE / name).read_text(encoding="utf-8")
            self.assertNotIn("ALLOY_KINETICS_DB.get(", src)
            self.assertNotIn("ALLOY_FATIGUE_DATABASE.get(", src)
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "get" and len(node.args) == 2
                        and isinstance(node.args[1], ast.Subscript)):
                    self.fail(f"{name}:{node.lineno} uses .get(key, TABLE[...])")

    # test_phase9_mapping_moved left with python/phase9_surrogate.py (deleted 2026-10-04 with
    # industrial-certification); the mapping itself stays covered by test_alloy_data_kinetics_uq_fatigue.


if __name__ == "__main__":
    unittest.main()
