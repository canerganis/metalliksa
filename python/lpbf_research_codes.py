"""P8 research route: reason-code registry, option-rule texts and label tables (integration contract 2026-10-15,
sections 7 to 9).

Phase B skeleton. It holds the closed code list of contract 9.1 with class, scope and the causes each code may carry,
the precedence rule, the option-problem rules and message templates of 9.3, and the request field labels the
request checks need. The leaf labels (7.1, 13.4), the per-code noun phrases and n/a templates of 9.2 and the
served-difference templates of section 8 are phase C work (W-1 drafts awaiting maintainer approval); their tables
are empty here and nothing in phase B renders them.

Research only: no served module may import this file (guard R-ISO-1, python/test_lpbf_research_isolation.py).
Every English string here is a W-1 draft.
"""

from __future__ import annotations

import json
from types import MappingProxyType
from typing import Any, Mapping

REGISTRY_REVISION = "p8-research-codes-v1-phase-b-skeleton"

# Class order is the precedence order: a null leaf carries the code of the lowest class number among its causes
# (contract 9.1); W is never a reasonCode.
CLASS_ORDER = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10")
WARNING_CLASS = "W"

CAUSES = ("request", "evaluator", "option", "alloy-not-admitted", "software-limit", "source-range", "input-missing",
          "default-cleared", "domain", "upstream", "convention", "comparison", "numerical", "closure-falsified",
          "closure-missing", "data-missing", "band")


def _codes(cls: str, scope: tuple, causes: tuple, *names: str) -> dict:
    return {name: MappingProxyType({"class": cls, "scope": scope, "causes": causes}) for name in names}


_REASON_CODES: dict = {}
_REASON_CODES.update(_codes("C1", ("request",), ("request",),
                            "RESEARCH_REQUEST_INVALID", "PROPERTY_SNAPSHOT_MISMATCH", "RESEARCH_CODE_STALE",
                            "RESEARCH_TIMEOUT"))
_REASON_CODES.update(_codes("C2", ("request", "module", "arm"), ("evaluator",),
                            "RESEARCH_EVALUATION_FAILED", "RESEARCH_SERIALIZATION_FAILED",
                            "RESEARCH_RESPONSE_TOO_LARGE"))
_REASON_CODES.update(_codes("C3", ("module",), ("option",),
                            "RESEARCH_OPTIONS_INVALID", "RESEARCH_PRESET_ALLOY_MISMATCH",
                            "SURFACTANT_BINARY_COMBINATION_UNSUPPORTED", "RESEARCH_ARM_LIMIT_EXCEEDED"))
_REASON_CODES.update(_codes("C4", ("module",), ("alloy-not-admitted",),
                            "ALLOY_CONSTANT_CHAIN_NOT_ADMITTED", "ALLOY_NOT_ALSI10MG", "UNSOURCED_PROPERTY_OVERRIDE"))
_REASON_CODES.update(_codes("C5", ("module", "leaf"), ("software-limit", "source-range"),
                            "INVALID_INPUT", "PREHEAT_OUTSIDE_PROPERTY_SCOPE", "WAVELENGTH_UNSUPPORTED",
                            "POWDER_CONTEXT_UNSUPPORTED", "PECLET_OUTSIDE_NUMERICAL_SCOPE",
                            "ASPECT_BOUND_OUTSIDE_NUMERICAL_SCOPE", "NUMERICAL_INPUT_BELOW_FLOOR",
                            "VAPOUR_PRESSURE_OUTSIDE_SOURCE_RANGE"))
_REASON_CODES.update(_codes("C6", ("module", "leaf"), ("input-missing", "default-cleared", "domain",
                                                       "alloy-not-admitted"),
                            "SURFACE_VAPOUR_INPUT_REQUIRED", "MARANGONI_VISCOSITY_INPUT_REQUIRED",
                            "MARANGONI_SOLUTE_INPUT_REQUIRED", "ONSET_REFERENCE_UNAVAILABLE"))
_REASON_CODES.update(_codes("C7", ("leaf",), ("upstream", "convention", "comparison"),
                            "MELT_LINK_NOT_AVAILABLE", "NOT_APPLICABLE_BELOW_ONSET", "NOT_APPLICABLE_FOR_CONVENTION",
                            "ONSET_COMPARISON_EVENT_MISMATCH", "ONSET_COMPARISON_TUPLE_MISMATCH"))
