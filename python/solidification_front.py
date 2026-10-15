#!/usr/bin/env python3
"""
Solidification front of the conduction field: the SOL-A1 quantity container (2026-10-15).

Authority: docs/research/SPEC_solidification_integration_2026-10-15.md (Revision 1 with the lead-check fixes of
759a4cb7: sections 3.4, 4.1 to 4.3, 6.2, 6.3, 7.1, 7.4) and docs/research/SPEC_solidification_2026-10-14.md (5.2 and
Amendments 1 to 3, A3.A1 to A3.A4).

SOL-A1 is the blanket-null containment bump (gate decision RA1). No served liquidus is an admitted source-bound parent
(contract 4.3 item 5, last row: AlSi10Mg and Inconel 625 legacy estimates; Ti-6Al-4V, Inconel 718 and 316L declared
assumptions without a provenance entry), so every default front quantity of every alloy is null with the reason
missing-source-constant naming the liquidus input and its provenance kind; a served depth from the Fabbro keyhole
leg adds keyhole-field-inconsistent. G, R, the cooling rate, G/R, PDAS, SDAS, the morphology and the solid-state
transformation note are not computed and the field is not sampled. The front reads nothing back into the thermal
result, so width, depth, regime, verdict, extentStatus, the process window and the defect diagnostics are untouched.
SOL-T installs admitted endpoints; SOL-C is the earliest return of local per-sample values.

Manifest rule (contract 4.1 items 5 and 6, RA4): this file never imports quantity_envelope.py and emits codes,
structured parameters and provenance kinds only, never an English sentence. The display text is the registry's
(quantity_envelope.REASON_TEMPLATES and INPUT_KIND_LABELS), so a wording change moves no pin; an input record's label
is its kind code for the same reason. The literal vocabularies below are pinned against the registry by
python/test_solidification_front.py.

Retired here (contract 6.2; SPEC A3.A3, A3.A4): the alloy-neutral Hunt G/R morphology cuts and hunt_morphology, the
chosen Hunt-Lu prefactor and hunt_lu_pdas_um, kirkwood_sdas_um, phase_transformation_note with its Ti-6Al-4V 410 K/s
switch (a liquidus cooling rate is not a subsolidus history), the substring alloy match that classed Inconel 625 as
IN718, the HUNT_DOI and AHMED_RACK_DOI claims on null front blocks, the caption coefficients 9.56e-4 and 2.6e-3, the
ignored legacy keywords of evaluate_solidification and the rounding of transported values.

Kept for SOL-C: the rear-liquidus sampler map_solidification_front (quasi-steady laser frame, +x travel, z >= 0 depth;
G = |grad T|, R = v n_x on solidifying samples n_x > 0, cooling G R per sample; Ghosh et al. 2017 Sec. 3.1; P6
derivation section 7 Eq. 13). The served path does not call it at SOL-A1.

Kept as a direct source-model function, not served at SOL-A1: the Ni-Nb PDAS literature arm pdas_band_um of Ghosh et
al. 2017 (S04) with the equation-derived coefficients (SPEC A3.A2) and the fixed-G line admission (SPEC 5.2, A3.A4).
Does not re-score Build Job printability.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Sequence

from four_alloy_materials import resolve_alloy_id

MODEL_ID = "solidification-front-v2"

# Quantity envelope v1 literals (contract 4.2; registry: quantity_envelope.py, never imported here).
ENVELOPE_SCHEMA = "metalliksa-quantity-envelope-1"
MODULE_EVIDENCE_CEILING = "screening-only"
# Registry label of the host module (3d-distortion-lab, scope Research), echoed by the container (contract 4.1 item 7).
MODULE_MATURITY = "Research"

CANONICAL_ALLOY_IDS = ("ti6al4v", "alsi10mg", "in718", "in625", "ss316l")
_IN625_COMPACT_ALIASES = ("in625", "inconel625")

# Served liquidus at SOL-A1, nothing installed (contract 4.3 item 5, last row): the provenance kind, a status code in
# the record's scope and where the value is declared. Equal to quantity_envelope.SERVED_LIQUIDUS_INPUT_KINDS (tested).
SERVED_LIQUIDUS_PROVENANCE: Dict[str, Dict[str, str]] = {
    "ti6al4v": {"kind": "declaredAssumption", "scope": "no-provenance-entry",
                "declarationLocator": "python/four_alloy_materials.py#_THERMAL/ti6al4v/liquidus_C"},
    "alsi10mg": {"kind": "legacyEstimate", "scope": "unsourced-estimate",
                 "declarationLocator": "python/four_alloy_materials.py#_THERMAL/alsi10mg/liquidus_C"},
    "in718": {"kind": "declaredAssumption", "scope": "no-provenance-entry",
              "declarationLocator": "python/four_alloy_materials.py#_THERMAL/in718/liquidus_C"},
    "in625": {"kind": "legacyEstimate", "scope": "secondary-unreconciled",
              "declarationLocator": "python/lpbf_thermal_solver.py#SECONDARY_THERMOPHYSICAL_DB/in625/liquidus_C"},
    "ss316l": {"kind": "declaredAssumption", "scope": "no-provenance-entry",
               "declarationLocator": "python/four_alloy_materials.py#_THERMAL/ss316l/liquidus_C"},
}
LIQUIDUS_INPUT = "liquidus_K"
KELVIN_OFFSET = 273.15

# Front quantities of the thermal container: name -> (quantity definition, SI unit), registry definitions of 4.2.
FRONT_QUANTITIES: Dict[str, tuple] = {
    "thermalGradient": ("liquidus-front-thermal-gradient", "K/m"),
    "normalSpeed": ("liquidus-front-normal-speed", "m/s"),
    "coolingRate": ("liquidus-front-cooling-rate", "K/s"),
    "gOverR": ("liquidus-front-g-over-r", "K*s/m^2"),
    "pdas": ("pdas-model-alternatives", "m"),
    "sdas": ("sdas", "m"),
    "morphology": ("front-morphology", "1"),
    "solidStateTransformation": ("solid-state-transformation", "1"),
}
# Reason codes emitted by this file (a subset of quantity_envelope.REASON_CODES; tested).
EMITTED_REASON_CODES = ("missing-source-constant", "keyhole-field-inconsistent", "parent-unavailable",
                        "missing-source-bound-model", "missing-thermal-history", "unknown-alloy-alias",
                        "nonphysical-input", "outside-source-model-domain")

# --- Ni-Nb PDAS literature arm (S04: Ghosh, Ma, Ofori-Opoku and Guyer 2017, Modelling Simul. Mater. Sci. Eng. 25,
# 065002) -------------------------------------------------------------------------------------------------------------
#
# lambda1 = A G^-1/2 R^-1/4 (Eq. 7 Hunt, Eq. 8 Kurz and Fisher; PDF12/printed11, Fig. 6), A in m^0.75 s^-0.25 K^0.5.
# The sole runtime constants are the equation-derived binary64 values of SPEC A3.A2 with the Table 2 inputs
# k_e 0.48, Gamma 3.65e-7 K m, DeltaT0 57 K, D_l 3e-9 m^2/s:
#   Hunt        2.83 (k_e Gamma DeltaT0 D_l)^0.25 = 1.1773863284676703e-3 (display about 1.18e-3; the caption's 9.56e-4
#               conflicts with Eq. 7 and the Fig. 6 line and is rejected)
#   Kurz-Fisher 4.3 (Gamma DeltaT0 D_l / k_e)^0.25 = 2.5821435943712695e-3 (the caption's 2.6e-3 is display rounding)
# Default admission (SPEC 5.2, A3.A4): the fixed line G = 1e7 K/m of the source simulations (Sec. 3.1, PDF9), with
# x = G^-1/2 R^-1/4 in [4e-4, 1.2e-3], cooling G R in [5e4, 3e6] K/s, and Vcs < R < Vab with Vcs = G D_l / DeltaT0 and
# Vab about 0.98 m/s (Sec. 3.2.1). Relative 1e-12 only compares an encoded G with the line, it is no extrapolation
# band. Pairs outside get outside-source-model-domain before the spacing arithmetic. The arm is an explicitly
# transferred dilute binary Ni-Nb screen for IN625 and IN718, never Ti-6Al-4V, AlSi10Mg or 316L; the two members are
# model alternatives, never a confidence interval. It admits no served sample at SOL-A1 (A3.A4).
PDAS_A_HUNT_SI = 1.1773863284676703e-3
PDAS_A_KURZ_FISHER_SI = 2.5821435943712695e-3
PDAS_SOURCE_K_E = 0.48
PDAS_SOURCE_GAMMA_K_M = 3.65e-7
PDAS_SOURCE_DELTA_T0_K = 57.0
PDAS_SOURCE_D_L_M2_S = 3.0e-9
PDAS_SOURCE_LINE_G_K_M = 1.0e7
PDAS_LINE_RELATIVE_TOLERANCE = 1.0e-12
PDAS_VAB_M_S = 0.98
PDAS_X_RANGE = (4.0e-4, 1.2e-3)
PDAS_COOLING_RANGE_K_S = (5.0e4, 3.0e6)
PDAS_ALLOY_IDS = ("in625", "in718")
GHOSH2017_SOURCE = {
    "id": "ghosh2017",
    "locator": ("Ghosh, Ma, Ofori-Opoku and Guyer 2017, Modelling Simul. Mater. Sci. Eng. 25, 065002, "
                "doi 10.1088/1361-651X/aa7369: PDF12/printed11 Eq. 7, Eq. 8 and Fig. 6; PDF8 Table 2; PDF9 Sec. 3.1 "
                "(G = 1e7 K/m); Sec. 3.2.1 (Vcs, Vab)"),
    "readLevel": "primary-read",
}


def canonical_alloy_id(name: Any) -> Optional[str]:
    """One of the five canonical alloy IDs for an exact alias, else None (never a substring match).

    The four authority alloys resolve through four_alloy_materials.resolve_alloy_id; Inconel 625 through its own
    exact compact aliases (in625, inconel625), so it can never be classed as IN718."""
    if not isinstance(name, str):
        return None
    if name in CANONICAL_ALLOY_IDS:
        return name
    aid = resolve_alloy_id(name)
    if aid in CANONICAL_ALLOY_IDS:
        return aid
    compact = "".join(name.strip().lower().split()).replace("-", "").replace("_", "")
    if compact in _IN625_COMPACT_ALIASES:
        return "in625"
    return None


def _finite_positive(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
            and value > 0.0)


def pdas_on_source_line(G_K_m: Any) -> bool:
    """True when G sits on the source line G = 1e7 K/m within relative 1e-12 (an encoding comparison)."""
    if not _finite_positive(G_K_m):
        return False
    return abs(float(G_K_m) - PDAS_SOURCE_LINE_G_K_M) <= PDAS_LINE_RELATIVE_TOLERANCE * PDAS_SOURCE_LINE_G_K_M


def pdas_vcs_m_s(G_K_m: float) -> float:
    """Constitutional-supercooling limit Vcs = G D_l / DeltaT0 of the source alloy (S04 Sec. 3.2.1)."""
    return float(G_K_m) * PDAS_SOURCE_D_L_M2_S / PDAS_SOURCE_DELTA_T0_K


def pdas_above_vcs(G_K_m: Any, R_m_s: Any) -> bool:
    """True when R lies strictly above Vcs (not on the planar side)."""
    if not (_finite_positive(G_K_m) and _finite_positive(R_m_s)):
        return False
    return float(R_m_s) > pdas_vcs_m_s(G_K_m)


def pdas_below_vab(R_m_s: Any) -> bool:
    """True when R lies strictly below the absolute-stability speed Vab = 0.98 m/s (S04 Sec. 3.2.1)."""
    if not _finite_positive(R_m_s):
        return False
    return float(R_m_s) < PDAS_VAB_M_S


def _reason(code: str, parent: Optional[Dict[str, str]] = None, **params: Any) -> Dict[str, Any]:
    return {"code": code, "params": dict(params), "parent": dict(parent) if parent is not None else None}


def pdas_band_um(G_K_m: Any, R_m_s: Any, alloy_id: Any, cooling_K_s: Any = None) -> Dict[str, Any]:
    """Ni-Nb PDAS model alternatives (um) for one co-located (G, R) pair, or null with reason codes.

    ``alloy_id`` is a canonical alloy ID; anything else is refused with unknown-alloy-alias. ``cooling_K_s`` defaults
    to G R. Return shape (kept for the kinetics probe, contract 6.3): {"pdasBand_um": {"hunt", "kurzFisher"} | None,
    "pdasOutOfRange": bool | None (True when a Ni-Nb pair falls outside the source support, None when no domain was
    evaluated), "reasons": [{code, params, parent}], "admission": {...} | None, "x", "coolingRate_K_s", "vcs_m_s",
    "alloyId", "sources", "modelId"}. Only codes and structured parameters; no sentence (RA4)."""
    out: Dict[str, Any] = {"pdasBand_um": None, "pdasOutOfRange": None, "reasons": [], "admission": None, "x": None,
                           "coolingRate_K_s": None, "vcs_m_s": None, "alloyId": None, "sources": [],
                           "modelId": MODEL_ID}
    if not (isinstance(alloy_id, str) and alloy_id in CANONICAL_ALLOY_IDS):
        out["reasons"] = [_reason("unknown-alloy-alias")]
        return out
    out["alloyId"] = alloy_id
    if alloy_id not in PDAS_ALLOY_IDS:
        out["reasons"] = [_reason("missing-source-bound-model")]
        return out
    cooling = None
    if _finite_positive(G_K_m) and _finite_positive(R_m_s):
        cooling = float(G_K_m) * float(R_m_s) if cooling_K_s is None else cooling_K_s
    if not (_finite_positive(G_K_m) and _finite_positive(R_m_s) and _finite_positive(cooling)):
        out["reasons"] = [_reason("nonphysical-input")]
        return out
    G, R, cooling = float(G_K_m), float(R_m_s), float(cooling)
    x = (G ** -0.5) * (R ** -0.25)
    x_lo, x_hi = PDAS_X_RANGE
    c_lo, c_hi = PDAS_COOLING_RANGE_K_S
    admission = {
        "onSourceLine": pdas_on_source_line(G),
        "xInRange": x_lo <= x <= x_hi,
        "coolingInRange": c_lo <= cooling <= c_hi,
        "aboveVcs": pdas_above_vcs(G, R),
        "belowVab": pdas_below_vab(R),
    }
    out.update(x=x, coolingRate_K_s=cooling, vcs_m_s=pdas_vcs_m_s(G), admission=admission)
    if not all(admission.values()):
        out["pdasOutOfRange"] = True
        out["reasons"] = [_reason("outside-source-model-domain", **admission)]
        return out
    out["pdasOutOfRange"] = False
    out["pdasBand_um"] = {"hunt": PDAS_A_HUNT_SI * x * 1.0e6, "kurzFisher": PDAS_A_KURZ_FISHER_SI * x * 1.0e6}
    out["sources"] = [dict(GHOSH2017_SOURCE)]
    return out


# --- Rear-liquidus sampler (kept for SOL-C; not called by the served path at SOL-A1) -----------------------------------

def _t_scalar(T_fn: Callable, x: float, y: float, z: float) -> float:
    val = T_fn(x, y, z)
    try:
        return float(val)
    except (TypeError, ValueError):
        return float(val.reshape(-1)[0])


def _grad_T(T_fn: Callable, x: float, y: float, z: float, h: float) -> tuple[float, float, float]:
    h = max(8e-8, float(h))
    dTdx = (_t_scalar(T_fn, x + h, y, z) - _t_scalar(T_fn, x - h, y, z)) / (2.0 * h)
    dTdy = (_t_scalar(T_fn, x, y + h, z) - _t_scalar(T_fn, x, y - h, z)) / (2.0 * h)
    if z - h >= 0.0:
        dTdz = (_t_scalar(T_fn, x, y, z + h) - _t_scalar(T_fn, x, y, z - h)) / (2.0 * h)
    else:
        # One-sided difference at the free surface over its own step (P6: the former form divided the one-sided
        # difference by 2h and halved the surface derivative).
        dTdz = (_t_scalar(T_fn, x, y, z + h) - _t_scalar(T_fn, x, y, z)) / h
    return dTdx, dTdy, dTdz


def _binary_z_liquidus(T_fn: Callable, x: float, T_liq: float, z_hi: float) -> float:
    if _t_scalar(T_fn, x, 0.0, 0.0) < T_liq:
        return -1.0
    lo, hi = 0.0, max(4e-6, float(z_hi))
    # Bisection needs a sign-changing bracket. If the top of the search
    # domain is still superheated, the liquidus crossing lies beyond the
    # requested domain; do not report its boundary as a physical front.
    if _t_scalar(T_fn, x, 0.0, hi) > T_liq:
        return -1.0
    for _ in range(16):
        mid = 0.5 * (lo + hi)
        if _t_scalar(T_fn, x, 0.0, mid) >= T_liq:
            lo = mid
        else:
            hi = mid
    return lo


def map_solidification_front(
    T_fn: Callable,
    T_liq: float,
    v_scan: float,
    x_rear: float,
    search_depth: float,
    h_m: float,
    cos_theta: Optional[float] = None,
    n_samples: int = 9,
) -> Optional[Dict[str, Any]]:
    """Sample the rear liquidus in the x-z plane (y=0) and return G, R, Tdot stats (kept for SOL-C).

    Only solidifying samples (n_x > 0, behind the deepest liquidus point) are kept, and every
    median is taken over that same set; fewer than 3 such samples -> None.
    cos_theta is accepted for signature compatibility and ignored (P6: no incline multiplier). SOL-C replaces the
    separate medians with per-sample tuples and a defined aggregation (contract 7.1)."""
    del cos_theta
    x_rear = max(4e-6, float(x_rear))
    z_hi = max(8e-6, float(search_depth))
    n_samples = max(5, min(16, int(n_samples)))
    # Solidifying part of the rear liquidus: from the deepest liquidus point (n_x = 0) back to the tail.
    scan = [-x_rear * (0.98 - 0.96 * j / 32.0) for j in range(33)]
    depths = [(_binary_z_liquidus(T_fn, xb, T_liq, z_hi), xb) for xb in scan]
    z_b, x_b = max(depths)
    if z_b < 0.0:
        x_b = -0.22 * x_rear
    span = -x_rear - x_b
    xs = [x_b + span * (0.08 + 0.84 * i / max(1, n_samples - 1)) for i in range(n_samples)]
    samples: List[Dict[str, float]] = []
    for x in xs:
        z = _binary_z_liquidus(T_fn, x, T_liq, z_hi)
        if z < 0.0:
            continue
        gx, gy, gz = _grad_T(T_fn, x, 0.0, z, h_m)
        g_mag = math.sqrt(gx * gx + gy * gy + gz * gz)
        if g_mag < 1.0:
            continue
        nx = gx / g_mag
        if nx <= 0.0:
            # Ahead of the deepest liquidus point the isotherm advances into solid (melting side):
            # R_n = v n_x is a solidification rate only where n_x > 0 (Kou §6.1 geometry).
            continue
        R_loc = float(v_scan) * nx
        samples.append({
            "x_um": round(x * 1e6, 1),
            "z_um": round(z * 1e6, 1),
            "G_K_m": g_mag,
            "R_m_s": R_loc,
            "coolingRate_K_s": g_mag * R_loc,
            "g_over_r": g_mag / R_loc,
            "n_x": nx,
        })
    if len(samples) < 3:
        return None

    def _med(key: str) -> float:
        vals = sorted(s[key] for s in samples)
        return vals[len(vals) // 2]

    tail = min(samples, key=lambda s: s["x_um"])
    bottom = max(samples, key=lambda s: s["z_um"])
    return {
        "nPoints": len(samples),
        "G_median_K_m": _med("G_K_m"),
        "G_tail_K_m": tail["G_K_m"],
        "R_median_m_s": _med("R_m_s"),
        "R_tail_m_s": tail["R_m_s"],
        "coolingRate_median_K_s": _med("coolingRate_K_s"),
        "tail": tail,
        "bottom": bottom,
        "samples": samples,
    }


# --- The SOL-A1 container ----------------------------------------------------------------------------------------------

def _null_quantity(name: str, reasons: Sequence[Dict[str, Any]], depends_on: Sequence[str] = ()) -> Dict[str, Any]:
    definition, unit = FRONT_QUANTITIES[name]
    return {
        "status": "unavailable", "value": None, "unit": unit, "quantityDefinition": definition,
        "leafRole": "derived", "sourceEvidenceKind": None, "dependsOn": list(depends_on), "weakestInputs": [],
        "labelSources": [], "reasons": [dict(item) for item in reasons],
        "numericalStatus": {"state": "not-assessed", "settings": {}, "residuals": {}},
        "physicalValidation": {"status": "unvalidated", "experimentalValidation": False, "productionReady": False},
        "sources": [], "assumptions": [], "validity": None, "uncertainty": None, "fractionBasis": None,
        "identity": {"input": None, "model": MODEL_ID, "parent": None},
    }


def _input_record(kind: str, source_id: str, *, declaration_locator: Optional[str], scope: str,
                  source_evidence_kind: str, default_value: Optional[float],
                  default_kind: Optional[str]) -> Dict[str, Any]:
    """P8-shaped input provenance record (contract 4.2; the 17 keys of quantity_envelope.INPUT_RECORD_KEYS)."""
    return {
        "kind": kind, "label": kind, "sourceId": source_id, "sourceLocator": None,
        "declarationLocator": declaration_locator, "source": None, "scope": scope, "status": "inRange",
        "sourceEvidenceKind": source_evidence_kind, "defaultValue": default_value, "defaultKind": default_kind,
        "followsInput": None, "followState": None, "dependsOn": [], "phase": None, "referenceTemperature_K": None,
        "sourceRange_K": None,
    }


def _liquidus_input(alloy_id: str, T_liq_C: float, authority_liquidus_C: Optional[float]) -> Dict[str, Any]:
    """The liquidus input record. A value typed over the served one (float.hex differs) is a userInput naming the
    served default it replaced; an equal value keeps the served kind (decision 2)."""
    served = SERVED_LIQUIDUS_PROVENANCE[alloy_id]
    default_C = float(T_liq_C) if authority_liquidus_C is None else float(authority_liquidus_C)
    default_K = default_C + KELVIN_OFFSET
    if float(T_liq_C).hex() != default_C.hex():
        return _input_record(
            "userInput", f"request:prop_overrides:liquidus_C:{alloy_id}", declaration_locator=None,
            scope="typed-over-served-liquidus", source_evidence_kind="User input", default_value=default_K,
            default_kind=None if served["kind"] == "legacyEstimate" else served["kind"])
    return _input_record(
        served["kind"], f"served-liquidus:{alloy_id}", declaration_locator=served["declarationLocator"],
        scope=served["scope"], source_evidence_kind="Unresolved", default_value=default_K, default_kind=None)


def _front_quantities(blocking: Sequence[Dict[str, Any]], depends_on: Sequence[str],
                      model_reasons: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Every front quantity null: G and R carry the blocking reasons; dependents add parent-unavailable for each null
    parent they name (contract 4.3 item 8 and the parent-propagation rule of quantity_envelope.container_problems)."""
    def parents(*names: str) -> List[Dict[str, Any]]:
        return [_reason("parent-unavailable", parent={"input": name, "kind": "derived"}) for name in names]

    quantities: Dict[str, Any] = {
        "thermalGradient": _null_quantity("thermalGradient", blocking, depends_on),
        "normalSpeed": _null_quantity("normalSpeed", blocking, depends_on),
    }
    for name in ("coolingRate", "gOverR", "pdas"):
        quantities[name] = _null_quantity(
            name, list(blocking) + parents("thermalGradient", "normalSpeed") + model_reasons.get(name, []),
            ("thermalGradient", "normalSpeed"))
    quantities["sdas"] = _null_quantity("sdas", list(blocking) + parents("coolingRate") + model_reasons["sdas"],
                                        ("coolingRate",))
    quantities["morphology"] = _null_quantity("morphology", list(blocking) + model_reasons["morphology"], depends_on)
    quantities["solidStateTransformation"] = _null_quantity("solidStateTransformation",
                                                            list(blocking) + model_reasons["solidStateTransformation"], depends_on)
    return quantities


