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
    hunt_morphology,
    morphology_fractions,
    compute_solidification_microstructure,
)


class Phase8Correlations(unittest.TestCase):
    # Tests 1 and 2 (Hunt-Lu PDAS 80 and Kirkwood SDAS 64.5 ranges) removed in P7a (2026-10-11): the prefactors were
    # unsourced and are deleted; the CFD path serves PDAS_um and SDAS_um as None (test_phase8_microstructure_contract).

    # Test 3 -- Hunt morphology criterion
    def test_morphology_columnar(self):
        """G/R > 1e8 -> columnar."""
        G, R = 1.0e9, 0.05   # G/R = 2e10 >> 1e8
        morph = hunt_morphology(G, R)
        self.assertEqual(morph, "columnar", f"Expected columnar, got {morph}")

    def test_morphology_equiaxed(self):
        """G/R < 1e6 -> equiaxed."""
        G, R = 1.0e4, 0.5    # G/R = 2e4 << 1e6
        morph = hunt_morphology(G, R)
        self.assertEqual(morph, "equiaxed", f"Expected equiaxed, got {morph}")

    def test_morphology_mixed(self):
        """G/R between 1e6 and 1e8 -> mixed."""
        G, R = 1.0e6, 0.02   # G/R = 5e7 (in between)
        morph = hunt_morphology(G, R)
        self.assertEqual(morph, "mixed", f"Expected mixed, got {morph}")

    # Test 4 -- Morphology fractions sum to 1.0
    def test_morphology_fractions_sum_to_unity(self):
        for G_Km, R_ms in [
            (1e9, 0.01),   # pure columnar
            (1e4, 1.0),    # pure equiaxed
            (5e6, 0.1),    # mixed zone
        ]:
            with self.subTest(G_Km=G_Km, R_ms=R_ms):
                fracs = morphology_fractions(G_Km, R_ms)
                total = fracs["columnar"] + fracs["equiaxed"] + fracs["mixed"]
                self.assertLess(
                    abs(total - 1.0), 0.01,
                    f"Morphology fractions sum {total:.4f} != 1.0 for G={G_Km:.1e}, R={R_ms}")


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
