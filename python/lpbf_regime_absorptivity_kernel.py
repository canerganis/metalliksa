"""Regime-dependent absorptivity: candidate law and read-only kernel recomposition (research, SCREENING ONLY).

FROZEN AS THE PRE-P1 BASELINE (served path before 2026-10-11). Pre-registered in
docs/research/PREDECLARED_regime_absorptivity_2026-10-09.md. This module is NOT part of
``lpbf_simulation.IMPLEMENTATION_SOURCE_FILES`` and no frozen file imports it. It rebuilds the geometry part of
``lpbf_thermal_solver.calculate_meltpool_physics`` as served before the P1 planned bump
(docs/research/SPEC_p1_sourced_served_physics_2026-10-11.md) from the building blocks EagarTsaiField, GoldakField,
rosenthal_temperature_C, _liquidus_extent, _axial_peak_x and fabbro_keyhole_depth_m, with the absorptivity passed in
as an input. The pre-P1 constants that P1 removed from the served solver are copied here (PRE_P1_*: the Rosenthal
multi-reflection ramp, the 1/(1 + 0.55 St) latent-heat factor, the Rosenthal depth increment with its 30 band edge
and the fallback floor ratio), so the baseline mode (policy None) keeps reproducing the committed
RESULTS_regime_absorptivity_2026-10-09, RESULTS_depth_path_stage1 and _stage1b numbers, which were run against that
served path. It no longer equals the live solver: after P1 the served path is P_field = A_flat P, depth = max(d_iso,
Fabbro leg) for every kernel. python/test_lpbf_regime_absorptivity_eval.py pins the baseline against served outputs
recorded at the pre-P1 revision (a self-contained fixture, not a live call).

Nothing here is a validated model. Outputs are 'Screening' only.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

import lpbf_thermal_solver as ts
from eagar_tsai_solver import EagarTsaiField
from fabbro_keyhole import fabbro_keyhole_depth_m
from four_alloy_materials import thermal_props
from goldak_solver import GoldakField, seed_goldak_axes

KERNELS = ("eagar-tsai", "goldak", "rosenthal")

# Pre-P1 served constants (lpbf_thermal_solver.py at 393cdbd1, pin 0d52d7f7), copied locally so this baseline stays
# frozen while the served solver moved on (P1, 2026-10-11).
PRE_P1_ENTHALPY_TRANSITION = 15.0          # start of the ramp and of the increment (ts.ENTHALPY_TRANSITION, unchanged)
PRE_P1_KEYHOLE_INCREMENT_FULL_AT = 30.0    # former ts.KEYHOLE_INCREMENT_FULL_AT (removed from the served solver)
PRE_P1_LATENT_FACTOR_COEFF = 0.55          # former 1/(1 + 0.55 St) Rosenthal field-power factor
PRE_P1_FALLBACK_FLOOR = (0.38, 0.10)       # former d_iso floor half_w * (0.38 + 0.10 min(1, dH/hs / 15))

# Policy specs are plain tuples so they pickle into worker processes and hash into cache keys.
#   None                                  baseline: pre-P1 served behaviour (flat A; Rosenthal multi-reflection ramp)
#   ("law", A_kh, H_on, H_s, fabbro)      saturating-exponential law A(H); fabbro=True feeds A(H) to Fabbro (ET/Goldak)
#   ("gan", eta_max, rate, Am, floor_K)   Gan 2021 Eq. 6, ADAPTED (floor, app properties, 1/e2 radius), Am
Policy = Optional[Tuple]


def absorptivity_law(H: float, A_flat: float, A_kh: float, H_on: float, H_s: float) -> float:
    """A(H): A_flat for H <= H_on, else A_kh - (A_kh - A_flat) exp(-(H - H_on)/H_s); A_flat if A_flat >= A_kh."""
    if A_flat >= A_kh or H <= H_on:
        return float(A_flat)
    return float(A_kh - (A_kh - A_flat) * math.exp(-(H - H_on) / H_s))


def gan_absorptivity(A_flat: float, Am: float, P_W: float, v_m_s: float, r_m: float, rho: float, cp_s: float,
                     T_liq_C: float, T0_C: float, eta_max: float, rate: float, floor_K: float) -> float:
    """Gan et al. 2021 Eq. 6, adapted (see config arm G): A = max(A_flat, eta_max (1 - exp(-rate X))), X = Am P / (dT pi rho cp_s v r^2)."""
    dT = max(floor_K, T_liq_C - T0_C)
    X = Am * P_W / (dT * math.pi * rho * cp_s * v_m_s * r_m * r_m)
    return float(max(A_flat, eta_max * (1.0 - math.exp(-rate * X))))


def resolve_props(material: str) -> Dict[str, Any]:
    props = thermal_props(material) or ts.SECONDARY_THERMOPHYSICAL_DB.get(material)
    if props is None:
        raise ValueError(f"Unsupported LPBF material identity: {material!r}")
    return dict(props)


def flat_enthalpy(material: str, P_W: float, v_mm_s: float, d_um: float, preheat_C: float) -> float:
    """dH/hs exactly as calculate_meltpool_physics computes it (flat A, solid k and cp, r = 1/e^2 radius)."""
    props = resolve_props(material)
    v_scan = float(v_mm_s) * 1e-3
    r_beam = float(d_um) * 1e-6 / 2.0
    rho, k_s, cp_s = props["density_kg_m3"], props["thermal_conductivity_W_mK"], props["specific_heat_J_kgK"]
    alpha_solid = k_s / (rho * cp_s)
    denom = rho * cp_s * max(50.0, props["liquidus_C"] - float(preheat_C)) * math.sqrt(
        math.pi * alpha_solid * v_scan * (r_beam ** 3))
    return (float(props["absorptivity_IR"]) * float(P_W)) / max(1e-9, denom)


def meltpool_wd(material: str, P_W: float, v_mm_s: float, d_um: float, preheat_C: float, layer_um: float,
                hatch_um: float, kernel: str, policy: Policy = None) -> Dict[str, Any]:
    """Width, depth (um, rounded to 0.1 um like the frozen output) and extent status of one kernel.

    The arithmetic order follows the pre-P1 ``calculate_meltpool_physics`` so that the baseline policy is bit-identical
    to the served path before 2026-10-11. Returns {'W_um', 'D_um', 'status', 'H', 'A_cond', 'A_fabbro'}; 'A_cond' is
    the absorptivity that scaled the conduction-field power (Rosenthal: eta_eff before the latent-heat factor)."""
    if kernel not in KERNELS:
        raise ValueError(f"unsupported kernel {kernel!r}")
    props = resolve_props(material)
    P_laser = float(P_W)
    v_scan = float(v_mm_s) * 1e-3
    d_beam = float(d_um) * 1e-6
    r_beam = d_beam / 2.0
    T_preheat = float(preheat_C)
    T_liq = props["liquidus_C"]
    T_vap = props["boiling_C"]
    rho = props["density_kg_m3"]
    k_s = props["thermal_conductivity_W_mK"]
    k_l = float(props.get("thermal_conductivity_liquid_W_mK", k_s))
    cp_s = props["specific_heat_J_kgK"]
    cp_l = float(props.get("specific_heat_liquid_J_kgK", cp_s))
    k_th = 0.5 * (k_s + k_l)
    cp = 0.5 * (cp_s + cp_l)
    alpha_th = k_th / (rho * cp)
    alpha_solid = k_s / (rho * cp_s)
    eta_base_flat = float(props["absorptivity_IR"])
    eta_base = eta_base_flat

    enthalpy_denom = rho * cp_s * max(50.0, T_liq - T_preheat) * math.sqrt(math.pi * alpha_solid * v_scan * (r_beam ** 3))
    normalized_enthalpy = (eta_base_flat * P_laser) / max(1e-9, enthalpy_denom)

    # Candidate absorptivity (None = baseline behaviour).
    a_law: Optional[float] = None
    fabbro_flat = True
    if policy is not None:
        if policy[0] == "law":
            _, A_kh, H_on, H_s, fabbro = policy
            a_law = absorptivity_law(normalized_enthalpy, eta_base_flat, A_kh, H_on, H_s)
            fabbro_flat = not fabbro
        elif policy[0] == "gan":
            _, eta_max, rate, Am, floor_K = policy
            a_law = gan_absorptivity(eta_base_flat, Am, P_laser, v_scan, r_beam, rho, cp_s, T_liq, T_preheat,
                                     eta_max, rate, floor_K)
        else:
            raise ValueError(f"unsupported absorptivity policy {policy!r}")

    # Pre-P1 multi-reflection ramp of the Rosenthal path (replaced, not stacked, by a candidate).
    if normalized_enthalpy > PRE_P1_ENTHALPY_TRANSITION:
        cavity_aspect = min(4.0, (normalized_enthalpy - PRE_P1_ENTHALPY_TRANSITION) / 8.0)
        n_reflections = 1.0 + 1.8 * cavity_aspect
        eta_eff = 1.0 - (1.0 - eta_base) ** n_reflections
    else:
        eta_eff = eta_base
    if a_law is not None:
        eta_eff = a_law

    Lf = props["latent_heat_fusion_J_kg"]
    stefan = Lf / max(1.0, cp * max(50.0, T_liq - T_preheat))
    if kernel in ("eagar-tsai", "goldak"):
        a_cond = eta_base if a_law is None else a_law
        P_absorbed = a_cond * P_laser
        A_fabbro = eta_base_flat if (a_law is None or fabbro_flat) else a_law
        latent_heat_power_factor = 1.0
    else:
        a_cond = eta_eff
        P_absorbed = eta_eff * P_laser
        A_fabbro = eta_base_flat
        latent_heat_power_factor = 1.0 / (1.0 + PRE_P1_LATENT_FACTOR_COEFF * stefan)
    P_geom = P_absorbed * latent_heat_power_factor
    r_reg = max(r_beam / math.sqrt(2.0), 8e-6)

    goldak_seed = seed_goldak_axes(r_beam)
    if kernel == "eagar-tsai":
        et_field = EagarTsaiField(T_preheat, P_geom, k_th, alpha_th, r_beam).bind_speed(v_scan)

        def T_field(x_m, y_m, z_m):
            return et_field.temperature_C(x_m, y_m, z_m)
    elif kernel == "goldak":
        gk_field = GoldakField(T_preheat, P_geom, rho, cp, alpha_th, goldak_seed["af_m"], goldak_seed["ar_m"],
                               goldak_seed["b_m"], goldak_seed["c_m"]).bind_speed(v_scan)

        def T_field(x_m, y_m, z_m):
            return gk_field.temperature_C(x_m, y_m, z_m)
    else:
        def T_field(x_m, y_m, z_m):
            return ts.rosenthal_temperature_C(x_m, y_m, z_m, T_preheat, P_geom, k_th, v_scan, alpha_th, r_reg)

    fabbro = fabbro_keyhole_depth_m(P_laser, v_scan, d_beam, k_s, alpha_solid, T_vap, T_preheat, A_fabbro,
                                    normalized_enthalpy)
    denom_thermal = rho * cp * max(50.0, T_liq - T_preheat) * v_scan
    w_analytical = math.sqrt(max(1e-12, (8.0 / (math.pi * math.e)) * (P_geom / denom_thermal)))
    search_half_w = max(d_beam * 1.8, w_analytical * 1.8, 50e-6)
    search_len = max(d_beam * 3.0, w_analytical * 4.5, 80e-6)
    search_depth = max(d_beam * 2.2, w_analytical * 2.0, 40e-6, fabbro["depth_m"] * 1.35)

    t_peak_C = float(T_field(0.0, 0.0, 0.0))
    x_peak = ts._axial_peak_x(T_field, -search_len * 1.4 * 8.0, search_len)
    max(t_peak_C, float(T_field(x_peak, 0.0, 0.0)))  # same evaluation sequence as the frozen function
    ext = ts._liquidus_extent(T_field, T_liq, x_peak, search_len, search_half_w, search_depth, d_beam, r_beam,
                              w_analytical, normalized_enthalpy)
    w_melt_m = ext["w_melt_m"]
    d_iso = ext["d_iso"]
    if ext["extent_status"] == "heuristic-width-fallback":
        # Pre-P1 fallback floor (the served _liquidus_extent now floors at half_w; rebuild the old floor from the
        # isotherm depth and the substituted half width it returns).
        a, b = PRE_P1_FALLBACK_FLOOR
        d_iso = max(ext["d_iso_isotherm_m"],
                    ext["half_w_m"] * (a + b * min(1.0, normalized_enthalpy / PRE_P1_ENTHALPY_TRANSITION)))
        d_iso = max(d_iso, 4e-6)

    if kernel in ("eagar-tsai", "goldak"):
        extra = max(0.0, fabbro["depth_m"] - d_iso)
    elif normalized_enthalpy < PRE_P1_ENTHALPY_TRANSITION:
        extra = 0.0
    elif normalized_enthalpy < PRE_P1_KEYHOLE_INCREMENT_FULL_AT:
        trans = ((normalized_enthalpy - PRE_P1_ENTHALPY_TRANSITION)
                 / (PRE_P1_KEYHOLE_INCREMENT_FULL_AT - PRE_P1_ENTHALPY_TRANSITION))
        extra = d_iso * (0.15 + 0.55 * trans)
    else:
        over = (normalized_enthalpy - PRE_P1_KEYHOLE_INCREMENT_FULL_AT) / 10.0
        extra = d_iso * (0.85 + 0.55 * math.log10(1.0 + max(0.0, over)))
    d_melt_m = d_iso + extra
    return {"W_um": round(w_melt_m * 1e6, 1), "D_um": round(d_melt_m * 1e6, 1), "status": ext["extent_status"],
            "H": normalized_enthalpy, "A_cond": float(a_cond), "A_fabbro": float(A_fabbro)}
