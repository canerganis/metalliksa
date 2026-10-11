#!/usr/bin/env python3
"""Preview of the P1 sourced depth path on process inputs only (no measured depth anywhere).

Served numbers come from calculate_meltpool_physics. The P1 numbers re-run the served Rosenthal field
(rosenthal_temperature_C, _axial_peak_x, _liquidus_extent, same search seeds) with the P1 forms:
P_field = A_flat P (no multi-reflection ramp, no latent factor), depth = max(d_iso, Fabbro leg ramped),
fallback floor d_iso = half_w. Eagar-Tsai and Goldak are unchanged outside the fallback, so only Rosenthal is
re-run here. Companion of docs/research/SPEC_p1_sourced_served_physics_2026-10-11.md section 2.4.

Usage (from python/): python -B tools/p1_sourced_path_preview.py
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lpbf_thermal_solver as ts  # noqa: E402
from fabbro_keyhole import fabbro_keyhole_depth_m  # noqa: E402

CASES = [
    ("Inconel 718", 200, 800, 80, 20.0),
    ("Inconel 625", 200, 800, 80, 20.0),
    ("Inconel 625", 195, 800, 100, 20.0),
    ("Inconel 625", 195, 800, 170, 20.0),
    ("Inconel 625", 150, 400, 100, 20.0),
    ("Inconel 625", 150, 400, 170, 20.0),
    ("316L Stainless Steel", 150, 700, 80, 20.0),
    ("316L Stainless Steel", 200, 900, 80, 20.0),
    ("Ti-6Al-4V", 280, 1200, 70, 20.0),
    ("Inconel 625", 100, 300, 80, 20.0),
    ("Inconel 625", 75, 50, 80, 20.0),
    ("AlSi10Mg", 350, 1200, 80, 20.0),
    ("Pure Copper (Cu-OF)", 300, 800, 80, 20.0),
]


def p1_rosenthal(material: str, P: float, v_mm_s: float, d_um: float, T0: float) -> dict:
    p = ts.THERMOPHYSICAL_DB[material]
    T_liq, T_vap, rho = p["liquidus_C"], p["boiling_C"], p["density_kg_m3"]
    k_s, k_l = p["thermal_conductivity_W_mK"], float(p.get("thermal_conductivity_liquid_W_mK", p["thermal_conductivity_W_mK"]))
    cp_s, cp_l = p["specific_heat_J_kgK"], float(p.get("specific_heat_liquid_J_kgK", p["specific_heat_J_kgK"]))
    k_th, cp = 0.5 * (k_s + k_l), 0.5 * (cp_s + cp_l)
    alpha_th, alpha_s = k_th / (rho * cp), k_s / (rho * cp_s)
    A = float(p["absorptivity_IR"])
    v, d = v_mm_s * 1e-3, d_um * 1e-6
    r = d / 2.0
    enth = A * P / max(1e-9, rho * cp_s * max(50.0, T_liq - T0) * math.sqrt(math.pi * alpha_s * v * r ** 3))
    P_geom = A * P
    r_reg = max(r / math.sqrt(2.0), 8e-6)

    def T_field(x, y, z):
        return ts.rosenthal_temperature_C(x, y, z, T0, P_geom, k_th, v, alpha_th, r_reg)

    fab = fabbro_keyhole_depth_m(P, v, d, k_s, alpha_s, T_vap, T0, A, enth)
    denom = rho * cp * max(50.0, T_liq - T0) * v
    w_an = math.sqrt(max(1e-12, (8.0 / (math.pi * math.e)) * (P_geom / denom)))
    s_hw = max(d * 1.8, w_an * 1.8, 50e-6)
    s_len = max(d * 3.0, w_an * 4.5, 80e-6)
    s_dep = max(d * 2.2, w_an * 2.0, 40e-6, fab["depth_m"] * 1.35)
    x_peak = ts._axial_peak_x(T_field, -s_len * 1.4 * 8.0, s_len)
    ext = ts._liquidus_extent(T_field, T_liq, x_peak, s_len, s_hw, s_dep, d, r, w_an, enth)
    d_iso = ext["d_iso"]
    if ext["extent_status"] == "heuristic-width-fallback":
        d_iso = ext["w_melt_m"] / 2.0  # P1 floor: half width (Rosenthal y/z symmetry)
    e = fab["depth_m"]
    return {"idx": enth, "Pe": fab["peclet"], "A": A, "w_um": ext["w_melt_m"] * 1e6, "d_iso_um": d_iso * 1e6,
            "e_um": e * 1e6, "depth_um": max(d_iso, e) * 1e6, "status": ext["extent_status"],
            "peak_C": float(T_field(0.0, 0.0, 0.0))}


def main() -> None:
    print("material P v d | idx Pe | eta_eff_srv A | served: w d d_iso cavity peak | P1: w d_iso e depth peak | status")
    for mat, P, v, d, T0 in CASES:
        srv = ts.calculate_meltpool_physics(mat, P, v, d, T0, heat_source="rosenthal")
        pp, geo = srv["processParameters"], srv["meltPoolGeometry"]
        new = p1_rosenthal(mat, P, v, d, T0)
        print(f"{mat[:12]:12s} {P:4d} {v:5d} {d:4d} | {new['idx']:5.1f} {new['Pe']:5.1f} | {pp['effectiveAbsorptivity']:.3f} {new['A']:.2f} | "
              f"{geo['width_um']:6.1f} {geo['depth_um']:6.1f} {geo['depth_um'] - geo['keyholeVaporCavityDepth_um']:6.1f} "
              f"{geo['keyholeVaporCavityDepth_um']:5.1f} {srv['hydrodynamicsAndRecoil']['peakTemperature_C']:7.0f} | "
              f"{new['w_um']:6.1f} {new['d_iso_um']:6.1f} {new['e_um']:6.1f} {new['depth_um']:6.1f} {new['peak_C']:7.0f} | {new['status']}")


if __name__ == "__main__":
    main()
