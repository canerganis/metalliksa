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


def _kernel_onset_power(mat: Material,v: float,d: float,method: str="trapp2017") -> float:
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










from scipy.special import i0e
from scipy.optimize import brentq
import copy
import lpbf_research_manifest as provenance_data
import lpbf_research_codes as codes
RG = GAS_CONSTANT
SB = 5.670374419e-8

SPEC = 'docs/research/SPEC_p8_research_arm_2026-10-14.md'
METHOD_SETTINGS = dict(rootScans=[1025, 2049], harmonics=[24, 32],
                       gaussianOrders=[512, 1024], gaussianSamples=[65, 129],
                       lineOrders=[32, 64], lineSamples=[65, 129],
                       depthAtol_m=1e-14, depthRtol=1e-11, floorExtractorId='p8-gaussian-liquidus-envelope-v2')
MODEL_IDS = dict(keyholeCavity='p8-cavity-served-kernel-v2', meltDepthLink='p8-melt-link-s2-hypothesis-v2',
                 marangoni='p8-marangoni-diagnostic-v1', surfaceBalance='p8-flat-hkl-balance-v1',
                 alSi10MgIndexDisclosure='p8-alsi-index-disclosure-v1',
                 alSi10MgVapourMgAware='p8-alsi-vapour-mg-sensitivity-v1', unavailablePhysics='p8-unavailable-closures-v1')


def belton_slope(mode, ppm, temperature):
    k, dh, gamma = (.00318, -166200., 1.30e-5) if mode == 'fe-s-belton' else (.0138, -146300., 2.03e-5)
    b = k * (ppm/10000.) * math.exp(-dh/(GAS_CONSTANT*temperature))
    return -.00043 - GAS_CONSTANT*gamma*math.log1p(b) - gamma*(dh/temperature)*b/(1+b)
NON_SURFACE_VALIDATION = "Not experimentally validated; research diagnostic/model only."
SURFACE_VALIDATION = ("Falsified flat non-receding HKL closure against an open IN625 mass-loss test; "
                      "numeric closure artefacts only, no physical prediction or blind-validation pass.")

def gaussian_gain(v, d, k, alpha, x=0, tolerance=2e-10, z=0):
    """K/W; P6 Eq2, tan substitution, Gaussian radius d/2."""
    r = d/2
    def kernel(theta):
        u2 = math.tan(theta)**2
        return math.exp(-2*(x/r + v*r/(8*alpha)*u2)**2/(1+u2)-2*(z/r)**2/u2)
    return math.sqrt(2)/(math.pi**1.5*k*r)*quad(
        kernel, 0, math.pi/2, epsabs=1e-12, epsrel=tolerance, limit=240)[0]


def surface(s):
    """P6 beam-centre flat balance; this is a peak proxy, not spatial peak."""
    q = 2*s["A"]*s["P"]/(math.pi*(s["d"]/2)**2)
    tg = s["T0"] + s["A"]*s["P"]*gaussian_gain(s["v"], s["d"], s["K"], s["alpha"])
    h = 2/(math.pi*(s['d']/2)**2*gaussian_gain(s['v'],s['d'],s['K'],s['alpha']))
    if s['P'] == 0:
        return dict(peakTemperatureProxy_K=s['T0'], lossFreeCenterTemperature_K=s['T0'],
                    absorbedCenterFlux_W_m2=0., conductiveAdmittance_W_m2K=h,
                    monotonicDerivative_W_m2K=h, evaporationMassFlux_kg_m2_s=0.,
                    evaporationEnergyFlux_W_m2=0., recoilPressure_Pa=0., saturationPressure_Pa=0.,
                    conductionFlux_W_m2=0., radiationFlux_W_m2=0., energyResidualRelative=0.,
                    effectiveAccommodation=s['accommodation']*s['effectiveNetFactor'],
                    effectiveNetFactor=s['effectiveNetFactor'], evaporationAccommodation=s['accommodation'],
                    surfaceGainRefinementRelative=0., iterations=0)
    b = s["Lv"]*s["M"]/RG
    def terms(t):
        ps = 101325*math.exp(b*(1/s["Tv"]-1/t))
        j = s["accommodation"]*s["effectiveNetFactor"]*ps*math.sqrt(s["M"]/(2*math.pi*RG*t))
        return h*(t-s["T0"]), s["Lv"]*j, s["emissivity"]*SB*(t**4-s["T0"]**4), j, s["recoil"]*ps
    lo, hi = s["T0"], min(tg, .999*2*b)
    residual = lambda t: sum(terms(t)[:3])-q
    if residual(lo)>0 or residual(hi)<0:
        raise ValueError("SURFACE_BALANCE_NO_BRACKET")
    for _ in range(100):
        t = (lo+hi)/2
        f = residual(t)
        if abs(f) <= q*1e-10:
            break
        if f>0:
            hi=t
        else:
            lo=t
    else:
        raise ValueError("SURFACE_BALANCE_CONVERGENCE_FAILED")
    c, e, radiation, j, recoil = terms(t)
    derivative=h+e*(b/t**2-1/(2*t))+4*s["emissivity"]*SB*t**3
    assert h>0 and derivative>0
    refined=gaussian_gain(s["v"],s["d"],s["K"],s["alpha"],tolerance=1e-12)
    gain=gaussian_gain(s["v"],s["d"],s["K"],s["alpha"])
    difference=abs(refined-gain)/refined
    assert difference<=1e-8
    return {"peakTemperatureProxy_K": t, "evaporationMassFlux_kg_m2_s": j,
            "recoilPressure_Pa": recoil, "lossFreeCenterTemperature_K": tg,
            "absorbedCenterFlux_W_m2":q,"conductiveAdmittance_W_m2K":h,
            "monotonicDerivative_W_m2K":derivative,"surfaceGainRefinementRelative":difference,
            "evaporationEnergyFlux_W_m2":e,"conductionFlux_W_m2":c,"radiationFlux_W_m2":radiation,
            "effectiveAccommodation":s["accommodation"]*s["effectiveNetFactor"],
            "effectiveNetFactor":s["effectiveNetFactor"],"evaporationAccommodation":s["accommodation"],
            "energyResidualRelative": (c+e+radiation-q)/q, "iterations": _+1,
            "saturationPressure_Pa":101325*math.exp(b*(1/s['Tv']-1/t))}


def marangoni(s):
    alpha = s["kl"]/(s["rhol"]*s["cpl"])
    ma = -s["slope"]*s["L"]*s["deltaT"]/(s["mu"]*alpha)
    u = (abs(s["slope"])*s["deltaT"]/math.sqrt(s["rhol"]*s["mu"]*s["L"]))**(2/3)
    return {"marangoniNumber": ma, "surfaceVelocityScale_m_s": u,
            "liquidPecletScale": u*s["L"]/alpha,
            "surfaceTensionSlope_N_mK":s["slope"],"viscosity_Pa_s":s["mu"],
            "deltaTemperature_K":s["deltaT"],"length_m":s["L"],
            "flowDirection":("outward" if s["slope"]<0 else "inward")
                if s["slope"]!=0 and s["deltaT"]>0 else "none"}


def gaussian_floor(s, order=512, samples=65):
    """Independent finite-Gaussian liquidus envelope, no served extent helpers.

    y=0 maximizes every positive time-kernel term; x>0 decreases every term.
    A stationary Gaussian surface profile bounds the moving field at every x,
    hence its i0e tail provides a deterministic rear exclusion boundary. The
    stationary point-power bound Q/(2*pi*K*z) gives a deterministic depth cap.
    Refine every local x maximum continuously, then bisect its depth crossing.
    Grid/quadrature doubling checks numerical completeness, not experimental
    validity or a proof that a grid contains every extremum.
    """
    q=s["A"]*s["P"];a=s["d"]/2;dt=s["Tl"]-s["T0"]
    if q==0:
        return dict(depth_m=0.,peakX_m=0.,status="no-melting",rearBound_m=0.)
    stationary=q/(math.sqrt(2*math.pi)*s["K"]*a)
    if stationary<=dt:
        return dict(depth_m=0.,peakX_m=0.,status="no-melting",rearBound_m=0.)
    left=-2*a
    while stationary*float(i0e((left/a)**2))>=dt:
        left*=2
    nodes,weights=np.polynomial.legendre.leggauss(order)
    theta=(nodes+1)*math.pi/4;weights=weights*math.pi/4
    u2=np.tan(theta)**2;speed=s["v"]*a/(8*s["alpha"])
    pref=q*math.sqrt(2)/(math.pi**1.5*s["K"]*a)
    def peak(z):
        def field(xs):
            xs=np.asarray(xs)
            exponent=-2*(xs[...,None]/a+speed*u2)**2/(1+u2)-2*(z/a)**2/u2
            return pref*(np.exp(exponent)@weights)
        xs=np.linspace(left,0,samples);ys=field(xs)
        candidates=[(float(ys[0]),left),(float(ys[-1]),0.)]
        for i in range(1,samples-1):
            if ys[i]>=ys[i-1] and ys[i]>=ys[i+1]:
                opt=minimize_scalar(lambda x:-float(field(x)),bounds=(xs[i-1],xs[i+1]),
                    method="bounded",options={"xatol":1e-13,"maxiter":100})
                assert opt.success
                candidates.append((-float(opt.fun),float(opt.x)))
        return max(candidates)
    surface_peak=peak(0)
    if surface_peak[0]<=dt:
        return dict(depth_m=0.,peakX_m=surface_peak[1],status="no-melting",rearBound_m=left)
    lo=0.;hi=q/(2*math.pi*s["K"]*dt)
    assert peak(hi)[0]<dt
    for _ in range(80):
        mid=(lo+hi)/2
        if peak(mid)[0]>=dt:lo=mid
        else:hi=mid
        if hi-lo<=1e-13:break
    else:raise RuntimeError("Gaussian envelope depth bisection failed")
    depth=(lo+hi)/2
    return dict(depth_m=depth,peakX_m=peak(depth)[1],status="computed",rearBound_m=left)


def material(s):
    return Material("synthetic",s["K"],s["rho"],s["cp"],s["Tl"],s["Tv"],s["A"],
                           s["Lv"],s["M"],s["Lm"],s["cpl"],s["T0"])


def onset_power(s):
    mat=material(s);method=s["onsetMethod"]
    if method=="O2":
        raise ValueError("GEOMETRIC_THRESHOLD_NOT_INCEPTION")
    if method=="O3":return _kernel_onset_power(mat,s["v"],s["d"],method="gaussian_peak")
    onset=_kernel_onset_power(mat,s["v"],s["d"])
    if method=="O1":onset*=2*(s["Tv"]-s["T0"])/(threshold_temperature(mat)-s["T0"])
    return onset


