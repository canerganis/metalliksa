#!/usr/bin/env python3
"""SOL-A1 solidification front container (2026-10-15): self-contained regression tests.

Authority: docs/research/SPEC_solidification_integration_2026-10-15.md (Revision 1 and the lead-check fixes of
759a4cb7: 4.1 items 5 to 7, 4.2, 4.3 items 5 and 8, 6.2, 6.3, 7.4) and SPEC_solidification_2026-10-14.md Amendment 3.
Synthetic process inputs on the served solver and analytic fields only; no measured datum is read. Nothing here is a
physical test: these are software invariants of the blanket-null contract.

    python -B -m unittest test_solidification_front
"""
import json
import math
import unittest

import quantity_envelope as qe
import solidification_front as sf
from lpbf_thermal_solver import THERMOPHYSICAL_DB, calculate_meltpool_physics

SERVED_NAMES = {"ti6al4v": "Ti-6Al-4V", "alsi10mg": "AlSi10Mg", "in718": "Inconel 718", "in625": "Inconel 625",
                "ss316l": "316L Stainless Steel"}
KERNELS = ("rosenthal", "eagar-tsai", "goldak")
# Synthetic process points: 150 W / 1200 mm/s (conduction isotherm depth for the four authority alloys) and
# 370 W / 600 mm/s (Fabbro keyhole leg for most alloys); the keyhole reason is checked against the served cavity.
POINTS = ((150.0, 1200.0), (370.0, 600.0))
FRONT_NAMES = ("thermalGradient", "normalSpeed", "coolingRate", "gOverR", "pdas", "sdas", "morphology",
               "solidStateTransformation")
RETIRED = ("hunt_morphology", "hunt_lu_pdas_um", "HUNT_LU_A_SI", "kirkwood_sdas_um", "phase_transformation_note",
           "TI64_MARTENSITE_K_S", "G_OVER_R_PLANAR", "G_OVER_R_CELLULAR", "G_OVER_R_COLUMNAR", "HUNT_DOI",
           "AHMED_RACK_DOI", "pdas_alloy_sourced", "PDAS_BASIS", "PDAS_NO_COEFFICIENTS_REASON",
           "SDAS_UNAVAILABLE_REASON", "INTERFACE_LABEL", "UNAVAILABLE_KEYHOLE_LEG", "UNAVAILABLE_FEW_SAMPLES",
           "GRADIENT_SOURCE_CONDUCTION_INTERFACE", "_DISCLAIMER", "_unavailable")
FORMER_FLAT_KEYS = ("thermalGradient_G_K_m", "solidificationRate_R_m_s", "coolingRate_K_s", "g_over_r_ratio",
                    "microstructureMorphology", "primaryDendriteArmSpacing_PDAS_um", "pdasBand_um",
                    "secondaryDendriteArmSpacing_SDAS_um", "phaseTransformation", "unavailableReason", "interface",
                    "disclaimer", "doi", "gradientSource", "usedFieldMap", "tail", "bottom", "frontPointCount")
OLD_DOIS = ("10.1016/0025-5416(84)90201-5", "10.1016/S0921-5093(97)00802-2")


def _run(name, power, speed, kernel, **kw):
    return calculate_meltpool_physics(name, power, speed, 80.0, 80.0, 40.0, 100.0, heat_source=kernel, **kw)


def _leaves(obj, path=()):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _leaves(value, path + (str(key),))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _leaves(value, path + (f"[{index}]",))
    else:
        yield path, obj


