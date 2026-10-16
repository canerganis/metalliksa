"""Quantity envelope v1: closed vocabularies, builders, the source-label rule and validators.

Authority: the solidification integration contract (docs/research/SPEC_solidification_integration_2026-10-15.md,
Revision 1, section 4), the maintainer's label decisions 1 and 2 of 2026-10-15 (per-value sourceEvidenceKind under
a screening-only module ceiling; Literature estimate / User input / Unresolved with named inputs, Unresolved first)
and the per-value encoding of the P8 integration contract (sections 6.1 to 6.3, 13.5 and 13.12).

Placement rules (contract 4.1):

- Stdlib only and outside the LPBF thermal fingerprint manifest. No manifest file may import this module, or the
  closure test would pull it into the manifest and every wording change would move the pin
  (python/test_quantity_envelope.py checks the manifest files). Manifest producers emit the codes, kinds and
  structured parameters below as literals, never an English sentence; consumers attach text with ``reason_text``.
- Every English string here (reason sentences, status labels, source-label display, definition names, container
  header) is a DRAFT pending the maintainer's wording round (MD2, literal groups L1, L2, L3, L8 and L9).
- Nothing here computes, raises or upgrades an evidence claim. Every container states the module ceiling
  "screening-only"; the per-value sourceEvidenceKind is a source label and is never compared with that ceiling.
  "Measured" appears only on observation records (transcribed measurements); no quantity and no input used to
  compute one reads "Measured".
"""
from __future__ import annotations

import copy
import json
import math
import re
import string
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# --- Closed vocabularies ---------------------------------------------------------------------------------------

ENVELOPE_SCHEMA = "metalliksa-quantity-envelope-1"
# Decision 1: every container says screening-only; no ceiling is raised by this envelope.
MODULE_EVIDENCE_CEILING = "screening-only"
# Mirrors module_contract.MATURITY (Production is not expressible); test_quantity_envelope checks the equality.
MODULE_MATURITIES: Tuple[str, ...] = ("Research", "Preview")
CONTAINER_REQUIRED_KEYS: Tuple[str, ...] = ("quantityEnvelopeSchema", "moduleEvidenceCeiling", "moduleMaturity",
                                            "quantities")
CONTAINER_OPTIONAL_KEYS: Tuple[str, ...] = ("observations", "inputProvenance", "default")
CONTAINER_ONLY_KEYS: Tuple[str, ...] = ("quantityEnvelopeSchema", "moduleEvidenceCeiling", "moduleMaturity")

QUANTITY_STATUSES: Tuple[str, ...] = ("computed", "partial", "unavailable", "failed", "not-requested")
VALUE_STATUSES: Tuple[str, ...] = ("computed", "partial")  # the only statuses that carry a value
# L2 drafts (MD2).
STATUS_LABELS: Dict[str, str] = {
    "computed": "Computed",
    "partial": "Partial",
    "unavailable": "Unavailable",
    "failed": "Failed",
    "not-requested": "Not requested",
}

# Reason codes: the 21 codes of SPEC:34 followed by the four integration codes (contract 4.6). Each has one
# sentence template (L1 drafts, MD2). A template may name parameters as {name}; every named parameter must then be
# present in the reason's params. All v1 drafts are parameterless; parameters stay structured data.
REASON_TEMPLATES: Dict[str, str] = {
    "missing-assessed-system": "No assessed thermodynamic description covers this system.",
    "outside-database-domain": "The request lies outside the composition or temperature domain the database declares.",
    "unknown-database-temperature-domain": "The database declares no assessed temperature range, so its temperature "
                                           "support is unknown.",
    "outside-source-model-domain": "The inputs lie outside the domain of the source model.",
    "missing-source-bound-model": "No source-bound model exists for this quantity, alloy or process.",
    "missing-source-constant": "A required input has no admitted source.",
    "missing-thermal-history": "No eligible temperature history is available for this quantity.",
    "unsupported-precipitate": "No admitted model supports this precipitate.",
    "unverified-equation": "The source equation has not been read and reproduced.",
    "invalid-interface-sample": "The interface sample is invalid: zero, non-finite or on the melting side.",
    "nonphysical-input": "An input is non-finite or outside its physical range.",
    "unknown-alloy-alias": "The alloy name is not a known canonical alloy ID.",
    "not-requested": "This quantity was not requested.",
    "phase-selection-sensitive": "The result changes with the phase selection or the minimizer sampling.",
    "residual-liquid-at-termination": "Liquid remained when the calculation stopped.",
    "numerical-conservation-failed": "Phase or element inventories do not close within the declared tolerance.",
    "stale-parent-input": "A parent input changed after this value was computed.",
    "keyhole-field-inconsistent": "The temperature field is not consistent with the keyhole cavity and melt geometry.",
    "incompatible-liquidus-parent": "The thermal and thermodynamic liquidus definitions do not match.",
    "unsupported-fraction-conversion": "Converting between these fraction bases needs data that is not available.",
    "licence-scope-unconfirmed": "The data licence does not confirm this use.",
    "parent-unavailable": "A parent value this quantity depends on is unavailable.",
    "solver-error": "The solver failed for this quantity.",
    "insufficient-sample-support": "Too few valid interface samples support this value.",
    "quarantined-legacy-path": "This legacy path is quarantined and is not served.",
}
REASON_CODES: Tuple[str, ...] = tuple(REASON_TEMPLATES)
SPEC_REASON_CODES: Tuple[str, ...] = REASON_CODES[:21]
INTEGRATION_REASON_CODES: Tuple[str, ...] = REASON_CODES[21:]

# Closed SI unit strings. "per-member-SI" marks a record value whose members carry the units in memberUnits.
UNITS: Tuple[str, ...] = ("K/m", "m/s", "K/s", "K*s/m^2", "m", "K", "Pa", "1", "per-member-SI")
VALUE_KINDS: Tuple[str, ...] = ("number", "alternatives", "map", "record", "category")
VALUE_RANGES: Tuple[str, ...] = ("positive", "fraction", "finite")


def _definition(label: str, unit: str, kind: str, value_range: Optional[str], *, fraction: bool = False,
                members: Sequence[str] = (), member_units: Optional[Mapping[str, str]] = None,
                categories: Sequence[str] = ()) -> Dict[str, Any]:
    return {"label": label, "unit": unit, "valueKind": kind, "valueRange": value_range, "fraction": fraction,
            "members": list(members), "memberUnits": dict(member_units or {}), "categories": list(categories)}


# Contract 4.2 quantity definitions (labels are L8 drafts). A category definition with no categories admits no
# non-null value in v1: no source-bound classifier is served for it (SPEC A3.A4, 6.1).
QUANTITY_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "liquidus-front-thermal-gradient": _definition("Thermal gradient G at the liquidus front", "K/m", "number",
                                                   "positive"),
    "liquidus-front-normal-speed": _definition("Normal speed R of the liquidus front", "m/s", "number", "positive"),
    "liquidus-front-cooling-rate": _definition("Cooling rate G R at the liquidus front", "K/s", "number", "positive"),
    "liquidus-front-g-over-r": _definition("G/R at the liquidus front", "K*s/m^2", "number", "positive"),
    "pdas-model-alternatives": _definition("Primary dendrite arm spacing (two model alternatives)", "m",
                                           "alternatives", "positive", members=("hunt", "kurzFisher")),
    "sdas": _definition("Secondary dendrite arm spacing", "m", "number", "positive"),
    "front-morphology": _definition("Solidification front morphology", "1", "category", None),
    "solid-state-transformation": _definition("Solid-state transformation", "1", "category", None),
    "cet-class": _definition("Columnar-to-equiaxed class", "1", "category", None,
                             categories=("columnar", "mixed", "equiaxed")),
    "laves-trapped-scheil-fraction": _definition("Laves fraction, trapped Scheil bound", "1", "number", "fraction",
                                                 fraction=True),
    "scheil-phase-inventory": _definition("Scheil phase inventory", "1", "map", "fraction", fraction=True),
    "scheil-residual-liquid": _definition("Scheil residual liquid", "1", "number", "fraction", fraction=True),
    "critical-temperature": _definition("Critical temperature", "K", "number", "positive"),
    "lsw-mean-radius": _definition("LSW mean precipitate radius", "m", "number", "positive"),
    "precipitation-strengthening": _definition("Precipitation strengthening", "Pa", "number", "finite"),
    "user-threshold-isotherm-kinematics": _definition(
        "Kinematics of a user-defined threshold isotherm (software diagnostic)", "per-member-SI", "record", "positive",
        member_units={"thermalGradient": "K/m", "normalSpeed": "m/s", "coolingRate": "K/s", "gOverR": "K*s/m^2"}),
}

