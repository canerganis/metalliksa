#!/usr/bin/env python3
"""SOL-A1 G/R request transport: direct thermal front envelopes, with no liquidus admission bypass.

The analytic centreline and binary trapping helpers are standalone offline test utilities; the served route
projects only the source-bounded thermal container. Default LPBF CET remains outside its source model domain.
"""
from __future__ import annotations

import contextlib
import json
import math
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Tuple

import lpbf_cet_screening as cet_mod
from lpbf_job_cache import BUILD_JOB_SOLVER_REVISION

SCHEMA = "lpbf-gr-solidification-2"
ENGINE = "lpbf_gr_solidification"
SUPPORTED: Dict[str, str] = {"in718": "in718", "in625": "Inconel 625", "ti6al4v": "ti6al4v", "alsi10mg": "alsi10mg", "ss316l": "ss316l"}
MATERIAL_NAMES: Dict[str, str] = {"in718": "Inconel 718", "in625": "Inconel 625", "ti6al4v": "Ti-6Al-4V", "alsi10mg": "AlSi10Mg", "ss316l": "316L Stainless Steel"}
STATUSES = ("computed", "partial", "unavailable", "failed", "not-requested")
LOCATIONS = ("bottom", "median", "tail")
MIN_AXIS_DEFAULT_N = 11

# Wording table: pending maintainer approval (SOL-A, MD2).
WORDING = {"evidence": "Screening only", "experimentalLimit": "No experimental comparison."}
EVIDENCE_STATEMENT = WORDING["evidence"]
LIMITS: List[str] = [WORDING["experimentalLimit"]]

LAVES_BASIS = (
    "Binary C = 0 gamma/Laves eutectic-type constituent, fraction of the liquid, nominal Nb; Aziz-trapped k(R) at the "
    "sampled rear-arc R and V_D 0.23-0.31 m/s"
)
LAVES_NOTE = (
    "Binary C = 0 gamma/Laves eutectic-type constituent, fraction of the liquid, nominal Nb; upper bound with respect to "
    "back-diffusion, tip undercooling and carbon, and over the V_D range and the sampled rear arc only. At the deepest "
    "liquidus point n_x = 0 so R -> 0 and k(R) -> k_e: over the whole boundary the bound is equilibriumKBound."
)
IN625_PHASE_NOTE = " Phase identity (Laves or NbC) not established (C88, D96)."


def _refuse(message: str, kind: str = "validation") -> Dict[str, Any]:
    return {"success": False, "errorKind": kind, "error": message}


