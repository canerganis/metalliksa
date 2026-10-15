"""P8 research route: reason-code registry, option-rule texts and label tables (integration contract 2026-10-15,
sections 7 to 9).

Phase B skeleton. It holds the closed code list of contract 9.1 with class, scope and the causes each code may carry,
the precedence rule, the option-problem rules and message templates of 9.3, the request field labels the request
checks need, and (Revision 3, section 14) the closed sender list with its supersedeKey rules, the relay limits and the
blind relay projection BLIND_RELAY_V1. The leaf labels (7.1, 13.4), the per-code noun phrases and n/a templates of 9.2
and the served-difference templates of section 8 are phase C work (W-1 drafts awaiting maintainer approval); their
tables are empty here and nothing in phase B renders them.

Research only: no served module may import this file (guard R-ISO-1, python/test_lpbf_research_isolation.py).
Every English string here is a W-1 draft.
"""

from __future__ import annotations

import hashlib
import json
import re
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
    # Revision 3 (14.1 item 2): sender and relay rules, request scope.
    "sender-key-mismatch": MappingProxyType({
        "scope": "request", "code": "RESEARCH_REQUEST_INVALID",
        "template": "Supersede key {value} does not match sender {sender} (expected {expected})."}),
    "relay-sender-mismatch": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                               "template": "Sender {sender} cannot send a relay."}),
    "relay-options-forbidden": MappingProxyType({
        "scope": "request", "code": "RESEARCH_REQUEST_INVALID",
        "template": "Research options are not accepted {context}; the relay uses the default research inputs."}),
    "relay-required": MappingProxyType({"scope": "request", "code": "RESEARCH_REQUEST_INVALID",
                                        "template": "A blind-freeze band request needs a relay."}),
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
    "/sender": "Sender",
    "/relay": "Relay",
    "/relay/kind": "Relay kind",
    "/relay/previewSha256": "Relay preview SHA-256",
    "/relay/conditionOrdinal": "Relay condition ordinal",
})


# --- Senders and the blind relay (Revision 3, section 14) ---------------------------------------------------------

DEFAULT_SENDER = "research-panel"
SENDERS = ("research-panel", "blind-freeze", "batch-client")
PANEL_SUPERSEDE_KEYS = ("p8-research:melt-pool", "p8-research:build-job")
BLIND_SUPERSEDE_KEY = re.compile(r"p8-research:blind:([0-9a-f]{16})\Z")
BATCH_SUPERSEDE_KEY = re.compile(r"p8-research:batch:[a-z0-9]{8,32}\Z")
SUPERSEDE_KEY_RULES = MappingProxyType({
    "research-panel": "p8-research:melt-pool or p8-research:build-job",
    "blind-freeze": "p8-research:blind:<first 16 hex of relay.previewSha256>",
    "batch-client": "p8-research:batch:<runId of 8 to 32 characters a-z 0-9>",
})

RELAY_KIND = "blind-freeze-v1"
RELAY_CONDITION_ORDINAL_MAX = 1023      # R-REL-1: integer conditionOrdinal 0 to 1023
RELAY_SUBSET_MAX_CHARS = 12000          # 14.3 item 5 and 14.4 item 4, enforced by the route per condition
# 14.4 item 3: per freeze (blind relay) and per batch-client run. The route sees one condition per request, so these
# counts are enforced where conditions are counted (the hub freeze and scripts/research-route-batch.ts); they are
# recorded here as the one Python statement of the caps.
RELAY_MAX_CONDITIONS = 48
BATCH_DEFAULT_MAX_REQUESTS = 48
BATCH_MAX_REQUESTS = 256


def supersede_key_matches(sender: str, key: str, preview_sha256: str | None) -> bool:
    """14.1: the supersedeKey prefix of each sender. A blind-freeze key must name the first 16 hex of the relay's
    previewSha256 when the request carries a relay."""
    if sender == "research-panel":
        return key in PANEL_SUPERSEDE_KEYS
    if sender == "blind-freeze":
        match = BLIND_SUPERSEDE_KEY.match(key)
        return bool(match) and (preview_sha256 is None or match.group(1) == preview_sha256[:16])
    if sender == "batch-client":
        return bool(BATCH_SUPERSEDE_KEY.match(key))
    return False


