"""Small independent equation/contract checks for the mechanical research note.

Run: python -I -B docs/research/scripts/engine_est_mechanical_check.py --check
No served imports, experimental rows, external data, network or third parties.
Source strings below are normalized web transcriptions, not PDF authentication.
Synthetic E/alpha/yield fixtures are not proposed alloy constants.
"""

from __future__ import annotations

import argparse
import ast
import math
from pathlib import Path
import re
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[3]
SOURCES = {
    "surface": {
        "url": "https://www.mdpi.com/2075-4701/11/6/964",
        "locator": "Equation (1), normalized mathematical transcription",
        "equation": "sigma_w=1.43*(120+HV)/(sqrt_area_um**(1/6))",
    },
    "internal": {
        "url": "https://www.mdpi.com/1996-1944/14/18/5315",
        "locator": "Equation (1), normalized mathematical transcription",
        "equation": "sigma_th_sc=1.56*(HV+120)/(sqrt_A_um**(1/6))",
    },
    "both": {
        "url": "https://www.mdpi.com/1996-1944/13/20/4642",
        "locator": "Equations (10) and (11), both geometries at R=-1",
    },
    "elasticity": {
        "url": "https://solidmechanics.org/text/Chapter3_2/Chapter3_2.htm",
        "locator": "Section 3.2.2, isotropic thermoelastic constitutive law",
    },
    "plasticity": {
        "url": "https://solidmechanics.org/text/Chapter3_7/Chapter3_7.htm",
        "locator": "Sections 3.7.2 and 3.7.5-8, strain decomposition/yield/flow",
    },
    "gumbel": {
        "url": "https://www.itl.nist.gov/div898/handbook/eda/section3/eda366g.htm",
        "locator": "Maximum extreme-value Type I CDF and percent-point function",
    },
}


def positive(x: float) -> float:
    if not math.isfinite(x) or x <= 0:
        raise ValueError("finite positive input required")
    return x


def bar_cycle(temperatures, imposed, E, alpha, sy):
    """Constant-property perfect plasticity; initial stress-free state at T[0]."""
    E, alpha, sy = positive(E), positive(alpha), positive(sy)
    if len(temperatures) < 2 or len(temperatures) != len(imposed):
        raise ValueError("complete paired history required")
    if any(not math.isfinite(x) for x in [*temperatures, *imposed]):
        raise ValueError("nonfinite history")
    if imposed[0] != 0:
        raise ValueError("initial stress-free fixture needs zero imposed strain")
    p = 0.0
    for temp, total in zip(temperatures, imposed):
        thermal = alpha * (temp - temperatures[0])
        trial = E * (total - thermal - p)
        if abs(trial) <= sy:
            stress = trial
        else:
            stress = math.copysign(sy, trial)
            p = total - thermal - stress / E
    return stress, p


def zero_traction_release(E, area, length, plastic, thermal=0.0):
    """Solve the free end displacement from the bar's assembled end reaction.

    The plastic state is frozen during elastic unloading. A nonzero initial
    reaction is required in the fixture; displacement is an unknown, not a
    preassigned copy of the eigenstrain.
    """
    E, area, length = positive(E), positive(area), positive(length)
    if not all(math.isfinite(x) for x in (plastic, thermal)):
        raise ValueError("finite release state required")
    def reaction(displacement):
        return E * area * (displacement / length - thermal - plastic)
    span = length * (abs(plastic) + abs(thermal) + 0.01)
    lo, hi = -span, span
    for _ in range(70):
        mid = (lo + hi) / 2
        if reaction(mid) > 0:
            hi = mid
        else:
            lo = mid
    displacement = (lo + hi) / 2
    return displacement, reaction(displacement)


def fatigue(s_um, hv, location):
    c = {"surface": 1.43, "internal": 1.56}
    if location not in c:
        raise ValueError("explicit supported location required")
    return c[location] * (positive(hv) + 120) / positive(s_um) ** (1 / 6)


def gumbel_quantile(mu, beta, p):
    positive(beta)
    if not math.isfinite(mu) or not 0 < p < 1:
        raise ValueError("finite location, positive scale and interior p required")
    return mu - beta * math.log(-math.log(p))


def valid_maxima(values, block_kind):
    if block_kind != "comparable-independent-block-maxima" or len(values) < 3:
        raise ValueError("maxima sampling design required")
    for value in values:
        positive(value)
    if max(values) == min(values):
        raise ValueError("zero-scale fit is not a Gumbel distribution")
    return True


