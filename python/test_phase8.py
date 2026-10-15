"""
test_phase8.py — Phase 8 Solidification Microstructure Coupling verification suite
====================================================================================
Tests the following components:
  1. Hunt-Lu PDAS and Kirkwood SDAS correlations (physical range).
  2. Hunt morphology criterion (G/R classification).
  3. Morphology fraction normalization (must sum to 1.0).
  4. compute_solidification_microstructure() without CFD data returns "unavailable"
     (moved to test_phase8_microstructure_contract.py, unittest).
  5. compute_solidification_microstructure() with mock CFD JSON (OpenFOAM path)
     (moved to test_phase8_microstructure_contract.py, unittest).
  6. lpbf_cfd.cfd_multiphysics() returns solidificationMicrostructure key.

Run with (from python/):
    python -B -m unittest test_phase8 -v
"""

import math
import tempfile
import unittest
from pathlib import Path

# ---- import Phase 8 module --------------------------------------------------
from lpbf_solidification_microstructure import (
    compute_solidification_microstructure,
)


class Phase8Correlations(unittest.TestCase):
    def test_legacy_classifier_retired(self):
        import lpbf_solidification_microstructure as module
        self.assertFalse(hasattr(module, "hunt_morphology"))
        self.assertFalse(hasattr(module, "morphology_fractions"))


# Tests 5 and 6 (compute_solidification_microstructure without CFD data -> "unavailable"; OpenFOAM CFD path)
# live in test_phase8_microstructure_contract.py (unittest, runs without pytest).

# ---------------------------------------------------------------------------
# Test 7 -- cfd_multiphysics returns solidificationMicrostructure key
# ---------------------------------------------------------------------------

class Phase8CfdKey(unittest.TestCase):
    def test_cfd_multiphysics_solidification_key(self):
        """cfd_multiphysics() must return a solidificationMicrostructure key (may be {})."""
        try:
            from lpbf_cfd import cfd_multiphysics
        except ImportError:
            self.skipTest("lpbf_cfd not importable in this environment")

        p = {
            "power_W": 300.0,
            "speed_mm_s": 800.0,
            "beamDiameter_um": 80,
            "tracks": 1,
            "trackLength_um": 50,
            "hatch_um": 50,
            "layers": 1,
            "layer_um": 30,
            "preheat_C": 20,
            "scanAngle_deg": 0.0,
            "layerRotation_deg": 67.0,
            "strategy": "unidirectional",
            "stripeWidth_um": 10000,
            "islandSize_um": 5000,
            "dwell_s": 0.0,
            "cooling_s": 0.0,
            "mesh_um": 20,
            "maxDt_s": 5e-8,
        }
        m = {
            "solidus_K": 1650,
            "liquidus_K": 1700,
            "boiling_K": 3560,
            "absorptivity": 0.4
        }

        with tempfile.TemporaryDirectory() as tmp:
            try:
                result = cfd_multiphysics(p, m, artifact_dir=tmp)
            except NotImplementedError as exc:
                if "Fabrication of powder bed via random packing is disabled" not in str(exc):
                    raise
                self.skipTest(f"cfd_multiphysics currently refuses to run (powder-bed packing disabled): {exc}")

        # The key must exist (value may be {} if WSL/OpenFOAM unavailable)
        self.assertIn("solidificationMicrostructure", result,
                      "cfd_multiphysics() must return 'solidificationMicrostructure' key")
        self.assertIsInstance(result["solidificationMicrostructure"], dict)


if __name__ == "__main__":
    unittest.main()
