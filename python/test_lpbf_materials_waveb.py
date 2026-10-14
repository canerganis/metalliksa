"""Wave B materials-data fixes (MD-1..MD-7): self-contained regression tests."""
import unittest

import numpy as np

import four_alloy_materials as fam
import in625_thermal_material as in625
import lpbf_material_registry as registry
from lpbf_material_capabilities import capability_for

# Identity digests that MD-1 must NOT move (rising-k alloys keep the 3-row table bit-for-bit). Re-pinned at the P7b
# sourced-constants bump (2026-10-14): the absorptivity authority (IN718 0.32, 316L 0.30, Ti-6Al-4V 0.32) and the
# Ti-6Al-4V liquid row (k_l 29.8, cp_l 930, rho_l 4087, Mohr 2020) move the snapshot, the table shape does not.
UNCHANGED_REVISIONS = {
    "Inconel 718": "8bbceb4e810f",
    "Ti-6Al-4V": "ac61f9564639",
    "316L Stainless Steel": "51f124e66e86",
}


class LegacyTableShapeTest(unittest.TestCase):  # MD-1
    def test_rising_k_alloys_unchanged(self):
        for name, prefix in UNCHANGED_REVISIONS.items():
            m = registry.material(name)
            self.assertEqual(len(m["table"]), 3, name)
            self.assertTrue(m["materialRevisionSha256"].startswith(prefix), name)

    def test_falling_k_alloys_hold_solid_k_to_solidus(self):
        for name in ("AlSi10Mg", "Scalmalloy (Al-Mg-Sc-Zr)"):
            m = registry.material(name)
            k_rt = m["table"][0][2]
            self.assertEqual(len(m["table"]), 4)
            for t in (353.15, 600.0, m["solidus_K"]):
                self.assertAlmostEqual(float(registry.property_at(m, t, 2)), k_rt, places=9)
            mid = 0.5 * (m["solidus_K"] + m["liquidus_K"])
            self.assertLess(float(registry.property_at(m, mid, 2)), k_rt)

    def test_copper_solidus_conductivity_is_sourced(self):
        m = registry.material("Pure Copper (Cu-OF)")
        # Ho, Powell & Liley 1972: 352 W/(m K) at 1000 K, 328 at the melting point.
        self.assertAlmostEqual(float(registry.property_at(m, 1000.0, 2)), 352.0, delta=0.02 * 352.0)
        self.assertAlmostEqual(float(registry.property_at(m, m["solidus_K"], 2)), 328.0, places=6)
        self.assertEqual(m["table"][1][0], m["solidus_K"])
        self.assertEqual(m["table"][2][0], m["liquidus_K"])

    def test_density_and_cp_lines_unchanged(self):
        m = registry.material("AlSi10Mg")
        p = fam.thermal_props("alsi10mg")
        tl = m["liquidus_K"]
        for t in (300.0, 500.0, m["solidus_K"]):
            f = (t - 273.15) / (tl - 273.15)
            rho = p["density_kg_m3"] + (p["density_liquid_kg_m3"] - p["density_kg_m3"]) * f
            self.assertAlmostEqual(float(registry.property_at(m, t, 1)), rho, places=6)


class SurfaceTensionSlopeTest(unittest.TestCase):  # MD-2, MD-5
    def test_one_value_per_alloy(self):
        for aid in fam.FOUR_ALLOY_IDS:
            self.assertEqual(fam.thermal_props(aid)["d_gamma_dT_N_mK"],
                             fam.marangoni_props(aid)["d_gamma_dT_pure_N_mK"], aid)

    def test_provenance_labels(self):
        in718 = fam.PROPERTY_PROVENANCE["in718"]["d_gamma_dT_N_mK"]
        self.assertEqual(in718["value"], fam.thermal_props("in718")["d_gamma_dT_N_mK"])
        self.assertIn("10.2355/isijinternational.46.623", in718["source"])
        self.assertEqual(in718["commercialMeasured_N_mK"], -0.00011)
        # P7b (2026-10-14): the AlSi10Mg slope is the Seimiya 2026 Table 1 EML value (binary Al-Si proxy, cited).
        al = fam.PROPERTY_PROVENANCE["alsi10mg"]["d_gamma_dT_N_mK"]
        self.assertEqual(al["basis"], "cited-primary")
        self.assertIn("Seimiya", al["source"])
        self.assertEqual(al["value"], -0.000103)

    def test_capability_exposes_cross_model_slope(self):
        cap = capability_for("in718")
        block = cap["crossModelDGammaDT"]
        self.assertEqual(block["transient"], block["marangoniPure"])
        self.assertEqual(block["provenance"]["basis"], "cited-primary")


