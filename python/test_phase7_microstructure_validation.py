import unittest
from lpbf_solidification_microstructure import (
    hunt_morphology,
    morphology_fractions
)
from kinetics_ttt_cct_solver import solve_phase_transformation_kinetics

class TestPhase7MicrostructureValidation(unittest.TestCase):
    # P7a (2026-10-11): the CFD-path Hunt-Lu (80) and Kirkwood (64.5) prefactors were unsourced and are deleted;
    # the former test_01 and test_02 on them are removed. PDAS/SDAS on that path are served as None.
    def test_01_cfd_path_serves_no_spacing(self):
        from lpbf_solidification_microstructure import compute_solidification_microstructure
        cfd = {"solidificationMicrostructure": {"meanG_K_m": 1.0e6, "meanR_m_s": 0.5, "meanCoolingRate_K_s": 5.0e5}}
        out = compute_solidification_microstructure({}, {}, cfd)
        self.assertEqual(out["status"], "available")
        self.assertIsNone(out["PDAS_um"])
        self.assertIsNone(out["SDAS_um"])
        self.assertIn("no source", out["spacingUnavailableReason"])

    def test_03_hunt_morphology(self):
        # Columnar: G/R > 1e8 K s/m^2
        self.assertEqual(hunt_morphology(1e6, 0.005), "columnar")
        # Equiaxed: G/R < 1e6
        self.assertEqual(hunt_morphology(1e5, 0.2), "equiaxed")
        # Mixed: G/R between 1e6 and 1e8
        self.assertEqual(hunt_morphology(1e6, 0.1), "mixed")
        
        fracs = morphology_fractions(1e6, 0.1)
        self.assertGreater(fracs["columnar"], 0.0)
        self.assertGreater(fracs["equiaxed"], 0.0)
        self.assertAlmostEqual(fracs["columnar"] + fracs["equiaxed"] + fracs["mixed"], 1.0)

    def test_04_kinetics_lpbf_quench(self):
        # LPBF Cooling Rate (1e6 K/s) for AISI 4140 should suppress diffusion completely.
        # Martensite fraction should be very high (or 100% within metastable limit).
        res = solve_phase_transformation_kinetics(
            alloy_name="AISI 4140",
            cooling_rate_c_s=1e5, # Very fast cooling
            grain_size_um=25.0
        )
        self.assertTrue(res["success"])
        gap = res["calphadVsKineticsGap"]["kineticRealityAtSelectedCooling"]
        self.assertTrue(gap["isSuppressedEquilibrium"])
        # Lane kin-li (Li 1998 model): no diffusional start above Ms; Koistinen-Marburger fraction at 25 C
        self.assertIn("No diffusional start above Ms", gap["verdict"])
        self.assertGreaterEqual(gap["predictedMartensite_pct"], 90.0)

    def test_05_kinetics_slow_cooling(self):
        # Slow cooling (furnace anneal) for AISI 4140 should result in Pearlite/Bainite.
        res = solve_phase_transformation_kinetics(
            alloy_name="AISI 4140",
            cooling_rate_c_s=0.5, # Slow cool
            grain_size_um=25.0
        )
        gap = res["calphadVsKineticsGap"]["kineticRealityAtSelectedCooling"]
        self.assertFalse(gap["isSuppressedEquilibrium"])
        # Lane kin-li: a diffusional (ferrite) start is reached; fractions are not computed, so no martensite %
        self.assertIn("Ferrite start at", gap["verdict"])
        self.assertIsNone(gap["predictedMartensite_pct"])

if __name__ == '__main__':
    unittest.main()