UNCERTAINTY_KINDS: Tuple[str, ...] = ("model-alternatives", "parameter-sensitivity", "numerical-refinement",
                                      "calibrated-prediction-interval", "not-quantified")
FRACTION_BASES: Tuple[str, ...] = ("mole-of-atoms", "mass", "volume", "reaction-progress", "microconstituent")
NUMERICAL_STATES: Tuple[str, ...] = ("not-assessed", "unresolved", "refinement-passed", "failed")
READ_LEVELS: Tuple[str, ...] = ("primary-read", "secondary-read", "repository-attribution")
PHYSICAL_VALIDATION: Dict[str, Any] = {"status": "unvalidated", "experimentalValidation": False,
                                       "productionReady": False}

# Per-value source labels (decisions 1 and 2). Weakest first: Unresolved takes precedence over User input.
SOURCE_EVIDENCE_KINDS: Tuple[str, ...] = ("Measured", "Literature estimate", "User input", "Unresolved")
QUANTITY_SOURCE_EVIDENCE_KINDS: Tuple[str, ...] = ("Literature estimate", "User input", "Unresolved")
OBSERVATION_SOURCE_EVIDENCE_KINDS: Tuple[str, ...] = ("Measured", "Literature estimate")
LABEL_RANK: Dict[str, int] = {"Unresolved": 0, "User input": 1, "Literature estimate": 2}
# L3 drafts, shared with P8 (W-1).
SOURCE_LABEL_DISPLAY: Dict[str, str] = {
    "Literature estimate": "Literature estimate",
    "User input": "User input: {names}",
    "Unresolved": "Unresolved: {names}",
    "Measured": "Measured (transcribed)",
}
# L9 drafts: container header text.
CONTAINER_HEADER_TEXT: Dict[str, str] = {"screening-only": "Screening only"}

# P8 leaf roles (P8 contract 6.1).
LEAF_ROLES: Tuple[str, ...] = ("derived", "requestInput", "physicalInput", "softwareLimit", "convention",
                               "indexConvention")
LABELLED_ROLES: Tuple[str, ...] = ("derived", "physicalInput")  # labelled by the rule over their inputs
UNLABELLED_ROLES: Tuple[str, ...] = ("softwareLimit", "convention", "indexConvention")  # always null

# Input provenance records: P8's ResearchInputProvenance (P8 contract 6.3), the same closed kind enum.
INPUT_KINDS: Tuple[str, ...] = ("sourceDefault", "sourceModelAssumption", "sourcedAlternative", "alloyTransfer",
                                "modelConvention", "declaredAssumption", "legacyEstimate", "userInput",
                                "followsInput", "derived")
SOURCED_INPUT_KINDS: Tuple[str, ...] = INPUT_KINDS[:5]
UNSOURCED_INPUT_KINDS: Tuple[str, ...] = ("declaredAssumption", "legacyEstimate")
# P8 contract 13.5 display labels (shared drafts).
INPUT_KIND_LABELS: Dict[str, str] = {
    "sourceDefault": "sourced default",
    "sourceModelAssumption": "source model assumption",
    "sourcedAlternative": "sourced alternative",
    "alloyTransfer": "transferred: {scope}",
    "modelConvention": "alternative convention: {event}",
    "declaredAssumption": "declared assumption (no source)",
    "legacyEstimate": "legacy estimate (no located source)",
    "userInput": "user input",
    "followsInput": "follows {followsInput}",
    "derived": "derived from {dependsOn}",
}
# The label each kind gives directly; followsInput and derived are computed from their rule and inputs (None).
INPUT_KIND_EVIDENCE: Dict[str, Optional[str]] = {
    **{kind: "Literature estimate" for kind in SOURCED_INPUT_KINDS},
    "declaredAssumption": "Unresolved", "legacyEstimate": "Unresolved", "userInput": "User input",
    "followsInput": None, "derived": None,
}
INPUT_STATUSES: Tuple[str, ...] = ("inRange", "extrapolated", "outOfRange")
INPUT_PHASES: Tuple[str, ...] = ("solid", "liquid", "solid-liquid-mean", "vapour", "process")
# Request process values (P, v, d, T0) are recorded with phase "process"; they never decide a label (4.3 item 3).
PROCESS_PHASE = "process"
# Fixed request echoes, never physical coefficients. Their phase cannot decide the label.
REQUEST_PROCESS_INPUTS = ("P", "v", "d", "T0", "power_W", "speed_m_s", "speed_mm_s", "beamDiameter_um",
                          "beamDiameter_m", "preheat_C", "preheat_K", "preheatTemp_C", "h", "t", "hatch_um",
                          "layer_um", "hatchSpacing_um", "layerThickness_um", "scanStrategy", "heatSource",
                          "solver", "solverSettings", "nx", "ny", "nz", "dt_s", "timeStep_s", "maxDt_s",
                          "gridSpacing_um", "gridSpacing_m", "quadratureOrder", "maxSteps", "maxIterations",
                          "tolerance", "integrationTolerance", "sampleCount", "seed")
FOLLOW_STATES: Tuple[str, ...] = ("following", "user-fixed")
INPUT_RECORD_KEYS: Tuple[str, ...] = ("kind", "label", "sourceId", "sourceLocator", "declarationLocator", "source",
                                      "scope", "status", "sourceEvidenceKind", "defaultValue", "defaultKind",
                                      "followsInput", "followState", "dependsOn", "phase", "referenceTemperature_K",
                                      "sourceRange_K")

QUANTITY_KEYS: Tuple[str, ...] = ("status", "value", "unit", "quantityDefinition", "leafRole", "sourceEvidenceKind",
                                  "dependsOn", "weakestInputs", "labelSources", "reasons", "numericalStatus",
                                  "physicalValidation", "sources", "assumptions", "validity", "uncertainty",
                                  "fractionBasis", "identity")
OBSERVATION_RECORD_KIND = "source-observation"
OBSERVATION_KEYS: Tuple[str, ...] = ("recordKind", "observable", "value", "unit", "sourceEvidenceKind", "sources",
                                     "materialScope", "processScope", "comparability")
COMPARABILITY: Tuple[str, ...] = ("context-only", "not-assessed")

CANONICAL_ALLOY_IDS: Tuple[str, ...] = ("ti6al4v", "alsi10mg", "in718", "in625", "ss316l")

# --- Melt-point ledger admission classes (contract 4.3 item 5) ---------------------------------------------------
#
# Records: docs/research/scripts/solidification_melt_point_ledger.py (schema 2, 024e30cd). Class stems are mapped,
# so a renamed status prefix ("proposed-", later "admitted-") keeps the mapping. A family transfer never reads as
# Measured, although its source measured its own batch.
LEDGER_CLASS_MAPPING: Dict[str, Dict[str, Any]] = {
    "fixed-front-literature-model": {
        "role": "input", "inputKind": "sourceModelAssumption", "sourceEvidenceKind": "Literature estimate",
        "status": None, "scope": "nominal alloy model convention", "observationEvidenceKind": None},
    "fixed-front-explicit-family-transfer": {
        "role": "input", "inputKind": "alloyTransfer", "sourceEvidenceKind": "Literature estimate",
        "status": "extrapolated", "scope": None, "observationEvidenceKind": None},
    "refusal-default-liquidus": {
        "role": "observation-only", "inputKind": None, "sourceEvidenceKind": None, "status": None, "scope": None,
        "observationEvidenceKind": "Measured"},
    "datasheet-disclosure-only": {
        "role": "observation-only", "inputKind": None, "sourceEvidenceKind": None, "status": None, "scope": None,
        "observationEvidenceKind": "Literature estimate"},
}
# Alternatives (MP02 cooling, MP03 fast pulse, MP06 Cieslak family): sensitivity arms only, never the default.
LEDGER_ALTERNATIVE_MAPPING: Dict[str, Any] = {"inputKind": "sourcedAlternative",
                                              "sourceEvidenceKind": "Literature estimate", "default": False}
# Nothing installed until SOL-T: the current served liquidus kinds; dependents are Unresolved (null at SOL-A1).
SERVED_LIQUIDUS_INPUT_KINDS: Dict[str, str] = {
    "alsi10mg": "alloyTransfer", "ss316l": "alloyTransfer",
    "ti6al4v": "modelConvention", "in718": "modelConvention", "in625": "modelConvention",
}

_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class EnvelopeError(ValueError):
    """Raised by a builder asked to produce an envelope that the contract forbids."""


# --- Reason text ---------------------------------------------------------------------------------------------------

def template_params(template: str) -> Tuple[str, ...]:
    """Named {placeholders} of a sentence template, in order of first use."""
    names: List[str] = []
    for _, field, _, _ in string.Formatter().parse(template):
        if field is not None:
            if not _KEY.match(field):
                raise EnvelopeError(f"template placeholder {field!r} must be a plain name")
            if field not in names:
                names.append(field)
    return tuple(names)


