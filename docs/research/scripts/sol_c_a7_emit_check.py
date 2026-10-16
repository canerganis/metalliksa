"""Research-only prospective A7 payload validator; never imported by served code."""
from __future__ import annotations

import argparse
import copy
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "python"))
from quantity_envelope import INPUT_KINDS, INPUT_STATUSES, REASON_CODES  # noqa: E402

WARNINGS = {
    "domain-extrapolation", "alloy-family-transfer", "low-peclet-tip-law",
    "nucleation-scenario-unresolved", "Ti-slope-closure", "binary-eutectic-omission",
    "equilibrium-limit-only", "microconstituent-not-phase", "km-source-fit-uncertainty",
    "km-quench-reference-only",
}
DOMAIN_WARNINGS = WARNINGS - {
    "nucleation-scenario-unresolved", "microconstituent-not-phase", "km-source-fit-uncertainty",
}
UNKNOWN = {"model-error", "input-interactions", "alloy-transfer-error", "source-parameter-uncertainty"}
UNKNOWN_TEXT = "Uncertainty is unknown and may be large. Calibrate to your machine for better accuracy."
CET_TEXT = ("N0 and activation undercooling are declared scenarios with Unresolved provenance. "
            "The model class may change substantially with these scenarios. " + UNKNOWN_TEXT)
# unit, basis, precision, value kind / exact members
DEFINITIONS = {
    "liquidus-front-thermal-gradient": ("K/m", None, 2, "positive"),
    "liquidus-front-normal-speed": ("m/s", None, 2, "positive"),
    "liquidus-front-cooling-rate": ("K/s", None, 2, "positive"),
    "liquidus-front-g-over-r": ("K*s/m^2", None, 2, "positive"),
    "pdas-correlation": ("m", None, 2, "positive"),
    "pdas-model-alternatives": ("m", None, 2, "alternatives"),
    "sdas": ("m", None, 2, "positive"),
    "planar-stability-index": ("1", None, 1, "nonnegative"),
    "equiaxed-envelope-fraction": ("1", "volume", 1, "fraction"),
    "km-alpha-m-fraction": ("1", "reaction-progress", 1, "fraction"),
    "terminal-equilibrium-phase-inventory": ("1", "mass", 1, ("alphaAl", "Si", "Mg2Si")),
    "scheil-microconstituent-inventory": ("1", "mass", 1, ("primaryAlphaAl", "eutecticConstituent")),
    "cet-class": ("1", None, 1, "category"),
}


def finite(x):
    return isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x)


def strings(x, *, nonempty=False):
    return (isinstance(x, list) and (bool(x) or not nonempty)
            and all(isinstance(s, str) and s.strip() for s in x) and len(x) == len(set(x)))


def range_problems(band, value, unit):
    errors = []
    keys = {"lower", "upper", "unit", "construction", "inputRanges", "armIds", "unknownComponents"}
    if not isinstance(band, dict) or set(band) != keys:
        return ["range object keys"]
    if band["unit"] != unit or band["construction"] not in ("ofat", "joint"):
        errors.append("range unit/construction")
    low, high = band["lower"], band["upper"]
    if isinstance(value, dict):
        if not (isinstance(low, dict) and isinstance(high, dict) and set(low) == set(high) == set(value)):
            errors.append("range members")
        else:
            for name, nominal in value.items():
                if not (finite(low[name]) and finite(high[name]) and low[name] <= nominal <= high[name]):
                    errors.append("range nominal containment")
    elif not (finite(value) and finite(low) and finite(high) and low <= value <= high):
        errors.append("range nominal containment")
    ranges = band["inputRanges"]
    if not isinstance(ranges, list) or not ranges:
        errors.append("range inputRanges")
    else:
        names = []
        for row in ranges:
            if not isinstance(row, dict) or set(row) != {"name", "unit", "nominal", "lower", "upper"}:
                errors.append("input range keys")
                continue
            names.append(row["name"])
            if not all(isinstance(row[k], str) and row[k].strip() for k in ("name", "unit")):
                errors.append("input range name/unit")
            if not (all(finite(row[k]) for k in ("lower", "nominal", "upper"))
                    and row["lower"] <= row["nominal"] <= row["upper"]):
                errors.append("input range bounds")
        if len(names) != len(set(str(n) for n in names)):
            errors.append("duplicate input range")
    if not strings(band["armIds"], nonempty=True):
        errors.append("range armIds")
    unknown = band["unknownComponents"]
    if not strings(unknown) or not set(unknown) <= UNKNOWN or "model-error" not in unknown:
        errors.append("range unknownComponents")
    if band["construction"] == "ofat" and "input-interactions" not in unknown:
        errors.append("OFAT omits interactions")
    return errors


