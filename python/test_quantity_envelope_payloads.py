"""Real SOL-A1 thermal payloads: envelope validity and manifest sentence boundary.

Synthetic process requests, no measured data or physical accuracy claim.
"""
import copy
import unittest

from lpbf_thermal_solver import calculate_meltpool_physics
from quantity_envelope import envelope_problems


def manifest_text_problems(value, path=()):
    """RA4: manifest containers carry codes; only sources[].locator may contain whitespace."""
    problems = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "text":
                problems.append(path + (key,))
            problems.extend(manifest_text_problems(child, path + (key,)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            problems.extend(manifest_text_problems(child, path + (index,)))
    elif isinstance(value, str) and any(char.isspace() for char in value):
        if not (len(path) >= 3 and path[-3] == "sources"
                and isinstance(path[-2], int) and path[-1] == "locator"):
            problems.append(path)
    return problems


class ThermalEnvelopePayloads(unittest.TestCase):
    def test_real_thermal_containers(self):
        for material in ("Ti-6Al-4V", "AlSi10Mg", "316L Stainless Steel", "Inconel 718", "Inconel 625"):
            for source in ("rosenthal", "eagar-tsai", "goldak"):
                with self.subTest(material=material, source=source):
                    front = calculate_meltpool_physics(
                        material, 285, 960, 80, heat_source=source,
                        include_process_map=False)["solidificationKinetics"]
                    self.assertEqual(envelope_problems(front), [])
                    self.assertEqual(manifest_text_problems(front), [])
                    self.assertTrue(front["quantities"])
                    self.assertTrue(all(q["value"] is None for q in front["quantities"].values()))

    def test_sentence_guard_rejects_text_and_arbitrary_whitespace(self):
        allowed = {"sources": [{"locator": "Paper section 3"}]}
        self.assertEqual(manifest_text_problems(allowed), [])
        for mutation in ({"text": "code"}, {"reason": "free sentence"},
                         {"identity": {"model": "two words"}},
                         {"locator": "not a source locator"}):
            payload = copy.deepcopy(allowed)
            payload.update(mutation)
            self.assertTrue(manifest_text_problems(payload))


if __name__ == "__main__":
    unittest.main()
