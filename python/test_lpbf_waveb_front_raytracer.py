"""Wave B (raytracer-solidification): KS-1 front sampling, KS-4/6/7 powder-bed ray tracer, KS-8 DOIs.

Self-contained: KS-1/KS-8 use analytic fields and module constants only; the ray-tracer checks run only
when warp + CUDA are importable (the module hard-codes cuda:0) and are skipped otherwise.
"""
import importlib
import math
import sys
import unittest
from unittest import mock

import numpy as np

import solidification_front as sf
from lpbf_solidification_microstructure import _MICROSTRUCTURE_DOI


def rosenthal(q=100.0, v=1.0, k=20.0, alpha=5e-6, T0=25.0):
    """Exact Rosenthal 3D point source on a half space, laser frame, +x travel (no regularisation)."""
    def T(x, y, z):
        r = math.sqrt(x * x + y * y + z * z) or 1e-12
        return T0 + q / (2.0 * math.pi * k * r) * math.exp(-v * (r + x) / (2.0 * alpha))
    return T


def rear_extent(T, T_liq):
    lo, hi = 1e-7, 1e-2
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if T(-mid, 0.0, 0.0) >= T_liq:
            lo = mid
        else:
            hi = mid
    return lo


class FrontSamplingKS1(unittest.TestCase):
    def setUp(self):
        self.T = rosenthal()
        self.T_liq = 1400.0
        self.x_rear = rear_extent(self.T, self.T_liq)

    def _map(self, **kw):
        return sf.map_solidification_front(self.T, self.T_liq, 1.0, self.x_rear, 4.0 * self.x_rear,
                                           h_m=1e-7, **kw)

    def test_only_solidifying_samples(self):
        m = self._map()
        self.assertIsNotNone(m)
        self.assertGreaterEqual(m["nPoints"], 3)
        self.assertTrue(all(s["n_x"] > 0.0 and s["R_m_s"] > 0.0 for s in m["samples"]), m["samples"])

    def test_medians_over_one_sample_set(self):
        m = self._map()
        for key, med in (("G_K_m", "G_median_K_m"), ("R_m_s", "R_median_m_s"),
                         ("coolingRate_K_s", "coolingRate_median_K_s")):
            vals = sorted(s[key] for s in m["samples"])
            self.assertEqual(m[med], vals[len(vals) // 2])

    def test_r_matches_v_cos_alpha_on_exact_field(self):
        # Kou: R = v cos(alpha) with cos(alpha) = n_x of grad T on the trailing liquidus.
        m = self._map()
        for s in m["samples"]:
            x, z = s["x_um"] * 1e-6, s["z_um"] * 1e-6
            h = 1e-8
            gx = (self.T(x + h, 0, z) - self.T(x - h, 0, z)) / (2 * h)
            gz = (self.T(x, 0, z + h) - self.T(x, 0, z - h)) / (2 * h)
            self.assertAlmostEqual(s["R_m_s"], gx / math.hypot(gx, gz), delta=0.02)

    def test_all_melting_side_field_returns_none(self):
        # dT/dx < 0 everywhere: every liquidus point is melting (n_x < 0) -> no solidification sample.
        def melting(x, _y, z):
            return 1500.0 - 1.0e6 * x - 1.0e7 * z
        self.assertIsNone(sf.map_solidification_front(melting, 1400.0, 1.0, 20e-6, 1e-4, h_m=1e-7))


class CitationsKS8(unittest.TestCase):
    def test_dois_are_the_crossref_resolving_ones(self):
        # SOL-A1 (2026-10-15, SPEC A3.A3): no Hunt DOI on a null front block; the front module carries none.
        self.assertFalse(hasattr(sf, "HUNT_DOI"))
        self.assertEqual(_MICROSTRUCTURE_DOI, {
            "pdas": "10.1007/BF02648950",
            "sdas": "10.1016/0025-5416(85)90319-2",
            "morphology": "10.1016/0025-5416(84)90201-5",
        })


class GaussianSamplerKS6(unittest.TestCase):
    def test_inverse_cdf_reproduces_gaussian_second_moment(self):
        # I ~ exp(-2 r^2 / w^2): <r^2> = w^2 / 2 and P(r > w) = exp(-2).
        w = 40.0
        u = (np.arange(200000) + 0.5) / 200000
        r = w * np.sqrt(-0.5 * np.log(1.0 - u))
        self.assertAlmostEqual(float(np.mean(r * r)) / (w * w), 0.5, delta=2e-3)
        self.assertAlmostEqual(float(np.mean(r > w)), math.exp(-2.0), delta=1e-3)


def _cuda():
    try:
        import warp as wp
        wp.init()
        return wp.is_cuda_available()
    except Exception:
        return False


@unittest.skipUnless(_cuda(), "warp + CUDA not available")
class PowderBedRaytracerKS4KS6KS7(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # tools/lpbf_dataset_comparison.py and tools/lpbf_powder_layer_analysis.py pin the flat-plate path by
        # setting sys.modules["powder_bed_raytracer"] = None and never restore it; when their tests run first
        # in the same process the import below would fail. Drop only that None pin, for this import only.
        with mock.patch.dict(sys.modules):
            if "powder_bed_raytracer" in sys.modules and sys.modules["powder_bed_raytracer"] is None:
                del sys.modules["powder_bed_raytracer"]
            cls.pbr = importlib.import_module("powder_bed_raytracer")

    def test_energy_closure_and_convergence(self):
        a = self.pbr.calculate_powder_bed_absorptivity(40.0, 0.18, 100000)
        self.assertLess(a["energy_closure_residual"], 1e-5)
        self.assertLess(a["truncated_fraction"], 1e-5)
        b = self.pbr.calculate_powder_bed_absorptivity(40.0, 0.18, 100000, max_bounces=200,
                                                       min_remaining_power=1e-9)
        self.assertAlmostEqual(a["effective_absorptivity"], b["effective_absorptivity"], delta=1e-4)

    def test_gaussian_beam_result_does_not_swing_with_radius(self):
        vals = [self.pbr.calculate_powder_bed_absorptivity(r, 0.38, 100000)["effective_absorptivity"]
                for r in (27.5, 35.0, 40.0, 50.0)]
        self.assertLess(max(vals) - min(vals), 0.005, vals)

    def test_penetration_depth_is_inside_the_bed(self):
        d = self.pbr.calculate_powder_bed_absorptivity(40.0, 0.38, 100000)["average_penetration_depth_um"]
        self.assertGreater(d, 0.0)
        self.assertLessEqual(d, 2.0 * self.pbr.PARTICLE_RADIUS_UM)


if __name__ == "__main__":
    unittest.main()