# BLIND_RELAY_V1 (14.3 item 4): the closed key set of relay.subsetJson. A None leaf is an opaque value copied from the
# request, the response or the block; the dotted keys of scored, context, support, notes and statements are paths
# into researchModels (a path the block does not carry is null). "knownContradictions[].id" keeps only the ids.
_RELAY_MODULES = ("keyholeCavity", "meltDepthLink")
_RELAY_SECTIONS = {
    "scored": ("meltDepthLink.fields.linkedMeltDepth_um",),
    "context": tuple(f"meltDepthLink.fields.{name}" for name in (
        "conditionalMeltDepth_um", "conductionDepth_um", "controllingLeg", "linkDispatch", "conductionStatus",
        "floorFieldModelId", "floorExtractorId", "cavityLedgerRatio"))
    + tuple(f"keyholeCavity.fields.{name}" for name in (
        "cavityDepth_um", "onsetPower_W", "powerOverOnset", "peclet", "onsetEvent")),
    "support": ("keyholeCavity.band.onsetSupport", "keyholeCavity.band.statusSupport",
                "meltDepthLink.band.statusSupport"),
    "notes": tuple(f"{module}.consistencyNote.{name}" for module in _RELAY_MODULES for name in (
        "status", "worstArmStatus", "sentence", "assumptions", "knownContradictions[].id", "reasons", "onsetMismatch"))
    + ("meltDepthLink.consistencyNote.fieldShapeStep", "meltDepthLink.consistencyNote.fieldShapeShare"),
    "statements": tuple(f"{module}.{name}" for module in _RELAY_MODULES for name in (
        "moduleMaturity", "moduleEvidenceCeiling", "validationStatus", "validationStatusLocator",
        "experimentalValidation", "uiSentence")),
}
RELAY_PROCESS_KEYS = ("material", "laserPower_W", "scanSpeed_mm_s", "beamDiameter_um", "preheatTemp_C",
                      "laserWavelength", "absorptionModel")
RELAY_SI_KEYS = ("power_W", "speed_m_s", "beamDiameter_m", "preheat_K")
BLIND_RELAY_V1: Mapping[str, Any] = MappingProxyType({
    "relaySchemaVersion": None,
    "relayPathsSha256": None,
    "binding": MappingProxyType({"previewSha256": None, "conditionOrdinal": None}),
    "request": MappingProxyType({
        "process": MappingProxyType({key: None for key in RELAY_PROCESS_KEYS}),
        "si": MappingProxyType({key: None for key in RELAY_SI_KEYS}),
        "propertyContext": None,
        "sender": None,
    }),
    "requestKey": None,
    "identity": MappingProxyType({key: None for key in (
        "researchImplementationSha256", "servedImplementationFingerprint", "researchSchemaVersion",
        "propertySetSha256", "propertyContextKind")}),
    "digests": MappingProxyType({"researchModelsSha256": None, "labelsSha256": None}),
    **{section: MappingProxyType({path: None for path in paths}) for section, paths in _RELAY_SECTIONS.items()},
    "labels": None,   # {"<container>.<field>": label} for the field paths of scored and context the response labels
})


def relay_paths(spec: Mapping[str, Any] = BLIND_RELAY_V1, prefix: tuple = ()) -> list:
    """The canonical path list of BLIND_RELAY_V1: every key path, as lists of keys, sorted."""
    out = []
    for key, sub in spec.items():
        path = prefix + (key,)
        out.append(list(path))
        if isinstance(sub, Mapping):
            out.extend(relay_paths(sub, path))
    return sorted(out)


def canonical_json(value: Any) -> str:
    """The route's canonical JSON (14.3 item 1): sorted keys, separators (",", ":"), ensure_ascii, allow_nan=False."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


RELAY_PATHS_SHA256 = hashlib.sha256(canonical_json(relay_paths()).encode("ascii")).hexdigest()

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
              "nominal": "", "material": "", "mode": "", "presetAlloy": "", "sender": "", "expected": "",
              "context": ""}
    params.update({key: val for key, val in fields.items() if val is not None})
    message = " ".join(spec["template"].format(**params).split())
    return {"pointer": pointer, "rule": rule, "limit": limit, "value": value_text, "message": message}


def option_problem_code(problems) -> str | None:
    """The module or request code for a list of option problems: the code of the first problem's rule."""
    for problem in problems:
        return OPTION_RULES[problem["rule"]]["code"]
    return None
