#!/usr/bin/env python3
"""
Fabbro keyhole-depth screening (Appl. Sci. 2020, 10, 1487; DOI 10.3390/app10041487).

Cylindrical multiple-reflection keyhole, conduction loss only:

    e = A P / [k (T_v − T_0) (m Pe + n)]
    R = e / d = R0 / (1 + V / V0)

Pe = V d / (2 α), m ≈ 2.4, n ≈ 3 for 2 ≤ Pe ≤ 10 (Fabbro §2.1). Outside that band the
linear g(Pe) fit is extrapolated and the result carries pecletInFitRange = False.
In Fabbro eq. 2 A(R) is the keyhole absorptivity, which depends on the aspect ratio R = e/d
through multiple reflection. It is NOT modelled here: callers pass the flat-surface (Fresnel)
absorptivity, a disclosed lower bound (measured absorptance rises at R about 1: Trapp 2017,
Deisenroth 2020, Fabbro 2020 Sec. 4.1), so the depth from this leg is biased low.
The dH/hs 15 -> 30 linear onset ramp ("blend") is an uncited screening heuristic, not Fabbro.
Not CFD, not a collapse simulation.
"""

from __future__ import annotations

import math

MODEL_ID = "fabbro-keyhole-v1"
ENTHALPY_ONSET = 15.0
ENTHALPY_KEYHOLE = 30.0
# Fabbro linear g(Pe) ≈ m Pe + n in the LPBF-relevant Peclet band.
FABBRO_M = 2.4
FABBRO_N = 3.0
PECLET_FIT_MIN = 2.0
PECLET_FIT_MAX = 10.0


def fabbro_keyhole_depth_m(
    power_W: float,
    speed_m_s: float,
    beam_diameter_m: float,
    k_W_mK: float,
    alpha_m2_s: float,
    T_vap_C: float,
    T0_C: float,
    absorptivity: float,
    normalized_enthalpy: float,
) -> dict:
    """Return keyhole depth from the free surface. Zero below King transition (ΔH/hs < 15)."""
    P = max(1.0, float(power_W))
    v = max(1e-4, float(speed_m_s))
    d = max(8e-6, float(beam_diameter_m))
    k = max(1e-3, float(k_W_mK))
    alpha = max(1e-12, float(alpha_m2_s))
    A = min(0.99, max(0.02, float(absorptivity)))
    dT = max(50.0, float(T_vap_C) - float(T0_C))
    enth = float(normalized_enthalpy)

    Pe = v * d / (2.0 * alpha)
    # Eq. 2. Eq. 3 (R = R0 / (1 + V/V0)) is the same expression rewritten, so it is not averaged in.
    e = A * P / (k * dT * (FABBRO_M * Pe + FABBRO_N))
    R0 = A * P / (FABBRO_N * d * k * dT)
    V0 = (2.0 * FABBRO_N * alpha) / (FABBRO_M * d)

    if enth < ENTHALPY_ONSET:
        scale = 0.0
    elif enth < ENTHALPY_KEYHOLE:
        scale = (enth - ENTHALPY_ONSET) / (ENTHALPY_KEYHOLE - ENTHALPY_ONSET)
    else:
        scale = 1.0
    e *= scale

    return {
        "modelId": MODEL_ID,
        "depth_m": float(e),
        "aspectRatio_e_over_d": float(e / d),
        "peclet": float(Pe),
        "pecletInFitRange": bool(PECLET_FIT_MIN <= Pe <= PECLET_FIT_MAX),
        "blendBasis": "uncited linear dH/hs onset ramp 15 -> 30 (screening heuristic, not Fabbro)",
        "R0": float(R0),
        "V0_m_s": float(V0),
        "blend": float(scale),
        "doi": "10.3390/app10041487",
    }
