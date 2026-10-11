#!/usr/bin/env python3
"""
Eagar–Tsai 3D traveling Gaussian heat source (Welding Journal, Dec 1983, 346-s–354-s).

Quasi-steady temperature on a semi-infinite solid with an adiabatic free surface
(image-source factor 2), conduction only. Absorbed power P_eff is spread as the
surface intensity I(r) = 2 P_eff /(π r0²) · exp(−2 r²/r0²): r0 is the 1/e² beam
radius, σ = r0/2 is the Gaussian standard deviation.

Dimensionless form used here (X = x/σ, Y = y/σ, Z = z/σ, U = v σ/(2α), τ = 4 α t'/(2 σ²)):

    ΔT = P_eff /(2π √(2π) k σ) · ∫₀^∞ dτ τ^{-1/2} (1+τ)^{-1}
         exp(−((X + U τ)² + Y²)/(2(1+τ)) − Z²/(2τ))

With τ = u² the integrand becomes 2/(1+u²) · exp(…), bounded on [0, ∞). Checks the
implementation must satisfy (test_eagar_tsai.py): static centre ΔT(0) = P_eff/(√(2π) k r0);
r0 → 0 recovers the Rosenthal point source; the independent dimensional integral at
reference points within 0.5 %.

No Marangoni advection, no recoil keyhole; finite peak T and explicit spot-size
dependence are the physical gains over a point source.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.polynomial.legendre import leggauss

MODEL_ID = "eagar-tsai-v2"

# Composite Gauss–Legendre in u = √τ: a first panel [0, u0], geometric panels (×2) while their
# width stays below the wake-pulse scale du = KAPPA/(√2 U), then uniform panels of width du up to
# u_max. The far-wake pulse of a point X < 0 sits at u_p = √(|X|/U) with standard deviation
# 1/(√2 U) in u at every distance, so uniform-in-u panels resolve it at any distance Péclet
# number (geometric panels alone lost 0.6 % at 3 m/s near the window edge).
_GL_GEOMETRIC_N = 16
_GL_UNIFORM_N = 8
_PULSE_PANEL_SIGMAS = 1.5
# Wake window (laser frame, x < 0) the quadrature is sized for at bind time; temperature_C widens
# it on demand, so no point is ever evaluated with a truncated quadrature (never silently zero).
WAKE_LENGTH_M = 1.5e-3
# exp(−E_CUT) is the truncation level of the x-Gaussian tail beyond the far-wake pulse.
_E_CUT = 9.0


def _as_float64(value):
    return np.asarray(value, dtype=np.float64)


def _composite_nodes(u_max: float, du: float, u0: float = 0.05):
    xi_g, w_g = leggauss(_GL_GEOMETRIC_N)
    xi_u, w_u = leggauss(_GL_UNIFORM_N)
    edges = [0.0, u0]
    while edges[-1] < du and edges[-1] * 2.0 < u_max:
        edges.append(edges[-1] * 2.0)
    us, ws = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        us.append(0.5 * (b - a) * (xi_g + 1.0) + a)
        ws.append(w_g * (0.5 * (b - a)))
    lo = edges[-1]
    while lo < u_max:
        hi = lo + du if lo + du < u_max else u_max
        us.append(0.5 * (hi - lo) * (xi_u + 1.0) + lo)
        ws.append(w_u * (0.5 * (hi - lo)))
        lo = hi
    return np.concatenate(us), np.concatenate(ws)


class EagarTsaiField:
    """Cached quadrature for T(x, y, z) in the laser-attached frame (laser at origin, +x travel)."""

    def __init__(self, T0_C: float, P_eff: float, k_th: float, alpha_th: float, r0_m: float):
        self.T0_C = float(T0_C)
        self.P_eff = float(P_eff)
        self.k_th = max(1e-6, float(k_th))
        self.alpha_th = max(1e-12, float(alpha_th))
        self.r0_m = max(1e-7, float(r0_m))
        self.sigma_m = 0.5 * self.r0_m
        self._pref = self.P_eff / (2.0 * math.pi * math.sqrt(2.0 * math.pi) * self.k_th * self.sigma_m)
        self.v_star = 0.0  # U = v σ /(2 α), set in bind_speed
        self._u = None
        self._w = None
        self._u2 = None
        self._den = None

    def bind_speed(self, v_scan_m_s: float) -> "EagarTsaiField":
        v = max(1e-6, float(v_scan_m_s))
        self.v_star = v * self.sigma_m / (2.0 * self.alpha_th)
        self._build(WAKE_LENGTH_M)
        return self

    def _build(self, wake_m: float) -> None:
        """Quadrature nodes for points down to x = -wake_m behind the source."""
        U = self.v_star
        X_wake = wake_m / self.sigma_m
        # Far-wake pulse centre u_p² = X_wake/U; its half-width in Uu² is √(2(1+u_p²)) per e-fold.
        u_p2 = X_wake / U
        u_max = max(math.sqrt(2.0 * _E_CUT) / U,
                    math.sqrt((X_wake + _E_CUT * math.sqrt(2.0 * (1.0 + u_p2)) + _E_CUT) / U)) + 1.0
        du = _PULSE_PANEL_SIGMAS / (math.sqrt(2.0) * U)
        self._u, self._w = _composite_nodes(u_max, du)
        self._u2 = self._u * self._u
        self._den = self._u2 + 1.0
        self._wake_m = wake_m

    def temperature_C(self, x_m, y_m, z_m):
        """Scalar or numpy array temperature in °C. z ≥ 0 is depth into the solid."""
        if self._u is None:
            raise RuntimeError("EagarTsaiField.bind_speed() must be called first.")
        x = _as_float64(x_m)
        y = _as_float64(y_m)
        z = _as_float64(np.abs(z_m))
        scalar = x.ndim == 0 and y.ndim == 0 and z.ndim == 0
        x, y, z = np.broadcast_arrays(np.atleast_1d(x), np.atleast_1d(y), np.atleast_1d(z))
        shape = x.shape
        x_min = float(x.min())
        if -x_min > self._wake_m:
            # Adaptive wake window (never silently truncated); the window only grows.
            self._build(1.25 * -x_min)
        X = x.reshape(-1) / self.sigma_m
        Y = y.reshape(-1) / self.sigma_m
        Z = z.reshape(-1) / self.sigma_m

        u2 = self._u2[:, None]
        den = self._den[:, None]
        w = self._w[:, None]
        # Past source position in the laser frame: X + U τ (wake at x < 0).
        dx = X[None, :] + self.v_star * u2
        z_term = (Z[None, :] ** 2) / (2.0 * u2)  # u > 0 at every Gauss node
        expo = -((dx * dx + Y[None, :] ** 2) / (2.0 * den)) - z_term
        integrand = (2.0 / den) * np.exp(np.clip(expo, -700.0, 0.0))
        T = self.T0_C + self._pref * np.sum(w * integrand, axis=0)
        T = T.reshape(shape)
        if scalar:
            return float(T.reshape(-1)[0])
        return T


def eagar_tsai_temperature_C(x_m, y_m, z_m, T0_C, P_eff, k_th, v_scan, alpha_th, r0_m):
    field = EagarTsaiField(T0_C, P_eff, k_th, alpha_th, r0_m).bind_speed(v_scan)
    return field.temperature_C(x_m, y_m, z_m)


# P6 containment (2026-10-11, docs/research/SPEC_p6_containment_2026-10-11.md item 1): the served peak is the
# loss-free surface maximum of this Gaussian source (Eagar & Tsai 1983, printed p.347-s Eq. 6, 8 to 10, p.348-s
# Eq. 11 and Appendix B), a numerical maximum along the axis y = z = 0. Every y != 0 and z > 0 lowers every
# positive time-kernel term, so the surface maximum lies on the axis; for v > 0 it lies behind the beam centre.
SURFACE_MAXIMUM_BASIS = "eagar-tsai-loss-free-surface-maximum"
_SURFACE_MAXIMUM_GRID = 128
_SURFACE_MAXIMUM_XTOL_M = 1e-11


def _i0e(a: float) -> float:
    """exp(-a) I0(a) for a >= 0 (the stationary Gaussian surface profile is proportional to i0e((x/r0)^2))."""
    if a < 500.0:
        return float(np.i0(a)) * math.exp(-a)
    # Asymptotic series with positive terms (every truncation is a lower bound); the margin makes it an upper bound.
    s = 1.0 + 1.0 / (8.0 * a) + 9.0 / (128.0 * a * a) + 225.0 / (3072.0 * a ** 3)
    return s * (1.0 + 1e-6) / math.sqrt(2.0 * math.pi * a)


def eagar_tsai_surface_maximum(T0_C: float, P_eff: float, k_th: float, alpha_th: float, r0_m: float,
                               v_scan_m_s: float) -> dict:
    """Loss-free surface maximum of the Eagar-Tsai field on the axis y = z = 0, with its x location.

    Search: the beam centre T(0,0,0) and a rear bracket [x_left, 0] that is widened (doubling) until the
    stationary surface bound T0 + P_eff/(sqrt(2 pi) k r0) i0e((x/r0)^2), which bounds every moving kernel
    (every moving point kernel is below its stationary counterpart), falls below the centre value; a uniform
    scan of the bracket, then a golden-section refinement of every interior candidate bracket. A numerical
    maximisation, not a proof of unimodality. Conduction only: no evaporation, flow or recoil loss, so above
    the boiling point it is not a wall temperature (Eagar & Tsai 1983 p.348-s: an impossible situation).
    """
    field = EagarTsaiField(T0_C, P_eff, k_th, alpha_th, r0_m).bind_speed(v_scan_m_s)
    r0 = field.r0_m
    centre = float(field.temperature_C(0.0, 0.0, 0.0))
    stationary_scale = field.P_eff / (math.sqrt(2.0 * math.pi) * field.k_th * r0)
    left = -2.0
    while field.T0_C + stationary_scale * _i0e(left * left) >= centre:
        left *= 2.0
        if left < -1048576.0:
            raise RuntimeError("could not bound the Eagar-Tsai surface maximum search")
    n = _SURFACE_MAXIMUM_GRID
    xs = np.array([left * (1.0 - i / n) for i in range(n + 1)]) * r0  # left ... 0, ascending
    temps = field.temperature_C(xs, np.zeros_like(xs), np.zeros_like(xs))
    temps = np.asarray(temps, dtype=np.float64).reshape(-1)
    candidates = [(centre, 0.0), (float(temps[0]), float(xs[0]))]

    def axis(x):
        return float(field.temperature_C(x, 0.0, 0.0))

    for i in range(1, n):
        if temps[i] >= temps[i - 1] and temps[i] >= temps[i + 1]:
            a, b = float(xs[i - 1]), float(xs[i + 1])
            phi = (math.sqrt(5.0) - 1.0) / 2.0
            c = b - phi * (b - a)
            d = a + phi * (b - a)
            fc, fd = axis(c), axis(d)
            while b - a > _SURFACE_MAXIMUM_XTOL_M:
                if fc > fd:
                    b, d, fd = d, c, fc
                    c = b - phi * (b - a)
                    fc = axis(c)
                else:
                    a, c, fc = c, d, fd
                    d = a + phi * (b - a)
                    fd = axis(d)
            x_best = 0.5 * (a + b)
            candidates.append((axis(x_best), x_best))
    T_max, x_max = max(candidates)
    return {
        "modelId": MODEL_ID,
        "basis": SURFACE_MAXIMUM_BASIS,
        "T_C": float(T_max),
        "x_m": float(x_max),
        "beamCentre_T_C": centre,
        "searchStart_m": float(left * r0),
    }
