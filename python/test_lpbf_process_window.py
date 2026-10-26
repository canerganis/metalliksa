#!/usr/bin/env python3
"""Self-contained tests for python/lpbf_process_window.py (screening-only process-window map)."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lpbf_process_window as pw  # noqa: E402
import lpbf_process_window_cache as pwc  # noqa: E402
from four_alloy_materials import LITERATURE_PV_WINDOWS  # noqa: E402

REPO_ROOT = HERE.parent
NIST_JSON = REPO_ROOT / "data" / "benchmark" / "nist-amb2022-03-optical" / "table4-aggregate-v2.json"


def request(alloy="in718", **extra):
    base = {"alloyId": alloy, "beamDiameter_um": 80, "layer_um": 40, "hatch_um": 110, "preheatTemp_C": 80}
    base.update(extra)
    return base


SMALL = {"powers": [150, 250, 350], "speeds": [500, 800, 1100]}


class ProcessWindowTests(unittest.TestCase):
    def setUp(self):
        pwc.clear_results()

    @classmethod
    def setUpClass(cls):
        pwc.clear()
        cls.default = pw.run_process_window(request("in718", beamDiameter_um=67))

    def test_default_grid_shape_and_range_from_literature_box(self):
        r = self.default
        self.assertTrue(r["success"], r)
        box = LITERATURE_PV_WINDOWS["in718"]
        grid = r["grid"]
        self.assertEqual((grid["nP"], grid["nV"], grid["nCells"]), (11, 11, 121))
        self.assertEqual(len(r["cells"]), 121)
        self.assertAlmostEqual(grid["powers_W"][0], 0.5 * box["powerMin_W"], places=6)
        self.assertAlmostEqual(grid["powers_W"][-1], 1.5 * box["powerMax_W"], places=6)
        self.assertAlmostEqual(grid["speeds_mm_s"][0], 0.5 * box["speedMin_mm_s"], places=6)
        self.assertAlmostEqual(grid["speeds_mm_s"][-1], 1.5 * box["speedMax_mm_s"], places=6)
        self.assertEqual(grid["rangeBasis"]["power"]["basis"], "default")
        self.assertEqual(grid["rangeBasis"]["speed"]["basis"], "default")
        self.assertEqual(grid["literatureBox"], box)
        self.assertEqual(sum(r["counts"].values()), 121)
        for verdict, n in r["counts"].items():
            self.assertEqual(n, sum(1 for c in r["cells"] if c["verdict"] == verdict))

    def test_cells_equal_direct_compose_verdict(self):
        import lpbf_build_job_solver as bj
        import lpbf_thermal_solver as ts
        r = pw.run_process_window(request("ss316l", **SMALL))
        self.assertTrue(r["success"], r)
        by_pv = {(c["power_W"], c["speed_mm_s"]): c for c in r["cells"]}
        for p, v in ((150, 500), (250, 800), (350, 1100)):
            th = ts.calculate_meltpool_physics(
                material_name="ss316l", laser_power_W=float(p), scan_speed_mm_s=float(v), beam_diameter_um=80.0,
                preheat_temp_C=80.0, layer_thickness_um=40.0, hatch_spacing_um=110.0, laser_wavelength="IR_1064nm")
            vd = bj.compose_verdict(th, "ss316l")
            c = by_pv[(p, v)]
            self.assertEqual(c["verdict"], vd["verdict"])
            self.assertEqual(c["headline"], vd["headline"])
            self.assertEqual(c["dominantGate"], vd["dominantGate"])
            self.assertEqual(c["blockingGates"], vd["blockingGates"])
            self.assertEqual(c["riskGates"], vd["riskGates"])
            self.assertEqual(c["unavailableGates"], vd["unavailableGates"])
            self.assertEqual(c["reasons"], vd["reasons"])  # verbatim
            self.assertEqual(c["extentStatus"], vd["extentStatus"])
            self.assertEqual(c["insideLiteratureBox"], vd["literatureWindow"]["inside"])
            self.assertEqual(c["normalizedEnthalpy"], th["processParameters"]["normalizedEnthalpy"])
            # hoisted grid advisories are removed from the cell list, everything else stays
            hoisted = {a["gate"] for a in r["gridAdvisories"]}
            self.assertEqual(c["advisoryGates"], [g for g in vd["advisoryGates"] if g not in hoisted])

    def test_width_depth_null_unless_extent_computed(self):
        # Own grid: 10 W cells have no resolvable liquidus extent (after P1, 2026-10-11, the latent-free Rosenthal
        # field resolves every cell of the default in718 grid, which this test used before).
        r = pw.run_process_window(request("in718", powers=[10, 150, 300], speeds=[500, 1500, 3000]))
        non_computed = [c for c in r["cells"] if c["extentStatus"] != "computed"]
        computed = [c for c in r["cells"] if c["extentStatus"] == "computed"]
        self.assertTrue(non_computed, "the 10 W cells are expected to be unresolved-geometry cells")
        self.assertTrue(computed)
        for c in non_computed:
            self.assertIsNone(c["width_um"])
            self.assertIsNone(c["depth_um"])
            self.assertEqual(c["verdict"], "inconclusive")
        for c in computed:
            self.assertIsInstance(c["width_um"], float)
            self.assertIsInstance(c["depth_um"], float)

    def test_parameter_independent_advisories_listed_once(self):
        adv = self.default["gridAdvisories"]
        self.assertTrue(adv)
        from lpbf_build_job_solver import STRESS_GATES_NOT_EVALUATED_NOTE
        # P7a (2026-10-11): recoater and distortion are not evaluated in every cell (no sourced stress model).
        self.assertEqual([a["gate"] for a in adv], ["recoater", "distortion"])
        for a in adv:
            self.assertEqual(a["note"], STRESS_GATES_NOT_EVALUATED_NOTE)
            self.assertEqual(a["cells"], 121)
            self.assertTrue(all(a["gate"] not in c["advisoryGates"] for c in self.default["cells"]))
            self.assertTrue(all(a["gate"] in c["unavailableGates"] for c in self.default["cells"]))

    def test_validation_refusals(self):
        nan = float("nan")
        cases = {
            "unknown alloy": request("inconel-999", **SMALL),
            "missing alloy": {k: v for k, v in request().items() if k != "alloyId"},
            "16x16": request(powers=[100 + 10 * i for i in range(16)], speeds=[500 + 10 * i for i in range(16)]),
            "1 value": request(powers=[100], speeds=[500, 600]),
            "NaN power": request(powers=[100, nan], speeds=[500, 600]),
            "string power": request(powers=[100, "200"], speeds=[500, 600]),
            "bool power": request(powers=[100, True], speeds=[500, 600]),
            "P<=0": request(powers=[0, 200], speeds=[500, 600]),
            "negative v": request(powers=[100, 200], speeds=[-5, 600]),
            "P over cap": request(powers=[100, 1501], speeds=[500, 600]),
            "v over cap": request(powers=[100, 200], speeds=[500, 10001]),
            "min>=max": request(powers=[300, 100], speeds=[500, 600]),
            "duplicate": request(powers=[100, 100], speeds=[500, 600]),
            "preheat>=solidus": request(preheatTemp_C=1260),
            "preheat<0": request(preheatTemp_C=-1),
            "beam<=0": request(beamDiameter_um=0),
            "layer<=0": request(layer_um=-3),
            "hatch missing": {k: v for k, v in request().items() if k != "hatch_um"},
            "tolerance": request(overlayBeamTolerance_pct=150),
            "not an object": [1, 2],
        }
        for name, payload in cases.items():
            with self.subTest(name):
                out = pw.run_process_window(payload)
                self.assertFalse(out["success"])
                self.assertEqual(out["errorKind"], "validation")
                self.assertTrue(out["error"])

    def test_max_axis_is_accepted(self):
        norm, refusal = pw.validate_request(request(powers=[100 + 10 * i for i in range(15)],
                                                    speeds=[500 + 10 * i for i in range(15)]))
        self.assertIsNone(refusal)
        self.assertEqual(len(norm["powers"]) * len(norm["speeds"]), 225)

    def test_cell_exception_becomes_error_verdict(self):
        import lpbf_thermal_solver as ts
        real = ts.calculate_meltpool_physics

        def flaky(*args, **kwargs):
            if kwargs["laser_power_W"] == 250.0:
                raise RuntimeError("boom")
            return real(*args, **kwargs)

        with mock.patch.object(ts, "calculate_meltpool_physics", flaky):
            r = pw.run_process_window(request("ss316l", powers=[150, 250], speeds=[500, 800]))
        self.assertTrue(r["success"])
        errors = [c for c in r["cells"] if c["verdict"] == "error"]
        self.assertEqual(len(errors), 2)
        self.assertEqual(r["counts"]["error"], 2)
        for c in errors:
            self.assertEqual(c["error"], "RuntimeError: boom")
            self.assertIsNone(c["width_um"])
            self.assertIsNone(c["depth_um"])
            self.assertEqual(c["reasons"], [])
        self.assertNotIn("error", {c["verdict"] for c in r["cells"] if c["power_W"] == 150.0})
        self.assertFalse(r["cache"]["stored"])  # an incomplete result is never cached

    def test_cache_hit_and_miss_on_solver_revision(self):
        pwc.clear()
        payload = request("ss316l", **SMALL)
        first = pw.run_process_window(payload)
        second = pw.run_process_window(payload)
        self.assertFalse(first["cache"]["hit"])
        self.assertEqual(first["cache"]["scope"], "python-worker-process")
        self.assertEqual(second["cache"]["scope"], "python-worker-process")
        self.assertTrue(second["cache"]["hit"])
        self.assertEqual(first["cache"]["key"], second["cache"]["key"])
        self.assertEqual(first["cells"], second["cells"])
        self.assertTrue(first["cache"]["stored"])
        self.assertEqual(pwc.stats()["implementationHashComputations"], 1)
        with mock.patch.object(pw, "BUILD_JOB_SOLVER_REVISION", "patched-revision"):
            third = pw.run_process_window(payload)
        self.assertFalse(third["cache"]["hit"])
        self.assertNotEqual(third["cache"]["key"], first["cache"]["key"])
        self.assertEqual(third["provenance"]["solverRevision"], "patched-revision")
        # a different request is a different entry
        other = pw.run_process_window(request("ss316l", powers=[150, 250], speeds=[500, 800]))
        self.assertFalse(other["cache"]["hit"])

    def test_cache_is_lru_bounded_at_16(self):
        pwc.clear()
        for i in range(20):
            pwc.put(f"k{i}", {"i": i})
        self.assertEqual(pwc.stats()["entries"], 16)
        self.assertIsNone(pwc.get("k0"))
        self.assertIsNotNone(pwc.get("k19"))

    def test_failing_loader_marks_only_that_dataset_unavailable(self):
        import lpbf_public_datasets as pd
        with mock.patch.object(pd, "load_hofmann_316l", side_effect=OSError("disk gone")):
            r = pw.run_process_window(request("ss316l", powers=[150, 250], speeds=[500, 800]))
        self.assertTrue(r["success"])
        self.assertEqual(len(r["cells"]), 4)
        (ds,) = r["overlay"]["datasets"]
        self.assertEqual(ds["status"], "unavailable")
        self.assertIn("disk gone", ds["reason"])
        self.assertEqual(ds["points"], [])

    def test_alsi10mg_has_no_source(self):
        r = pw.run_process_window(request("alsi10mg", powers=[300, 350], speeds=[900, 1100]))
        self.assertTrue(r["success"])
        self.assertEqual(r["overlay"]["datasets"], [])
        self.assertTrue(r["overlay"]["note"])

    def test_lane_in625_is_never_selected_for_supported_alloys(self):
        for alloy in ("ss316l", "ti6al4v", "in718", "alsi10mg"):
            self.assertNotIn("lane-in625-2020", [s["id"] for s in pw.DATASET_REGISTRY[alloy]])

    def test_beam_tolerance_filter_and_hidden_counts(self):
        import lpbf_public_datasets as pd
        rows = pd.load_hofmann_316l()["rows"]
        matched_counts = {}
        for tol in (0.0, 40.0):
            payload = request("ss316l", beamDiameter_um=80, overlayBeamTolerance_pct=tol,
                              powers=[100, 300, 500, 800], speeds=[200, 1000, 2000, 3000])
            r = pw.run_process_window(payload)
            (ds,) = r["overlay"]["datasets"]
            lo, hi = 80 * (1 - tol / 100), 80 * (1 + tol / 100)
            matched = [x for x in rows if lo <= x["beamDiameter_um"] <= hi]
            in_range = [x for x in matched if 100 <= x["power_W"] <= 800 and 200 <= x["speed_mm_s"] <= 3000]
            self.assertEqual(ds["nRows"], len(rows))
            self.assertEqual(ds["hiddenByBeam"], len(rows) - len(matched))
            self.assertEqual(ds["hiddenOutsideRange"], len(matched) - len(in_range))
            self.assertEqual(ds["nShown"], len(in_range))
            self.assertEqual(len(ds["points"]), len(in_range))
            for pt in ds["points"]:
                self.assertTrue(lo <= pt["beamDiameter_um"] <= hi)
                self.assertIn(pt["modelVerdict"]["verdict"], (*pw.VERDICTS, "error"))
            self.assertGreater(len(matched), 0)
            matched_counts[tol] = len(matched)
        self.assertLess(matched_counts[0.0], matched_counts[40.0])  # the tolerance changes the selection

    def test_in718_overlay_contains_nist_case_0_from_the_json(self):
        doc = json.loads(NIST_JSON.read_text(encoding="utf-8"))
        case0 = next(c for c in doc["cases"] if c["caseNumber"] == "0")
        self.assertEqual((case0["laserPower_W"], case0["scanSpeed_mm_s"], case0["beamDiameterD4sigma_um"]), (285, 960, 67))
        ds = next(d for d in self.default["overlay"]["datasets"] if d["id"] == "nist-amb2022-03-table4")
        self.assertEqual(ds["status"], "available")
        pt = next(p for p in ds["points"] if p["rowId"] == "nist-amb2022-03-case-0")
        self.assertEqual((pt["power_W"], pt["speed_mm_s"], pt["beamDiameter_um"]), (285.0, 960.0, 67.0))
        self.assertEqual(pt["measuredWidth_um"], case0["widthMean_um"])
        self.assertEqual(pt["measuredDepth_um"], case0["depthMean_um"])
        self.assertEqual((pt["measuredWidth_um"], pt["measuredDepth_um"]), (136.3, 139.7))
        self.assertIn(pt["modelVerdict"]["verdict"], pw.VERDICTS)
        # the other NIST cases use a different beam and are hidden by the 10 % tolerance, and counted
        self.assertEqual(ds["nShown"] + ds["hiddenByBeam"] + ds["hiddenOutsideRange"] + ds["hiddenNoBeam"], ds["nRows"])
        self.assertGreater(ds["hiddenByBeam"], 0)

    def test_measurement_points_carry_no_print_outcome_fields(self):
        for ds in self.default["overlay"]["datasets"]:
            for pt in ds["points"]:
                self.assertNotIn("balling", pt)
        self.assertIn("not print outcomes", self.default["overlay"]["measurementKind"])

    def test_evidence_and_provenance_flags(self):
        r = self.default
        self.assertEqual(r["evidence"]["kind"], "screening-only")
        self.assertIs(r["evidence"]["experimentalValidation"], False)
        self.assertTrue(r["evidence"]["statement"])
        prov = r["provenance"]
        self.assertEqual(prov["modelId"], "rosenthal-screening-v1")
        self.assertEqual(prov["solverRevision"], pw.BUILD_JOB_SOLVER_REVISION)
        self.assertRegex(prov["implementationHash"], r"^[0-9a-f]{64}$")
        self.assertEqual(prov["absorptionModel"], "flat-plate")

    def test_response_contains_no_non_finite_numbers(self):
        json.dumps(self.default, allow_nan=False)

    def test_main_prints_exactly_one_json_document(self):
        proc = subprocess.run(
            [sys.executable, str(HERE / "lpbf_process_window.py")],
            input=json.dumps(request("ss316l", powers=[150, 250], speeds=[500, 800])),
            capture_output=True, text=True, cwd=str(HERE), timeout=180)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1, proc.stdout[:500])
        out = json.loads(lines[0])
        self.assertTrue(out["success"])
        self.assertEqual(len(out["cells"]), 4)

    def test_cache_key_depends_on_own_source_hash(self):
        norm = {"alloyId": "in718"}
        base = pwc.make_key(norm, "rev", "hash")
        with mock.patch.object(pwc, "_OWN_SOURCES_HASH", "edited-source"):
            self.assertNotEqual(base, pwc.make_key(norm, "rev", "hash"))

    def test_unknown_verdict_becomes_error_cell(self):
        with mock.patch("lpbf_build_job_solver.compose_verdict", return_value={"verdict": "brand-new"}):
            out = pw.run_process_window(request(powers=[200, 250], speeds=[800, 900]))
        self.assertTrue(out["success"])
        self.assertTrue(all(c["verdict"] == "error" for c in out["cells"]))
        self.assertEqual(out["counts"]["error"], 4)

    def test_main_unexpected_exception_prints_one_engine_json(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with mock.patch.object(pw, "run_process_window", side_effect=RuntimeError("boom")),                 mock.patch("sys.stdin", io.StringIO(json.dumps(request()))), redirect_stdout(buf):
            pw.main()
        lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1)
        out = json.loads(lines[0])
        self.assertFalse(out["success"])
        self.assertEqual(out["errorKind"], "engine")

    def test_main_refuses_empty_and_invalid_json_with_one_json(self):
        for stdin in ("", "{not json"):
            proc = subprocess.run([sys.executable, str(HERE / "lpbf_process_window.py")], input=stdin,
                                  capture_output=True, text=True, cwd=str(HERE), timeout=60)
            out = json.loads(proc.stdout)
            self.assertFalse(out["success"])
            self.assertEqual(out["errorKind"], "validation")



# Tang advisory bump (2026-10-27). UI default settings of the four alloy presets (src/store/useMaterialSpecimenStore.ts
# deriveSpecimenProperties: beam 80 um fallback, recommended layer 40 um and hatch 100 um, recommended preheat by base
# metal / hot-tearing class) on the engine default 11 x 11 axes. BEFORE was measured on the pre-bump tree (fc585b4a,
# solver revision lpbf-build-job-solt-v28); only its do-not-print cells may move, and only to printable or risky.
UI_DEFAULTS = {"in718": (80, 40, 100, 200), "ti64": (80, 40, 100, 150), "ss316l": (80, 40, 100, 80),
               "alsi10mg": (80, 40, 100, 160)}
VERDICT_ORDER = ("printable", "risky", "do-not-print", "inconclusive", "error")
BEFORE = {"in718": (0, 58, 58, 5, 0), "ti64": (0, 68, 53, 0, 0), "ss316l": (0, 22, 91, 8, 0),
          "alsi10mg": (62, 43, 16, 0, 0)}
AFTER = {"in718": (27, 89, 0, 5, 0), "ti64": (31, 90, 0, 0, 0), "ss316l": (56, 57, 0, 8, 0),
         "alsi10mg": (78, 43, 0, 0, 0)}


class TangAdvisoryDefaultGrid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pwc.clear()
        cls.maps = {}
        for alloy, (beam, layer, hatch, preheat) in UI_DEFAULTS.items():
            cls.maps[alloy] = pw.run_process_window({"alloyId": alloy, "beamDiameter_um": beam, "layer_um": layer,
                                                     "hatch_um": hatch, "preheatTemp_C": preheat})

    def test_counts_after_the_bump(self):
        for alloy, r in self.maps.items():
            self.assertTrue(r["success"], alloy)
            self.assertEqual(r["grid"]["nCells"], 121, alloy)
            self.assertEqual(tuple(r["counts"][k] for k in VERDICT_ORDER), AFTER[alloy], alloy)

    def test_only_former_do_not_print_cells_moved(self):
        for alloy in UI_DEFAULTS:
            b, a = dict(zip(VERDICT_ORDER, BEFORE[alloy])), dict(zip(VERDICT_ORDER, AFTER[alloy]))
            self.assertEqual(a["do-not-print"], 0, alloy)
            self.assertEqual((a["inconclusive"], a["error"]), (b["inconclusive"], b["error"]), alloy)
            self.assertGreaterEqual(a["printable"], b["printable"], alloy)
            self.assertGreaterEqual(a["risky"], b["risky"], alloy)
            self.assertEqual(a["printable"] + a["risky"], b["printable"] + b["risky"] + b["do-not-print"], alloy)

    def test_tang_never_blocks_and_is_reported_as_an_advisory(self):
        for alloy, r in self.maps.items():
            for c in r["cells"]:
                self.assertNotIn("lof_tang", c["blockingGates"], (alloy, c["power_W"], c["speed_mm_s"]))
                self.assertNotEqual(c["dominantGate"], "lof_tang")
            self.assertTrue(any("lof_tang" in c["advisoryGates"] for c in r["cells"]), alloy)
            self.assertIs(r["evidence"]["experimentalValidation"], False)

    def test_in718_has_printable_cells_inside_the_literature_box(self):
        cells = self.maps["in718"]["cells"]
        inside = sorted((c["power_W"], c["speed_mm_s"]) for c in cells
                        if c["verdict"] == "printable" and c["insideLiteratureBox"])
        self.assertEqual(inside, [(138.0, 765.0), (138.0, 887.5)])
        for c in cells:
            if c["verdict"] == "printable":
                self.assertIn("fusion adequacy is not established", c["headline"])


if __name__ == "__main__":
    unittest.main()