def reason_text(code: str, params: Optional[Mapping[str, Any]] = None) -> str:
    """English display sentence for a reason code (L1 draft). Python consumers attach text with this."""
    if code not in REASON_TEMPLATES:
        raise EnvelopeError(f"unknown reason code {code!r}")
    template = REASON_TEMPLATES[code]
    params = dict(params or {})
    missing = [name for name in template_params(template) if name not in params]
    if missing:
        raise EnvelopeError(f"reason {code!r} needs params {missing}")
    return template.format(**params)


# --- Ledger class mapping --------------------------------------------------------------------------------------------

def ledger_class_stem(class_text: str) -> str:
    """Mapped stem of a ledger admission class: the first clause, with any status prefix ("proposed-") removed.

    Unknown classes fail closed (EnvelopeError)."""
    if not isinstance(class_text, str) or not class_text.strip():
        raise EnvelopeError("ledger class must be a non-empty string")
    clause = class_text.split(";", 1)[0].strip()
    if clause in LEDGER_CLASS_MAPPING:
        return clause
    prefix, _, stem = clause.partition("-")
    if prefix in ("proposed", "admitted") and stem in LEDGER_CLASS_MAPPING:
        return stem
    raise EnvelopeError(f"unknown ledger admission class {class_text!r}")


def ledger_class_mapping(class_text: str) -> Dict[str, Any]:
    return dict(LEDGER_CLASS_MAPPING[ledger_class_stem(class_text)])


def ledger_input_record(class_text: str, *, source_id: str, source_locator: str, source: Optional[str] = None,
                        scope: Optional[str] = None, phase: Optional[str] = "solid-liquid-mean",
                        status: Optional[str] = None, reference_temperature_K: Optional[float] = None,
                        source_range_K: Optional[Sequence[float]] = None,
                        default_value: Any = None) -> Dict[str, Any]:
    """Input record for an endpoint admitted under a ledger class (contract 4.3 item 5).

    Refuses the observation-only classes (MP05 316L proxy, MP07 datasheet): they are never inputs of the default
    front. The transfer class always reads Literature estimate with status extrapolated, never Measured."""
    mapping = ledger_class_mapping(class_text)
    if mapping["role"] != "input":
        raise EnvelopeError(f"ledger class {class_text!r} is observation-only and never an input of the default front")
    kind = mapping["inputKind"]
    if mapping["status"] is not None:
        if status not in (None, mapping["status"]):
            raise EnvelopeError(f"ledger class {class_text!r} fixes status {mapping['status']!r}")
        status = mapping["status"]
    scope_text = scope if scope is not None else mapping["scope"]
    if not scope_text:
        raise EnvelopeError(f"ledger class {class_text!r} needs its transfer scope text")
    return input_record(kind, source_id, source_locator=source_locator, source=source, scope=scope_text,
                        status=status or "extrapolated", phase=phase,
                        reference_temperature_K=reference_temperature_K, source_range_K=source_range_K,
                        default_value=default_value, default_kind=kind)


def ledger_observation_kind(class_text: str) -> str:
    """sourceEvidenceKind of an observation record built from a ledger class (only observation-only classes)."""
    mapping = ledger_class_mapping(class_text)
    if mapping["observationEvidenceKind"] is None:
        raise EnvelopeError(f"ledger class {class_text!r} is an input class, not an observation record")
    return mapping["observationEvidenceKind"]


# --- Input provenance records ----------------------------------------------------------------------------------------

def input_label(kind: str, *, scope: str = "", event: str = "", follows_input: Optional[str] = None,
                depends_on: Sequence[str] = ()) -> str:
    template = INPUT_KIND_LABELS[kind]
    return template.format(scope=scope, event=event, followsInput=follows_input or "",
                           dependsOn=", ".join(depends_on))


def input_record(kind: str, source_id: str, *, status: str, source_locator: Optional[str] = None,
                 declaration_locator: Optional[str] = None, source: Optional[str] = None, scope: str = "",
                 source_evidence_kind: Optional[str] = None, default_value: Any = None,
                 default_kind: Optional[str] = None, follows_input: Optional[str] = None,
                 follow_state: Optional[str] = None, depends_on: Sequence[str] = (), phase: Optional[str] = None,
                 reference_temperature_K: Optional[float] = None,
                 source_range_K: Optional[Sequence[float]] = None, label: Optional[str] = None,
                 event: str = "") -> Dict[str, Any]:
    """One P8-shaped input provenance record (17 keys). Raises EnvelopeError when it breaks a record rule."""
    if kind not in INPUT_KINDS:
        raise EnvelopeError(f"unknown input kind {kind!r}")
    evidence = source_evidence_kind if source_evidence_kind is not None else INPUT_KIND_EVIDENCE[kind]
    if follows_input is not None and follow_state is None:
        follow_state = "following" if kind == "followsInput" else "user-fixed"
    record = {
        "kind": kind,
        "label": label if label is not None else input_label(kind, scope=scope, event=event,
                                                             follows_input=follows_input, depends_on=depends_on),
        "sourceId": source_id,
        "sourceLocator": source_locator,
        "declarationLocator": declaration_locator,
        "source": source,
        "scope": scope,
        "status": status,
        "sourceEvidenceKind": evidence,
        "defaultValue": default_value,
        "defaultKind": default_kind,
        "followsInput": follows_input,
        "followState": follow_state,
        "dependsOn": list(depends_on),
        "phase": phase,
        "referenceTemperature_K": reference_temperature_K,
        "sourceRange_K": list(source_range_K) if source_range_K is not None else None,
    }
    problems = input_record_problems(record, "input")
    if problems:
        raise EnvelopeError("; ".join(problems))
    return record


def process_input_record(name: str, *, source_id: Optional[str] = None) -> Dict[str, Any]:
    """Echo record of a request process value (P, v, d, T0): user input, phase process, never label-deciding."""
    return input_record("userInput", source_id or f"request:{name}", status="inRange", phase=PROCESS_PHASE,
                        scope="Process request value; excluded from the source-label rule")


def typed_input(default: Mapping[str, Any], typed_value: float, default_value: float, *, source_id: str,
                scope: str = "") -> Dict[str, Any]:
    """Record for a value the user typed over a sourced default (decision 2, P8 13.12 item 3).

    A typed value equal to its default (float.hex after unit conversion, so both are SI floats here) keeps the
    default's record and label; any other value is a userInput naming the default it replaced."""
    if not (_is_number(typed_value) and _is_number(default_value)):
        raise EnvelopeError("typed and default values must be finite SI numbers")
    if float(typed_value).hex() == float(default_value).hex():
        kept = copy.deepcopy(dict(default))
        kept["defaultValue"] = default_value
        return kept
    kind = default.get("kind")
    default_kind = {"legacyEstimate": None, "userInput": default.get("defaultKind")}.get(kind, kind)
    follows = default.get("followsInput") if kind == "followsInput" else None
    # The 17-key P8 record has no current-value field: bind the actual typed SI value in sourceId.
    return input_record("userInput", f"{source_id}:value:{float(typed_value).hex()}",
                        status="inRange", scope=scope, default_value=default_value,
                        default_kind=default_kind, follows_input=follows, phase=default.get("phase"),
                        reference_temperature_K=default.get("referenceTemperature_K"),
                        source_range_K=default.get("sourceRange_K"))


def _is_number(value: Any) -> bool:
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def _text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item != "" for item in value)


