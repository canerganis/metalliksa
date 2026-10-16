"""Read-only COST507 phase compatibility diagnosis. No equilibrium or measured rows.

python -I -B docs/research/scripts/engine_est_calphad_check.py --check
Use the existing pycalphad interpreter with --with-pycalphad for construction tests.
The in-memory extension is a structural experiment, NOT a repaired assessment.
"""
import argparse
import hashlib
import json
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
    return {"version": pycalphad.__version__, "originalFailure": failure,
            "carbonFreeConstruction": "pass", "declarationExtensionConstruction": "pass",
            "disorderedLimitStates": 6, "scientificRepair": False}


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
