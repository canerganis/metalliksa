#!/usr/bin/env python3
"""
Solidification-front G, R, G·R from a conduction temperature field.

Quasi-steady laser frame (+x travel, z ≥ 0 depth). On the rear liquidus isotherm of the
conduction field (the "conduction-field interface"), G = |∇T| and local growth R = v n_x
with n = ∇T/|∇T| into the melt (Kou / Hunt geometry; Ghosh et al. 2017 introduction;
P6 derivation section 7 Eq. 13), cooling = G R per sample. Not Gäumann–Trivedi–Kurz CET (no N0).

P6 containment (2026-10-11, docs/research/SPEC_p6_containment_2026-10-11.md item 6): the
tail-length fallback (G = ΔT/x_rear from a clipped surface temperature), the build-surface
incline multiplier max(0.05, cos θ) and the floors G >= 100 K/m, R >= 1e-4 m/s, Ṫ >= 1 K/s,
G/R >= 1 are removed. Fewer than 3 solidifying samples, or a served depth that comes from the
Fabbro keyhole leg (the conduction field does not describe that interface), give null with a
reason; PDAS, SDAS and morphology propagate null. An inclined surface needs the velocity
vector and the normal in one frame, not a second multiplier.

PDAS is Hunt–Lu λ1 ∝ G^{-1/2} R^{-1/4} with an LPBF-scale SI prefactor
(µm cells), not unused welding pdas_A1. SDAS is Kirkwood λ2 ∝ Ṫ^{-1/3}.

Does not re-score Build Job printability.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional

MODEL_ID = "solidification-front-v1"
GRADIENT_SOURCE_CONDUCTION_INTERFACE = "conduction-field-interface"
INTERFACE_LABEL = ("rear liquidus isotherm of the loss-free conduction field in the y = 0 plane "
                   "(conduction-field interface); G = |grad T|, R = v n_x, cooling = G R per sample, "
                   "medians over the solidifying samples (n_x > 0)")
UNAVAILABLE_KEYHOLE_LEG = ("the served depth comes from the Fabbro keyhole leg (e_kh > d_iso): the conduction field "
                           "does not describe the keyhole interface, so G, R, cooling rate, PDAS, SDAS and morphology "
                           "are not served (P6 containment)")
UNAVAILABLE_FEW_SAMPLES = ("fewer than 3 solidifying rear-liquidus samples (n_x > 0) in the conduction field: no "
                           "interface statistic is served and the former tail-length fallback G = dT/x_rear was removed "
                           "as uncited (P6 containment)")
HUNT_DOI = "10.1016/0025-5416(84)90201-5"
AHMED_RACK_DOI = "10.1016/S0921-5093(97)00802-2"

# Hunt 1984 morphology vs G/R (K s / m²). Screening bands, not alloy K_col.
G_OVER_R_PLANAR = 1.0e10
G_OVER_R_CELLULAR = 5.0e8
G_OVER_R_COLUMNAR = 1.0e7

# Hunt–Lu SI: λ1 = A G^{-1/2} R^{-1/4}. G=1e6 K/m, R=0.5 m/s → ~1 µm.
HUNT_LU_A_SI = 1.19e-3

TI64_MARTENSITE_K_S = 410.0


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


def hunt_morphology(g_over_r: float) -> str:
    if g_over_r >= G_OVER_R_PLANAR:
        return "Planar (Hunt G/R screening)"
    if g_over_r >= G_OVER_R_CELLULAR:
        return "Cellular (Hunt G/R screening)"
    if g_over_r >= G_OVER_R_COLUMNAR:
        return "Columnar dendritic (Hunt G/R screening)"
    return "Mixed / equiaxed tendency (Hunt G/R screening)"


def hunt_lu_pdas_um(G_K_m: float, R_m_s: float) -> float:
    G = max(1.0e4, float(G_K_m))
    R = max(1.0e-5, float(R_m_s))
    return HUNT_LU_A_SI * (G ** -0.5) * (R ** -0.25) * 1.0e6


def kirkwood_sdas_um(cooling_K_s: float, B: float) -> float:
    tdot = max(10.0, float(cooling_K_s))
    return abs(float(B)) * (tdot ** -0.33)


def phase_transformation_note(material_name: str, cooling_rate_K_s: float) -> Dict[str, Any]:
    name = (material_name or "").lower()
    Tdot = float(cooling_rate_K_s)
    if "ti-6al-4v" in name or "ti6al4v" in name or name.startswith("ti64"):
        martensite = Tdot >= TI64_MARTENSITE_K_S
        return {
            "alloyClass": "Ti-6Al-4V",
            "expected": "beta_to_alpha_prime_martensite" if martensite else "diffusion_alpha_possible",
            "criterion": (
                f"Ahmed & Rack 1998: β → α' when cooling > {TI64_MARTENSITE_K_S:.0f} K/s "
                f"(here {Tdot:.0f} K/s)"
            ),
            "source": "Ahmed & Rack, Mater. Sci. Eng. A 243 (1998) 206–211",
            "doi": AHMED_RACK_DOI,
        }
    if "316" in name:
        return {
            "alloyClass": "316L",
            "expected": "austenite_cellular_dendritic",
            "criterion": "LPBF cooling typically yields sub-micron cells; spacing from PDAS/SDAS only",
            "source": "screening — no invented cell-size table",
            "doi": HUNT_DOI,
        }
    if "alsi10mg" in name or "al-si" in name:
        return {
            "alloyClass": "AlSi10Mg",
            "expected": "alpha_Al_plus_eutectic_Si",
            "criterion": "rapid solidification eutectic Si network (not quantified here)",
            "source": "screening — no invented Si spacing table",
            "doi": HUNT_DOI,
        }
    if "718" in name or "inconel" in name:
        return {
            "alloyClass": "IN718",
            "expected": "gamma_cellular_possible_laves",
            "criterion": "interdendritic Laves possible; not quantified without Scheil/CALPHAD",
            "source": "screening — no invented Laves fraction",
            "doi": HUNT_DOI,
        }
    return {
        "alloyClass": "unspecified",
        "expected": "not_classified",
        "criterion": "no alloy-specific solid-state rule",
        "source": None,
        "doi": None,
    }


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
    """Sample the rear liquidus in the x–z plane (y=0) and return G, R, Tdot stats.

    Only solidifying samples (n_x > 0, behind the deepest liquidus point) are kept, and every
    median is taken over that same set; fewer than 3 such samples -> None (served as unavailable).
    cos_theta is accepted for signature compatibility and ignored (P6: no incline multiplier)."""
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


_DISCLAIMER = (
    "G,R from the rear liquidus of the loss-free conduction field (conduction-field interface). Hunt G/R bands "
    "are not calibrated N0 CET. Does not re-score Build Job. Null with unavailableReason where the interface is "
    "not described by that field (P6 containment)."
)


def _unavailable(reason: str) -> Dict[str, Any]:
    return {
        "modelId": MODEL_ID,
        "gradientSource": None,
        "usedFieldMap": False,
        "interface": INTERFACE_LABEL,
        "unavailableReason": reason,
        "thermalGradient_G_K_m": None,
        "solidificationRate_R_m_s": None,
        "coolingRate_K_s": None,
        "g_over_r_ratio": None,
        "microstructureMorphology": None,
        "primaryDendriteArmSpacing_PDAS_um": None,
        "secondaryDendriteArmSpacing_SDAS_um": None,
        "phaseTransformation": None,
        "doi": HUNT_DOI,
        "disclaimer": _DISCLAIMER,
    }


def evaluate_solidification(
    T_fn: Callable,
    *,
    T_liq: float,
    v_scan: float,
    x_rear: float,
    search_depth: float,
    r_beam: float,
    sdas_B1: float,
    material_name: str,
    depth_from_keyhole_leg: bool = False,
    T_sol: Optional[float] = None,
    t_surface: Optional[float] = None,
    x_front: Optional[float] = None,
    cos_theta: Optional[float] = None,
    pdas_A1: Optional[float] = None,
) -> Dict[str, Any]:
    """Interface G, R, cooling rate and the Hunt-Lu / Kirkwood spacings, or null with a reason.

    T_sol, t_surface, x_front, cos_theta and pdas_A1 are accepted for signature compatibility and ignored
    (P6: no tail-length fallback from a surface temperature, no incline multiplier, Hunt-Lu SI replaces
    the welding pdas_A1)."""
    del T_sol, t_surface, x_front, cos_theta, pdas_A1
    if depth_from_keyhole_leg:
        return _unavailable(UNAVAILABLE_KEYHOLE_LEG)
    mapped = map_solidification_front(
        T_fn,
        T_liq,
        v_scan,
        x_rear,
        search_depth,
        h_m=max(1.2e-7, 0.025 * max(8e-6, r_beam)),
    )
    if mapped is None:
        return _unavailable(UNAVAILABLE_FEW_SAMPLES)
    G = mapped["G_median_K_m"]
    R = mapped["R_median_m_s"]
    Tdot = mapped["coolingRate_median_K_s"]
    if not (G > 0.0 and R > 0.0 and Tdot > 0.0):
        return _unavailable(UNAVAILABLE_FEW_SAMPLES)

    g_over_r = G / R
    out: Dict[str, Any] = {
        "modelId": MODEL_ID,
        "gradientSource": GRADIENT_SOURCE_CONDUCTION_INTERFACE,
        "usedFieldMap": True,
        "interface": INTERFACE_LABEL,
        "unavailableReason": None,
        "thermalGradient_G_K_m": G,
        "solidificationRate_R_m_s": R,
        "coolingRate_K_s": Tdot,
        "g_over_r_ratio": g_over_r,
        "microstructureMorphology": hunt_morphology(g_over_r),
        "primaryDendriteArmSpacing_PDAS_um": hunt_lu_pdas_um(G, R),
        "secondaryDendriteArmSpacing_SDAS_um": kirkwood_sdas_um(Tdot, sdas_B1),
        "phaseTransformation": phase_transformation_note(material_name, Tdot),
        "doi": HUNT_DOI,
        "disclaimer": _DISCLAIMER,
    }
    if mapped is not None:
        out["G_tail_K_m"] = mapped["G_tail_K_m"]
        out["R_tail_m_s"] = mapped["R_tail_m_s"]
        out["frontPointCount"] = mapped["nPoints"]
        out["tail"] = {
            "x_um": mapped["tail"]["x_um"],
            "z_um": mapped["tail"]["z_um"],
            "G_K_m": round(mapped["tail"]["G_K_m"], 0),
            "R_m_s": round(mapped["tail"]["R_m_s"], 4),
        }
        out["bottom"] = {
            "x_um": mapped["bottom"]["x_um"],
            "z_um": mapped["bottom"]["z_um"],
            "G_K_m": round(mapped["bottom"]["G_K_m"], 0),
            "R_m_s": round(mapped["bottom"]["R_m_s"], 4),
        }
    return out
