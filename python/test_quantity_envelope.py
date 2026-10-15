"""Quantity envelope v1 (python/quantity_envelope.py): vocabularies, label rule, ledger mapping, validators.

Solidification integration contract Revision 1, sections 4.1 to 4.3 and 4.6; the maintainer's label decisions 1 and
2 (2026-10-15); SPEC Amendment 3 A3.A5 (F16). Self-contained: the expected lists are pinned here and the shared
fixtures under tests/fixtures/quantity-envelope/ are regenerated from python/tools/quantity_envelope_fixtures.py.
No measured dataset, golden or served solver result is read.
"""
from __future__ import annotations

import ast
import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import module_contract as mc  # noqa: E402
import quantity_envelope as qe  # noqa: E402

_SPEC = importlib.util.spec_from_file_location("quantity_envelope_fixtures",
                                               HERE / "tools" / "quantity_envelope_fixtures.py")
fixtures = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fixtures)

# SPEC_solidification_2026-10-14.md section 2 (SPEC:34), in order, then the four integration codes of contract 4.6.
SPEC_CODES = (
    "missing-assessed-system", "outside-database-domain", "unknown-database-temperature-domain",
    "outside-source-model-domain", "missing-source-bound-model", "missing-source-constant",
    "missing-thermal-history", "unsupported-precipitate", "unverified-equation", "invalid-interface-sample",
    "nonphysical-input", "unknown-alloy-alias", "not-requested", "phase-selection-sensitive",
    "residual-liquid-at-termination", "numerical-conservation-failed", "stale-parent-input",
    "keyhole-field-inconsistent", "incompatible-liquidus-parent", "unsupported-fraction-conversion",
    "licence-scope-unconfirmed")
INTEGRATION_CODES = ("parent-unavailable", "solver-error", "insufficient-sample-support", "quarantined-legacy-path")
# P8 contract 6.3 closed kind enum (p8_input_provenance.KINDS on research/p8-research-arm).
P8_KINDS = {"sourceDefault", "sourceModelAssumption", "sourcedAlternative", "alloyTransfer", "modelConvention",
            "declaredAssumption", "legacyEstimate", "userInput", "followsInput", "derived"}
# The two manifest files named by contract 4.1 item 5; the whole manifest is read from lpbf_simulation.py by AST.
NAMED_MANIFEST_FILES = ("solidification_front.py", "lpbf_thermal_solver.py")


