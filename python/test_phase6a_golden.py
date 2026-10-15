"""Phase 6a golden regression: migrated solvers must stay bit-exact.

Every case in python/golden/phase6a/<solver>/<case>.json was captured at the
pre-migration revision (tools/capture_phase6a_golden.py). The current solver is
run exactly like the app's ad-hoc spawn path and its stdout, with only the
volatile keys stripped, must serialise to the identical canonical JSON text.

Deliberate behaviour changes (silent default -> validation error) are listed in
EXPECTED_BEHAVIOUR_CHANGES; for those cases the old golden stays on disk as the
record of the old behaviour and the test asserts the new validation envelope.
"""

import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "tools"))

import capture_phase6a_golden as golden  # noqa: E402
import drift_report  # noqa: E402
from phase6a_test_support import require_git_revision  # noqa: E402

EXPECTED_BEHAVIOUR_CHANGES: dict = {}
EXPECTED_BEHAVIOUR_CHANGES.update(golden._t2b_cases.EXPECTED_BEHAVIOUR_CHANGES)
# ---- END phase6a-t2b block ----


class GoldenFilesTest(unittest.TestCase):
    def test_every_case_has_a_golden_file(self):
        for solver, case in golden.iter_golden_cases():
            path = golden.golden_path(solver, case)
            self.assertTrue(path.is_file(), str(path))
            doc = golden.load_golden(solver, case)
            self.assertEqual(doc["schema"], golden.GOLDEN_SCHEMA)
            self.assertEqual(doc["solver"], solver)
            self.assertEqual(doc["case"], case)
            self.assertEqual(doc["baseRevision"], golden.BASE_REVISION)
            self.assertEqual(golden.canonical(doc["input"]), golden.canonical(golden.CASES[solver][case]))
            # N2: the stored input is exactly the key-sorted payload (same text, same
            # order), so the regression re-run sends what the sorted payload says.
            self.assertEqual(json.dumps(doc["input"], ensure_ascii=False),
                             json.dumps(golden.CASES[solver][case], sort_keys=True, ensure_ascii=False),
                             f"{solver}/{case}")

    def test_case_counts(self):
        for solver, cases in golden.CASES.items():
            self.assertGreaterEqual(len(cases), 3, solver)
            self.assertLessEqual(len(cases), 5, solver)

    def test_golden_files_hold_no_volatile_keys(self):
        for solver, case in golden.iter_golden_cases():
            text = golden.golden_path(solver, case).read_text(encoding="utf-8")
            stdout = json.dumps(golden.load_golden(solver, case)["stdout"])
            for key in golden.VOLATILE_KEYS:
                self.assertNotIn(f'"{key}"', stdout, f"{solver}/{case}: {key}")
            self.assertTrue(text.endswith("\n"))


class GoldenRegressionTest(unittest.TestCase):
    maxDiff = None

    def _check(self, solver: str, case: str):
        doc = golden.load_golden(solver, case)
        # Design step (b): a re-blessed expectation (step_b/<case>.json) replaces the
        # d33b6f5 golden for the comparison; StepBGoldenTest checks its recorded drift.
        expected = golden.load_expected(solver, case)
        # Run the CASES payload, not doc["input"]: golden files store the input with
        # sorted keys, and key order can be significant for some solvers.
        # GoldenFilesTest asserts both are canonically equal.
        fresh = golden.run_solver(solver, golden.CASES[solver][case])
        expected_code = EXPECTED_BEHAVIOUR_CHANGES.get((solver, case))
        if expected_code is not None:
            self.assertEqual(fresh["exitCode"], 2, fresh["stderr"])
            out = fresh["stdout"]
            self.assertIs(out.get("success"), False)
            self.assertEqual(out.get("errorKind"), "validation")
            self.assertEqual(out["error"]["code"], expected_code)
            self.assertTrue(out["error"]["field"])
            self.assertTrue(out["error"]["message"])
            self.assertIsInstance(out["error"]["detail"], dict)
            self.assertEqual(set(out), {"success", "error", "errorKind"})
            # The old golden is still the pre-migration record of the silent default.
            self.assertEqual(doc["exitCode"], 0)
            # (the fatigue driver output has no "success" key; it must not be an error)
            self.assertIsNot(doc["stdout"].get("success"), False)
            self.assertNotIn("error", doc["stdout"])
            return
        self.assertEqual(fresh["exitCode"], expected["exitCode"], fresh["stderr"])
        rows = drift_report.diff(expected["stdout"], fresh["stdout"])
        self.assertEqual(rows, [], drift_report.render(f"{solver}/{case}", rows, 20))
        self.assertEqual(golden.canonical(fresh["stdout"]), golden.canonical(expected["stdout"]))