def evaluate_reference(s):
    onset=onset_power(s)
    solution=solve_e(s["P"],s["v"],s["d"],s["K"],s["Tv"]-s["T0"],s["alpha"],s["A"],
                           closure="cylinder_exact",P_star=onset)
    e=solution.selected_e_m;ac=specular_cone(e/s["d"],s["A"])
    w=1-math.exp(-2);p=1-w
    if s["P"]<=onset:qs=s["A"]*s["P"];qc=0.
    else:
        qs=s["A"]*(p*s["P"]+w*onset)
        qc=w*(ac*s["P"]-s["A"]*onset)
    qabs=qs+qc;chi=qc/qabs if qabs else 0.
    photons=qabs-total_absorptance(e/s["d"],s["A"])*s["P"]
    assert abs(photons)<=1e-10*max(1.,qabs)
    floor0=gaussian_floor(s);floor=gaussian_floor(s,1024,129)
    floor_difference=abs(floor["depth_m"]-floor0["depth_m"])
    assert floor_difference<=max(2e-11,1e-6*floor["depth_m"])
    if s["P"]<=onset:
        depths=[floor0["depth_m"],floor["depth_m"]];dispatch="gaussian-below-onset"
    else:
        depths=[melt_depth_from_e(e,qabs,s["v"],s["K"],s["Tl"]-s["T0"],s["alpha"],
                  chi=chi,observable="envelope",order=n,x_samples=m) for n,m in [(32,65),(64,129)]]
        dispatch="conditional-line-above-onset"
    depth_difference=abs(depths[1]-depths[0])/max(depths[1],1e-12)
    assert depth_difference<=.01
    g24=thermal_g(solution.Pe,"cylinder_exact");lam=solution.Pe/2
    g32=-2*math.pi*lam*math.fsum([float(iv(0,lam)**2*kvp(0,lam)/kv(0,lam))]+
             [2*(-1)**n*float(iv(n,lam)**2*kvp(n,lam)/kv(n,lam)) for n in range(1,33)])
    gdiff=abs(g32-g24)/abs(g32);assert gdiff<=1e-8
    roots=[]
    for root in solution.roots if s["P"]>onset else []:
        residual=energy_balance_residual(root.e_m,s["P"],s["v"],s["d"],s["K"],
                       s["Tv"]-s["T0"],s["alpha"],s["A"],closure="cylinder_exact",P_star=onset)
        assert abs(residual)<=max(1e-6,1e-8*max(1.,qabs))
        roots.append(dict(R=root.R,depth_um=root.e_m*1e6,scalarRelaxation=root.stability,
                          cavityEnergyResidual_W=residual,selected=bool(root.e_m==e)))
    stable=[r for r in solution.roots if r.stability=="stable"]
    assert stable and e==min(r.e_m for r in stable)
    wall=s["K"]*(s["Tv"]-s["T0"])*g24*e
    return dict(peclet=solution.Pe,powerOverOnset=s["P"]/onset,onsetPower_W=onset,
                cavityDepth_um=e*1e6,conditionalMeltDepth_um=depths[1]*1e6,
                conductionDepth_um=floor["depth_m"]*1e6,linkedMeltDepth_um=max(depths[1],floor["depth_m"])*1e6,
                surfacePower_W=qs,cavityPower_W=qc,absorbedPower_W=qabs,lineFraction=chi,
                cavityLedgerRatio=qc/wall if wall>0 else None,
                photonResidual_W=photons,cylinderHarmonicDifference=gdiff,
                meltDepthRefinementRelative=depth_difference,meltDepthCoarse_m=depths[0],meltDepthRefined_m=depths[1],
                conductionRefinement_m=floor_difference,
                conductionPeakX_m=floor["peakX_m"],conductionRearBound_m=floor["rearBound_m"],
                conductionStatus=floor["status"],linkDispatch=dispatch,
                controllingLeg="conduction" if s["P"]<=onset else
                    ("equal" if depths[1]==floor["depth_m"] else
                     "conditional-link" if depths[1]>floor["depth_m"] else "conduction"),
                rootCount=len(roots),roots=roots,rootTopologyStatus="computed" if s["P"]>onset else "NOT_APPLICABLE",
                selectedBranch="lowest-strictly-stable" if s["P"]>onset else None,
                modeledAboveOnset=s["P"]>onset,**marangoni(s),**surface(s))




def consistency_status(module, *, above_onset=True, peclet=3., aspect=1.,
                       source_transfer=False, hard_failure=False):
    """Availability is independent; inRange never implies experimental validity."""
    if hard_failure or module == "surfaceBalance":
        return "outOfRange"
    if source_transfer or (module in {"cavity","meltDepthLink"} and
                           (peclet < 2 or (above_onset and aspect < .5))):
        return "extrapolated"
    return "inRange"


def input_scope_reasons(module, provenance):
    """Classify actual coefficient/source scopes without borrowing another arm."""
    reasons=[]
    for key in provenance_data.PHYSICAL_INPUTS[module]:
        record=provenance[key]
        if record["sourceEvidenceKind"]=="Unresolved":reasons.append(key+": physical scope not established")
        scope=record["scope"].lower()
        if record["kind"]=="alloyTransfer" or "transferred" in scope or "molten-wall" in scope:
            reasons.append(key+": source/material-state transfer")
        temperature=record["referenceTemperature_K"];limits=record["sourceRange_K"]
        if temperature is not None and limits is not None and not limits[0]<=temperature<=limits[1]:
            reasons.append(key+": reference temperature outside source range")
    return reasons


def field_shape_policy(ratio, floor, excess, shape):
    """Declared disclosure convention; no experimental threshold inference."""
    resolution = max(2e-5, 1e-6 * abs(floor))  # um; Gaussian refinement bound
    share = shape / excess if ratio > 1 and excess > resolution else None
    below_near = .999 <= ratio <= 1.
    dominant = share is not None and shape > resolution and share >= .5
    return dict(nearOnset=bool(below_near or dominant), fieldShapeShare=share,
                excessResolution_um=resolution,
                nearOnsetTrigger="below-or-at-onset-0.1-percent" if below_near else
                    "field-shape-share-at-least-half" if dominant else None)


def field_shape_diagnostic(s, output):
    """Same-absorbed-power point counterfactual; not an alternate prediction."""
    if not output["modeledAboveOnset"]:
        return dict(applicable=False, reason="Gaussian dispatch at or below inception",
                    **field_shape_policy(output["powerOverOnset"], output["conductionDepth_um"], 0., 0.))
    point = melt_depth_from_e(0.,output["absorbedPower_W"],s["v"],s["K"],
        s["Tl"]-s["T0"],s["alpha"],chi=0.,observable="envelope",order=64,x_samples=129)*1e6
    excess = output["conditionalMeltDepth_um"]-output["conductionDepth_um"]
    shape = point-output["conductionDepth_um"]
    return dict(applicable=True,samePowerPointDepth_um=point,fieldShapeExcess_um=shape,
        conditionalExcessOverGaussian_um=excess,
        **field_shape_policy(output["powerOverOnset"], output["conductionDepth_um"], excess, shape),
        caveat="Counterfactual decomposition at the same absorbed power; no physical validation.")


def independent_point_depth(s, power):
    """Stationary-x condition of Q exp[-beta(x+r)]/(2 pi K r).

    Set u=-x/r, r=u/(beta(1-u)), then solve beta L(1-u) exp(-u)/u=1.
    This uses neither the conditional-field optimizer nor its depth bisection.
    """
    beta=s["v"]/(2*s["alpha"])
    length=s["A"]*power/(2*math.pi*s["K"]*(s["Tl"]-s["T0"]))
    u=brentq(lambda value:beta*length*(1-value)*math.exp(-value)-value,
             0.,1.,xtol=1e-14)
    radius=u/(beta*(1-u))
    return radius*math.sqrt(1-u*u)*1e6


def value_provenance(module, values, inputs):
    """Determine support from actual physical dependencies, separately from validity."""
    echoes={"surfaceTensionSlope_N_mK":"slope","viscosity_Pa_s":"mu",
            "deltaTemperature_K":"deltaT","length_m":"L",
            "effectiveNetFactor":"effectiveNetFactor","evaporationAccommodation":"accommodation"}
    conventions={"selectedBranch","rootTopologyStatus","modeledAboveOnset","flowDirection",
                 "conductionStatus","linkDispatch","controllingLeg","roots"}
    thermal=("K","cp","rho")
    inception=thermal+("A","Tv","Lv","M")
    floor=thermal+("A","Tl")
    records={}
    for key in values:
        dependencies=provenance_data.PHYSICAL_INPUTS[module]
        if key in echoes:dependencies=(echoes[key],)
        elif key=="peclet":dependencies=thermal
        elif module=="cavity":dependencies=inception
        elif module=="meltDepthLink":
            dependencies=(floor if key.startswith("conduction") else inception if key in {
                "surfacePower_W","cavityPower_W","absorbedPower_W","lineFraction",
                "cavityLedgerRatio","photonResidual_W"} else inception+("Tl",))
        elif module=="marangoni" and key=="surfaceVelocityScale_m_s":
            dependencies=("slope","deltaT","rhol","mu","L")
        elif module=="surfaceBalance":
            dependencies=tuple(k for k in dependencies if k!="recoil")
            if key=="recoilPressure_Pa":dependencies=dependencies+("recoil",)
            if key=="effectiveAccommodation":dependencies=("accommodation","effectiveNetFactor")
            if key=="absorbedCenterFlux_W_m2":dependencies=("A",)
            if key in {"conductiveAdmittance_W_m2K","surfaceGainRefinementRelative"}:dependencies=thermal
            if key=="lossFreeCenterTemperature_K":dependencies=thermal+("A",)
        if key in conventions:
            records[key]=dict(sourceEvidenceKind=None,dependsOn=[],weakestInputs=[])
        else:
            evidence,weak=provenance_data.evidence_kind(inputs,dependencies)
            records[key]=dict(sourceEvidenceKind=evidence,dependsOn=list(dependencies),weakestInputs=weak)
    return records


R_GAS = 8.31446261815324  # SI molar gas constant, J/(mol K).
ELEMENTS = {
    # M: CIAAW aluminium page (full value), 2024 abridged table for others.
    # Tb/H: Mondal et al., Materials 16 (2023) 50, Table 1, PDF/printed p.3.
    "Al": {"M_kg_mol": 0.0269815384, "Tb_K": 2743.0, "H_J_mol": 284000.0},
    "Si": {"M_kg_mol": 0.028085, "Tb_K": 3533.0, "H_J_mol": 383000.0},
    "Mg": {"M_kg_mol": 0.024305, "Tb_K": 1383.0, "H_J_mol": 132000.0},
    "Fe": {"M_kg_mol": 0.055845, "Tb_K": 3134.0, "H_J_mol": 354000.0},
}
# Mondal Eq.2 p.4, Table 2 p.7: log10(p/atm)=-A/T+B+C log10(T)+1e-3 D T.
# The Mg polynomial is NOT extrapolated. Its fit ends at 1730 K.
FITS = {
    "Al": {"coefficients": [12210.0, -27.06, 10.09, -1.16], "range_K": [1200.0, 3370.0]},
    "Si": {"coefficients": [17250.0, -15.97, 6.403, -0.5281], "range_K": [1700.0, 4300.0]},
    "Fe": {"coefficients": [27180.0, 50.1, -12.62, 0.8586], "range_K": [1400.0, 3775.0]},
}
MG_FIT_RANGE_K = [600.0, 1730.0]
COMPOSITION_WT_PCT = {"Al": 89.67, "Si": 9.75, "Mg": 0.44, "Fe": 0.14}