def km_problems(q):
    ev, residual = q.get("evaluation"), q.get("residual")
    errors = []
    keys = {"ruleId", "preheat_K", "offset_K", "temperature_K", "time_s", "historyBracketIds",
            "timeInterpolation", "refinement"}
    if not isinstance(ev, dict) or set(ev) != keys:
        errors.append("KM evaluation keys")
    else:
        if ev["ruleId"] != "finite-25K-above-preheat-v1" or ev["timeInterpolation"] != "linear-in-temperature":
            errors.append("KM evaluation rule")
        if not (all(finite(ev[k]) and ev[k] > 0 for k in ("preheat_K", "offset_K", "temperature_K"))
                and ev["offset_K"] == 25 and math.isclose(ev["temperature_K"], ev["preheat_K"] + 25,
                                                         rel_tol=0, abs_tol=1e-9)):
            errors.append("KM evaluation temperature")
        if not finite(ev["time_s"]) or ev["time_s"] < 0:
            errors.append("KM evaluation time")
        if not strings(ev["historyBracketIds"]) or len(ev["historyBracketIds"]) != 2:
            errors.append("KM history bracket")
        ref = ev["refinement"]
        if not (isinstance(ref, dict) and set(ref) == {"status", "timeTolerance_s", "temperatureTolerance_K"}
                and ref["status"] == "refinement-passed"
                and all(finite(ref[k]) and ref[k] > 0 for k in ("timeTolerance_s", "temperatureTolerance_K"))):
            errors.append("KM refinement")
    if not (isinstance(residual, dict) and set(residual) == {"untransformedAsymptote", "beta0", "preExistingConstituent"}
            and all(finite(x) and 0 <= x <= 1 for x in residual.values())
            and math.isclose(q["value"] + residual["untransformedAsymptote"], residual["beta0"], abs_tol=1e-12)
            and math.isclose(residual["preExistingConstituent"], 1 - residual["beta0"], abs_tol=1e-12)):
        errors.append("KM progress conservation / residual naming")
    return errors


