"""Reproduce O8 alloy-vapour estimates, without reading papers or depth data.

Run: python -I docs/research/scripts/alsi10mg_vapour_o8.py
Verify committed output: add --check. Standard library only; no solver imports.
This calculation closes reproducibility, not blind validation or a MELT licence.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

R_GAS = 8.31446261815324  # SI molar gas constant, J/(mol K).
ELEMENTS = {
    # M: CIAAW aluminium page (full value), 2024 abridged table for others.
    # Tb/H: Mondal et al., Materials 16 (2023) 50, Table 1, PDF/printed p.3.
    "Al": {"M_kg_mol": 0.0269815384, "Tb_K": 2743.0, "H_J_mol": 284000.0},
    "Si": {"M_kg_mol": 0.028085, "Tb_K": 3533.0, "H_J_mol": 383000.0},
    "Mg": {"M_kg_mol": 0.024305, "Tb_K": 1383.0, "H_J_mol": 132000.0},
    "Fe": {"M_kg_mol": 0.055845, "Tb_K": 3134.0, "H_J_mol": 354000.0},
}
# Mondal Eq.2 p.4, Table 2 p.7: log10(p/atm)=-A/T+B+C log10(T)+1e-3 D T.
# The Mg polynomial is NOT extrapolated. Its fit ends at 1730 K.
FITS = {
    "Al": {"coefficients": [12210.0, -27.06, 10.09, -1.16], "range_K": [1200.0, 3370.0]},
    "Si": {"coefficients": [17250.0, -15.97, 6.403, -0.5281], "range_K": [1700.0, 4300.0]},
    "Fe": {"coefficients": [27180.0, 50.1, -12.62, 0.8586], "range_K": [1400.0, 3775.0]},
}
MG_FIT_RANGE_K = [600.0, 1730.0]
COMPOSITION_WT_PCT = {"Al": 89.67, "Si": 9.75, "Mg": 0.44, "Fe": 0.14}


def composition(mg_wt_pct: float) -> dict[str, float]:
    """Synthetic Mg sensitivity; Si/Fe fixed, Al balances to 100 mass percent."""
    if not math.isfinite(mg_wt_pct) or not 0 <= mg_wt_pct <= 0.45:
        raise ValueError("Mg must be finite and inside [0, 0.45] mass percent")
    return {"Al": 100.0 - 9.75 - 0.14 - mg_wt_pct,
            "Si": 9.75, "Mg": mg_wt_pct, "Fe": 0.14}


def mole_fractions(weights: dict[str, float]) -> dict[str, float]:
    if set(weights) != set(ELEMENTS) or any(not math.isfinite(w) or w < 0 for w in weights.values()):
        raise ValueError("four finite nonnegative constituent mass percentages required")
    if abs(sum(weights.values()) - 100.0) > 1e-10:
        raise ValueError("composition must sum to 100 mass percent")
    moles = {s: w / ELEMENTS[s]["M_kg_mol"] for s, w in weights.items()}
    total = sum(moles.values())
    return {s: n / total for s, n in moles.items()}


def pressure_atm(symbol: str, temperature_K: float, route: str) -> float:
    if not math.isfinite(temperature_K) or temperature_K <= 0:
        raise ValueError("temperature must be finite and positive")
    if route not in ("hybrid", "cc"):
        raise ValueError("unknown elemental pressure route")
    if route == "hybrid" and symbol in FITS:
        fit = FITS[symbol]
        if not fit["range_K"][0] <= temperature_K <= fit["range_K"][1]:
            raise ValueError("elemental fit outside declared temperature range")
        a, b, c, d = fit["coefficients"]
        return 10 ** (-a / temperature_K + b + c * math.log10(temperature_K)
                      + 1e-3 * d * temperature_K)
    element = ELEMENTS[symbol]
    # Mondal Eq.1 p.2, constant-H ideal-gas Clausius-Clapeyron.
    return math.exp(element["H_J_mol"] / R_GAS
                    * (1 / element["Tb_K"] - 1 / temperature_K))


def fit_enthalpy_J_mol(symbol: str, temperature_K: float, route: str) -> float:
    """R T^2 d ln(p)/dT; local derivative, not measured latent heat."""
    if route == "hybrid" and symbol in FITS:
        a, _, c, d = FITS[symbol]["coefficients"]
        return R_GAS * (math.log(10) * a + c * temperature_K
                        + math.log(10) * 1e-3 * d * temperature_K ** 2)
    return ELEMENTS[symbol]["H_J_mol"]


def vapour_constants(weights: dict[str, float], route: str = "hybrid",
                     mg_activity_factor: float = 1.0) -> dict:
    if not math.isfinite(mg_activity_factor) or mg_activity_factor <= 0:
        raise ValueError("positive finite Mg activity factor required")
    xs = mole_fractions(weights)

    def partials(t):
        return {s: xs[s] * pressure_atm(s, t, route)
                * (mg_activity_factor if s == "Mg" else 1.0) for s in xs}

    lo, hi = 1800.0, 3000.0
    if not sum(partials(lo).values()) < 1 < sum(partials(hi).values()):
        raise ValueError("one-atmosphere mixture root not bracketed")
    for _ in range(80):
        if hi - lo <= 1e-9:
            break
        mid = (lo + hi) / 2
        if sum(partials(mid).values()) < 1:
            lo = mid
        else:
            hi = mid
    else:
        raise RuntimeError("boiling-root bisection did not converge")
    t = (lo + hi) / 2
    ps = partials(t)
    total = sum(ps.values())
    ys = {s: p / total for s, p in ps.items()}
    mass = sum(ys[s] * ELEMENTS[s]["M_kg_mol"] for s in ys)
    h_cc = sum(ys[s] * ELEMENTS[s]["H_J_mol"] for s in ys)
    h_local = sum(ys[s] * fit_enthalpy_J_mol(s, t, route) for s in ys)
    mg_pressure = pressure_atm("Mg", t, route)
    return {
        "composition_wt_pct": weights, "liquid_mole_fractions": xs,
        "pressure_route": route, "mg_activity_factor": mg_activity_factor,
        "T_v_K": t, "mixture_pressure_atm": total,
        "root_pressure_residual_atm": abs(total - 1.0),
        "partial_pressures_atm": ps, "vapour_mole_fractions": ys,
        "M_vapour_kg_mol": mass,
        "H_table_weighted_J_mol": h_cc, "L_table_weighted_J_kg": h_cc / mass,
        "H_local_slope_J_mol": h_local, "L_local_slope_J_kg": h_local / mass,
        "mg_pure_pressure_atm": mg_pressure,
        "mg_above_fitted_temperature_range": t > MG_FIT_RANGE_K[1],
        "mg_above_mondal_synthesized_pressure_limit": mg_pressure > 10.0,
    }


def build_record() -> dict:
    primary = vapour_constants(COMPOSITION_WT_PCT)
    cc = vapour_constants(COMPOSITION_WT_PCT, "cc")
    pure_al = ELEMENTS["Al"]
    proposed = {"T_v_K": 2480.0, "L_v_J_kg": 6.8e6, "M_kg_mol": 0.025}
    # This replay cannot establish uncertainty; these are assumption sensitivities.
    sensitivities = [vapour_constants(composition(mg)) for mg in (0.0, 0.2, 0.3, 0.45)]
    return {
        "schema": "metalliksa-alsi10mg-vapour-o8-v1",
        "evidenceKind": "Literature estimate", "moduleMaturity": "Research",
        "validationStatus": "not validated: no blind test passed (open data unavailable, see GOAL.md)",
        "experimentalValidation": False,
        "uiSentence": "Ideal-mixture vapour sensitivity; extrapolated Mg pressure, no blind validation.",
        "o8Status": "reproducible calculation closed; material validity unresolved",
        "registeredMeltS2Licence": False, "servedChange": False,
        "use": "research sensitivity only; never replace the served Al proxy",
        "sources": {
            "elemental_thermodynamics": "Mondal et al. 2023, Materials 16, 50; Eq.1 p.2, Table1 p.3; https://doi.org/10.3390/ma16010050",
            "elemental_pressure_fits": "Same paper Eq.2 p.4, Table2 p.7; Al/Si/Fe valid locally; Mg polynomial never extrapolated",
            "composition": "Liu and Gibbons, SFF 2023, Controlling chemical composition changes in laser powder bed fusion of AlSi10Mg; Table1 printed p.341/PDFp.3; feedstock composition, not depth data; https://utw10945.utweb.utexas.edu/sites/default/files/2023/027%20ControllingChemicalCompositionChangesinLaserPowderBedFusionofAlSi10Mg.pdf",
            "atomic_masses": "CIAAW aluminium.htm (Al 26.9815384); abridged-atomic-weights.htm 2024 (Mg24.305 Si28.085 Fe55.845); accessed 2026-10-14",
        },
        "element_constants": ELEMENTS, "fit_coefficients": FITS,
        "composition_rule": "Measured feedstock Al/Si/Mg/Fe entries sum to100 wt%; other elements unreported and omitted, not measured zeros; liquid surface chemistry unknown",
        "equations": {
            "cc": "p_i/atm=exp[(H_i/R)(1/Tb_i-1/T)]",
            "fit": "log10(p_i/atm)=-A_i/T+B_i+C_i log10(T)+1e-3 D_i T",
            "liquid": "x_i=(w_i/M_i)/sum_j(w_j/M_j)",
            "mixture": "P/atm=sum_i x_i p_i/atm; solve P=1atm; y_i=x_i p_i/P",
            "effective_constants": "M=sum_i y_i M_i; H_table=sum_i y_i H_i; H_local=sum_i y_i R T^2 dln(p_i)/dT; L=H/M",
        },
        "numerics": {"R_J_molK": R_GAS, "temperature_bracket_K": [1800, 3000],
                     "temperature_abs_tolerance_K": 1e-9, "max_iterations": 80,
                     "monotonicity": "Each included pressure law increases throughout this bracket"},
        "primary_hybrid": primary, "independent_all_cc": cc,
        "pure_al_proxy": {"T_v_K": pure_al["Tb_K"], "H_J_mol": pure_al["H_J_mol"],
                          "M_kg_mol": pure_al["M_kg_mol"], "L_v_J_kg": pure_al["H_J_mol"] / pure_al["M_kg_mol"],
                          "basis": "pure Al constant-H proxy, not measured AlSi10Mg"},
        "proposed_rounded_triple": proposed,
        "proposed_relative_errors": {
            "T_v": proposed["T_v_K"] / primary["T_v_K"] - 1,
            "L_v_local_slope": proposed["L_v_J_kg"] / primary["L_local_slope_J_kg"] - 1,
            "M": proposed["M_kg_mol"] / primary["M_vapour_kg_mol"] - 1,
        },
        "synthetic_composition_sensitivities": sensitivities,
        "limitations": [
            "Ideal Raoult activities, equilibrium monatomic ideal vapour, no selective depletion or Knudsen layer",
            "Mg CC extrapolation reaches >150atm pure pressure; Mondal synthesizes only to10atm; not a located validated vapour law at this pressure",
            "Hybrid local-slope H differs from weighted tabulated H; rounded6.8MJ/kg corresponds to the former, not a universal latent heat",
            "Nominal powder composition is not the evolving liquid surface composition; missing Zn and other trace activities could move the root",
            "No alloy boiling/latent-heat measurement, blind test, fitted depth or measured depth enters this calculation",
            "Registered MELT O8 additionally required independent Opus recomputation before a scored S2 freeze; this script does not grant it",
        ],
    }


def self_checks(record: dict) -> None:
    for route in ("hybrid", "cc"):
        for symbol in ELEMENTS:
            vals = [pressure_atm(symbol, t, route) for t in range(1800, 3001, 100)]
            assert all(a < b for a, b in zip(vals, vals[1:]))
    cc = record["independent_all_cc"]
    assert math.isclose(cc["T_v_K"], 2471.72850385532, rel_tol=0, abs_tol=1e-8)
    assert math.isclose(cc["M_vapour_kg_mol"], 0.024921287780114803, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(cc["L_table_weighted_J_kg"], 6700437.223773384, rel_tol=0, abs_tol=0.001)
    primary = record["primary_hybrid"]
    assert math.isclose(primary["T_v_K"], 2477.605213217703, rel_tol=0, abs_tol=1e-8)
    assert math.isclose(primary["M_vapour_kg_mol"], 0.024889589126757754, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(primary["L_local_slope_J_kg"], 6823019.62479557, rel_tol=0, abs_tol=0.001)
    # An independent central finite difference checks the analytic logarithmic slope.
    t, step = primary["T_v_K"], 0.02
    for symbol in ELEMENTS:
        derivative = (math.log(pressure_atm(symbol, t + step, "hybrid"))
                      - math.log(pressure_atm(symbol, t - step, "hybrid"))) / (2 * step)
        numerical_h = R_GAS * t ** 2 * derivative
        assert math.isclose(numerical_h, fit_enthalpy_J_mol(symbol, t, "hybrid"),
                            rel_tol=0, abs_tol=0.01)
    zero_mg = vapour_constants(composition(0.0))
    assert zero_mg["vapour_mole_fractions"]["Mg"] == 0.0
    assert zero_mg["partial_pressures_atm"]["Mg"] == 0.0
    assert math.isclose(zero_mg["T_v_K"], 2764.433435472074, rel_tol=0, abs_tol=1e-8)
    assert math.isclose(pressure_atm("Al", ELEMENTS["Al"]["Tb_K"], "cc"),
                        1.0, rel_tol=0, abs_tol=1e-15)
    invalid_calls = [
        lambda: composition(-0.01), lambda: composition(0.450001),
        lambda: composition(math.nan), lambda: pressure_atm("Al", 0.0, "cc"),
        lambda: pressure_atm("Al", math.inf, "cc"),
        lambda: pressure_atm("Al", 1199.0, "hybrid"),
        lambda: pressure_atm("Al", 3371.0, "hybrid"),
        lambda: pressure_atm("Al", t, "unknown"),
        lambda: vapour_constants({**COMPOSITION_WT_PCT, "Al": 90.0}),
        lambda: vapour_constants(COMPOSITION_WT_PCT, mg_activity_factor=0.0),
    ]
    for invalid_call in invalid_calls:
        try:
            invalid_call()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid calculation input was accepted")
    for rec in [record["primary_hybrid"], cc, *record["synthetic_composition_sensitivities"]]:
        assert rec["root_pressure_residual_atm"] < 1e-10
        assert abs(sum(rec["vapour_mole_fractions"].values()) - 1) < 1e-14
        assert math.isclose(rec["L_table_weighted_J_kg"] * rec["M_vapour_kg_mol"], rec["H_table_weighted_J_mol"], rel_tol=1e-14)
    assert record["primary_hybrid"]["vapour_mole_fractions"]["Mg"] > 0.75
    assert record["primary_hybrid"]["mg_above_mondal_synthesized_pressure_limit"]
    assert not record["servedChange"] and not record["experimentalValidation"]
    json.dumps(record, allow_nan=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare output without writing")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_suffix(".json"))
    args = parser.parse_args()
    record = build_record()
    self_checks(record)
    rendered = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n"
    if args.check:
        if args.output.read_text(encoding="utf-8") != rendered:
            raise RuntimeError("O8 output does not exactly reproduce")
    else:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    primary = record["primary_hybrid"]
    print(f"O8 reproducible {'CHECK PASS' if args.check else 'written'}: T={primary['T_v_K']:.6f} K, "
          f"M={primary['M_vapour_kg_mol']:.9f} kg/mol, "
          f"L_local={primary['L_local_slope_J_kg']:.3f} J/kg; research sensitivity only")


if __name__ == "__main__":
    main()
