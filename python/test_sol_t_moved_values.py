"""The synthetic receipt preserves the served IN625 refusal contract."""
import unittest
from lpbf_thermal_solver import calculate_meltpool_physics
from tools.sol_t_moved_values import capture_verdict


class MovedValueContract(unittest.TestCase):
    def test_in625_refusal_is_a_value(self):
        result = calculate_meltpool_physics("Inconel 625", 220, 900, 80, 80, 40, 100,
                                          heat_source="rosenthal")
        self.assertEqual(capture_verdict(result, "in625"), {
            "verdictStatus": "refused",
            "error": "ValueError: Unsupported LPBF alloy identity: 'in625'",
        })

    def test_other_alloy_errors_are_not_silenced(self):
        with self.assertRaises((KeyError, ValueError)):
            capture_verdict({}, "in718")


if __name__ == "__main__":
    unittest.main()
