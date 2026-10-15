"""The legacy CFD numerical path is quarantined at SOL-A1."""
import unittest
from lpbf_solidification_microstructure import compute_solidification_microstructure
from quantity_envelope import envelope_problems

class Phase8MicrostructureContractTest(unittest.TestCase):
    def test_legacy_path_never_serves_quantities(self):
        for cfd in (None, {}, {"solidificationMicrostructure": {"meanG_K_m": 1e6, "meanR_m_s": 0.5}}):
            out = compute_solidification_microstructure({}, {}, cfd)
            self.assertEqual(out["schema"], "lpbf-solidification-microstructure-2")
            self.assertEqual(out["status"], "unavailable")
            self.assertEqual(envelope_problems(out), [])
            for q in out["quantities"].values():
                self.assertIsNone(q["value"])
                self.assertEqual(q["reasons"][0]["code"], "quarantined-legacy-path")
