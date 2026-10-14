"""Pins the Melt Pool lab consumer numbers of the corrected kernels (SPEC-lpbf-kernels-fable §6).

CPU path (flat-plate absorptivity, the default on every host). These are screening
numbers for regression only, not validation against NIST; the measured NIST width is 136.3 µm
and depth 139.7 µm (keyhole), the model is conduction-only plus the Fabbro depth proxy.
"""
import contextlib
import io
import unittest

from lpbf_thermal_solver import calculate_meltpool_physics

NIST = ("Inconel 718", 285, 960, 67, 23.5, 40, 110)


def _geometry(heat_source, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        result = calculate_meltpool_physics(*args, heat_source=heat_source, **kwargs)
    return result["meltPoolGeometry"], result


class MeltPoolConsumerPins(unittest.TestCase):
    def test_nist_goldak_cpu_fallback(self):
        g, r = _geometry("goldak", *NIST)
        self.assertEqual(r["modelId"], "goldak-half-space-v3")
        # Wave B LA-5 (absorbed power as Q, no latent-heat cut): Tier 2 117.4 / 558.5 um; v2 kernel 81.7 / 280.7.
        # P7b (2026-10-14): IN718 authority 0.32 and melting-point k / cp (P1 values 128.5 / 123.9 / 665.6; the Fabbro
        # depth follows A linearly, 123.9 x 0.32 / 0.38).
        self.assertAlmostEqual(g["width_um"], 104.7, delta=0.5)
        self.assertAlmostEqual(g["depth_um"], 104.4, delta=0.5)   # Fabbro depth at the authority A
        self.assertAlmostEqual(g["length_um"], 389.9, delta=1.0)
        self.assertEqual(g["extentStatus"], "computed")

    def test_nist_eagar_tsai(self):
        g, r = _geometry("eagar-tsai", *NIST)
        self.assertEqual(r["modelId"], "eagar-tsai-v2")
        # Wave B LA-5: Tier 2 122.5 / 567.7 um; v1 kernel 127.8 / 776.0.
        # P7b (2026-10-14): P1 values 133.1 / 123.9 / 674.6.
        self.assertAlmostEqual(g["width_um"], 110.5, delta=0.5)
        self.assertAlmostEqual(g["depth_um"], 104.4, delta=0.5)
        self.assertAlmostEqual(g["length_um"], 397.8, delta=1.0)
        self.assertEqual(g["extentStatus"], "computed")

    def test_g11_payloads(self):
        g, _ = _geometry("eagar-tsai", "Ti-6Al-4V", 280.0, 1200.0, 70.0, 200.0, 30.0, 120.0)
        # P7b (2026-10-14): Ti-6Al-4V kernel ledger and authority 0.32 (P1: 135.8; Tier 2: 126.7; v1 kernel: 132.6)
        self.assertAlmostEqual(g["width_um"], 131.2, delta=0.5)
        g, _ = _geometry("goldak", "316L Stainless Steel", 370.0, 600.0, 60.0, 25.0, 50.0, 90.0)
        # P7b: 316L authority 0.30 and melting-point k / cp (P1: 183.2; Tier 2: 168.9; v2 kernel: 117.4)
        self.assertAlmostEqual(g["width_um"], 134.8, delta=0.5)

    def test_retired_heat_source_ids_are_refused(self):
        for retired in ("eagar-tsai-v1", "goldak-v1", "goldak-total-power-v2"):
            with self.assertRaisesRegex(ValueError, "Retired LPBF heat-source id"):
                _geometry(retired, *NIST)

    def test_heuristic_width_fallback_is_labelled(self):
        # A cold low-power case: the conduction field has no resolvable liquidus extent.
        g, _ = _geometry("goldak", "Inconel 718", 20.0, 2000.0, 80.0, 23.5, 40, 110)
        self.assertEqual(g["extentStatus"], "heuristic-width-fallback")
        self.assertIn("not a computed isotherm", g["extentNote"])

    def test_width_floor_is_labelled_not_computed(self):
        # The computed half-width is below the 0.55 x beam-diameter floor (rr1 S1: 16 such cases).
        # Wave B LA-5 raised the ET/Goldak field power, so the floored cases are lower-power than at Tier 2
        # (Goldak IN718 50 W and ET Ti64 20 W are computed now).
        # P7b (2026-10-14): the lower IN718 field power (A 0.32, k 29.6) sends the former 40 W Goldak and 30 W
        # Rosenthal cases into the width fallback; the floored cases are re-pinned one step higher in power.
        for source, args in (("goldak", ("Inconel 718", 48.0, 800.0, 80.0, 80.0, 40, 110)),
                             ("eagar-tsai", ("Ti-6Al-4V", 18.0, 800.0, 80.0, 80.0, 40, 110)),
                             ("rosenthal", ("Inconel 718", 40.0, 2000.0, 80.0, 80.0, 40, 110))):
            g, _ = _geometry(source, *args)
            self.assertEqual(g["extentStatus"], "width-floor-applied", (source, g["width_um"]))
            self.assertAlmostEqual(g["width_um"], 44.0, delta=0.05)
            self.assertIn("width floor", g["extentNote"])

    def test_search_box_grows_until_the_isotherm_closes(self):
        # rr1 S1: these lengths were capped by the search box (836.2 / 1535.3 / 1011.7 / 373.1 um);
        # the box now grows and the extents equal the reviewer's unbounded search. Rosenthal values after the P1 bump
        # (2026-10-11, flat absorptivity and no latent factor; Wave B: 1896.2 / 1033.5; Tier 2: 1849.5 / 1011.7 um);
        # Eagar-Tsai and Goldak unchanged by P1.
        # P7b (2026-10-14): IN718 authority 0.32 and melting-point k / cp shorten every pool (P1: 1211.7 / 898.9 /
        # 486.0 / 472.4 um).
        for source, args, length in (("eagar-tsai", ("Inconel 718", 500.0, 1500.0, 40.0, 80.0, 40, 110), 704.8),
                                     ("rosenthal", ("Inconel 718", 370.0, 800.0, 80.0, 80.0, 40, 110), 523.2),
                                     ("rosenthal", ("Inconel 718", 200.0, 1500.0, 40.0, 80.0, 40, 110), 282.9),
                                     ("goldak", ("Inconel 718", 200.0, 3000.0, 40.0, 80.0, 40, 110), 271.6)):
            g, _ = _geometry(source, *args)
            self.assertEqual(g["extentStatus"], "computed", (source, args))
            self.assertAlmostEqual(g["length_um"], length, delta=0.5, msg=(source, args))

    def test_search_box_limit_status_when_the_isotherm_never_closes(self):
        from unittest import mock
        import lpbf_thermal_solver as solver
        # Force the growth loop to give up at once so the limit branch is exercised deterministically.
        original = solver._binary_extent
        with mock.patch.object(solver, "_binary_extent", lambda pred, lo, hi, iters=18: hi):
            g, _ = _geometry("rosenthal", *NIST)
        self.assertEqual(g["extentStatus"], "search-box-limited")
        self.assertIn("lower bound", g["extentNote"])
        self.assertIs(solver._binary_extent, original)


if __name__ == "__main__":
    unittest.main()
