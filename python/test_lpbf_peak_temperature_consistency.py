"""The served peak is the loss-free Eagar-Tsai surface maximum at the kernel's own inputs (P6 containment).

Since the P6 bump (2026-10-11) hydrodynamicsAndRecoil.peakTemperature_C is the numerical maximum along the axis
y = z = 0 of the loss-free Eagar & Tsai 1983 field driven by the requested kernel's field power, k/alpha blend and
1/e^2 radius (eagar_tsai_solver.eagar_tsai_surface_maximum), served only below the sourced vapour temperature and
null with a reason otherwise. meltPoolGeometry.axialFieldMaximum_C is the kernel's own axial maximum at
peakOffset_um for Eagar-Tsai and Goldak under the same policy, and null for Rosenthal (regularised value). The
former T(0,0,0) beam-centre peak of the kernel is no longer served.
"""
import unittest
from unittest.mock import patch

import lpbf_thermal_solver as solver

# 316L carries a sourced T_v (Khairallah 2016, 3086 K); 20 W / 2000 mm/s keeps the loss-free maximum below it.
LOW = ("316L Stainless Steel", 20.0, 2000.0, 80.0)
HIGH = ("316L Stainless Steel", 285.0, 960.0, 80.0)
UNSOURCED = ("Inconel 718", 20.0, 2000.0, 80.0)


class PeakTemperatureConsistency(unittest.TestCase):
    def _record(self, args, heat_source):
        calls = []
        original = solver.eagar_tsai_surface_maximum

        def recording(*a, **kw):
            out = original(*a, **kw)
            calls.append((a, out))
            return out

        with patch.object(solver, "eagar_tsai_surface_maximum", recording):
            result = solver.calculate_meltpool_physics(*args, preheat_temp_C=80.0, heat_source=heat_source)
        self.assertEqual(len(calls), 1, "the loss-free maximum is evaluated exactly once")
        return result, calls[0]

    def test_served_peak_is_the_loss_free_maximum_at_the_kernel_inputs(self):
        inputs = {}
        for src in ("rosenthal", "eagar-tsai", "goldak"):
            result, (args, out) = self._record(LOW, src)
            pp = result["processParameters"]
            T0, P_eff, k_th, alpha_th, r0, v = args
            self.assertEqual(P_eff, pp["fieldPower_W"], src)
            self.assertAlmostEqual(k_th, pp["effectiveConductivity_W_mK"], places=9)
            self.assertAlmostEqual(r0, 40e-6, places=15)
            self.assertAlmostEqual(v, 2.0, places=12)
            self.assertEqual(T0, 80.0)
            inputs[src] = args
            h = result["hydrodynamicsAndRecoil"]
            self.assertEqual(h["peakTemperature_C"], round(out["T_C"], 1), src)
            self.assertEqual(h["peakLocation_x_um"], round(out["x_m"] * 1e6, 1), src)
            self.assertLessEqual(h["peakLocation_x_um"], 0.0)
            self.assertEqual(h["surfaceTemperature_C"], h["peakTemperature_C"])
            self.assertEqual(h["peakTemperatureModelId"], "eagar-tsai-v2")
            self.assertLess(h["peakTemperature_C"], h["vaporTemperatureSourced_C"])
        self.assertEqual(len({v for v in inputs.values()}), 1, "every kernel passes the same inputs")

    def test_null_above_the_sourced_tv_and_where_unsourced(self):
        for src in ("rosenthal", "eagar-tsai", "goldak"):
            above, (_, out) = self._record(HIGH, src)
            h = above["hydrodynamicsAndRecoil"]
            self.assertGreaterEqual(out["T_C"], h["vaporTemperatureSourced_C"])
            self.assertIsNone(h["peakTemperature_C"], src)
            self.assertIsNone(h["peakLocation_x_um"])
            self.assertIs(h["peakExceedsVaporization"], True)
            self.assertIn("impossible situation", h["peakUnavailableReason"])
            unsourced, _ = self._record(UNSOURCED, src)
            u = unsourced["hydrodynamicsAndRecoil"]
            self.assertIsNone(u["peakTemperature_C"], src)
            self.assertIsNone(u["peakExceedsVaporization"])
            self.assertIn("no sourced vapour temperature", u["peakUnavailableReason"])

    def _axial(self, args, heat_source, field_owner, method_name):
        axial_values = []
        original = getattr(field_owner, method_name)

        def recording_temperature(field, x_m, y_m, z_m):
            value = original(field, x_m, y_m, z_m)
            # Scalar axis samples of the kernel field only (the loss-free maximum search passes arrays).
            if getattr(x_m, "ndim", 0) == 0 and y_m == 0.0 and z_m == 0.0:
                axial_values.append(float(value))
            return value

        with patch.object(field_owner, method_name, recording_temperature):
            result = solver.calculate_meltpool_physics(*args, preheat_temp_C=80.0, heat_source=heat_source)
        return result, axial_values

    def test_distributed_source_axial_maximum_is_the_kernels_own_under_the_tv_policy(self):
        for heat_source, owner in (("eagar-tsai", solver.EagarTsaiField), ("goldak", solver.GoldakField)):
            result, axial_values = self._axial(LOW, heat_source, owner, "temperature_C")
            g = result["meltPoolGeometry"]
            self.assertTrue(axial_values, heat_source)
            self.assertAlmostEqual(g["axialFieldMaximum_C"], round(max(axial_values), 1), delta=0.11, msg=heat_source)
            self.assertLessEqual(g["peakOffset_um"], 0.0)
            self.assertIsNone(g["axialFieldMaximumUnavailableReason"])
            high, _ = self._axial(HIGH, heat_source, owner, "temperature_C")
            self.assertIsNone(high["meltPoolGeometry"]["axialFieldMaximum_C"], heat_source)
            self.assertIn("sourced vapour temperature", high["meltPoolGeometry"]["axialFieldMaximumUnavailableReason"])

    def test_rosenthal_axial_maximum_is_null(self):
        for args in (LOW, HIGH, UNSOURCED):
            g = solver.calculate_meltpool_physics(*args, preheat_temp_C=80.0, heat_source="rosenthal")["meltPoolGeometry"]
            self.assertIsNone(g["axialFieldMaximum_C"])
            self.assertIn("regularised singular-source value", g["axialFieldMaximumUnavailableReason"])
            # Wave B LA-2: R + x = 0 on the trailing axis, so the Rosenthal field still peaks at the beam centre.
            self.assertEqual(g["peakOffset_um"], 0.0)


if __name__ == "__main__":
    unittest.main()