_REASON_CODES.update(_codes("C8", ("leaf", "arm"), ("numerical",),
                            "CYLINDER_CONVERGENCE_FAILED", "OPTICAL_TRACE_UNRESOLVED", "CAVITY_ROOT_SCAN_UNRESOLVED",
                            "CAVITY_RESIDUAL_FAILED", "NO_STRICTLY_STABLE_ROOT", "CONDUCTION_EXTENT_UNRESOLVED",
                            "MELT_BRACKET_FAILURE", "MELT_OPTIMIZER_FAILURE", "MELT_CONVERGENCE_FAILED",
                            "TIP_SHELL_UNRESOLVED", "SURFACE_BALANCE_NO_BRACKET",
                            "SURFACE_BALANCE_CONVERGENCE_FAILED", "NONFINITE_RESULT"))
_REASON_CODES.update(_codes("C9", ("leaf",), ("closure-falsified", "closure-missing", "data-missing"),
                            "MARANGONI_SURFACE_CHEMISTRY_UNAVAILABLE", "MARANGONI_TRANSPORT_CLOSURE_UNAVAILABLE",
                            "SURFACE_BALANCE_CLOSURE_FALSIFIED", "POWDER_ALLOY_OPTICAL_CONSTANTS_UNAVAILABLE",
                            "POWDER_LOT_INPUTS_UNAVAILABLE", "POWDER_THERMAL_OPERATOR_UNAVAILABLE",
                            "KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE", "SOURCE_RANGE_NOT_ESTABLISHED"))
_REASON_CODES.update(_codes("C10", ("band",), ("band",),
                            "BAND_PENDING", "BAND_NO_SUCCESSFUL_ARM", "BAND_MANIFEST_NOT_DECLARED"))
REASON_CODES: Mapping[str, Mapping[str, Any]] = MappingProxyType(_REASON_CODES)

WARNING_CODES = frozenset({
    "LOW_PE_HYDRODYNAMICS_OMITTED", "LOW_ASPECT_CAVITY_MECHANICS_OMITTED", "THERMAL_CYLINDER_CLOSURE_EXTRAPOLATED",
    "SOURCE_SCOPE_TRANSFER", "FIELD_SHAPE_STEP_NEAR_ONSET", "VAPOUR_PRESSURE_EXTRAPOLATED",
    "HKL_SUBBOILING_FIXED_BETA", "VAPOUR_CONSTANT_LV_EXTREME_EXTRAPOLATION", "USER_COEFFICIENT_PAIR_DECOUPLED",
    "FE_ANALOGUE_BASELINE_SUBSTITUTED",
})

# Never cached (contract 3.6): request-scope failures, evaluator bugs and timeouts.
TRANSIENT_CODES = frozenset(code for code, entry in _REASON_CODES.items() if entry["class"] in ("C1", "C2"))
# Deterministic for the same inputs, so an arm record failed with one of them is cacheable (C3 to C9).
DETERMINISTIC_CODES = frozenset(code for code, entry in _REASON_CODES.items()
                                if entry["class"] in ("C3", "C4", "C5", "C6", "C7", "C8", "C9"))

TIMEOUT_KINDS = ("queue", "run", "reply", "adhoc")


def code_class(code: str) -> str:
    if code in WARNING_CODES:
        return WARNING_CLASS
    entry = REASON_CODES.get(code)
    if entry is None:
        raise KeyError(f"unregistered research reason code: {code!r}")
    return entry["class"]


def winning_code(codes_in_detection_order) -> str | None:
    """Precedence of contract 9.1: lowest class number; inside one class the first detected. Warnings never win."""
    best = None
    best_rank = None
    for code in codes_in_detection_order:
        cls = code_class(code)
        if cls == WARNING_CLASS:
            raise ValueError(f"warning {code} can never be a reasonCode")
        rank = CLASS_ORDER.index(cls)
        if best_rank is None or rank < best_rank:
            best, best_rank = code, rank
    return best


# --- Option problems (contract 9.3) ------------------------------------------------------------------------------