def _manifest_files():
    tree = ast.parse((HERE / "lpbf_simulation.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "IMPLEMENTATION_SOURCE_FILES"
                                                for t in node.targets):
            return tuple(ast.literal_eval(node.value))
    raise AssertionError("IMPLEMENTATION_SOURCE_FILES not found")


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            names.add(node.value)  # importlib.import_module("...") / __import__("...") literals
    return names


def _fixture(name):
    return json.loads((fixtures.FIXTURE_DIR / name).read_text(encoding="utf-8"))


class VocabularyTests(unittest.TestCase):
    def test_reason_codes_are_the_21_spec_codes_and_four_integration_codes(self):
        self.assertEqual(qe.SPEC_REASON_CODES, SPEC_CODES)
        self.assertEqual(qe.INTEGRATION_REASON_CODES, INTEGRATION_CODES)
        self.assertEqual(len(qe.REASON_CODES), 25)

    def test_every_code_has_one_sentence_and_unknown_codes_fail(self):
        for code in qe.REASON_CODES:
            with self.subTest(code=code):
                text = qe.reason_text(code)
                self.assertTrue(text.endswith(".") and text[0].isupper(), text)
                self.assertNotIn("—", text)
        with self.assertRaises(qe.EnvelopeError):
            qe.reason_text("no-such-code")
        self.assertEqual(qe.template_params("Only {count} of {required} samples; {count} again."),
                         ("count", "required"))

    def test_statuses_kinds_and_roles_are_the_contract_vocabularies(self):
        self.assertEqual(qe.QUANTITY_STATUSES, ("computed", "partial", "unavailable", "failed", "not-requested"))
        self.assertEqual(set(qe.INPUT_KINDS), P8_KINDS)
        self.assertEqual(qe.LEAF_ROLES, ("derived", "requestInput", "physicalInput", "softwareLimit", "convention",
                                         "indexConvention"))
        self.assertEqual(qe.QUANTITY_SOURCE_EVIDENCE_KINDS, ("Literature estimate", "User input", "Unresolved"))
        self.assertNotIn("Measured", qe.QUANTITY_SOURCE_EVIDENCE_KINDS)
        self.assertIn("Measured", qe.OBSERVATION_SOURCE_EVIDENCE_KINDS)
        self.assertEqual(set(qe.QUANTITY_DEFINITIONS), {
            "liquidus-front-thermal-gradient", "liquidus-front-normal-speed", "liquidus-front-cooling-rate",
            "liquidus-front-g-over-r", "pdas-model-alternatives", "sdas", "front-morphology",
            "solid-state-transformation", "cet-class", "laves-trapped-scheil-fraction", "scheil-phase-inventory",
            "scheil-residual-liquid", "critical-temperature", "lsw-mean-radius", "precipitation-strengthening",
            "user-threshold-isotherm-kinematics"})
        for definition in qe.QUANTITY_DEFINITIONS.values():
            self.assertIn(definition["unit"], qe.UNITS)
            self.assertIn(definition["valueKind"], qe.VALUE_KINDS)

    def test_ceiling_and_maturity_echo_match_the_sdk(self):
        self.assertEqual(qe.MODULE_EVIDENCE_CEILING, mc.PENDING_ORACLE_CEILING)
        self.assertIn(qe.MODULE_EVIDENCE_CEILING, mc.EVIDENCE_TYPES)
        self.assertEqual(qe.MODULE_MATURITIES, mc.MATURITY)
        self.assertNotIn("Production", qe.MODULE_MATURITIES)

    def test_no_morphology_or_transformation_category_is_admitted(self):
        # SPEC A3.A4: no front-stability classifier is served; no non-null category exists for these in v1.
        self.assertEqual(qe.QUANTITY_DEFINITIONS["front-morphology"]["categories"], [])
        self.assertEqual(qe.QUANTITY_DEFINITIONS["solid-state-transformation"]["categories"], [])


class PlacementTests(unittest.TestCase):
    def test_no_manifest_file_imports_the_envelope(self):
        manifest = _manifest_files()
        for name in NAMED_MANIFEST_FILES:
            self.assertIn(name, manifest)
        self.assertNotIn("quantity_envelope.py", manifest)
        for name in manifest:
            path = HERE / name
            if not name.endswith(".py"):
                continue
            with self.subTest(file=name):
                imports = _imports(path)
                self.assertNotIn("quantity_envelope", imports)
                self.assertNotIn("module_contract", imports)  # module_contract imports the envelope

    def test_envelope_is_stdlib_only(self):
        tree = ast.parse((HERE / "quantity_envelope.py").read_text(encoding="utf-8"))
        modules = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)
                   for alias in node.names}
        modules |= {node.module.split(".")[0] for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom) and node.module}
        self.assertTrue(modules <= set(sys.stdlib_module_names) | {"__future__"}, modules)