class LiteratureFixtureTest(unittest.TestCase):  # MD-3 (remaining after tier-2)
    def test_wd_anchors_are_measurements(self):
        for case in fam.LITERATURE_MELT_POOL_CASES:
            self.assertNotIn(case["doi"], ("10.1063/1.1712881", "10.1016/j.jmatprotec.2014.04.021"))
            if case["check"] == "wd":
                self.assertEqual(case["widthDepthBasis"], "published-measurement", case["id"])

    def test_rosenthal_doi(self):
        ti = next(c for c in fam.LITERATURE_MELT_POOL_CASES if c["alloy_id"] == "ti6al4v")
        self.assertEqual(ti["doi"], "10.1115/1.4018624")
        self.assertEqual(ti["check"], "class")


class In625ExtendedConsistencyTest(unittest.TestCase):  # MD-4
    def test_reported_constants_are_integrated(self):
        e = in625.in625_extended_thermal_at_kelvin(1600.0)
        self.assertEqual(e["latentHeatFusion_J_kg"], in625.LATENT_HEAT_J_KG)
        self.assertEqual(e["liquidCp_J_kgK"], in625.LIQUID_CP_J_KGK)

    def test_liquid_cp_continuous(self):
        below = in625.in625_extended_thermal_at_kelvin(in625.IN625_LIQUIDUS_K)
        above = in625.in625_extended_thermal_at_kelvin(in625.IN625_LIQUIDUS_K + 1e-3)
        self.assertEqual(below["specificHeat_J_kgK"], above["specificHeat_J_kgK"])
        hi = in625.in625_extended_thermal_at_kelvin(2000.0)
        self.assertAlmostEqual(hi["specificEnthalpy_J_kg"] - below["specificEnthalpy_J_kg"],
                               in625.LIQUID_CP_J_KGK * (2000.0 - in625.IN625_LIQUIDUS_K), delta=1e-6)

    def test_density_matches_spec_table(self):
        self.assertEqual(in625.in625_extended_thermal_at_kelvin(in625.IN625_SOLIDUS_K)["density_kg_m3"], 8220.0)


class LabelTest(unittest.TestCase):  # MD-6, MD-7
    def test_u95_budgets_labelled_assumed(self):
        self.assertEqual(fam.FOUR_ALLOY_U95_BUDGET_BASIS, "assumed-engineering-budget-not-derived")
        self.assertEqual(in625.IN625_U95_BUDGET_BASIS, "assumed-engineering-budget-not-derived")
        self.assertAlmostEqual(in625.IN625_U95_SOLID_SOURCE_LIMIT_K, 1255.15)
        self.assertIn("assumed engineering budget",
                      in625.in625_transient_material_specification()["uncertaintyNote"])

    def test_emissivity_labelled(self):
        legacy = next(row for row in registry.catalog() if row["name"] == "AlSi10Mg")
        self.assertIn("emissivity 0.35 is an assumed screening constant", legacy["note"])
        self.assertEqual(capability_for("alsi10mg")["emissivityProvenance"]["basis"], "assumed-screening-constant")
        self.assertEqual(registry.material("AlSi10Mg")["emissivity"], 0.35)


if __name__ == "__main__":
    unittest.main()
