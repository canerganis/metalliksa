"""Manufactured numerical oracles, not experimental LPBF validation."""
import math
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from lpbf_simulation import liquidus_crossing_sums
from solidification_front import map_solidification_front


class CrossingVerification(unittest.TestCase):
    def setUp(self):
        self.x, self.y, self.z = np.meshgrid(np.arange(-1., 2.), np.arange(-1., 2.), np.arange(-1., 2.), indexing="ij")
        self.active = np.ones_like(self.x, dtype=bool)

    def test_front_is_unavailable_when_liquidus_crossing_is_beyond_search_depth(self):
        liquidus = 1700.0

        def superheated_domain(x, _y, z):
            return liquidus + 100.0 + 1.0e6 * x - 1.0e5 * z

        self.assertGreater(superheated_domain(-4e-6, 0.0, 8e-6), liquidus)
        self.assertIsNone(map_solidification_front(
            superheated_domain,
            liquidus,
            v_scan=1.0,
            x_rear=20e-6,
            search_depth=8e-6,
            h_m=0.5e-6,
            n_samples=9,
        ))

    def test_liquidus_crossing_at_search_boundary_remains_valid(self):
        liquidus = 1700.0

        def boundary_crossing(x, _y, z):
            # Weak +x gradient (500 K/m): n_x > 0, a solidifying trailing front; the crossing moves < 0.1 um.
            return liquidus + 1.0 - 125000.0 * z + 500.0 * x

        mapped = map_solidification_front(
            boundary_crossing,
            liquidus,
            v_scan=1.0,
            x_rear=20e-6,
            search_depth=8e-6,
            h_m=0.5e-6,
            n_samples=9,
        )
        self.assertIsNotNone(mapped)
        self.assertEqual(mapped["nPoints"], 9)
        self.assertTrue(all(abs(sample["z_um"] - 8.0) <= 0.1 for sample in mapped["samples"]))

    def rotating(self, t):
        # A static z gradient separates planes. Multiple cells cross; compare
        # their independently calculated event sums below.
        return 100.+1.-2*t+(2.-2*t)*self.x+2*t*self.y+10*self.z

    def oracle(self, a, b):
        old, new = self.rotating(a), self.rotating(b)
        ids = self.active & (old >= 100.) & (new < 100.)
        # Exact local crossing time for T=A+B*t, independent of extraction code.
        x, y = self.x[ids], self.y[ids]
        t = (1+2*x+10*self.z[ids])/(2+2*x-2*y)
        g = np.sqrt((2-2*t)**2+(2*t)**2+100)
        cooling = 2+2*x-2*y
        return np.array([g.sum(), (cooling/g).sum(), cooling.sum(), len(g)])

    def test_rotating_vectors_and_step_subdivision(self):
        full = liquidus_crossing_sums(self.rotating(0), self.rotating(1), self.active, 1., 1., 100.)
        np.testing.assert_allclose(full, self.oracle(0, 1), rtol=1e-12)
        sums = np.zeros(4)
        for a, b in zip([0., .4, .8], [.4, .8, 1.]):
            actual = liquidus_crossing_sums(self.rotating(a), self.rotating(b), self.active, 1., b-a, 100.)
            if actual is not None:
                np.testing.assert_allclose(actual, self.oracle(a, b), rtol=1e-12)
                sums += actual
        np.testing.assert_allclose(sums, full, rtol=1e-12)

    def test_inactive_boundary_has_one_sided_gradient(self):
        active = (self.x >= 0) & (self.y >= 0)
        old = 101.+3*self.x+4*self.y+10*self.z
        new = old-2
        expected = [math.sqrt(125), 2/math.sqrt(125), 2., 1.]
        # Only (x,y,z)=(0,0,0) crosses in this active domain.
        for sentinel in (-1e9, 1e9):
            a, b = old.copy(), new.copy()
            a[~active], b[~active] = sentinel, -sentinel
            np.testing.assert_allclose(liquidus_crossing_sums(a, b, active, 1., 1., 100.), expected)

    def test_cancellation_zero_gradient_and_no_cooling(self):
        # Gradients +x and -x cancel at the centre's theta=.5 crossing.
        old, new = 101.+.25*self.x, 99.-.25*self.x
        self.assertIsNone(liquidus_crossing_sums(old, new, self.active, 1., 1., 100.))
        self.assertIsNone(liquidus_crossing_sums(new, old, self.active, 1., 1., 100.))
        self.assertIsNone(liquidus_crossing_sums(old, new, ~self.active, 1., 1., 100.))

    def test_equality_counted_once_and_units(self):
        old = 100.+10*self.x+10*self.y+10*self.z
        # theta=0: use the old gradient, including at a one-sided boundary.
        result = liquidus_crossing_sums(old, old-1, self.active, .001, .01, 100.)
        count = int((old == 100.).sum())
        g = math.sqrt(3)*10000
        np.testing.assert_allclose(result, [count*g, count*100/g, count*100, count])
        self.assertIsNone(liquidus_crossing_sums(old+1, old, self.active, .001, .01, 100.))

    @unittest.skipIf(os.name == "nt", "OpenFOAM dispatch is Linux-only")
    def test_previous_extraction_binary_rejected(self):
        from lpbf_core_physics import SOURCE_INTEGRATION
        from lpbf_openfoam import thermal
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/"openfoam-case"
            folder.mkdir()
            def launch(*args, **kwargs):
                # Passes the earlier capture and source-integration checks so the run reaches the intended
                # solidification-extraction check (a binary built before linear-liquidus-crossing-v1).
                # Without a valid capture fraction the Linux-only dispatch raises the capture error first.
                (folder/"numerical-diagnostics.json").write_text(
                    json.dumps({"minimumCapturedSourceFraction": 1.0, "sourceIntegration": SOURCE_INTEGRATION}))
                return SimpleNamespace(stdout=io.StringIO(""), wait=lambda: 0)
            with patch("lpbf_openfoam.BINARY", Path(__file__)), patch("lpbf_openfoam.generate_case", return_value=(1., [])), patch("lpbf_openfoam.subprocess.Popen", side_effect=launch):
                with self.assertRaisesRegex(ValueError, "solidification extraction contract mismatch"):
                    thermal({}, {}, artifact_dir=tmp)


if __name__ == "__main__":
    unittest.main()
