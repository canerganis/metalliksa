"""Real SOL-A captures must stay reproducible and contain the null front contract."""
import json
import unittest

from tools.fixture_compare import differences, mapping_differences
from tools.solidification_payload_fixtures import FIXTURE_DIR, serialized_payloads


class SolidificationPayloadFixturesTest(unittest.TestCase):
    def test_committed_payloads_equal_real_producers(self):
        expected = serialized_payloads()
        actual = {path.name: path.read_text(encoding="utf-8") for path in FIXTURE_DIR.glob("*.json")}
        # Platform float noise is tolerated explicitly (see tools/fixture_compare.py); structure and keys stay exact.
        self.assertEqual(mapping_differences(actual, expected), [],
                         "Regenerate with python/tools/solidification_payload_fixtures.py --write")

    def test_two_real_captures_are_byte_equal(self):
        self.assertEqual(serialized_payloads(), serialized_payloads())

    def test_thermal_captures_are_valid_quantity_envelopes(self):
        from quantity_envelope import envelope_problems

        paths = list(FIXTURE_DIR.glob("thermal-*.json"))
        self.assertEqual(len(paths), 6)
        for path in paths:
            with self.subTest(fixture=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(envelope_problems(payload), [])
                self.assertTrue(payload["quantities"])
                self.assertTrue(all(quantity["value"] is None for quantity in payload["quantities"].values()))

    def test_keyhole_reason_survives_capture(self):
        payload = json.loads((FIXTURE_DIR / "thermal-keyhole.json").read_text(encoding="utf-8"))
        reasons = payload["quantities"]["thermalGradient"]["reasons"]
        self.assertIn("keyhole-field-inconsistent", [reason["code"] for reason in reasons])

    def test_every_captured_payload_validates_quantity_envelopes(self):
        from module_contracts_lpbf_secondary import build_solidification_microstructure_contract
        from module_registry import load_seed
        from quantity_envelope import envelope_problems

        seed = next(item for item in load_seed() if item["id"] == "solidification-microstructure")
        contract = build_solidification_microstructure_contract(seed)
        operations = {item.id: item for item in contract.operations}
        paths = list(FIXTURE_DIR.glob("*.json"))
        self.assertEqual(len(paths), 15)
        for path in paths:
            with self.subTest(fixture=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                declaration = (operations["gr-solidification"] if path.name.startswith("gr-") else
                               operations["solidification-microstructure"] if path.name.startswith("worker-") else None)
                self.assertEqual(envelope_problems(payload, declaration), [])


class FixtureComparePolicyTest(unittest.TestCase):
    """The cross-platform tolerance must absorb float noise only, never a real change."""

    def test_float_noise_hex_noise_and_observed_order_are_tolerated(self):
        a = {"v": 1.0, "observedOrder": 2.00020, "id": "p:0x1.afaaa4ad34d17p-16:" + "a" * 64}
        b = {"v": 1.0 + 1e-12, "observedOrder": 2.00028, "id": "p:0x1.afaaa4ad34d18p-16:" + "b" * 64}
        self.assertEqual(differences(a, b), [])

    def test_real_changes_are_reported(self):
        base = {"v": 1.0, "n": 3, "s": "text", "flag": True, "observedOrder": 2.0, "items": [1.0, 2.0]}
        for key, value in (("v", 1.0 + 1e-6), ("n", 4), ("s", "other"), ("flag", False),
                           ("observedOrder", 2.01), ("items", [1.0]), ("extra", 1)):
            with self.subTest(key=key):
                self.assertTrue(differences({**base, key: value}, base))
        self.assertTrue(differences({"id": "a-" + "a" * 64}, {"id": "b-" + "a" * 64}))
        self.assertTrue(differences({"v": None}, {"v": 0.0}))


if __name__ == "__main__":
    unittest.main()