class LabelRuleTests(unittest.TestCase):
    def test_committed_fixtures_equal_regenerated(self):
        self.assertEqual(fixtures.stale(), [])

    def test_label_cases_follow_the_decided_rule(self):
        for case in _fixture("label-cases.json")["cases"]:
            with self.subTest(case=case["name"]):
                result = qe.source_label(case["inputs"], case["dependsOn"])
                self.assertEqual({key: result[key] for key in case["expected"]}, case["expected"])

    def test_unresolved_takes_precedence_and_names_only_its_inputs(self):
        inputs = {"k": fixtures._declared("k"), "cp": fixtures._user("cp"), "rho": fixtures._sourced("rho")}
        result = qe.source_label(inputs, ["rho", "cp", "k"])
        self.assertEqual((result["sourceEvidenceKind"], result["weakestInputs"]), ("Unresolved", ["k"]))
        del inputs["k"]
        result = qe.source_label(inputs, ["rho", "cp"])
        self.assertEqual((result["sourceEvidenceKind"], result["weakestInputs"]), ("User input", ["cp"]))

    def test_process_values_never_make_an_output_user_input(self):
        sourced = fixtures._sourced("k")
        inputs = {"k": sourced}
        for name in ("P", "v", "d", "T0"):
            inputs[name] = qe.process_input_record(name)
        result = qe.source_label(inputs, ["P", "v", "d", "T0", "k"])
        self.assertEqual(result["sourceEvidenceKind"], "Literature estimate")
        self.assertEqual(result["determiningInputs"], ["k"])
        # Only process values: never upgraded to Literature estimate by emptiness.
        only = qe.source_label(inputs, ["P", "v"])
        self.assertEqual((only["sourceEvidenceKind"], only["weakestInputs"]), ("Unresolved", []))

    def test_typed_value_equal_to_its_sourced_default_keeps_the_sourced_label(self):
        default = fixtures._sourced("k")
        same = qe.typed_input(default, 25.0, 25.0, source_id="user:k")
        self.assertEqual(same["kind"], "sourceDefault")
        other = qe.typed_input(default, 25.0 + 2 ** -48, 25.0, source_id="user:k")
        self.assertEqual((other["kind"], other["defaultKind"], other["defaultValue"]),
                         ("userInput", "sourceDefault", 25.0))
        self.assertEqual(qe.source_label({"k": other}, ["k"])["sourceEvidenceKind"], "User input")

    def test_a_record_never_reads_stronger_than_its_kind(self):
        problems = qe.input_record_problems({**fixtures._declared("k"), "sourceEvidenceKind": "Literature estimate"},
                                            "k")
        self.assertTrue(any("cannot read" in p for p in problems), problems)
        unlocated = qe.input_record_problems({**fixtures._sourced("k"), "sourceLocator": None}, "k")
        self.assertTrue(any("located source" in p for p in unlocated), unlocated)
        measured = qe.input_record_problems({**fixtures._sourced("k"), "sourceEvidenceKind": "Measured"}, "k")
        self.assertTrue(any("never reads Measured" in p for p in measured), measured)
        self.assertEqual(qe.source_label({"k": {**fixtures._sourced("k"), "sourceEvidenceKind": "Measured"}},
                                         ["k"])["sourceEvidenceKind"], "Unresolved")