def validate(payload):
    """Return prospective-subset errors; base v1/source/path checks remain separate."""
    if not isinstance(payload, dict) or not isinstance(payload.get("quantities"), dict) or not isinstance(payload.get("inputProvenance"), dict):
        return ["payload maps"]
    quantities, inputs = payload["quantities"], payload["inputProvenance"]
    errors = []
    if set(quantities) & set(inputs):
        errors.append("duplicate input/quantity IDs")

    def closure(name, stack=()):
        if name in stack:
            errors.append("dependency cycle")
            return set(), False
        record = quantities.get(name, inputs.get(name))
        if not isinstance(record, dict):
            errors.append("missing dependency " + name)
            return set(), False
        warnings = set()
        if name in inputs:
            if record.get("kind") not in INPUT_KINDS or record.get("status") not in INPUT_STATUSES:
                errors.append("input kind/status " + name)
            if record.get("kind") == "alloyTransfer":
                warnings.add("alloy-family-transfer")
            if record.get("status") in ("extrapolated", "outOfRange"):
                warnings.add("domain-extrapolation")
        validity = record.get("validity")
        validity = validity if isinstance(validity, dict) else {}
        warning_rows = validity.get("domainWarnings")
        for item in warning_rows if isinstance(warning_rows, list) else []:
            if isinstance(item, dict) and isinstance(item.get("code"), str):
                warnings.add(item["code"])
        null_parent = name in quantities and record.get("value") is None
        deps = record.get("dependsOn", [])
        if not strings(deps):
            errors.append("dependency list " + name)
            return warnings, null_parent
        for dep in deps:
            inherited, null = closure(dep, stack + (name,))
            warnings |= inherited
            null_parent |= null
        return warnings, null_parent

    for name, q in quantities.items():
        at = lambda message: errors.append(name + ": " + message)
        if not isinstance(q, dict) or q.get("quantityDefinition") not in DEFINITIONS:
            at("unknown definition")
            continue
        unit, basis, precision, kind = DEFINITIONS[q["quantityDefinition"]]
        value = q.get("value")
        has = value is not None
        if q.get("unit") != unit:
            at("unit")
        if "fractionBasis" not in q or q["fractionBasis"] != (basis if has else None):
            at("fraction basis")
        if q.get("status") not in ("computed", "partial", "unavailable", "failed", "not-requested") or has != (q.get("status") in ("computed", "partial")):
            at("status/value")
        if not strings(q.get("dependsOn"), nonempty=True):
            at("dependsOn")
        validity = q.get("validity")
        if not isinstance(validity, dict):
            at("validity")
            continue
        tier = validity.get("estimateTier")
        if tier not in ("Estimated", "Physics estimate", "no-value") or has == (tier == "no-value"):
            at("tier/value")
        digits = validity.get("displaySignificantDigits")
        if digits != (precision if has else None) or (has and type(digits) is not int):
            at("display precision")
        warnings = validity.get("domainWarnings")
        if not isinstance(warnings, list):
            at("domainWarnings")
            warnings = []
        codes = set()
        for warning in warnings:
            if not (isinstance(warning, dict) and set(warning) == {"code", "detail"}
                    and isinstance(warning["code"], str) and warning["code"] in WARNINGS
                    and isinstance(warning["detail"], str) and warning["detail"].strip()):
                at("warning code/detail")
            else:
                codes.add(warning["code"])
        inherited, null_parent = closure(name)
        if has and null_parent:
            at("null dependency")
        if has and not inherited <= codes:
            at("inherited warning missing")
        if tier == "Estimated" and inherited & DOMAIN_WARNINGS:
            at("domain/transfer cannot be promoted")
        reasons = q.get("reasons")
        if not isinstance(reasons, list) or bool(reasons) == has:
            at("blocking reasons/value")
        else:
            for reason in reasons:
                if not isinstance(reason, dict) or not isinstance(reason.get("code"), str) or reason["code"] not in REASON_CODES:
                    at("blocking reason code")
        for field in ("estimateTier", "displaySignificantDigits", "domainWarnings", "estimateBand", "uncertaintyStatement"):
            if field not in validity:
                at("missing validity field " + field)
        band = validity.get("estimateBand")
        if tier == "Estimated":
            errors.extend(name + ": " + e for e in range_problems(band, value, unit))
        elif band is not None:
            at("band forbidden for this tier")
        sensitivity = validity.get("inputSensitivity")
        if sensitivity is not None:
            if tier != "Physics estimate":
                at("auxiliary sensitivity tier")
            errors.extend(name + ": " + e for e in range_problems(sensitivity, value, unit))
        uncertainty = q.get("uncertainty")
        if has:
            expected = ("model-alternatives" if kind == "alternatives" else
                        "parameter-sensitivity" if tier == "Estimated" else "not-quantified")
            if not (isinstance(uncertainty, dict) and set(uncertainty) == {"kind", "construction"}
                    and uncertainty["kind"] == expected and isinstance(uncertainty["construction"], str)
                    and uncertainty["construction"].strip()):
                at("uncertainty shape/kind")
            if q.get("sourceEvidenceKind") not in ("Literature estimate", "User input", "Unresolved"):
                at("value source label")
        elif uncertainty is not None or q.get("sourceEvidenceKind") is not None:
            at("null uncertainty/source")
        if validity.get("uncertaintyStatement") != (UNKNOWN_TEXT if tier == "Physics estimate" else None):
            at("uncertainty statement")
        if has and q["quantityDefinition"] in ("equiaxed-envelope-fraction", "cet-class"):
            if validity.get("nucleationScenarioNote") != CET_TEXT:
                at("missing/incorrect Unresolved nucleation scenario text")
        if has:
            if kind == "alternatives":
                if not (isinstance(value, dict) and set(value) == {"hunt", "kurzFisher"}
                        and all(finite(v) and v > 0 for v in value.values())):
                    at("PDAS positive model-alternative members")
                if tier != "Physics estimate":
                    at("PDAS alternatives are Tier 2 in this subset")
            elif isinstance(kind, tuple):
                if not (isinstance(value, dict) and set(value) == set(kind)
                        and all(finite(v) and 0 <= v <= 1 for v in value.values())
                        and math.isclose(sum(value.values()), 1, abs_tol=1e-12)):
                    at("fraction map members/conservation")
            elif kind == "category":
                if value not in ("columnar", "mixed", "equiaxed") or tier == "Estimated":
                    at("CET category")
            elif not (finite(value) and (value > 0 if kind == "positive" else value >= 0)
                      and (kind != "fraction" or value <= 1)):
                at("value domain")
            if q["quantityDefinition"] == "km-alpha-m-fraction" and finite(value):
                errors.extend(name + ": " + e for e in km_problems(q))
    return errors