def _container(alloy_id: Optional[str], quantities: Dict[str, Any],
               input_provenance: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "quantityEnvelopeSchema": ENVELOPE_SCHEMA,
        "moduleEvidenceCeiling": MODULE_EVIDENCE_CEILING,
        "moduleMaturity": MODULE_MATURITY,
        "modelId": MODEL_ID,
        "alloyId": alloy_id,
        "quantities": quantities,
    }
    if input_provenance is not None:
        out["inputProvenance"] = input_provenance
    return out


def evaluate_solidification(
    T_fn: Callable,
    *,
    T_liq: float,
    v_scan: float,
    x_rear: float,
    search_depth: float,
    r_beam: float,
    material_name: str,
    depth_from_keyhole_leg: bool = False,
    authority_liquidus_C: Optional[float] = None,
) -> Dict[str, Any]:
    """The front container of one thermal result (quantity envelope v1, contract 4.2 and 4.3 item 8).

    T_fn, v_scan, x_rear, search_depth and r_beam name the conduction field and its rear-liquidus search box, the
    parent of the front; at SOL-A1 no admitted liquidus exists, so the field is not sampled and every quantity is
    null. T_liq is the liquidus the field used (C); authority_liquidus_C is the served authority value when the
    caller can tell (a different T_liq was typed over it). material_name is resolved exactly (canonical_alloy_id);
    an unknown alias is refused with unknown-alloy-alias on every quantity."""
    del T_fn, v_scan, x_rear, search_depth, r_beam  # the field parent is sampled from SOL-C on, never at SOL-A1
    alloy_id = canonical_alloy_id(material_name)
    if alloy_id is None:
        refused = [_reason("unknown-alloy-alias")]
        model_reasons = {"sdas": [], "morphology": refused, "solidStateTransformation": refused}
        return _container(None, _front_quantities(refused, ("alloyIdentity",), model_reasons),
                          {"alloyIdentity": _input_record("declaredAssumption", "request:unknown-alloy",
                           declaration_locator="python/solidification_front.py#canonical_alloy_id", scope="unresolved-alloy-identity",
                           source_evidence_kind="Unresolved", default_value=None, default_kind=None)})

    liquidus = _liquidus_input(alloy_id, T_liq, authority_liquidus_C)
    blocking = [_reason("missing-source-constant", parent={"input": LIQUIDUS_INPUT, "kind": liquidus["kind"]})]
    if depth_from_keyhole_leg:
        blocking.append(_reason("keyhole-field-inconsistent"))
    no_model = [_reason("missing-source-bound-model")]
    model_reasons = {
        # PDAS: the Ni-Nb arm is a transferred screen for IN625 and IN718 only (SPEC 5.2).
        "pdas": [] if alloy_id in PDAS_ALLOY_IDS else no_model,
        # SDAS: Kirkwood gives the exponent form only; no sourced prefactor for any alloy (P7a).
        "sdas": no_model,
        # No source-bound front-stability or morphology classifier is served (SPEC A3.A4).
        "morphology": no_model,
        # A liquidus-front cooling rate is not a subsolidus history; no source-bound transformation model (A2.4).
        "solidStateTransformation": [_reason("missing-thermal-history"), _reason("missing-source-bound-model")],
    }
    quantities = _front_quantities(blocking, (LIQUIDUS_INPUT,), model_reasons)
    return _container(alloy_id, quantities, {LIQUIDUS_INPUT: liquidus})
