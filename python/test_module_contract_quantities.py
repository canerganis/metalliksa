"""SDK declarations for the quantity envelope (module_contract.QuantityDeclaration / ObservationDeclaration).

Solidification integration contract Revision 1, 4.1 items 2 and 3: "Measured" is legal only in an
ObservationDeclaration; unknown statuses, codes or kinds fail; paths start at an output field; quantity and
observation paths do not overlap; the container ceiling is checked with within_ceiling against the contract
ceiling; the registry emits the declarations and the generated src/generated/quantityEnvelope.ts.
Synthetic contracts only; no real module declares quantities before SOL-A.
"""
from __future__ import annotations

import dataclasses
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import module_contract as mc  # noqa: E402
import module_registry as mr  # noqa: E402
import quantity_envelope as qe  # noqa: E402


def _quantity(path="front.quantities.thermalGradient", **overrides):
    values = dict(path=path, definition="liquidus-front-thermal-gradient", unit="K/m",
                  statuses=("computed", "unavailable"), source_evidence_kinds=("Literature estimate", "Unresolved"),
                  reason_codes=("missing-source-constant", "parent-unavailable"))
    values.update(overrides)
    return mc.QuantityDeclaration(**values)


def _observation(path="front.observations.dscEndpoints", **overrides):
    values = dict(path=path, observable="DSC operational temperatures of evaporating SRM316L",
                  source_evidence_kinds=("Measured",))
    values.update(overrides)
    return mc.ObservationDeclaration(**values)


def _operation(quantities=(), observations=(), fields=("front", "status")):
    return mc.Operation(id="front-run", method="POST", route="/api/fixture/front",
                        authority=mc.Authority(kind="python-ipc", script="python/fixture.py", timeout_ms=1000),
                        output=mc.OutputSchema(fields=fields, status_key=None,
                                               transport_values=(("status", ("success",)),)),
                        quantities=tuple(quantities), observations=tuple(observations))


def _contract(operation, ceiling="screening-only", maturity="Research"):
    return mc.ModuleContract(
        id="fixture-front", version="0.2.0", owner=mc.OWNER_UNASSIGNED, workspace="lpbf", label="Fixture",
        description="Synthetic contract for envelope declarations.", next="fixture-front", maturity=maturity,
        navigation="listed", view=mc.View(component="src/components/Fixture.tsx", export="Fixture"),
        evidence=mc.Evidence(emits=(), ceiling=ceiling, forbidden_claims=mc.FORBIDDEN_CLAIM_KEYS,
                             note="Synthetic: emits no status."),
        tests=mc.TestRefs(oracle=mc.Oracle(status="pending"), schema="python/test_fixture.py",
                          docs="docs/modules/fixture-front.md"),
        migration_state="contracted", operations=(operation,),
        lifecycle=mc.Lifecycle(background_work="none", resources=("fetch",)), source_refs=("python/fixture.py",))


