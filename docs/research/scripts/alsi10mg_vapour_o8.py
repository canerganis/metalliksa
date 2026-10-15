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


def pressure_atm(symbol: str, temperature_K: float, route: str,
                 mg_boiling_temperature_K: float = 1383.0) -> float:
    if not math.isfinite(temperature_K) or temperature_K <= 0:
        raise ValueError("temperature must be finite and positive")
    if route not in ("hybrid", "cc"):
        raise ValueError("unknown elemental pressure route")
    if mg_boiling_temperature_K not in (1363.0, 1383.0):
        raise ValueError("Mg boiling temperature must select the recorded 1363 or 1383 K scenario")
    if route == "hybrid" and symbol in FITS:
        fit = FITS[symbol]
        if not fit["range_K"][0] <= temperature_K <= fit["range_K"][1]:
            raise ValueError("elemental fit outside declared temperature range")
        a, b, c, d = fit["coefficients"]
        return 10 ** (-a / temperature_K + b + c * math.log10(temperature_K)
                      + 1e-3 * d * temperature_K)
    element = ELEMENTS[symbol]
    # Mondal Eq.1 p.2, constant-H ideal-gas Clausius-Clapeyron.
    boiling_temperature = mg_boiling_temperature_K if symbol == "Mg" else element["Tb_K"]
    return math.exp(element["H_J_mol"] / R_GAS
                    * (1 / boiling_temperature - 1 / temperature_K))


def fit_enthalpy_J_mol(symbol: str, temperature_K: float, route: str) -> float:
    """R T^2 d ln(p)/dT; local derivative, not measured latent heat."""
    if route == "hybrid" and symbol in FITS:
        a, _, c, d = FITS[symbol]["coefficients"]
        return R_GAS * (math.log(10) * a + c * temperature_K
                        + math.log(10) * 1e-3 * d * temperature_K ** 2)
    return ELEMENTS[symbol]["H_J_mol"]