def example(definition="liquidus-front-thermal-gradient", value=1e7, tier="Estimated"):
    unit, basis, precision, kind = DEFINITIONS[definition]
    band = {"lower": value * .8, "upper": value * 1.2, "unit": unit, "construction": "ofat",
            "inputRanges": [{"name": "absorptivity", "unit": "1", "nominal": .4, "lower": .2, "upper": .6}],
            "armIds": ["nominal", "absorptivity-low", "absorptivity-high"],
            "unknownComponents": ["model-error", "input-interactions"]} if finite(value) else None
    payload = {"inputProvenance": {"absorptivity": {"kind": "sourceDefault", "status": "inRange", "dependsOn": []}},
            "quantities": {"result": {"quantityDefinition": definition, "value": value, "unit": unit,
                "fractionBasis": basis, "status": "computed", "sourceEvidenceKind": "Literature estimate",
                "dependsOn": ["absorptivity"], "reasons": [],
                "uncertainty": {"kind": "model-alternatives" if kind == "alternatives" else
                                        "parameter-sensitivity" if tier == "Estimated" else "not-quantified",
                                "construction": "Executed declared input sweep" if tier == "Estimated" else "Unknown model uncertainty"},
                "validity": {"estimateTier": tier, "displaySignificantDigits": precision, "domainWarnings": [],
                             "estimateBand": band if tier == "Estimated" else None,
                             "uncertaintyStatement": UNKNOWN_TEXT if tier == "Physics estimate" else None}}}}
    if definition in ("equiaxed-envelope-fraction", "cet-class"):
        payload["quantities"]["result"]["validity"]["nucleationScenarioNote"] = CET_TEXT
    return payload