def _git_available() -> bool:
    try:
        golden.solver_bytes("calphad_solver", golden.BASE_REVISION)
        return True
    except Exception:
        return False


@require_git_revision(_git_available(), f"git or revision {golden.BASE_REVISION} unavailable")
class GoldenBindingTest(unittest.TestCase):
    """Golden files are bound to the immutable solver blobs they were captured from."""

    def _blob_sha(self, solver):
        return golden.normalised_sha256(golden.solver_bytes(solver, golden.BASE_REVISION))

    def test_every_golden_records_the_base_blob_sha256(self):
        for solver, case in golden.iter_golden_cases():
            doc = golden.load_golden(solver, case)
            self.assertEqual(doc["solverSha256"], self._blob_sha(solver), f"{solver}/{case}")
            self.assertEqual(doc["solverFile"], f"python/{solver}.py")
            self.assertIn(doc["solverSource"], {f"git:{golden.BASE_REVISION}", "worktree"})
        for solver in golden._TABLE_TARGETS:
            path = golden.GOLDEN_DIR / solver / golden.SOURCE_TABLES_FILE
            doc = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(doc["solverSha256"], self._blob_sha(solver), solver)

    def test_normalised_sha256_ignores_only_crlf(self):
        self.assertEqual(golden.normalised_sha256(b"a\r\nb\n"), golden.normalised_sha256(b"a\nb\n"))
        self.assertNotEqual(golden.normalised_sha256(b"a\nb\n"), golden.normalised_sha256(b"a\nc\n"))

    def _in_temp_golden_dir(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        original = golden.GOLDEN_DIR
        golden.GOLDEN_DIR = Path(tmp.name)
        self.addCleanup(setattr, golden, "GOLDEN_DIR", original)
        return Path(tmp.name)

    def test_force_capture_of_changed_solver_is_refused(self):
        # The migrated working-tree solvers differ from the d33b6f5 blobs.
        tmp = self._in_temp_golden_dir()
        for solver in golden.CASES:
            self.assertNotEqual(golden.normalised_sha256(golden.solver_bytes(solver)), self._blob_sha(solver))
            case = next(iter(golden.CASES[solver]))
            with self.assertRaises(golden.CaptureRefused):
                golden.capture(solver, case, force=True)
        with self.assertRaises(golden.CaptureRefused):
            golden.capture_source_tables(force=True)
        self.assertEqual(list(tmp.rglob("*.json")), [])

    def test_capture_from_base_blob_reproduces_committed_golden(self):
        committed = {(s, c): golden.load_golden(s, c) for s, c in golden.iter_golden_cases()}
        tmp = self._in_temp_golden_dir()
        for solver, case in golden.iter_golden_cases():
            golden.capture(solver, case, force=True, from_revision=golden.BASE_REVISION)
            fresh = json.loads((tmp / solver / f"{case}.json").read_text(encoding="utf-8"))
            old = committed[(solver, case)]
            self.assertEqual(fresh["exitCode"], old["exitCode"], f"{solver}/{case}")
            self.assertEqual(golden.canonical(fresh["stdout"]), golden.canonical(old["stdout"]), f"{solver}/{case}")
            self.assertEqual(fresh["solverSha256"], old["solverSha256"])
        golden.capture_source_tables(force=True, from_revision=golden.BASE_REVISION)
        for solver in golden._TABLE_TARGETS:
            fresh = json.loads((tmp / solver / golden.SOURCE_TABLES_FILE).read_text(encoding="utf-8"))
            old = json.loads((HERE / "golden" / "phase6a" / solver / golden.SOURCE_TABLES_FILE).read_text(encoding="utf-8"))
            self.assertEqual(golden.canonical(fresh["values"]), golden.canonical(old["values"]), solver)

    def test_calphad_goldens_record_the_no_pycalphad_branch_that_capture_reproduces(self):
        # Root cause of the former failure of the base-blob re-capture on an interpreter with
        # pycalphad installed: the d33b6f5 calphad_solver blob imports pycalphad when it can and
        # then takes the "pycalphad-open-tdb" path, while every calphad golden was captured
        # without pycalphad. capture() therefore hides GOLDEN_HIDDEN_MODULES in blob runs.
        self.assertEqual(golden.GOLDEN_HIDDEN_MODULES, ("pycalphad",))
        calphad_cases = []
        for solver, case in golden.iter_golden_cases():
            if solver != "calphad_solver":
                continue
            calphad_cases.append(case)
            stdout = golden.load_golden(solver, case)["stdout"]
            self.assertIn("pycalphadVersion", stdout, case)
            self.assertEqual(stdout["pycalphadVersion"], "No module named 'pycalphad'", case)
            self.assertEqual(stdout["engine"], "subregular-adaptive-minimizer", case)
        self.assertTrue(calphad_cases, "no calphad_solver golden cases were found")

    def test_hidden_modules_raise_the_not_installed_error_in_blob_runs_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "calphad_solver.py"
            script.write_text(
                "import json, sys\n"
                "out = {}\n"
                "for name in ('pycalphad', 'pycalphad.variables', 'json'):\n"
                "    try:\n"
                "        __import__(name)\n"
                "        out[name] = 'imported'\n"
                "    except ModuleNotFoundError as exc:\n"
                "        out[name] = [type(exc).__name__, str(exc), exc.name]\n"
                "print(json.dumps(out))\n", encoding="utf-8")
            hidden = golden.run_solver("calphad_solver", {}, script=script, hide_modules=("pycalphad",))
            self.assertEqual(hidden["exitCode"], 0, hidden["stderr"])
            self.assertEqual(hidden["stdout"], {
                "pycalphad": ["ModuleNotFoundError", "No module named 'pycalphad'", "pycalphad"],
                "pycalphad.variables": ["ModuleNotFoundError", "No module named 'pycalphad'", "pycalphad"],
                "json": "imported"})
            plain = golden.run_solver("calphad_solver", {}, script=script)
            self.assertEqual(plain["exitCode"], 0, plain["stderr"])
            self.assertEqual(plain["stdout"]["json"], "imported")
        with self.assertRaises(ValueError):
            golden.run_solver("calphad_solver", {}, hide_modules=("pycalphad",))

    def test_from_revision_other_than_base_is_refused(self):
        self._in_temp_golden_dir()
        with self.assertRaises(golden.CaptureRefused):
            golden.capture("calphad_solver", "in718_wt_pct", force=True, from_revision="HEAD")


class StepBGoldenTest(unittest.TestCase):
    """Re-blessed expectations of design step (b) carry their full drift against d33b6f5."""

    def _step_b_files(self):
        return sorted(golden.GOLDEN_DIR.glob(f"*/{golden.STEP_B_DIR}/*.json"))

    def test_every_step_b_file_belongs_to_a_known_case(self):
        for path in self._step_b_files():
            solver, case = path.parent.parent.name, path.stem
            with self.subTest(file=f"{solver}/{case}"):
                self.assertIn(solver, golden.CASES)
                self.assertIn(case, golden.CASES[solver])
                # A behaviour change (validation envelope or success-flag flip) is never a re-bless.
                self.assertNotIn((solver, case), EXPECTED_BEHAVIOUR_CHANGES)
                self.assertNotIn((solver, case), golden._t2a_cases.EXPECTED_BEHAVIOUR_CHANGES)
                self.assertNotIn((solver, case), golden._t2a_cases.EXPECTED_SUCCESS_FLAG_CHANGES)
                self.assertNotIn((solver, case), golden._t2a_cases.EXPECTED_UNAVAILABLE_CHANGES)
                self.assertNotIn((solver, case), golden.step_b_excluded_cases())

    def test_excluded_cases_cover_every_behaviour_change(self):
        excluded = golden.step_b_excluded_cases()
        for key in (set(EXPECTED_BEHAVIOUR_CHANGES) | set(golden._t2a_cases.EXPECTED_BEHAVIOUR_CHANGES)
                    | set(golden._t2a_cases.EXPECTED_SUCCESS_FLAG_CHANGES)
                    | set(golden._t2a_cases.EXPECTED_UNAVAILABLE_CHANGES)):
            self.assertIn(key, excluded)

    def test_recorded_drift_is_a_bounded_value_change(self):
        # Fix round item 7: numeric rows only (changed strings only under pythonCode),
        # |rel| <= 1e-2, tafel <= 3 * |EW rel| + 1e-2 (see step_b_max_rel).
        for path in self._step_b_files():
            solver, case = path.parent.parent.name, path.stem
            with self.subTest(file=f"{solver}/{case}"):
                doc = json.loads(path.read_text(encoding="utf-8"))
                base = golden.load_golden(solver, case)["stdout"]
                self.assertEqual(golden.step_b_violations(solver, doc["driftVsBase"], doc["stdout"],
                                                          golden.CASES[solver][case], base), [])
                self.assertEqual(golden.step_b_document_violations(solver, doc["stdout"]), [])

    def test_guard_rejects_structural_and_large_drift(self):
        num = lambda key, rel: {"key": key, "kind": "numeric", "old": 1.0, "new": 1.0 + rel, "abs": rel, "rel": rel}
        self.assertEqual(golden.step_b_violations("kinetics_ttt_cct_solver", [num("x", 0.009)]), [])
        self.assertTrue(golden.step_b_violations("kinetics_ttt_cct_solver", [num("x", 0.02)]))

    def test_documented_hardness_change_is_checked_exactly(self):
        # EXPECTED_DOCUMENTED_VALUE_CHANGES: kinetics predictedHardness_HV -> ASTM E140 Table 1.
        solver = "kinetics_ttt_cct_solver"
        key = "cctContinuousCoolingMap[0].predictedHardness_HV"
        skey = key + "_status"

        def doc(alloy_type, hrc, status):
            return {"alloyMetadata": {"type": alloy_type},
                    "cctContinuousCoolingMap": [{"predictedHardness_HRC": hrc, "predictedHardness_HV_status": status}]}

        def hv_row(old, new):
            kind = "numeric" if new is not None else "changed"
            row = {"key": key, "kind": kind, "old": old, "new": new}
            if kind == "numeric":
                row.update(abs=new - old, rel=(new - old) / old)
            return row

        conv, rng, cls = ("converted-astm-e140-table1", "unavailable-outside-e140-table1-hrc-20-68",
                          "unavailable-no-verified-table-for-alloy-class")
        steel = lambda hrc, status: doc("Low-Alloy Steel", hrc, status)
        add = lambda status: {"key": skey, "kind": "added", "old": None, "new": status}
        # accepted: steel 42 HRC 481 -> 412 (|rel| 0.14), steel 18 HRC 229 -> null, Ti 64 HRC 712 -> null
        self.assertEqual(golden.step_b_violations(solver, [hv_row(481.0, 412.0), add(conv)], steel(42.0, conv)), [])
        self.assertEqual(golden.step_b_violations(solver, [hv_row(229.0, None), add(rng)], steel(18.0, rng)), [])
        self.assertEqual(golden.step_b_violations(
            solver, [hv_row(712.0, None), add(cls)], doc("Alpha-Beta Titanium Alloy", 64.0, cls)), [])
        # rejected: no document, wrong new value, int instead of float, wrong old value,
        # non-steel given a number, wrong status, status changed instead of added
        self.assertTrue(golden.step_b_violations(solver, [hv_row(481.0, 412.0)]))
        self.assertTrue(golden.step_b_violations(solver, [hv_row(481.0, 413.0)], steel(42.0, conv)))
        self.assertTrue(golden.step_b_violations(solver, [hv_row(481.0, 412)], steel(42.0, conv)))
        self.assertTrue(golden.step_b_violations(solver, [hv_row(480.0, 412.0)], steel(42.0, conv)))
        self.assertTrue(golden.step_b_violations(
            solver, [hv_row(712.0, 800.0)], doc("Precipitation-Hardenable Ni-Fe Superalloy", 64.0, conv)))
        self.assertTrue(golden.step_b_violations(solver, [add(rng)], steel(42.0, conv)))
        self.assertTrue(golden.step_b_violations(
            solver, [{"key": skey, "kind": "changed", "old": "x", "new": conv}], steel(42.0, conv)))
        # the exception is per solver and per key: same key elsewhere, or a null HRC, stays structural
        self.assertTrue(golden.step_b_violations(solver, [{"key": "cctContinuousCoolingMap[0].predictedHardness_HRC",
                                                           "kind": "changed", "old": 18.0, "new": None}],
                                                 steel(18.0, rng)))
        big = {"key": "x", "kind": "numeric", "old": 1.0, "new": 1.02, "abs": 0.02, "rel": 0.02}
        self.assertTrue(golden.step_b_violations(solver, [big], steel(42.0, conv)))

    def _kinetics_step_b(self, case):
        path = golden.step_b_path("kinetics_ttt_cct_solver", case)
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc["driftVsBase"], doc["stdout"]

    def test_kinetics_documented_changes_are_checked_against_the_document(self):
        # Lanes fx-kinetics + kin-li + SOL-K (tools/kinetics_documented_changes.py): every documented row must equal
        # the re-blessed document at its key (an LSW row: the old value is the old formula's, the new value is null),
        # and the whole document must equal the independent expectation (Li oracle for AISI 4140/4340, exact
        # unavailable blocks for the others, LSW rows unavailable for every alloy).
        import copy
        solver = "kinetics_ttt_cct_solver"
        for case in ("aisi4140_ui_defaults", "aisi4340_slow_cool", "in718_lpbf_quench", "ti64_beta_quench"):
            rows, new = self._kinetics_step_b(case)
            self.assertEqual(golden.step_b_violations(solver, rows, new), [], case)
            self.assertEqual(golden.step_b_document_violations(solver, new), [], case)

        def violations(case, mutate_rows=None, mutate_doc=None):
            rows, new = self._kinetics_step_b(case)
            rows, new = copy.deepcopy(rows), copy.deepcopy(new)
            if mutate_rows:
                mutate_rows(rows)
            if mutate_doc:
                mutate_doc(new)
            return golden.step_b_violations(solver, rows, new) + golden.step_b_document_violations(solver, new)

        def row(rows, key):
            return next(r for r in rows if r["key"] == key)

        def doc_set(path, value):
            def mutate(doc):
                node = doc
                for part in path[:-1]:
                    node = node[part]
                node[path[-1]] = value
            return mutate

        # a row whose value is not the document's value
        self.assertTrue(violations("aisi4140_ui_defaults", mutate_rows=lambda rows: row(
            rows, "cctContinuousCoolingMap[4].transformedStartTemp_C").update(new=448.0)))
        self.assertTrue(violations("in718_lpbf_quench", mutate_rows=lambda rows: row(
            rows, "cctContinuousCoolingMap[0].transformedStart_status").update(new="available")))
        # non-steel: the steel-only claim must hold in the document
        self.assertTrue(violations("in718_lpbf_quench", mutate_doc=doc_set(["kineticsModel", "status"], "available")))
        self.assertTrue(violations("in718_lpbf_quench", mutate_doc=doc_set(["alloyMetadata", "type"], "Low-Alloy Steel")))
        # placeholders: only keys flagged in alloy_registry.KINETICS_PLACEHOLDERS may be null
        self.assertTrue(violations("ti64_beta_quench", mutate_rows=lambda rows: rows.append(
            {"key": "alloyMetadata.Ms_C", "kind": "changed", "old": 800.0, "new": None})))
        # LSW (SOL-K): the recorded old value must equal the old formula, the new value must be null
        key = "lswPrecipitateCoarsening[9].meanRadius_nm"
        hard = "lswPrecipitateCoarsening[9].precipitationHardening_MPa"
        mech = "lswPrecipitateCoarsening[9].strengtheningMechanism"
        self.assertTrue(violations("aisi4140_ui_defaults", mutate_rows=lambda rows: row(rows, key).update(new=22.9)))
        self.assertTrue(violations("aisi4140_ui_defaults", mutate_rows=lambda rows: row(rows, key).update(old=1.6)))
        self.assertTrue(violations("aisi4140_ui_defaults", mutate_rows=lambda rows: row(rows, hard).update(old=117.0)))
        self.assertTrue(violations("aisi4140_ui_defaults", mutate_rows=lambda rows: row(rows, mech).update(
            old="Orowan Dislocation Looping (Over-aged)")))  # the d33b6f5 radius 1.52 nm is the cutting regime
        self.assertTrue(violations("aisi4140_ui_defaults", mutate_rows=lambda rows: row(rows, key).update(
            kind="numeric", new=22.9, abs=21.38, rel=14.07)))  # a value change is not a documented removal
        self.assertTrue(violations("aisi4140_ui_defaults", mutate_doc=doc_set(
            ["lswPrecipitateCoarsening", 0, "meanRadius_nm"], 1.5)))
        # the new LSW status and reason-code rows are accepted only with the document's own values
        status_key = "lswPrecipitateCoarsening[3].status"
        self.assertTrue(violations("aisi4140_ui_defaults", mutate_rows=lambda rows: row(rows, status_key).update(
            new="generic-constants-illustrative")))
        self.assertTrue(violations("aisi4140_ui_defaults", mutate_rows=lambda rows: row(
            rows, "lswPrecipitateCoarsening[3].reasonCodes[0]").update(new="missing-source-constant")))
        # an undocumented section stays under the default guard (alloyMetadata composition, inputParameters)
        self.assertTrue(golden.step_b_violations(solver, [{"key": "inputParameters.agingTime_h", "kind": "changed",
                                                           "old": 8.0, "new": "8"}],
                                                 self._kinetics_step_b("aisi4140_ui_defaults")[1]))
        # without the re-blessed document nothing of this is accepted
        self.assertTrue(golden.step_b_violations(solver, self._kinetics_step_b("in718_lpbf_quench")[0]))

    def test_kinetics_document_checks_reject_model_mutants(self):
        # A value that equals the base golden produces no drift row, so the whole-document checks must catch it.
        import copy
        solver = "kinetics_ttt_cct_solver"
        docs = {c: self._kinetics_step_b(c)[1] for c in ("aisi4140_ui_defaults", "aisi4340_slow_cool",
                                                           "in718_lpbf_quench", "ti64_beta_quench")}

        def rejected(case, mutate):
            doc = copy.deepcopy(docs[case])
            mutate(doc)
            self.assertTrue(golden.step_b_document_violations(solver, doc), case)

        for case, doc in docs.items():
            self.assertEqual(golden.step_b_document_violations(solver, doc), [], case)

        # Li model numbers: TTT time, curve dropped, critical temperatures, CCT start, CCR, verdict
        rejected("aisi4140_ui_defaults", lambda d: d["tttIsothermalCurves"][10].update(
            tStart_s=d["tttIsothermalCurves"][10]["tStart_s"] * 1.001))
        rejected("aisi4140_ui_defaults", lambda d: d["tttIsothermalCurves"].pop())
        rejected("aisi4140_ui_defaults", lambda d: d["tttIsothermalCurves"][0].update(floorHit=True))
        rejected("aisi4140_ui_defaults", lambda d: d["criticalTransformationTemperatures"].update(Bs_C=545.0))
        rejected("aisi4140_ui_defaults", lambda d: d["criticalTransformationTemperatures"].update(Ms_C=330.0))
        rejected("aisi4140_ui_defaults", lambda d: d["criticalTransformationTemperatures"].update(Mf_C=180.0))
        rejected("aisi4140_ui_defaults", lambda d: d["criticalTransformationTemperatures"].update(
            CriticalCoolingRate_CCR_C_s=45.0))
        rejected("aisi4140_ui_defaults", lambda d: d["cctContinuousCoolingMap"][2].update(transformedStartTemp_C=615.0))
        rejected("aisi4140_ui_defaults", lambda d: d["cctContinuousCoolingMap"][3]["phaseStartTemps_C"].update(
            Ferrite=600.0))
        rejected("aisi4140_ui_defaults", lambda d: d["cctContinuousCoolingMap"][9].update(
            primaryMicrostructure="Bainite", transformedStart_status="li1998-additivity-first-diffusional-start"))
        rejected("aisi4140_ui_defaults", lambda d: d["cctContinuousCoolingMap"][0]["phaseFractions"].update(
            Martensite_pct=0.0))
        rejected("aisi4140_ui_defaults", lambda d: d["cctContinuousCoolingMap"][7].update(predictedHardness_HRC=58.0))
        rejected("aisi4140_ui_defaults", lambda d: d["calphadVsKineticsGap"]["kineticRealityAtSelectedCooling"].update(
            verdict="Mixed Microstructure (Martensite + Bainite)"))
        rejected("aisi4340_slow_cool", lambda d: d["calphadVsKineticsGap"]["kineticRealityAtSelectedCooling"].update(
            predictedMartensite_pct=96.5))
        # labels and the model block
        rejected("aisi4140_ui_defaults", lambda d: d["kineticsModel"].update(validationStatus="validated"))
        rejected("aisi4140_ui_defaults", lambda d: d["kineticsModel"].update(evidenceLevel="validated"))
        rejected("aisi4140_ui_defaults", lambda d: d["kineticsModel"].update(modelVersion="li1998-additivity-v2"))
        rejected("aisi4140_ui_defaults", lambda d: d["kineticsModel"]["validityDomain"].update(status="outside"))
        rejected("aisi4140_ui_defaults", lambda d: d["kineticsModel"]["li1998"].update(fractionsComputed=True))
        rejected("aisi4140_ui_defaults", lambda d: d["kineticsModel"]["li1998"].update(astmGrainSize_G=8.0))
        rejected("aisi4140_ui_defaults", lambda d: d["kineticsModel"].update(status="unavailable"))
        rejected("aisi4140_ui_defaults", lambda d: d["tttIncubationFloor"].update(note="x"))
        rejected("aisi4140_ui_defaults", lambda d: d.update(engine="MetalliX-Python-HPC-JMAK-Kinetics-v3.10"))
        rejected("aisi4140_ui_defaults", lambda d: d["inputParameters"].update(priorGrainSize_um=30.0))
        # placeholders / non-steel registry echoes
        rejected("in718_lpbf_quench", lambda d: d["alloyMetadata"].update(Ms_C=-50.0))
        rejected("in718_lpbf_quench", lambda d: d["criticalTransformationTemperatures"].update(Ms_C=-50.0))
        rejected("in718_lpbf_quench", lambda d: d["criticalTransformationTemperatures"].update(CriticalCoolingRate_CCR_C_s=150.0))
        rejected("in718_lpbf_quench", lambda d: d["alloyMetadata"].update(critical_cooling_rate_C_s=150.0))
        rejected("ti64_beta_quench", lambda d: d["criticalTransformationTemperatures"].update(Ae1_C=700.0))
        rejected("ti64_beta_quench", lambda d: d["alloyMetadata"].update(Ms_C=None))  # unflagged: must stay a number
        rejected("in718_lpbf_quench", lambda d: d["kineticsModel"].update(illustrativeOnly=False))
        rejected("in718_lpbf_quench", lambda d: d["kineticsModel"].update(li1998={}))
        rejected("ti64_beta_quench", lambda d: d["calphadVsKineticsGap"]["equilibriumPrediction"].update(
            stablePhasesAtRT="Ferrite + Cementite / Equilibrium intermetallics"))
        rejected("ti64_beta_quench", lambda d: d.update(tttIsothermalCurves=[]))
        # LSW (SOL-K): unavailable for every alloy, exact status and reason codes; an aging temperature that would put
        # the rows above the registry solvus changes the expected status; nonphysical aging inputs never appear
        for case in ("aisi4140_ui_defaults", "in718_lpbf_quench", "ti64_beta_quench"):
            rejected(case, lambda d: d["lswPrecipitateCoarsening"][0].update(meanRadius_nm=5.03))
            rejected(case, lambda d: d["lswPrecipitateCoarsening"][4].update(precipitationHardening_MPa=209.3))
            rejected(case, lambda d: d["lswPrecipitateCoarsening"][1].update(
                strengtheningMechanism="Weak-Pair / Strong-Pair Cutting"))
            rejected(case, lambda d: d["lswPrecipitateCoarsening"][2].update(status="generic-constants-illustrative"))
            rejected(case, lambda d: d["lswPrecipitateCoarsening"][2].update(
                reasonCodes=["missing-source-bound-model"]))
            rejected(case, lambda d: d["lswPrecipitateCoarsening"][5].pop("reasonCodes"))
            rejected(case, lambda d: d["lswPrecipitateCoarsening"].pop())
            rejected(case, lambda d: d["kineticsModel"]["lswPrecipitateCoarsening"].update(note="x"))
            rejected(case, lambda d: d["kineticsModel"]["lswPrecipitateCoarsening"].update(
                reasonCodes=["missing-source-constant"]))
            rejected(case, lambda d: d["kineticsModel"]["lswPrecipitateCoarsening"].update(
                status="unavailable-aging-temperature-at-or-above-solvus"))
            rejected(case, lambda d: d["inputParameters"].update(agingTemp_C=-273.15))
            rejected(case, lambda d: d["inputParameters"].update(agingTemp_C=float("nan")))
            rejected(case, lambda d: d["inputParameters"].update(agingTime_h=-1.0))
        rejected("in718_lpbf_quench", lambda d: d["inputParameters"].update(agingTemp_C=1100.0))

        # HV rows of a row whose HRC is now null: the old value must be the old formula of an old HRC band
        steel_doc, in718_doc = docs["aisi4140_ui_defaults"], docs["in718_lpbf_quench"]
        hv = lambda old: {"key": "cctContinuousCoolingMap[0].predictedHardness_HV", "kind": "changed", "old": old, "new": None}
        for doc in (steel_doc, in718_doc):
            self.assertEqual(golden.step_b_violations(solver, [hv(229.0)], doc), [])
            self.assertTrue(golden.step_b_violations(solver, [hv(500.0)], doc))
        status = {"key": "cctContinuousCoolingMap[0].predictedHardness_HV_status", "kind": "added", "old": None,
                  "new": "unavailable-no-predicted-hrc"}
        self.assertEqual(golden.step_b_violations(solver, [status], steel_doc), [])
        self.assertTrue(golden.step_b_violations(solver, [status], in718_doc))
        # a handler that cannot verify (bad index) is a violation, never "accepted"
        bad_index = {"key": "tttIsothermalCurves[999].tStart_s", "kind": "added", "old": None, "new": 1.0}
        self.assertTrue(golden.step_b_violations(solver, [bad_index], steel_doc))

    def test_recorded_solver_sha256_is_the_current_solver(self):
        # A solver edit after a re-bless must come with a new re-bless (and drift table).
        for path in self._step_b_files():
            solver = path.parent.parent.name
            with self.subTest(file=str(path.relative_to(golden.GOLDEN_DIR))):
                doc = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(doc["solverSha256"], golden.normalised_sha256(golden.solver_bytes(solver)))

    def test_step_b_metadata_and_recorded_drift(self):
        for path in self._step_b_files():
            solver, case = path.parent.parent.name, path.stem
            with self.subTest(file=f"{solver}/{case}"):
                doc = json.loads(path.read_text(encoding="utf-8"))
                base = golden.load_golden(solver, case)
                self.assertEqual(doc["schema"], golden.STEP_B_SCHEMA)
                self.assertEqual(doc["label"], golden.STEP_B_LABEL)
                self.assertEqual((doc["solver"], doc["case"]), (solver, case))
                self.assertEqual(doc["solverFile"], f"python/{solver}.py")
                self.assertEqual(len(doc["solverSha256"]), 64)
                self.assertEqual(golden.canonical(doc["input"]), golden.canonical(golden.CASES[solver][case]))
                self.assertEqual(doc["exitCode"], base["exitCode"])
                rows = drift_report.diff(base["stdout"], doc["stdout"])
                # A re-bless exists only for a real drift, and the recorded table is complete.
                self.assertTrue(rows)
                self.assertEqual(golden.canonical(doc["driftVsBase"]), golden.canonical(rows))
                self.assertTrue(text_ends_with_newline(path))

    def test_load_expected_prefers_step_b(self):
        for path in self._step_b_files():
            solver, case = path.parent.parent.name, path.stem
            self.assertEqual(golden.load_expected(solver, case)["label"], golden.STEP_B_LABEL)

    def test_bless_dry_run_reports_no_drift_for_the_committed_state(self):
        import bless_step_b
        before = sorted(p.as_posix() for p in golden.GOLDEN_DIR.rglob("*.json"))
        drift, log = bless_step_b.bless("kinetics_ttt_cct_solver", dry_run=True)
        self.assertEqual([rows for _, rows in drift if rows], [])
        self.assertTrue(any("behaviour change" in line for line in log))
        self.assertEqual(sorted(p.as_posix() for p in golden.GOLDEN_DIR.rglob("*.json")), before)


def text_ends_with_newline(path: Path) -> bool:
    return path.read_text(encoding="utf-8").endswith("\n")


class ProvenanceTest(unittest.TestCase):
    """Provenance is stripped from the bit-exact comparison, so pin it here."""

    def _fresh(self, solver, case):
        return golden.run_solver(solver, golden.CASES[solver][case])

    def test_validation_envelope_has_no_provenance(self):
        for solver, case in EXPECTED_BEHAVIOUR_CHANGES:
            self.assertIsNone(self._fresh(solver, case)["provenance"])


class DriftReportTest(unittest.TestCase):
    def test_identical_documents_have_no_rows(self):
        doc = {"a": 1.5, "b": [1, {"c": "x"}], "d": None}
        self.assertEqual(drift_report.diff(doc, json.loads(json.dumps(doc))), [])

    def test_numeric_row_has_abs_and_rel(self):
        rows = drift_report.diff({"x": {"y": 2.0}}, {"x": {"y": 2.5}})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], "x.y")
        self.assertEqual(rows[0]["kind"], "numeric")
        self.assertEqual(rows[0]["abs"], 0.5)
        self.assertEqual(rows[0]["rel"], 0.25)

    def test_type_change_is_detected_even_when_equal(self):
        rows = drift_report.diff({"x": 1}, {"x": 1.0})
        self.assertEqual(len(rows), 1)

    def test_added_removed_changed(self):
        rows = {r["key"]: r["kind"] for r in drift_report.diff(
            {"a": 1, "b": "s", "l": [1, 2]}, {"b": "t", "c": 3, "l": [1]})}
        self.assertEqual(rows, {"a": "removed", "b": "changed", "c": "added", "l[1]": "removed"})

    def test_empty_containers_are_kept(self):
        rows = {r["key"]: r["kind"] for r in drift_report.diff({"a": {}, "b": []}, {"c": {}})}
        self.assertEqual(rows, {"a": "removed", "b": "removed", "c": "added"})
        self.assertEqual(drift_report.diff({"a": {}}, {"a": {}}), [])
        rows = drift_report.diff({"a": {}}, {"a": {"x": 1}})
        self.assertEqual({r["key"] for r in rows}, {"a", "a.x"})

    def test_zero_old_value_has_no_relative_delta(self):
        rows = drift_report.diff({"x": 0.0}, {"x": 1e-9})
        self.assertIsNone(rows[0]["rel"])

    def test_strip_volatile_is_recursive(self):
        doc = {"durationMs": 1, "a": {"timestamp": "t", "b": [{"computeTimeMs": 2, "c": 3}]},
               "pythonVersion": "3.12"}
        self.assertEqual(golden.strip_volatile(doc), {"a": {"b": [{"c": 3}]}})


if __name__ == "__main__":
    unittest.main()