class LedgerMappingTests(unittest.TestCase):
    # Class strings as recorded in solidification_melt_point_ledger.json (schema 2, 024e30cd).
    LEDGER = {
        "MP01": "proposed-fixed-front-literature-model",
        "MP02": "proposed-fixed-front-explicit-family-transfer",
        "MP03": "proposed-fixed-front-explicit-family-transfer",
        "MP04": "proposed-fixed-front-literature-model",
        "MP05": "proposed-refusal-default-liquidus; operational-proxy-only",
        "MP07": "datasheet-disclosure-only; not selected physical front",
    }

    def test_class_stems_map_and_a_renamed_prefix_keeps_the_mapping(self):
        self.assertEqual(qe.ledger_class_stem(self.LEDGER["MP01"]), "fixed-front-literature-model")
        self.assertEqual(qe.ledger_class_stem("admitted-fixed-front-literature-model"), "fixed-front-literature-model")
        self.assertEqual(qe.ledger_class_stem("fixed-front-explicit-family-transfer"),
                         "fixed-front-explicit-family-transfer")
        self.assertEqual(qe.ledger_class_stem(self.LEDGER["MP05"]), "refusal-default-liquidus")
        self.assertEqual(qe.ledger_class_stem(self.LEDGER["MP07"]), "datasheet-disclosure-only")
        for unknown in ("proposed-something-else", "", "measured-endpoint"):
            with self.assertRaises(qe.EnvelopeError):
                qe.ledger_class_stem(unknown)

    def test_transfers_never_read_as_measured(self):
        for record_id in ("MP02", "MP03"):
            record = qe.ledger_input_record(self.LEDGER[record_id], source_id=f"{record_id}:endpoint",
                                            source_locator=f"{record_id} locator", scope="Al9Si0.6Mg to AlSi10Mg")
            self.assertEqual((record["kind"], record["sourceEvidenceKind"], record["status"]),
                             ("alloyTransfer", "Literature estimate", "extrapolated"))
            self.assertEqual(qe.source_label({"Tl": record}, ["Tl"])["sourceEvidenceKind"], "Literature estimate")
            with self.assertRaises(qe.EnvelopeError):
                qe.ledger_input_record(self.LEDGER[record_id], source_id="x", source_locator="y", scope="z",
                                       status="inRange")
            with self.assertRaises(qe.EnvelopeError):  # the transfer scope must travel with the value
                qe.ledger_input_record(self.LEDGER[record_id], source_id="x", source_locator="y")
            self.assertTrue(qe.input_record_problems({**record, "sourceEvidenceKind": "Measured"}, "Tl"))
        literature = qe.ledger_input_record(self.LEDGER["MP01"], source_id="MP01", source_locator="Gan 2021 SI T1")
        self.assertEqual((literature["kind"], literature["scope"]),
                         ("sourceModelAssumption", "nominal alloy model convention"))

    def test_observation_only_classes_are_never_inputs(self):
        for record_id in ("MP05", "MP07"):
            with self.assertRaises(qe.EnvelopeError):
                qe.ledger_input_record(self.LEDGER[record_id], source_id="x", source_locator="y", scope="z")
        self.assertEqual(qe.ledger_observation_kind(self.LEDGER["MP05"]), "Measured")
        self.assertEqual(qe.ledger_observation_kind(self.LEDGER["MP07"]), "Literature estimate")
        with self.assertRaises(qe.EnvelopeError):
            qe.ledger_observation_kind(self.LEDGER["MP02"])
        mp05 = qe.observation("DSC operational temperatures of evaporating SRM316L", {"Ts": 1675.0, "Tl": 1708.0},
                              "K", qe.ledger_observation_kind(self.LEDGER["MP05"]),
                              [qe.source_ref("MP05", "Pichler et al. Table 2", "primary-read")],
                              material_scope="SRM316L (evaporating)", process_scope="DSC heating")
        self.assertEqual(qe.observation_problems(mp05, "mp05"), [])

    def test_nothing_installed_until_sol_t_keeps_every_front_unresolved(self):
        self.assertEqual(set(qe.SERVED_LIQUIDUS_INPUT_KINDS), set(qe.CANONICAL_ALLOY_IDS))
        for alloy, kind in qe.SERVED_LIQUIDUS_INPUT_KINDS.items():
            with self.subTest(alloy=alloy):
                self.assertIn(kind, qe.UNSOURCED_INPUT_KINDS)
                self.assertEqual(qe.INPUT_KIND_EVIDENCE[kind], "Unresolved")
        self.assertEqual(qe.LEDGER_ALTERNATIVE_MAPPING["inputKind"], "sourcedAlternative")
        self.assertFalse(qe.LEDGER_ALTERNATIVE_MAPPING["default"])