def composition(mg_wt_pct: float) -> dict[str, float]:
    """Synthetic Mg sensitivity; Si/Fe fixed, Al balances to 100 mass percent."""
    if not math.isfinite(mg_wt_pct) or not 0 <= mg_wt_pct <= 0.45:
        raise ValueError("Mg must be finite and inside [0, 0.45] mass percent")
    return {"Al": 100.0 - 9.75 - 0.14 - mg_wt_pct,
            "Si": 9.75, "Mg": mg_wt_pct, "Fe": 0.14}


def mole_fractions(weights: dict[str, float]) -> dict[str, float]:
    if set(weights) != set(ELEMENTS) or any(not math.isfinite(w) or w < 0 for w in weights.values()):
        raise ValueError("four finite nonnegative constituent mass percentages required")
    if abs(sum(weights.values()) - 100.0) > 1e-10:
        raise ValueError("composition must sum to 100 mass percent")
    moles = {s: w / ELEMENTS[s]["M_kg_mol"] for s, w in weights.items()}
    total = sum(moles.values())
    return {s: n / total for s, n in moles.items()}


def pressure_atm(symbol: str, temperature_K: float, route: str,
                 mg_boiling_temperature_K: float = 1383.0) -> float:
    if not math.isfinite(temperature_K) or temperature_K <= 0:
        raise ValueError("temperature must be finite and positive")
    if route not in ("hybrid", "cc"):
        raise ValueError("unknown elemental pressure route")
    if mg_boiling_temperature_K not in (1363.0, 1383.0):
        raise ValueError("Mg boiling temperature must select the recorded 1363 or 1383 K scenario")
    if route == "hybrid" and symbol in FITS:
        fit = FITS[symbol]
        if not fit["range_K"][0] <= temperature_K <= fit["range_K"][1]:
            raise ValueError("elemental fit outside declared temperature range")
        a, b, c, d = fit["coefficients"]
        return 10 ** (-a / temperature_K + b + c * math.log10(temperature_K)
                      + 1e-3 * d * temperature_K)
    element = ELEMENTS[symbol]
    # Mondal Eq.1 p.2, constant-H ideal-gas Clausius-Clapeyron.
    boiling_temperature = mg_boiling_temperature_K if symbol == "Mg" else element["Tb_K"]
    return math.exp(element["H_J_mol"] / R_GAS
                    * (1 / boiling_temperature - 1 / temperature_K))


def fit_enthalpy_J_mol(symbol: str, temperature_K: float, route: str) -> float:
    """R T^2 d ln(p)/dT; local derivative, not measured latent heat."""
    if route == "hybrid" and symbol in FITS:
        a, _, c, d = FITS[symbol]["coefficients"]
        return R_GAS * (math.log(10) * a + c * temperature_K
                        + math.log(10) * 1e-3 * d * temperature_K ** 2)
    return ELEMENTS[symbol]["H_J_mol"]


def vapour_constants(weights: dict[str, float], route: str = "hybrid",
                     mg_activity_factor: float = 1.0,
                     mg_boiling_temperature_K: float = 1383.0) -> dict:
    if not math.isfinite(mg_activity_factor) or mg_activity_factor <= 0:
        raise ValueError("positive finite Mg activity factor required")
    xs = mole_fractions(weights)

    def partials(t):
        return {s: xs[s] * pressure_atm(s, t, route, mg_boiling_temperature_K)
                * (mg_activity_factor if s == "Mg" else 1.0) for s in xs}

    lo, hi = 1800.0, 3000.0
    if not sum(partials(lo).values()) < 1 < sum(partials(hi).values()):
        raise ValueError("one-atmosphere mixture root not bracketed")
    for _ in range(80):
        if hi - lo <= 1e-9:
            break
        mid = (lo + hi) / 2
        if sum(partials(mid).values()) < 1:
            lo = mid
        else:
            hi = mid
    else:
        raise RuntimeError("boiling-root bisection did not converge")
    t = (lo + hi) / 2
    ps = partials(t)
    total = sum(ps.values())
    ys = {s: p / total for s, p in ps.items()}
    mass = sum(ys[s] * ELEMENTS[s]["M_kg_mol"] for s in ys)
    h_cc = sum(ys[s] * ELEMENTS[s]["H_J_mol"] for s in ys)
    h_local = sum(ys[s] * fit_enthalpy_J_mol(s, t, route) for s in ys)
    mg_pressure = pressure_atm("Mg", t, route, mg_boiling_temperature_K)
    return {
        "composition_wt_pct": weights, "liquid_mole_fractions": xs,
        "pressure_route": route, "mg_activity_factor": mg_activity_factor,
        "T_v_K": t, "mixture_pressure_atm": total,
        "root_pressure_residual_atm": abs(total - 1.0),
        "partial_pressures_atm": ps, "vapour_mole_fractions": ys,
        "M_vapour_kg_mol": mass,
        "H_table_weighted_J_mol": h_cc, "L_table_weighted_J_kg": h_cc / mass,
        "H_local_slope_J_mol": h_local, "L_local_slope_J_kg": h_local / mass,
        "mg_pure_pressure_atm": mg_pressure,
        "mg_above_fitted_temperature_range": t > MG_FIT_RANGE_K[1],
        "mg_above_mondal_synthesized_pressure_limit": mg_pressure > 10.0,
    }


def cavity_values(s):
    onset = onset_power(s)
    solution = solve_e(s['P'], s['v'], s['d'], s['K'], s['Tv']-s['T0'], s['alpha'], s['A'],
                       closure='cylinder_exact', P_star=onset)
    e = solution.selected_e_m; r = e/s['d']; g = thermal_g(solution.Pe, 'cylinder_exact'); lam=solution.Pe/2
    g32 = -2*math.pi*lam*math.fsum([float(iv(0,lam)**2*kvp(0,lam)/kv(0,lam))] +
              [2*(-1)**n*float(iv(n,lam)**2*kvp(n,lam)/kv(n,lam)) for n in range(1,33)])
    difference=abs(g32-g)/abs(g32)
    if difference>1e-8:raise ValueError('CYLINDER_CONVERGENCE_FAILED')
    roots=[]; scan_difference=None; residual=0.
    if s['P']>onset:
        for root in solution.roots:
            rr=energy_balance_residual(root.e_m,s['P'],s['v'],s['d'],s['K'],s['Tv']-s['T0'],s['alpha'],s['A'],closure='cylinder_exact',P_star=onset)
            if abs(rr)>max(1e-6,1e-8*max(1.,total_absorptance(r,s['A'])*s['P'])):
                raise ValueError('CAVITY_RESIDUAL_FAILED')
            roots.append(dict(depth_um=root.e_m*1e6,aspectRatio_e_over_d=root.R,scalarRelaxation=root.stability,
                              cavityEnergyResidual_W=rr,selected=bool(root.e_m==e)))
            if root.e_m==e:residual=rr
        coarse=_scan_roots(solution.S,s['A'],'specular_cone',1025)
        scan_difference=max(abs(a.R-b.R)/max(1.,abs(b.R)) for a,b in zip(coarse,solution.roots))
    return dict(peclet=solution.Pe,thermalResponse_g=g,thresholdTemperature_K=threshold_temperature(material(s)),
                onsetPower_W=onset,powerOverOnset=s['P']/onset,modeledAboveOnset=s['P']>onset,
                cavityDepth_um=e*1e6,aspectRatio_e_over_d=r,cavityAbsorptance=specular_cone(r,s['A']),
                totalAbsorptance=total_absorptance(r,s['A']),energyResidual_W=residual,rootCount=len(roots),roots=roots,
                rootTopologyStatus='computed' if s['P']>onset else 'NOT_APPLICABLE',
                selectedBranch='lowest-strictly-stable' if s['P']>onset else None,
                rootScanRelativeDifference=scan_difference,cylinderHarmonicDifference=difference)


def link_values(s, cavity):
    """Independent legs: a failed Gaussian does not erase a resolved line envelope."""
    onset=cavity['onsetPower_W'];e=cavity['cavityDepth_um']*1e-6;ac=cavity['cavityAbsorptance']
    qs=s['A']*s['P'] if s['P']<=onset else s['A']*(OUTSIDE*s['P']+INSIDE*onset)
    qc=0. if s['P']<=onset else INSIDE*(ac*s['P']-s['A']*onset)
    qabs=qs+qc;chi=qc/qabs if qabs else 0.;wall=s['K']*(s['Tv']-s['T0'])*cavity['thermalResponse_g']*e
    values=dict(cavityDepth_um=cavity['cavityDepth_um'],surfacePower_W=qs,cavityPower_W=qc,absorbedPower_W=qabs,
                depositedThermalPower_W=qabs,unresolvedPower_W=0.,cavityPowerFraction=chi,wallConductionPower_W=wall,
                cavityLedgerRatio=qc/wall if wall>0 else None,lossMultiplier=1.,
                photonResidual_W=qabs-cavity['totalAbsorptance']*s['P'],quadratureOrder=64,xSamples=129,
                observable='deepest-below-original-datum-liquidus-envelope',floorFieldModelId='eagar-tsai-v2',
                floorExtractorId='p8-gaussian-liquidus-envelope-v2',linkDispatch='gaussian-below-onset' if s['P']<=onset else 'conditional-line-above-onset')
    failures={}
    if wall<=0:failures['cavityLedgerRatio']='NOT_APPLICABLE_BELOW_ONSET'
    try:
        if s['K']<1e-6 or s['alpha']<1e-12 or s['d']/2<1e-7 or s['v']<1e-6:
            raise ValueError('NUMERICAL_INPUT_BELOW_FLOOR')
        coarse=gaussian_floor(s);fine=gaussian_floor(s,1024,129)
        fdiff=abs(fine['depth_m']-coarse['depth_m'])
        if fdiff>max(2e-11,1e-6*fine['depth_m']):raise ValueError('CONDUCTION_EXTENT_UNRESOLVED')
        values.update(conductionDepth_um=fine['depth_m']*1e6,conductionStatus=fine['status'],conductionRefinement_m=fdiff,
                      conductionPeakX_m=fine['peakX_m'],conductionRearBound_m=fine['rearBound_m'])
    except (ValueError,RuntimeError,AssertionError) as exc:
        code=str(exc) if str(exc) in codes.REASON_CODES else 'CONDUCTION_EXTENT_UNRESOLVED'
        for key in ('conductionDepth_um','conductionStatus','conductionRefinement_m','conductionPeakX_m','conductionRearBound_m'):
            values[key]=None;failures[key]=code
    if s['P']<=onset:
        values.update(conditionalMeltDepth_um=values['conductionDepth_um'],linkedMeltDepth_um=values['conductionDepth_um'],
                      controllingLeg='conduction' if values['conductionDepth_um'] is not None else None,
                      meltDepthCoarse_m=coarse['depth_m'] if values['conductionDepth_um'] is not None else None,
                      meltDepthRefined_m=fine['depth_m'] if values['conductionDepth_um'] is not None else None)
        values['relativeConvergenceDifference']=(abs(fine['depth_m']-coarse['depth_m'])/max(fine['depth_m'],1e-12)
                                                 if values['conductionDepth_um'] is not None else None)
        if values['conductionDepth_um'] is None:
            for k in ('conditionalMeltDepth_um','linkedMeltDepth_um','controllingLeg','meltDepthCoarse_m','meltDepthRefined_m','relativeConvergenceDifference'):
                failures[k]=failures['conductionDepth_um']
    else:
        try:
            depths=[melt_depth_from_e(e,qabs,s['v'],s['K'],s['Tl']-s['T0'],s['alpha'],chi=chi,observable='envelope',order=n,x_samples=m)
                    for n,m in ((32,65),(64,129))]
            difference=abs(depths[1]-depths[0])/max(depths[1],1e-12)
            if difference>.01:raise ValueError('MELT_CONVERGENCE_FAILED')
            floor=values['conductionDepth_um'];depth=depths[1]*1e6
            values.update(conditionalMeltDepth_um=depth,linkedMeltDepth_um=max(depth,floor) if floor is not None else None,
                          controllingLeg=None if floor is None else 'equal' if depth==floor else 'conditional-link' if depth>floor else 'conduction',
                          relativeConvergenceDifference=difference,meltDepthCoarse_m=depths[0],meltDepthRefined_m=depths[1])
            if floor is None:
                for key in ('linkedMeltDepth_um','controllingLeg'):failures[key]=failures['conductionDepth_um']
        except (ValueError,RuntimeError) as exc:
            text=str(exc)
            code=text if text in codes.REASON_CODES else ('TIP_SHELL_UNRESOLVED' if 'tip' in text else
                  'MELT_OPTIMIZER_FAILURE' if 'refinement' in text else 'MELT_BRACKET_FAILURE')
            for key in ('conditionalMeltDepth_um','linkedMeltDepth_um','controllingLeg','relativeConvergenceDifference','meltDepthCoarse_m','meltDepthRefined_m'):
                values[key]=None;failures[key]=code
    return values,failures


