#!/usr/bin/env python3
"""
Literature-default Monte Carlo UQ for LPBF build-job screening.

Perturbs P, absorptivity, spot, k, and density with published-typical ± bands.
Not machine-calibrated. Seeded for bit reproducibility.

Screening sensitivity uses Spearman |ρ| share vs verdict score (still a proxy —
not Saltelli / full Sobol'). Labelled screeningSensitivity / sobolProxy for UI.
"""

from __future__ import annotations

import math
import random
from typing import Any, Callable, Dict, List, Optional

# Literature screening defaults (not OEM-calibrated).
UQ_BANDS = {
    "power_rel": 0.03,
    "absorptivity_rel": 0.15,
    "spot_rel": 0.075,
    "conductivity_rel": 0.12,
    "density_rel": 0.10,
}

DEFAULT_UQ_SAMPLES = 96


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _mean_std(vals: List[float]) -> tuple[float, float]:
    if not vals:
        return 0.0, 0.0
    n = len(vals)
    mu = sum(vals) / n
    if n < 2:
        return mu, 0.0
    var = sum((v - mu) ** 2 for v in vals) / (n - 1)
    return mu, math.sqrt(var)


def _pearson(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    if n < 3 or n != len(ys):
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx < 1e-12 or dy < 1e-12:
        return 0.0
    return num / (dx * dy)


def _rankdata(vals: List[float]) -> List[float]:
    """Average ranks for ties (1-based)."""
    n = len(vals)
    order = sorted(range(n), key=lambda i: vals[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = 0.5 * (i + j) + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _spearman(xs: List[float], ys: List[float]) -> float:
    if len(xs) < 3 or len(xs) != len(ys):
        return 0.0
    return _pearson(_rankdata(xs), _rankdata(ys))


def _verdict_score(v: str) -> float:
    if v == "printable":
        return 1.0
    if v == "risky":
        return 0.5
    return 0.0


def run_screening_uq(
    *,
    base_power_W: float,
    base_beam_um: float,
    thermal_runner: Callable[[float, float, Optional[Dict[str, float]]], Dict[str, Any]],
    verdict_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    n_samples: int = DEFAULT_UQ_SAMPLES,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    thermal_runner(power_W, beam_um, prop_overrides) -> thermal dict
    verdict_fn(thermal) -> compose_verdict result
    """
    n = max(8, min(500, int(n_samples)))
    rng = random.Random(int(seed))

    dh_vals: List[float] = []
    scores: List[float] = []
    printable = 0
    risky = 0
    dnp = 0
    inconclusive = 0

    z_power: List[float] = []
    z_abs: List[float] = []
    z_spot: List[float] = []
    z_k: List[float] = []
    z_rho: List[float] = []
    
    defect_samples = []

    for _ in range(n):
        zp = rng.gauss(0.0, 1.0)
        za = rng.gauss(0.0, 1.0)
        zs = rng.gauss(0.0, 1.0)
        zk = rng.gauss(0.0, 1.0)
        zr = rng.gauss(0.0, 1.0)
        z_power.append(zp)
        z_abs.append(za)
        z_spot.append(zs)
        z_k.append(zk)
        z_rho.append(zr)

        p = base_power_W * (1.0 + UQ_BANDS["power_rel"] * zp)
        p = _clamp(p, 10.0, 2000.0)
        beam = base_beam_um * (1.0 + UQ_BANDS["spot_rel"] * zs)
        beam = _clamp(beam, 20.0, 300.0)
        a_scale = _clamp(1.0 + UQ_BANDS["absorptivity_rel"] * za, 0.4, 1.8)
        k_scale = _clamp(1.0 + UQ_BANDS["conductivity_rel"] * zk, 0.5, 1.6)
        rho_scale = _clamp(1.0 + UQ_BANDS["density_rel"] * zr, 0.6, 1.4)

        # Absorptivity scale applied in runner via relative multipliers on IR/Green.
        overrides = {
            "_uq_absorptivity_scale": a_scale,
            "_uq_k_scale": k_scale,
            "_uq_rho_scale": rho_scale,
        }
        thermal = thermal_runner(p, beam, overrides)
        defect_samples.append(thermal.get("geometricDefectScreen", {}))
        decision = verdict_fn(thermal)
        v = decision.get("verdict", "risky")
        if v == "printable":
            printable += 1
        elif v == "do-not-print":
            dnp += 1
        elif v == "inconclusive":
            # Melt-pool geometry unresolved (extentStatus != "computed"): not a risky verdict.
            inconclusive += 1
        else:
            risky += 1
        scores.append(_verdict_score(v))
        dh_vals.append(float(thermal["processParameters"]["normalizedEnthalpy"]))

    dh_mu, dh_sigma = _mean_std(dh_vals)
    p_printable = printable / float(n)

    # Spearman |ρ| share — still a screening proxy, not Saltelli Sobol'.
    sensitivity_raw = {
        "power": round(abs(_spearman(z_power, scores)), 4),
        "absorptivity": round(abs(_spearman(z_abs, scores)), 4),
        "spot": round(abs(_spearman(z_spot, scores)), 4),
        "conductivity": round(abs(_spearman(z_k, scores)), 4),
        "density": round(abs(_spearman(z_rho, scores)), 4),
    }
    ssum = sum(sensitivity_raw.values()) or 1.0
    sensitivity_share = {k: round(v / ssum, 4) for k, v in sensitivity_raw.items()}
    dominant = max(sensitivity_share.items(), key=lambda kv: kv[1])[0]

    return {
        "enabled": True,
        "nSamples": n,
        "seed": int(seed),
        "bands": dict(UQ_BANDS),
        "calibration": "literature-default",
        "P_printable": round(p_printable, 4),
        "counts": {"printable": printable, "risky": risky, "do_not_print": dnp, "inconclusive": inconclusive},
        "normalizedEnthalpy": {
            "mean": round(dh_mu, 3),
            "std": round(dh_sigma, 3),
            "unit": "1",
        },
        "sensitivityMethod": "spearman-proxy",
        "screeningSensitivity": sensitivity_share,
        # Alias for older UI / tests.
        "sobolProxy": sensitivity_share,
        "dominantUncertainty": dominant,
        "defectSamples": defect_samples,
        "note": (
            "Monte Carlo with literature \u00b1 bands; screeningSensitivity is |Spearman \u03c1| share "
            "vs verdict score (proxy - not Saltelli Sobol'). SCREENING ONLY - not machine-calibrated."
        ),
    }


def apply_uq_prop_scales(props: Dict[str, Any], overrides: Optional[Dict[str, float]],
                         kernel: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Expand UQ scale keys into concrete thermophysical overrides.

    ``kernel`` (P7b, Amendment 1 item 3.3): the ledger kernel of the alloy at the job's own preheat
    (four_alloy_materials.kernel_properties), materialised into explicit kernel_* keys so that _uq_k_scale and
    _uq_rho_scale reach the conduction kernel of a ledger alloy (the solver's ledger rule would otherwise ignore the
    scaled solid and liquid keys). None for an alloy without a ledger entry.
    """
    if not overrides:
        return {}
    out: Dict[str, Any] = {}
    a_scale = overrides.get("_uq_absorptivity_scale")
    k_scale = overrides.get("_uq_k_scale")
    rho_scale = overrides.get("_uq_rho_scale")
    if a_scale is not None:
        # P7b: the field absorptivity is scaled; the index convention constant absorptivity_index_IR is NOT scaled
        # (passed through unchanged from the base props), so UQ no longer moves the regime label or the Fabbro
        # onset weight (spec question 4, reasons file IR-2).
        out["absorptivity_IR"] = float(props["absorptivity_IR"]) * float(a_scale)
        out["absorptivity_Green"] = float(props["absorptivity_Green"]) * float(a_scale)
    if k_scale is not None:
        ks = float(props["thermal_conductivity_W_mK"]) * float(k_scale)
        kl = float(props.get("thermal_conductivity_liquid_W_mK", props["thermal_conductivity_W_mK"])) * float(
            k_scale
        )
        out["thermal_conductivity_W_mK"] = ks
        out["thermal_conductivity_liquid_W_mK"] = kl
        # P7b (spec 3.3.4): the two melting-point keys follow the same scale when the property set carries them.
        for melt_key in ("thermal_conductivity_melt_W_mK", "specific_heat_melt_J_kgK"):
            if melt_key in props:
                out[melt_key] = float(props[melt_key]) * float(k_scale)
    if kernel is not None and (k_scale is not None or rho_scale is not None):
        # Materialise the ledger kernel at the job preheat into explicit kernel keys (precedence rule (i)).
        kk = float(k_scale) if k_scale is not None else 1.0
        out["kernel_conductivity_W_mK"] = float(kernel["kernel_conductivity_W_mK"]) * kk
        out["kernel_specific_heat_J_kgK"] = float(kernel["kernel_specific_heat_J_kgK"]) * kk
        out["kernel_density_kg_m3"] = float(kernel["kernel_density_kg_m3"]) * (
            float(rho_scale) if rho_scale is not None else 1.0)
    if rho_scale is not None:
        out["density_kg_m3"] = float(props["density_kg_m3"]) * float(rho_scale)
        if "density_liquid_kg_m3" in props:
            out["density_liquid_kg_m3"] = float(props["density_liquid_kg_m3"]) * float(rho_scale)
        if "kernel_density_kg_m3" in props and "kernel_density_kg_m3" not in out:
            out["kernel_density_kg_m3"] = float(props["kernel_density_kg_m3"]) * float(rho_scale)
    # Pass through any direct overrides that are not scale keys.
    for k, v in overrides.items():
        if not str(k).startswith("_uq_"):
            out[k] = v
    return out