def input_record_problems(record: Any, where: str) -> List[str]:
    """Problems of one input provenance record (the shared value-provenance rules, P8 6.3 and 13.5)."""
    if not isinstance(record, dict):
        return [f"{where}: input record must be an object"]
    problems: List[str] = []
    keys = set(record)
    missing = [key for key in INPUT_RECORD_KEYS if key not in keys]
    extra = sorted(keys - set(INPUT_RECORD_KEYS))
    if missing:
        problems.append(f"{where}: missing keys {missing}")
    if extra:
        problems.append(f"{where}: unknown keys {extra}")
    if missing:
        return problems
    kind = record["kind"]
    if kind not in INPUT_KINDS:
        return problems + [f"{where}: unknown kind {kind!r}"]
    if not _text(record["label"]):
        problems.append(f"{where}: label must be a non-empty string")
    if not _text(record["sourceId"]):
        problems.append(f"{where}: sourceId must be a non-empty string")
    for key in ("sourceLocator", "declarationLocator", "source"):
        if record[key] is not None and not _text(record[key]):
            problems.append(f"{where}: {key} must be null or a non-empty string")
    if not isinstance(record["scope"], str):
        problems.append(f"{where}: scope must be a string")
    if record["status"] not in INPUT_STATUSES:
        problems.append(f"{where}: status must be one of {INPUT_STATUSES}")
    evidence = record["sourceEvidenceKind"]
    if evidence == "Measured":
        problems.append(f"{where}: an input used to compute a value never reads Measured (contract 4.3 item 4)")
    elif not isinstance(evidence, str) or evidence not in LABEL_RANK:
        problems.append(f"{where}: sourceEvidenceKind must be one of {QUANTITY_SOURCE_EVIDENCE_KINDS}")
    else:
        ceiling = INPUT_KIND_EVIDENCE[kind]
        if ceiling is not None and LABEL_RANK[evidence] > LABEL_RANK[ceiling]:
            problems.append(f"{where}: kind {kind} cannot read {evidence!r} (at most {ceiling!r})")
    if kind in SOURCED_INPUT_KINDS and not _text(record["sourceLocator"]):
        problems.append(f"{where}: a {kind} record needs a located source (sourceLocator); an unlocated value is "
                        "a declaredAssumption")
    if kind == "declaredAssumption" and not _text(record["declarationLocator"]):
        problems.append(f"{where}: a declaredAssumption names where it is declared (declarationLocator)")
    if kind == "alloyTransfer" and record["status"] == "inRange":
        problems.append(f"{where}: a transfer keeps its scope extrapolated, never inRange")
    default = record["defaultValue"]
    if default is not None and not (_is_number(default) or isinstance(default, str)):
        problems.append(f"{where}: defaultValue must be a finite number, a string or null")
    default_kind = record["defaultKind"]
    if default_kind is not None and default_kind not in INPUT_KINDS:
        problems.append(f"{where}: defaultKind must be an input kind or null")
    if default_kind == "legacyEstimate":
        problems.append(f"{where}: a legacy estimate is never a default")
    if default_kind == "sourcedAlternative":
        problems.append(f"{where}: a sourcedAlternative is never a defaultKind")
    follows, state = record["followsInput"], record["followState"]
    if kind == "followsInput":
        if not _text(follows) or state != "following":
            problems.append(f"{where}: followsInput needs followsInput and followState 'following'")
        if default_kind is None:
            problems.append(f"{where}: followsInput needs defaultKind, the kind of its rule")
    elif kind == "userInput" and state is not None:
        if state != "user-fixed" or not _text(follows):
            problems.append(f"{where}: a typed follower is userInput with followState 'user-fixed' and its "
                            "followsInput")
    elif follows is not None or state is not None:
        problems.append(f"{where}: only followsInput (or a user-fixed userInput) carries followsInput/followState")
    if not _str_list(record["dependsOn"]) or len(set(record["dependsOn"])) != len(record["dependsOn"]):
        problems.append(f"{where}: dependsOn must be a list of unique names")
    if record["phase"] is not None and record["phase"] not in INPUT_PHASES:
        problems.append(f"{where}: phase must be one of {INPUT_PHASES} or null")
    if record["phase"] == PROCESS_PHASE and kind != "userInput":
        problems.append(f"{where}: only userInput may carry phase process")
    if record["referenceTemperature_K"] is not None and not _is_number(record["referenceTemperature_K"]):
        problems.append(f"{where}: referenceTemperature_K must be a finite number or null")
    source_range = record["sourceRange_K"]
    if source_range is not None and not (isinstance(source_range, list) and len(source_range) == 2
                                         and all(_is_number(v) for v in source_range)
                                         and source_range[0] <= source_range[1]):
        problems.append(f"{where}: sourceRange_K must be [low, high] finite numbers or null (never invented)")
    return problems


# --- Source-label rule (decision 2; contract 4.3; P8 13.12) ------------------------------------------------------

def _determining(depends_on: Sequence[str], inputs: Mapping[str, Any],
                 quantities: Optional[Mapping[str, Any]], seen: frozenset = frozenset()) -> List[str]:
    """Input names a value depends on, with sibling quantities resolved to their own inputs (order kept)."""
    names: List[str] = []
    for name in depends_on:
        if quantities is not None and name in quantities and name not in inputs:
            if name in seen:
                names.append(name)  # a cycle: left unresolved, so it labels Unresolved
                continue
            sibling = quantities[name]
            nested = sibling.get("dependsOn", []) if isinstance(sibling, dict) else []
            for inner in _determining(nested if _str_list(nested) else [], inputs, quantities,
                                      seen | {name}):
                if inner not in names:
                    names.append(inner)
        elif name not in names:
            names.append(name)
    return names


def _input_label(name: str, inputs: Mapping[str, Any], seen: frozenset) -> Tuple[Optional[str], List[str]]:
    """(label, locators) of one input record; label None when the record is a request process value."""
    if name in REQUEST_PROCESS_INPUTS:
        return None, []
    record = inputs.get(name)
    if not isinstance(record, dict) or name in seen:
        return "Unresolved", []  # missing record or a cycle: never upgraded
    kind = record.get("kind")
    own = record.get("sourceEvidenceKind")
    locators: List[str] = []
    if kind in SOURCED_INPUT_KINDS:
        if _text(record.get("sourceLocator")):
            label = "Literature estimate"
            locators = [record["sourceLocator"]]
        else:
            label = "Unresolved"
    elif kind in UNSOURCED_INPUT_KINDS:
        label = "Unresolved"
    elif kind == "userInput":
        label = "User input"
    elif kind == "followsInput":
        rule_kind = record.get("defaultKind")
        rule = (INPUT_KIND_EVIDENCE.get(rule_kind) if isinstance(rule_kind, str) else None) or "Unresolved"
        label = rule
        if rule == "Literature estimate":
            if _text(record.get("sourceLocator")):
                locators = [record["sourceLocator"]]
            else:
                label = "Unresolved"
        deps = record.get("dependsOn")
        followed = [record.get("followsInput")] + (deps if _str_list(deps) else [])
        for other in followed:
            if not isinstance(other, str):
                continue
            other_label, other_locators = _input_label(other, inputs, seen | {name})
            if other_label is None:
                continue
            if LABEL_RANK[other_label] < LABEL_RANK[label]:
                label = other_label
            locators += [loc for loc in other_locators if loc not in locators]
    elif kind == "derived":
        deps = record.get("dependsOn") if _str_list(record.get("dependsOn")) else []
        labels = [(dep,) + _input_label(dep, inputs, seen | {name}) for dep in deps]
        labels = [item for item in labels if item[1] is not None]
        if labels:
            label = min((item[1] for item in labels), key=LABEL_RANK.__getitem__)
            for item in labels:
                locators += [loc for loc in item[2] if loc not in locators]
        elif _text(record.get("sourceLocator")):
            label = "Literature estimate"
            locators = [record["sourceLocator"]]
        else:
            label = "Unresolved"
    else:
        label = "Unresolved"
    # A record never reads stronger than its own label; Measured or an unknown label on an input is refused.
    if not isinstance(own, str) or own not in LABEL_RANK:
        label = "Unresolved"
    elif LABEL_RANK[own] < LABEL_RANK[label]:
        label = own
    return label, (locators if label == "Literature estimate" else [])


def _weakest_roots(name: str, inputs: Mapping[str, Any], label: str, seen: frozenset = frozenset()) -> List[str]:
    """Trace weak labels to their root inputs; an unsourced rule remains its own root."""
    record = inputs.get(name)
    if not isinstance(record, dict) or name in seen:
        return [name]
    kind = record.get("kind")
    if kind not in ("followsInput", "derived"):
        return [name]
    if kind == "followsInput" and record.get("defaultKind") in UNSOURCED_INPUT_KINDS:
        return [name]
    deps = record.get("dependsOn") if _str_list(record.get("dependsOn")) else []
    if kind == "followsInput" and isinstance(record.get("followsInput"), str):
        deps = [record["followsInput"]] + deps
    roots = []
    for dep in deps:
        if _input_label(dep, inputs, seen | {name})[0] == label:
            for root in _weakest_roots(dep, inputs, label, seen | {name}):
                if root not in roots:
                    roots.append(root)
    return roots or [name]