def field_shape_step(s):
    onset=onset_power(s);records=[]
    for side,factor in (('below',1-1e-9),('at',1.),('above',1+1e-9)):
        state={**s,'P':onset*factor}
        records.append(dict(side=side,powerFactor=factor,values=provenance_data.map_fixture_values(evaluate_reference(state))))
    at=records[1]['values']
    point=melt_depth_from_e(0.,s['A']*onset,s['v'],s['K'],s['Tl']-s['T0'],s['alpha'],chi=0.,observable='envelope',order=64,x_samples=129)*1e6
    independent=independent_point_depth(s,onset)
    return dict(onsetPower_W=onset,relativeBracket=1e-9,gaussianDepthAtOnset_um=at['conductionDepth_um'],
                pointDepthAtOnset_um=point,pointMinusGaussian_um=point-at['conductionDepth_um'],pointToGaussianRatio=point/at['conductionDepth_um'] if at['conductionDepth_um'] else None,
                pointDepthIndependentCheck_um=independent,pointDepthIndependentDifference_m=abs(independent-point)*1e-6,
                linkedDepthJustBelowOnset_um=records[0]['values']['linkedMeltDepth_um'],linkedDepthJustAboveOnset_um=records[2]['values']['linkedMeltDepth_um'],
                onsetSideRecords=records,aboveOnsetFieldChanged=False,cause='Finite Gaussian below/at onset versus singular surface-point limit above onset.')


def admission(context, s, module):
    if module in ('alSi10MgIndexDisclosure','alSi10MgVapourMgAware'):
        return None if context.alloyId=='alsi10mg' else 'ALLOY_NOT_ALSI10MG'
    if module not in ('keyholeCavity','meltDepthLink'):return None
    if context.alloyId not in ('ti6al4v','alsi10mg'):return 'ALLOY_CONSTANT_CHAIN_NOT_ADMITTED'
    if not context.tupleEqualsNominal:return 'UNSOURCED_PROPERTY_OVERRIDE'
    if context.laserWavelength!='IR_1064nm':return 'WAVELENGTH_UNSUPPORTED'
    if context.absorptionModel!='flat-plate':return 'POWDER_CONTEXT_UNSUPPORTED'
    if not 293.15<=s['T0']<=s['Tl']-50:return 'PREHEAT_OUTSIDE_PROPERTY_SCOPE'
    if any(s.get(k) is None or not math.isfinite(s[k]) for k in ('P','v','d','T0','Tl','K','cp','rho','alpha','A','Tv','Lv','M')):return 'INVALID_INPUT'
    if s['P']<0 or min(s['v'],s['d'],s['K'],s['cp'],s['rho'],s['alpha'])<=0 or not 0<s['A']<1 or s['Tl']<=s['T0'] or s['Tv']<=s['T0']:return 'INVALID_INPUT'
    pe=s['v']*s['d']/(2*s['alpha'])
    if not .01<=pe<=10:return 'PECLET_OUTSIDE_NUMERICAL_SCOPE'
    try:
        onset=onset_power(s)
        if onset<=0 or threshold_temperature(material(s))<=s['T0']:return 'ONSET_REFERENCE_UNAVAILABLE'
        g=thermal_g(pe,'cylinder_exact')
        bound=(INSIDE+OUTSIDE*s['A'])*max(s['P']-onset,0)/(s['d']*s['K']*(s['Tv']-s['T0'])*g)
        if bound>10:return 'ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE'
    except ValueError:return 'ONSET_REFERENCE_UNAVAILABLE'
    return None


def _source_support(module, key, state, provenance):
    fixture_module='cavity' if module=='keyholeCavity' else module
    reverse={v:k for k,v in provenance_data.FIXTURE_TO_RUNTIME.items()}
    original=reverse.get(key,key)
    if module=='meltDepthLink' and key in ('cavityDepth_um','depositedThermalPower_W','wallConductionPower_W'):
        original='absorbedPower_W'
    if fixture_module not in provenance_data.PHYSICAL_INPUTS:return dict(sourceEvidenceKind='Literature estimate',dependsOn=[],weakestInputs=[],labelSources=[SPEC+' section 6'])
    record=value_provenance(fixture_module,{original:0.},provenance)[original]
    # User coefficients are named, and request processes never enter this rule.
    dependencies=record['dependsOn']
    weak=[k for k in dependencies if provenance[k]['sourceEvidenceKind']=='Unresolved']
    users=[k for k in dependencies if provenance[k]['sourceEvidenceKind']=='User input']
    record['weakestInputs']=[provenance_data.INPUT_NAMES.get(k,k) for k in (weak or users)]
    record['dependsOn']=[provenance_data.INPUT_NAMES.get(k,k) for k in dependencies]
    record['labelSources']=list(dict.fromkeys(provenance[k]['sourceLocator'] for k in dependencies if provenance[k].get('sourceLocator')))
    return record


def _field(module, name, value, record=None, reason=None, *, role=None, surface=None):
    state=(record or {}).get('state',{});prov=(record or {}).get('provenance',{})
    support=dict(sourceEvidenceKind=None,dependsOn=[],weakestInputs=[],labelSources=[])
    key=next((k for k,v in provenance_data.INPUT_NAMES.items() if v==name),None)
    if role is None:
        role=('requestInput' if name in ('alloy','power_W','speed_m_s','beamDiameter_m','preheat_K') else
              'physicalInput' if key is not None else 'derived')
        if isinstance(value,(str,bool)) or name in ('rootCount','quadratureOrder','xSamples','iterations','onsetEvent'):
            role='convention'
    if role=='requestInput':support['sourceEvidenceKind']='User input'
    elif role=='physicalInput' and key in prov:
        p=prov[key];support.update(sourceEvidenceKind=p['sourceEvidenceKind'],dependsOn=[name],
            weakestInputs=[name] if p['sourceEvidenceKind'] in ('Unresolved','User input') else [],
            labelSources=[p['sourceLocator']] if p.get('sourceLocator') else [])
    elif role=='derived' and prov:
        if module=='alSi10MgVapourMgAware':
            weak=[k for k,p in prov.items() if p['sourceEvidenceKind']=='Unresolved']
            support=dict(sourceEvidenceKind='Unresolved' if weak else 'Literature estimate',
                         dependsOn=list(prov),weakestInputs=weak,labelSources=list(dict.fromkeys(p['sourceLocator'] for p in prov.values() if p['sourceLocator'])))
        else:support=_source_support('surfaceBalance' if surface else module,name,state,prov)
    status=SURFACE_VALIDATION if surface is True or surface is None and module=='surfaceBalance' else NON_SURFACE_VALIDATION
    return dict(value=value,unit=codes.unit_for(name),reasonCode=(reason or 'SOURCE_RANGE_NOT_ESTABLISHED') if value is None else None,warnings=list((record or {}).get('warnings',[])),leafRole=role,
                **support,moduleMaturity='Research',validationStatus=status,
                validationStatusLocator=SPEC+(' Amendment 2 B2' if status==SURFACE_VALIDATION else ' Amendment 3 C4'),
                experimentalValidation=False,uiSentence=codes.WORDING['leafSentence'])


def _reason(code, fields, record=None):
    entry=codes.REASON_CODES[code]
    result=dict(code=code,fieldPaths=fields,cause=entry['causes'][0],quantity=None,value=None,
                limitMin=None,limitMax=None,allowedValues=None,missingInputs=[],changeInputs=[])
    s=(record or {}).get('state',{})
    limits={
        'PECLET_OUTSIDE_NUMERICAL_SCOPE':('peclet',(record or {}).get('pe',s.get('v',0)*s.get('d',0)/(2*s['alpha']) if s.get('alpha') else None),.01,10.,['scanSpeed_mm_s','beamDiameter_um']),
        'PREHEAT_OUTSIDE_PROPERTY_SCOPE':('preheat_K',s.get('T0'),293.15,s.get('Tl',343.15)-50 if s.get('Tl') else None,['preheatTemp_C']),
        'ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE':('cavity aspect bound',None,None,10.,['laserPower_W','scanSpeed_mm_s','beamDiameter_um']),
    }
    if code in limits:
        quantity,value,lo,hi,change=limits[code]
        result.update(quantity=quantity,value=value,limitMin=lo,limitMax=hi,changeInputs=change,
                      cause='source-range' if code=='PREHEAT_OUTSIDE_PROPERTY_SCOPE' else 'software-limit')
        if code=='ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE' and s.get('Tv'):
            pe=s['v']*s['d']/(2*s['alpha']);onset=onset_power(s)
            result['value']=(INSIDE+OUTSIDE*s['A'])*max(s['P']-onset,0)/(s['d']*s['K']*(s['Tv']-s['T0'])*thermal_g(pe,'cylinder_exact'))
    if code=='NUMERICAL_INPUT_BELOW_FLOOR':
        for key,lo,change in (('K',1e-6,'material'),('alpha',1e-12,'material'),('d',2e-7,'beamDiameter_um'),('v',1e-6,'scanSpeed_mm_s')):
            if s.get(key) is not None and s[key]<lo:
                result.update(quantity=provenance_data.INPUT_NAMES[key],value=s[key],limitMin=lo,changeInputs=[change]);break
    if code=='VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE':result.update(cause='source-range',quantity='Mg source temperature',limitMin=600.,limitMax=1730.)
    if code in ('WAVELENGTH_UNSUPPORTED','POWDER_CONTEXT_UNSUPPORTED'):
        key='laserWavelength' if code=='WAVELENGTH_UNSUPPORTED' else 'absorptionModel'
        result.update(quantity=key,value=(record or {}).get('requestContext',{}).get(key),allowedValues=['IR_1064nm' if key=='laserWavelength' else 'flat-plate'],changeInputs=[key])
    if code=='ONSET_REFERENCE_UNAVAILABLE':
        result.update(cause='alloy-not-admitted' if any(s.get(k) is None for k in ('Tv','Lv','M')) else 'domain',quantity='onset reference',value=None)
    if code in ('SURFACE_VAPOUR_INPUT_REQUIRED','MARANGONI_VISCOSITY_INPUT_REQUIRED','MARANGONI_SOLUTE_INPUT_REQUIRED'):
        keys=('Tv','Lv','M') if code=='SURFACE_VAPOUR_INPUT_REQUIRED' else ('mu','kl','cpl','rhol') if code=='MARANGONI_VISCOSITY_INPUT_REQUIRED' else ('solubleSulfur_ppm','solubleOxygen_ppm')
        result.update(cause='input-missing',missingInputs=[provenance_data.INPUT_NAMES.get(k,k) for k in keys if s.get(k) is None],changeInputs=[provenance_data.INPUT_NAMES.get(k,k) for k in keys if s.get(k) is None])
        if code=='SURFACE_VAPOUR_INPUT_REQUIRED' and (record or {}).get('defaultCleared'):result['cause']='default-cleared'
    if code.startswith('ONSET_COMPARISON_'):result['cause']='comparison'
    if code=='SURFACE_BALANCE_CLOSURE_FALSIFIED':result['cause']='closure-falsified'
    if code in ('MARANGONI_TRANSPORT_CLOSURE_UNAVAILABLE','KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE','POWDER_THERMAL_OPERATOR_UNAVAILABLE'):result['cause']='closure-missing'
    missing={
        'MARANGONI_SURFACE_CHEMISTRY_UNAVAILABLE':['measured soluble S','measured soluble O'],
        'POWDER_ALLOY_OPTICAL_CONSTANTS_UNAVAILABLE':['grade/wavelength/temperature/state n and kappa'],
        'POWDER_LOT_INPUTS_UNAVAILABLE':['lot D32','porosity','layer thickness','substrate boundary'],
        'SOURCE_RANGE_NOT_ESTABLISHED':['located source range'],
    }
    if code in missing:result.update(cause='data-missing',missingInputs=missing[code])
    return result


