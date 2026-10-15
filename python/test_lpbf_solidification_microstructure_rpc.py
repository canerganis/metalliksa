"""RPC "solidification-microstructure": screening-field path (no CFD) from lpbf_thermal_solver.

The Microstructure Lab sends materialName + process inputs; Python resolves the alloy and returns the
projection of thermal.solidificationKinetics. Unusable inputs give status "unavailable" (no defaults, no
surrogate alloy). The legacy cfdResult path is kept only when a cfdResult is supplied.
"""
import collections
import math
import unittest

import lpbf_worker_rpc
from lpbf_solidification_microstructure import SCREENING_FIELD_SCOPE
from lpbf_thermal_solver import calculate_meltpool_physics

FALLBACK_REASON = (
    "thermal.solidificationKinetics used the tail-length heuristic (G = ΔT/x_rear, R = v·cosθ), "
    "not the liquidus field map; treat G/R/PDAS/SDAS as screening only"
)

DEGENERATE_FLOOR_REASON = (
    "solidification front degenerate: floor-clamped R/cooling "
    "(R <= 1e-4 m/s or cooling <= 1 K/s), not a computed value"
)

# P6 containment (2026-10-11): the former 285 W / 960 mm/s base case now serves null G/R (the served depth comes
# from the Fabbro keyhole leg), so the available base case is the conduction point 150 W / 1200 mm/s.
IN718_285 = {
    "materialName": "Inconel 718",
    "power_W": 150,
    "speed_mm_s": 1200,
    "beamDiameter_um": 80,
    "preheat_C": 80,
    "layerThickness_um": 40,
    "hatch_um": 110,
    "heatSource": "rosenthal",
}


def rpc(params, **extra):
    return lpbf_worker_rpc._rpc_solidification_microstructure({"payload": {"params": params, **extra}})


class SolidificationMicrostructureRpcTest(unittest.TestCase):
    def assert_null_envelope(self, out, code=None):
        from quantity_envelope import envelope_problems
        self.assertEqual(out["schema"], "lpbf-solidification-microstructure-2")
        self.assertEqual(out["status"], "unavailable")
        self.assertEqual(envelope_problems(out), [])
        self.assertNotIn("G_K_m", out)
        for q in out["quantities"].values():
            self.assertIsNone(q["value"])
            if code is not None:
                self.assertIn(code, {r["code"] for r in q["reasons"]})

    def test_all_fields_are_copied_from_thermal_for_each_source(self):
        for source in ("rosenthal", "goldak", "eagar-tsai"):
            with self.subTest(source=source):
                out = rpc({**IN718_285, "heatSource": source})
                thermal = calculate_meltpool_physics("Inconel 718", 150, 1200, 80, 80, 40, 110, heat_source=source)
                self.assert_null_envelope(out)
                self.assertEqual(out["quantities"], thermal["solidificationKinetics"]["quantities"])
                self.assertEqual(out["inputProvenance"], thermal["solidificationKinetics"]["inputProvenance"])
                self.assertNotIn("morphologyBands_G_over_R", out)

    def test_keyhole_reason_survives_projection(self):
        out = rpc({**IN718_285, "power_W": 285, "speed_mm_s": 960})
        self.assert_null_envelope(out)
        self.assertIn("keyhole-field-inconsistent", {r["code"] for r in out["quantities"]["thermalGradient"]["reasons"]})

    def test_default_heat_source_and_material_payload(self):
        params = {k: v for k, v in IN718_285.items() if k != "heatSource"}
        expected = rpc(IN718_285)
        self.assertEqual(rpc(params)["quantities"], expected["quantities"])
        self.assertEqual(rpc(params, material={"liquidus_C": 10, "k": 1e8})["quantities"], expected["quantities"])

    def test_required_inputs_never_get_defaults(self):
        for key in IN718_285:
            if key == "heatSource":
                continue
            with self.subTest(key=key):
                params = dict(IN718_285)
                del params[key]
                self.assert_null_envelope(rpc(params), "nonphysical-input")

    def test_nonphysical_and_unknown_inputs_refused(self):
        for patch in ({"power_W": 0}, {"speed_mm_s": float("nan")}, {"beamDiameter_um": True},
                      {"preheat_C": -274}, {"preheat_C": 3000}, {"materialName": "unknown"},
                      {"heatSource": "unknown"}):
            with self.subTest(patch=patch):
                self.assert_null_envelope(rpc({**IN718_285, **patch}), "nonphysical-input")

    def test_cfd_key_always_quarantined_even_if_empty(self):
        for cfd in (None, {}, {"solidificationMicrostructure": {"meanG_K_m": 1e6, "meanR_m_s": 0.1}}):
            self.assert_null_envelope(rpc(IN718_285, cfdResult=cfd), "quarantined-legacy-path")

    def test_projection_copies_envelope_without_legacy_aliases(self):
        import copy
        from lpbf_solidification_microstructure import project_build_job_microstructure
        thermal = calculate_meltpool_physics("Inconel 718", 150, 1200, 80, 80, 40, 110)
        snapshot = copy.deepcopy(thermal)
        out = project_build_job_microstructure(thermal)
        out["quantities"]["thermalGradient"]["reasons"].clear()
        self.assertEqual(thermal, snapshot)
        self.assert_null_envelope(project_build_job_microstructure({"solidificationKinetics": {"thermalGradient_G_K_m": 1e6}}))