class QuantityDeclarationTests(unittest.TestCase):
    def test_a_valid_declaration_round_trips(self):
        declaration = _quantity()
        self.assertEqual(declaration.to_dict()["sourceEvidenceKinds"], ["Literature estimate", "Unresolved"])
        self.assertEqual(declaration.to_dict()["leafRole"], "derived")

    def test_measured_is_legal_only_in_an_observation_declaration(self):
        with self.assertRaisesRegex(mc.ContractError, "Measured is legal only in an ObservationDeclaration"):
            _quantity(source_evidence_kinds=("Measured",))
        self.assertEqual(_observation().source_evidence_kinds, ("Measured",))
        self.assertEqual(_observation(source_evidence_kinds=("Literature estimate",)).source_evidence_kinds,
                         ("Literature estimate",))
        with self.assertRaises(mc.ContractError):
            _observation(source_evidence_kinds=("User input",))
        with self.assertRaises(mc.ContractError):
            _observation(source_evidence_kinds=())

    def test_unknown_statuses_codes_kinds_definitions_and_units_fail(self):
        for overrides in (dict(statuses=("available",)), dict(statuses=()),
                          dict(reason_codes=("no-such-code",)),
                          dict(source_evidence_kinds=("screening-only",)),
                          dict(definition="liquidus-speed"), dict(unit="mm/s"),
                          dict(leaf_role="model-output")):
            with self.subTest(overrides=overrides):
                with self.assertRaises(mc.ContractError):
                    _quantity(**overrides)

    def test_statuses_other_than_computed_need_reason_codes(self):
        with self.assertRaisesRegex(mc.ContractError, "need reason codes"):
            _quantity(reason_codes=())
        self.assertEqual(_quantity(statuses=("computed",), reason_codes=()).reason_codes, ())
        with self.assertRaisesRegex(mc.ContractError, "not-requested"):
            _quantity(statuses=("not-requested",), reason_codes=("missing-source-constant",))

    def test_value_carrying_quantities_declare_labels_and_unlabelled_roles_declare_none(self):
        with self.assertRaisesRegex(mc.ContractError, "per-value source labels"):
            _quantity(source_evidence_kinds=())
        self.assertEqual(_quantity(statuses=("unavailable",), source_evidence_kinds=()).statuses, ("unavailable",))
        with self.assertRaisesRegex(mc.ContractError, "carries no source label"):
            _quantity(leaf_role="convention")
        with self.assertRaisesRegex(mc.ContractError, "request echo"):
            _quantity(leaf_role="requestInput")

    def test_fraction_basis_is_required_exactly_for_fraction_quantities(self):
        fraction = dict(definition="scheil-residual-liquid", unit="1", path="scheil.quantities.residualLiquid")
        with self.assertRaises(mc.ContractError):
            _quantity(**fraction)
        self.assertEqual(_quantity(**fraction, fraction_basis="mole-of-atoms").fraction_basis, "mole-of-atoms")
        with self.assertRaises(mc.ContractError):
            _quantity(fraction_basis="mass")

    def test_paths_name_one_container_member_and_hide_no_claim(self):
        for path in ("front.thermalGradient", "front.quantities", "quantities", "front.quantities.a.b",
                     "front.observations.x", "a.quantities.b.quantities.c", "front.quantities.bad-name",
                     "evidence.quantities.x", "validated.quantities.x", ""):
            with self.subTest(path=path):
                with self.assertRaises(mc.ContractError):
                    _quantity(path=path)
        self.assertEqual(_quantity(path="quantities.thermalGradient").path, "quantities.thermalGradient")
        with self.assertRaises(mc.ContractError):
            _observation(path="front.quantities.dsc")