class SyntheticAdmittedLiquidusTests(unittest.TestCase):
    """F16 (SPEC A3.A5): the production validator accepts the synthetic non-null fixture and rejects each mutation."""

    def setUp(self):
        self.doc = _fixture("synthetic-admitted-liquidus.json")

    def problems(self, doc=None):
        return qe.envelope_problems(self.doc if doc is None else doc)

    def mutated(self, change):
        doc = copy.deepcopy(self.doc)
        change(doc)
        return self.problems(doc)

    def assertRejected(self, change, fragment):
        problems = self.mutated(change)
        self.assertTrue(any(fragment in p for p in problems), f"expected {fragment!r} in {problems}")

    def test_fixture_is_accepted_with_co_located_full_precision_values(self):
        self.assertEqual(self.problems(), [])
        q = self.doc["quantities"]
        g, r = q["thermalGradient"]["value"], q["normalSpeed"]["value"]
        self.assertEqual(g, 12345678.901234567)
        self.assertEqual(r, 0.051234567890123456)
        self.assertEqual(q["coolingRate"]["value"], g * r)
        self.assertEqual(q["gOverR"]["value"], g / r)
        for name, item in q.items():
            with self.subTest(quantity=name):
                self.assertEqual(item["sourceEvidenceKind"], "Literature estimate")
                self.assertTrue(item["labelSources"])
                self.assertIn("synthetic", item["identity"]["model"])
                self.assertEqual(item["physicalValidation"], qe.PHYSICAL_VALIDATION)
        self.assertEqual(self.doc["moduleEvidenceCeiling"], "screening-only")
        self.assertEqual(self.doc["inputProvenance"]["liquidus_K"]["kind"], "alloyTransfer")
        self.assertEqual(self.doc["inputProvenance"]["liquidus_K"]["status"], "extrapolated")

    def test_non_null_unavailable_and_null_computed_are_rejected(self):
        self.assertRejected(lambda d: d["quantities"]["thermalGradient"].update(status="unavailable"),
                            "must carry value null")
        self.assertRejected(lambda d: d["quantities"]["thermalGradient"].update(value=None), "needs a value")

    def test_missing_parent_engine_definition_or_unit_is_rejected(self):
        self.assertRejected(lambda d: d["quantities"]["normalSpeed"]["identity"].update(model=None),
                            "engine/model identity")
        self.assertRejected(lambda d: d["quantities"]["normalSpeed"]["identity"].update(parent=None),
                            "parent identity")
        self.assertRejected(lambda d: d["quantities"]["normalSpeed"].update(quantityDefinition="liquidus-speed"),
                            "not a registered definition")
        self.assertRejected(lambda d: d["quantities"]["normalSpeed"].update(unit="mm/s"), "unit must be")
        self.assertRejected(lambda d: d["quantities"]["normalSpeed"].pop("unit"), "missing keys")

    def test_missing_source_label_or_named_inputs_is_rejected(self):
        self.assertRejected(lambda d: d["quantities"]["gOverR"].update(sourceEvidenceKind=None),
                            "per-value source label")
        self.assertRejected(lambda d: d["quantities"]["gOverR"].update(labelSources=[]), "labelSources")
        self.assertRejected(lambda d: d["quantities"]["gOverR"].update(dependsOn=[]), "names the inputs")

    def test_forbidden_evidence_upgrade_is_rejected(self):
        def unsourced_conductivity(d):
            d["inputProvenance"]["conductivity_W_mK"] = qe.input_record(
                "declaredAssumption", "synthetic-f16:conductivity", status="inRange",
                declaration_locator="synthetic declaration")
        self.assertRejected(unsourced_conductivity, "differs from the label rule")
        self.assertRejected(lambda d: d["quantities"]["thermalGradient"].update(sourceEvidenceKind="Measured"),
                            "Measured never labels a quantity")
        self.assertRejected(lambda d: d.update(moduleEvidenceCeiling="literature-estimate"), "decision 1")
        self.assertRejected(lambda d: d.update(moduleMaturity="Production"), "moduleMaturity")
        self.assertRejected(lambda d: d["quantities"]["thermalGradient"]["physicalValidation"].update(
            experimentalValidation=True), "physicalValidation")

    def test_stale_parent_output_presented_as_current_is_rejected(self):
        # A new endpoint record (changed sourceId) invalidates children even when the numbers agree.
        self.assertRejected(lambda d: d["inputProvenance"]["liquidus_K"].update(
            sourceId="synthetic-f16:liquidus:other-record"), "stale-parent value is not current")

    def test_parent_refusal_propagates_null_and_reason_to_every_dependent(self):
        def refuse_gradient(d):
            d["quantities"]["thermalGradient"] = qe.unavailable(
                "liquidus-front-thermal-gradient",
                [qe.reason("missing-source-constant", parent={"input": "liquidus_K", "kind": "alloyTransfer"})],
                depends_on=["liquidus_K"])
        problems = self.mutated(refuse_gradient)
        for dependent in ("coolingRate", "gOverR"):
            self.assertTrue(any(f"quantities.{dependent}: parent quantity 'thermalGradient' is null" in p
                                for p in problems), problems)

    def test_user_input_and_unresolved_values_name_their_inputs(self):
        for kind in ("userInput", "declaredAssumption"):
            with self.subTest(kind=kind):
                inputs = fixtures._front_inputs()
                if kind == "userInput":
                    inputs["conductivity_W_mK"] = qe.typed_input(inputs["conductivity_W_mK"], 30.0, 25.0,
                                                                 source_id="user:conductivity")
                    expected = "User input"
                else:
                    inputs["conductivity_W_mK"] = qe.input_record("declaredAssumption", "decl:k", status="inRange",
                                                                  declaration_locator="synthetic declaration")
                    expected = "Unresolved"
                q = qe.quantity("liquidus-front-thermal-gradient", 1.0e7, inputs=inputs,
                                depends_on=["liquidus_K", "conductivity_W_mK", "power_W"],
                                sources=[fixtures.SYNTHETIC_SOURCE], model_identity=fixtures.SYNTHETIC_ENGINE,
                                uncertainty={"kind": "not-quantified", "construction": None})
                doc = qe.container({"thermalGradient": q}, input_provenance=inputs)
                self.assertEqual(qe.envelope_problems(doc), [])
                self.assertEqual((q["sourceEvidenceKind"], q["weakestInputs"]), (expected, ["conductivity_W_mK"]))
                doc["quantities"]["thermalGradient"]["weakestInputs"] = []
                self.assertTrue(any("must name its inputs" in p for p in qe.envelope_problems(doc)))

    def test_text_on_reasons_sources_on_null_and_stray_container_keys_are_rejected(self):
        blanket = _fixture("blanket-null-front.json")
        blanket["quantities"]["normalSpeed"]["reasons"][0]["text"] = "A sentence from a producer."
        self.assertTrue(any("no text from producers" in p for p in qe.envelope_problems(blanket)))
        blanket = _fixture("blanket-null-front.json")
        blanket["quantities"]["pdas"]["sources"] = [qe.source_ref("hunt-lu", "Hunt-Lu 1996", "secondary-read")]
        self.assertTrue(any("no source claim" in p for p in qe.envelope_problems(blanket)))
        stray = {"block": {"moduleEvidenceCeiling": "screening-only", "fields": {}}}
        self.assertTrue(any("one placement" in p for p in qe.envelope_problems(stray)))

    def test_model_alternatives_are_never_an_interval(self):
        inputs = fixtures._front_inputs()
        q = qe.quantity("pdas-model-alternatives", {"hunt": 1.0e-6, "kurzFisher": 2.2e-6}, inputs=inputs,
                        depends_on=["liquidus_K"], sources=[fixtures.SYNTHETIC_SOURCE],
                        model_identity=fixtures.SYNTHETIC_ENGINE,
                        uncertainty={"kind": "model-alternatives", "construction": "two source models"})
        doc = qe.container({"pdas": q}, input_provenance=inputs)
        self.assertEqual(qe.envelope_problems(doc), [])
        doc["quantities"]["pdas"]["uncertainty"]["kind"] = "calibrated-prediction-interval"
        self.assertTrue(any("never an interval" in p for p in qe.envelope_problems(doc)))


