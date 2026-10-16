"""R-CTX: the P8 research context (integration contract 2026-10-15, 3.4, 3.8, 10.3).

R-CTX-1 the 3.8 tuple literals for Ti-6Al-4V and AlSi10Mg at 20 C. R-CTX-2 float.hex equality of K, cp, rho_k and
alpha with the served internals, captured by wrapping resolve_conduction_kernel during calculate_meltpool_physics, for
five alloys and three kernels. R-CTX-3 a build-job snapshot equals the nominal tuple for the four Build Job alloys, a
tampered hash gives PROPERTY_SNAPSHOT_MISMATCH, a wrong alloy gives alloy-material-mismatch. R-CTX-4 SI conversions by
float.hex. Every test runs with calculate_meltpool_physics patched to raise; only R-CTX-2 calls the served original
itself, outside research code, to read the served internals.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lpbf_research_context as research_context  # noqa: E402
import lpbf_research_models as models  # noqa: E402
import lpbf_thermal_solver  # noqa: E402
from four_alloy_materials import ALLOY_MATERIALS  # noqa: E402
from test_lpbf_research_harness import ResearchTestCase, request  # noqa: E402

SERVED = research_context.served_property_provider()
FIVE_ALLOYS = ("Ti-6Al-4V", "AlSi10Mg", "Inconel 718", "316L Stainless Steel", "Inconel 625")
KERNELS = ("rosenthal", "eagar-tsai", "goldak")
BUILD_JOB_ALLOYS = ("alsi10mg", "in718", "ss316l", "ti6al4v")


def _context(material, **process):
    body = request(material=material, process=process or None)
    return research_context.resolve(models.check_request(json.dumps(body), SERVED), SERVED)


class TupleLiterals(ResearchTestCase):  # R-CTX-1
    def test_ti64_tuple_at_20_c(self):
        t = _context("Ti-6Al-4V").conduction
        self.assertEqual((t.conductivity_W_mK, t.specificHeat_J_kgK, t.density_kg_m3, t.diffusivity_m2_s,
                          t.wallAbsorptance, t.liquidus_K - 273.15),
                         (16.44854, 645.74021, 4430.0, 5.749972908328388e-06, 0.32, 1660.0))
        self.assertEqual(t.propertyConvention, "kernel-ledger-kirchhoff")

    def test_alsi10mg_tuple_at_20_c(self):
        t = _context("AlSi10Mg").conduction
        self.assertEqual((t.conductivity_W_mK, t.specificHeat_J_kgK, t.density_kg_m3, t.diffusivity_m2_s,
                          t.wallAbsorptance, t.liquidus_K - 273.15),
                         (152.63126079447323, 1020.8488773747841, 2696.0, 5.545773756739041e-05, 0.3, 599.0))  # SOL-T re-pin
        self.assertEqual(t.propertyConvention, "kernel-ledger-kirchhoff")

    def test_context_is_immutable_and_hands_out_copies(self):
        ctx = _context("Ti-6Al-4V")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            ctx.power_W = 1.0  # type: ignore[misc]
        with self.assertRaises(TypeError):
            ctx.properties["density_kg_m3"] = 1.0  # type: ignore[index]
        copy = ctx.property_dict()
        copy["density_kg_m3"] = 1.0
        self.assertEqual(ctx.properties["density_kg_m3"], 4430.0)
        self.assertEqual(len(ctx.propertySetSha256), 64)


class ServedInternals(ResearchTestCase):  # R-CTX-2
    def test_float_hex_equality_with_the_served_kernel_tuple(self):
        original = lpbf_thermal_solver.resolve_conduction_kernel
        for material in FIVE_ALLOYS:
            research = _context(material).conduction
            for kernel in KERNELS:
                with self.subTest(material=material, kernel=kernel):
                    seen = []

                    def capture(*args, **kwargs):
                        out = original(*args, **kwargs)
                        seen.append(out)
                        return out
                    with mock.patch.object(lpbf_thermal_solver, "resolve_conduction_kernel", side_effect=capture):
                        self.served_calculate_meltpool_physics(material, 200.0, 800.0, 80.0, 20.0, heat_source=kernel)
                    self.assertGreaterEqual(len(seen), 1)
                    k_th, cp, rho_k = seen[0][:3]
                    alpha = k_th / (rho_k * cp)
                    self.assertEqual(
                        (k_th.hex(), float(cp).hex(), float(rho_k).hex(), alpha.hex()),
                        (research.conductivity_W_mK.hex(), research.specificHeat_J_kgK.hex(),
                         research.density_kg_m3.hex(), research.diffusivity_m2_s.hex()))


class BuildJobSnapshot(ResearchTestCase):  # R-CTX-3
    def _snapshot_request(self, alloy_id, sha=None, material=None):
        material = material or ALLOY_MATERIALS[alloy_id]["thermal"]
        _, real = SERVED.material_snapshot(alloy_id)
        return request(material=material, property_context={"kind": "build-job-snapshot", "alloyId": alloy_id,
                                                            "materialPropertySha256": sha or real})

    def test_snapshot_resolves_to_the_nominal_tuple_for_the_four_build_job_alloys(self):
        for alloy_id in BUILD_JOB_ALLOYS:
            with self.subTest(alloy=alloy_id):
                body = self._snapshot_request(alloy_id)
                ctx = research_context.resolve(models.check_request(json.dumps(body), SERVED), SERVED)
                nominal = _context(ALLOY_MATERIALS[alloy_id]["thermal"])
                self.assertTrue(ctx.tupleEqualsNominal)
                self.assertEqual(ctx.conduction.hex_tuple(), nominal.conduction.hex_tuple())
                self.assertEqual(ctx.propertyContextKind, "build-job-snapshot")

    def test_tampered_hash_is_a_property_snapshot_mismatch(self):
        body = self._snapshot_request("ti6al4v", sha="0" * 64)
        with self.assertRaises(models.Refused) as caught:
            models.check_request(json.dumps(body), SERVED)
        self.assertEqual(caught.exception.code, "PROPERTY_SNAPSHOT_MISMATCH")
        self.assertEqual([(p["pointer"], p["rule"]) for p in caught.exception.problems],
                         [("/propertyContext/materialPropertySha256", "snapshot-hash-mismatch")])

    def test_wrong_alloy_is_an_alloy_material_mismatch(self):
        body = self._snapshot_request("in718", material="Ti-6Al-4V")
        with self.assertRaises(models.Refused) as caught:
            models.check_request(json.dumps(body), SERVED)
        self.assertEqual(caught.exception.code, "RESEARCH_REQUEST_INVALID")
        self.assertEqual([(p["pointer"], p["rule"]) for p in caught.exception.problems],
                         [("/propertyContext/alloyId", "alloy-material-mismatch")])


class SiConversions(ResearchTestCase):  # R-CTX-4
    def test_si_conversions_by_float_hex(self):
        ctx = _context("Ti-6Al-4V")
        self.assertEqual(ctx.speed_m_s.hex(), (0.8).hex())
        self.assertEqual(ctx.beamDiameter_m.hex(), (8e-05).hex())
        self.assertEqual(ctx.preheat_K.hex(), (293.15).hex())
        self.assertEqual(ctx.power_W.hex(), (200.0).hex())

    def test_conversions_divide_exactly_as_the_p8_spec_says(self):
        si = research_context.si_process({"laserPower_W": 200, "scanSpeed_mm_s": 950, "beamDiameter_um": 70,
                                          "preheatTemp_C": 80})
        self.assertEqual(si["speed_m_s"].hex(), (950 / 1000).hex())
        self.assertEqual(si["beamDiameter_m"].hex(), (70 / 1e6).hex())
        self.assertEqual(si["preheat_K"].hex(), (80.0 + 273.15).hex())


if __name__ == "__main__":
    unittest.main()
