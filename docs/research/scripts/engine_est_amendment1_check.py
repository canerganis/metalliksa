"""Amendment 1 research contracts and manufactured mechanics, not served code.

python -I -B docs/research/scripts/engine_est_amendment1_check.py --check
Requires the two named ignored fatigue PDFs and pdftotext. No measured-row
loaders, equilibrium grids, bands, served imports, installations or network.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import math
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[3]
SHORT_CRACK_CEILING_UM = 1000.0  # Conservative SPEC policy, not a fitted transition.


def geometry_admission(flux, recoil=None, ambient=None, sigma=None, radius=None,
                       other_onset=False):
    """Per-state gate. The consuming trajectory must latch any crossed gate."""
    if not math.isfinite(flux) or flux < 0:
        raise ValueError("finite nonnegative evaporation flux required")
    if other_onset:
        return "keyhole-onset"
    if flux == 0:
        return "admitted-fixed-surface"
    if any(x is None for x in (recoil, ambient, sigma, radius)):
        return "onset-unresolved"
    if not all(math.isfinite(x) for x in (recoil, ambient, sigma, radius)):
        raise ValueError("finite onset inputs required")
    if min(sigma, radius) <= 0 or min(recoil, ambient) < 0:
        raise ValueError("positive tension/radius and nonnegative pressures required")
    return ("keyhole-onset" if recoil-ambient >= 2*sigma/radius
            else "admitted-fixed-surface")


def profile_admission(kind, build_id=None, matched_build_id=None, derived_from_m1=False):
    if derived_from_m1:
        raise ValueError("M1 alone has no layerwise build memory")
    if kind == "user-effective-profile-scenario":
        return True
    if kind == "matched-build-effective-profile" and build_id and build_id == matched_build_id:
        return True
    raise ValueError("need explicit effective scenario or matched-build calibration")


def section_release(profile, H, E, cells=400):
    """Assemble force/moment equations and solve the 2x2 section stiffness.

    This solves for mean strain and curvature; it does not insert the closed
    form curvature from SPEC. Piecewise midpoints are exact for the RHS of
    uniform/linear fixtures and convergent for a two-half-section step.
    """
    dz = H/cells
    k00 = k01 = k11 = f0 = f1 = 0.
    for i in range(cells):
        z = -H/2 + (i+.5)*dz
        weight = E*dz
        k00 += weight
        k01 += weight*z
        k11 += weight*z*z
        f0 += weight*profile(z)
        f1 += weight*z*profile(z)
    determinant = k00*k11-k01*k01
    mean = (f0*k11-f1*k01)/determinant
    curvature = (f1*k00-f0*k01)/determinant
    return mean, curvature


def fatigue_size_domain(size, support=None, long_crack=False):
    if not math.isfinite(size) or size <= 0:
        raise ValueError("finite positive projected square-root area required")
    if long_crack or size >= SHORT_CRACK_CEILING_UM:
        return "refuse-short-crack", {"size_um": size, "ceiling_um": SHORT_CRACK_CEILING_UM}
    if support is None:
        return "support-unestablished", {"size_um": size}
    low, high = support
    if not all(math.isfinite(x) for x in (low, high)) or not 0 < low <= high:
        raise ValueError("source support must be finite ordered positive bounds")
    return ("within-study-size" if low <= size <= high else "size-extrapolation",
            {"size_um": size, "source_low_um": low, "source_high_um": high})


def source_page(filename, digest, page):
    pdf = ROOT / "papers" / filename
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == digest, filename
    return subprocess.run(["pdftotext", "-f", str(page), "-l", str(page),
                           "-raw", "-enc", "UTF-8", str(pdf), "-"],
                          capture_output=True, check=True).stdout.decode("utf-8")


def load_mechanical():
    spec = importlib.util.spec_from_file_location(
        "_amendment1_mechanics", Path(__file__).with_name("engine_est_mechanical_check.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AmendmentChecks(unittest.TestCase):
    def test_capillary_onset_boundary_and_missing_inputs(self):
        # Manufactured hemisphere: integrating rim tension gives 2*pi*r*sigma;
        # pressure force is dp*pi*r^2. This is independent of a TDB/vapor fit.
        r, sigma, ambient = 50e-6, 1., 100000.
        for pressure, expected in ((139999., "admitted-fixed-surface"),
                                   (140000., "keyhole-onset"),
                                   (140001., "keyhole-onset")):
            self.assertEqual(geometry_admission(1., pressure, ambient, sigma, r), expected)
        self.assertAlmostEqual(40000*math.pi*r*r, 2*math.pi*r*sigma)
        self.assertEqual(geometry_admission(0.), "admitted-fixed-surface")
        self.assertEqual(geometry_admission(1.), "onset-unresolved")
        self.assertEqual(geometry_admission(0., other_onset=True), "keyhole-onset")
        # Radius is d/2, not diameter: a swapped input must change this state.
        self.assertEqual(geometry_admission(1., 130000., ambient, sigma, r), "admitted-fixed-surface")
        self.assertEqual(geometry_admission(1., 130000., ambient, sigma, 2*r), "keyhole-onset")
        # A later cool step does not restore a whole-run geometric envelope.
        trajectory = [geometry_admission(1., p, ambient, sigma, r)
                      for p in (120000., 150000., 120000.)]
        self.assertIn("keyhole-onset", trajectory)
        for bad in (0., -1., math.nan):
            with self.assertRaises(ValueError):
                geometry_admission(1., 140000., ambient, sigma, bad)

    def test_effective_profile_provenance(self):
        self.assertTrue(profile_admission("user-effective-profile-scenario"))
        self.assertTrue(profile_admission("matched-build-effective-profile", "a", "a"))
        for args in (("M1",), ("matched-build-effective-profile",),
                     ("matched-build-effective-profile", "a", "b")):
            with self.assertRaises(ValueError):
                profile_admission(*args)
        with self.assertRaises(ValueError):
            profile_admission("user-effective-profile-scenario", derived_from_m1=True)

    def test_section_release_equilibrium_not_build_prediction(self):
        H, E, e, L = .004, 100e9, -.001, .040
        mean, curvature = section_release(lambda z: e, H, E)
        self.assertAlmostEqual(mean, e)
        self.assertAlmostEqual(curvature, 0)
        # Linear effective profile: exact target, sign and root integration.
        mean, curvature = section_release(lambda z: .0002+0.1*z, H, E)
        self.assertAlmostEqual(mean, .0002)
        self.assertAlmostEqual(curvature, .1)
        self.assertAlmostEqual(curvature*L*L/2, .00008)
        # Two half-section profile: closed-form moment from the two rectangles.
        coarse = section_release(lambda z: e if z > 0 else 0., H, E, 200)[1]
        fine = section_release(lambda z: e if z > 0 else 0., H, E, 400)[1]
        oracle = 1.5*e/H
        self.assertLess(abs(fine-oracle), abs(coarse-oracle))
        self.assertAlmostEqual(fine, oracle, delta=3e-6)

    def test_m1_saturation_threshold_and_release(self):
        model = load_mechanical()
        # Synthetic E*alpha=1 MPa/K; threshold is 200 K, not 100 K.
        for delta, expected, saturated in ((99, 0, False), (100, 0, False),
                                            (150, 50, False), (199, 99, False),
                                            (200, 100, True), (201, 100, True)):
            stress, plastic = model.bar_cycle([300, 300+delta, 300], [0]*3,
                                              100e9, 1e-5, 100e6)
            self.assertAlmostEqual(stress/1e6, expected)
            self.assertEqual(math.isclose(abs(stress), 100e6, rel_tol=1e-12), saturated)
            displacement, reaction = model.zero_traction_release(100e9, 1e-6, .01, plastic)
            self.assertAlmostEqual(reaction, 0, delta=1e-10)
            self.assertAlmostEqual(displacement/.01, plastic)

    def test_fatigue_numeric_support_and_hard_ceiling(self):
        support = (120., 300.)
        for s, expected in ((119., "size-extrapolation"), (120., "within-study-size"),
                            (300., "within-study-size"), (301., "size-extrapolation"),
                            (999., "size-extrapolation"), (1000., "refuse-short-crack"),
                            (1001., "refuse-short-crack")):
            status, details = fatigue_size_domain(s, support)
            self.assertEqual(status, expected)
            self.assertEqual(details["size_um"], s)
        self.assertEqual(fatigue_size_domain(200., long_crack=True)[0], "refuse-short-crack")
        self.assertEqual(fatigue_size_domain(200.)[0], "support-unestablished")
        self.assertEqual(fatigue_size_domain(64e-6*1e6, support)[0], "size-extrapolation")
        for invalid in (0., -1., math.inf, math.nan):
            with self.assertRaises(ValueError):
                fatigue_size_domain(invalid, support)

    def test_bounded_source_support_replay(self):
        text = source_page("engine_est_fatigue_radlof2020.pdf",
                           "8f3f0c49f517a9ffb76800f47ab45cd2e113fec3cd8afedef1d08d2dc9b66b3a", 15)
        match = re.search(r"range of approximately\s+(\d+)[-\u2013](\d+).*?vertically and (\d+)[-\u2013](\d+)", text, re.S)
        self.assertIsNotNone(match)
        self.assertEqual(tuple(map(float, match.groups())), (120., 300., 75., 200.))
        for support in ((float(match[1]), float(match[2])), (float(match[3]), float(match[4]))):
            self.assertEqual(fatigue_size_domain(support[0]-1, support)[0], "size-extrapolation")
            self.assertEqual(fatigue_size_domain(support[1]+1, support)[0], "size-extrapolation")
        text = source_page("engine_est_fatigue_uematsu2021.pdf",
                           "91d1de349b3141bef9dbe68fb903b52a6c398aa6d78001b0a81967adf37b6261", 1)
        normalized = " ".join(text.replace("\u2010", "-").split())
        self.assertRegex(normalized, r"un-conservative predictions.*?108 cycles")
        # Bind the SPEC receipt to these exact source bytes as well as testing
        # source extraction; catches a mistyped hash in the handoff table.
        receipt = (ROOT / "docs/research/SPEC_engine_estimates_2026-10-17.md").read_text("utf-8")
        for filename in ("engine_est_fatigue_radlof2020.pdf", "engine_est_fatigue_uematsu2021.pdf"):
            row = next(line for line in receipt.splitlines() if line.startswith("| `papers/"+filename+"`"))
            digest = hashlib.sha256((ROOT/"papers"/filename).read_bytes()).hexdigest()
            self.assertIn(digest, row)

    def test_spec_is_append_only_against_parallel_lane_baseline(self):
        path = "docs/research/SPEC_engine_estimates_2026-10-17.md"
        baseline = subprocess.run(["git", "show", "f8d70f74:"+path], cwd=ROOT,
                                  capture_output=True, check=True).stdout.decode("utf-8")
        current = (ROOT/path).read_text("utf-8")
        self.assertTrue(current.startswith(baseline.replace("\r\n", "\n")))
        self.assertIn("## Amendment 1", current[len(baseline.replace("\r\n", "\n")):])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(AmendmentChecks))
    print("Research-only checks; gates are not yet served. No new physical validation.")
    raise SystemExit(0 if result.wasSuccessful() else 1)
