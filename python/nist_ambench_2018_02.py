#!/usr/bin/env python3
"""
NIST AM-Bench AMB2018-02 melt-pool geometry reference (Lane et al., IMMI 2020 Table 4).

Benchmark alloy is IN625 on EOS M270-class CBM. Four locked MetalliX alloys have no
direct AM-Bench coverage; IN718 is marked proxy_only. Numbers from published Table 4 —
not invented. DOI: 10.1007/s40192-020-00169-1
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

SOURCE = {
    "challenge": "AMB2018-02",
    "subChallenge": "CHAL-AMB2018-02-MP",
    "alloy": "IN625",
    "machine": "CBM (EOS M270-class commercial build machine)",
    "spotDiameter_um": 100.0,
    "substrate": "bare plate (no powder)",
    "doi": "10.1007/s40192-020-00169-1",
    "url": "https://www.nist.gov/ambench/benchmark-test-data",
    "table": "Lane et al., Integrating Materials and Manufacturing Innovation (2020), Table 4 CBM class means",
    "citation": (
        "Lane B. et al. (2020) Measurements of Melt Pool Geometry and Cooling Rates of "
        "Individual Laser Traces on IN625 Bare Plates. Integr Mater Manuf Innov. "
        "doi:10.1007/s40192-020-00169-1"
    ),
}

CBM_CASES: List[Dict[str, Any]] = [
    {
        "caseId": "CBM-A",
        "power_W": 150.0,
        "speed_mm_s": 400.0,
        "length_um": 659.0,
        "width_um": 171.0,
        "depth_um": 151.0,
    },
    {
        "caseId": "CBM-B",
        "power_W": 195.0,
        "speed_mm_s": 800.0,
        "length_um": 780.0,
        "width_um": 133.0,
        "depth_um": 91.0,
    },
    {
        "caseId": "CBM-C",
        "power_W": 195.0,
        "speed_mm_s": 1200.0,
        "length_um": 754.0,
        "width_um": 100.0,
        "depth_um": 60.0,
    },
]

IN625_VALIDATION_PROPS = {
    "base": "Ni",
    "liquidus_C": 1350.0,
    "solidus_C": 1290.0,
    "boiling_C": 2730.0,
    "M_molar_kg_mol": 0.0587,
    "density_kg_m3": 8440.0,
    "density_liquid_kg_m3": 7600.0,
    "thermal_conductivity_W_mK": 9.8,
    "thermal_conductivity_liquid_W_mK": 25.0,
    "specific_heat_J_kgK": 410.0,
    "specific_heat_liquid_J_kgK": 620.0,
    "latent_heat_fusion_J_kg": 290000.0,
    "latent_heat_vap_J_kg": 6400000.0,
    "absorptivity_IR": 0.32,
    "absorptivity_Green": 0.50,
    "surface_tension_N_m": 1.8,
    "d_gamma_dT_N_mK": -0.00038,
    "viscosity_Pa_s": 0.006,
    "thermal_expansion_1_K": 13.1e-6,
    "youngs_modulus_GPa": 205.0,
    "poissons_ratio": 0.29,
    # unused since P7a (2026-10-11): the solver reads neither; kept so the AM-Bench property hash does not move.
    "pdas_A1": 80.0,
    "sdas_B1": 42.0,
}

FOUR_ALLOY_AMBENCH_COVERAGE = {
    "ti6al4v": {
        "status": "no_coverage",
        "note": "NIST AMB2018-02 is IN625 only; no Ti-6Al-4V AM-Bench melt-pool table in this module.",
    },
    "ss316l": {
        "status": "no_coverage",
        "note": "NIST AMB2018-02 is IN625 only; no 316L AM-Bench melt-pool table in this module.",
    },
    "alsi10mg": {
        "status": "no_coverage",
        "note": "NIST AMB2018-02 is IN625 only; no AlSi10Mg AM-Bench melt-pool table in this module.",
    },
    "in718": {
        "status": "proxy_only",
        "note": (
            "No IN718 AM-Bench case. Job attaches NIST IN625 CBM validation (separate alloy). "
            "Not alloy-matched qualification."
        ),
    },
}


def _mape(pred: float, ref: float) -> Optional[float]:
    if ref is None or abs(ref) < 1e-9:
        return None
    return abs(pred - ref) / abs(ref) * 100.0


def compare_case_to_nist(pred_L: float, pred_W: float, pred_D: float, case: Dict[str, Any]) -> Dict[str, Any]:
    mape_L = _mape(pred_L, float(case["length_um"]))
    mape_W = _mape(pred_W, float(case["width_um"]))
    mape_D = _mape(pred_D, float(case["depth_um"]))
    maps = [m for m in (mape_L, mape_W, mape_D) if m is not None]
    return {
        "caseId": case["caseId"],
        "nist": {
            "length_um": case["length_um"],
            "width_um": case["width_um"],
            "depth_um": case["depth_um"],
        },
        "predicted": {
            "length_um": round(pred_L, 2),
            "width_um": round(pred_W, 2),
            "depth_um": round(pred_D, 2),
        },
        "mape_pct": {
            "length": None if mape_L is None else round(mape_L, 2),
            "width": None if mape_W is None else round(mape_W, 2),
            "depth": None if mape_D is None else round(mape_D, 2),
            "mean": None if not maps else round(sum(maps) / len(maps), 2),
        },
    }


def run_ambench_validation(thermal_fn, material_props=None) -> Dict[str, Any]:
    """Compare IN625 bare-plate cases using one copied property set per run."""
    # The caller may supply its hashed snapshot. Direct callers retain the
    # original default, but all three cases use the same copied properties.
    props = dict(IN625_VALIDATION_PROPS if material_props is None else material_props)
    cases_out = []
    mean_mapes = []
    for case in CBM_CASES:
        th = thermal_fn(
            float(case["power_W"]),
            float(case["speed_mm_s"]),
            float(SOURCE["spotDiameter_um"]),
            dict(props),
        )
        geo = th["meltPoolGeometry"]
        row = compare_case_to_nist(
            float(geo["length_um"]),
            float(geo["width_um"]),
            float(geo["depth_um"]),
            case,
        )
        extent_status = str(geo.get("extentStatus") or "not-reported")
        row["extentStatus"] = extent_status
        row["extentNote"] = geo.get("extentNote")
        if extent_status == "computed":
            row["status"] = "computed"
            if row["mape_pct"]["mean"] is not None:
                mean_mapes.append(row["mape_pct"]["mean"])
        else:
            # Heuristic / floored / box-limited extent is not a liquidus isotherm: the row is
            # reported but carries no error and never enters the overall mean.
            row["status"] = "not-computed"
            row["mape_pct"] = None
            row["predictedIsHeuristic"] = True
        cases_out.append(row)

    overall = None if not mean_mapes else round(sum(mean_mapes) / len(mean_mapes), 2)
    not_computed = len(cases_out) - len(mean_mapes)
    return {
        "source": SOURCE,
        "model": "rosenthal-screening-v1",
        "disclaimer": (
            "SCREENING ONLY. Bare-plate IN625 AM-Bench vs analytical Rosenthal; "
            "not powder-bed, not Goldak FEA, not a pass/fail qualification gate."
        ),
        "cases": cases_out,
        "overallMeanMape_pct": overall,
        "computedCases": len(mean_mapes),
        "notComputedCases": not_computed,
        "overallNote": (
            "overallMeanMape_pct is the mean over cases whose melt-pool extent is a computed "
            "liquidus isotherm (extentStatus 'computed') only; cases with status 'not-computed' "
            "(heuristic fallback, width floor or search-box limit) are listed without an error "
            "and excluded. null when no case is computed."
        ),
        "fourAlloyCoverage": FOUR_ALLOY_AMBENCH_COVERAGE,
    }


def coverage_for_alloy(alloy_id: str) -> Dict[str, Any]:
    return FOUR_ALLOY_AMBENCH_COVERAGE.get(
        alloy_id,
        {"status": "no_coverage", "note": f"Unknown alloyId {alloy_id}."},
    )
