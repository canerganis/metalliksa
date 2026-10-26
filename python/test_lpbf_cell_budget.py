"""Cell-budget arithmetic for the NIST AMB2022-03 bare-plate case; no solver is run."""
import math
import unittest

from lpbf_core_physics import calculate_mesh_domain


class NistCellBudgetTests(unittest.TestCase):
    def test_nist_case_at_coarsest_mesh_exceeds_reference_limit(self):
        p = dict(beamDiameter_um=67, mesh_um=80, trackLength_um=10000, tracks=1, hatch_um=0,
                 surfaceMode='bare-plate', layers=0, layer_um=0)
        d = calculate_mesh_domain(p)
        plate_cells = max(1, math.ceil(3170e-6 / d['dx'] - 1e-12))
        support_cells = 1  # smallest support the solver allows
        self.assertEqual((d['nx'], d['ny'], plate_cells, support_cells), (128, 128, 40, 1))
        total = d['nx'] * d['ny'] * (plate_cells + support_cells)
        self.assertEqual(total, 671744)
        self.assertGreater(total, 600000)  # limit in lpbf_simulation.py


if __name__ == '__main__':
    unittest.main()