def check():
    count = 0

    def accept(p):
        nonlocal count
        assert not validate(p), validate(p)
        count += 1

    def reject(p, mutate):
        nonlocal count
        changed = copy.deepcopy(p)
        mutate(changed)
        assert changed != p, "mutation did not change actual payload"
        assert validate(changed), "mutated payload unexpectedly accepted"
        count += 1

    thermal = example()
    accept(thermal)
    for mutate in (
        lambda p: p["quantities"]["result"].pop("unit"),
        lambda p: p["quantities"]["result"]["validity"].update(displaySignificantDigits=3),
        lambda p: p["quantities"]["result"]["validity"].pop("estimateBand"),
        lambda p: p["quantities"]["result"]["validity"]["estimateBand"].update(inputRanges=[]),
        lambda p: p["quantities"]["result"]["validity"]["estimateBand"].update(armIds=[]),
        lambda p: p["quantities"]["result"]["validity"]["estimateBand"].update(unknownComponents=["model-error"]),
        lambda p: p["inputProvenance"]["absorptivity"].update(kind="alloyTransfer"),
        lambda p: p["inputProvenance"]["absorptivity"].update(status="outOfRange"),
        lambda p: p["quantities"]["result"].update(reasons=[{"code": "domain-extrapolation"}]),
        lambda p: p["quantities"]["result"]["validity"].update(domainWarnings=[{"code": "outside-source-model-domain", "detail": "bad"}]),
    ):
        reject(thermal, mutate)
    # Actual transitive parent graph, including a physical thermal-input transfer.
    inherited = example(tier="Physics estimate")
    q = inherited["quantities"]["result"]
    q["validity"]["domainWarnings"] = [{"code": "alloy-family-transfer", "detail": "thermal absorptivity family"}]
    inherited["inputProvenance"]["absorptivity"]["kind"] = "alloyTransfer"
    parent = copy.deepcopy(q)
    inherited["quantities"]["thermalParent"] = parent
    q["dependsOn"] = ["thermalParent"]
    q["validity"]["inputSensitivity"] = copy.deepcopy(thermal["quantities"]["result"]["validity"]["estimateBand"])
    accept(inherited)

    def launder(p):
        result = p["quantities"]["result"]
        result["validity"].update(estimateTier="Estimated", estimateBand=result["validity"].pop("inputSensitivity"), uncertaintyStatement=None)
        result["uncertainty"]["kind"] = "parameter-sensitivity"

    reject(inherited, launder)
    reject(inherited, lambda p: p["quantities"]["result"]["validity"].update(domainWarnings=[]))
    for definition, value in (
        ("pdas-correlation", 1e-6), ("sdas", 2e-6), ("planar-stability-index", 2.0),
        ("equiaxed-envelope-fraction", .1), ("cet-class", "mixed"),
        ("terminal-equilibrium-phase-inventory", {"alphaAl": .9, "Si": .095, "Mg2Si": .005}),
        ("scheil-microconstituent-inventory", {"primaryAlphaAl": .23, "eutecticConstituent": .77}),
    ):
        p = example(definition, value, "Physics estimate")
        accept(p)
        reject(p, lambda p: p["quantities"]["result"]["validity"].update(displaySignificantDigits=4))
        if DEFINITIONS[definition][1]:
            reject(p, lambda p: p["quantities"]["result"].pop("fractionBasis"))
        if definition in ("equiaxed-envelope-fraction", "cet-class"):
            reject(p, lambda p: p["quantities"]["result"]["validity"].pop("nucleationScenarioNote"))
            reject(p, lambda p: p["quantities"]["result"]["validity"].update(nucleationScenarioNote="Measured active N0"))
    alternatives = example("pdas-model-alternatives", {"hunt": 1e-6, "kurzFisher": 2e-6}, "Physics estimate")
    accept(alternatives)
    reject(alternatives, lambda p: p["quantities"]["result"]["uncertainty"].update(kind="not-quantified"))
    reject(alternatives, lambda p: p["quantities"]["result"].update(value={"hunt": 1e-6, "TiLaw": 2e-6}))
    reject(alternatives, lambda p: p["quantities"]["result"].update(value={"hunt": 0., "kurzFisher": 2e-6}))
    reject(alternatives, lambda p: p["quantities"]["result"].update(fractionBasis="mass"))

    def promote_alternatives(p):
        result = p["quantities"]["result"]
        band = copy.deepcopy(thermal["quantities"]["result"]["validity"]["estimateBand"])
        band.update(unit="m", lower={key: value * .8 for key, value in result["value"].items()},
                    upper={key: value * 1.2 for key, value in result["value"].items()})
        result["validity"].update(estimateTier="Estimated", estimateBand=band, uncertaintyStatement=None)

    reject(alternatives, promote_alternatives)
    phases = example("terminal-equilibrium-phase-inventory", {"alphaAl": .9, "Si": .095, "Mg2Si": .005}, "Physics estimate")
    reject(phases, lambda p: p["quantities"]["result"].update(value={"primaryAlphaAl": .23, "eutecticConstituent": .77}))
    km = example("km-alpha-m-fraction", .9, "Physics estimate")
    kmq = km["quantities"]["result"]
    kmq["evaluation"] = {"ruleId": "finite-25K-above-preheat-v1", "preheat_K": 298.15, "offset_K": 25,
                         "temperature_K": 323.15, "time_s": .01, "historyBracketIds": ["t20", "t21"],
                         "timeInterpolation": "linear-in-temperature", "refinement": {"status": "refinement-passed",
                         "timeTolerance_s": 1e-5, "temperatureTolerance_K": .1}}
    kmq["residual"] = {"untransformedAsymptote": .1, "beta0": 1., "preExistingConstituent": 0.}
    accept(km)
    reject(km, lambda p: p["quantities"]["result"]["evaluation"].update(ruleId="last-history-point"))
    reject(km, lambda p: p["quantities"]["result"]["evaluation"].update(temperature_K=298.15))
    reject(km, lambda p: p["quantities"]["result"]["residual"].update(beta=.1))
    reject(km, lambda p: p["quantities"]["result"]["residual"].update(untransformedAsymptote=.2))
    no = example()
    noq = no["quantities"]["result"]
    noq.update(value=None, status="unavailable", fractionBasis=None, sourceEvidenceKind=None, uncertainty=None,
               reasons=[{"code": "outside-source-model-domain", "params": {"detail": "below admitted dendrite scale"}}])
    noq["validity"].update(estimateTier="no-value", displaySignificantDigits=None, estimateBand=None, uncertaintyStatement=None)
    accept(no)
    reject(no, lambda p: p["quantities"]["result"].update(reasons=[{"code": "alloy-family-transfer"}]))
    reject(no, lambda p: p["quantities"]["result"].update(reasons=[]))
    print(f"PASS: prospective A7 validator; {count} actual acceptance/mutation checks; no served migration")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    check()
