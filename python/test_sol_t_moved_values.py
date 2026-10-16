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

    def test_compare_names_every_moved_leaf_and_the_w_d_extremes(self):
        from tools.sol_t_moved_values import compare
        row = {"meltPoolGeometry": {"width_um": 100.0, "depth_um": 50.0, "regime": "C", "extentStatus": "computed"},
               "processParameters": {"normalizedEnthalpy": 10.0}, "verdict": "printable"}
        moved = {"meltPoolGeometry": {"width_um": 98.0, "depth_um": 50.0, "regime": "T", "extentStatus": "computed"},
                 "processParameters": {"normalizedEnthalpy": 11.0}, "verdict": "printable"}
        side = lambda rows: {"revision": "r", "implementationHash": "h", "endpoints": {}, "rows": rows}
        out = compare(side({"a/k/1/1": row, "b/k/1/1": row}), side({"a/k/1/1": moved, "b/k/1/1": row}))
        self.assertEqual(out["alloys"]["a"]["casesWithAnyChange"], 1)
        self.assertEqual(out["alloys"]["a"]["changedLeavesByBlock"], {"meltPoolGeometry": 2, "processParameters": 1})
        self.assertEqual(out["alloys"]["a"]["width_um"]["min"]["delta"], -2.0)
        self.assertEqual(out["alloys"]["a"]["regimeChanges"], [{"case": "a/k/1/1", "before": "C", "after": "T"}])
        self.assertEqual(out["alloys"]["b"]["casesWithAnyChange"], 0)
        with self.assertRaises(ValueError):
            compare(side({"a/k/1/1": row}), side({}))

    def test_other_alloy_errors_are_not_silenced(self):
        with self.assertRaises((KeyError, ValueError)):
            capture_verdict({}, "in718")


if __name__ == "__main__":
    unittest.main()