class MechanicalChecks(unittest.TestCase):
    def test_bar_history_and_analytic_piecewise_oracle(self):
        # Synthetic units: E=100 GPa, alpha=10^-5/K, sy=100 MPa.
        # Thermal stresses are 1 MPa/K; the independent piecewise result follows
        # elastic unloading from the hot compressive yield state.
        for delta, expected_mpa in [(25, 0), (100, 0), (150, 50), (250, 100)]:
            stress, plastic = bar_cycle([300, 300 + delta, 300], [0] * 3,
                                        100e9, 1e-5, 100e6)
            self.assertAlmostEqual(stress / 1e6, expected_mpa)
            self.assertAlmostEqual(stress, -100e9 * plastic)
        # Same final T and peak T, different restraint history: not determined
        # from peak temperature alone. Free expansion has no stress or plasticity.
        stress, plastic = bar_cycle([300, 550, 300], [0, 0.0025, 0],
                                    100e9, 1e-5, 100e6)
        self.assertAlmostEqual(stress, 0)
        self.assertAlmostEqual(plastic, 0)

    def test_free_release_is_not_constrained_residual(self):
        stress, plastic = bar_cycle([300, 550, 300], [0, 0, 0],
                                    100e9, 1e-5, 100e6)
        self.assertGreater(stress, 0)
        self.assertAlmostEqual(stress, 100e6)
        displacement, force = zero_traction_release(100e9, 1e-6, .01, plastic)
        self.assertAlmostEqual(displacement, -1e-5)
        self.assertAlmostEqual(force, 0, delta=1e-10)
        self.assertAlmostEqual(displacement / .01, plastic)
        # The old constrained displacement must fail the traction condition.
        self.assertGreater(abs(100e9 * 1e-6 * -plastic), 1)
        # Distinct eigenstrains prevent an always-zero-displacement fake solve.
        for eigen in (-.002, .0003):
            displacement, force = zero_traction_release(70e9, 2e-6, .02, eigen)
            self.assertAlmostEqual(force, 0, delta=1e-10)
            self.assertAlmostEqual(displacement, .02 * eigen)

    def test_two_layer_beam_independent_section_equilibrium(self):
        # Numerical midpoint quadrature against closed-form half-section strain.
        H, L, E, e = 0.004, 0.040, 100e9, -0.001
        kappa = 1.5 * e / H
        mean = e / 2
        n = 400
        dz = H / n
        axial = moment = strain_moment = 0.0
        for i in range(n):
            z = -H / 2 + (i + 0.5) * dz
            eigen = e if z > 0 else 0
            sigma = E * (mean + kappa * z - eigen)
            axial += sigma * dz
            moment += sigma * z * dz
            strain_moment += z * eigen * dz
        self.assertLess(abs(axial) / (E * abs(e) * H), 1e-12)
        self.assertLess(abs(moment) / (E * abs(e) * H**2), 2e-6)
        self.assertAlmostEqual(12 / H**3 * strain_moment, kappa)
        # Numerically integrate slope from constant curvature independently.
        step = L / n
        tip = sum(kappa * (i + 0.5) * step * step for i in range(n))
        self.assertAlmostEqual(tip, kappa * L**2 / 2)
        # Uniform eigenstrain is stress-free expansion, no bending.
        self.assertAlmostEqual(sum((-H / 2 + (i + 0.5) * dz) * e * dz
                                   for i in range(n)), 0)

    def test_live_constants_and_source_transcriptions(self):
        # Parse the served constants without importing the served dependency tree.
        tree = ast.parse((ROOT / "python/murakami_constants.py").read_text("utf-8"))
        literals = {}
        c_map = None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for name in node.targets:
                    if isinstance(name, ast.Name) and isinstance(node.value, ast.Constant):
                        literals[name.id] = node.value.value
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id == "MURAKAMI_C":
                    c_map = node.value.args[0]
        self.assertIsNotNone(c_map)
        constants = {literals[key.id]: ast.literal_eval(val)
                     for key, val in zip(c_map.keys, c_map.values)}
        # Direct source-transcription checks are necessary, but are not the only
        # checks: the sixth-power and unit oracles below detect wrong exponents,
        # coefficient swaps and metres/micrometres mistakes.
        self.assertIn("1.43*(120+HV)", SOURCES["surface"]["equation"])
        self.assertIn("1.56*(HV+120)", SOURCES["internal"]["equation"])
        record = (ROOT / "docs/research/engine_est_stress_fatigue.md").read_text("utf-8")
        extracted = {}
        for source_id, coefficient in [("M-S03", "C_surface"), ("M-S04", "C_internal")]:
            row = next(line for line in record.splitlines()
                       if line.startswith("| " + source_id + " |"))
            match = re.search(coefficient + r"=(\d+(?:\.\d+)?); HV_offset=(\d+); exponent=(\d+)/(\d+)", row)
            self.assertIsNotNone(match, source_id + " source extraction missing")
            c, offset, numerator, denominator = map(float, match.groups())
            extracted[coefficient] = c
            self.assertEqual(offset, literals["HV_OFFSET"])
            self.assertEqual(numerator / denominator, 1 / 6)
            self.assertIn("https://www.mdpi.com/", row)
        self.assertEqual(constants["surface"], extracted["C_surface"])
        self.assertEqual(constants["internal"], extracted["C_internal"])
        # Execute only the actual scalar function AST, supplying its validation
        # and constant lookup explicitly. This exercises the served exponent and
        # arithmetic without importing any service, rows or solver dependencies.
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == "murakami_sqrt_area_limit_MPa")
        def require_positive(_name, value):
            return positive(value)
        namespace = {
            "input_validation": SimpleNamespace(require_positive=require_positive),
            "murakami_geometric_constant": lambda location: constants[location],
            "HV_OFFSET": literals["HV_OFFSET"],
            "INTERNAL": "internal", "Any": object,
        }
        exec(compile(ast.Module(body=[function], type_ignores=[]),
                     "<served-murakami-scalar>", "exec"), namespace)
        live = namespace["murakami_sqrt_area_limit_MPa"]
        self.assertAlmostEqual(live(64, 120, "surface"), 171.6)
        self.assertAlmostEqual(live(64, 120, "internal"), 187.2)
        for size, hardness in [(64, 120), (729, 360), (1e4, 210)]:
            sigma = live(size, hardness, "surface")
            self.assertAlmostEqual((sigma / (1.43 * (hardness + 120)))**6 * size, 1)

    def test_fatigue_exact_oracle_units_and_monotonicity(self):
        self.assertAlmostEqual(fatigue(64, 120, "surface"), 171.6)
        self.assertAlmostEqual(fatigue(64, 120, "internal"), 187.2)
        for s, hv in [(64, 120), (729, 360), (1e4, 210)]:
            sigma = fatigue(s, hv, "surface")
            # Independent integral-power invariant, no duplicated root formula.
            self.assertAlmostEqual((sigma / (1.43 * (hv + 120)))**6 * s, 1)
            self.assertGreater(fatigue(s, hv + 10, "surface"), sigma)
            self.assertLess(fatigue(s * 64, hv, "surface"), sigma)
            self.assertAlmostEqual(fatigue(s * 64, hv, "surface"), sigma / 2)
        self.assertAlmostEqual(fatigue(64e-6 * 1e6, 120, "surface"), 171.6)
        # A metre-as-micrometre mutation changes the result by a factor of ten.
        self.assertAlmostEqual(fatigue(64e-6, 120, "surface"), 10 * 171.6)

    def test_gumbel_inverse_and_explicit_volume(self):
        for p in [0.1, 0.5, 0.9, 0.99]:
            x = gumbel_quantile(40, 5, p)
            self.assertAlmostEqual(math.exp(-math.exp(-(x - 40) / 5)), p)
        p_target, blocks = 0.95, 100
        x = gumbel_quantile(40, 5, p_target ** (1 / blocks))
        cdf = math.exp(-math.exp(-(x - 40) / 5))
        self.assertAlmostEqual(cdf**blocks, p_target)
        self.assertGreater(x, gumbel_quantile(40, 5, p_target))

    def test_refusals(self):
        for s, hv, location in [(0, 120, "surface"), (-1, 120, "surface"),
                                 (64, 0, "internal"), (64, math.nan, "internal"),
                                 (math.inf, 120, "surface"), (64, 120, "unknown")]:
            with self.assertRaises(ValueError):
                fatigue(s, hv, location)
        for beta, p in [(0, 0.5), (-1, 0.5), (1, 0), (1, 1), (1, math.nan)]:
            with self.assertRaises(ValueError):
                gumbel_quantile(40, beta, p)
        for data, design in [([1, 2, 3], "individual-pores"),
                             ([1, 1, 1], "comparable-independent-block-maxima"),
                             ([1, 2], "comparable-independent-block-maxima")]:
            with self.assertRaises(ValueError):
                valid_maxima(data, design)
        with self.assertRaises(ValueError):
            bar_cycle([300], [0], 100e9, 1e-5, 100e6)
        with self.assertRaises(ValueError):
            bar_cycle([300, math.nan], [0, 0], 100e9, 1e-5, 100e6)
        with self.assertRaises(ValueError):
            bar_cycle([300, 400], [0, 0], 0, 1e-5, 100e6)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(MechanicalChecks))
    print("Evidence: synthetic model checks and primary-equation web transcriptions only.")
    print("No PDF-byte authentication, experimental validation or served integration claimed.")
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
