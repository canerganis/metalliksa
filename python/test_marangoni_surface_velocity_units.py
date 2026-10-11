#!/usr/bin/env python3
"""LA-1: Marangoni surface velocity follows DebRoy & David, Rev. Mod. Phys. 67 (1995) 85, Eq. (8)."""
import math
import unittest

from marangoni_screening import debroy_david_surface_velocity_m_s, marangoni_screening


class SurfaceVelocityTest(unittest.TestCase):
    def test_debroy_david_worked_example(self):
        # RMP 67 (1995) p. 88: W = 0.5 cm, rho = 7.2 g/cm3, mu = 0.06 P, dgamma/dT = 0.5 dyn/(cm K),
        # dT/dy = 600 K/cm -> "approximately 62 cm/sec".
        u = debroy_david_surface_velocity_m_s(0.5e-3, 6.0e4, 5e-3, 7200.0, 6e-3)
        self.assertAlmostEqual(u, 0.62, delta=0.01)

    def test_velocity_scales_as_length_to_minus_one_third(self):
        # dT/dy = dT/L and W = 2L -> u^(3/2) ~ L^(-1/2): doubling L at fixed dT divides u by 2^(1/3).
        a = marangoni_screening(-4e-4, 5e-3, 4.2e-6, 7450.0, 50e-6, 2850.0, 1336.0)
        b = marangoni_screening(-4e-4, 5e-3, 4.2e-6, 7450.0, 100e-6, 2850.0, 1336.0)
        self.assertAlmostEqual(a["surfaceVelocity_m_s"] / b["surfaceVelocity_m_s"], 2.0 ** (1.0 / 3.0), places=9)
        # Ma is unchanged by the fix and stays linear in L.
        self.assertAlmostEqual(b["marangoniNumber"] / a["marangoniNumber"], 2.0, places=9)

    def test_lpbf_order_of_magnitude(self):
        # IN718-like inputs, L = 77 um: metres per second (Khairallah et al. 2016 report 1-9 m/s
        # surface flow in LPBF CFD), not the 0.009 m/s of the old sqrt(|dgamma/dT| dT / rho).
        r = marangoni_screening(-4e-4, 5e-3, 4.2e-6, 7450.0, 77e-6, 2850.0, 1336.0)
        self.assertGreater(r["surfaceVelocity_m_s"], 1.0)
        self.assertLess(r["surfaceVelocity_m_s"], 20.0)
        self.assertAlmostEqual(r["pecletMarangoni"], r["surfaceVelocity_m_s"] * 77e-6 / 4.2e-6, places=9)
        self.assertEqual(r["surfaceVelocityDoi"], "10.1103/RevModPhys.67.85")

    def test_zero_gradient_gives_zero_velocity(self):
        r = marangoni_screening(-4e-4, 5e-3, 4.2e-6, 7450.0, 77e-6, 2850.0, 1336.0, sulfur_ppm=45.0)
        self.assertEqual(r["flowDirection"], "neutral")
        self.assertEqual(r["surfaceVelocity_m_s"], 0.0)
        self.assertTrue(math.isfinite(r["pecletMarangoni"]))


class SolverPassThroughTest(unittest.TestCase):
    def test_build_job_marangoni_block_carries_the_doi(self):
        import contextlib, io, sys
        from unittest import mock
        import lpbf_thermal_solver as solver
        with mock.patch.dict(sys.modules, {"powder_bed_raytracer": None}), contextlib.redirect_stdout(io.StringIO()):
            r = solver.calculate_meltpool_physics("Inconel 718", 200.0, 800.0, 80.0, 80.0, 40.0, 110.0)
            served = solver.calculate_meltpool_physics("316L Stainless Steel", 20.0, 2000.0, 80.0, 80.0, 40.0, 110.0)
        # P6 (2026-10-11): the velocity reads the served peak; IN718 has no sourced vapour temperature, so it is null
        # with a reason (the DOI of the method is still carried); a served 316L peak gives a positive velocity.
        self.assertEqual(r["marangoniModel"]["surfaceVelocityDoi"], "10.1103/RevModPhys.67.85")
        self.assertIsNone(r["marangoniModel"]["surfaceVelocity_m_s"])
        self.assertIn("no sourced vapour temperature", r["marangoniModel"]["marangoniUnavailableReason"])
        self.assertEqual(served["marangoniModel"]["surfaceVelocityDoi"], "10.1103/RevModPhys.67.85")
        self.assertGreater(served["marangoniModel"]["surfaceVelocity_m_s"], 0.0)
        self.assertIsNone(served["marangoniModel"]["marangoniUnavailableReason"])

if __name__ == "__main__":
    unittest.main()
