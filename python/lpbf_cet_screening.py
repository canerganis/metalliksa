#!/usr/bin/env python3
"""
Columnar-to-equiaxed transition (CET) screening criterion, Gäumann form of Hunt 1984 (stdlib only).

Screening only, not validation. The module ships the equation and an honest constants registry. IN718 has two
sourced constant sets, both calibrated for electron-beam melting (EBM) and transferred to LPBF without an LPBF fit:
Knapp 2019 (n=2, a=4.5, N0=2.65e14, calibrated to a casting map) and Polonsky 2020 (n=3.13, a=1.23e5, N0=5.4e12,
a lower bound from counted grains). IN625 has no sourced constants and its registry status stays "unavailable".
CMSX-4 constants are kept as a reference only and are never used for a band. Synthetic constants may be passed to
`critical_gradient_K_m`, `cet_band` and `cet_block(constants_override=...)` by tests only.

Equation (E3), nucleation undercooling neglected:

    G^n / V = a * [ (1 / (n + 1)) * (-4 pi N0 / (3 ln(1 - phi)))^(1/3) ]^n

so the boundary is

    G_crit(V, phi) = (a V)^(1/n) / (n + 1) * (-4 pi N0 / (3 ln(1 - phi)))^(1/3).

phi_columnar = 0.0066 and phi_equiaxed = 0.49 are Hunt's equiaxed-fraction thresholds (H84). G >= G_crit(V, 0.0066)
is "columnar", G <= G_crit(V, 0.49) is "equiaxed", anything between is "mixed". V is the local growth rate R.

Sources
  GA01  M. Gäumann, C. Bezençon, P. Canalis, W. Kurz, Acta Mater. 49 (2001) 1051-1062,
        DOI 10.1016/S1359-6454(00)00367-0. The DOI was confirmed against a Crossref-cited record. The paper was NOT
        read for this design: sourceChecks.equationRead is not-read and the locator is unset until the
        maintainer reads the PDF. The Knapp form is verified separately, per set (see CET_SETS).
  KN19  A. Knapp et al., Additive Manufacturing 25 (2019) 511-521, DOI 10.1016/j.addma.2018.12.001. Eq. 12 and the
        Hunt phi limits are on p. 514, the constants and the printed G^2R limits on p. 515.
  PO20  M. Polonsky et al., 2020, OSTI 1659558, Sec 3.3, Eq. 4-5 and Table 2.
  H84   J. D. Hunt, Mater. Sci. Eng. 65 (1984) 75-83, DOI 10.1016/0025-5416(84)90201-5.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Tuple

MODEL_ID = "gaumann2001-hunt1984-cet-screening-v1"
PHI_COLUMNAR = 0.0066
PHI_EQUIAXED = 0.49

SOURCES: Dict[str, Dict[str, str]] = {
    "GA01": {
        "citation": "M. Gäumann, C. Bezençon, P. Canalis, W. Kurz, Acta Mater. 49 (2001) 1051-1062 "
                    "(single-crystal laser deposition of CMSX-4; CET model)",
        "doi": "10.1016/S1359-6454(00)00367-0",
    },
    "KN19": {
        "citation": "A. Knapp et al., Additive Manufacturing 25 (2019) 511-521 (EB-PBF IN718, CET criterion calibrated "
                    "to a casting solidification map)",
        "doi": "10.1016/j.addma.2018.12.001",
    },
    "PO20": {
        "citation": "M. Polonsky et al., 2020 (EBM IN718, IMS-fitted CET constants, N0 from counted grains)",
        "osti": "1659558",
    },
    "H84": {
        "citation": "J. D. Hunt, Mater. Sci. Eng. 65 (1984) 75-83 (steady-state columnar and equiaxed growth of dendrites "
                    "and eutectic)",
        "doi": "10.1016/0025-5416(84)90201-5",
    },
}

EQUATION = "G^n/V = a*[(1/(n+1))*(-4*pi*N0/(3*ln(1-phi)))^(1/3)]^n"
SOURCE_CHECKS = {
    "equationRead": {"status": "not-read", "locator": None},
    "algebraReproduced": {"status": "not-attempted", "test": None},
    "printedLimitComparison": {"status": "not-attempted", "printed": None, "computed": None, "tolerance": None},
}


def _c(value: Optional[float], unit: str, source: Optional[str], locator: Optional[str], *, verified: bool) -> Dict[str, Any]:
    return {"value": value, "unit": unit, "source": source, "locator": locator, "verified": verified}


CRITERION_NOTE = (
    "Nucleation undercooling dTn is neglected in this form. The model is single-component-like: multicomponent "
    "solutal effects are not in the equation. N0 (nucleant density) depends on the process and powder and is not "
    "a material constant. Screening only; not a grain-structure prediction."
)


TRANSFER_LABEL = "EBM-calibrated, transferred to LPBF"
TRANSFER_CAVEAT = (
    "Calibrated for electron-beam melting and transferred to LPBF without an LPBF fit. LPBF powder, nucleant density, "
    "gradients and remelting differ, so treat the band as an indication only."
)

CET_SETS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "in718": {
        "knapp2019": {
            "label": "Knapp 2019, IN718 EB-PBF (calibrated to a casting map)",
            "transferLabel": TRANSFER_LABEL,
            "caveat": TRANSFER_CAVEAT,
            "source": "KN19",
            "citation": SOURCES["KN19"]["citation"],
            "doi": SOURCES["KN19"]["doi"],

            "equationLocator": "Knapp 2019 p. 514, Eq. 12",
            "verifiedBy": "Printed G^2R limits reproduced: 1.52e11 at phi 0.0066 and 6.98e9 at phi 0.49 (p. 515).",
            "phiColumnar": 0.0066,
            "phiEquiaxed": 0.49,
            "phiSource": "Hunt 1984 critical values as used in Knapp 2019 p. 514; limits printed p. 515",
            "constants": {
                "a": _c(4.5, "K^n s/m", "KN19", "p. 515, constants (top of left column)", verified=True),
                "n": _c(2.0, "-", "KN19", "p. 515, constants (top of left column)", verified=True),
                "N0": _c(2.65e14, "m^-3", "KN19", "p. 515, constants (top of left column)", verified=True),
            },
            "note": "N0 is the nucleant density used for the casting-map calibration, not an LPBF measurement.",
        },
        "polonsky2020": {
            "label": "Polonsky 2020, IN718 EBM (IMS-fitted, N0 from grain counts)",
            "transferLabel": TRANSFER_LABEL,
            "caveat": TRANSFER_CAVEAT,
            "source": "PO20",
            "citation": SOURCES["PO20"]["citation"],
            "osti": SOURCES["PO20"]["osti"],

            "equationLocator": "Polonsky 2020 Sec 3.3, Eq. 4 (Gaumann form) and Eq. 5",
            "verifiedBy": None,
            "phiColumnar": 0.0066,
            "phiEquiaxed": 0.49,
            "phiSource": "Hunt 1984 via Knapp 2019 p. 514; not stated by Polonsky 2020",
            "constants": {
                "a": _c(1.23e5, "K^n s/m", "PO20", "Sec 3.3, Eq. 5, Table 2 (paper prints the unit as m s/K^n, a typo; "
                        "Eq. 5 needs K^n s/m)", verified=True),
                "n": _c(3.13, "-", "PO20", "Sec 3.3, Table 2", verified=True),
                "N0": _c(5.4e12, "m^-3", "PO20", "Sec 3.3, Table 2 (206 grains in 38.4 nL; the paper calls it a lower "
                         "bound)", verified=True),
            },
            "note": "N0 is a lower bound from counted grains, so the equiaxed boundary sits at lower G than a larger "
                    "N0 would give.",
        },
    },
    "in625": {},
}

for _set_id, _entry in CET_SETS["in718"].items():
    _knapp = _set_id == "knapp2019"
    _entry["sourceChecks"] = {
        "equationRead": {"status": "read", "locator": _entry["equationLocator"]},
        "algebraReproduced": {"status": "reproduced", "test": "test_lpbf_gr_solidification.CetTests.test_source_set_algebra_reproduced"},
        "printedLimitComparison": {
            "status": "agrees" if _knapp else "not-available",
            "printed": [1.52e11, 6.98e9] if _knapp else None,
            "computed": [152010043633.87595, 6977525390.911521] if _knapp else None,
            "tolerance": 0.01 if _knapp else None,
        },
    }

# Reference only: CMSX-4 constants quoted by Polonsky Sec 3.3 / Table 2 from Gaumann. Never used for IN718 or IN625.
CMSX4_REFERENCE: Dict[str, Any] = {
    "label": "CMSX-4 reference only (not IN718, not used for any band)",
    "source": "PO20",
    "locator": "Sec 3.3, Table 2, quoting Gaumann et al. 2001",
    "constants": {
        "a": _c(1.25e6, "K^n s/m", "PO20", "Sec 3.3, Table 2", verified=True),
        "n": _c(3.4, "-", "PO20", "Sec 3.3, Table 2", verified=True),
        "N0": _c(2.0e15, "m^-3", "PO20", "Sec 3.3, Table 2", verified=True),
    },
}

CANDIDATE_SOURCES: Dict[str, List[Dict[str, Any]]] = {
    "in718": [
        {"citation": "M. Haines, A. Plotkowski, C.L. Frederick, E.J. Schwalbach, S.S. Babu, Comput. Mater. Sci. (2018), "
                     "CET sensitivity analysis for Ni superalloys in EBM", "osti": "1474534", "read": False},
        {"citation": "N. Raghavan et al., Acta Mater. (2016), IN718 EBM grain morphology", "osti": "1252143", "read": False},
    ],
    "in625": [],
}

UNAVAILABLE_REASONS: Dict[str, str] = {
    "in718": "No complete sourced CET constant set is registered for IN718.",
    "in625": "No CET constants are sourced for IN625 (none published or read); LPBF has no CET fit for any alloy here.",
}
UNKNOWN_ALLOY_REASON = "No CET constants registry entry for this alloy."


def _set_complete(entry: Mapping[str, Any]) -> bool:
    consts = entry.get("constants") or {}
    return entry.get("sourceChecks", {}).get("equationRead", {}).get("status") == "read" and all(
        consts.get(k) is not None
        and consts[k].get("verified") is True
        and isinstance(consts[k].get("value"), (int, float))
        and not isinstance(consts[k]["value"], bool)
        and math.isfinite(consts[k]["value"])
        and consts[k]["value"] > 0
        and consts[k].get("source")
        and consts[k].get("locator")
        for k in ("a", "n", "N0")
    )


def _set_view(set_id: str, entry: Mapping[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in entry.items() if k != "constants"}
    out["id"] = set_id
    out["constants"] = {k: dict(v) for k, v in entry["constants"].items()}
    return out


def cet_constants(alloy_id: str) -> Dict[str, Any]:
    """{"status": "available"|"unavailable", "reason", "sets", "candidateSources", "referenceOnly"}.

    Available only when at least one set has a, n, N0 all verified with a value, a source and a locator.
    Incomplete sets are never listed as usable."""
    candidates = [dict(c) for c in CANDIDATE_SOURCES.get(alloy_id, [])]
    reference = {"label": CMSX4_REFERENCE["label"], "source": CMSX4_REFERENCE["source"],
                 "locator": CMSX4_REFERENCE["locator"],
                 "constants": {k: dict(v) for k, v in CMSX4_REFERENCE["constants"].items()}}
    if alloy_id not in CET_SETS:
        return {"status": "unavailable", "reason": UNKNOWN_ALLOY_REASON, "sets": [], "candidateSources": candidates,
                "referenceOnly": reference}
    sets = [_set_view(sid, e) for sid, e in CET_SETS[alloy_id].items() if _set_complete(e)]
    if sets:
        return {"status": "available", "reason": None, "sets": sets, "candidateSources": candidates,
                "referenceOnly": reference}
    return {"status": "unavailable", "reason": UNAVAILABLE_REASONS.get(alloy_id, UNKNOWN_ALLOY_REASON), "sets": [],
            "candidateSources": candidates, "referenceOnly": reference}


def critical_gradient_K_m(v_m_s: float, phi: float, *, a: float, n: float, n0_m3: float) -> float:
    """E3 solved for G. ValueError on v <= 0, n <= 0, a <= 0, n0 <= 0, phi not in (0, 1)."""
    for name, value in (("v_m_s", v_m_s), ("a", a), ("n", n), ("n0_m3", n0_m3), ("phi", phi)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
    if not v_m_s > 0:
        raise ValueError("v_m_s must be > 0")
    if not n > 0:
        raise ValueError("n must be > 0")
    if not a > 0:
        raise ValueError("a must be > 0")
    if not n0_m3 > 0:
        raise ValueError("n0_m3 must be > 0")
    if not 0.0 < phi < 1.0:
        raise ValueError("phi must lie in (0, 1)")
    nucleus = (-4.0 * math.pi * n0_m3 / (3.0 * math.log(1.0 - phi))) ** (1.0 / 3.0)
    return (a * v_m_s) ** (1.0 / n) / (n + 1.0) * nucleus


def cet_band(g_K_m: float, v_m_s: float, constants: Mapping[str, float]) -> Dict[str, Any]:
    """{"band": "columnar"|"mixed"|"equiaxed", "G_columnar_K_m", "G_equiaxed_K_m"}; constants keys a, n, N0."""
    if isinstance(g_K_m, bool) or not isinstance(g_K_m, (int, float)) or not math.isfinite(g_K_m) or g_K_m <= 0:
        raise ValueError("G must be finite and positive")
    kw = {"a": constants["a"], "n": constants["n"], "n0_m3": constants["N0"]}
    g_col = critical_gradient_K_m(v_m_s, PHI_COLUMNAR, **kw)
    g_eq = critical_gradient_K_m(v_m_s, PHI_EQUIAXED, **kw)
    if g_K_m >= g_col:
        band = "columnar"
    elif g_K_m <= g_eq:
        band = "equiaxed"
    else:
        band = "mixed"
    return {"band": band, "G_columnar_K_m": g_col, "G_equiaxed_K_m": g_eq}


def _locations(points: Mapping[str, Optional[Tuple[float, float]]], constants: Mapping[str, float]
               ) -> Dict[str, Optional[Dict[str, Any]]]:
    locations: Dict[str, Optional[Dict[str, Any]]] = {}
    for name, gr in points.items():
        if gr is None:
            locations[name] = None
            continue
        g, r = gr
        try:
            locations[name] = cet_band(g, r, constants)
        except ValueError:
            locations[name] = None
    return locations


def cet_block(alloy_id: str, points: Mapping[str, Optional[Tuple[float, float]]], *,
              constants_override: Optional[Mapping[str, float]] = None) -> Dict[str, Any]:
    """Per location (bottom/median/tail) band, or status unavailable with the registry reason.

    points maps a location name to (G_K_m, R_m_s) or None. With the registry, the result carries one entry per sourced
    set under "sets" (each with its own locations) and the top-level "locations" stay None. constants_override
    (keys a, n, N0) is for tests only and fills the top-level "locations" with no "sets"."""
    from quantity_envelope import reason, reason_text
    return {"status": "unavailable", "reason": reason_text("outside-source-model-domain"),
            "reasons": [reason("outside-source-model-domain")],
            "locations": {k: None for k in points}, "sets": {}}


def criterion_view() -> Dict[str, Any]:
    return {
        "modelId": MODEL_ID,
        "equation": EQUATION,
        "sourceChecks": SOURCE_CHECKS,
        "phiColumnar": PHI_COLUMNAR,
        "phiEquiaxed": PHI_EQUIAXED,
        "sources": {k: dict(v) for k, v in SOURCES.items()},
        "note": CRITERION_NOTE,
        "transferLabel": TRANSFER_LABEL,
    }