class BlanketNullFrontTests(unittest.TestCase):
    """The SOL-A1 shape of contract 4.3 item 8: null with missing-source-constant and the liquidus parent."""

    def test_fixture_is_accepted_and_every_front_value_is_null_with_its_parent(self):
        doc = _fixture("blanket-null-front.json")
        self.assertEqual(qe.envelope_problems(doc), [])
        for name, q in doc["quantities"].items():
            with self.subTest(quantity=name):
                self.assertIsNone(q["value"])
                self.assertIsNone(q["sourceEvidenceKind"])
                self.assertEqual(q["sources"], [])
        for name in ("thermalGradient", "normalSpeed", "coolingRate", "gOverR", "pdas"):
            first = doc["quantities"][name]["reasons"][0]
            self.assertEqual((first["code"], first["parent"]),
                             ("missing-source-constant", {"input": "liquidus_K", "kind": "declaredAssumption"}))

    def test_a_dependent_must_name_each_null_parent_and_the_parent_kind_must_match(self):
        doc = _fixture("blanket-null-front.json")
        doc["quantities"]["coolingRate"]["reasons"].pop()  # drops the reason naming normalSpeed
        self.assertTrue(any("must name the null parent 'normalSpeed'" in p for p in qe.envelope_problems(doc)))
        doc = _fixture("blanket-null-front.json")
        doc["quantities"]["normalSpeed"]["reasons"][0]["parent"]["kind"] = "sourceDefault"
        self.assertTrue(any("differs from the input record" in p for p in qe.envelope_problems(doc)))
        doc = _fixture("blanket-null-front.json")
        doc["quantities"]["normalSpeed"]["reasons"] = []
        self.assertTrue(any("needs at least one reason" in p for p in qe.envelope_problems(doc)))