class Engine:
    """ResearchEngine implementation; all state and cache ownership stays in the protocol."""
    def module_revision(self, module_id):return MODEL_IDS[module_id]+'-phase-c-r4'
    def method_settings(self, module_id):return METHOD_SETTINGS

    def manifest(self, module_id, context, options):
        if module_id=='alSi10MgVapourMgAware' and context.alloyId=='alsi10mg':
            rows=[]
            definitions=[('nominal',.44,'hybrid',1383.,False),('route_all_cc',.44,'cc',1383.,True),
                         ('latent_heat_table_weighted',.44,'hybrid',1383.,True),
                         *[(f'mg_wt_pct_{mg:g}',mg,'hybrid',1383.,False) for mg in (0.,.2,.3,.45)],
                         ('mg_boiling_1363K',.44,'hybrid',1363.,False)]
            for name,mg,route,tb,table in definitions:
                provenance=provenance_data.arm_provenance('alsi10mg','vapour_o8')
                state=dict(composition_Mg_wt_pct=mg,pressureRoute=route,mgBoilingTemperature_K=tb,
                           latentHeatConvention='table-weighted' if table else 'local-slope')
                prov={k:{**copy.deepcopy(provenance),'sourceId':provenance['sourceId']+':'+k} for k in state}
                if name.startswith('mg_wt_pct_'):
                    prov['composition_Mg_wt_pct']=provenance_data._assumption(name,'Declared Mg feedstock sensitivity, not measured surface chemistry')
                anchor=dict(composition_Mg_wt_pct=.44,pressureRoute='hybrid',mgBoilingTemperature_K=1383.,latentHeatConvention='local-slope')
                descriptor=dict(armId=name,family='nominal' if name=='nominal' else 'composition' if name.startswith('mg_wt') else 'vapour-source',
                    label=name.replace('_',' ')+': transferred O8 scenario',onsetEvent=None,
                    armProvenance=provenance_data.input_entry(provenance)['provenance'],
                    changes=[dict(input=k,value=v,nominalAnchor=anchor[k],**provenance_data.input_entry(prov[k])) for k,v in state.items() if v!=anchor[k]],aliasArmIds=[])
                rows.append(dict(armId=name,inputs=dict(mg=mg,route=route,tb=tb,table=table,sourceId=provenance['sourceId']),
                                 descriptor=descriptor,dependsOn=[],state=state,provenance=prov))
            return dict(banded=True,declared=True,arms=rows)
        return provenance_data.build_manifest(module_id,context,options)

    def presets(self,context):
        return dict(vapourPreset=[dict(id=k,label=k,admitted=aid==context.alloyId,
                    reasonCode=None if aid==context.alloyId else 'RESEARCH_PRESET_ALLOY_MISMATCH')
                    for k,(aid,_) in provenance_data.PRESETS.items()]+[dict(id='custom',label='Custom research vapour triple',admitted=True,reasonCode=None)],
                    slopeMode=[dict(id=k,label=k) for k in ('direct','fe-s-belton','fe-o-belton')])

    def controls(self,context,options):
        result=[]
        keys={'marangoni':('slopeMode','surfaceTensionSlope_N_mK','length_m','deltaTemperature_K','referenceTemperature_K','viscosity_Pa_s','solubleSulfur_ppm','solubleOxygen_ppm'),
              'surfaceBalance':('vapourPreset','vapourTemperature_K','vapourLatentHeat_J_kg','vapourMolarMass_kg_mol','evaporationConvention','evaporationAccommodation','netEvaporationFactor','recoilFraction','emissivity')}
        for module,names in keys.items():
            plan=self.manifest(module,context,options);row=plan['arms'][0];state=row['state'];prov=row['provenance'];local=options.get(module,{})
            for key in names:
                target=provenance_data.OPTION_TO_INPUT.get(key,key)
                if key=='referenceTemperature_K':value=state.get('Tref',state['Tl']+state['deltaT']/2 if state.get('Tl') is not None else None)
                elif key=='slopeMode':value=local.get(key,'direct')
                elif key=='vapourPreset':value=local.get(key,'gan-ti64' if context.alloyId=='ti6al4v' else 'pure-al-proxy' if context.alloyId=='alsi10mg' else 'custom')
                elif key=='evaporationConvention':value=local.get(key,'accommodation-and-beta')
                elif key=='netEvaporationFactor':value=state['effectiveNetFactor'] if local.get('evaporationConvention')=='net-factor' else None
                else:value=state.get(target)
                record=prov.get(target) or provenance_data._assumption(target,'Research control; no sourced default')
                record=copy.deepcopy(record)
                if key=='referenceTemperature_K' and 'Tref' not in prov:
                    record.update(kind='followsInput',followsInput='deltaTemperature_K',followState='following',defaultKind='declaredAssumption',dependsOn=['Tl','deltaT'])
                entry=provenance_data.input_entry(record)
                enums=([p['id'] for p in self.presets(context)['vapourPreset']] if key=='vapourPreset' else
                       ['direct','fe-s-belton','fe-o-belton'] if key=='slopeMode' else
                       ['accommodation-and-beta','net-factor'] if key=='evaporationConvention' else None)
                lo,hi=provenance_data.CONTROL_LIMITS.get(key,(None,None))
                enabled=not (key=='surfaceTensionSlope_N_mK' and local.get('slopeMode','direct')!='direct' or
                    key in ('solubleSulfur_ppm','solubleOxygen_ppm') and local.get('slopeMode','direct')=='direct' or
                    key=='netEvaporationFactor' and local.get('evaporationConvention')!='net-factor' or
                    key=='evaporationAccommodation' and local.get('evaporationConvention')=='net-factor')
                default_kind=record['defaultKind'] or record['kind']
                reset=('Clear (input required)' if record.get('defaultValue') is None and value is None else
                       'Follow '+str(record['followsInput'])+' again' if record['kind']=='followsInput' else
                       'Reset to '+provenance_data.KIND_LABELS.get(default_kind,'declared assumption'))
                result.append(dict(key=key,module=module,label=codes.LEAF_LABELS.get(module+'.'+key,'Research '+key),
                    help=codes.WORDING['marangoniHelp' if module=='marangoni' else 'surfaceHelp'],unit=codes.unit_for(key),
                    displayUnits={'mN/(m K)':1000} if key=='surfaceTensionSlope_N_mK' else {},valueType='enum' if enums else 'number',
                    enumValues=enums,min=lo,max=hi,enabled=enabled,value=value,provenance=entry['provenance'],
                    rangeAdmitted=enums is None and enabled,resetLabel=reset))
        return result

    def option_rule_problems(self,module,context,options):
        local=options.get(module,{});problems=[];base='/researchOptions/'+module
        def problem(key,rule,**kw):
            problems.append(codes.option_problem(base+'/'+key,rule,value=local.get(key),label=key,**kw))
        if module=='surfaceBalance':
            preset=local.get('vapourPreset')
            if preset in provenance_data.PRESETS and provenance_data.PRESETS[preset][0]!=context.alloyId:
                problem('vapourPreset','preset-alloy-mismatch',presetAlloy=provenance_data.PRESETS[preset][0])
            if local.get('vapourTemperature_K',math.inf)<=context.preheat_K:
                problem('vapourTemperature_K','below-min',limit=context.preheat_K,min=context.preheat_K,max=6000,unit='K')
            if local.get('evaporationConvention','accommodation-and-beta')=='net-factor' and 'evaporationAccommodation' in local:
                problem('evaporationAccommodation','mode-field-ignored',mode='net-factor')
            if local.get('evaporationConvention','accommodation-and-beta')!='net-factor' and 'netEvaporationFactor' in local:
                problem('netEvaporationFactor','mode-field-ignored',mode='accommodation-and-beta')
        else:
            mode=local.get('slopeMode','direct')
            if local.get('solubleSulfur_ppm') is not None and local.get('solubleOxygen_ppm') is not None:
                problem('solubleOxygen_ppm','binary-combination')
            for key in ('solubleSulfur_ppm','solubleOxygen_ppm'):
                if key in local and (mode=='direct' or key==('solubleOxygen_ppm' if mode=='fe-s-belton' else 'solubleSulfur_ppm')):
                    problem(key,'mode-field-ignored',mode=mode)
            if mode!='direct' and 'surfaceTensionSlope_N_mK' in options.get('ranges',{}).get(module,{}):
                problem('surfaceTensionSlope_N_mK','mode-field-ignored',mode=mode)
            if mode!='direct' and 'surfaceTensionSlope_N_mK' in local:
                problem('surfaceTensionSlope_N_mK','mode-field-ignored',mode=mode)
            for key in options.get('ranges',{}).get(module,{}):
                if key in ('solubleSulfur_ppm','solubleOxygen_ppm') and (mode=='direct' or key==('solubleOxygen_ppm' if mode=='fe-s-belton' else 'solubleSulfur_ppm')):
                    problem(key,'mode-field-ignored',mode=mode)
        return problems

    def module_availability(self,module_id,context,options):
        code=admission(context,provenance_data.nominal_state(context),module_id)
        if module_id in ('marangoni','surfaceBalance'):
            row=self.manifest(module_id,context,options)['arms'][0];s=row['state']
            if module_id=='surfaceBalance' and any(s.get(k) is None for k in ('Tv','Lv','M')):code='SURFACE_VAPOUR_INPUT_REQUIRED'
            if module_id=='marangoni' and s.get('mu') is None:code='MARANGONI_VISCOSITY_INPUT_REQUIRED'
        return dict(status='not-applicable' if code=='ALLOY_NOT_ALSI10MG' else 'unavailable' if code else 'available',reasonCode=code)

    def evaluate_arm(self,module,context,options,arm,upstream):
        s=arm.get('state',{});prov=arm.get('provenance',{});values={};failures={};extra={}
        code=admission(context,s,module)
        if code:
            return dict(values={k:None for k in provenance_data.FIELD_LIST[module]},failures={k:code for k in provenance_data.FIELD_LIST[module]},
                        state=s,provenance=prov,armFailure=code,status='outOfRange',warnings=[],inputScopeReasons=[],
                        requestContext=dict(laserWavelength=context.laserWavelength,absorptionModel=context.absorptionModel))
        try:
            if module=='keyholeCavity':
                values={provenance_data.INPUT_NAMES[k]:v for k,v in s.items() if k in provenance_data.INPUT_NAMES and provenance_data.INPUT_NAMES[k] in provenance_data.FIELD_LIST[module]}
                values.update(alloy=context.alloyId,propertyConvention=context.conduction.propertyConvention,
                    propertySource=SPEC+' section 3; shared material authority',vapourSource='gan-ti64' if context.alloyId=='ti6al4v' else 'pure-al-proxy')
                pe=s['v']*s['d']/(2*s['alpha']);onset=onset_power(s)
                values.update(peclet=pe,thermalResponse_g=thermal_g(pe,'cylinder_exact'),onsetPower_W=onset,
                              thresholdTemperature_K=threshold_temperature(material(s)),powerOverOnset=s['P']/onset,
                              modeledAboveOnset=s['P']>onset)
                values.update(cavity_values(s))
                if values['selectedBranch'] is None:failures['selectedBranch']='NOT_APPLICABLE_BELOW_ONSET';failures['rootScanRelativeDifference']='NOT_APPLICABLE_BELOW_ONSET'
                # Both notes require the same field-shape disclosure. Compute
                # this companion once and let the dependent link arm reuse it;
                # failures of either melt leg never erase the cavity solve.
                linked,linked_failures=link_values(s,values)
                extra.update(linkValues=linked,linkFailures=linked_failures)
                if linked.get('conductionDepth_um') is not None and linked.get('conditionalMeltDepth_um') is not None:
                    extra['fieldShapeDiagnostics']=field_shape_diagnostic(s,{**linked,**{k:values[k] for k in ('modeledAboveOnset','powerOverOnset')}})
                extra['onsetMismatch']=self._onset_mismatch(module,s,arm,upstream,values)
                if arm['armId']=='nominal':
                    extra['geometricThresholdDiagnostics']=[dict(armId='onset_O2',event='geometric-R-about-1',
                        thresholdPower_W=piston_threshold_sensitivity(material(s),s['v'],s['d']),
                        thresholdToInceptionRatio=piston_threshold_sensitivity(material(s),s['v'],s['d'])/values['onsetPower_W'],
                        provenance=provenance_data.input_entry(provenance_data.arm_provenance(context.alloyId,'onset_O2'))['provenance'],includedInInceptionEnvelope=False)]
            elif module=='meltDepthLink':
                cavity=upstream.get('keyholeCavity/'+arm['reference']['comparedArmId'],{})
                if cavity.get('armFailure') or cavity.get('values',{}).get('cavityDepth_um') is None:
                    code='MELT_LINK_NOT_AVAILABLE';values={k:None for k in provenance_data.FIELD_LIST[module]};failures={k:code for k in values}
                else:
                    if 'linkValues' in cavity:
                        values=copy.deepcopy(cavity['linkValues']);failures=dict(cavity['linkFailures'])
                    else:values,failures=link_values(s,cavity['values'])
                    if values.get('conductionDepth_um') is not None and values.get('conditionalMeltDepth_um') is not None:
                        shape=field_shape_diagnostic(s,{**values,**{k:cavity['values'][k] for k in ('modeledAboveOnset','powerOverOnset')}})
                        extra['fieldShapeDiagnostics']=shape
                    extra['onsetMismatch']=self._onset_mismatch(module,s,arm,upstream,cavity['values'])
                    if arm['armId']=='nominal':extra['fieldShapeStep']=field_shape_step(s)
            elif module=='marangoni':
                mode=options.get(module,{}).get('slopeMode','direct')
                values={provenance_data.INPUT_NAMES[k]:s.get(k) for k in ('slope','L','deltaT','mu','kl','cpl','rhol')}
                values.update(slopeMode=mode,slopeBaseline='alloy-direct' if mode=='direct' else 'fe-clean-analogue',
                              referenceTemperature_K=s.get('Tref',s['Tl']+s['deltaT']/2 if s.get('Tl') is not None else None),
                              solubleSulfur_ppm=options.get(module,{}).get('solubleSulfur_ppm'),solubleOxygen_ppm=options.get(module,{}).get('solubleOxygen_ppm'),source=SPEC+' A2 / B8')
                for key in ('solubleSulfur_ppm','solubleOxygen_ppm'):
                    if values[key] is None:failures[key]='NOT_APPLICABLE_FOR_CONVENTION' if mode=='direct' else 'MARANGONI_SOLUTE_INPUT_REQUIRED'
                if s.get('slope') is None:code='MARANGONI_SOLUTE_INPUT_REQUIRED'
                elif s.get('mu') is None:code='MARANGONI_VISCOSITY_INPUT_REQUIRED'
                elif any(s.get(k) is None for k in ('kl','cpl','rhol')):code='MARANGONI_VISCOSITY_INPUT_REQUIRED'
                else:
                    values.update(marangoni(s));alpha=s['kl']/(s['rhol']*s['cpl']);u=values['surfaceVelocityScale_m_s']
                    values.update(liquidDiffusivity_m2_s=alpha,marangoniMagnitude=abs(values['marangoniNumber']),
                                  liquidReynoldsScale=s['rhol']*u*s['L']/s['mu'],liquidPrandtl=s['mu']*s['cpl']/s['kl'])
                if code:
                    for key in ('marangoniNumber','marangoniMagnitude','surfaceVelocityScale_m_s','liquidPecletScale','liquidReynoldsScale','liquidPrandtl','liquidDiffusivity_m2_s'):
                        values[key]=None;failures[key]=code
                    values['flowDirection']='outward' if s.get('slope',0) is not None and s['slope']<0 else 'inward' if s.get('slope') else 'none'
            elif module=='surfaceBalance':
                local=options.get(module,{});convention='net-factor' if arm['armId'].startswith('accommodation_') else local.get('evaporationConvention','accommodation-and-beta')
                s=copy.deepcopy(s)
                if convention=='net-factor':s['accommodation']=1.
                values={provenance_data.INPUT_NAMES[k]:s.get(k) for k in ('Tv','Lv','M','accommodation','effectiveNetFactor','recoil','emissivity')}
                values.update(vapourPreset=local.get('vapourPreset','gan-ti64' if context.alloyId=='ti6al4v' else 'pure-al-proxy' if context.alloyId=='alsi10mg' else 'custom'),
                              evaporationConvention=convention,netEvaporationFactor=s['effectiveNetFactor'] if convention=='net-factor' else None,
                              evaluationLocation='beam-centre-flat-surface',source=SPEC+' A3 / Amendment 2 B2')
                if convention!='net-factor':failures['netEvaporationFactor']='NOT_APPLICABLE_FOR_CONVENTION'
                if any(s.get(k) is None for k in ('Tv','Lv','M','K','cp','rho','alpha','A')):
                    code='SURFACE_VAPOUR_INPUT_REQUIRED'
                    if all(s.get(k) is not None for k in ('K','alpha','A')):
                        gain=gaussian_gain(s['v'],s['d'],s['K'],s['alpha'])
                        values.update(lossFreeCenterTemperature_K=s['T0']+s['A']*s['P']*gain,
                                      absorbedCenterFlux_W_m2=2*s['A']*s['P']/(math.pi*(s['d']/2)**2),
                                      conductiveAdmittance_W_m2K=2/(math.pi*(s['d']/2)**2*gain))
                else:values.update(provenance_data.map_fixture_values(surface(s)))
                if code:
                    for key in provenance_data.FIELD_LIST[module]:
                        if key not in values:values[key]=None;failures[key]=code
                extra['onsetMismatch']=self._onset_mismatch(module,s,arm,upstream,{})
            elif module=='alSi10MgIndexDisclosure':
                values=dict(physicalAbsorptance=context.conduction.wallAbsorptance,indexAbsorptance=context.indexAbsorptance,
                    physicalToIndexRatio=context.conduction.wallAbsorptance/context.indexAbsorptance if context.indexAbsorptance else None,
                    decision='disclosure-only',classificationChanged=False,basis='Physical absorption and the historical regime index are separate conventions; '+SPEC+' section 6')
            elif module=='alSi10MgVapourMgAware':
                inputs=arm['inputs'];o8=vapour_constants(composition(inputs['mg']),inputs['route'],mg_boiling_temperature_K=inputs['tb'])
                values=dict(scenarioTemperature_K=o8['T_v_K'],scenarioMolarMass_kg_mol=o8['M_vapour_kg_mol'],
                    scenarioLatentHeatLocalSlope_J_kg=o8['L_local_slope_J_kg'],scenarioLatentHeatTableWeighted_J_kg=o8['L_table_weighted_J_kg'],
                    pureMgPressure_atm=o8['mg_pure_pressure_atm'],composition_wt_pct=o8['composition_wt_pct'],
                    pressureRoute=inputs['route'],calculationStatus='reproduced-extrapolated-sensitivity',source=SPEC+' section 6 / Amendment 2 B7',dynamicVapourTemperature_K=None)
                failures['dynamicVapourTemperature_K']='VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE'
            else:
                failures=dict(marangoniWidthDepthCorrection='MARANGONI_SURFACE_CHEMISTRY_UNAVAILABLE',
                    physicalWallPeakTemperature_K='SURFACE_BALANCE_CLOSURE_FALSIFIED',physicalWallRecoilPressure_Pa='SURFACE_BALANCE_CLOSURE_FALSIFIED',
                    powderAbsorptance='POWDER_ALLOY_OPTICAL_CONSTANTS_UNAVAILABLE',physicalKeyholeGradient_K_m='KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE',
                    physicalKeyholeCoolingRate_K_s='KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE')
                values={k:None for k in failures}
        except (ValueError,RuntimeError) as exc:
            code=str(exc)
            if code not in codes.REASON_CODES:
                text=code.lower()
                code=('NO_STRICTLY_STABLE_ROOT' if 'strictly stable' in text else 'OPTICAL_TRACE_UNRESOLVED' if 'trace' in text else
                      'CAVITY_ROOT_SCAN_UNRESOLVED' if module=='keyholeCavity' else 'SURFACE_BALANCE_NO_BRACKET' if module=='surfaceBalance' else 'MELT_BRACKET_FAILURE')
            for key in provenance_data.FIELD_LIST[module]:
                if key not in values:values[key]=None;failures[key]=code
        reference=next(iter(upstream.values()),{}).get('values',{})
        pe=values.get('peclet',reference.get('peclet'));ratio=values.get('powerOverOnset',reference.get('powerOverOnset'))
        r=values.get('aspectRatio_e_over_d',reference.get('aspectRatio_e_over_d',0.))
        scope=input_scope_reasons('cavity' if module=='keyholeCavity' else module,prov) if module in ('keyholeCavity','meltDepthLink','marangoni','surfaceBalance') else []
        status=consistency_status('cavity' if module=='keyholeCavity' else module,
            above_onset=ratio is not None and ratio>1,peclet=pe if pe is not None else 3.,aspect=r or 0.,source_transfer=bool(scope) or module=='alSi10MgVapourMgAware',
            hard_failure=code is not None or module in ('keyholeCavity','meltDepthLink') and any(codes.code_class(c) in ('C5','C6','C8') for c in failures.values()))
        warnings=[]
        if scope:warnings.append('SOURCE_SCOPE_TRANSFER')
        if module in ('keyholeCavity','meltDepthLink'):
            if pe is not None and pe<2:warnings+=['LOW_PE_HYDRODYNAMICS_OMITTED','THERMAL_CYLINDER_CLOSURE_EXTRAPOLATED']
            if ratio is not None and ratio>1 and r is not None and r<.5:warnings+=['LOW_ASPECT_CAVITY_MECHANICS_OMITTED','THERMAL_CYLINDER_CLOSURE_EXTRAPOLATED']
        if arm['armId']=='vapour_o8' or module=='alSi10MgVapourMgAware' or options.get(module,{}).get('vapourPreset')=='o8-mg-inclusive':warnings.append('VAPOUR_PRESSURE_EXTRAPOLATED')
        if module=='surfaceBalance' and values.get('beamCenterBalanceTemperature_K') is not None:
            t=values['beamCenterBalanceTemperature_K']
            if t<s['Tv']:warnings.append('HKL_SUBBOILING_FIXED_BETA')
            if t>1.6*s['Tv']:warnings.append('VAPOUR_CONSTANT_LV_EXTREME_EXTRAPOLATION')
            if s['effectiveNetFactor']!=.8 or s['recoil']!=.6 or s['accommodation']!=1.:warnings.append('USER_COEFFICIENT_PAIR_DECOUPLED')
        if module=='marangoni' and options.get(module,{}).get('slopeMode','direct')!='direct':warnings.append('FE_ANALOGUE_BASELINE_SUBSTITUTED')
        for key in provenance_data.FIELD_LIST[module]:
            if key not in values:values[key]=None;failures[key]=code or 'SOURCE_RANGE_NOT_ESTABLISHED'
            if values[key] is None and key not in failures:failures[key]=code or 'SOURCE_RANGE_NOT_ESTABLISHED'
        return dict(values=values,failures=failures,state=s,provenance=prov,status=status,warnings=list(dict.fromkeys(warnings)),
                    inputScopeReasons=scope,reference=arm.get('reference'),pe=pe,ratio=ratio,aspect=r,
                    defaultCleared=options.get(module,{}).get('vapourPreset')=='custom' and context.alloyId in ('ti6al4v','alsi10mg'),**extra)

    def _onset_mismatch(self,module,s,arm,upstream,values):
        event=s.get('onsetMethod','dwell')
        matched=arm.get('comparisonArmId')
        if module=='keyholeCavity':matched=arm['armId']
        code=None
        if event!='dwell':comparison='event-mismatch';code='ONSET_COMPARISON_EVENT_MISMATCH'
        elif any(s.get(k) is None for k in ('Tv','Lv','M','K','alpha','A')):comparison='unavailable';code='ONSET_REFERENCE_UNAVAILABLE'
        elif matched is None:comparison='tuple-mismatch';code='ONSET_COMPARISON_TUPLE_MISMATCH'
        else:comparison='matching-tuple'
        names=('onsetPower_W','thresholdTemperature_K','surfaceTemperatureAtOnsetPower_K','surfaceRecoilAtOnsetPower_Pa','surfaceThresholdPower_W','surfaceToCavityOnsetRatio')
        result={k:None for k in names}
        if code is None:
            onset=onset_power(s);threshold=threshold_temperature(material(s));surface_at=surface({**s,'P':onset})
            gain=gaussian_gain(s['v'],s['d'],s['K'],s['alpha'])
            q_per_watt=2*s['A']/(math.pi*(s['d']/2)**2)
            h=2/(math.pi*(s['d']/2)**2*gain)
            ps=101325*math.exp(s['Lv']*s['M']/RG*(1/s['Tv']-1/threshold))
            j=s['accommodation']*s['effectiveNetFactor']*ps*math.sqrt(s['M']/(2*math.pi*RG*threshold))
            power=(h*(threshold-s['T0'])+s['Lv']*j+s['emissivity']*SB*(threshold**4-s['T0']**4))/q_per_watt
            result.update(onsetPower_W=onset,thresholdTemperature_K=threshold,
                surfaceTemperatureAtOnsetPower_K=surface_at['peakTemperatureProxy_K'],surfaceRecoilAtOnsetPower_Pa=surface_at['recoilPressure_Pa'],
                surfaceThresholdPower_W=power,surfaceToCavityOnsetRatio=power/onset)
        return dict(comparison=comparison,reasonCode=code,comparedArmId=matched,values=result)

    def refused_container(self,module,context,code,problems):
        s=provenance_data.nominal_state(context)
        record=dict(values={k:None for k in provenance_data.FIELD_LIST[module]},failures={k:code for k in provenance_data.FIELD_LIST[module]},
                    state=s,provenance=provenance_data.input_provenance(context.alloyId or context.material,'nominal',s,s),status='outOfRange',warnings=[],inputScopeReasons=[])
        plan=dict(arms=[dict(armId='nominal',descriptor=None)],banded=module not in ('alSi10MgIndexDisclosure','unavailablePhysics'),declared=False)
        result=self.aggregate(module,context,{},plan,{'nominal':record},None)
        result.update(status='unavailable',reasonCode=code,problems=problems)
        return result

    def failed_container(self,module_id,context,code):return self.refused_container(module_id,context,code,[])

    def aggregate(self,module,context,options,manifest,records,bands):
        nominal=records['nominal'];values=nominal['values'];fields={};descriptors=[copy.deepcopy(a['descriptor']) for a in manifest['arms'] if a.get('descriptor')]
        for descriptor in descriptors:
            record=records.get(descriptor['armId'],nominal)
            for change in descriptor['changes']:
                name=change['input']
                change['value']=_field(module,name,change['value'],record)
                if change['nominalAnchor'] is not None:
                    change['nominalAnchor']=_field(module,name,change['nominalAnchor'],nominal)
        status=nominal.get('status','outOfRange')
        statuses={}
        for record in records.values():statuses[record.get('status','outOfRange')]=statuses.get(record.get('status','outOfRange'),0)+1
        worst=max(statuses,key=lambda k:('inRange','extrapolated','outOfRange').index(k))
        status_support=[dict(status=k,count=_field(module,'count',v,role='convention')) for k,v in statuses.items()]
        crossing=any(r.get('ratio') is not None and r['ratio']>1 for r in records.values()) and any(r.get('ratio') is not None and r['ratio']<=1 for r in records.values())
        for name,value in values.items():
            reason=nominal.get('failures',{}).get(name)
            field=_field(module,name,value,nominal,reason,surface=module=='unavailablePhysics' and name in ('physicalWallPeakTemperature_K','physicalWallRecoilPressure_Pa'))
            field['warnings']=list(nominal.get('warnings',[]))
            if name=='indexAbsorptance':field.update(leafRole='indexConvention',sourceEvidenceKind=None)
            if name=='roots' and isinstance(value,list):
                field['value']=[{k:_field(module,k,v,nominal,role='convention' if k in ('scalarRelaxation','selected') else 'derived') for k,v in row.items()} for row in value]
            if name=='composition_wt_pct' and isinstance(value,dict):
                field['value']={k:_field(module,'composition_wt_pct',v,nominal) for k,v in value.items()}
            if module in ('keyholeCavity','meltDepthLink') and name in ('linkedMeltDepth_um','conditionalMeltDepth_um','controllingLeg') and (crossing or nominal.get('fieldShapeDiagnostics',{}).get('nearOnset')):
                field['warnings']=list(dict.fromkeys(field['warnings']+['FIELD_SHAPE_STEP_NEAR_ONSET']))
            if bands is not None and name in bands['numeric']:
                envelope=bands['numeric'][name];wrapped={k:v for k,v in envelope.items() if k not in ('min','nominal','max','nominalReasonCode')}
                for position in ('min','nominal','max'):
                    aid='nominal' if position=='nominal' else envelope[position+'ArmId']
                    row=records.get(aid,nominal)
                    endpoint_reason=(envelope.get('nominalReasonCode') if position=='nominal' else envelope.get('reasonCode')) or reason
                    wrapped[position]=_field(module,name,envelope[position],row,endpoint_reason or 'BAND_NO_SUCCESSFUL_ARM')
                    wrapped[position]['warnings']=list(row.get('warnings',[]))
                    if name in ('linkedMeltDepth_um','conditionalMeltDepth_um','controllingLeg') and (crossing or row.get('fieldShapeDiagnostics',{}).get('nearOnset')):
                        wrapped[position]['warnings']=list(dict.fromkeys(wrapped[position]['warnings']+['FIELD_SHAPE_STEP_NEAR_ONSET']))
                for count in ('successfulArms','totalArms'):
                    wrapped[count]=_field(module,count,envelope[count],reason=envelope.get('reasonCode'),role='convention')
                wrapped.update(unit=field['unit'],statusSupport=status_support)
                for position in ('min','max'):
                    desc=next((d for d in descriptors if d['armId']==envelope[position+'ArmId']),None)
                    wrapped[position+'ArmLabel']=desc['label'] if desc else None
                field['band']=wrapped;field['consistencyNoteRef']=module
            fields[name]=field
        notes=[dict(armId=aid,note=self._note(module,record,crossing)) for aid,record in records.items()]
        # Contract 13.15: the onset-side field-shape carrier is once per request,
        # not repeated inside the nominal arm note.
        for entry in notes:entry['note'].pop('fieldShapeStep',None)
        note=self._note(module,nominal,crossing)
        note.update(armNotes=notes,worstArmStatus=worst,statusSupport=status_support)
        result=dict(modelId=MODEL_IDS[module],status='available' if any(v is not None for v in values.values()) else 'not-applicable' if nominal.get('armFailure')=='ALLOY_NOT_ALSI10MG' else 'unavailable',
                    reasonCode=nominal.get('armFailure'),warnings=list(nominal.get('warnings',[])),fields=fields,
                    moduleMaturity='Research',moduleEvidenceCeiling='screening-only',validationStatus=SURFACE_VALIDATION if module=='surfaceBalance' else NON_SURFACE_VALIDATION,
                    validationStatusLocator=SPEC+(' Amendment 2 B2' if module=='surfaceBalance' else ' Amendment 3 C4'),experimentalValidation=False,
                    uiSentence=codes.UI_SENTENCES[module],consistencyNote=note,
                    inputProvenance={provenance_data.INPUT_NAMES.get(k,k):provenance_data.input_entry(v) for k,v in nominal.get('provenance',{}).items()},
                    servedDifferences=[copy.deepcopy(d) for d in codes.SERVED_DIFFERENCES if d['researchPaths'][0].split('.')[0]==module])
        if 'geometricThresholdDiagnostics' in nominal:
            result['geometricThresholdDiagnostics']=[{**row,**{k:_field(module,k,row[k],nominal) for k in ('thresholdPower_W','thresholdToInceptionRatio')}} for row in nominal['geometricThresholdDiagnostics']]
        if manifest.get('banded'):
            state=(bands or {}).get('state','not-declared');reason='BAND_PENDING' if state=='pending' else 'BAND_MANIFEST_NOT_DECLARED' if state=='not-declared' else None
            complete='pending' if state=='pending' else 'unavailable' if state=='not-declared' else 'complete'
            failed=[dict(armId=aid,reasonCode=r['armFailure']) for aid,r in records.items() if r.get('armFailure')]
            success=len(records)-len(failed)
            if complete=='complete' and success==0:complete='unavailable';reason='BAND_NO_SUCCESSFUL_ARM'
            result['band']=dict(method='declared-ofat-envelope-v1',caption=codes.WORDING['bandCaption'],manifest=descriptors,
                completeness=complete,reasonCode=reason,successfulArmCount=_field(module,'count',success,role='convention'),failedArms=failed,statusSupport=status_support,
                fields={k:v['band'] for k,v in fields.items() if 'band' in v},
                categoricalSupport=[dict(field=k,value=_field(module,k,row['value'],nominal,role='convention'),count=_field(module,'count',row['count'],role='convention')) for k,rows in (bands or {}).get('categorical',{}).items() for row in rows])
            if module=='keyholeCavity' and bands and bands['state']=='computed':
                from lpbf_research_models import categorical_support
                result['band']['categoricalSupport'] += [dict(field='rootCount',value=_field(module,'rootCount',r['value'],role='convention'),count=_field(module,'count',r['count'],role='convention'))
                    for r in categorical_support('rootCount',list(records),records)]
            if module=='keyholeCavity':
                above=sum(r.get('values',{}).get('modeledAboveOnset') is True for r in records.values());unresolved=sum(r.get('values',{}).get('modeledAboveOnset') is None for r in records.values())
                result['band']['onsetSupport']=dict(supported=_field(module,'count',above,role='convention'),total=_field(module,'count',len(descriptors),role='convention'),unresolved=_field(module,'count',unresolved,role='convention'),
                    caveat='Equal-weight named inception scenarios, not a calibrated probability. Excluded: O2 (geometric-R-about-1) is a geometric threshold and is listed separately.')
            if module=='meltDepthLink':result['band']['onsetSupportRef']='keyholeCavity.band.onsetSupport';result['band']['bandCrossesOnset']=crossing
        return result

    def _note(self,module,record,crossing=False):
        status=record.get('status','outOfRange');pe=record.get('pe');ratio=record.get('ratio');aspect=record.get('aspect');scope=record.get('inputScopeReasons',[])
        hard=[c for c in record.get('failures',{}).values() if codes.code_class(c) in ('C1','C2','C3','C4','C5','C6','C8')]
        if hard:
            winner=codes.winning_code(hard)
            sentence=codes.refusal_text(winner,_reason(winner,[],record))
        elif module=='surfaceBalance':sentence=codes.WORDING['surface']
        elif module=='alSi10MgVapourMgAware' or 'VAPOUR_PRESSURE_EXTRAPOLATED' in record.get('warnings',[]):sentence=codes.WORDING['o8']
        elif module in ('keyholeCavity','meltDepthLink') and ratio is not None and ratio<=1:
            sentence=codes.WORDING['belowOnset']+(' Extrapolated: '+', '.join(scope)+'.' if status=='extrapolated' else '')
        elif module in ('keyholeCavity','meltDepthLink') and aspect is not None and ratio is not None and ratio>1 and aspect<.5:sentence=codes.WORDING['lowAspect'].format(R=f'{aspect:.6g}')
        elif module in ('keyholeCavity','meltDepthLink') and pe is not None and pe<2:sentence=codes.WORDING['lowPe'].format(Pe=f'{pe:.6g}')
        elif module=='marangoni':sentence='This surface-flow diagnostic uses a transferred or user-supplied coefficient; the velocity is a scale and no melt-depth correction is available.'
        elif status!='inRange':sentence=codes.WORDING['sourceTransfer'].format(reasons=', '.join(scope) or 'source range not established')
        else:sentence=f'This diagnostic is inside its declared input range (Pe={pe}); no sourced onset reference or blind validation is available.'
        assumptions=[]
        if module in ('keyholeCavity','meltDepthLink','surfaceBalance'):assumptions.append(codes.WORDING['onsetMismatch'])
        if module in ('keyholeCavity','meltDepthLink'):
            assumptions += [codes.WORDING['ledgers'],codes.WORDING['fieldShape']]
            if pe is not None and pe<2:assumptions.append(codes.WORDING['lowPe'].format(Pe=f'{pe:.6g}'))
            if crossing or record.get('fieldShapeDiagnostics',{}).get('nearOnset'):
                assumptions.insert(0,codes.WORDING['nearOnset'].format(fieldShapeShareOfExcess=record.get('fieldShapeDiagnostics',{}).get('fieldShapeShare')))
        if module=='surfaceBalance':assumptions.append('Flat normal incidence, no recession or convective export, constant latent heat and effective single species; local diagonal conductive admittance is not a spatial boundary operator.')
        if module=='marangoni' and 'FE_ANALOGUE_BASELINE_SUBSTITUTED' in record.get('warnings',[]):assumptions.append(codes.WORDING['beltonHelp'])
        valid=dict(peclet=_field(module,'peclet',pe,record,'ONSET_REFERENCE_UNAVAILABLE' if pe is None else None),
                   powerOverOnset=_field(module,'powerOverOnset',ratio,record,'ONSET_REFERENCE_UNAVAILABLE' if ratio is None else None),
                   temperatureRanges=[])
        for k,bound in (('pecletMin',.01),('pecletMax',10.),('cylinderFitPecletMin',2.),('aspectBound',10.)):
            valid[k]=_field(module,k,bound,role='softwareLimit' if k!='cylinderFitPecletMin' else 'physicalInput')
        for key,p in record.get('provenance',{}).items():
            if key not in provenance_data.PHYSICAL_INPUTS.get('cavity' if module=='keyholeCavity' else module,()):continue
            t=p['referenceTemperature_K'];bounds=p['sourceRange_K'];rngstatus='rangeNotEstablished' if bounds is None else 'inRange' if t is None or bounds[0]<=t<=bounds[1] else 'extrapolated'
            # This is a temperature-scope list (7.2), not a second full input
            # inventory. Inputs without either a reference temperature or a
            # source range remain explicitly unlocated in inputProvenance.
            if t is None and bounds is None:continue
            valid['temperatureRanges'].append(dict(property=provenance_data.INPUT_NAMES.get(key,key),phase=p['phase'],
                referenceTemperature_K=_field(module,'referenceTemperature_K',t,record,'SOURCE_RANGE_NOT_ESTABLISHED' if t is None else None),
                sourceRange_K=_field(module,'sourceRange_K',bounds,record,'SOURCE_RANGE_NOT_ESTABLISHED' if bounds is None else None,role='physicalInput'),status=rngstatus))
        grouped={}
        for path,code in record.get('failures',{}).items():grouped.setdefault(code,[]).append(module+'.'+path)
        result=dict(status=status,validRange=valid,assumptions=[_field(module,'assumption',s,role='convention') for s in assumptions],
                    sentence=_field(module,'sentence',sentence,role='convention'),reasons=[_reason(c,paths,record) for c,paths in grouped.items()],
                    knownContradictions=[])
        if module=='surfaceBalance':result['knownContradictions'].append(dict(id='HKL-vs-Deisenroth',statement=_field(module,'statement','The flat closure overpredicts open IN625 mass loss by 36 to 64 times; transfer to other alloys is closure-level.',role='convention'),source=_field(module,'source',SPEC+' Amendment 2 B2; P6 Amendment 1 item 1; Deisenroth 2020 section 3.2 Fig.5',role='convention')))
        if module=='marangoni':result['knownContradictions'].append(dict(id='negative-slope-depth-sign',statement=_field(module,'statement','Negative surface slope does not determine the sign of penetration changes in a coupled flow model.',role='convention'),source=_field(module,'source','Khairallah 2016 p.38; P8 A2',role='convention')))
        mismatch=record.get('onsetMismatch') or dict(comparison='unavailable',reasonCode='ONSET_REFERENCE_UNAVAILABLE',comparedArmId=None,
            values={k:None for k in ('onsetPower_W','thresholdTemperature_K','surfaceTemperatureAtOnsetPower_K','surfaceRecoilAtOnsetPower_Pa','surfaceThresholdPower_W','surfaceToCavityOnsetRatio')})
        result['onsetMismatch']={k:v for k,v in mismatch.items() if k!='values'}
        for key,value in mismatch['values'].items():
            result['onsetMismatch'][key]=_field(module,key,value,record,mismatch['reasonCode'],surface=key not in ('onsetPower_W','thresholdTemperature_K'))
        if record.get('reference'):result['cavityReference']=record['reference']
        if 'fieldShapeDiagnostics' in record and module=='meltDepthLink':
            shape=record['fieldShapeDiagnostics'];result['fieldShapeShare']={k:shape.get(k) for k in ('applicable','nearOnset','caveat')}
            for key in ('samePowerPointDepth_um','fieldShapeExcess_um','conditionalExcessOverGaussian_um','fieldShapeShare'):
                result['fieldShapeShare'][provenance_data.FIXTURE_TO_RUNTIME.get(key,key)]=_field(module,key,shape.get(key),record,'NOT_APPLICABLE_BELOW_ONSET' if not shape['applicable'] else 'SOURCE_RANGE_NOT_ESTABLISHED')
        if 'fieldShapeStep' in record:
            step=record['fieldShapeStep'];result['fieldShapeStep']={}
            for key,value in step.items():
                if key=='onsetSideRecords':
                    result['fieldShapeStep'][key]=[{**row,'values':{k:_field(module,k,v,record) for k,v in row['values'].items() if k in provenance_data.FIELD_LIST['meltDepthLink'] or k in ('onsetPower_W','powerOverOnset','cavityDepth_um')}} for row in value]
                elif key in ('relativeBracket','aboveOnsetFieldChanged','cause'):result['fieldShapeStep'][key]=value
                else:result['fieldShapeStep'][key]=_field(module,key,value,record)
            result['fieldShapeStep']['locator']=SPEC+' Amendment 3 C2'
        return result