def _finite(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _clean(obj: Any) -> Any:
    """Recursively replace non-finite floats with None so allow_nan=False output is always valid."""
    if isinstance(obj, float):
        return _finite(obj)
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    return obj


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def resolve_gr_alloy(raw: Any) -> Optional[str]:
    from solidification_front import canonical_alloy_id
    return canonical_alloy_id(raw)


def _liquidus_C(alloy_id: str) -> float:
    from four_alloy_materials import thermal_props
    from lpbf_thermal_solver import SECONDARY_THERMOPHYSICAL_DB
    material = SUPPORTED[alloy_id]
    props = thermal_props(material) or SECONDARY_THERMOPHYSICAL_DB[material]
    return float(props["liquidus_C"])


def _solidus_C(alloy_id: str) -> float:
    from four_alloy_materials import thermal_props
    from lpbf_thermal_solver import SECONDARY_THERMOPHYSICAL_DB
    material = SUPPORTED[alloy_id]
    props = thermal_props(material) or SECONDARY_THERMOPHYSICAL_DB[material]
    return float(props["solidus_C"])


def rosenthal_centerline_tail(power_W: float, conductivity_W_mK: float, liquidus_C: float, preheat_C: float,
                              speed_m_s: float, cos_theta: float = 1.0) -> Dict[str, float]:
    """E2: pure point-source trailing surface-centreline reference at the liquidus (see module docstring)."""
    for name, value in (("power_W", power_W), ("conductivity_W_mK", conductivity_W_mK), ("speed_m_s", speed_m_s)):
        if not _is_num(value) or not value > 0:
            raise ValueError(f"{name} must be a finite number > 0 (got {value!r})")
    for name, value in (("liquidus_C", liquidus_C), ("preheat_C", preheat_C), ("cos_theta", cos_theta)):
        if not _is_num(value):
            raise ValueError(f"{name} must be a finite number (got {value!r})")
    d_t = float(liquidus_C) - float(preheat_C)
    if not d_t > 0:
        raise ValueError("liquidus_C must be above preheat_C")
    p, k, v = float(power_W), float(conductivity_W_mK), float(speed_m_s)
    x_tail_m = p / (2.0 * math.pi * k * d_t)
    g = 2.0 * math.pi * k * d_t * d_t / p
    r = v * float(cos_theta)
    return {
        "xTail_um": x_tail_m * 1.0e6,
        "G_K_m": g,
        "R_m_s": r,
        "GoverR_K_s_m2": g / max(1.0e-6, r),
        "GtimesR_K_s": g * r,
    }


def laves_trapping(alloy_id: str, r_points: Mapping[str, Optional[float]]) -> Dict[str, Any]:
    """Aziz-trapped binary Scheil bound on the gamma/Laves constituent at the present, positive R values."""
    from lpbf_solidification_segregation import (
        V_D_VALUES, aziz_partition_coefficient, binary_laves_inputs, scheil_eutectic_fraction)
    inp = binary_laves_inputs(alloy_id)
    k_e, c_e, nb = inp["k_e"], inp["C_e_wt"], inp["Nb_nominal_wt"]
    v_ds = sorted(float(v["value"]) for v in V_D_VALUES)
    present = {name: float(r) for name, r in r_points.items() if _is_num(r) and r > 0}
    if not present:
        return {"status": "unavailable", "reason": "no positive solidification rate at any sampled location"}

    def at(r: float, v_d: float) -> Tuple[float, float]:
        k = aziz_partition_coefficient(k_e, r, v_d)
        return k, scheil_eutectic_fraction(nb, c_e, k)

    name_min = min(present, key=lambda n: present[n])
    r_min = present[name_min]
    k_ub, f_ub = at(r_min, max(v_ds))
    note = LAVES_NOTE + (IN625_PHASE_NOTE if alloy_id == "in625" else "")

    def band(name: str) -> Optional[Dict[str, Any]]:
        if name not in present:
            return None
        pairs = [at(present[name], vd) for vd in v_ds]
        ks = [p[0] for p in pairs]
        fs = [p[1] for p in pairs]
        return {"R_m_s": present[name], "kEff": {"min": round(min(ks), 6), "max": round(max(ks), 6)},
                "f": {"min": round(min(fs), 4), "max": round(max(fs), 4)}}

    return {
        "status": "available",
        "reason": None,
        "equilibriumKBound": round(scheil_eutectic_fraction(nb, c_e, k_e), 4),
        "sampledArcUpperBound": {"R_m_s": r_min, "V_D_m_s": max(v_ds), "kEff": round(k_ub, 6), "f": round(f_ub, 4),
                                 "location": name_min},
        "atMedian": band("median"),
        "atTail": band("tail"),
        "note": note,
    }


def _dependent_block(definition: str, name: str, code: str) -> Dict[str, Any]:
    from quantity_envelope import container, reason, unavailable
    return {"status": "unavailable", **container({name: unavailable(definition, [reason(code)])})}


def _unavailable_body(status: str, reason: str) -> Dict[str, Any]:
    from lpbf_solidification_microstructure import project_build_job_microstructure
    from quantity_envelope import reason as coded_reason
    front = project_build_job_microstructure({})
    if status == "failed":
        for q in front["quantities"].values():
            q.update(status="failed", reasons=[coded_reason("solver-error")])
        front["status"] = status
    return {"status": status, "regime": None, "normalizedEnthalpy": None, "extentStatus": None,
            "front": front,
            "cet": _dependent_block("cet-class", "class", "outside-source-model-domain"),
            "laves": _dependent_block("laves-trapped-scheil-fraction", "fraction", "parent-unavailable")}


def couple_thermal_block(thermal: Mapping[str, Any], alloy_id: str, *, preheat_C: float, speed_mm_s: float,
                         cet_constants_override: Optional[Mapping[str, float]] = None) -> Dict[str, Any]:
    """Project the admitted front; never bypass its liquidus admission through an analytic reference."""
    from lpbf_solidification_microstructure import project_build_job_microstructure
    front = project_build_job_microstructure(dict(thermal))
    geometry = thermal.get("meltPoolGeometry") or {}
    process = thermal.get("processParameters") or {}
    return {"status": front["status"], "regime": geometry.get("regime"),
            "normalizedEnthalpy": process.get("normalizedEnthalpy"), "extentStatus": geometry.get("extentStatus"),
            "front": front,
            "cet": _dependent_block("cet-class", "class", "outside-source-model-domain"),
            "laves": _dependent_block("laves-trapped-scheil-fraction", "fraction", "parent-unavailable")}


def _thermal(alloy_id: str, power_W: float, speed_mm_s: float, s: Mapping[str, Any]) -> Dict[str, Any]:
    from lpbf_thermal_solver import calculate_meltpool_physics
    return calculate_meltpool_physics(
        SUPPORTED[alloy_id], float(power_W), float(speed_mm_s), float(s["beamDiameter_um"]), float(s["preheatTemp_C"]),
        float(s["layer_um"]), float(s["hatch_um"]), "IR_1064nm")


def _eval(alloy_id: str, power_W: float, speed_mm_s: float, s: Mapping[str, Any]) -> Tuple[Dict[str, Any], Any]:
    try:
        thermal = _thermal(alloy_id, power_W, speed_mm_s, s)
        body = couple_thermal_block(thermal, alloy_id, preheat_C=float(s["preheatTemp_C"]), speed_mm_s=float(speed_mm_s))
        return body, thermal.get("materialEvidence")
    except Exception as e:  # a failed cell is an error, never coloured as a result
        return _unavailable_body("failed", f"{type(e).__name__}: {e}"), None


def evaluate_point(alloy_id: str, power_W: float, speed_mm_s: float, settings: Mapping[str, Any]) -> Dict[str, Any]:
    return _eval(alloy_id, power_W, speed_mm_s, settings)[0]


def validate_request(data: Any) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    from four_alloy_materials import LITERATURE_PV_WINDOWS
    from lpbf_process_window import (
        MAX_CELLS, MAX_POWER_W, MAX_SPEED_MM_S, _axis_from_request, _linspace, _num,
        DEFAULT_RANGE_LOW_FACTOR, DEFAULT_RANGE_HIGH_FACTOR)
    if not isinstance(data, dict):
        return None, _refuse("Request body must be a JSON object.")
    mode = data.get("mode")
    if mode not in ("point", "map"):
        return None, _refuse("mode must be 'point' or 'map'.")
    alloy = resolve_gr_alloy(data.get("alloyId"))
    if alloy is None:
        return None, _refuse("Unknown alloy ID; no fallback alloy.")
    try:
        beam = _num(data.get("beamDiameter_um"), "beamDiameter_um")
        layer = _num(data.get("layer_um"), "layer_um")
        hatch = _num(data.get("hatch_um"), "hatch_um")
        preheat = _num(data.get("preheatTemp_C"), "preheatTemp_C")
    except ValueError as e:
        return None, _refuse(str(e))
    for name, value in (("beamDiameter_um", beam), ("layer_um", layer), ("hatch_um", hatch)):
        if not value > 0:
            return None, _refuse(f"{name} must be > 0 (got {value:g}).")
    solidus = _solidus_C(alloy)
    if not (0 <= preheat < solidus):
        return None, _refuse(f"preheatTemp_C must be >= 0 and below the {alloy} solidus ({solidus:g} C).")
    norm: Dict[str, Any] = {"mode": mode, "alloyId": alloy, "beamDiameter_um": beam, "layer_um": layer,
                            "hatch_um": hatch, "preheatTemp_C": preheat}
    try:
        if mode == "point":
            power = _num(data.get("power_W"), "power_W")
            speed = _num(data.get("speed_mm_s"), "speed_mm_s")
            if not (0 < power <= MAX_POWER_W):
                return None, _refuse(f"power_W must be > 0 and <= {MAX_POWER_W:g} W (got {power:g}).")
            if not (0 < speed <= MAX_SPEED_MM_S):
                return None, _refuse(f"speed_mm_s must be > 0 and <= {MAX_SPEED_MM_S:g} mm/s (got {speed:g}).")
            norm.update(power_W=power, speed_mm_s=speed)
            return norm, None
        box = LITERATURE_PV_WINDOWS.get(alloy)
        basis = {"power": "request", "speed": "request"}
        if data.get("powers") is None or data.get("speeds") is None:
            if box is None:
                return None, _refuse("No literature P-v box for IN625 in four_alloy_materials; give powers and speeds.")
        if data.get("powers") is None:
            powers = _linspace(DEFAULT_RANGE_LOW_FACTOR * box["powerMin_W"], DEFAULT_RANGE_HIGH_FACTOR * box["powerMax_W"],
                               MIN_AXIS_DEFAULT_N)
            basis["power"] = "default"
        else:
            powers = _axis_from_request(data["powers"], "powers", MAX_POWER_W, "W")
        if data.get("speeds") is None:
            speeds = _linspace(DEFAULT_RANGE_LOW_FACTOR * box["speedMin_mm_s"], DEFAULT_RANGE_HIGH_FACTOR * box["speedMax_mm_s"],
                               MIN_AXIS_DEFAULT_N)
            basis["speed"] = "default"
        else:
            speeds = _axis_from_request(data["speeds"], "speeds", MAX_SPEED_MM_S, "mm/s")
    except ValueError as e:
        return None, _refuse(str(e))
    if len(powers) * len(speeds) > MAX_CELLS:
        return None, _refuse(f"At most {MAX_CELLS} cells are allowed (got {len(powers) * len(speeds)}).")
    norm.update(powers=powers, speeds=speeds, _rangeBasis=basis)
    return norm, None


def _counts(bodies: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {k: 0 for k in STATUSES}
    for b in bodies:
        counts[b["status"]] += 1
    return counts


def run_gr_solidification(data: Any) -> Dict[str, Any]:
    from lpbf_solidification_segregation import RAPID_MODEL_ID
    from solidification_front import MODEL_ID as SOLIDIFICATION_MODEL_ID
    t0 = time.time()
    norm, refusal = validate_request(data)
    if refusal is not None:
        return refusal
    alloy = norm["alloyId"]
    settings = {k: norm[k] for k in ("beamDiameter_um", "layer_um", "hatch_um", "preheatTemp_C")}
    request: Dict[str, Any] = {"alloyId": alloy, **settings}
    response: Dict[str, Any] = {"success": True, "engine": ENGINE, "schema": SCHEMA, "mode": norm["mode"],
                                "alloyId": alloy, "materialName": MATERIAL_NAMES[alloy]}
    evidence = None
    if norm["mode"] == "point":
        request.update(power_W=norm["power_W"], speed_mm_s=norm["speed_mm_s"])
        body, evidence = _eval(alloy, norm["power_W"], norm["speed_mm_s"], settings)
        bodies = [body]
        response["request"] = request
        response["point"] = {"power_W": norm["power_W"], "speed_mm_s": norm["speed_mm_s"], **body}
    else:
        cells = []
        for i, p in enumerate(norm["powers"]):
            for j, v in enumerate(norm["speeds"]):
                body, ev = _eval(alloy, p, v, settings)
                evidence = evidence or ev
                cells.append({"iP": i, "iV": j, "power_W": p, "speed_mm_s": v, **body})
        bodies = cells
        basis = norm["_rangeBasis"]
        response["request"] = request
        response["grid"] = {"powers_W": norm["powers"], "speeds_mm_s": norm["speeds"], "nP": len(norm["powers"]),
                            "nV": len(norm["speeds"]), "nCells": len(cells),
                            "rangeBasis": {
                                "power": {"basis": basis["power"], "min_W": norm["powers"][0], "max_W": norm["powers"][-1],
                                          "n": len(norm["powers"])},
                                "speed": {"basis": basis["speed"], "min_mm_s": norm["speeds"][0],
                                          "max_mm_s": norm["speeds"][-1], "n": len(norm["speeds"])}}}
        response["cells"] = cells
    response["counts"] = _counts(bodies)
    cet_view = cet_mod.criterion_view()
    cet_view["constantsStatus"] = cet_mod.cet_constants(alloy)
    response["cet"] = cet_view
    response["laves"] = {"modelId": RAPID_MODEL_ID}
    response["materialEvidence"] = evidence
    response["evidence"] = {"kind": "screening-only", "experimentalValidation": False, "statement": EVIDENCE_STATEMENT}
    response["limits"] = list(LIMITS)
    response["provenance"] = {"heatSource": "rosenthal", "solidificationModelId": SOLIDIFICATION_MODEL_ID,
                              "buildJobSolverRevision": BUILD_JOB_SOLVER_REVISION, "frozenFilesModified": False}
    response["computeMs"] = round((time.time() - t0) * 1000.0, 1)
    return _clean(response)


def main() -> None:
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps(_refuse("Empty payload.")))
        return
    try:
        data = json.loads(raw)
    except Exception as e:
        print(json.dumps(_refuse(f"Invalid JSON: {e}")))
        return
    # Solver imports (e.g. NVIDIA Warp) print banners to stdout; keep stdout for the one JSON document only.
    with contextlib.redirect_stdout(sys.stderr):
        try:
            result = run_gr_solidification(data)
        except Exception as e:  # unexpected engine failure still yields exactly one JSON document
            result = _refuse(f"{type(e).__name__}: {e}", "engine")
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
