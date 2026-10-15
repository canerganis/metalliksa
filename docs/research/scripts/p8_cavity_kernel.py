# Vendored safe, synthetic-only P3 kernel. No runner or experimental data imports.
# Upstream source: c4470b017cfe533c74b23dc5712a2df720ae00c4:python/tools/p3_cavity_model_sketch.py
# Git blob: b762dc6268b82f15f9e1fe529845b5e3e9013415
# Original SHA256: eefd4c80c1341b776d3e0166dfcc45e140d9d8ff3448425415cce15676a11d81
# Amendment identity: p8-amendment2-kernel-2026-10-15
# Changes: Gaussian dwell prefactor /sqrt(2); D(e) absolute tolerance 1e-14 m
# and relative tolerance 1e-11, retaining upstream root residual/stability rules.
"""Synthetic, conditional cavity sketch; not a served or validated LPBF model.

Companion: docs/research/DERIVATION_p3_keyhole_cavity_2026-10-11.md.
SI units throughout. No datasets or results files are read. Existing NumPy and
SciPy supply quadrature and E1. Optical and deposition closures are hypotheses.
Run with python -B to avoid creating bytecode outside the two permitted files.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math

import numpy as np
from scipy.special import exp1, iv, kv, kvp
from scipy.optimize import minimize_scalar
from scipy.integrate import quad

OUTSIDE = math.exp(-2.0)
INSIDE = 1.0 - OUTSIDE
GAS_CONSTANT = 8.31446261815324


@lru_cache(maxsize=8192)
def cone_reflection_radii(R: float) -> tuple[float, ...]:
    """Independent homogeneous meridional trace, aperture radius a=.5.

    Trace the first wall hit at (r,2Rr), with r=1. Each subsequent hit
    scales with launch radius r; survival requires r<=R/z_hit. Integrating
    those exact survival intervals avoids discrete ray quadrature artifacts.
    Reflection continues while traveling upward until the aperture is crossed.
    The gate script was read, but is neither imported nor called.
    """
    _positive(R=R)
    x, z, dx, dz, side = 1.0, 2.0 * R, 0.0, -1.0, 1.0
    radius, limits = 0.5, [0.5]
    norm = math.hypot(0.5, R)
    for _ in range(10000):
        tx, tz = side * 0.5 / norm, R / norm
        dot = dx * tx + dz * tz
        dx, dz = 2 * dot * tx - dx, 2 * dot * tz - dz
        side = -side
        slope = side / (2 * R)
        denominator = dx - slope * dz
        if abs(denominator) < 1e-14:
            return tuple(limits)
        distance = (slope * z - x) / denominator
        if distance <= 1e-13:
            return tuple(limits)
        x, z = x + distance * dx, z + distance * dz
        if z <= 0:
            return tuple(limits)
        radius = min(radius, 0.5, R / z)
        limits.append(radius)
    raise ValueError("cone reflection cap reached; aspect ratio outside numerical scope")


def specular_cone(R: float, A0: float, weighting: str = "gaussian") -> float:
    """Exact constant-A0 cone survival integral within D4sigma aperture.

    Radial Gaussian exp(-8r**2), or uniform disk as an independent sensitivity.
    Coherent interference, angle-dependent Fresnel, plasma and roughness absent.
    """
    if weighting not in ("gaussian", "disk"):
        raise ValueError("weighting must be gaussian or disk")
    if R == 0:
        return A0
    limits = cone_reflection_radii(R)
    return math.fsum(A0 * (1-A0)**n *
                     (-math.expm1(-8*b*b)/INSIDE if weighting == "gaussian" else 4*b*b)
                     for n, b in enumerate(limits))


def _positive(**values: float) -> None:
    for name, value in values.items():
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")


def _nonnegative(**values: float) -> None:
    for name, value in values.items():
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and nonnegative")


def A_R(R: float, A0: float, form: str = "specular_cone") -> float:
    """Conditional cavity absorption, not primary alloy Fresnel data.

    specular_cone: independently traced meridional, Gaussian aperture weighting.
    kaplan_mean: Kaplan 1994 p1808 Eq24 upward-turn stopping surrogate;
    Fig3 wall angles<=30deg (R>=.866). Constant normal-incidence Fresnel
    per reflection is sourced; the N>=1 floor and cone transfer are additions.
    kelly_cone/v: Kelly 1966 p926 Eq5, Eq6 and p927 following text,
    exact *local vertex* diffuse absorptance, not beam averaged absorption.
    gouffe: Coleman 2024 manuscript pp11-12 Eq7 with cone G and F.
    Its Eq8 conduction switch is deliberately not included.
    """
    _nonnegative(R=R)
    if not math.isfinite(A0) or not 0 < A0 < 1:
        raise ValueError("A0 must be strictly between zero and one")
    if form not in ("specular_cone", "specular_disk", "kaplan_mean", "kelly_cone", "kelly_v", "gouffe", "flat"):
        raise ValueError("unknown optical form")
    if R == 0 or form == "flat":
        return A0
    if form in ("specular_cone", "specular_disk"):
        return specular_cone(R, A0, "disk" if form == "specular_disk" else "gaussian")
    if form == "kaplan_mean":
        N = max(1.0, math.pi / (4.0 * math.atan2(1.0, 2.0 * R)))
        return -math.expm1(N * math.log1p(-A0))
    t = math.hypot(1.0, 2.0 * R)
    if form in ("kelly_cone", "kelly_v"):
        p = 3 if form == "kelly_cone" else 2
        return A0 / (A0 + (1 - A0) * t ** (-p))
    G, F = 1.0 / (1.0 + t), t ** -3
    return A0 * (1 + (1 - A0) * (G - F)) / (A0 + (1 - A0) * G)


def total_absorptance(R: float, A0: float, form: str = "specular_cone") -> float:
    """Every arm: D4sigma radius equals Gaussian 1/e**2 radius."""
    return INSIDE * A_R(R, A0, form) + OUTSIDE * A0


def thermal_g(Pe: float, closure: str = "gpm") -> float:
    """Separate fitted/exact thermal responses, never a zero-speed drilling law.

    gpm: Fabbro 2020 p7 Eqs11,13, m1=2.1 n1=2.2, GPM calculations;
    Pe is converted D4sigma->FWHM internally, .588705Pe. Coupling GPM
    thermal fit to a D4sigma optical cone is an explicitly inferred transfer.
    cylinder2020: pp2-3 Eqs1-2, m=2.4 n=3, only fitted for 2<=Pe<=10.
    cylinder_exact: derived Bessel solution of Fabbro 2018 Eq4 moving
    isothermal cylinder, 24 harmonics, restricted to 0.01<=Pe<=10.
    This fixes thermal low-Pe extrapolation, not cavity mechanics/low aspect.
    """
    _nonnegative(Pe=Pe)
    if closure == "cylinder_exact":
        if not 0.01 <= Pe <= 10:
            raise ValueError("exact-cylinder numerical scope is 0.01<=Pe<=10; no Pe=0 law")
        lam = Pe / 2
        term0 = float(iv(0, lam) ** 2 * kvp(0, lam) / kv(0, lam))
        terms = [2 * (-1) ** n * float(iv(n, lam) ** 2 * kvp(n, lam) / kv(n, lam))
                 for n in range(1, 25)]
        return -2 * math.pi * lam * math.fsum([term0, *terms])
    # Fabbro2020 Sec3.4 diameter is FWHM=.sqrt(ln2/2)*D4sigma.
    # Removed cylinder2018 m~5,n~3: g(5)=28 vs exact~15.5, inconsistent.
    coefficients = {"gpm": (2.1, 2.2), "cylinder2020": (2.4, 3.0)}
    if closure not in coefficients:
        raise ValueError("unknown thermal closure")
    m, n = coefficients[closure]
    if closure == "gpm":
        f = math.sqrt(math.log(2)/2)
        return m*f*Pe+n  # GPM Pe uses FWHM; e itself is unchanged
    return m * Pe + n


def energy_balance_residual(e: float, P: float, v: float, d: float,
                            K: float, delta_Tv: float, alpha: float,
                            A0: float, *, form: str = "specular_cone",
                            closure: str = "gpm", P_star: float = 0.0) -> float:
    """Residual in W: K*delta_Tv*g*e - A_tot(e/d)*(P-Pstar)+.

    Fabbro 2020 Eqs13-14, replacing *front* A_F with total A is inference.
    P_star is supplied by onset_power or an explicitly labeled inception
    sensitivity. A finite-aspect geometric threshold is a different event;
    piston_threshold_sensitivity must not supply this e=0 inception offset.
    P_star=0 reproduces unshifted Eq13 and has no physical onset gate.
    Low Pe values are diagnostic extrapolations; see solve_e warnings.
    """
    _nonnegative(e=e, P=P, v=v, P_star=P_star)
    _positive(d=d, K=K, delta_Tv=delta_Tv, alpha=alpha)
    return K * delta_Tv * thermal_g(v * d / (2 * alpha), closure) * e \
        - total_absorptance(e / d, A0, form) * max(0.0, P - P_star)


def _bisect(f, lo: float, hi: float, *, atol: float = 1e-10,
            rtol: float = 1e-10, maxiter: int = 80) -> float:
    """Bounded bisection; error or iteration exhaustion is never silent."""
    flo, fhi = f(lo), f(hi)
    if flo == 0:
        return lo
    if fhi == 0:
        return hi
    if flo * fhi > 0:
        raise ValueError("root not bracketed")
    for _ in range(maxiter):
        mid = lo + (hi - lo) / 2
        fm = f(mid)
        if fm == 0 or hi - lo <= atol + rtol * max(abs(lo), abs(hi)):
            return mid
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    raise RuntimeError("bisection did not reach requested tolerance")


def _kelly_folds(A0: float) -> tuple[float, ...]:
    """All cone h=R/A extrema, from Kelly Eq5 plus derived calculus.

    h'=0 becomes t^5-2Ct^2+3C=0, t=sqrt(1+4R^2), C=(1-A0)/A0.
    The polynomial has one minimum for t>1, so two brackets suffice.
    """
    C = (1 - A0) / A0
    Ccrit = 0.5 * (2.5 ** 2.5)
    if C < Ccrit:
        return ()
    tmin = (4 * C / 5) ** (1 / 3)
    if math.isclose(C, Ccrit, rel_tol=1e-13):
        return (math.sqrt(tmin * tmin - 1) / 2,)
    polynomial = lambda t: t ** 5 - 2 * C * t * t + 3 * C
    ts = (_bisect(polynomial, 1.0, tmin),
          _bisect(polynomial, tmin, (2 * C) ** (1 / 3)))
    return tuple(math.sqrt(t * t - 1) / 2 for t in ts)


@dataclass(frozen=True)
class Root:
    R: float
    e_m: float
    stability: str


@dataclass(frozen=True)
class CavitySolution:
    roots: tuple[Root, ...]
    selected_e_m: float
    Pe: float
    S: float
    warnings: tuple[str, ...]


def _scan_roots(S: float, A0: float, form: str, resolution: int = 1025
                ) -> tuple[Root, ...]:
    """Bracket roots between a*S and aperture-ceiling*S; refine h extrema.

    Smooth folds have no sign change: local extrema are independently minimized
    and inserted as partition boundaries. Exact cone survival integrals are
    continuous; isolated ray-count changes are integrated, never accepted as
    discontinuity roots. This is a bounded numerical scan, not all-root proof.
    Scan-doubling agreement is required for specular/Gouffe arms by solve_e.
    """
    ceiling = INSIDE + OUTSIDE*A0
    lo, hi = A0*S, ceiling*S
    h = lambda r: r / total_absorptance(float(r), A0, form)
    f = lambda r: h(r)-S
    grid = np.linspace(lo,hi,resolution)
    if lo < 4 < hi:
        grid = np.unique(np.r_[grid,np.linspace(lo,4.,resolution)])
    hs = np.array([h(r) for r in grid])
    extrema = []
    for j in range(1,len(grid)-1):
        left, right = hs[j]-hs[j-1], hs[j+1]-hs[j]
        if left*right < 0:
            sign = 1 if left < 0 else -1
            opt = minimize_scalar(lambda r: sign*h(r), bounds=(grid[j-1],grid[j+1]),
                                  method="bounded", options={"xatol":1e-12})
            if not opt.success:
                raise RuntimeError("optical extrema refinement failed")
            extrema.append(float(opt.x))
    cuts = sorted(set([*grid, *extrema]))
    found = []
    tol = 2e-9*max(1.0,S)
    for left,right in zip(cuts[:-1],cuts[1:]):
        if abs(f(left)) < tol:
            found.append(left)
        if f(left)*f(right)<0:
            r = _bisect(f,left,right,atol=1e-12,rtol=1e-11)
            if abs(f(r)) > tol:
                raise RuntimeError("sign flip is not a resolved continuous root")
            found.append(r)
    if abs(f(hi)) < tol:
        found.append(hi)
    unique = []
    for r in sorted(found):
        if unique and abs(r-unique[-1].R) < 1e-7*max(1.0,r):
            continue
        step = 1e-6*max(1.0,r)
        slope = (h(r+step)-h(max(0.,r-step)))/(r+step-max(0.,r-step))
        stability = "neutral" if abs(slope)<1e-4 else ("stable" if slope>0 else "unstable")
        unique.append(Root(r,0.0,stability))
    return tuple(unique)


def solve_e(P: float, v: float, d: float, K: float, delta_Tv: float,
            alpha: float, A0: float, *, form: str = "specular_cone",
            closure: str = "gpm", P_star: float = 0.0,
            branch: str = "forward", require_low_pe_closure: bool = False
            ) -> CavitySolution:
    """Fold-aware bounded scan: forward lowest stable root; reverse highest.

    Relaxation stability h'>0 is inferred, not hydrodynamic stability. Each
    power's forward choice is lowest stable ordinary root. A branch disappears
    at a fold: its next choice is a jump, scored by bracket/jump power and
    branch separation separately from depth; tangent is neutral and excluded
    from selection; if no strictly stable root exists, return an explicit error. Discontinuous
    table sign changes must never be called roots. Lowest-root branch is an
    explicitly declared quasi-static convention, not measured history.
    """
    energy_balance_residual(0.,P,v,d,K,delta_Tv,alpha,A0,
                            form=form,closure=closure,P_star=P_star)
    if branch not in ("forward","reverse"):
        raise ValueError("branch must be forward or reverse")
    Pe = v*d/(2*alpha)
    if require_low_pe_closure and Pe < 2:
        raise ValueError("no sourced low-Pe drilling closure implemented")
    S=max(0.,P-P_star)/(d*K*delta_Tv*thermal_g(Pe,closure))
    warnings=["conditional A_tot replaces front A_F; not validated",
              "root scan convergence is numerical, not a root-count proof"]
    if Pe<2:
        warnings.append("low-Pe diagnostic; drilling/time/recoil unclosed")
    if P_star==0:
        warnings.append("unshifted sensitivity; inception unresolved")
    if S==0:
        return CavitySolution((Root(0.,0.,"stable"),),0.,Pe,S,tuple(warnings))
    roots=_scan_roots(S,A0,form)
    if form in ("specular_cone","specular_disk","gouffe","kelly_cone"):
        refined=_scan_roots(S,A0,form,2049)
        if len(roots)!=len(refined) or any(abs(a.R-b.R)>1e-7*max(1.,a.R)
                                          for a,b in zip(roots,refined)):
            raise RuntimeError("root scan failed resolution-doubling check")
        roots=refined
    if not roots:
        raise RuntimeError("existence bracket produced no resolved root")
    roots=tuple(Root(r.R,d*r.R,r.stability) for r in roots)
    stable=[r for r in roots if r.stability=="stable"]
    if not stable:
        raise RuntimeError("only neutral/unstable roots resolved; exact fold has no strictly stable selection")
    chosen=stable[0] if branch=="forward" else stable[-1]
    fwhm_ratio=math.sqrt(math.log(2)/2)
    if closure=="gpm" and not .5<=chosen.R/fwhm_ratio<=3:
        warnings.append("outside GPM half-maximum aspect fit [0.5,3]")
    if closure.startswith("cylinder"):
        warnings.append("high-aspect isothermal cylinder hypothesis; finite tip/flow unclosed")
    if closure=="cylinder2020" and not 2<=Pe<=10:
        warnings.append("outside exact-cylinder fitted Pe interval [2,10]")
    return CavitySolution(roots,chosen.e_m,Pe,S,tuple(warnings))


def forward_scan(powers, *args, **kwargs):
    """Increasing powers only; report selected branches and resolved jump brackets.

    A jump is loss of the prior lowest branch: root count drops and the chosen
    root crosses its prior unstable separator. Finite power steps give brackets,
    not an exact fold power; unresolved steps require refinement.
    """
    if any(b<=a for a,b in zip(powers[:-1],powers[1:])):
        raise ValueError("forward powers must be strictly increasing")
    solutions=[solve_e(p,*args,branch="forward",**kwargs) for p in powers]
    jumps=[]
    for i,(a,b) in enumerate(zip(solutions[:-1],solutions[1:])):
        separators=[r.e_m for r in a.roots if r.stability=="unstable"
                    and r.e_m>a.selected_e_m]
        if len(b.roots)<len(a.roots) and separators and b.selected_e_m>min(separators):
            jumps.append((powers[i],powers[i+1],a.selected_e_m,b.selected_e_m))
    return tuple(solutions),tuple(jumps)

def _axial_temperature(z: float, e: float, Q: float, K: float, beta: float,
                       chi: float) -> float:
    """Derived finite uniform line plus surface point, z>e, Neumann image."""
    if e == 0:
        return Q * math.exp(-beta * z) / (2 * math.pi * K * z)
    surface = (1 - chi) * Q * math.exp(-beta * z) / (2 * math.pi * K * z)
    integral = (math.log1p(2 * e / (z - e)) if beta == 0 else
                float(exp1(beta * (z - e)) - exp1(beta * (z + e))))
    return surface + chi * Q * integral / (4 * math.pi * K * e)


def _peak_temperature(temperature, L: float, samples: int) -> float:
    """Approximate global trailing-x maximum: grid then refine every peak.

    Threshold feasibility bound is -L<=x<=0. No unimodality is assumed.
    The grid has to be convergence checked; this is not certified optimization.
    """
    xs = -L * np.linspace(1.0, 0.0, samples) ** 2
    values = temperature(xs)
    best = float(np.max(values))
    for i in range(1, samples - 1):
        if values[i] >= values[i - 1] and values[i] >= values[i + 1]:
            fit = minimize_scalar(lambda x: -float(temperature(np.array([x]))[0]),
                                  bounds=(xs[i - 1], xs[i + 1]), method="bounded",
                                  options={"xatol": max(1e-14, L * 1e-9), "maxiter": 80})
            if not fit.success:
                raise RuntimeError("trailing-x refinement failed")
            best = max(best, -float(fit.fun))
    return best


def melt_depth_from_e(e: float, Q_net: float, v: float, K: float,
                      delta_Tm: float, alpha: float, *, chi: float,
                      observable: str = "axial", order: int = 32,
                      x_samples: int = 65) -> float:
    """Conditional liquidus postprocessor, not a sourced etched-depth law.

    Kaplan 1994 p1805 motivates point/line superposition, p1806 Eq1 is an
    *infinite* Rosenthal line. Here a finite vertical uniform q=chi*Q_net/e
    and its Neumann image are derived in the companion; chi is REQUIRED from
    energy_partition, or explicitly chi=1 pure-Fabbro sensitivity. Never fit chi.
    Q_net already excludes vapour/export loss: never add AP on top again.
    This function's e=0 limit is a singular surface point, not a finite
    Gaussian beam. The P8 caller dispatches P<=P_star to its independent
    Gaussian floor instead; the retained above-onset field therefore has a
    field-shape depth step at inception even with continuous photon power.
    A same-Q_net e=0 evaluation is a counterfactual field-shape diagnostic,
    not the P8 below-onset prediction or a cavity contribution.
    Rai 2007 pp5757-5758 Eqs4-6,11 include physics omitted here.
    axial returns x=y=0 depth; envelope maximizes trailing x numerically and
    is the conditional etched-depth observable. Requires grid convergence.
    Outer depth bracket [e,e+Q/(2*pi*K*delta_Tm)], 1e-14 m abs tolerance,
    80 iterations maximum. Uniform-line temperature is logarithmically singular
    at tip; very thin predicted shells can be below tolerance/resolution.
    """
    _nonnegative(e=e, Q_net=Q_net, v=v)
    _positive(K=K, delta_Tm=delta_Tm, alpha=alpha)
    if not math.isfinite(chi) or not 0 <= chi <= 1:
        raise ValueError("chi must be in [0,1]")
    if observable not in ("axial", "envelope"):
        raise ValueError("observable must be axial or envelope")
    if order < 8 or x_samples < 9:
        raise ValueError("quadrature/search resolution too small")
    if Q_net == 0:
        if e > 0:
            raise ValueError("zero thermal power cannot support a positive cavity")
        return 0.0
    beta = v / (2 * alpha)
    L = Q_net / (2 * math.pi * K * delta_Tm)
    if observable == "envelope":
        nodes, weights = np.polynomial.legendre.leggauss(order)

    def temperature(z):
        if observable == "axial":
            return _axial_temperature(z, e, Q_net, K, beta, chi)
        # For uniform q, real and image intervals join to w in [z-e,z+e].
        # Log-coordinate quadrature resolves a thin tip shell without cutoff.
        if e > 0 and chi > 0:
            loglo, loghi = math.log(z - e), math.log(z + e)
            half = (loghi - loglo) / 2
            w = np.exp((loghi + loglo) / 2 + half * nodes)
        def field(xs):
            r0 = np.hypot(xs, z)
            result = (1 - chi if e > 0 else 1.0) * Q_net \
                * np.exp(-beta * (xs + r0)) / (2 * math.pi * K * r0)
            if e > 0 and chi > 0:
                r = np.hypot(xs[:, None], w[None, :])
                values = np.exp(-beta * (xs[:, None] + r)) / r * w
                result += chi * Q_net / (4 * math.pi * K * e) \
                    * half * (values @ weights)
            return result
        return _peak_temperature(field, L, x_samples)

    lo = math.nextafter(e, math.inf) if e > 0 else L * 1e-12
    hi = e + L
    if temperature(lo) < delta_Tm:
        # No below-tip isotherm exists at represented resolution; do not max(D,e).
        raise ValueError("thermal postprocessor does not support a resolved liquidus below tip")
    return _bisect(lambda z: temperature(z) - delta_Tm, lo, hi,
                   atol=1e-14, rtol=1e-11)


def melt_surface_width_from_e(e: float, Q_net: float, v: float, K: float,
                              delta_Tm: float, alpha: float, *, chi: float,
                              order: int = 48, x_samples: int = 65) -> float:
    """Conditional top-surface liquidus width, not maximum etched width.

    Same inferred Green source as melt_depth_from_e. At fixed Q_net it cannot
    exceed the surface point source width. Absorptance feedback can change Q.
    """
    _nonnegative(e=e, v=v)
    _positive(Q_net=Q_net, K=K, delta_Tm=delta_Tm, alpha=alpha)
    if not math.isfinite(chi) or not 0 <= chi <= 1 or order < 8 or x_samples < 9:
        raise ValueError("invalid deposition split or numerical resolution")
    beta = v / (2 * alpha)
    L = Q_net / (2 * math.pi * K * delta_Tm)
    nodes, weights = np.polynomial.legendre.leggauss(order)
    def temperature(y):
        def field(xs):
            r0 = np.hypot(xs, y)
            result = (1 - chi if e > 0 else 1.0) * Q_net \
                * np.exp(-beta * (xs + r0)) / (2 * math.pi * K * r0)
            if e > 0 and chi > 0:
                # s=h*sinh(u), h=hypot(x,y): ds/r=du exactly, no core cutoff.
                half = np.arcsinh(e / r0) / 2
                u = half[:, None] * (1 + nodes)
                r = r0[:, None] * np.cosh(u)
                result += chi * Q_net / (2 * math.pi * K * e) * half \
                    * (np.exp(-beta * (xs[:, None] + r)) @ weights)
            return result
        return _peak_temperature(field, L, x_samples)
    lo = L * 1e-12
    if temperature(lo) < delta_Tm:
        raise ValueError("surface intersection below search resolution; not physical zero width")
    return 2 * _bisect(lambda y: temperature(y) - delta_Tm, lo, L,
                       atol=1e-14, rtol=1e-11)


@dataclass(frozen=True)
class Material:
    name: str
    K: float
    rho: float
    cp: float
    Tm: float
    Tv: float
    A0: float
    Lv: float
    Mw: float
    Lm: float
    cp_liquid: float
    T0: float = 293.15

    @property
    def alpha(self):
        return self.K / (self.rho * self.cp)




def threshold_temperature(mat: Material, beta_recoil: float = .2) -> float:
    """Fabbro2020 AppA p20 EqsA10-A11, alloy-specific latent-vapour c."""
    _positive(Lv=mat.Lv,Mw=mat.Mw,Tv=mat.Tv)
    if not math.isfinite(beta_recoil) or not 0 <= beta_recoil <= 1:
        raise ValueError("condensation fraction must be in [0,1]")
    c=mat.Lv*mat.Mw/(GAS_CONSTANT*mat.Tv)
    denominator=1-math.log(2/(1+beta_recoil))/c
    if denominator <= 0:
        raise ValueError("no finite positive recoil-temperature threshold")
    return mat.Tv/denominator


def piston_threshold_sensitivity(mat: Material,v: float,d: float) -> float:
    """Fabbro2018 p032410-2 Eq2 geometric R~1 threshold, not initial onset.

    u=20.7,nu=.7 are explicitly the source's strip geometry example only.
    Gan SI Table1 provides Lm and liquid cp; solid cp is fixed at T0.
    Transferring these strip constants is a declared synthetic sensitivity.
    Return a power diagnostic only: Eq2 supplies no geometric cavity e(P)
    law here. Do not use this power as the e=0 offset in solve_e, include it
    in an inception depth envelope, or count it as an inception-support vote.
    """
    _positive(v=v,d=d,Lm=mat.Lm,cp_liquid=mat.cp_liquid)
    Pe=v*d/(2*mat.alpha)
    hs=mat.rho*mat.cp*(mat.Tm-mat.T0)
    hm=mat.rho*(mat.cp*(mat.Tm-mat.T0)+mat.Lm
                +mat.cp_liquid*(mat.Tv-mat.Tm)/2)
    return math.pi/4*v*d*d*(hm+hs*20.7*Pe**(-.7))/mat.A0


def flat_conduction_peak_per_watt(mat: Material, v: float, d: float) -> tuple[float,float]:
    """Derived steady moving Gaussian Neumann half-space kernel, constant K/cp.

    q(r)=2A0P exp(-2r**2/a**2)/(pi*a**2), a=d_D4sigma/2. Diffusion-time
    integration substitutes w=sqrt(8alpha*t/a**2). Surface temperature is
    proportional to P; a coarse peak grid then every local bounded maximum
    is refined. This is a declared derived kernel, not served-kernel parity
    or TrappEq3 (which evaluates a transient estimate at t=a/v).
    """
    _positive(v=v,d=d)
    a=d/2
    speed=v*a/(8*mat.alpha)
    factor=mat.A0/(math.sqrt(2)*math.pi**1.5*mat.K*a)
    def kernel(eta):
        integral=quad(lambda w: 2/(1+w*w)*math.exp(
            -2*(eta+speed*w*w)**2/(1+w*w)),0,math.inf,
            epsabs=1e-10,epsrel=1e-10,limit=200)[0]
        return factor*integral
    xs=np.linspace(-4.,0.,65)
    vals=[kernel(x) for x in xs]
    candidates=[(vals[0],xs[0]),(vals[-1],xs[-1])]
    for i in range(1,len(xs)-1):
        if vals[i]>=vals[i-1] and vals[i]>=vals[i+1]:
            fit=minimize_scalar(lambda eta:-kernel(eta),bounds=(xs[i-1],xs[i+1]),
                                method="bounded",options={"xatol":1e-10})
            if not fit.success:
                raise RuntimeError("surface peak refinement failed")
            candidates.append((-float(fit.fun),float(fit.x)))
    peak,eta=max(candidates)
    if eta in (-4.,0.) and eta == -4.:
        raise ValueError("surface peak outside synthetic search scope")
    return peak,eta


def onset_power(mat: Material,v: float,d: float,method: str="trapp2017") -> float:
    """Primary Trapp2017 Eq3 p346 dwell t=a/v Gaussian conduction estimate.

    The primary explicit source estimate is not an exact moving peak. The
    independently derived steady moving Gaussian peak is a sensitivity only.
    """
    _positive(v=v,d=d)
    if method=="trapp2017":
        a=d/2
        gain=math.sqrt(2)*mat.A0/(a*mat.K*math.pi**1.5)*math.atan(math.sqrt(8*mat.alpha/(v*a)))
    elif method=="gaussian_peak":
        gain=flat_conduction_peak_per_watt(mat,v,d)[0]
    else:
        raise ValueError("onset method must be trapp2017 or gaussian_peak")
    return (threshold_temperature(mat)-mat.T0)/gain


@dataclass(frozen=True)
class EnergyPartition:
    Q_surface: float
    Q_cavity: float
    chi: float
    Q_net: float
    photon_mismatch: float


def energy_partition(P: float,P_star: float,R: float,A0: float,
                     form: str="specular_cone",conductive_fraction: float=1.) -> EnergyPartition:
    """Fixed prescribed split; never calibrate chi.

    Active: Qs=A0*tail*P+A0*Pstar, Qc=Acav*inside*(P-Pstar), chi=Qc/(Qs+Qc).
    Inactive: ordinary flat A0P. Active allocation is Eq14-inspired effective
    closure, not exact incident photon balance: difference from A_totP is
    [A0-inside*Acav]*Pstar. GPM postprocessor conductive_fraction=.325,
    source-scoped .30/.35 sensitivity; loss is not applied again to e equation.
    q(s)=Qc/e is uniform (Fabbro2020 Sec2.1). Dirichlet-to-line transfer and
    missing convection/latent heat remain inferred. chi=1 pure-Fabbro sensitivity
    is explicit and does not replace this primary partition.
    """
    _nonnegative(P=P,P_star=P_star,R=R)
    A_R(0.,A0,form)  # Validate the optical input even below inception.
    if not 0<conductive_fraction<=1:
        raise ValueError("conductive fraction must be in (0,1]")
    if P<=P_star:
        qs,qc=A0*P,0.
        mismatch=0.
    else:
        ac=A_R(R,A0,form)
        qs=A0*OUTSIDE*P+A0*P_star
        qc=ac*INSIDE*(P-P_star)
        mismatch=(A0-INSIDE*ac)*P_star
    q=qs+qc
    return EnergyPartition(qs,qc,qc/q if q>0 else 0.,conductive_fraction*q,mismatch)


def melt_observables(solution: CavitySolution,partition: EnergyPartition,
                     v: float,mat: Material) -> tuple[float,float]:
    """Parameter-free D(e),W from prescribed split; MELT-only later scoring.

    No chi calibration. Synthetic checks do not licence depth/width validation.
    """
    args=(partition.Q_net,v,mat.K,mat.Tm-mat.T0,mat.alpha)
    return (melt_depth_from_e(solution.selected_e_m,*args,chi=partition.chi),
            melt_surface_width_from_e(solution.selected_e_m,*args,chi=partition.chi))


def _direct_ray_count(radius: float,R: float) -> int:
    """Independent launch-space arithmetic trace used only as synthetic cross-check."""
    x,z,dx,dz,side=radius,R,0.,-1.,1.
    count=0
    for _ in range(10000):
        slope=side/(2*R)
        den=dx-slope*dz
        if abs(den)<1e-14:
            return count
        tau=(slope*z-x)/den
        zh=z+tau*dz
        if tau<=1e-13 or not 0<=zh<=R*(1+1e-12):
            return count
        x,z=x+tau*dx,zh
        # Reflect across a wall using its unnormalized line vector.
        proj=(dx*slope+dz)/(1+slope*slope)
        dx,dz=2*proj*slope-dx,2*proj-dz
        count+=1
        side=-side
    raise RuntimeError("direct trace did not exit")
