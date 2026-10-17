#!/usr/bin/env python3
"""
Murakami sqrt(area) defect-conditioned threshold scenario, block-maxima Gumbel statistics, CT threshold echo and the
qualification template (SPEC_engine_estimates_2026-10-17 group 7 with Amendment 1, A1.4 and A1.5).

Nothing is invented: no defect size, hardness, cycle target or CT threshold has a default, on any route (Build Job,
direct API, unknown alloy). Missing inputs give an actionable missing-input result. Every value is an
"Uncalibrated estimate" (Tier 2): the law is Murakami's steel-derived small-defect law, its cited applications are EBM
or forged Ti-6Al-4V and AlSi10Mg studies, and no input sensitivity range is a promotion.

F1  sigma_w = C (HV + 120) / s^(1/6) [MPa], s = projected sqrt(area) in micrometres, HV the Vickers number, C 1.43
    (surface) or 1.56 (internal), fully reversed loading R = -1. It is a threshold scenario, never a fatigue strength
    at a cycle count (Uematsu 2021: the unmodified law is nonconservative at 1e8 cycles). Refused at s >= 1000 um and
    for an identified long crack (long-crack route needed).
F2  Gumbel on comparable independent block maxima only: method of moments, explicit block and target volumes and an
    explicit target probability p: x = mu - beta ln(-ln(p^(V0/V))). Individual pore lists give the observed maximum,
    labelled "observed in supplied data", with no estimate tier.
F3  CT detection threshold: echo of the supplied measured/validated threshold and its method; no numerical tier.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Mapping, Optional

import input_validation
import murakami_constants
import quantity_envelope as qe

SCHEMA = "murakami-screening-2"
MODEL_ID = "murakami-threshold-scenario-v1"
TIER2 = qe.ESTIMATE_TIER_LABELS["Physics estimate"]
UNKNOWN = qe.UNCERTAINTY_STATEMENT_TIER2
LOCATIONS = ("surface", "internal")
EVIDENCE = ("measured", "assumed-scenario")
SHORT_CRACK_LIMIT_UM = 1000.0
GUMBEL_DESIGN = "comparable-independent-block-maxima"
EULER_GAMMA = 0.5772156649015329

PASTE_HINT = (
    "Paste sqrt(area) values in micrometres: one per line, or CSV / whitespace / semicolon separated. "
    "No sizes are invented when this is empty."
)
MISSING_TEXT = ("Supply projected defect square-root area in micrometres, defect location and material hardness, or "
                "select an explicit defect scenario. Add the load ratio and cycle target to interpret the estimate. "
                "Laser settings alone do not determine fatigue strength.")
LONG_CRACK_TEXT = ("The supplied defect size is {s} micrometres, at or above this short-crack model's 1000 micrometre "
                   "screening limit. Supply a long-crack threshold, geometry factor and crack length for a compatible "
                   "fracture-mechanics estimate.")
IDENTIFIED_LONG_CRACK_TEXT = ("The defect is identified as a long crack. Supply a long-crack threshold, geometry "
                              "factor and crack length for a compatible fracture-mechanics estimate.")
LOAD_RATIO_TEXT = ("This threshold law is stated for fully reversed loading (R = -1). A load ratio of {r} needs a "
                   "sourced mean-stress model. Remove the load ratio to see the R = -1 scenario.")
CYCLE_TEXT = ("No fatigue strength is given at {n} cycles. The unmodified Murakami law is a threshold scenario and "
              "is nonconservative at very high cycle counts; a cycle-specific estimate needs an applicable sourced "
              "life model.")
GUMBEL_TEXT = ("A largest-defect distribution needs independent maxima from comparable inspected regions and a target "
               "volume. The supplied pore list can show its observed maximum, but cannot establish the part-wide "
               "maximum.")
CT_MISSING_TEXT = "Add the CT detection threshold and its validation method to describe which defect sizes may be missed."

# A1.4 size support of the cited application (source specimen ranges, not LPBF applicability rectangles).
RADLOF_LOCATOR = ("Radlof et al. 2020, Materials 13, 4642, doi 10.3390/ma13204642, section 3.2.3 and Eqs. 10-11 "
                  "(PDF p.15): EBM Ti-6Al-4V defect sizes")
SIZE_SUPPORT = {
    "ti6al4v": {"vertical": (120.0, 300.0), "horizontal": (75.0, 200.0)},
}
SRC_UEMATSU = qe.source_ref("uematsu2021", "Uematsu et al. 2021, Metals 11, 964, doi 10.3390/met11060964, Eq. 1 "
                            "(surface form C = 1.43; unmodified law nonconservative at 1e8 cycles, abstract)",
                            "primary-read")
SRC_TI_INTERNAL = qe.source_ref("ti64-internal-2021", "Materials 14 (2021) 5315, doi 10.3390/ma14185315, Eq. 1 "
                                "(internal form C = 1.56, R = -1)", "primary-read")
SRC_RADLOF = qe.source_ref("radlof2020", RADLOF_LOCATOR + "; both forms 1.43 and 1.56", "primary-read")
SRC_STRAUSS = qe.source_ref("strauss2024", "Strauss et al. 2024, Fatigue Fract. Eng. Mater. Struct., doi "
                            "10.1111/ffe.14441, section 2.3.1 Eq. 1 (AlSi10Mg application)", "primary-read")
SRC_MACHADO = qe.source_ref("machado2019", "Machado et al. 2019, MATEC Web Conf. 300, 16005, doi "
                            "10.1051/matecconf/201930016005, section 2 (small-defect limit about 1000 um; indexed "
                            "publisher text)", "secondary-read")
SRC_NIST_GUMBEL = qe.source_ref("nist-gumbel", "NIST/SEMATECH e-Handbook 1.3.6.6.16, Extreme Value Type I (maximum): "
                                "CDF and percent point function", "primary-read")
ALLOY_NAMES = {"ti6al4v": "Ti-6Al-4V", "alsi10mg": "AlSi10Mg", "in718": "IN718", "ss316l": "316L", "in625": "IN625"}
TRANSFER = {
    "ti6al4v": "The cited Ti-6Al-4V applications are EBM and forged specimens, not this LPBF state.",
    "alsi10mg": "The cited AlSi10Mg application does not supply this build's residual stress or surface state.",
    "ss316l": "The defect law is transferred to 316L; it is not a stainless fatigue qualification.",
    "in718": "The defect law is transferred to IN718; heat treatment and temperature are not represented.",
    "in625": "The defect law is transferred to IN625; no nickel calibration is claimed.",
}


def parse_defect_sqrt_areas_text(text: Optional[str]) -> List[float]:
    """Parse pasted CSV / whitespace / line-separated sqrt(area) (um). Empty -> [].

    Non-numeric tokens and non-positive numbers are skipped; "inf" / "nan" tokens
    are rejected with input_validation.ValidationError (NON_FINITE) instead of being
    kept (inf) or silently dropped (nan) and poisoning the Gumbel fit.
    """
    if not text or not str(text).strip():
        return []
    parts = re.split(r"[\s,;|/]+", str(text).strip())
    out: List[float] = []
    for p in parts:
        if not p:
            continue
        try:
            v = float(p)
        except ValueError:
            continue
        if not math.isfinite(v):
            raise input_validation.ValidationError(
                input_validation.NON_FINITE, "defectSqrtAreasPaste",
                f"defect size {p!r} is not a finite number", {"token": p})
        if v > 0:
            out.append(v)
    return out


def murakami_fatigue_limit_MPa(sqrt_area_um: float, hardness_HV: float, location: str = "internal") -> float:
    """Murakami sigma_w = C (HV + 120) / sqrt(area)^(1/6) [MPa] (constants in murakami_constants).

    Non-positive / non-finite sqrt_area or HV, or an unknown location, raise input_validation.ValidationError."""
    return murakami_constants.murakami_sqrt_area_limit_MPa(sqrt_area_um, hardness_HV, location)


def gumbel_block_maxima(maxima: List[float], *, block_volume: float, target_volume: float,
                        target_probability: float) -> Dict[str, float]:
    """Method-of-moments Gumbel fit of comparable independent block maxima and the target-volume quantile.

    x = mu - beta ln(-ln(p^(V0/V))): the value not exceeded by the largest defect of the target volume with
    probability p, for n = V/V0 independent equivalent blocks. Raises ValueError on an inadmissible design."""
    values = [float(x) for x in maxima]
    if len(values) < 3:
        raise ValueError("at least three block maxima are needed for the two-moment fit")
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError("block maxima must be finite and positive")
    if not (math.isfinite(block_volume) and block_volume > 0 and math.isfinite(target_volume)
            and target_volume >= block_volume):
        raise ValueError("block and target volumes must be finite, positive and target >= block")
    if not (math.isfinite(target_probability) and 0 < target_probability < 1):
        raise ValueError("the target probability must lie strictly between 0 and 1")
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    if not variance > 0:
        raise ValueError("zero empirical variance: no Gumbel scale can be formed")
    std = math.sqrt(variance)
    beta = std * math.sqrt(6.0) / math.pi
    mu = mean - EULER_GAMMA * beta
    blocks = target_volume / block_volume
    per_block = target_probability ** (1.0 / blocks)
    x = mu - beta * math.log(-math.log(per_block))
    if not (math.isfinite(x) and x > 0):
        raise ValueError("the fitted target-volume quantile is not a positive size")
    return {"n": n, "mu_um": mu, "beta_um": beta, "mean_um": mean, "std_um": std, "blocks": blocks,
            "perBlockProbability": per_block, "quantile_um": x}


# --- request reading ---------------------------------------------------------------------------------------------

def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    out = float(value)
    return out if math.isfinite(out) else None


def _choice(value: Any, allowed) -> Optional[str]:
    return value if isinstance(value, str) and value in allowed else None


def _builder():
    from lpbf_solidification_estimates import Builder
    return Builder(MODEL_ID)


def _warn(code: str, detail: str) -> Dict[str, str]:
    from lpbf_solidification_estimates import _warn as warn
    return warn(code, detail)


def _record(kind: str, source_id: str, **kw) -> Dict[str, Any]:
    from lpbf_solidification_estimates import _record as record
    return record(kind, source_id, **kw)


def _fmt(value: float, digits: int = 2) -> str:
    """Reduced-precision display text without exponent notation for ordinary magnitudes (370, not 3.7e+02)."""
    if value == 0:
        return "0"
    rounded = float(f"{value:.{digits}g}")
    return f"{rounded:.{digits}g}" if abs(rounded) < 1e-3 or abs(rounded) >= 1e6 else f"{rounded:f}".rstrip("0").rstrip(".")


MISSING_LABELS = {"defectSqrtArea_um": "defect square-root area", "defectLocation": "defect location (surface or internal)",
                  "hardness_HV": "Vickers hardness", "defectEvidence": "whether the defect size is measured or an assumed "
                  "scenario", "hardnessEvidence": "whether the hardness is measured or an assumed scenario"}


def _size_warnings(alloy: Optional[str], s: float, orientation: Optional[str]) -> List[Dict[str, str]]:
    """A1.4 quantitative size-domain comparison with the named source context; never a merged universal range."""
    support = SIZE_SUPPORT.get(alloy or "")
    if support is None:
        return [_warn("domain-extrapolation", "Size-domain support is not established for this alloy and state. "
                                              f"The supplied size is {_fmt(s, 3)} micrometres.")]
    keys = [orientation] if orientation in support else list(support)
    out = []
    for key in keys:
        lo, hi = support[key]
        if not lo <= s <= hi:
            out.append(_warn("domain-extrapolation", f"The supplied size is {_fmt(s, 3)} micrometres. The cited "
                             f"radlof2020 EBM Ti-6Al-4V {key} specimen study reports {lo:g} to {hi:g} micrometres. "
                             "This is a size-domain extrapolation."))
    return out


def evaluate_murakami_block(
    defect_sqrt_areas_um: Optional[List[float]] = None,
    hardness_HV: Optional[float] = None,
    ct_detection_threshold_um: Optional[float] = None,
    alloy_id: Optional[str] = None,
    defect_paste: Optional[str] = None,
    scenario: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Group 7 block: F1 threshold scenario, F2 block-maxima statistic and the observed maximum, F3 CT echo.

    ``scenario`` carries the explicit choices (defectSqrtArea_um, defectEvidence, defectLocation, hardnessEvidence,
    loadRatio, cycleTarget, specimenOrientation, defectIsLongCrack, defectSampling, ctDetectionMethod). There is no
    default hardness, size, location, evidence kind or cycle target."""
    sc = dict(scenario or {})
    defects = list(defect_sqrt_areas_um or [])
    if not defects and defect_paste:
        defects = parse_defect_sqrt_areas_text(defect_paste)
    for v in defects:
        if _num(v) is None or float(v) <= 0:
            raise input_validation.ValidationError(input_validation.OUT_OF_RANGE, "defectSqrtAreas_um",
                                                   "defect sizes must be finite and positive", {"value": v})
    single = _num(sc.get("defectSqrtArea_um"))
    if sc.get("defectSqrtArea_um") is not None and (single is None or single <= 0):
        raise input_validation.ValidationError(input_validation.OUT_OF_RANGE, "defectSqrtArea_um",
                                               "the defect size must be finite and positive", {})
    hv = _num(hardness_HV)
    if hardness_HV is not None and (hv is None or hv <= 0):
        raise input_validation.ValidationError(input_validation.OUT_OF_RANGE, "hardness_HV",
                                               "hardness must be finite and positive", {})
    location = _choice(sc.get("defectLocation"), LOCATIONS)
    size_evidence = _choice(sc.get("defectEvidence"), EVIDENCE)
    hv_evidence = _choice(sc.get("hardnessEvidence"), EVIDENCE)
    orientation = _choice(sc.get("specimenOrientation"), ("vertical", "horizontal"))
    load_ratio = _num(sc.get("loadRatio"))
    cycle_target = _num(sc.get("cycleTarget"))
    long_crack = sc.get("defectIsLongCrack") is True

    observed = None
    if defects:
        observed = {"value_um": max(float(x) for x in defects), "n": len(defects),
                    "label": "observed in supplied data", "evidence": size_evidence,
                    "note": "Largest supplied value. It is not a fitted population extreme or a part-wide maximum."}
    if single is not None:
        s, s_basis = single, "selected defect"
    elif observed is not None:
        s, s_basis = observed["value_um"], "largest supplied defect"
    else:
        s, s_basis = None, None

    b = _builder()
    missing = []
    if s is None:
        missing.append("defectSqrtArea_um")
    if location is None:
        missing.append("defectLocation")
    if hv is None:
        missing.append("hardness_HV")
    if s is not None and size_evidence is None:
        missing.append("defectEvidence")
    if hv is not None and hv_evidence is None:
        missing.append("hardnessEvidence")

    def user(name, value, unit, evidence, what):
        scope = (f"{what} {value:g} {unit}, " + ("assumed scenario typed by the user" if evidence == "assumed-scenario"
                                                 else "measured value supplied by the user"))
        b.add_input(name, _record("userInput", f"user:{name}:{float(value).hex()}", status="inRange",
                                  declaration="request", scope=scope, default_value=value))

    b.add_input("murakamiLaw", _record(
        "sourceModelAssumption", "murakami-sqrt-area-law", status="extrapolated",
        locator="Murakami and Endo 1994, doi 10.1016/0142-1123(94)90001-9 (lineage); C 1.43 surface (Uematsu 2021 "
                "Eq. 1), 1.56 internal (Materials 14 5315 Eq. 1), HV offset 120, exponent 1/6",
        scope="steel-derived small-defect law, R = -1 threshold amplitude; applied to AM alloys as a transfer"))
    if s is not None and size_evidence is not None:
        user("defectSqrtArea", s, "um", size_evidence, f"projected sqrt(area), {s_basis},")
    if hv is not None and hv_evidence is not None:
        user("hardness", hv, "HV", hv_evidence, "Vickers hardness")
    depends = ["murakamiLaw"] + (["defectSqrtArea"] if "defectSqrtArea" in b.inputs else []) + (
        ["hardness"] if "hardness" in b.inputs else [])
    refusal_text = None
    params: Dict[str, Any] = {}
    code = "missing-source-constant"
    if missing:
        refusal_text = MISSING_TEXT + " Missing: " + "; ".join(MISSING_LABELS[m] for m in missing) + "."
        params = {"missing": ", ".join(missing)}
    elif long_crack:
        refusal_text, code = IDENTIFIED_LONG_CRACK_TEXT, "outside-source-model-domain"
    elif s >= SHORT_CRACK_LIMIT_UM:
        refusal_text, code = LONG_CRACK_TEXT.format(s=_fmt(s, 4)), "outside-source-model-domain"
    elif load_ratio is not None and load_ratio != -1.0:
        refusal_text, code = LOAD_RATIO_TEXT.format(r=_fmt(load_ratio, 3)), "outside-source-model-domain"
    if refusal_text is not None:
        parent = "defectSqrtArea" if "defectSqrtArea" in b.inputs else "murakamiLaw"
        b.no_value("fatigueThreshold", "murakami-threshold-stress-amplitude", code, parent=parent,
                   depends_on=depends, text=refusal_text, params=params)
        value_MPa = None
    else:
        value_MPa = murakami_fatigue_limit_MPa(s, hv, location)
        own = [_warn("alloy-family-transfer", "Murakami's small-defect law was derived for steels; it is "
                                              f"applied to {ALLOY_NAMES.get(alloy_id or '', 'this alloy')} as a "
                                              "transfer"),
               _warn("domain-extrapolation", TRANSFER.get(alloy_id or "", "No application of this law to the "
                                                                          "selected alloy is cited."))]
        own += _size_warnings(alloy_id, s, orientation)
        kinds = {size_evidence, hv_evidence}
        inputs_text = ("Measured inputs." if kinds == {"measured"} else "Assumed defect scenario." if kinds ==
                       {"assumed-scenario"} else "Mixed measured and assumed inputs.")
        article = "an internal" if location == "internal" else "a surface"
        text = (f"{TIER2}: about {_fmt(value_MPa)} MPa fully reversed stress amplitude for {article} defect with "
                f"projected square-root area {_fmt(s, 3)} micrometres and hardness {_fmt(hv, 3)} HV. This is a "
                "defect-conditioned Murakami screening estimate for an R = -1 threshold scenario. It is not a fatigue "
                f"strength at a stated cycle count and not an infinite-life endurance limit. {inputs_text} "
                f"{TRANSFER.get(alloy_id or '', '')} {UNKNOWN}").replace("  ", " ")
        sources = [SRC_UEMATSU if location == "surface" else SRC_TI_INTERNAL, SRC_RADLOF, SRC_MACHADO]
        if alloy_id == "alsi10mg":
            sources.append(SRC_STRAUSS)
        b.value("fatigueThreshold", "murakami-threshold-stress-amplitude", value_MPa * 1e6, depends_on=depends,
                sources=sources, own_warnings=own, explanation=text,
                construction="Murakami sqrt(area) law at the supplied size and hardness; no interval.",
                extra_validity={"defectLocation": location, "loadRatio": -1.0, "sqrtAreaBasis": s_basis})

    # F2: block maxima only.
    sampling = sc.get("defectSampling") if isinstance(sc.get("defectSampling"), dict) else None
    gumbel = None
    gumbel_text = GUMBEL_TEXT
    if sampling and sampling.get("design") == GUMBEL_DESIGN and defects:
        try:
            gumbel = gumbel_block_maxima(defects, block_volume=_num(sampling.get("blockVolume_mm3")) or float("nan"),
                                         target_volume=_num(sampling.get("targetVolume_mm3")) or float("nan"),
                                         target_probability=_num(sampling.get("targetProbability")) or float("nan"))
        except ValueError as exc:
            gumbel_text = f"{GUMBEL_TEXT} {str(exc).capitalize()}."
    b.add_input("gumbelModel", _record("sourceModelAssumption", "gumbel-type-i-maximum", status="extrapolated",
                                       locator=SRC_NIST_GUMBEL["locator"],
                                       scope="statistical sampling transfer to the target volume"))
    if gumbel is not None and size_evidence is None:
        gumbel, gumbel_text = None, GUMBEL_TEXT + " State whether the block maxima are measured or an assumed scenario."
    if gumbel is not None:
        b.add_input("blockMaxima", _record("userInput", f"user:block-maxima:{len(defects)}", status="inRange",
                                           declaration="request", scope=(
                                               f"{len(defects)} block maxima, block {sampling['blockVolume_mm3']:g} "
                                               f"mm3, target {sampling['targetVolume_mm3']:g} mm3, p "
                                               f"{sampling['targetProbability']:g}; "
                                               + ("measured" if size_evidence == "measured" else "assumed scenario"))))
        x = gumbel["quantile_um"]
        b.value("gumbelLargest", "gumbel-characteristic-largest-defect", x * 1e-6,
                depends_on=("gumbelModel", "blockMaxima"), sources=[SRC_NIST_GUMBEL],
                own_warnings=[_warn("domain-extrapolation", f"Extrapolated from {gumbel['n']} block maxima to "
                                                            f"{gumbel['blocks']:.3g} target blocks")],
                explanation=(f"{TIER2}: the largest defect in the target volume is about {_fmt(x)} micrometres "
                             f"sqrt(area) at probability {sampling['targetProbability']:g} from a Gumbel fit to "
                             f"{gumbel['n']} block maxima. The fit has only two moments and does not establish tail "
                             f"adequacy. {UNKNOWN}"),
                construction="Method-of-moments Gumbel fit; quantile at p^(V0/V); no interval.",
                extra_validity={"fit": gumbel})
    else:
        b.no_value("gumbelLargest", "gumbel-characteristic-largest-defect", "missing-source-constant",
                   parent="gumbelModel", depends_on=("gumbelModel",), text=gumbel_text)

    container = qe.container(b.quantities, input_provenance=b.inputs, schema=qe.ENVELOPE_SCHEMA_V2)
    ct = (_num(ct_detection_threshold_um))
    ct_method = sc.get("ctDetectionMethod") if isinstance(sc.get("ctDetectionMethod"), str) and \
        sc.get("ctDetectionMethod").strip() else None
    status = ("screening_estimate" if value_MPa is not None else "data_not_supplied" if missing and s is None
              else "input_refused")
    return {
        "schema": SCHEMA,
        "status": status,
        **container,
        "fatigueLimit_MPa": value_MPa,
        "defectLocation": location,
        "missingInputs": missing,
        "scenarioEcho": {
            "defectSqrtArea_um": s, "defectSqrtAreaBasis": s_basis, "defectEvidence": size_evidence,
            "defectLocation": location, "hardness_HV": hv, "hardnessEvidence": hv_evidence, "loadRatio": -1.0
            if load_ratio is None else load_ratio, "specimenOrientation": orientation,
        },
        "cycleTarget": ({"requested": cycle_target, "value": None, "text": CYCLE_TEXT.format(n=f"{cycle_target:.3g}")}
                        if cycle_target is not None else None),
        "observedMaximum": observed,
        "ctDetectionThreshold": ({"value_um": ct, "method": ct_method, "label": "measured CT detection threshold "
                                  "(echo, no estimate tier)" if ct_method else "CT detection threshold supplied "
                                  "without a validation method", "text": None if ct_method else CT_MISSING_TEXT}
                                 if ct is not None else {"value_um": None, "method": None, "label": None,
                                                         "text": CT_MISSING_TEXT}),
        "ctDetectionThreshold_um": ct,
        "pasteHint": PASTE_HINT,
        "note": ("SCREENING ONLY. Murakami sqrt(area) threshold scenario; not a certified allowable and not a "
                 "fatigue life."),
        "references": [
            "Murakami Y., Metal Fatigue: Effects of Small Defects and Nonmetallic Inclusions",
            "NIST/SEMATECH e-Handbook, Extreme Value Type I distribution (block maxima)",
        ],
    }


