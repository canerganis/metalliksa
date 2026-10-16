"""SOL-T software acceptance (Amendment 4 installation); synthetic inputs only, no measured rows.

Run: python -B test_sol_t_installation.py   (``--write-d13-fixture`` regenerates the committed TS fixture).
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import four_alloy_materials as fm
import quantity_envelope as qe
from lpbf_material_registry import contain_front_metrics, material
from lpbf_thermal_solver import SECONDARY_THERMOPHYSICAL_DB, calculate_meltpool_physics

ROOT = Path(__file__).resolve().parents[1]
D13_FIXTURE = ROOT / "tests/fixtures/quantity-envelope/sol-t-d13.json"
PAIRS = {"ti6al4v": (1877.15, 1933.15), "in718": (1533.15, 1609.15),
         "ss316l": (1658.15, 1723.15), "alsi10mg": (840.15, 872.15),
         "in625": (1563.15, 1623.15)}
PROVENANCE_KEY = {"ti6al4v": "ti6al4v", "in718": "in718", "ss316l": "ss316l", "alsi10mg": "alsi10mg",
                  "in625": "Inconel 625"}
D13_VALUES = {"thermalGradient_K_m": 2e7, "solidificationRate_m_s": .2, "coolingRate_K_s": 4e6}


def d13_fixture():
    """The committed synthetic D13 container: AlSi10Mg (family transfer), synthetic values and field identity."""
    _, envelope = contain_front_metrics(dict(D13_VALUES), material("alsi10mg"), {"power_W": 220}, "synthetic-field")
    return envelope


class SolTInstallation(unittest.TestCase):
    def test_all_five_endpoint_pairs_and_admission_identity(self):
        records = json.loads((ROOT / "docs/research/sol_t_admission_records.json").read_text())["records"]
        self.assertEqual({record["id"] for record in records}, set(PAIRS))
        for record in records:
            aid = record["id"]
            props = fm.thermal_props(aid) if aid != "in625" else SECONDARY_THERMOPHYSICAL_DB["Inconel 625"]
            self.assertEqual((props["solidus_C"] + 273.15, props["liquidus_C"] + 273.15), PAIRS[aid])
            self.assertEqual(tuple(record["endpoint_K"]), PAIRS[aid])
            parent = fm.endpoint_admission(aid)
            self.assertEqual(parent["record"], record)
            canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            self.assertEqual(parent["recordSha256"], hashlib.sha256(canonical.encode()).hexdigest())
            self.assertEqual(parent["sourceEvidenceKind"], "Literature estimate")
            self.assertEqual(parent["kind"], "alloyTransfer" if aid in ("alsi10mg", "ss316l") else "modelConvention")
            self.assertEqual(parent["status"], "extrapolated" if aid in ("alsi10mg", "ss316l") else "admitted-convention")
            self.assertTrue(parent["sourceLocator"])
            self.assertIn(record["transfer"], parent["scope"])
        ti = fm.endpoint_admission("ti6al4v")
        for text in ("Cezairliyan", "1942.6", "8 K", "9.45 K", "1933.15"):
            self.assertIn(text, ti["scope"])

    def test_ledger_registry_and_provenance_carry_the_same_pair(self):
        for aid, (ts, tl) in PAIRS.items():
            with self.subTest(alloy=aid):
                prov = fm.PROPERTY_PROVENANCE[PROVENANCE_KEY[aid]]
                self.assertEqual((prov["solidus_C"]["value"] + 273.15, prov["liquidus_C"]["value"] + 273.15), (ts, tl))
                self.assertEqual(prov["liquidus_C"]["basis"], "admitted-nominal-convention")
                self.assertEqual(prov["liquidus_C"]["source"], f"SOL-T-A4-{aid}")
                if aid != "in625":
                    snapshot = material(aid)
                    self.assertEqual((snapshot["solidus_K"], snapshot["liquidus_K"]), (ts, tl))
                    self.assertIn(tl, [row[0] for row in snapshot["table"]])
        for aid in ("ti6al4v", "alsi10mg"):
            num = fm.PROPERTY_LEDGER[aid]["numeric"]
            self.assertEqual((num["T_sol_K"], num["T_liq_K"]), PAIRS[aid])
        # Al ledger pins and arms recomputed at the new liquidus (rounded as recorded).
        al = fm.PROPERTY_LEDGER["alsi10mg"]["numeric"]
        for t0, pins in ((293.15, al["pins_T0_293_15K"]), (353.15, al["pins_T0_353_15K"])):
            k = fm.kernel_properties("alsi10mg", t0)
            self.assertEqual(round(k["kernel_conductivity_W_mK"], 3), pins["K_W_mK"])
            self.assertEqual(round(k["kernel_specific_heat_J_kgK"], 2), pins["cp_J_kgK"])
            self.assertEqual(float(f"{k['alpha_m2_s']:.3e}"), pins["alpha_m2_s"])
        for state, key in (("AB_unrelaxed", "AB_unrelaxed_K_W_mK"), ("HT_low", "HT_low_K_W_mK"), ("HT", "HT_K_W_mK")):
            self.assertEqual(round(fm.kernel_properties("alsi10mg", 293.15, state=state)["kernel_conductivity_W_mK"], 3),
                             al["arms"][key])
        cp = fm.kernel_properties("alsi10mg", 293.15)["kernel_specific_heat_J_kgK"]
        for latent, value in al["arms"]["enthalpy_consistent_cp_J_kgK"].items():
            self.assertEqual(round(cp + float(latent) / (872.15 - 293.15), 1), value)
        # SOL-T changes no density: the served liquid density stays the pre-SOL-T value.
        self.assertEqual(fm.thermal_props("alsi10mg")["density_liquid_kg_m3"], 2393.8)

    def test_admission_is_copied_and_unknown_alloy_refused(self):
        parent = fm.endpoint_admission("in718")
        parent["record"]["endpoint_K"][0] = 1
        self.assertEqual(fm.endpoint_admission("in718")["record"]["endpoint_K"][0], 1533.15)
        self.assertIsNone(fm.endpoint_admission("unrecognised"))
        self.assertIsNone(fm.endpoint_input("unrecognised", 1000.0))

    def test_registry_binds_parent_but_user_tables_do_not_inherit_it(self):
        for aid in ("ti6al4v", "in718", "ss316l", "alsi10mg"):
            snapshot = material(aid)
            self.assertEqual(snapshot["endpointAdmission"], fm.endpoint_admission(aid))
            supplied = {k: copy.deepcopy(snapshot[k]) for k in
                        ("solidus_K", "liquidus_K", "boiling_K", "latentHeat_J_kg", "absorptivity",
                         "emissivity", "dGamma_dT", "table", "source")}
            self.assertNotIn("endpointAdmission", material(aid, supplied))
            with self.assertRaises(ValueError):
                material(aid, {**supplied, "endpointAdmission": snapshot["endpointAdmission"]})

    def test_d13_admitted_values_are_labelled_per_value(self):
        m = material("in718")
        labelled, envelope = contain_front_metrics(dict(D13_VALUES), m, {"power_W": 220}, "synthetic-field")
        self.assertEqual(qe.envelope_problems(envelope), [])
        self.assertEqual(labelled, D13_VALUES)
        self.assertEqual(envelope["moduleEvidenceCeiling"], "screening-only")
        self.assertEqual(envelope["parentBindings"]["materialRevisionSha256"], m["materialRevisionSha256"])
        self.assertEqual(envelope["parentBindings"]["selectedConvention"], fm.endpoint_admission("in718"))
        for key, q in envelope["quantities"].items():
            self.assertEqual(q["status"], "computed")
            self.assertEqual(q["value"], D13_VALUES[key])
            self.assertEqual(q["sourceEvidenceKind"], "Literature estimate")
            self.assertEqual(q["labelSources"], [fm.endpoint_admission("in718")["sourceLocator"]])
            self.assertIn(fm.endpoint_admission("in718")["scope"], q["assumptions"])
            self.assertEqual(q["identity"]["model"], "synthetic-field")
            self.assertNotEqual(q["physicalValidation"]["status"], "validated")

    def test_d13_missing_or_changed_parent_gives_null_with_the_parent_reason(self):
        base = material("ss316l")
        no_parent = dict(base)
        no_parent.pop("endpointAdmission")
        moved = dict(base, liquidus_K=base["liquidus_K"] + 1.0)
        user = dict(base, quality="user-supplied-unverified")
        for m in (no_parent, moved, user):
            refused, envelope = contain_front_metrics(dict(D13_VALUES), m, {}, "synthetic-field")
            self.assertEqual(qe.envelope_problems(envelope), [])
            self.assertTrue(all(v is None for v in refused.values()))
            self.assertIsNone(envelope["parentBindings"]["selectedConvention"])
            for q in envelope["quantities"].values():
                self.assertEqual(q["status"], "unavailable")
                self.assertIsNone(q["sourceEvidenceKind"])
                self.assertEqual(q["reasons"][0]["code"], "missing-source-constant")
                self.assertEqual(q["reasons"][0]["parent"], {"input": "liquidus_K", "kind": "declaredAssumption"})

    def test_d13_admitted_but_absent_event_mean_is_unavailable(self):
        _, envelope = contain_front_metrics({k: None for k in D13_VALUES}, material("ti6al4v"), {}, "synthetic-field")
        self.assertEqual(qe.envelope_problems(envelope), [])
        for q in envelope["quantities"].values():
            self.assertEqual(q["status"], "unavailable")
            self.assertEqual(q["reasons"][0]["code"], "insufficient-sample-support")

    def test_d13_identities_never_embed_the_served_fingerprint(self):
        import lpbf_simulation
        fingerprint = lpbf_simulation.implementation_fingerprint()
        sources = "".join((ROOT / "python" / name).read_text(encoding="utf-8")
                          for name in ("lpbf_simulation.py", "lpbf_openfoam.py"))
        self.assertNotIn("contain_front_metrics(best, m, p, implementation_fingerprint())", sources)
        self.assertIn("linear-liquidus-crossing-v1\")", sources)
        _, envelope = contain_front_metrics(dict(D13_VALUES), material("in718"), {}, "lpbf-transient:enthalpy-fv-6")
        self.assertNotIn(fingerprint, json.dumps(envelope))

    def test_committed_d13_fixture_equals_the_producer(self):
        self.assertEqual(json.loads(D13_FIXTURE.read_text(encoding="utf-8")), d13_fixture(),
                         "Regenerate with python -B test_sol_t_installation.py --write-d13-fixture")

    def test_front_stays_null_until_sol_c_with_admitted_input(self):
        for name, aid in (("AlSi10Mg", "alsi10mg"), ("Ti-6Al-4V", "ti6al4v"), ("316L Stainless Steel", "ss316l")):
            result = calculate_meltpool_physics(name, 220, 900, 80, 80, 40, 100,
                                               heat_source="rosenthal", include_process_map=False)
            front = result["solidificationKinetics"]
            self.assertEqual(front["modelId"], "solidification-front-v3")
            record = front["inputProvenance"]["liquidus_K"]
            self.assertEqual(record["kind"], fm.endpoint_admission(aid)["kind"])
            self.assertEqual(record["sourceEvidenceKind"], "Literature estimate")
            self.assertEqual(record["defaultValue"], PAIRS[aid][1])
            self.assertTrue(all(q["value"] is None for q in front["quantities"].values()))
            self.assertEqual(result["materialEvidence"]["liquidusParent"], fm.endpoint_admission(aid))

    def test_changed_endpoint_cannot_inherit_the_nominal_admission(self):
        for override in ({"liquidus_C": 600}, {"solidus_C": 560}):
            result = calculate_meltpool_physics("AlSi10Mg", 220, 900, 80, 80, 40, 100,
                                               heat_source="rosenthal", include_process_map=False,
                                               prop_overrides=override)
            self.assertIsNone(result["materialEvidence"]["liquidusParent"])


if __name__ == "__main__":
    if "--write-d13-fixture" in sys.argv:
        D13_FIXTURE.write_text(json.dumps(d13_fixture(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
                               newline="\n")
        print(f"wrote {D13_FIXTURE}")
    else:
        unittest.main()