OPTION_RULES: Mapping[str, Mapping[str, str]] = MappingProxyType({
    "unknown-key": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                     "template": "Unknown key {pointer}."}),
    "wrong-type": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                    "template": "{label} must be a {type}."}),
    "not-positive": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                      "template": "{label} must be greater than 0; got {value}."}),
    "too-large": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                   "template": "The research request exceeds 65536 bytes."}),
    "alloy-material-mismatch": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                                 "template": "Alloy {value} does not match material {material}."}),
    "snapshot-hash-mismatch": MappingProxyType({
        "scope": "request", "code": "PROPERTY_SNAPSHOT_MISMATCH",
        "template": ("The Build Job used a different material property revision. Re-run the Build Job, then run "
                     "research models.")}),
    "not-finite": MappingProxyType({"scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
                                    "template": "{label} must be a finite number."}),
    "below-min": MappingProxyType({"scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
                                   "template": "{label} must be between {min} and {max} {unit}; got {value}."}),
    "above-max": MappingProxyType({"scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
                                   "template": "{label} must be between {min} and {max} {unit}; got {value}."}),
    "range-inverted": MappingProxyType({"scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
                                        "template": "The range for {label} has min {min} above max {max}."}),
    "range-excludes-nominal": MappingProxyType({
        "scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
        "template": ("The range for {label} ({min} to {max} {unit}) does not contain its current value {nominal}. "
                     "Widen the range or reset it.")}),
    "range-without-nominal": MappingProxyType({
        "scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
        "template": "{label} has no value (input required), so a range cannot be used."}),
    "mode-field-ignored": MappingProxyType({"scope": "module", "code": "RESEARCH_OPTIONS_INVALID",
                                            "template": "{label} is not used in {mode}. Clear it or change the mode."}),
    "binary-combination": MappingProxyType({
        "scope": "module", "code": "SURFACTANT_BINARY_COMBINATION_UNSUPPORTED",
        "template": "Enter soluble S or soluble O, not both; the two Fe analogues cannot be combined."}),
    "preset-alloy-mismatch": MappingProxyType({"scope": "module", "code": "RESEARCH_PRESET_ALLOY_MISMATCH",
                                               "template": "Vapour preset {value} is defined for {presetAlloy} only."}),
})

MAX_PROBLEM_VALUE_CHARS = 64

# Request field labels used in request-check messages (W-1 drafts). Research option labels come from the control
# table of the describe stage (phase C).
REQUEST_FIELD_LABELS: Mapping[str, str] = MappingProxyType({
    "": "The research request",
    "/schemaVersion": "Request schema version",
    "/supersedeKey": "Supersede key",
    "/clientRequestId": "Client request id",
    "/stage": "Stage",
    "/timeBudgetMs": "Time budget (ms)",
    "/process": "Process",
    "/process/material": "Material",
    "/process/laserPower_W": "Laser power (W)",
    "/process/scanSpeed_mm_s": "Scan speed (mm/s)",
    "/process/beamDiameter_um": "Beam diameter (um)",
    "/process/preheatTemp_C": "Preheat temperature (C)",
    "/process/laserWavelength": "Laser wavelength",
    "/process/absorptionModel": "Absorption model",
    "/propertyContext": "Property context",
    "/propertyContext/kind": "Property context kind",
    "/propertyContext/alloyId": "Build Job alloy",
    "/propertyContext/materialPropertySha256": "Material property SHA-256",
    "/researchOptions": "Research options",
})

# Phase C (W-1): field path -> English label (7.1, 13.4). Empty in phase B; TypeScript never authors a label.
LEAF_LABELS: Mapping[str, str] = MappingProxyType({})


def json_value_text(value: Any) -> str:
    """JSON text of a received value, at most 64 characters (OptionProblem.value)."""
    try:
        text = json.dumps(value, ensure_ascii=False, allow_nan=True, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        text = json.dumps(repr(value), ensure_ascii=False)
    return text if len(text) <= MAX_PROBLEM_VALUE_CHARS else text[:MAX_PROBLEM_VALUE_CHARS - 3] + "..."


def request_label(pointer: str) -> str:
    if pointer in REQUEST_FIELD_LABELS:
        return REQUEST_FIELD_LABELS[pointer]
    return pointer.rsplit("/", 1)[-1] or "The research request"


def option_problem(pointer: str, rule: str, *, value: Any = None, limit: float | int | str | None = None,
                   label: str | None = None, **fields: Any) -> dict:
    """One OptionProblem (contract 9.3) with its message filled from the rule template."""
    spec = OPTION_RULES[rule]
    value_text = json_value_text(value)
    params = {"pointer": pointer, "label": label or request_label(pointer), "value": value_text,
              "limit": "" if limit is None else limit, "type": "valid value", "min": "", "max": "", "unit": "",
              "nominal": "", "material": "", "mode": "", "presetAlloy": ""}
    params.update({key: val for key, val in fields.items() if val is not None})
    message = " ".join(spec["template"].format(**params).split())
    return {"pointer": pointer, "rule": rule, "limit": limit, "value": value_text, "message": message}


def option_problem_code(problems) -> str | None:
    """The module or request code for a list of option problems: the code of the first problem's rule."""
    for problem in problems:
        return OPTION_RULES[problem["rule"]]["code"]
    return None