QUALIFICATION_BY_ALLOY = {
    "ti6al4v": {
        "standards": ["AMS 4999 / ASTM F2924 (Ti-6Al-4V LPBF)", "ASTM F3001 (ELI)", "AMS 7003 (process)"],
        "oContentLimit_wt_pct": 0.20,
        "couponPlan": ["0° tensile", "90° tensile", "density Archimedes ASTM B962", "CT porosity"],
    },
    "ss316l": {
        "standards": ["ASTM F3184", "ASTM F3303 (LPBF process)", "AMS 7003"],
        "oContentLimit_wt_pct": None,
        "couponPlan": ["0° tensile", "90° tensile", "density", "intergranular corrosion screen"],
    },
    "alsi10mg": {
        "standards": ["AMS 4215 / ASTM F3318", "ASTM F3303", "AMS 7003"],
        "oContentLimit_wt_pct": None,
        "couponPlan": ["0° tensile", "90° tensile", "density", "HIP vs as-built cohort"],
    },
    "in718": {
        "standards": ["AMS 5662 / ASTM F3055", "AMS 7003", "AMS 7032 (machine qualification context)"],
        "oContentLimit_wt_pct": None,
        "couponPlan": ["0° tensile", "90° tensile", "STA cohort", "density", "CT"],
    },
}


def build_qualification_block(alloy_id: str, input_hash: str, git_sha: Optional[str] = None) -> Dict[str, Any]:
    tmpl = QUALIFICATION_BY_ALLOY.get(alloy_id, QUALIFICATION_BY_ALLOY["in718"])
    return {
        "status": "not_executed",
        "screeningOnly": True,
        "alloyId": alloy_id,
        "standards": tmpl["standards"],
        "oContentLimit_wt_pct": tmpl["oContentLimit_wt_pct"],
        "couponPlan": tmpl["couponPlan"],
        "traceability": {
            "inputHash": input_hash,
            "gitSha": git_sha,
            "note": "Hash + SHA for report binding; not a digital signature / CoC.",
        },
        "note": (
            "SCREENING ONLY — standards listed for traceability. Protocol rows are Not executed; "
            "not a flight / MMPDS allowable release."
        ),
    }
