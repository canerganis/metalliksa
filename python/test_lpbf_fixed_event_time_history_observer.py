"""Opt-in scalar history at accepted LPBF steps; no field history copies."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import lpbf_simulation
import run_lpbf_fixed_event_time_history_probe as probe


SMALL_CASE = {
    "mode": "standard", "backend": "reference", "material": "Inconel 718",
    "power_W": 60, "speed_mm_s": 1200, "mesh_um": 40,
    "maxDt_s": 2e-7, "layer_um": 80, "trackLength_um": 100,
    "cooling_s": 0, "dwell_s": 0,
}
FROZEN_IMPLEMENTATION = json.loads(probe.PROTOCOL_PATH.read_bytes())["expectedImplementationFingerprint"]


class LocalTimeHistoryObserverTests(unittest.TestCase):
    def test_selected_cell_reports_accepted_post_step_state_and_rate_split(self):
        records = []
        original = lpbf_simulation.source_limited_step
        settings, _ = lpbf_simulation.validate(SMALL_CASE)
        domain = lpbf_simulation.calculate_mesh_domain(settings)
        dx = domain["dx"]
        cell_case = {"indices": [(0, 0, 0)], "dt": SMALL_CASE["maxDt_s"],
                     "positions": [[dx/2-domain["span"]/2,
                                    dx/2-domain["ny"]*dx/2,
                                    dx/2-domain["substrate_depth"]]]}
        buffer = probe.HistoryBuffer(cell_case, 1000)

        def quiet_source(*args, **kwargs):
            dt, source, rate, capture, retries = original(*args, **kwargs)
            return dt, np.zeros_like(source), rate-source, capture, retries

        def observe(record):
            records.append(record)
            buffer.observe(record)

        with mock.patch.object(lpbf_simulation, "source_limited_step", side_effect=quiet_source):
            result = lpbf_simulation.run(
                SMALL_CASE, local_history_observer=observe,
                local_history_indices_ijk=((0, 0, 0),))

        self.assertEqual(len(records), result["discretization"]["steps"])
        self.assertEqual(buffer.count, len(records))
        first = records[0]
        self.assertEqual(first["step"], 1)
        self.assertGreater(first["time_s"], 0)
        self.assertEqual(first["cell_indices_ijk"], [[0, 0, 0]])
        cell = first["cells"][0]
        self.assertEqual(cell["sourceRate_W_m3"], 0.)
        self.assertFalse(cell["everLiquidusBefore"])
        self.assertFalse(cell["everLiquidusAfter"])
        self.assertGreater(cell["effectiveConductivity_W_mK"], 0.)
        self.assertAlmostEqual(cell["enthalpy_J_m3"],
                               first["acceptedDt_s"]*(cell["sourceRate_W_m3"]
                                                       +cell["passiveRate_W_m3"]), places=8)
        self.assertTrue(np.isfinite(cell["temperature_K"]))

    def test_history_rejects_invalid_indices_before_solving(self):
        for index in (((-1, 0, 0),), ((0, 0, 0), (0, 0, 0)), ((True, 0, 0),)):
            with self.subTest(index=index), self.assertRaises(ValueError):
                lpbf_simulation.run(SMALL_CASE, local_history_observer=lambda record: None,
                                    local_history_indices_ijk=index)

    def test_runner_preflight_binds_prior_fields_without_solving(self):
        # The completed diagnostic owns these frozen destinations. Bypass only
        # freshness and source identity only for this historical archive fixture.
        # P7b (2026-10-14): the archive ran at the former IN718 default absorptivity 0.38; the served default is now the
        # authority 0.32, and the registry identity carries the authority keys and kernelLedgerSha256. Like the parity
        # reference replays, this test replays the archived request with its absorptivity explicit (the resolved-input
        # digests then reproduce the archive rows bit for bit) and binds the plan through a temporary protocol copy
        # whose materialRevisionSha256 is the re-identified material of that request. The frozen protocol keeps its
        # 2026-10-02 identities as a record; the diagnostic is not re-runnable at today's defaults.
        real_validate = lpbf_simulation.validate
        archived_request = lambda request: real_validate({**request, "absorptivity": 0.38})  # noqa: E731
        protocol = json.loads(probe.PROTOCOL_PATH.read_bytes())
        scenario = json.loads(probe.safe_path(protocol["scenarioFile"]).read_bytes())["scenario"]
        scenario.update(protocol["scenarioOverrides"])
        for dt in protocol["levels"]:
            resolved, material = archived_request({**scenario, "maxDt_s": dt})
            self.assertEqual(hashlib.sha256(json.dumps(resolved, sort_keys=True, allow_nan=False).encode()).hexdigest(),
                             protocol["expectedInputSha256ByMaxDt"][str(dt)])
            protocol["materialRevisionSha256"] = material["materialRevisionSha256"]
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "protocol.json"
            copy.write_bytes(json.dumps(protocol).encode())
            with mock.patch.object(probe, "PROTOCOL_PATH", copy), mock.patch.object(probe, "fresh_destinations"), \
                    mock.patch.object(lpbf_simulation, "validate", side_effect=archived_request), \
                    mock.patch.object(lpbf_simulation, "implementation_fingerprint", return_value=FROZEN_IMPLEMENTATION):
                with mock.patch.object(lpbf_simulation, "run", side_effect=AssertionError("must not solve")):
                    plan = probe.preflight()
        self.assertEqual(len(plan["cases"]), 2)
        self.assertEqual(len(plan["cases"][0]["indices"]), 19)
        self.assertEqual(plan["cases"][0]["centerIndices"],
                         [(30, 43, 60), (59, 43, 61), (59, 44, 61)])
        self.assertEqual(plan["historyMaximumUncompressedBytes"], 15939000)
        self.assertFalse(plan["protocol"]["experimentalValidation"])

    def test_runner_rejects_changed_prior_report_identity(self):
        with mock.patch.object(probe, "fresh_destinations"), \
                mock.patch.object(lpbf_simulation, "implementation_fingerprint", return_value=FROZEN_IMPLEMENTATION):
            with mock.patch.object(probe, "sha256_file", return_value="1" * 64):
                with self.assertRaisesRegex(ValueError, "report hash"):
                    probe.preflight()

    def test_runner_rejects_changed_source_before_solving(self):
        with mock.patch.object(probe, "fresh_destinations"), \
                mock.patch.object(lpbf_simulation, "implementation_fingerprint", return_value="1" * 64), \
                mock.patch.object(lpbf_simulation, "run", side_effect=AssertionError("must not solve")):
            with self.assertRaisesRegex(ValueError, "implementation differs"):
                probe.preflight()

    def test_runner_still_rejects_existing_diagnostic_destinations(self):
        protocol = json.loads(probe.PROTOCOL_PATH.read_bytes())
        with self.assertRaisesRegex(FileExistsError, "destination exists"):
            probe.fresh_destinations(protocol)

    def test_history_comparison_uses_physical_time(self):
        class SyntheticHistory:
            def __init__(self, times, temperatures):
                self._arrays = {
                    "time_s": np.asarray(times),
                    "cell_indices_ijk": np.array([[0, 0, 0]]),
                    "coordinates_m": np.array([[0., 0., 0.]]),
                    "values": np.zeros((len(times), 1, len(probe.VALUES))),
                    "ever": np.zeros((len(times), 1, 2), dtype=bool),
                }
                self._arrays["values"][:, 0, 0] = temperatures

            def arrays(self):
                return self._arrays

        coarse = SyntheticHistory([.05, .1], [300., 310.])
        fine = SyntheticHistory([.025, .05, .075, .1], [299., 300., 307., 312.])
        result = probe.compare_histories(coarse, fine, .1)
        self.assertEqual(result["matchedPhysicalCheckpoints"], 2)
        self.assertEqual(result["maximumAbsoluteTemperatureDifference_K"], 2.)
        self.assertEqual(result["maximumDifferenceAt"]["time_s"], .1)


if __name__ == "__main__":
    unittest.main()
