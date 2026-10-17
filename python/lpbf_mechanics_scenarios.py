"""Group 2 explicit mechanics scenarios (SPEC_engine_estimates_2026-10-17 group 2 with Amendment 1 A1.2 and A1.3).

M1  Constrained-bar thermal-cycle scenario: a slender, fully fixed, small-strain bar with constant E, alpha and ideal
    plasticity at yield sy goes through the declared solid-state cycle Tref -> Tpeak -> Tref. An incremental return
    mapping (Bower, Applied Mechanics of Solids 3.2.2 and 3.7) gives the final axial stress; for this cycle it equals
    min(sy, max(0, E alpha dT - sy)). The output carries ``saturatedAtYield`` (final |sigma| reaches the supplied
    return-temperature yield) and the mandatory upper-bound scope sentence. It is not a residual-stress field of a
    part and never fills defectDiagnostics.effectiveResidualStress_MPa.
M2  Released cantilever with an as-built-then-released EFFECTIVE inherent-strain profile from matched-build
    calibration or an explicit user scenario (A1.2). Never derived from M1. Rectangular section, constant E:
    eps_bar = (1/H) int eps* dz, kappa = (12/H^3) int z eps* dz, sigma = E (eps_bar + kappa z - eps*),
    tip deflection = kappa L^2 / 2 (z up from the centroid, positive deflection towards +z). Gates: declared
    small-rotation threshold, elastic release (|sigma| below the supplied yield), positive geometry, finite strains.
    The observable is new ("tip deflection divided by thickness"); the legacy distortionIndex stays unavailable.

Every input is typed by the user (no alloy constant, yield or profile default exists); every value is Tier 2.
Nothing here feeds the Build Job verdict, the recoater gate or the legacy stress/distortion keys.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional

import quantity_envelope as qe

MODEL_ID = "mechanics-scenarios-v1"
RETURN_STEPS = 400
SATURATION_RTOL = 1e-9
SLENDER_WARNING_RATIO = 10.0
EVIDENCE = ("measured", "literature", "assumed-scenario")
PROFILE_EVIDENCE = ("matched-build-calibration", "assumed-effective-profile-scenario")
CALIBRATION_KEYS = ("buildId", "machine", "alloyState", "orientation", "supportRestraint", "depositionHistory",
                    "referenceGeometry", "releaseSequence")

SRC_BOWER = qe.source_ref("bower-solids", "A. F. Bower, Applied Mechanics of Solids, open author text sections 3.2.2 "
                          "(thermoelastic strain) and 3.7.2, 3.7.5-3.7.8 (yield, flow, return mapping)", "primary-read")
SRC_BEAM = qe.source_ref("beam-release", "Elastic section release of a rectangular cantilever: zero axial force and "
                         "moment with beam compatibility (derived in SPEC_engine_estimates_2026-10-17 M2 and A1.2)",
                         "repository-attribution")
UNKNOWN = qe.UNCERTAINTY_STATEMENT_TIER2
TIER2 = qe.ESTIMATE_TIER_LABELS["Physics estimate"]
M1_SCOPE = ("In a fully constrained bar this equals the yield strength you supplied whenever thermal strain exceeds "
            "twice the yield strain. It is an upper-bound scenario, not a prediction of the part's stress.")
M1_SATURATED = "This result is saturated at the supplied return-temperature yield strength."
M1_REFUSAL = ("A residual-stress estimate needs a solid-state temperature history, restraint conditions and elastic, "
              "thermal-expansion and yield properties. Supply those inputs or select an explicit constrained-bar "
              "scenario.")
M1_MELT = ("The declared cycle reaches the solidus. A solid bar law cannot cross the melt interval: declare a "
           "mechanical activation temperature below the solidus and a solid-state cycle from it.")
M2_SCOPE = "This is a released-cantilever scenario. It does not predict distortion of your part geometry."
M2_UNIFORM = "Uniform eigenstrain giving zero curvature is not a prediction that LPBF parts do not bend."
M2_REFUSAL = ("Supply a matched-build effective inherent-strain profile or enter an explicit effective-profile "
              "scenario. A constrained-bar thermal cycle alone cannot determine cantilever bending.")
M2_GEOMETRY = ("Distortion needs the part geometry, support and release conditions, and an inherent-strain field or a "
               "thermal mechanical history. A laser parameter vector alone does not determine displacement.")
M2_ROTATION = ("The released beam rotates more than the declared small-rotation limit. A large-deflection model is "
               "needed for this profile.")
M2_PLASTIC = ("The release stress reaches the supplied yield strength. An elastoplastic release model is needed for "
              "this profile.")
M2_CALIBRATION = ("A matched-build calibration profile needs its build, machine, alloy state, orientation, support "
                  "restraint, deposition history, reference geometry and release sequence. Missing: {missing}. Enter "
                  "the profile as an explicit effective-profile scenario instead if these are not known.")


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    out = float(value)
    return out if math.isfinite(out) else None


def _sig(value: float, digits: int = 2) -> str:
    if value == 0:
        return "0"
    rounded = float(f"{value:.{digits}g}")
    return f"{rounded:.{digits}g}" if abs(rounded) < 1e-3 or abs(rounded) >= 1e6 else f"{rounded:f}".rstrip("0").rstrip(".")


# --- M1 -------------------------------------------------------------------------------------------------------------

def constrained_bar_cycle(E: float, alpha: float, sy: float, dT: float, steps: int = RETURN_STEPS) -> Dict[str, Any]:
    """Incremental elastic-predictor / plastic-corrector of the fully fixed bar (eps_tot = 0) over Tref -> +dT -> Tref.

    Returns final stress [Pa], plastic strain, whether yielding occurred and the hot-state stress."""
    if not (E > 0 and sy > 0 and alpha > 0 and dT > 0):
        raise ValueError("nonphysical-input")
    path = [dT * i / steps for i in range(steps + 1)] + [dT * (steps - i) / steps for i in range(1, steps + 1)]
    eps_p, sigma, yielded, hot = 0.0, 0.0, False, None
    for k, theta in enumerate(path):
        trial = E * (0.0 - alpha * theta - eps_p)
        if abs(trial) <= sy:
            sigma = trial
        else:
            sigma = math.copysign(sy, trial)
            eps_p = -alpha * theta - sigma / E
            yielded = True
        if k == steps:
            hot = sigma
    return {"stress_Pa": sigma, "plasticStrain": eps_p, "yielded": yielded, "hotStress_Pa": hot}


def m1_closed_form(E: float, alpha: float, sy: float, dT: float) -> float:
    return min(sy, max(0.0, E * alpha * dT - sy))


# --- M2 -------------------------------------------------------------------------------------------------------------

def section_release(H: float, segments: List[Mapping[str, float]], E: float) -> Dict[str, float]:
    """Exact section integrals of a piecewise-constant profile; segments give fractions of H from the bottom."""
    eps_int = first = 0.0
    for seg in segments:
        z1, z2 = (seg["from"] - 0.5) * H, (seg["to"] - 0.5) * H
        eps_int += seg["strain"] * (z2 - z1)
        first += seg["strain"] * (z2 * z2 - z1 * z1) / 2.0
    eps_bar = eps_int / H
    kappa = 12.0 / H ** 3 * first
    stresses = []
    for seg in segments:
        for frac in (seg["from"], seg["to"]):
            z = (frac - 0.5) * H
            stresses.append(E * (eps_bar + kappa * z - seg["strain"]))
    return {"meanStrain": eps_bar, "curvature_1_m": kappa, "maxReleaseStress_Pa": max(abs(s) for s in stresses)}


def _segments(raw: Any) -> Optional[List[Dict[str, float]]]:
    if not isinstance(raw, list) or not raw:
        return None
    out = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        a, b, e = _num(item.get("from")), _num(item.get("to")), _num(item.get("strain"))
        if a is None or b is None or e is None:
            return None
        out.append({"from": a, "to": b, "strain": e})
    out.sort(key=lambda s: s["from"])
    if abs(out[0]["from"]) > 1e-12 or abs(out[-1]["to"] - 1.0) > 1e-12:
        return None
    for left, right in zip(out, out[1:]):
        if abs(left["to"] - right["from"]) > 1e-12:
            return None
    if any(not s["to"] > s["from"] for s in out):
        return None
    return out


# --- assembly -------------------------------------------------------------------------------------------------------

def _builder():
    from lpbf_solidification_estimates import Builder
    return Builder(MODEL_ID)


def _rec(kind, sid, **kw):
    from lpbf_solidification_estimates import _record
    return _record(kind, sid, **kw)


def _warn(code, detail):
    from lpbf_solidification_estimates import _warn as warn
    return warn(code, detail)


def _user_input(b, name, value, unit, evidence, what):
    scope = f"{what} {value:g} {unit}, " + {"measured": "measured value supplied by the user",
                                            "literature": "literature value entered by the user",
                                            "assumed-scenario": "assumed scenario typed by the user"}[evidence]
    b.add_input(name, _rec("userInput", f"user:{name}:{float(value).hex()}", status="inRange", declaration="request",
                           scope=scope, default_value=value))


def evaluate_mechanics(scenario: Optional[Mapping[str, Any]], *, alloy_id: Optional[str],
                       solidus_C: Optional[float]) -> Dict[str, Any]:
    """v2 container with barStress (M1), tipDeflection and tipDeflectionOverThickness (M2)."""
    sc = dict(scenario or {})
    b = _builder()
    b.add_input("barModel", _rec("sourceModelAssumption", "m1-constrained-bar", status="extrapolated",
                                 locator=SRC_BOWER["locator"],
                                 scope="fully fixed slender bar, constant E and alpha, ideal plasticity, one declared "
                                       "solid-state cycle; three-dimensional restraint and relaxation omitted"))
    b.add_input("beamModel", _rec("sourceModelAssumption", "m2-released-cantilever", status="extrapolated",
                                  locator=SRC_BEAM["locator"],
                                  scope="rectangular released cantilever, constant E, elastic small-rotation release"))
    out_extra: Dict[str, Any] = {}
    _m1(b, sc.get("bar") if isinstance(sc.get("bar"), dict) else None, solidus_C, out_extra)
    _m2(b, sc.get("cantilever") if isinstance(sc.get("cantilever"), dict) else None, out_extra)
    out = qe.container(b.quantities, input_provenance=b.inputs, schema=qe.ENVELOPE_SCHEMA_V2)
    statuses = [q["status"] for q in b.quantities.values()]
    out.update(modelId=MODEL_ID, status=("computed" if all(s == "computed" for s in statuses) else "partial"
                                         if any(s == "computed" for s in statuses) else "unavailable"),
               usedForBuildJobVerdict=False, legacyKeysUnchanged=["defectDiagnostics.effectiveResidualStress_MPa",
                                                                   "distortionIndex"], **out_extra)
    return out


def _m1(b, bar, solidus_C, extra) -> None:
    name, definition = "barStress", "constrained-bar-axial-stress"
    fields = (("elasticModulus", "elasticModulus_GPa", "GPa", 1e9), ("thermalExpansion", "thermalExpansion_per_K",
              "1/K", 1.0), ("yieldStrength", "returnYield_MPa", "MPa", 1e6))
    values, missing = {}, []
    if bar is None:
        b.no_value(name, definition, "not-requested", parent="barModel", depends_on=("barModel",), text=M1_REFUSAL,
                   status="not-requested")
        return
    for key, field, unit, scale in fields:
        v, ev = _num(bar.get(field)), bar.get(field.split("_")[0] + "Evidence")
        if v is None or v <= 0 or ev not in EVIDENCE:
            missing.append(field)
            continue
        _user_input(b, key, v, unit, ev, key)
        values[key] = v * scale
    t_ref, t_peak = _num(bar.get("returnTemperature_C")), _num(bar.get("peakTemperature_C"))
    depends = ["barModel"] + [k for k in ("elasticModulus", "thermalExpansion", "yieldStrength") if k in values]
    if t_ref is None or t_peak is None or not t_peak > t_ref:
        missing.append("returnTemperature_C < peakTemperature_C")
    else:
        b.add_input("thermalCycle", _rec("userInput", f"user:cycle:{t_ref!r}:{t_peak!r}", status="inRange",
                                         declaration="request",
                                         scope=f"declared solid-state cycle {t_ref:g} C to {t_peak:g} C and back, "
                                               "fully fixed ends, stress-free start (scenario)"))
        depends.append("thermalCycle")
    if missing:
        b.no_value(name, definition, "missing-source-constant", parent="barModel", depends_on=depends,
                   text=M1_REFUSAL + " Missing: " + ", ".join(missing) + ".", params={"missing": ", ".join(missing)})
        return
    if solidus_C is not None and t_peak >= solidus_C:
        b.no_value(name, definition, "outside-source-model-domain", parent="thermalCycle", depends_on=depends,
                   text=M1_MELT)
        return
    E, alpha, sy = values["elasticModulus"], values["thermalExpansion"], values["yieldStrength"]
    result = constrained_bar_cycle(E, alpha, sy, t_peak - t_ref)
    sigma = result["stress_Pa"]
    saturated = abs(abs(sigma) - sy) <= SATURATION_RTOL * sy
    extra["barScenario"] = {"saturatedAtYield": saturated, "returnYield_MPa": sy / 1e6,
                            "returnYieldEvidence": bar.get("returnYieldEvidence"),
                            "constraint": "fully fixed bar, ends restrained, not released",
                            "thermalStrainOverYieldStrain": E * alpha * (t_peak - t_ref) / sy,
                            "hotStress_MPa": result["hotStress_Pa"] / 1e6, "yielded": result["yielded"]}
    text = (f"{TIER2}: about {_sig(sigma / 1e6)} MPa axial stress after the declared thermal cycle in a fully "
            f"constrained bar. The model uses the supplied inputs and ideal plasticity. It omits three-dimensional "
            "restraint, relaxation, phase-transformation strain and temperature-dependent properties. The bar remains "
            f"constrained. {M1_SCOPE}" + (f" {M1_SATURATED}" if saturated else "") + f" {UNKNOWN}")
    b.value(name, definition, sigma, depends_on=depends, sources=[SRC_BOWER],
            own_warnings=[_warn("domain-extrapolation", "Constant-property ideal-plastic bar with full axial restraint; "
                                                        "not a part residual-stress field")],
            explanation=text, construction="Incremental return mapping over the declared cycle; no interval.",
            extra_validity={"saturatedAtYield": saturated, "constraint": "fully fixed"})


def _m2(b, beam, extra) -> None:
    names = (("tipDeflection", "released-cantilever-tip-deflection"),
             ("tipDeflectionOverThickness", "tip-deflection-over-thickness"))
    if beam is None:
        for name, definition in names:
            b.no_value(name, definition, "not-requested", parent="beamModel", depends_on=("beamModel",),
                       text=M2_REFUSAL, status="not-requested")
        return

    def refuse(code, text, parent="beamModel", depends=("beamModel",)):
        for name, definition in names:
            b.no_value(name, definition, code, parent=parent, depends_on=depends, text=text)

    provenance = beam.get("profileEvidence")
    if beam.get("profileSource") == "m1-derived" or provenance == "m1-derived":
        refuse("missing-source-bound-model", M2_REFUSAL)
        return
    if provenance not in PROFILE_EVIDENCE:
        refuse("missing-source-constant", M2_REFUSAL)
        return
    if provenance == "matched-build-calibration":
        identity = beam.get("calibrationIdentity") if isinstance(beam.get("calibrationIdentity"), dict) else {}
        missing = [k for k in CALIBRATION_KEYS if not (isinstance(identity.get(k), str) and identity[k].strip())]
        if missing:
            refuse("missing-source-constant", M2_CALIBRATION.format(missing=", ".join(missing)))
            return
    L, H = _num(beam.get("length_mm")), _num(beam.get("thickness_mm"))
    E, sy = _num(beam.get("elasticModulus_GPa")), _num(beam.get("releaseYield_MPa"))
    limit = _num(beam.get("maxRotation_rad"))
    segments = _segments(beam.get("profile"))
    if None in (L, H, E, sy, limit) or min(L, H, E, sy, limit) <= 0 or segments is None:
        refuse("missing-source-constant", M2_GEOMETRY + " Also supply the elastic modulus, the yield strength for the "
               "elastic-release check, a small-rotation limit and a profile covering the full thickness.")
        return
    L, H, E, sy = L * 1e-3, H * 1e-3, E * 1e9, sy * 1e6
    b.add_input("beamGeometry", _rec("userInput", f"user:beam:{L!r}:{H!r}", status="inRange", declaration="request",
                                     scope=f"rectangular cantilever L {L * 1e3:g} mm, H {H * 1e3:g} mm, one root, "
                                           "released (user geometry)"))
    b.add_input("beamModulus", _rec("userInput", f"user:beam-E:{E!r}", status="inRange", declaration="request",
                                    scope=f"elastic modulus {E / 1e9:g} GPa entered by the user", default_value=E))
    label = ("matched-build calibration profile" if provenance == "matched-build-calibration"
             else "assumed effective-profile scenario typed by the user")
    b.add_input("inherentStrainProfile", _rec("userInput", f"user:profile:{len(segments)}", status="inRange",
                                              declaration="request",
                                              scope=f"{label}: {len(segments)} piecewise-constant segments, z up from "
                                                    "the bottom face, positive strain is expansion; never derived "
                                                    "from the constrained-bar scenario"))
    depends = ("beamModel", "beamGeometry", "beamModulus", "inherentStrainProfile")
    release = section_release(H, segments, E)
    kappa = release["curvature_1_m"]
    rotation = abs(kappa) * L
    extra["cantileverScenario"] = {**release, "rotation_rad": rotation, "rotationLimit_rad": limit,
                                   "profileEvidence": provenance, "segments": segments}
    if rotation > limit:
        refuse("outside-source-model-domain", M2_ROTATION, parent="inherentStrainProfile", depends=depends)
        return
    if release["maxReleaseStress_Pa"] >= sy:
        refuse("outside-source-model-domain", M2_PLASTIC, parent="inherentStrainProfile", depends=depends)
        return
    tip = kappa * L * L / 2.0
    uniform = len({s["strain"] for s in segments}) == 1
    own = [_warn("domain-extrapolation", "Released-cantilever beam reduction with constant E; transferred to the "
                                         "selected alloy without an alloy-specific calibration")]
    if L / H < SLENDER_WARNING_RATIO:
        own.append(_warn("domain-extrapolation", f"L/H = {L / H:.3g} is below the declared slenderness screen of "
                                                 f"{SLENDER_WARNING_RATIO:g}; beam theory may be inaccurate"))
    tail = (f" {M2_UNIFORM}" if uniform else "") + f" {UNKNOWN}"
    b.value("tipDeflection", "released-cantilever-tip-deflection", tip, depends_on=depends, sources=[SRC_BEAM],
            own_warnings=own,
            explanation=(f"{TIER2}: about {_sig(tip * 1e3)} mm tip displacement for the selected cantilever and "
                         f"inherent-strain profile. {M2_SCOPE} The geometry, restraint and strain profile determine "
                         f"the result.{tail}"),
            construction="Exact section integrals of the piecewise profile; kappa L^2 / 2; no interval.",
            extra_validity={"curvature_1_m": kappa, "rotation_rad": rotation})
    b.value("tipDeflectionOverThickness", "tip-deflection-over-thickness", abs(tip) / H,
            depends_on=("tipDeflection", "beamGeometry"), sources=[SRC_BEAM],
            explanation=(f"{TIER2}: the tip deflection divided by thickness is about {_sig(abs(tip) / H)}. {M2_SCOPE}"
                         f"{tail}"),
            construction="abs(tip deflection) / H; a new observable, not the legacy distortionIndex.")