class DeclarationTests(unittest.TestCase):
    def _declarations(self, statuses=("computed", "unavailable"), kinds=("Literature estimate",)):
        definitions = {"thermalGradient": "liquidus-front-thermal-gradient", "normalSpeed": "liquidus-front-normal-speed",
                       "coolingRate": "liquidus-front-cooling-rate", "gOverR": "liquidus-front-g-over-r"}
        return [mc.QuantityDeclaration(path=f"front.quantities.{name}", definition=definition,
                                       unit=qe.QUANTITY_DEFINITIONS[definition]["unit"], statuses=statuses,
                                       source_evidence_kinds=kinds, reason_codes=("missing-source-constant",))
                for name, definition in definitions.items()]

    def test_declared_payload_is_accepted_through_lists_and_undeclared_values_fail(self):
        payload = {"front": _fixture("synthetic-admitted-liquidus.json")}
        self.assertEqual(qe.envelope_problems(payload, self._declarations()), [])
        listed = {"front": [_fixture("synthetic-admitted-liquidus.json"), _fixture("synthetic-admitted-liquidus.json")]}
        self.assertEqual(qe.envelope_problems(listed, self._declarations()), [])
        self.assertTrue(any("not declared" in p for p in qe.envelope_problems(payload, self._declarations()[:3])))
        self.assertTrue(any("is missing from this container" in p for p in qe.envelope_problems(
            {"front": qe.container({}, input_provenance={})}, self._declarations())))

    def test_values_outside_the_declared_statuses_or_labels_fail(self):
        payload = {"front": _fixture("synthetic-admitted-liquidus.json")}
        self.assertTrue(any("status 'computed' is not declared" in p
                            for p in qe.envelope_problems(payload, self._declarations(statuses=("unavailable",)))))
        self.assertTrue(any("is not declared (['User input'])" in p
                            for p in qe.envelope_problems(payload, self._declarations(kinds=("User input",)))))


if __name__ == "__main__":
    unittest.main()
