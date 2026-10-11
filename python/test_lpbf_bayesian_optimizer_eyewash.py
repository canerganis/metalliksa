import unittest
from unittest import mock

import lpbf_bayesian_optimizer as bo


class TestBayesianOptimizerHonesty(unittest.TestCase):
    def test_unknown_alloy_refused_not_in718(self):
        res = bo.run_bayesian_optimization("specimen-inconel-718", n_iter=2, n_warmup=1)
        self.assertFalse(res["success"])
        self.assertEqual(res["errorKind"], "validation")
        self.assertNotIn("iterations", res)

    def test_missing_alloy_refused(self):
        self.assertFalse(bo.run_bayesian_optimization(None, n_iter=2, n_warmup=1)["success"])

    def test_ti64_resolves_to_ti64(self):
        res = bo.run_bayesian_optimization("Ti64", n_iter=2, n_warmup=1)
        self.assertTrue(res["success"])
        self.assertEqual(res["alloyId"], "ti6al4v")
        self.assertEqual(res["beamDiameter_um"], 80.0)
        self.assertEqual(res["preheatTemp_C"], 80.0)

    def test_beam_and_preheat_reach_solver(self):
        import lpbf_thermal_solver as ts
        real = ts.calculate_meltpool_physics
        seen = []

        def spy(**kw):
            seen.append((kw["beam_diameter_um"], kw["preheat_temp_C"]))
            return real(**kw)

        with mock.patch.object(ts, "calculate_meltpool_physics", spy):
            res = bo.run_bayesian_optimization("in718", n_iter=1, n_warmup=1,
                                               beam_diameter_um=100, preheat_temp_C=200)
        self.assertTrue(res["success"])
        self.assertEqual(seen, [(100.0, 200.0)])

    def test_solver_error_propagates_not_scored_zero(self):
        import lpbf_thermal_solver as ts
        with mock.patch.object(ts, "calculate_meltpool_physics", side_effect=RuntimeError("boom")):
            res = bo.run_bayesian_optimization("in718", n_iter=2, n_warmup=1)
        self.assertFalse(res["success"])
        self.assertEqual(res["errorKind"], "solver")
        self.assertIn("boom", res["error"])
        self.assertNotIn("iterations", res)

    def test_iteration_cap_enforced_not_clamped(self):
        res = bo.run_bayesian_optimization("in718", n_iter=bo.MAX_ITERATIONS + 1, n_warmup=1)
        self.assertFalse(res["success"])
        self.assertIn(str(bo.MAX_ITERATIONS), res["error"])

    def test_iterations_report_verdicts(self):
        res = bo.run_bayesian_optimization("ss316l", n_iter=2, n_warmup=1)
        self.assertTrue(all(isinstance(i["verdict"], str) for i in res["iterations"]))

    def _bad(self, **kw):
        args = dict(alloy_id="in718", n_iter=2, n_warmup=1); args.update(kw)
        res = bo.run_bayesian_optimization(**args)
        self.assertFalse(res["success"], kw)
        self.assertEqual(res["errorKind"], "validation", kw)
        return res

    def test_fractional_and_boolean_counts_rejected(self):
        self._bad(n_iter=20.7)
        self._bad(n_warmup=2.9)
        self._bad(n_iter=True)
        self.assertTrue(bo.run_bayesian_optimization("in718", n_iter=2.0, n_warmup=1)["success"])

    def test_bad_seed_is_validation_not_crash(self):
        self._bad(seed="abc")
        self._bad(seed=1.5)

    def test_preheat_must_be_below_solidus(self):
        self._bad(preheat_temp_C=5000)
        self._bad(preheat_temp_C=-1)

    def test_unknown_param_bounds_key_rejected(self):
        res = self._bad(param_bounds={"laser_power": (1, 2)})
        self.assertIn("laser_power", res["error"])

    def test_no_surrogate_step_is_reported(self):
        res = bo.run_bayesian_optimization("in718", n_iter=2, n_warmup=3)
        self.assertTrue(res["success"])
        self.assertEqual(res["surrogateSteps"], 0)
        res = bo.run_bayesian_optimization("in718", n_iter=3, n_warmup=1)
        self.assertEqual(res["surrogateSteps"], 2)

    def test_all_zero_run_presents_no_best_params(self):
        import lpbf_build_job_solver as bj
        with mock.patch.object(bj, "compose_verdict", return_value={"verdict": "do-not-print"}):
            res = bo.run_bayesian_optimization("in718", n_iter=3, n_warmup=3)
        self.assertTrue(res["success"])
        self.assertEqual(res["bestScore"], 0)
        self.assertTrue(res["noPositiveScore"])
        self.assertIsNone(res["bestParams"])
        self.assertEqual(res["verdictCounts"], {"do-not-print": 3})

    def test_iterations_return_gate_diagnostics(self):
        res = bo.run_bayesian_optimization("in718", n_iter=2, n_warmup=1)
        self.assertTrue(res["success"])
        keys = {"blockingGates", "riskGates", "advisoryGates", "reasons", "extentStatus",
                "normalizedEnthalpy", "aspectRatio_L_over_W", "keyholeRisk", "keyholeHigh", "keyholeMode",
                "ballingBand", "ballingLengthToWidthEagarTsai"}
        for it in res["iterations"]:
            d = it["diagnostics"]
            self.assertEqual(set(d), keys)
            self.assertIsInstance(d["normalizedEnthalpy"], float)
            self.assertIsInstance(d["keyholeHigh"], bool)
            self.assertTrue(d["reasons"])
            # Recoater / distortion never appear as failing or risk gates.
            self.assertFalse({"recoater", "distortion"} & set(d["blockingGates"] + d["riskGates"]))
            if it["verdict"] == "do-not-print":
                self.assertTrue(d["blockingGates"])
        self.assertIn("frozen", res["keyholeGateNote"])
        self.assertIn("keyhole-regime bump", res["keyholeGateNote"])
        self.assertEqual(set(res["gateSummary"]),
                         {"blockingGateCounts", "riskGateCounts", "advisoryGateCounts",
                          "inconclusiveExtentStatusCounts"})

    def test_all_zero_run_summarises_blocking_gates(self):
        import lpbf_build_job_solver as bj
        vd = {"verdict": "do-not-print", "blockingGates": ["keyhole"], "riskGates": ["balling"],
              "advisoryGates": ["recoater", "distortion"], "reasons": ["Keyhole porosity: ..."]}
        with mock.patch.object(bj, "compose_verdict", return_value=vd):
            res = bo.run_bayesian_optimization("in718", n_iter=3, n_warmup=3)
        self.assertTrue(res["noPositiveScore"])
        self.assertEqual(res["gateSummary"]["blockingGateCounts"], {"keyhole": 3})
        self.assertEqual(res["gateSummary"]["riskGateCounts"], {"balling": 3})
        self.assertEqual(res["iterations"][0]["diagnostics"]["advisoryGates"], ["recoater", "distortion"])
        self.assertEqual(res["gateSummary"]["advisoryGateCounts"], {"distortion": 3, "recoater": 3})

    def test_inconclusive_counted_and_scored_zero(self):
        import lpbf_build_job_solver as bj
        with mock.patch.object(bj, "compose_verdict", return_value={"verdict": "inconclusive"}):
            res = bo.run_bayesian_optimization("in718", n_iter=2, n_warmup=2)
        self.assertEqual(res["nInconclusive"], 2)
        self.assertIn("inconclusive", res["objective"])

    def test_surrogate_failure_is_not_labelled_solver(self):
        with mock.patch.object(bo.BayesianProcessOptimizer, "suggest_next", side_effect=RuntimeError("gp")):
            res = bo.run_bayesian_optimization("in718", n_iter=2, n_warmup=1)
        self.assertEqual(res["errorKind"], "optimizer")
        self.assertNotIn("Solver", res["error"])

    def test_cli_stdout_is_one_json_document(self):
        # Solver imports (NVIDIA Warp) print banners; the CLI must keep stdout parseable for the server route.
        import json, os, subprocess, sys
        here = os.path.dirname(os.path.abspath(__file__))
        payload = json.dumps({"alloyId": "in718", "nIterations": 2, "nWarmup": 1, "seed": 1})
        proc = subprocess.run([sys.executable, "-B", os.path.join(here, "lpbf_bayesian_optimizer.py")],
                              input=payload, capture_output=True, text=True, timeout=300, cwd=here)
        doc = json.loads(proc.stdout)
        self.assertTrue(doc["success"], doc)
        self.assertEqual(doc["alloyId"], "in718")
        self.assertEqual(len(doc["iterations"]), 2)

    def test_alias_requires_alloy(self):
        with self.assertRaises(TypeError):
            bo.optimize_process_window()


if __name__ == "__main__":
    unittest.main()
