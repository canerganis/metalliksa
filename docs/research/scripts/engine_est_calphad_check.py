"""Read-only COST507 phase compatibility diagnosis. No equilibrium or measured rows.

python -I -B docs/research/scripts/engine_est_calphad_check.py --check
Use the existing pycalphad interpreter with --with-pycalphad for construction tests.
The in-memory extension is a structural experiment, NOT a repaired assessment.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def commands(text):
    return [x.strip() for x in re.sub(r"\$[^\n]*", "", text).split("!") if x.strip()]


def phase_sets(text, name):
    cmd = next(c for c in commands(text) if re.match(rf"CONST(?:ITUENT)?\s+{name}\s*:", c, re.I))
    return [set(re.findall(r"[A-Z]+", field)) for field in cmd.split(":")[1:-1]]


def check(text):
    a2, b2 = phase_sets(text, "BCC_A2"), phase_sets(text, "BCC_B2")
    assert a2[-1] == {"B", "C", "N", "VA"} and b2[-1] == {"VA"}
    assert a2[0] == b2[0] == b2[1]
    assert any(re.search(r"TYPE_DEF\s+O.*BCC_B2\s+DIS_PART\s+BCC_A2", c) for c in commands(text))
    # Negative controls: the mismatch depends on the requested components.
    for active, compatible in [({"TI", "AL", "V", "FE", "O", "C", "VA"}, False),
                               ({"TI", "AL", "V", "FE", "O", "VA"}, True),
                               ({"TI", "AL", "V", "N", "VA"}, False)]:
        assert (a2[-1] & active == b2[-1] & active) == compatible
    # A declaration-only extension fixes this test but does not establish Gibbs parameters.
    extended = text.replace("W,Y,ZN,ZR : VA : !", "W,Y,ZN,ZR : B,C,N,VA : !", 1)
    assert phase_sets(extended, "BCC_B2")[-1] == a2[-1]
    source = (ROOT / "python/calphad_solver.py").read_text(encoding="utf-8")
    assert 'phases = [p for p in dbf.phases.keys() if p not in excluded_phases]' in source
    return extended


def construction(text, extended):
    from pycalphad import Database, Model, variables as v
    import pycalphad
    db = Database(text)
    comps = ["TI", "AL", "V", "C", "FE", "O", "VA"]
    try:
        Model(db, comps, "BCC_B2")
    except ValueError as exc:
        assert "interstitial sublattice" in str(exc)
        failure = str(exc)
    else:
        raise AssertionError("Expected full-chemistry model construction refusal")
    Model(db, [x for x in comps if x != "C"], "BCC_B2")
    patched = Database(extended)
    m = Model(patched, comps, "BCC_B2")
    a = Model(patched, comps, "BCC_A2")
    # Check disordered energy recovery at finite carbon using independently mapped
    # site fractions. Merely allowing construction is not the limiting test.
    for temp in (900., 1400., 1900.):
        for carbon_sites in (0.0001, 0.002):
            substitution = {"TI": .88, "AL": .08, "V": .04, "FE": 0.}
            def substitutions(model):
                out = {v.T: temp, v.P: 101325.}
                for sy in model.GM.free_symbols:
                    if isinstance(sy, v.SiteFraction):
                        out[sy] = (carbon_sites if sy.species.name == "C" else 1-carbon_sites
                                   if sy.species.name == "VA" else substitution.get(sy.species.name, 0.))
                return out
            x = float(m.GM.subs(substitutions(m)))
            y = float(a.GM.subs(substitutions(a)))
            assert abs(x-y) < 1.e-7 * max(1., abs(y)), (temp, carbon_sites, x, y)
    ordering = carbon_ordering_checks(db, patched, comps)
    return {"version": pycalphad.__version__, "originalFailure": failure,
            "carbonFreeConstruction": "pass", "declarationExtensionConstruction": "pass",
            "disorderedLimitStates": 6, "carbonOrdering": ordering,
            "scientificRepair": False}


def carbon_ordering_checks(original, extended, comps):
    """Off-order probe of the declaration-only extension, never an assessment.

    Derive its vacancy weighting/atom normalization and compare with the real
    library expression. Equal-sublattice zero limits alone cannot reveal this.
    """
    from pycalphad import Model, variables as v
    m0 = Model(original, [c for c in comps if c != "C"], "BCC_B2")
    m = Model(extended, comps, "BCC_B2")
    # The admitted Ti-Al-V-Fe subset has only vacancy energetic parameters.
    for parameter in extended._parameters.all():
        if parameter["phase_name"] != "BCC_B2":
            continue
        species = {s.name for lattice in parameter["constituent_array"] for s in lattice}
        if species <= set(comps):
            assert parameter["parameter_type"] == "G"
            assert {s.name for s in parameter["constituent_array"][-1]} == {"VA"}

    def value(model, fractions, c, temperature):
        subs = {v.T: temperature, v.P: 101325.}
        for symbol in model.models["ord"].free_symbols:
            if isinstance(symbol, v.SiteFraction):
                subs[symbol] = (c if symbol.species.name == "C" else 1-c
                                if symbol.species.name == "VA" else
                                fractions[symbol.sublattice_index].get(symbol.species.name, 0.))
        return float(model.models["ord"].subs(subs))

    # Independently summed configurational entropy, not m.models['ord'] at c=0.
    gas = 8.3145  # COST507/pycalphad TDB R convention, J/(mol K).
    samples = 0
    max_shift = 0.
    for temperature in (900., 1400., 1900.):
        for first, second in (({"TI": .92, "AL": .04, "V": .03, "FE": .01},
                               {"TI": .76, "AL": .20, "V": .03, "FE": .01}),
                              ({"TI": .70, "AL": .25, "V": .04, "FE": .01},
                               {"TI": .90, "AL": .05, "V": .04, "FE": .01})):
            mean = {s: (first[s] + second[s]) / 2 for s in first}
            entropy = gas * temperature * sum(
                .5*first[s]*math.log(first[s]) + .5*second[s]*math.log(second[s])
                - mean[s]*math.log(mean[s]) for s in first)
            carbon_free = value(m0, (first, second), 0., temperature)
            energetic = carbon_free - entropy
            assert abs(carbon_free) > 1., "Off-order control is too close to zero"
            # xC is atomic fraction, c is interstitial occupancy: xC=3c/(1+3c).
            for xcarbon in (.0001, .001, .01):
                c = xcarbon / (3*(1-xcarbon))
                expected = ((1-c)*energetic + entropy)/(1+3*c)
                actual = value(m, (first, second), c, temperature)
                assert math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-7)
                assert not math.isclose(actual, carbon_free, rel_tol=1e-6)
                # Centered finite difference versus derived carbon derivative.
                step = 1e-7
                numeric = (value(m, (first, second), c+step, temperature)
                           - value(m, (first, second), c-step, temperature))/(2*step)
                derivative = (-4*energetic-3*entropy)/(1+3*c)**2
                assert math.isclose(numeric, derivative, rel_tol=2e-7, abs_tol=1e-4)
                max_shift = max(max_shift, abs(actual-carbon_free))
                samples += 1
            # Continuity from positive C; no equal-sublattice cancellation oracle.
            near_zero = value(m, (first, second), 1e-10, temperature)
            assert math.isclose(near_zero, carbon_free, rel_tol=1e-8, abs_tol=1e-6)
    return {"offOrderStates": samples, "carbonDerivative": "finite-difference pass",
            "declarationOnlyIsCarbonIndependent": False,
            "maxOrderingShift_J_mol_atoms_in_manufactured_states": max_shift,
            "status": "derived-unreviewed; not equilibrium or experimental validation"}


def main():
    p = argparse.ArgumentParser(); p.add_argument("--check", action="store_true", required=True)
    p.add_argument("--with-pycalphad", action="store_true"); args = p.parse_args()
    path = ROOT / "python/databases/COST507.tdb"
    raw = path.read_bytes(); text = path.read_text(encoding="utf-8")
    extended = check(text)
    result = {"check": "pass", "tdbSha256": hashlib.sha256(raw).hexdigest(),
              "originalInterstitial": [sorted(phase_sets(text, n)[-1]) for n in ("BCC_A2", "BCC_B2")]}
    if args.with_pycalphad:
        result["construction"] = construction(text, extended)
    else:
        result["construction"] = "not requested; static constituent and negative-control checks only"
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
