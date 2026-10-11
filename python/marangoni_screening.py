#!/usr/bin/env python3
"""
Heiple–Roper Marangoni screening (not Navier–Stokes CFD).

Heiple & Roper, *Welding Journal* 61 (1982) / follow-on 1983: surface-active S (or O)
flips ∂γ/∂T and therefore the surface-flow direction — outward (wide, shallow) when
∂γ/∂T < 0, inward (narrow, deep) when ∂γ/∂T > 0.

Inversion band 30–60 ppm S is the welding / LPBF review range (Heiple–Roper;
Ebrahimi et al., *Int. J. Heat Mass Transfer* 2021, DOI 10.1016/j.ijheatmasstransfer.2020.120801).
Alloy ∂γ/∂T comes from `four_alloy_materials.py`. This module does **not** refit W/D.

Surface velocity: order-of-magnitude estimate of DebRoy & David, *Rev. Mod. Phys.* 67 (1995) 85,
Eq. (8) (DOI 10.1103/RevModPhys.67.85): Marangoni stress (Eq. 6) balanced against laminar
boundary-layer shear (Eq. 7) at y = W/4, u_m^(3/2) ≈ |dγ/dT|·(dT/dy)·W^(1/2) / (0.664·ρ^(1/2)·μ^(1/2)).
"""

from __future__ import annotations

import math

MODEL_ID = "marangoni-heiple-v1"
SULFUR_OUTWARD_PPM = 30.0
SULFUR_INWARD_PPM = 60.0
SURFACE_VELOCITY_DOI = "10.1103/RevModPhys.67.85"


def debroy_david_surface_velocity_m_s(
    d_gamma_N_mK: float, dT_dy_K_m: float, pool_width_m: float, density_kg_m3: float, viscosity_Pa_s: float
) -> float:
    """DebRoy & David (1995) Eq. (8): u_m^(3/2) ≈ |dγ/dT|·(dT/dy)·W^(1/2) / (0.664·sqrt(ρμ)). SI in, m/s out."""
    drive = abs(float(d_gamma_N_mK)) * abs(float(dT_dy_K_m)) * math.sqrt(max(0.0, float(pool_width_m)))
    return (drive / (0.664 * math.sqrt(float(density_kg_m3) * float(viscosity_Pa_s)))) ** (2.0 / 3.0)


def heiple_roper_d_gamma_dT(d_gamma_pure_N_mK: float, sulfur_ppm: float) -> float:
    """Linear blend across the 30–60 ppm inversion band. Sign follows Heiple–Roper."""
    s = max(0.0, float(sulfur_ppm))
    mag = abs(float(d_gamma_pure_N_mK))
    if mag < 1e-9:
        return 0.0
    low_s = -mag if d_gamma_pure_N_mK <= 0.0 else float(d_gamma_pure_N_mK)
    high_s = mag
    if s <= SULFUR_OUTWARD_PPM:
        return low_s
    if s >= SULFUR_INWARD_PPM:
        return high_s
    blend = (s - SULFUR_OUTWARD_PPM) / (SULFUR_INWARD_PPM - SULFUR_OUTWARD_PPM)
    return low_s + (high_s - low_s) * blend


def marangoni_flow_direction(d_gamma_pure_N_mK: float, sulfur_ppm: float) -> dict:
    """Heiple–Roper direction and note from the blended dγ/dT alone (no temperature input).

    P6 containment (2026-10-11): served when the Marangoni number is unavailable (no served peak), so the
    direction never depends on a clipped or unsourced surface temperature."""
    d_gamma = heiple_roper_d_gamma_dT(d_gamma_pure_N_mK, sulfur_ppm)
    if d_gamma > 0.0:
        direction = "inward"
        aspect_note = "Heiple–Roper: inward jet — deeper / narrower pool expected (not applied to W/D)."
    elif d_gamma < 0.0:
        direction = "outward"
        aspect_note = "Heiple–Roper: outward rolls — wider / shallower pool expected (not applied to W/D)."
    else:
        direction = "neutral"
        aspect_note = "∂γ/∂T ≈ 0 in the 30–60 ppm inversion band."
    return {"dGamma_dT_N_mK": float(d_gamma), "sulfur_ppm": float(sulfur_ppm), "flowDirection": direction,
            "aspectNote": aspect_note}


def marangoni_screening(
    d_gamma_pure_N_mK: float,
    viscosity_Pa_s: float,
    alpha_m2_s: float,
    density_kg_m3: float,
    half_width_m: float,
    T_surface_C: float,
    T_liquidus_C: float,
    sulfur_ppm: float = 15.0,
) -> dict:
    """Dimensionless Ma / Pe_Ma and flow direction. Geometry stays thermal."""
    flow = marangoni_flow_direction(d_gamma_pure_N_mK, sulfur_ppm)
    d_gamma = flow["dGamma_dT_N_mK"]
    delta_T = max(10.0, float(T_surface_C) - float(T_liquidus_C))
    L = max(4e-6, float(half_width_m))
    mu = max(1e-6, float(viscosity_Pa_s))
    alpha = max(1e-12, float(alpha_m2_s))
    rho = max(100.0, float(density_kg_m3))

    Ma = (abs(d_gamma) * delta_T * L) / (mu * alpha)
    # DebRoy & David (1995) Eq. (8) with the screening gradient dT/dy ≈ ΔT / L over the half-width L
    # (W = 2L). Order-of-magnitude only; replaces sqrt(|dγ/dT|ΔT/ρ), which had units of m^1.5/s.
    u_m_s = debroy_david_surface_velocity_m_s(d_gamma, delta_T / L, 2.0 * L, rho, mu)
    Pe_Ma = (u_m_s * L) / alpha

    return {
        "modelId": MODEL_ID,
        "dGamma_dT_N_mK": float(d_gamma),
        "sulfur_ppm": float(sulfur_ppm),
        "flowDirection": flow["flowDirection"],
        "marangoniNumber": float(Ma),
        "surfaceVelocity_m_s": float(u_m_s),
        "surfaceVelocityDoi": SURFACE_VELOCITY_DOI,
        "pecletMarangoni": float(Pe_Ma),
        "geometrySource": "thermal",
        "aspectNote": flow["aspectNote"],
        "doi": "10.1016/j.ijheatmasstransfer.2020.120801",
    }