def source_label(inputs: Mapping[str, Any], depends_on: Sequence[str],
                 quantities: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """The decided label rule over the determining inputs of one value.

    Any declaredAssumption or legacyEstimate input (directly, through a followed rule or a derivation) gives
    Unresolved naming those inputs; otherwise any userInput gives User input naming them; otherwise Literature
    estimate with labelSources. Fixed request process names are excluded, regardless of phase. With no determining input
    left the result is Unresolved with no named input: a label is never upgraded by emptiness (envelope_problems
    reports that case for a non-null value). Missing records read Unresolved.

    Returns {"sourceEvidenceKind", "weakestInputs", "labelSources", "determiningInputs"}."""
    names = _determining(depends_on, inputs, quantities)
    labelled: List[Tuple[str, str, List[str]]] = []
    for name in names:
        label, locators = _input_label(name, inputs, frozenset())
        if label is not None:
            labelled.append((name, label, locators))
    if not labelled:
        return {"sourceEvidenceKind": "Unresolved", "weakestInputs": [], "labelSources": [], "determiningInputs": []}
    weakest = min((item[1] for item in labelled), key=LABEL_RANK.__getitem__)
    sources: List[str] = []
    if weakest == "Literature estimate":
        for _, _, locators in labelled:
            sources += [loc for loc in locators if loc not in sources]
    return {
        "sourceEvidenceKind": weakest,
        "weakestInputs": list(dict.fromkeys(root for name, label, _ in labelled
                                            if label == weakest and weakest != "Literature estimate"
                                            for root in _weakest_roots(name, inputs, weakest))),
        "labelSources": sources,
        "determiningInputs": [name for name, _, _ in labelled],
    }


def _content_key(value: Any) -> str:
    """Collision-free content digest, with SI numbers encoded as binary64 float.hex on both runtimes."""
    def encode(item):
        if isinstance(item, bool) or item is None or isinstance(item, str):
            return item
        if isinstance(item, (int, float)):
            return ["number", float(item).hex()] if _is_number(item) else ["invalid", "number"]
        if isinstance(item, list):
            return ["list", [encode(v) for v in item]]
        if isinstance(item, dict):
            return ["object", [[k, encode(v)] for k, v in sorted(item.items())]]
        return ["invalid", type(item).__name__]
    return json.dumps(encode(value), ensure_ascii=False, separators=(",", ":"))


def parent_key(inputs: Mapping[str, Any], depends_on: Sequence[str],
               quantities: Optional[Mapping[str, Any]] = None) -> str:
    """Bind complete input records plus each transitive sibling's identity and full-precision value.

    The content digest is stored directly, without a lossy hash. Reused sourceIds cannot hide changed provenance.
    """
    parts = {}
    def visit(names, seen):
        for name in names:
            if not isinstance(name, str) or name in seen:
                continue
            if name in inputs:
                record = inputs[name]
                parts[name] = {"input": record}
                if isinstance(record, dict):
                    deps = record.get("dependsOn") if _str_list(record.get("dependsOn")) else []
                    if isinstance(record.get("followsInput"), str):
                        deps = deps + [record["followsInput"]]
                    visit(deps, seen | {name})
            elif quantities is not None and isinstance(quantities.get(name), dict):
                sibling = quantities[name]
                parts[name] = {"identity": sibling.get("identity"), "value": sibling.get("value")}
                deps = sibling.get("dependsOn")
                visit(deps if _str_list(deps) else [], seen | {name})
            else:
                parts[name] = None
    visit(depends_on, frozenset())
    return "parents-v2:" + _content_key(parts)


# --- Quantity, observation and container builders ---------------------------------------------------------------

def reason(code: str, params: Optional[Mapping[str, Any]] = None,
           parent: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    if code not in REASON_TEMPLATES:
        raise EnvelopeError(f"unknown reason code {code!r}")
    return {"code": code, "params": dict(params or {}), "parent": dict(parent) if parent is not None else None}


def reason_parent(name: str, inputs: Mapping[str, Any], quantities: Optional[Mapping[str, Any]] = None
                  ) -> Dict[str, str]:
    """{input, kind} naming the blocking input and its provenance kind (a sibling quantity reads "derived")."""
    if name in inputs and isinstance(inputs[name], dict):
        return {"input": name, "kind": inputs[name]["kind"]}
    if quantities is not None and name in quantities:
        return {"input": name, "kind": "derived"}
    raise EnvelopeError(f"reason parent {name!r} is neither an input record nor a sibling quantity")


def numerical_status(state: str = "not-assessed", settings: Optional[Mapping[str, Any]] = None,
                     residuals: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    return {"state": state, "settings": dict(settings or {}), "residuals": dict(residuals or {})}


def source_ref(source_id: str, locator: str, read_level: str) -> Dict[str, str]:
    return {"id": source_id, "locator": locator, "readLevel": read_level}


def quantity(definition: str, value: Any, *, inputs: Mapping[str, Any], depends_on: Sequence[str],
             sources: Sequence[Mapping[str, str]], model_identity: str, uncertainty: Mapping[str, Any],
             status: str = "computed", reasons: Sequence[Mapping[str, Any]] = (),
             numerical: Optional[Mapping[str, Any]] = None, fraction_basis: Optional[str] = None,
             assumptions: Sequence[str] = (), validity: Optional[Mapping[str, Any]] = None,
             input_identity: Optional[str] = None, leaf_role: str = "derived",
             quantities: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """A non-null quantity; its label, named inputs, label sources and parent key come from the rule."""
    if status not in VALUE_STATUSES:
        raise EnvelopeError(f"a value needs status computed or partial, not {status!r}")
    label = source_label(inputs, depends_on, quantities)
    return {
        "status": status, "value": value, "unit": QUANTITY_DEFINITIONS[definition]["unit"],
        "quantityDefinition": definition, "leafRole": leaf_role,
        "sourceEvidenceKind": label["sourceEvidenceKind"], "dependsOn": list(depends_on),
        "weakestInputs": label["weakestInputs"], "labelSources": label["labelSources"],
        "reasons": [dict(item) for item in reasons],
        "numericalStatus": dict(numerical) if numerical is not None else numerical_status(),
        "physicalValidation": dict(PHYSICAL_VALIDATION),
        "sources": [dict(item) for item in sources], "assumptions": list(assumptions),
        "validity": dict(validity) if validity is not None else None,
        "uncertainty": dict(uncertainty), "fractionBasis": fraction_basis,
        "identity": {"input": input_identity, "model": model_identity,
                     "parent": parent_key(inputs, depends_on, quantities)},
    }


def unavailable(definition: str, reasons: Sequence[Mapping[str, Any]], *, status: str = "unavailable",
                depends_on: Sequence[str] = (), leaf_role: str = "derived",
                numerical: Optional[Mapping[str, Any]] = None, assumptions: Sequence[str] = (),
                validity: Optional[Mapping[str, Any]] = None, model_identity: Optional[str] = None,
                input_identity: Optional[str] = None) -> Dict[str, Any]:
    """A null quantity with its reasons: no label, no sources, no uncertainty claim."""
    if status in VALUE_STATUSES:
        raise EnvelopeError(f"status {status!r} carries a value; use quantity()")
    if not reasons:
        raise EnvelopeError("a null quantity needs at least one reason")
    return {
        "status": status, "value": None, "unit": QUANTITY_DEFINITIONS[definition]["unit"],
        "quantityDefinition": definition, "leafRole": leaf_role, "sourceEvidenceKind": None,
        "dependsOn": list(depends_on), "weakestInputs": [], "labelSources": [],
        "reasons": [dict(item) for item in reasons],
        "numericalStatus": dict(numerical) if numerical is not None else numerical_status(),
        "physicalValidation": dict(PHYSICAL_VALIDATION), "sources": [], "assumptions": list(assumptions),
        "validity": dict(validity) if validity is not None else None, "uncertainty": None, "fractionBasis": None,
        "identity": {"input": input_identity, "model": model_identity, "parent": None},
    }


def observation(observable: str, value: Any, unit: str, source_evidence_kind: str,
                sources: Sequence[Mapping[str, str]], *, material_scope: str, process_scope: str,
                comparability: str = "context-only") -> Dict[str, Any]:
    """A transcribed source observation; the only record that may read Measured."""
    return {"recordKind": OBSERVATION_RECORD_KIND, "observable": observable, "value": value, "unit": unit,
            "sourceEvidenceKind": source_evidence_kind, "sources": [dict(item) for item in sources],
            "materialScope": material_scope, "processScope": process_scope, "comparability": comparability}


def container(quantities: Mapping[str, Any], *, module_maturity: str = "Research",
              input_provenance: Optional[Mapping[str, Any]] = None,
              observations: Optional[Mapping[str, Any]] = None, default: Optional[bool] = None) -> Dict[str, Any]:
    """Container keys (4.2, 4.1 item 7). Only an object holding a quantities map carries them."""
    out: Dict[str, Any] = {"quantityEnvelopeSchema": ENVELOPE_SCHEMA, "moduleEvidenceCeiling": MODULE_EVIDENCE_CEILING,
                           "moduleMaturity": module_maturity, "quantities": dict(quantities)}
    if observations is not None:
        out["observations"] = dict(observations)
    if input_provenance is not None:
        out["inputProvenance"] = dict(input_provenance)
    if default is not None:
        out["default"] = default
    return out


# --- Validators -------------------------------------------------------------------------------------------------------

def _value_problems(value: Any, definition: Dict[str, Any], where: str) -> List[str]:
    kind, value_range = definition["valueKind"], definition["valueRange"]

    def number_ok(item: Any) -> Optional[str]:
        if not _is_number(item):
            return "must be a finite number"
        if value_range == "positive" and not item > 0:
            return "must be positive"
        if value_range == "fraction" and not 0 <= item <= 1:
            return "must lie in [0, 1]"
        return None

    problems: List[str] = []
    if kind == "number":
        problem = number_ok(value)
        if problem:
            problems.append(f"{where}.value {problem}")
    elif kind in ("alternatives", "record"):
        members = definition["members"] or list(definition["memberUnits"])
        if not isinstance(value, dict) or sorted(value) != sorted(members):
            problems.append(f"{where}.value must be an object with exactly the members {members}")
        else:
            for member in members:
                problem = number_ok(value[member])
                if problem:
                    problems.append(f"{where}.value.{member} {problem}")
    elif kind == "map":
        if not isinstance(value, dict) or not value or not all(_text(key) for key in value):
            problems.append(f"{where}.value must be a non-empty object keyed by names")
        else:
            for key, item in value.items():
                problem = number_ok(item)
                if problem:
                    problems.append(f"{where}.value.{key} {problem}")
    elif kind == "category":
        if value not in definition["categories"]:
            problems.append(f"{where}.value must be one of {definition['categories']} "
                            "(no admitted category means no non-null value)")
    return problems


def _source_list_problems(sources: Any, where: str) -> List[str]:
    if not isinstance(sources, list):
        return [f"{where} must be a list"]
    problems = []
    for index, item in enumerate(sources):
        if not isinstance(item, dict) or set(item) != {"id", "locator", "readLevel"}:
            problems.append(f"{where}[{index}] must be {{id, locator, readLevel}}")
        elif not (_text(item["id"]) and _text(item["locator"])) or item["readLevel"] not in READ_LEVELS:
            problems.append(f"{where}[{index}] needs id, locator and readLevel in {READ_LEVELS}")
    return problems


def _reason_problems(reasons: Any, where: str, inputs: Mapping[str, Any],
                     quantities: Mapping[str, Any]) -> List[str]:
    if not isinstance(reasons, list):
        return [f"{where}.reasons must be a list"]
    problems = []
    for index, item in enumerate(reasons):
        at = f"{where}.reasons[{index}]"
        if not isinstance(item, dict) or set(item) != {"code", "params", "parent"}:
            problems.append(f"{at} must be {{code, params, parent}} (no text from producers)")
            continue
        code, params, parent = item["code"], item["params"], item["parent"]
        if not isinstance(code, str) or code not in REASON_TEMPLATES:
            problems.append(f"{at}: unknown reason code {code!r}")
            continue
        if not isinstance(params, dict) or not all(isinstance(key, str) and _KEY.match(key) for key in params):
            problems.append(f"{at}.params must be an object keyed by names")
        else:
            for key, value in params.items():
                if value is not None and not (_is_number(value) or isinstance(value, (str, bool))):
                    problems.append(f"{at}.params.{key} must be a scalar")
            missing = [name for name in template_params(REASON_TEMPLATES[code]) if name not in params]
            if missing:
                problems.append(f"{at}: params {missing} are required by the sentence template")
        if parent is not None:
            if not isinstance(parent, dict) or set(parent) != {"input", "kind"}:
                problems.append(f"{at}.parent must be null or {{input, kind}}")
            elif not _text(parent["input"]):
                problems.append(f"{at}.parent.input must be a non-empty string")
            elif parent["input"] in inputs and isinstance(inputs[parent["input"]], dict):
                if parent["kind"] != inputs[parent["input"]].get("kind"):
                    problems.append(f"{at}.parent kind {parent['kind']!r} differs from the input record "
                                    f"{parent['input']!r} ({inputs[parent['input']].get('kind')!r})")
            elif parent["input"] in quantities:
                if parent["kind"] != "derived":
                    problems.append(f"{at}.parent names sibling quantity {parent['input']!r}, whose kind is derived")
            else:
                problems.append(f"{at}.parent {parent['input']!r} is neither an input record nor a sibling quantity "
                                "of this container")
    return problems


def quantity_problems(q: Any, where: str, inputs: Mapping[str, Any],
                      quantities: Mapping[str, Any]) -> List[str]:
    """Problems of one quantity in the context of its container (inputs and sibling quantities)."""
    if not isinstance(q, dict):
        return [f"{where} must be an object"]
    keys = set(q)
    missing = [key for key in QUANTITY_KEYS if key not in keys]
    extra = sorted(keys - set(QUANTITY_KEYS))
    problems: List[str] = []
    if missing:
        problems.append(f"{where}: missing keys {missing}")
    if extra:
        problems.append(f"{where}: unknown keys {extra}")
    if missing:
        return problems
    status, value = q["status"], q["value"]
    if status not in QUANTITY_STATUSES:
        return problems + [f"{where}.status must be one of {QUANTITY_STATUSES}"]
    definition = QUANTITY_DEFINITIONS.get(q["quantityDefinition"]) if isinstance(q["quantityDefinition"], str) else None
    if definition is None:
        return problems + [f"{where}.quantityDefinition {q['quantityDefinition']!r} is not a registered definition"]
    if q["unit"] != definition["unit"]:
        problems.append(f"{where}.unit must be {definition['unit']!r} for {q['quantityDefinition']}")
    role = q["leafRole"]
    if role not in LEAF_ROLES:
        problems.append(f"{where}.leafRole must be one of {LEAF_ROLES}")
    elif role not in LABELLED_ROLES:
        problems.append(f"{where}: a registered quantity definition requires a labelled role")
    has_value = value is not None
    if status in VALUE_STATUSES and not has_value:
        problems.append(f"{where}: status {status} needs a value")
    if status not in VALUE_STATUSES and has_value:
        problems.append(f"{where}: status {status} must carry value null")
    if has_value:
        problems += _value_problems(value, definition, where)
    evidence = q["sourceEvidenceKind"]
    if evidence == "Measured":
        problems.append(f"{where}: Measured never labels a quantity; transcribed measurements are observation "
                        "records")
    elif evidence is not None and evidence not in QUANTITY_SOURCE_EVIDENCE_KINDS:
        problems.append(f"{where}.sourceEvidenceKind must be one of {QUANTITY_SOURCE_EVIDENCE_KINDS} or null")
    for key in ("dependsOn", "weakestInputs", "labelSources", "assumptions"):
        if not _str_list(q[key]):
            problems.append(f"{where}.{key} must be a list of non-empty strings")
    if _str_list(q["dependsOn"]):
        unknown = [name for name in q["dependsOn"] if name not in inputs and name not in quantities]
        if unknown:
            problems.append(f"{where}.dependsOn names {unknown}, which are neither input records nor sibling "
                            "quantities of this container")
    if not has_value and evidence is not None:
        problems.append(f"{where}: a null value carries no source label")
    if not has_value:
        if q["uncertainty"] is not None:
            problems.append(f"{where}: a null value carries no uncertainty")
        if isinstance(q["identity"], dict) and q["identity"].get("parent") is not None:
            problems.append(f"{where}: a null value carries no parent identity")
        if not q["dependsOn"]:
            problems.append(f"{where}: a null quantity must name its blocking input or sibling in dependsOn")
    if evidence is None and (q["weakestInputs"] or q["labelSources"]):
        problems.append(f"{where}: weakestInputs and labelSources stay empty without a source label")
    if role in UNLABELLED_ROLES and evidence is not None:
        problems.append(f"{where}: a {role} leaf carries no source label")
    if role == "requestInput" and evidence not in (None, "User input"):
        problems.append(f"{where}: a request echo reads User input or null, never {evidence!r}")
    if has_value and role in LABELLED_ROLES and _str_list(q["dependsOn"]):
        expected = source_label(inputs, q["dependsOn"], quantities)
        if not expected["determiningInputs"]:
            problems.append(f"{where}: no determining physical or coefficient input; request process values never "
                            "decide a label")
        if evidence is None:
            problems.append(f"{where}: a non-null {role} value needs its per-value source label")
        elif evidence != expected["sourceEvidenceKind"]:
            problems.append(f"{where}: source label {evidence!r} differs from the label rule "
                            f"({expected['sourceEvidenceKind']!r}); no upgrade or downgrade by hand")
        if evidence in ("User input", "Unresolved") and not q["weakestInputs"]:
            problems.append(f"{where}: {evidence} must name its inputs (weakestInputs)")
        if evidence == "Literature estimate" and not q["labelSources"]:
            problems.append(f"{where}: Literature estimate needs its labelSources")
        if q["weakestInputs"] != expected["weakestInputs"] or q["labelSources"] != expected["labelSources"]:
            problems.append(f"{where}: weakestInputs/labelSources differ from the label rule "
                            f"({expected['weakestInputs']}, {expected['labelSources']})")
    problems += _reason_problems(q["reasons"], where, inputs, quantities)
    if isinstance(q["reasons"], list):
        codes = [item.get("code") for item in q["reasons"] if isinstance(item, dict)]
        if status == "computed" and codes:
            problems.append(f"{where}: a computed value carries no blocking reason")
        if status != "computed" and not codes:
            problems.append(f"{where}: status {status} needs at least one reason")
        if status == "not-requested" and "not-requested" not in codes:
            problems.append(f"{where}: status not-requested carries the reason not-requested")
    numerical = q["numericalStatus"]
    if not (isinstance(numerical, dict) and set(numerical) == {"state", "settings", "residuals"}
            and numerical["state"] in NUMERICAL_STATES and isinstance(numerical["settings"], dict)
            and isinstance(numerical["residuals"], dict)):
        problems.append(f"{where}.numericalStatus must be {{state in {NUMERICAL_STATES}, settings, residuals}}")
    physical = q["physicalValidation"]
    if not (isinstance(physical, dict) and set(physical) == set(PHYSICAL_VALIDATION)
            and physical["status"] == "unvalidated" and physical["experimentalValidation"] is False
            and physical["productionReady"] is False):
        problems.append(f"{where}.physicalValidation must be {PHYSICAL_VALIDATION}")
    problems += _source_list_problems(q["sources"], f"{where}.sources")
    if not has_value and q["sources"]:
        problems.append(f"{where}: a null value carries no source claim (no stale DOI on a null value)")
    if q["validity"] is not None and not isinstance(q["validity"], dict):
        problems.append(f"{where}.validity must be an object or null")
    uncertainty = q["uncertainty"]
    if uncertainty is not None:
        if not (isinstance(uncertainty, dict) and set(uncertainty) == {"kind", "construction"}
                and uncertainty["kind"] in UNCERTAINTY_KINDS
                and (uncertainty["construction"] is None or _text(uncertainty["construction"]))):
            problems.append(f"{where}.uncertainty must be {{kind in {UNCERTAINTY_KINDS}, construction}}")
        elif definition["valueKind"] == "alternatives" and uncertainty["kind"] != "model-alternatives":
            problems.append(f"{where}: two source models are model alternatives, never an interval")
    basis = q["fractionBasis"]
    if basis is not None and basis not in FRACTION_BASES:
        problems.append(f"{where}.fractionBasis must be one of {FRACTION_BASES} or null")
    if basis is not None and not definition["fraction"]:
        problems.append(f"{where}: fractionBasis applies only to fraction quantities")
    identity = q["identity"]
    if not (isinstance(identity, dict) and set(identity) == {"input", "model", "parent"}
            and all(identity[key] is None or _text(identity[key]) for key in identity)):
        problems.append(f"{where}.identity must be {{input, model, parent}} strings or null")
        identity = None
    if has_value and role in LABELLED_ROLES:
        if not q["dependsOn"]:
            problems.append(f"{where}: a non-null value names the inputs it depends on")
        if not q["sources"]:
            problems.append(f"{where}: a non-null value names its source relation (sources)")
        if uncertainty is None:
            problems.append(f"{where}: a non-null value states its uncertainty (at least not-quantified)")
        if definition["fraction"] and basis is None:
            problems.append(f"{where}: a fraction needs its fractionBasis")
        if identity is not None:
            if not identity["model"]:
                problems.append(f"{where}: a non-null value names its engine/model identity")
            expected_parent = parent_key(inputs, q["dependsOn"], quantities) if _str_list(q["dependsOn"]) else None
            if not identity["parent"]:
                problems.append(f"{where}: a non-null value names its parent identity")
            elif identity["parent"] != expected_parent:
                problems.append(f"{where}: parent identity {identity['parent']!r} is not the current parent "
                                f"{expected_parent!r}; a stale-parent value is not current")
    return problems


def observation_problems(o: Any, where: str) -> List[str]:
    if not isinstance(o, dict):
        return [f"{where} must be an object"]
    problems = []
    if set(o) != set(OBSERVATION_KEYS):
        return [f"{where}: keys must be exactly {list(OBSERVATION_KEYS)}"]
    if o["recordKind"] != OBSERVATION_RECORD_KIND:
        problems.append(f"{where}.recordKind must be {OBSERVATION_RECORD_KIND!r}")
    if not _text(o["observable"]):
        problems.append(f"{where}.observable must name the transcribed observable")
    value = o["value"]
    if not (_is_number(value) or (isinstance(value, dict) and value
                                  and all(_text(k) and _is_number(v) for k, v in value.items()))):
        problems.append(f"{where}.value must be a finite number or an object of finite numbers")
    if o["unit"] not in UNITS:
        problems.append(f"{where}.unit must be one of {UNITS}")
    if o["sourceEvidenceKind"] not in OBSERVATION_SOURCE_EVIDENCE_KINDS:
        problems.append(f"{where}.sourceEvidenceKind must be one of {OBSERVATION_SOURCE_EVIDENCE_KINDS}")
    problems += _source_list_problems(o["sources"], f"{where}.sources")
    if not o["sources"]:
        problems.append(f"{where}: an observation names its source")
    for key in ("materialScope", "processScope"):
        if not _text(o[key]):
            problems.append(f"{where}.{key} must be a non-empty string")
    if o["comparability"] not in COMPARABILITY:
        problems.append(f"{where}.comparability must be one of {COMPARABILITY}")
    return problems


def container_problems(c: Any, where: str, module_maturity: Optional[str] = None) -> List[str]:
    """Problems of one container (an object holding a quantities map)."""
    if not isinstance(c, dict):
        return [f"{where} must be an object"]
    problems: List[str] = []
    for key in CONTAINER_REQUIRED_KEYS:
        if key not in c:
            problems.append(f"{where}: a container carries {key}")
    if c.get("quantityEnvelopeSchema") != ENVELOPE_SCHEMA:
        problems.append(f"{where}.quantityEnvelopeSchema must be {ENVELOPE_SCHEMA!r}")
    if c.get("moduleEvidenceCeiling") != MODULE_EVIDENCE_CEILING:
        problems.append(f"{where}.moduleEvidenceCeiling must be {MODULE_EVIDENCE_CEILING!r} (decision 1)")
    if c.get("moduleMaturity") not in MODULE_MATURITIES:
        problems.append(f"{where}.moduleMaturity must be one of {MODULE_MATURITIES}")
    elif module_maturity is not None and c.get("moduleMaturity") != module_maturity:
        problems.append(f"{where}.moduleMaturity must echo the registry label {module_maturity!r}")
    quantities = c.get("quantities")
    if not isinstance(quantities, dict):
        return problems + [f"{where}.quantities must be an object"]
    inputs = c.get("inputProvenance", {})
    if not isinstance(inputs, dict):
        problems.append(f"{where}.inputProvenance must be an object")
        inputs = {}
    for name, record in inputs.items():
        if not (isinstance(name, str) and _KEY.match(name)):
            problems.append(f"{where}.inputProvenance key {name!r} must be a plain name")
        problems += input_record_problems(record, f"{where}.inputProvenance.{name}")
        if isinstance(record, dict) and record.get("kind") == "sourcedAlternative" and c.get("default") is not False:
            problems.append(f"{where}: sourcedAlternative requires container default: false")
    if "default" in c and not isinstance(c["default"], bool):
        problems.append(f"{where}.default must be a boolean")
    overlap = sorted(set(inputs) & set(quantities))
    if overlap:
        problems.append(f"{where}: names {overlap} are both an input and a quantity")
    observations = c.get("observations", {})
    if not isinstance(observations, dict):
        problems.append(f"{where}.observations must be an object")
        observations = {}
    for name, record in observations.items():
        problems += observation_problems(record, f"{where}.observations.{name}")
    for name, q in quantities.items():
        if not (isinstance(name, str) and _KEY.match(name)):
            problems.append(f"{where}.quantities key {name!r} must be a plain name")
        problems += quantity_problems(q, f"{where}.quantities.{name}", inputs, quantities)
    # Parent propagation: a dependent of a null sibling is null and names that parent in a reason.
    for name, q in quantities.items():
        if not isinstance(q, dict) or not _str_list(q.get("dependsOn")):
            continue
        for dep in q["dependsOn"]:
            parent_q = quantities.get(dep) if dep not in inputs else None
            if not isinstance(parent_q, dict) or parent_q.get("value") is not None:
                continue
            if q.get("value") is not None:
                problems.append(f"{where}.quantities.{name}: parent quantity {dep!r} is null, so this value is null")
            elif not any(isinstance(item, dict) and isinstance(item.get("parent"), dict)
                         and item["parent"].get("input") == dep for item in q.get("reasons") or []):
                problems.append(f"{where}.quantities.{name}: a reason must name the null parent {dep!r}")
    return problems


def _walk(obj: Any, path: Tuple[str, ...], decl: Tuple[str, ...], out: List[Tuple[str, str, Any]],
          strays: List[str]) -> None:
    if isinstance(obj, dict):
        if isinstance(obj.get("quantities"), dict):
            out.append((".".join(path) or "<top>", ".".join(decl), obj))
        elif any(key in obj for key in CONTAINER_ONLY_KEYS):
            strays.append(".".join(path) or "<top>")
        for key, value in obj.items():
            if key == "quantities" and isinstance(value, dict):
                continue  # quantities never hold nested containers
            _walk(value, path + (str(key),), decl + (str(key),), out, strays)
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            _walk(item, path + (f"[{index}]",), decl, out, strays)


def find_containers(obj: Any) -> List[Tuple[str, str, Any]]:
    """(where, declaration prefix, container) for every object holding a quantities map (list indices dropped)."""
    out: List[Tuple[str, str, Any]] = []
    _walk(obj, (), (), out, [])
    return out


def _declarations(declaration: Any) -> Tuple[list, list]:
    if declaration is None:
        return [], []
    if hasattr(declaration, "quantities") and hasattr(declaration, "observations"):
        return list(declaration.quantities), list(declaration.observations)
    quantities, observations = [], []
    for item in declaration:
        (observations if hasattr(item, "observable") else quantities).append(item)
    return quantities, observations


def envelope_problems(obj: Any, declaration: Any = None, *, module_maturity: Optional[str] = None) -> List[str]:
    """Every envelope problem in ``obj`` (a payload with zero or more containers), optionally against declarations.

    ``declaration`` is an Operation-like object (``quantities`` and ``observations``) or an iterable of
    QuantityDeclaration / ObservationDeclaration objects (module_contract). Declared paths are dot paths from the
    payload top (list levels are traversed); a container present in the payload must hold exactly its declared
    quantities and observations, and each one must stay inside its declared statuses, codes and kinds."""
    out: List[Tuple[str, str, Any]] = []
    strays: List[str] = []
    _walk(obj, (), (), out, strays)
    problems = [f"{where}: carries container keys without a quantities map (one placement, 4.1 item 7)"
                for where in strays]
    for where, _, c in out:
        problems += container_problems(c, where, module_maturity)
    quantity_decls, observation_decls = _declarations(declaration)
    if declaration is None:
        return problems
    by_quantity = {decl.path: decl for decl in quantity_decls}
    by_observation = {decl.path: decl for decl in observation_decls}
    for where, prefix, c in out:
        base = f"{prefix}." if prefix else ""
        for name, q in c["quantities"].items():
            path = f"{base}quantities.{name}"
            decl = by_quantity.get(path)
            if decl is None:
                problems.append(f"{where}.quantities.{name}: not declared ({path})")
                continue
            if not isinstance(q, dict):
                continue
            at = f"{where}.quantities.{name}"
            if q.get("quantityDefinition") != decl.definition or q.get("unit") != decl.unit:
                problems.append(f"{at}: definition/unit differ from the declaration ({decl.definition}, {decl.unit})")
            if q.get("status") not in decl.statuses:
                problems.append(f"{at}: status {q.get('status')!r} is not declared ({list(decl.statuses)})")
            if q.get("leafRole") != decl.leaf_role:
                problems.append(f"{at}: leafRole {q.get('leafRole')!r} differs from the declaration ({decl.leaf_role})")
            if q.get("sourceEvidenceKind") is not None and q.get("sourceEvidenceKind") not in decl.source_evidence_kinds:
                problems.append(f"{at}: source label {q.get('sourceEvidenceKind')!r} is not declared "
                                f"({list(decl.source_evidence_kinds)})")
            for item in q.get("reasons") or []:
                if isinstance(item, dict) and item.get("code") not in decl.reason_codes:
                    problems.append(f"{at}: reason code {item.get('code')!r} is not declared")
            if q.get("value") is not None and q.get("fractionBasis") != decl.fraction_basis:
                problems.append(f"{at}: fractionBasis {q.get('fractionBasis')!r} differs from the declaration "
                                f"({decl.fraction_basis})")
        for name, o in (c.get("observations") or {}).items():
            path = f"{base}observations.{name}"
            decl = by_observation.get(path)
            at = f"{where}.observations.{name}"
            if decl is None:
                problems.append(f"{at}: not declared ({path})")
                continue
            if isinstance(o, dict):
                if o.get("observable") != decl.observable:
                    problems.append(f"{at}: observable differs from the declaration ({decl.observable!r})")
                if o.get("sourceEvidenceKind") not in decl.source_evidence_kinds:
                    problems.append(f"{at}: source label {o.get('sourceEvidenceKind')!r} is not declared")
        present = {f"{base}quantities.{name}" for name in c["quantities"]}
        present |= {f"{base}observations.{name}" for name in (c.get("observations") or {})}
        for path in list(by_quantity) + list(by_observation):
            container_path = path.rsplit(".", 2)[0] if path.count(".") >= 2 else ""
            if container_path == prefix and path not in present:
                problems.append(f"{where}: declared {path} is missing from this container")
    return problems


def typescript_document() -> Dict[str, Any]:
    """Vocabularies emitted to src/generated/quantityEnvelope.ts by module_registry (sentence templates included)."""
    return {
        "schema": ENVELOPE_SCHEMA,
        "moduleEvidenceCeiling": MODULE_EVIDENCE_CEILING,
        "moduleMaturities": list(MODULE_MATURITIES),
        "containerHeaderText": dict(CONTAINER_HEADER_TEXT),
        "statuses": list(QUANTITY_STATUSES),
        "valueStatuses": list(VALUE_STATUSES),
        "statusLabels": dict(STATUS_LABELS),
        "reasonCodes": list(REASON_CODES),
        "reasonTemplates": {code: {"template": text, "params": list(template_params(text))}
                            for code, text in REASON_TEMPLATES.items()},
        "units": list(UNITS),
        "valueKinds": list(VALUE_KINDS),
        "quantityDefinitions": copy.deepcopy(QUANTITY_DEFINITIONS),
        "uncertaintyKinds": list(UNCERTAINTY_KINDS),
        "fractionBases": list(FRACTION_BASES),
        "numericalStates": list(NUMERICAL_STATES),
        "readLevels": list(READ_LEVELS),
        "physicalValidation": dict(PHYSICAL_VALIDATION),
        "sourceEvidenceKinds": list(SOURCE_EVIDENCE_KINDS),
        "quantitySourceEvidenceKinds": list(QUANTITY_SOURCE_EVIDENCE_KINDS),
        "observationSourceEvidenceKinds": list(OBSERVATION_SOURCE_EVIDENCE_KINDS),
        "labelRank": dict(LABEL_RANK),
        "sourceLabelDisplay": dict(SOURCE_LABEL_DISPLAY),
        "leafRoles": list(LEAF_ROLES),
        "labelledRoles": list(LABELLED_ROLES),
        "unlabelledRoles": list(UNLABELLED_ROLES),
        "inputKinds": list(INPUT_KINDS),
        "sourcedInputKinds": list(SOURCED_INPUT_KINDS),
        "unsourcedInputKinds": list(UNSOURCED_INPUT_KINDS),
        "inputKindLabels": dict(INPUT_KIND_LABELS),
        "inputKindEvidence": dict(INPUT_KIND_EVIDENCE),
        "inputStatuses": list(INPUT_STATUSES),
        "inputPhases": list(INPUT_PHASES),
        "processPhase": PROCESS_PHASE,
        "requestProcessInputs": list(REQUEST_PROCESS_INPUTS),
        "followStates": list(FOLLOW_STATES),
        "inputRecordKeys": list(INPUT_RECORD_KEYS),
        "quantityKeys": list(QUANTITY_KEYS),
        "observationRecordKind": OBSERVATION_RECORD_KIND,
        "observationKeys": list(OBSERVATION_KEYS),
        "comparability": list(COMPARABILITY),
        "containerRequiredKeys": list(CONTAINER_REQUIRED_KEYS),
        "containerOptionalKeys": list(CONTAINER_OPTIONAL_KEYS),
        "canonicalAlloyIds": list(CANONICAL_ALLOY_IDS),
    }