class OperationAndContractTests(unittest.TestCase):
    def test_paths_start_at_an_output_field_and_need_an_output(self):
        self.assertEqual(len(_operation((_quantity(),)).quantities), 1)
        with self.assertRaisesRegex(mc.ContractError, "must start at an output field"):
            _operation((_quantity(path="other.quantities.thermalGradient"),))
        with self.assertRaisesRegex(mc.ContractError, "need a declared output schema"):
            mc.Operation(id="front-run", method="POST", route="/api/fixture/front",
                         authority=mc.Authority(kind="python-ipc", script="python/fixture.py", timeout_ms=1000),
                         quantities=(_quantity(),))
        with self.assertRaisesRegex(mc.ContractError, "must start at an output field"):
            _operation((_quantity(path="quantities.thermalGradient"),))
        self.assertEqual(len(_operation((_quantity(path="quantities.thermalGradient"),),
                                        fields=("quantities", "status")).quantities), 1)

    def test_quantity_and_observation_paths_do_not_overlap_or_repeat(self):
        with self.assertRaisesRegex(mc.ContractError, "duplicates"):
            _operation((_quantity(), _quantity()))
        self.assertEqual(len(_operation((_quantity(),), (_observation(),)).observations), 1)
        nested = _observation(path="front.observations.thermalGradient")
        self.assertEqual(len(_operation((_quantity(),), (nested,)).observations), 1)
        # A record nested under a quantity cannot even be declared (one container member per path), and the
        # operation's prefix check stays as a second guard.
        with self.assertRaisesRegex(mc.ContractError, "exactly one container"):
            _observation(path="front.quantities.x.observations.y")
        self.assertTrue(mc._paths_overlap(("front", "quantities", "x"), ("front", "quantities", "x", "y")))
        self.assertFalse(mc._paths_overlap(("front", "quantities", "x"), ("front", "observations", "x")))

    def test_container_ceiling_is_checked_against_the_contract_ceiling(self):
        operation = _operation((_quantity(),), (_observation(),))
        contract = _contract(operation)
        self.assertTrue(mc.within_ceiling(qe.MODULE_EVIDENCE_CEILING, contract.evidence.ceiling))
        with self.assertRaisesRegex(mc.ContractError, "above the contract ceiling"):
            _contract(operation, ceiling="unresolved")
        self.assertEqual(_contract(_operation()).evidence.ceiling, "screening-only")
        self.assertEqual(_contract(_operation(), ceiling="unresolved").evidence.ceiling, "unresolved")

    def test_declarations_round_trip_through_the_emitted_dictionary(self):
        contract = _contract(_operation((_quantity(), _quantity(path="front.quantities.normalSpeed",
                                                                definition="liquidus-front-normal-speed",
                                                                unit="m/s")),
                                        (_observation(),)))
        self.assertEqual(mc.contract_from_dict(json.loads(json.dumps(contract.to_dict()))), contract)
        legacy = contract.to_dict()
        for op in legacy["operations"]:
            del op["quantities"], op["observations"]
        rebuilt = mc.contract_from_dict(legacy)
        self.assertEqual(rebuilt.operations[0].quantities, ())

    def test_module_doc_lists_declared_quantities_and_observations(self):
        contract = _contract(_operation((_quantity(),), (_observation(),)))
        text = mr.render_module_doc(contract)
        self.assertIn("`front.quantities.thermalGradient`: liquidus-front-thermal-gradient (K/m)", text)
        self.assertIn(qe.ENVELOPE_SCHEMA, text)
        self.assertIn("`front.observations.dscEndpoints`: DSC operational temperatures", text)

    def test_envelope_payload_check_uses_the_operation_declarations(self):
        inputs = {"liquidus_K": qe.input_record("declaredAssumption", "test:liquidus", status="inRange",
                                               declaration_locator="Synthetic contract test")}
        payload = {"front": qe.container({"thermalGradient": qe.unavailable(
            "liquidus-front-thermal-gradient", [qe.reason("missing-source-constant",
                parent=qe.reason_parent("liquidus_K", inputs))], depends_on=["liquidus_K"])}, input_provenance=inputs)}
        operation = _operation((_quantity(),))
        self.assertEqual(qe.envelope_problems(payload, operation), [])
        payload["front"]["quantities"]["thermalGradient"]["reasons"][0]["code"] = "solver-error"
        self.assertTrue(any("reason code 'solver-error' is not declared" in p
                            for p in qe.envelope_problems(payload, operation)))


class RegistryEmissionTests(unittest.TestCase):
    def test_registry_and_generated_envelope_are_current(self):
        self.assertEqual(mr.stale_outputs(), [])

    def test_every_operation_emits_its_declaration_lists(self):
        document = mr.registry_document(mr.build_registry())
        for contract in document["contracts"]:
            for operation in contract["operations"]:
                with self.subTest(module=contract["id"], operation=operation["id"]):
                    self.assertIsInstance(operation["quantities"], list)
                    self.assertIsInstance(operation["observations"], list)

    def test_generated_typescript_carries_every_vocabulary_and_template(self):
        document = qe.typescript_document()
        text = mr.render_envelope_ts(document)
        self.assertIn("export const QUANTITY_ENVELOPE = ", text)
        self.assertIn(qe.ENVELOPE_SCHEMA, text)
        for code, template in qe.REASON_TEMPLATES.items():
            self.assertEqual(document["reasonTemplates"][code]["template"], template)
            self.assertIn(json.dumps(code), text)
        self.assertEqual(document["inputKinds"], list(qe.INPUT_KINDS))
        self.assertEqual(document["quantityDefinitions"], qe.QUANTITY_DEFINITIONS)
        committed = (mr.GENERATED_ENVELOPE_TS.read_text(encoding="utf-8")).replace("\r\n", "\n")
        self.assertEqual(committed, text)


if __name__ == "__main__":
    unittest.main()