def vapour_constants(weights: dict[str, float], route: str = "hybrid",
                     mg_activity_factor: float = 1.0,
                     mg_boiling_temperature_K: float = 1383.0) -> dict:
    if not math.isfinite(mg_activity_factor) or mg_activity_factor <= 0:
        raise ValueError("positive finite Mg activity factor required")
    xs = mole_fractions(weights)

    def partials(t):
        return {s: xs[s] * pressure_atm(s, t, route, mg_boiling_temperature_K)
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
    mg_pressure = pressure_atm("Mg", t, route, mg_boiling_temperature_K)
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


def scenario_envelopes(primary: dict, cc: dict, sensitivities: list[dict]) -> dict:
    """Declared one-family-at-a-time scenarios; no interactions or physical bounds."""
    alternative_tb = vapour_constants(COMPOSITION_WT_PCT, mg_boiling_temperature_K=1363.0)
    definitions = [
        ("nominal", primary, "local-slope", 1383.0, "source-model-transfer",
         "Mondal hybrid Al/Si/Fe fits; Mg constant-H CC; feedstock composition"),
        ("route_all_cc", cc, "table-weighted", 1383.0, "source-model-transfer",
         "All constituents use Mondal constant-H CC; local and table enthalpies coincide"),
        ("latent_heat_table_weighted", primary, "table-weighted", 1383.0, "convention-sensitivity",
         "Same hybrid root and vapour fractions, tabulated constituent enthalpies instead of local pressure derivatives"),
        *[(f"mg_wt_pct_{rec['composition_wt_pct']['Mg']:g}", rec, "local-slope", 1383.0,
           "declared-assumption", "Synthetic feedstock Mg sensitivity; Si/Fe fixed, Al balances mass")
          for rec in sensitivities],
        ("mg_boiling_1363K", alternative_tb, "local-slope", 1363.0, "source-conflict-sensitivity",
         "Liu/Gibbons 1363 K alternative recorded in P8 gate PHY-13; Mondal nominal remains 1383 K"),
    ]
    scenarios = []
    for arm_id, values, convention, tb, provenance_kind, source in definitions:
        scenarios.append({
            "armId": arm_id, "pressureRoute": values["pressure_route"],
            "latentHeatConvention": convention, "mgBoilingTemperature_K": tb,
            "provenance": {"kind": provenance_kind, "source": source},
            "status": "extrapolated", "warnings": ["VAPOUR_PRESSURE_EXTRAPOLATED"],
            "values": {**values, "L_used_J_kg": values[
                "L_local_slope_J_kg" if convention == "local-slope" else "L_table_weighted_J_kg"]},
        })

    def numeric_leaves(values, prefix=""):
        for key, value in values.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                yield from numeric_leaves(value, path)
            elif type(value) in (int, float):
                yield path, value

    # Physical numeric scenario outputs, including constituent percentages and
    # pressures, are covered. One-atmosphere root diagnostics are checked separately:
    # last-decimal ordering of convergence residuals is not a scenario envelope.
    flattened = [dict(numeric_leaves(scenario["values"])) for scenario in scenarios]
    bands = {}
    for field, nominal in flattened[0].items():
        if field in ("root_pressure_residual_atm", "mixture_pressure_atm"):
            continue
        values = [arm[field] for arm in flattened]
        minimum = min(range(len(values)), key=lambda i: (values[i], i))
        maximum = max(range(len(values)), key=lambda i: (values[i], -i))
        bands[field] = {"min": values[minimum], "nominal": nominal, "max": values[maximum],
                        "minArmId": scenarios[minimum]["armId"],
                        "maxArmId": scenarios[maximum]["armId"],
                        "successfulArms": len(scenarios)}
    return {
        "method": "declared-ofat-envelope-v1", "nominalArmId": "nominal",
        "meaning": "Union of named one-family-at-a-time scenarios; no interactions; not a confidence interval, error bar or physical bound",
        "tieBreak": "first declared arm", "completeness": "complete",
        "orderedArmIds": [scenario["armId"] for scenario in scenarios],
        "scenarios": scenarios, "fields": bands,
        "nonBandedNumericDiagnostics": ["mixture_pressure_atm", "root_pressure_residual_atm"],
        "mgBoilingConflictEffect": {
            "alternativeTemperature_K": 1363.0, "nominalTemperature_K": 1383.0,
            "delta_T_v_K": alternative_tb["T_v_K"] - primary["T_v_K"],
            "relative_L_local_slope_change": alternative_tb["L_local_slope_J_kg"] / primary["L_local_slope_J_kg"] - 1,
            "relative_M_vapour_change": alternative_tb["M_vapour_kg_mol"] / primary["M_vapour_kg_mol"] - 1,
        },
    }


def build_record() -> dict:
    primary = vapour_constants(COMPOSITION_WT_PCT)
    cc = vapour_constants(COMPOSITION_WT_PCT, "cc")
    pure_al = ELEMENTS["Al"]
    proposed = {"T_v_K": 2480.0, "L_v_J_kg": 6.8e6, "M_kg_mol": 0.025}
    # This replay cannot establish uncertainty; these are assumption sensitivities.
    sensitivities = [vapour_constants(composition(mg)) for mg in (0.0, 0.2, 0.3, 0.45)]
    return {
        "schema": "metalliksa-alsi10mg-vapour-o8-v2",
        "evidenceKind": "Literature estimate", "moduleMaturity": "Research",
        "validationStatus": "not validated: physical alloy-vapour closure unresolved; no blind test passed",
        "experimentalValidation": False,
        "uiSentence": "Ideal-mixture vapour sensitivity; extrapolated Mg pressure, no blind validation.",
        "o8Status": "reproducibility complete; physical alloy-vapour closure unvalidated",
        "registeredMeltS2Licence": False, "servedChange": False,
        "use": "research sensitivity only, including explicitly labelled Mg-aware onset/cavity/melt-depth sensitivities under amended P8 scope; never replace the served Al proxy",
        "sources": {
            "elemental_thermodynamics": "Mondal et al. 2023, Materials 16, 50; Eq.1 p.2, Table1 p.3; https://doi.org/10.3390/ma16010050",
            "elemental_pressure_fits": "Same paper Eq.2 p.4, Table2 p.7; Al/Si/Fe valid locally; Mg polynomial never extrapolated",
            "composition": "Liu and Gibbons, SFF 2023, Controlling chemical composition changes in laser powder bed fusion of AlSi10Mg; Table1 printed p.341/PDFp.3; feedstock composition, not depth data; https://utw10945.utweb.utexas.edu/sites/default/files/2023/027%20ControllingChemicalCompositionChangesinLaserPowderBedFusionofAlSi10Mg.pdf",
            "atomic_masses": "CIAAW aluminium.htm (Al 26.9815384); abridged-atomic-weights.htm 2024 (Mg24.305 Si28.085 Fe55.845); accessed 2026-10-14",
            "mg_boiling_conflict": "Existing P8 gate PHY-13 records Liu/Gibbons 1363 K versus Mondal Table1 1383 K; source-page locator for the 1363 K statement was not independently refreshed in this replay",
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
        "band": scenario_envelopes(primary, cc, sensitivities),
        "consistencyNote": {
            "status": "extrapolated", "experimentalValidation": False,
            "uiSentence": "This ideal-mixture scenario uses feedstock composition, not the specimen or evolving liquid surface; Mg pressure exceeds its source scope and all dependent outputs are explicit sensitivities.",
            "validRange": {
                "mg_fitted_temperature_K": MG_FIT_RANGE_K,
                "mondal_synthesized_pressure_ceiling_atm": 10.0,
                "synthetic_mg_wt_pct": [0.0, 0.45],
                "physical_alloy_validity_range": None,
                "physical_range_reason": "SOURCE_RANGE_NOT_ESTABLISHED",
            },
            "assumptions": [
                "Measured source feedstock composition is transferred, not measured specimen or instantaneous liquid-surface composition",
                "Ideal Raoult mixing, monatomic equilibrium ideal vapour, no selective depletion or Knudsen layer",
                "Nominal: hybrid Al/Si/Fe fits, Mg constant-H CC with Tb=1383 K, local pressure-derivative latent heat",
                "All-CC and table-weighted enthalpy are distinct declared conventions; never silently substitute either for nominal",
                "Mg 0..0.45 wt% changes are synthetic composition scenarios, not measurement uncertainty",
                "Pure Mg pressure is the extrapolated elemental law at the mixture root, not the Raoult mixture Mg partial pressure; zero-Mg arms have exactly zero mixture Mg partial pressure",
                "Mg-aware onset, cavity and melt-depth outputs are permitted only as labelled research sensitivities in amended P8 scope",
                "No served output, scoring licence or physical validation follows from replay success",
            ],
            "knownContradictions": [
                "Mg CC pure partial-pressure law is extrapolated beyond the 600..1730 K fit and 10 atm synthesized-pressure ceiling; mixture total 1 atm does not make the pure Mg pressure in range",
                "Liu/Gibbons Mg Tb=1363 K conflicts with Mondal Tb=1383 K; the named alternative is a source-conflict sensitivity, not a resolved material identity",
                "Local-derivative latent heat and table-weighted constituent enthalpy differ under the hybrid route",
            ],
        },
        "replayComparison": {
            "method": "exact JSON structure and metadata; tolerant finite numeric leaves",
            "relativeTolerance": 2e-12,
            "absoluteTolerances": {"temperature_K": 1e-8, "enthalpy_or_latentHeat": 0.001,
                                   "pressure_atm": 1e-8, "other": 1e-12},
            "zeroPolicy": "physical zeros exact; root residual diagnostic tolerant; no missing or additional fields; list order, source constants and provenance exact",
        },
        "limitations": [
            "Ideal Raoult activities, equilibrium monatomic ideal vapour, no selective depletion or Knudsen layer",
            "Mg CC extrapolation reaches >150atm pure pressure; Mondal synthesizes only to10atm; not a located validated vapour law at this pressure",
            "Hybrid local-slope H differs from weighted tabulated H; rounded6.8MJ/kg corresponds to the former, not a universal latent heat",
            "Nominal powder composition is not the evolving liquid surface composition; missing Zn and other trace activities could move the root",
            "Mg Tb1363 K versus nominal1383 K is retained as a source-conflict sensitivity; nominal constants stay unchanged",
            "No alloy boiling/latent-heat measurement, blind test, fitted depth or measured depth enters this calculation",
            "Registered MELT O8 additionally required independent Opus recomputation before a scored S2 freeze; this script does not grant it",
        ],
    }


def compare_records(actual, expected, path: tuple[str, ...] = ()) -> None:
    """Compare decoded JSON without depending on libm's last decimal or newlines."""
    location = ".".join(path) or "root"
    if type(actual) in (int, float) and type(expected) in (int, float):
        if not math.isfinite(actual) or not math.isfinite(expected):
            raise RuntimeError(f"O8 nonfinite numeric leaf at {location}")
        metadata = (any(key in ("element_constants", "fit_coefficients", "numerics", "replayComparison") for key in path)
                    or path and path[-1] in ("mgBoilingTemperature_K", "alternativeTemperature_K", "nominalTemperature_K", "successfulArms"))
        # Preserve source/input metadata and physical zero constraints exactly;
        # a root pressure residual may reach exact zero on another libm.
        if metadata or type(actual) is int or type(expected) is int:
            matches = type(actual) is type(expected) and actual == expected
        elif any("root_pressure_residual_atm" in key for key in path):
            matches = math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12)
        elif actual == 0 or expected == 0:
            matches = actual == expected
        else:
            if any(key.endswith("_K") for key in path):
                absolute_tolerance = 1e-8
            elif any("_J_kg" in key or "_J_mol" in key for key in path):
                absolute_tolerance = 0.001
            elif any("_atm" in key for key in path):
                absolute_tolerance = 1e-8
            else:
                absolute_tolerance = 1e-12
            matches = math.isclose(actual, expected, rel_tol=2e-12,
                                   abs_tol=absolute_tolerance)
        if not matches:
            raise RuntimeError(f"O8 numeric replay mismatch at {location}: {actual!r} != {expected!r}")
        return
    if type(actual) is not type(expected):
        raise RuntimeError(f"O8 replay type mismatch at {location}")
    if isinstance(actual, dict):
        if actual.keys() != expected.keys():
            raise RuntimeError(f"O8 replay field mismatch at {location}")
        for key in actual:
            compare_records(actual[key], expected[key], (*path, key))
    elif isinstance(actual, list):
        if len(actual) != len(expected):
            raise RuntimeError(f"O8 replay list length mismatch at {location}")
        for index, (a, e) in enumerate(zip(actual, expected)):
            compare_records(a, e, (*path, str(index)))
    elif actual != expected:
        raise RuntimeError(f"O8 replay metadata mismatch at {location}")


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
        lambda: vapour_constants(COMPOSITION_WT_PCT, mg_boiling_temperature_K=1373.0),
    ]
    for invalid_call in invalid_calls:
        try:
            invalid_call()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid calculation input was accepted")
    for scenario in record["band"]["scenarios"]:
        rec = scenario["values"]
        assert rec["root_pressure_residual_atm"] < 1e-10
        assert abs(sum(rec["vapour_mole_fractions"].values()) - 1) < 1e-14
        assert math.isclose(rec["L_table_weighted_J_kg"] * rec["M_vapour_kg_mol"], rec["H_table_weighted_J_mol"], rel_tol=1e-14)
        assert math.isclose(rec["L_local_slope_J_kg"] * rec["M_vapour_kg_mol"], rec["H_local_slope_J_mol"], rel_tol=1e-14)
    assert len(record["band"]["scenarios"]) == 8
    assert len(set(record["band"]["orderedArmIds"])) == 8
    for band in record["band"]["fields"].values():
        assert band["min"] <= band["nominal"] <= band["max"]
        assert band["minArmId"] in record["band"]["orderedArmIds"]
        assert band["maxArmId"] in record["band"]["orderedArmIds"]
    effect = record["band"]["mgBoilingConflictEffect"]
    assert -42 < effect["delta_T_v_K"] < -40
    assert -0.044 < effect["relative_L_local_slope_change"] < -0.042
    # Portability tolerance accepts a last-decimal change while schema/provenance,
    # categorical types, exact zeros and meaningful numeric drift are rejected.
    compare_records({"T_v_K": primary["T_v_K"] + 1e-9}, {"T_v_K": primary["T_v_K"]})
    compare_records({"L_local_slope_J_kg": primary["L_local_slope_J_kg"] + 1e-4},
                    {"L_local_slope_J_kg": primary["L_local_slope_J_kg"]})
    for a, e in [({"T_v_K": primary["T_v_K"] + 0.001}, {"T_v_K": primary["T_v_K"]}),
                 ({"x": 1}, {"x": True}), ({"x": 1e-15}, {"x": 0.0}),
                 ({"x": 1.0, "extra": None}, {"x": 1.0}),
                 (["nominal", "cc"], ["cc", "nominal"]),
                 ({"source": "altered"}, {"source": "nominal"}),
                 ({"x": math.nan}, {"x": 1.0})]:
        try:
            compare_records(a, e)
        except RuntimeError:
            pass
        else:
            raise AssertionError("replay comparator accepted a meaningful change")
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
        stored = json.loads(args.output.read_text(encoding="utf-8"))
        compare_records(record, stored)
    else:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    primary = record["primary_hybrid"]
    print(f"O8 reproducible {'CHECK PASS' if args.check else 'written'}: T={primary['T_v_K']:.6f} K, "
          f"M={primary['M_vapour_kg_mol']:.9f} kg/mol, "
          f"L_local={primary['L_local_slope_J_kg']:.3f} J/kg; research sensitivity only")


if __name__ == "__main__":
    main()