def _keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _keys(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _keys(value)


def ra4_problems(container):
    """RA4 (contract 4.1 items 5 and 6): no text key and no free sentence from a manifest producer. A string leaf
    with whitespace is allowed only at sources[].locator and as a closed source-label value (sourceEvidenceKind)."""
    problems = [f"text key at {key}" for key in _keys(container) if key == "text"]
    for path, value in _leaves(container):
        if not isinstance(value, str) or not any(ch.isspace() for ch in value):
            continue
        if len(path) >= 3 and path[-1] == "locator" and path[-3] == "sources":
            continue
        if path[-1] == "sourceEvidenceKind" and value in qe.SOURCE_EVIDENCE_KINDS:
            continue
        problems.append(f"{'.'.join(path)}: {value!r}")
    return problems


def _plain_field(x, y, z):
    raise AssertionError("SOL-A1 never samples the field")


class RegistryLiterals(unittest.TestCase):
    """The manifest file cannot import quantity_envelope; its literal copies must equal the registry."""

    def test_served_liquidus_kinds_equal_the_registry(self):
        kinds = {alloy: entry["kind"] for alloy, entry in sf.SERVED_LIQUIDUS_PROVENANCE.items()}
        self.assertEqual(kinds, qe.SERVED_LIQUIDUS_INPUT_KINDS)
        for entry in sf.SERVED_LIQUIDUS_PROVENANCE.values():
            self.assertIn(entry["kind"], qe.UNSOURCED_INPUT_KINDS)

    def test_front_definitions_and_units_are_registered(self):
        self.assertEqual(tuple(sf.FRONT_QUANTITIES), FRONT_NAMES)
        for name, (definition, unit) in sf.FRONT_QUANTITIES.items():
            self.assertIn(definition, qe.QUANTITY_DEFINITIONS, name)
            self.assertEqual(qe.QUANTITY_DEFINITIONS[definition]["unit"], unit, name)

    def test_emitted_reason_codes_and_literals_are_registered(self):
        self.assertTrue(set(sf.EMITTED_REASON_CODES) <= set(qe.REASON_CODES))
        self.assertEqual(sf.ENVELOPE_SCHEMA, qe.ENVELOPE_SCHEMA)
        self.assertEqual(sf.MODULE_EVIDENCE_CEILING, qe.MODULE_EVIDENCE_CEILING)
        self.assertIn(sf.MODULE_MATURITY, qe.MODULE_MATURITIES)
        self.assertEqual(sf.CANONICAL_ALLOY_IDS, qe.CANONICAL_ALLOY_IDS)

    def test_model_id_is_v2(self):
        self.assertEqual(sf.MODEL_ID, "solidification-front-v2")


class BlanketNullContainer(unittest.TestCase):
    """Contract 4.3 item 8 and 7.4: every default front quantity is null for all five alloys at SOL-A1."""

    @classmethod
    def setUpClass(cls):
        cls.results = {(alloy, kernel, point): _run(name, *point, kernel)
                       for alloy, name in SERVED_NAMES.items() for kernel in KERNELS for point in POINTS}

    def test_the_payload_passes_the_production_envelope_validator(self):
        for key, result in self.results.items():
            self.assertEqual(qe.envelope_problems(result, module_maturity="Research"), [], key)
            self.assertEqual(len(qe.find_containers(result)), 1, key)

    def test_every_front_quantity_is_null_without_a_label_or_source(self):
        for key, result in self.results.items():
            container = result["solidificationKinetics"]
            self.assertEqual(tuple(container["quantities"]), FRONT_NAMES, key)
            self.assertEqual(container["modelId"], sf.MODEL_ID)
            self.assertEqual(container["alloyId"], key[0])
            for name, q in container["quantities"].items():
                self.assertEqual(q["status"], "unavailable", (key, name))
                self.assertIsNone(q["value"], (key, name))
                self.assertIsNone(q["sourceEvidenceKind"], (key, name))
                self.assertEqual(q["sources"], [], (key, name))
                self.assertTrue(q["reasons"], (key, name))

    def test_the_liquidus_parent_and_its_kind_are_named(self):
        for (alloy, kernel, point), result in self.results.items():
            container = result["solidificationKinetics"]
            served = sf.SERVED_LIQUIDUS_PROVENANCE[alloy]
            record = container["inputProvenance"]["liquidus_K"]
            self.assertEqual(record["kind"], served["kind"])
            self.assertEqual(record["label"], served["kind"])
            self.assertEqual(record["sourceEvidenceKind"], "Unresolved")
            self.assertEqual(record["declarationLocator"], served["declarationLocator"])
            self.assertEqual(record["defaultValue"], THERMOPHYSICAL_DB[SERVED_NAMES[alloy]]["liquidus_C"] + 273.15)
            for name in ("thermalGradient", "normalSpeed", "coolingRate", "gOverR", "pdas", "sdas"):
                first = container["quantities"][name]["reasons"][0]
                self.assertEqual(first, {"code": "missing-source-constant", "params": {},
                                         "parent": {"input": "liquidus_K", "kind": served["kind"]}}, (alloy, name))

    def test_keyhole_leg_keeps_keyhole_field_inconsistent(self):
        seen = set()
        for key, result in self.results.items():
            cavity = result["meltPoolGeometry"]["keyholeVaporCavityDepth_um"]
            codes = [r["code"] for r in result["solidificationKinetics"]["quantities"]["thermalGradient"]["reasons"]]
            keyhole = "keyhole-field-inconsistent" in codes
            seen.add(keyhole)
            if cavity > 0.0:
                self.assertTrue(keyhole, key)
            if not keyhole:
                self.assertEqual(cavity, 0.0, key)
        self.assertEqual(seen, {True, False}, "both a conduction and a keyhole-leg case are covered")

    def test_pdas_model_is_only_the_transferred_ni_nb_arm(self):
        for (alloy, _, _), result in self.results.items():
            codes = [r["code"] for r in result["solidificationKinetics"]["quantities"]["pdas"]["reasons"]]
            self.assertEqual("missing-source-bound-model" in codes, alloy not in ("in625", "in718"), alloy)

    def test_no_flat_keys_no_sentences_no_doi(self):
        for key, result in self.results.items():
            container = result["solidificationKinetics"]
            self.assertEqual(ra4_problems(container), [], key)
            for flat in FORMER_FLAT_KEYS:
                self.assertNotIn(flat, container, (key, flat))
            text = json.dumps(container)
            for doi in OLD_DOIS:
                self.assertNotIn(doi, text, key)
            self.assertNotIn("doi", set(_keys(container)), key)

    def test_ra4_check_rejects_a_sentence_and_a_text_key(self):
        container = json.loads(json.dumps(self.results[("in718", "rosenthal", POINTS[0])]["solidificationKinetics"]))
        container["quantities"]["thermalGradient"]["reasons"][0]["params"]["note"] = "a free sentence"
        container["quantities"]["normalSpeed"]["reasons"][0]["text"] = "x"
        self.assertEqual(len(ra4_problems(container)), 2)


class AliasesAndInputs(unittest.TestCase):
    def test_inconel_625_is_never_classed_as_in718(self):
        expected = {"Inconel 625": "in625", "IN625": "in625", "in625": "in625", "Inconel 718": "in718",
                    "Ti-6Al-4V": "ti6al4v", "AlSi10Mg": "alsi10mg", "316L Stainless Steel": "ss316l",
                    "inconel": None, "Inconel": None, "CoCrMo": None, "": None, None: None, "718": None}
        for name, aid in expected.items():
            self.assertEqual(sf.canonical_alloy_id(name), aid, name)

    def test_unknown_alias_is_a_value_with_a_reason_not_an_error(self):
        out = sf.evaluate_solidification(_plain_field, T_liq=1336.0, v_scan=0.8, x_rear=1e-4, search_depth=8e-5,
                                         r_beam=4e-5, material_name="inconel")
        self.assertIsNone(out["alloyId"])
        self.assertNotIn("inputProvenance", out)
        self.assertEqual(qe.envelope_problems(out), [])
        for name, q in out["quantities"].items():
            self.assertIsNone(q["value"], name)
            self.assertIn("unknown-alloy-alias", [r["code"] for r in q["reasons"]], name)
        secondary = _run("CoCrMo", 150.0, 1200.0, "rosenthal")
        self.assertIsNone(secondary["solidificationKinetics"]["alloyId"])
        self.assertEqual(qe.envelope_problems(secondary), [])

    def test_a_typed_liquidus_is_user_input_and_an_equal_one_keeps_the_served_kind(self):
        typed = _run("Inconel 718", 150.0, 1200.0, "rosenthal", prop_overrides={"liquidus_C": 1300.0})
        record = typed["solidificationKinetics"]["inputProvenance"]["liquidus_K"]
        self.assertEqual(record["kind"], "userInput")
        self.assertEqual(record["sourceEvidenceKind"], "User input")
        self.assertEqual(record["defaultValue"], 1336.0 + 273.15)
        self.assertEqual(record["defaultKind"], "declaredAssumption")
        reason = typed["solidificationKinetics"]["quantities"]["thermalGradient"]["reasons"][0]
        self.assertEqual(reason["parent"], {"input": "liquidus_K", "kind": "userInput"})
        self.assertEqual(qe.envelope_problems(typed), [])
        self.assertEqual(ra4_problems(typed["solidificationKinetics"]), [])
        equal = _run("Inconel 718", 150.0, 1200.0, "rosenthal", prop_overrides={"liquidus_C": 1336.0})
        self.assertEqual(equal["solidificationKinetics"], _run("Inconel 718", 150.0, 1200.0,
                                                                "rosenthal")["solidificationKinetics"])
        legacy = _run("AlSi10Mg", 150.0, 1200.0, "rosenthal", prop_overrides={"liquidus_C": 600.0})
        record = legacy["solidificationKinetics"]["inputProvenance"]["liquidus_K"]
        self.assertEqual(record["kind"], "userInput")
        self.assertIsNone(record["defaultKind"], "a legacy estimate is never a default")
        self.assertEqual(qe.envelope_problems(legacy), [])


class ServedPathDoesNotSample(unittest.TestCase):
    def test_the_field_is_not_sampled_at_sol_a1(self):
        for alloy in sf.CANONICAL_ALLOY_IDS:
            out = sf.evaluate_solidification(_plain_field, T_liq=1300.0, v_scan=1.0, x_rear=2e-4, search_depth=2e-4,
                                             r_beam=4e-5, material_name=alloy, depth_from_keyhole_leg=False)
            self.assertEqual(out["alloyId"], alloy)
            self.assertEqual(qe.envelope_problems(out), [], alloy)

    def test_the_legacy_keywords_are_refused(self):
        for keyword in ("T_sol", "t_surface", "x_front", "cos_theta", "pdas_A1", "sdas_B1"):
            with self.assertRaises(TypeError, msg=keyword):
                sf.evaluate_solidification(_plain_field, T_liq=1336.0, v_scan=0.8, x_rear=1e-4, search_depth=8e-5,
                                           r_beam=4e-5, material_name="in718", **{keyword: 1.0})

    def test_the_retired_helpers_are_gone(self):
        for name in RETIRED:
            self.assertFalse(hasattr(sf, name), name)

    def test_the_sampler_is_kept_for_sol_c(self):
        # Analytic liquidus plane T = T_l + 1 - a z + b x: n_x = b / sqrt(a^2 + b^2), R = v n_x (no floor).
        a, b = 1.0e7, 500.0
        mapped = sf.map_solidification_front(lambda x, y, z: 1300.0 + 1.0 - a * z + b * x, 1300.0, 1.0, 20e-6, 8e-6,
                                             h_m=1.2e-7)
        self.assertIsNotNone(mapped)
        for sample in mapped["samples"]:
            self.assertAlmostEqual(sample["R_m_s"], b / math.hypot(a, b), delta=1e-9)


class LineRuleSolA1(unittest.TestCase):
    def test_line_rule_alone_refuses_g2e7_r0p01(self):
        # Contract 6.3 pair 2 (SPEC A3.A4): x 7.07e-4 and cooling 2e5 K/s lie inside the old box and Vcs < R < Vab,
        # yet the default PDAS is refused because G is off the 1e7 K/m source line.
        for alloy in ("in625", "in718"):
            out = sf.pdas_band_um(2e7, 0.01, alloy)
            self.assertIsNone(out["pdasBand_um"], alloy)
            self.assertIs(out["pdasOutOfRange"], True)
            self.assertEqual(out["admission"], {"onSourceLine": False, "xInRange": True, "coolingInRange": True,
                                                "aboveVcs": True, "belowVab": True})
            self.assertEqual(out["reasons"], [{"code": "outside-source-model-domain",
                                               "params": out["admission"], "parent": None}])
            self.assertEqual(out["sources"], [])


if __name__ == "__main__":
    unittest.main()
