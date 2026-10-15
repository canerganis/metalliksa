"""Module contract schema (Phase 7 step 0 skeleton).

Stdlib-only frozen dataclasses that describe one product module: identity,
maturity, navigation, operations and their authority, canonical input fields,
validity domain, evidence ceiling, lifecycle, test references and migration
state. See .orchestra/DESIGN-7-module-sdk.md (section 1).

Every vocabulary below is closed. Validation happens in ``__post_init__`` so an
invalid contract cannot be constructed. The contract never computes or upgrades
an evidence status; it only bounds what a module may report. Quantity envelope
declarations (QuantityDeclaration, ObservationDeclaration) take their closed
vocabularies from python/quantity_envelope.py (stdlib only, outside the LPBF
fingerprint manifest).

Items marked TODO(maintainer-review) are skeleton defaults, not reviewed facts.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Optional, Tuple, Union

import quantity_envelope as _envelope

# --- Closed vocabularies ---------------------------------------------------

# Mirrors EVIDENCE_TYPES in src/types/research.ts (order preserved).
# TODO(maintainer-review): reusing the research.ts source-classification enum
# as the run-output status vocabulary is unreviewed
# (.orchestra/REVIEW-prep-opus-python.md, maintainer item 2).
# TODO(maintainer-review): "unresolved" is both an evidence type here and,
# semantically, close to a run state (no claim); the double meaning is
# unreviewed (.orchestra/REVIEW-prep-opus-python.md, maintainer item 8).
EVIDENCE_TYPES: Tuple[str, ...] = (
    "measured",
    "validated-simulation",
    "calibrated-simulation",
    "literature-estimate",
    "screening-only",
    "unresolved",
)
# Run states describe why a result carries no evidence claim. They never
# exceed any ceiling and are always allowed in ``emits``.
RUN_STATES: Tuple[str, ...] = (
    "unvalidated",
    "inconclusive",
    "unavailable",
    "outside-validity-domain",
)
EVIDENCE_STATUSES: Tuple[str, ...] = EVIDENCE_TYPES + RUN_STATES

# TODO(maintainer-review): strength order used only for ceiling comparison.
# Lower index = stronger claim. The relative position of literature-estimate
# and screening-only is a skeleton assumption pending review
# (.orchestra/REVIEW-prep-opus-python.md, maintainer item 1).
EVIDENCE_RANK = {status: index for index, status in enumerate(EVIDENCE_TYPES)}

# Ceiling cap applied while a module's oracle test is pending (design 1).
# TODO(maintainer-review): this cap also blocks literature-estimate (e.g. DB
# lookups) until an oracle exists (.orchestra/REVIEW-prep-opus-python.md,
# maintainer item 3).
PENDING_ORACLE_CEILING = "screening-only"

# Claim keys a module output must never set truthy unless allowed (design 1).
# TODO(maintainer-review): exact, case-sensitive, top-level closed list;
# synonyms (isQualified, certifiable, flightReady, approved, compliant) are not
# covered and a field named "measured" is barred even at a measured ceiling
# (.orchestra/REVIEW-prep-opus-python.md, maintainer item 5).
FORBIDDEN_CLAIM_KEYS: Tuple[str, ...] = (
    "qualified",
    "certified",
    "validated",
    "measured",
    "productionReady",
    "airworthy",
)
# TODO(maintainer-review): claims forbidden for every module while maturity
# is barred from Production (roadmap G03). Hard-coded until G03
# (.orchestra/REVIEW-prep-opus-python.md, maintainer item 6).
ALWAYS_FORBIDDEN_CLAIMS: Tuple[str, ...] = ("qualified", "certified", "productionReady", "airworthy")

MATURITY = ("Research", "Preview")  # Production barred until roadmap G03.
NAVIGATION = ("listed", "hidden")
WORKSPACES = ("lpbf", "materials", "evidence")
AUTHORITY_KINDS = ("python-ipc", "lpbf-worker", "browser-local", "node-provider")
GPU_MODES = ("none", "optional", "required")
BACKGROUND_WORK = ("none", "pausable", "server-job")
LIFECYCLE_RESOURCES = ("raf", "interval", "three", "fetch")
ORACLE_STATES = ("present", "pending")
MIGRATION_STATES = ("legacy", "contracted")
HTTP_METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH")
# Field value types. number/integer carry a canonical unit; boolean/enum carry none.
VALUE_TYPES = ("number", "integer", "boolean", "enum")

TODO_MARKER = "TODO(maintainer-review)"
# Explicit owner marker: no person or team has been assigned by a maintainer yet.
OWNER_UNASSIGNED = "unassigned (needs maintainer)"
# Identity text that originates in python/module_registry_seed.json (copied from the old UI
# list without review). A contract lists which of these it still inherits unreviewed.
SEED_TEXT_FIELDS = ("label", "description", "next", "maturity")

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_MODULE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

Scalar = Union[float, int, str, bool]


class ContractError(ValueError):
    """Raised when a contract violates the schema."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _one_of(value: str, allowed: Tuple[str, ...], name: str) -> None:
    _require(value in allowed, f"{name} must be one of {allowed}, got {value!r}")


def _text(value: Any, name: str) -> None:
    _require(isinstance(value, str) and value.strip() != "", f"{name} must be a non-empty string")


def _finite(value: Any, name: str) -> None:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
             f"{name} must be a finite number")


def _unique(values: Tuple[Any, ...], name: str) -> None:
    _require(len(set(values)) == len(values), f"{name} must not contain duplicates")


def evidence_rank(status: str) -> Optional[int]:
    """Rank of an evidence type, or None for run states (no claim)."""
    return EVIDENCE_RANK.get(status)


def within_ceiling(status: str, ceiling: str) -> bool:
    """True when ``status`` does not claim more than ``ceiling``."""
    _one_of(status, EVIDENCE_STATUSES, "status")
    _one_of(ceiling, EVIDENCE_TYPES, "ceiling")
    rank = evidence_rank(status)
    return rank is None or rank >= EVIDENCE_RANK[ceiling]


# --- Building blocks -------------------------------------------------------

def _is_integer(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and float(value).is_integer())


@dataclass(frozen=True)
class InputField:
    """One request key, with a fixed unit or an explicit selector-to-unit map.

    ``min``/``max`` are hard bounds (outside -> reject). A bound is None when no
    limit is established from the authority code or a source; it is never guessed.
    Selected-unit values pass unchanged to the authority; bounds/steps cannot
    silently apply across multiple scales. Operation validates the enum linkage.
    """
    key: str
    label: str
    unit: Optional[str]  # fixed canonical unit, or None with a closed selected-unit map
    quantity_kind: str
    min: Optional[float]
    max: Optional[float]
    default: Scalar
    required: bool = True
    step: Optional[float] = None
    display_units: Tuple[str, ...] = ()
    enum: Tuple[str, ...] = ()
    value_type: str = "number"
    # Recorded fact about how the authority treats this key (e.g. clamps instead of rejecting).
    note: Optional[str] = None
    unit_selector: Optional[str] = None
    unit_options: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _require(isinstance(self.key, str) and bool(_KEY.match(self.key)), f"invalid field key {self.key!r}")
        _text(self.label, f"{self.key}.label")
        _text(self.quantity_kind, f"{self.key}.quantityKind")
        _one_of(self.value_type, VALUE_TYPES, f"{self.key}.valueType")
        _require(isinstance(self.required, bool), f"{self.key}.required must be a boolean")
        _unique(self.display_units, f"{self.key}.displayUnits")
        if self.note is not None:
            _text(self.note, f"{self.key}.note")
        numeric = self.value_type in ("number", "integer")
        selected_unit = self.unit_selector is not None
        if selected_unit:
            _require(numeric, f"{self.key}: only numeric fields may select a unit")
            _require(isinstance(self.unit_selector, str) and bool(_KEY.fullmatch(self.unit_selector)),
                     f"{self.key}: unitSelector must name an input field")
            _require(self.unit is None and self.min is None and self.max is None and self.step is None,
                     f"{self.key}: selected units have no fixed unit or cross-scale bounds/step")
            _require(len(self.unit_options) > 0, f"{self.key}: selected units need a closed map")
            _unique(tuple(choice for choice, _ in self.unit_options), f"{self.key}.unitOptions keys")
            for choice, unit in self.unit_options:
                _text(choice, f"{self.key}.unitOptions key")
                _text(unit, f"{self.key}.unitOptions unit")
        else:
            _require(not self.unit_options, f"{self.key}: unitOptions require a unitSelector")
        if numeric:
            if not selected_unit:
                _text(self.unit, f"{self.key}.unit")
            for bound in ("min", "max"):
                if getattr(self, bound) is not None:
                    _finite(getattr(self, bound), f"{self.key}.{bound}")
            if self.min is not None and self.max is not None:
                _require(self.min <= self.max, f"{self.key}: min must not exceed max")
            if self.step is not None:
                _finite(self.step, f"{self.key}.step")
                _require(self.step > 0, f"{self.key}.step must be positive")
            _require(not self.enum, f"{self.key}: enum applies only to valueType 'enum'")
        else:
            _require(self.unit is None and self.min is None and self.max is None and self.step is None
                     and not self.display_units,
                     f"{self.key}: {self.value_type} fields carry no unit, bounds or step")
        if self.value_type == "enum":
            _require(len(self.enum) > 0, f"{self.key}: enum fields need values")
            _unique(self.enum, f"{self.key}.enum")
            for value in self.enum:
                _text(value, f"{self.key}.enum")
        else:
            _require(not self.enum, f"{self.key}: enum applies only to valueType 'enum'")
        problem = self.value_problem(self.default)
        _require(problem is None, f"{self.key}: default {problem}")
        if self.value_type == "integer" and self.step is not None:
            _require(_is_integer(self.step), f"{self.key}.step must be an integer")

    def value_problem(self, value: Any) -> Optional[str]:
        """Why ``value`` is not acceptable for this field, or None. Hard bounds reject."""
        if self.value_type == "boolean":
            return None if isinstance(value, bool) else "must be a boolean"
        if self.value_type == "enum":
            return None if isinstance(value, str) and value in self.enum else f"must be one of {list(self.enum)}"
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return "must be a finite number"
        if self.value_type == "integer" and not _is_integer(value):
            return "must be an integer"
        if self.min is not None and value < self.min:
            return f"must be >= {self.min}"
        if self.max is not None and value > self.max:
            return f"must be <= {self.max}"
        return None

    def to_dict(self) -> dict:
        return {
            "key": self.key, "label": self.label, "valueType": self.value_type, "unit": self.unit,
            "displayUnits": list(self.display_units), "quantityKind": self.quantity_kind,
            "min": self.min, "max": self.max, "step": self.step, "default": self.default,
            "required": self.required, "enum": list(self.enum), "note": self.note,
            "unitSelector": self.unit_selector, "unitOptions": dict(self.unit_options),
        }


@dataclass(frozen=True)
class Authority:
    kind: str
    # None means the code declares no timeout for this authority (browser-local,
    # node-provider). python-ipc and lpbf-worker always run under a deadline.
    timeout_ms: Optional[int] = None
    gpu: str = "none"
    warm: bool = False
    script: Optional[str] = None
    worker_method: Optional[str] = None
    exception_reason: Optional[str] = None

    def __post_init__(self) -> None:
        _one_of(self.kind, AUTHORITY_KINDS, "authority.kind")
        _one_of(self.gpu, GPU_MODES, "authority.gpu")
        if self.timeout_ms is not None or self.kind in ("python-ipc", "lpbf-worker"):
            _require(isinstance(self.timeout_ms, int) and not isinstance(self.timeout_ms, bool)
                     and self.timeout_ms > 0, "authority.timeoutMs must be a positive integer")
        _require(isinstance(self.warm, bool), "authority.warm must be a boolean")
        if self.warm:
            # Only the persistent Python IPC service keeps modules warm.
            _require(self.kind == "python-ipc", "authority.warm applies only to python-ipc")
        if self.kind == "python-ipc":
            _text(self.script, "authority.script")
        if self.kind == "lpbf-worker":
            _text(self.worker_method, "authority.workerMethod")
        if self.kind == "browser-local":
            # Recorded debt against the single-authority rule (design 1).
            _text(self.exception_reason, "authority.exceptionReason")

    def to_dict(self) -> dict:
        return {
            "kind": self.kind, "script": self.script, "workerMethod": self.worker_method,
            "timeoutMs": self.timeout_ms, "gpu": self.gpu, "warm": self.warm,
            "exceptionReason": self.exception_reason,
        }


def looks_like_status_key(key: str) -> bool:
    """Output keys a reader could take for a result/evidence status (case and '_' ignored)."""
    norm = key.replace("_", "").lower()
    return norm.endswith("status") or norm.startswith("evidence")


@dataclass(frozen=True)
class OutputSchema:
    fields: Tuple[str, ...]
    # Top-level key carrying the run's evidence status. None records that the
    # authority's output carries no evidence status at all (then emits is empty).
    status_key: Optional[str] = "evidenceStatus"
    # Status-like fields that are transport values, with every value the authority
    # can put there (e.g. ("status", ("success",))). Explicit availability-only
    # outputs may use unavailable without emitting evidence; claims stay forbidden.
    transport_values: Tuple[Tuple[str, Tuple[str, ...]], ...] = ()
    # Object-valued transport fields: explicit dot paths to status leaves, each
    # with its own closed vocabulary. Other result metadata is not asserted to
    # be validated by this inventory (e.g. reason text or numerical brackets).
    transport_objects: Tuple[Tuple[str, Tuple[Tuple[str, Tuple[str, ...]], ...]], ...] = ()

    def __post_init__(self) -> None:
        _require(len(self.fields) > 0, "output.fields must not be empty")
        _unique(self.fields, "output.fields")
        for key in self.fields:
            _require(key not in FORBIDDEN_CLAIM_KEYS, f"output field {key!r} is a forbidden claim key")
        transport = dict(self.transport_values)
        _require(len(transport) == len(self.transport_values), "output.transportValues keys must be unique")
        objects = dict(self.transport_objects)
        _require(len(objects) == len(self.transport_objects), "output.transportObjects keys must be unique")
        _require(not set(objects) & set(transport), "output transport scalar/object declarations cannot overlap")
        for key, values in transport.items():
            _require(key in self.fields, f"output.transportValues key {key!r} is not an output field")
            _require(key != self.status_key, f"output.transportValues cannot describe the status key {key!r}")
            _require(not key.replace("_", "").lower().startswith("evidence"),
                     f"output.transportValues cannot hide evidence field {key!r}")
            _require(len(values) > 0, f"output.transportValues[{key!r}] needs values")
            _unique(values, f"output.transportValues[{key!r}]")
            for value in values:
                _text(value, f"output.transportValues[{key!r}]")
                availability_only = value == "unavailable" and self.status_key is None
                _require((value not in EVIDENCE_STATUSES or availability_only) and value not in FORBIDDEN_CLAIM_KEYS,
                         f"output.transportValues[{key!r}] value {value!r} is an evidence status or claim")
        for key, members in objects.items():
            _require(key in self.fields, f"output.transportObjects key {key!r} is not an output field")
            _require(key != self.status_key, f"output.transportObjects cannot describe the status key {key!r}")
            _require(not key.replace("_", "").lower().startswith("evidence"),
                     f"output.transportObjects cannot hide evidence field {key!r}")
            _require(len(members) > 0, f"output.transportObjects[{key!r}] needs status paths")
            _unique(tuple(path for path, _ in members), f"output.transportObjects[{key!r}] paths")
            for path, values in members:
                _text(path, "output.transportObjects path")
                parts = path.split(".")
                _require(len(parts) >= 2 and all(_KEY.fullmatch(part) for part in parts),
                         f"output.transportObjects path {path!r} must name an explicit nested status leaf")
                _require(looks_like_status_key(parts[-1]), f"transport object path {path!r} must end in a status leaf")
                _require(all(part not in FORBIDDEN_CLAIM_KEYS and
                             not part.replace("_", "").lower().startswith("evidence") for part in parts),
                         f"transport object path {path!r} hides evidence or a claim")
                _require(len(values) > 0, f"transport object path {path!r} needs values")
                _unique(values, f"transport object path {path!r} values")
                for value in values:
                    _text(value, f"transport object path {path!r} value")
                    availability_only = value == "unavailable" and self.status_key is None
                    _require((value not in EVIDENCE_STATUSES or availability_only) and value not in FORBIDDEN_CLAIM_KEYS,
                             f"transport object path {path!r} value {value!r} is an evidence status or claim")
        for key in self.fields:
            if key != self.status_key and looks_like_status_key(key):
                # Without this, a contract with statusKey None could hide a real status field.
                _require(key in transport or key in objects, f"output field {key!r} looks like a status key; declare it as the "
                                           "statusKey or list its transport values")
        if self.status_key is None:
            return
        _text(self.status_key, "output.statusKey")
        # The status key is reserved by the same claim names as the fields.
        _require(self.status_key not in FORBIDDEN_CLAIM_KEYS,
                 f"output.statusKey {self.status_key!r} is a forbidden claim key")
        _require(self.status_key not in self.fields,
                 f"output.statusKey {self.status_key!r} collides with an output field")

    def to_dict(self) -> dict:
        return {"fields": list(self.fields), "statusKey": self.status_key,
                "transportValues": {key: list(values) for key, values in self.transport_values},
                "transportObjects": {key: {path: list(values) for path, values in members}
                                     for key, members in self.transport_objects}}


def _envelope_path(path: Any, member: str, name: str) -> Tuple[str, ...]:
    """Segments of a quantity/observation path: ``[container.]member.leaf`` with ``member`` exactly once."""
    _require(isinstance(path, str) and path != "", f"{name}.path must be a non-empty string")
    parts = tuple(path.split("."))
    _require(len(parts) >= 2 and all(_KEY.fullmatch(part) for part in parts),
             f"{name}.path {path!r} must be dot-separated plain names")
    _require(parts[-2] == member and parts.count("quantities") + parts.count("observations") == 1,
             f"{name}.path {path!r} must end in '{member}.<name>' under exactly one container")
    _require(all(part not in FORBIDDEN_CLAIM_KEYS and not part.replace("_", "").lower().startswith("evidence")
                 for part in parts), f"{name}.path {path!r} hides evidence or a claim")
    return parts


@dataclass(frozen=True)
class QuantityDeclaration:
    """One envelope quantity an operation output may carry (quantity_envelope wire format v1, contract 4.1).

    ``path`` starts at an output field and ends in ``quantities.<name>``; list levels in the payload are traversed.
    ``source_evidence_kinds`` are per-value source labels, never module evidence; "Measured" is refused here
    (it is legal only in an ObservationDeclaration)."""
    path: str
    definition: str
    unit: str
    statuses: Tuple[str, ...]
    source_evidence_kinds: Tuple[str, ...]
    reason_codes: Tuple[str, ...]
    fraction_basis: Optional[str] = None
    leaf_role: str = "derived"

    def __post_init__(self) -> None:
        name = f"quantity {self.path!r}"
        _envelope_path(self.path, "quantities", name)
        _one_of(self.definition, tuple(_envelope.QUANTITY_DEFINITIONS), f"{name}.definition")
        expected_unit = _envelope.QUANTITY_DEFINITIONS[self.definition]["unit"]
        _require(self.unit == expected_unit, f"{name}.unit must be {expected_unit!r} for {self.definition}")
        _require(len(self.statuses) > 0, f"{name}.statuses must not be empty")
        _unique(self.statuses, f"{name}.statuses")
        for status in self.statuses:
            _one_of(status, _envelope.QUANTITY_STATUSES, f"{name}.statuses")
        _unique(self.source_evidence_kinds, f"{name}.sourceEvidenceKinds")
        _require("Measured" not in self.source_evidence_kinds,
                 f"{name}: Measured is legal only in an ObservationDeclaration (transcribed measurements)")
        for kind in self.source_evidence_kinds:
            _one_of(kind, _envelope.QUANTITY_SOURCE_EVIDENCE_KINDS, f"{name}.sourceEvidenceKinds")
        _one_of(self.leaf_role, _envelope.LEAF_ROLES, f"{name}.leafRole")
        carries_value = any(status in _envelope.VALUE_STATUSES for status in self.statuses)
        if self.leaf_role in _envelope.UNLABELLED_ROLES:
            _require(not self.source_evidence_kinds, f"{name}: a {self.leaf_role} leaf carries no source label")
        elif self.leaf_role == "requestInput":
            _require(set(self.source_evidence_kinds) <= {"User input"}, f"{name}: a request echo reads User input")
        elif carries_value:
            _require(len(self.source_evidence_kinds) > 0,
                     f"{name}: a value-carrying {self.leaf_role} quantity declares its per-value source labels")
        _unique(self.reason_codes, f"{name}.reasonCodes")
        for code in self.reason_codes:
            _one_of(code, _envelope.REASON_CODES, f"{name}.reasonCodes")
        if any(status != "computed" for status in self.statuses):
            _require(len(self.reason_codes) > 0, f"{name}: statuses other than computed need reason codes")
        if "not-requested" in self.statuses:
            _require("not-requested" in self.reason_codes, f"{name}: not-requested needs the reason not-requested")
        if _envelope.QUANTITY_DEFINITIONS[self.definition]["fraction"]:
            _one_of(self.fraction_basis, _envelope.FRACTION_BASES, f"{name}.fractionBasis")
        else:
            _require(self.fraction_basis is None, f"{name}: fractionBasis applies only to fraction quantities")

    def to_dict(self) -> dict:
        return {"path": self.path, "definition": self.definition, "unit": self.unit,
                "statuses": list(self.statuses), "sourceEvidenceKinds": list(self.source_evidence_kinds),
                "reasonCodes": list(self.reason_codes), "fractionBasis": self.fraction_basis,
                "leafRole": self.leaf_role}


@dataclass(frozen=True)
class ObservationDeclaration:
    """One transcribed source observation record (``[container.]observations.<name>``); may read Measured."""
    path: str
    observable: str
    source_evidence_kinds: Tuple[str, ...]

    def __post_init__(self) -> None:
        name = f"observation {self.path!r}"
        _envelope_path(self.path, "observations", name)
        _text(self.observable, f"{name}.observable")
        _require(len(self.source_evidence_kinds) > 0, f"{name}.sourceEvidenceKinds must not be empty")
        _unique(self.source_evidence_kinds, f"{name}.sourceEvidenceKinds")
        for kind in self.source_evidence_kinds:
            _one_of(kind, _envelope.OBSERVATION_SOURCE_EVIDENCE_KINDS, f"{name}.sourceEvidenceKinds")

    def to_dict(self) -> dict:
        return {"path": self.path, "observable": self.observable,
                "sourceEvidenceKinds": list(self.source_evidence_kinds)}


def _paths_overlap(a: Tuple[str, ...], b: Tuple[str, ...]) -> bool:
    shorter = min(len(a), len(b))
    return a[:shorter] == b[:shorter]


@dataclass(frozen=True)
class Operation:
    id: str
    # None only for browser-local operations, which have no server route.
    route: Optional[str]
    authority: Authority
    input: Tuple[InputField, ...] = ()
    # None = output schema not yet declared (legacy contracts only; see ModuleContract).
    output: Optional[OutputSchema] = None
    # HTTP method of the route; required with a route, absent without one.
    method: Optional[str] = None
    # Request keys the authority reads that the Field schema cannot describe
    # (free-text labels, element maps). Recorded so they are not silently missing.
    undeclared_input: Tuple[str, ...] = ()
    # Quantity envelope declarations (contract 4.1 item 2): per-value quantities and transcribed observations.
    quantities: Tuple[QuantityDeclaration, ...] = ()
    observations: Tuple[ObservationDeclaration, ...] = ()

    def __post_init__(self) -> None:
        _require(isinstance(self.id, str) and bool(_MODULE_ID.match(self.id)), f"invalid operation id {self.id!r}")
        if self.route is None:
            _require(self.authority.kind == "browser-local", f"{self.id}: only browser-local operations may omit a route")
            _require(self.method is None, f"{self.id}: an operation without a route has no HTTP method")
        else:
            _require(isinstance(self.route, str) and self.route.startswith("/api/"), "operation.route must start with /api/")
            _one_of(self.method, HTTP_METHODS, f"{self.id}.method")
        _unique(tuple(f.key for f in self.input), f"{self.id}.input keys")
        _unique(self.undeclared_input, f"{self.id}.undeclaredInput")
        for key in self.undeclared_input:
            _require(isinstance(key, str) and bool(_KEY.match(key)), f"{self.id}: invalid undeclared key {key!r}")
        _require(not set(self.undeclared_input) & {f.key for f in self.input},
                 f"{self.id}: a key cannot be both declared and undeclared")
        fields = {field.key: field for field in self.input}
        for field in self.input:
            if field.unit_selector is None:
                continue
            selector = fields.get(field.unit_selector)
            _require(selector is not None and selector.value_type == "enum",
                     f"{self.id}.{field.key}: unitSelector must reference a declared enum")
            _require(set(dict(field.unit_options)) == set(selector.enum),
                     f"{self.id}.{field.key}: unitOptions must cover exactly the selector enum")
        _require(all(isinstance(item, QuantityDeclaration) for item in self.quantities),
                 f"{self.id}.quantities must hold QuantityDeclaration items")
        _require(all(isinstance(item, ObservationDeclaration) for item in self.observations),
                 f"{self.id}.observations must hold ObservationDeclaration items")
        declared = [item.path for item in self.quantities] + [item.path for item in self.observations]
        if declared:
            _require(self.output is not None, f"{self.id}: envelope declarations need a declared output schema")
            for path in declared:
                _require(path.split(".")[0] in self.output.fields,
                         f"{self.id}: envelope path {path!r} must start at an output field")
            _unique(tuple(declared), f"{self.id} envelope paths")
            segments = [tuple(path.split(".")) for path in declared]
            for index, first in enumerate(segments):
                for second in segments[index + 1:]:
                    _require(not _paths_overlap(first, second),
                             f"{self.id}: envelope paths {'.'.join(first)!r} and {'.'.join(second)!r} overlap")

    def to_dict(self) -> dict:
        return {
            "id": self.id, "method": self.method, "route": self.route, "authority": self.authority.to_dict(),
            "input": [f.to_dict() for f in self.input],
            "undeclaredInput": list(self.undeclared_input),
            "output": self.output.to_dict() if self.output else None,
            "quantities": [item.to_dict() for item in self.quantities],
            "observations": [item.to_dict() for item in self.observations],
        }

    def input_problems(self, payload: Any) -> list:
        """Contract-side request check: required keys, types, hard ranges, unknown keys.

        Pure; never coerces or clamps. Undeclared-but-recorded keys are passed through
        unchecked because the schema cannot describe them.
        """
        if not isinstance(payload, dict):
            return ["payload must be an object"]
        problems = []
        fields = {f.key: f for f in self.input}
        for key, spec in fields.items():
            if key not in payload:
                if spec.required:
                    problems.append(f"{key}: required")
                continue
            problem = spec.value_problem(payload[key])
            if problem:
                problems.append(f"{key}: {problem}")
        for key in payload:
            if key not in fields and key not in self.undeclared_input:
                problems.append(f"{key}: not declared by the contract")
        return problems


@dataclass(frozen=True)
class FieldRange:
    key: str
    min: float
    max: float
    unit: str

    def __post_init__(self) -> None:
        _require(isinstance(self.key, str) and bool(_KEY.match(self.key)), f"invalid range key {self.key!r}")
        _finite(self.min, f"validity.{self.key}.min")
        _finite(self.max, f"validity.{self.key}.max")
        _require(self.min <= self.max, f"validity.{self.key}: min must not exceed max")
        _text(self.unit, f"validity.{self.key}.unit")

    def to_dict(self) -> dict:
        return {"key": self.key, "min": self.min, "max": self.max, "unit": self.unit}


@dataclass(frozen=True)
class ValidityDomain:
    """Outside the domain a result is downgraded, never rejected (design 1)."""
    ranges: Tuple[FieldRange, ...]
    source_refs: Tuple[str, ...]
    materials: Tuple[str, ...] = ()
    regime_notes: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _unique(tuple(r.key for r in self.ranges), "validity.ranges keys")
        # A validity domain must come from sources and never be invented.
        _require(len(self.source_refs) > 0, "validity.sourceRefs must not be empty")

    def to_dict(self) -> dict:
        return {
            "ranges": [r.to_dict() for r in self.ranges], "materials": list(self.materials),
            "regimeNotes": list(self.regime_notes), "sourceRefs": list(self.source_refs),
        }


@dataclass(frozen=True)
class Oracle:
    status: str = "pending"
    ref: Optional[str] = None
    # Recorded gap when a present oracle cannot run in CI (its imports are outside the
    # CI CPU lock). Must also appear in evidence.note; checked against the oracle's imports.
    ci_note: Optional[str] = None
    # User-facing sentence on what a present oracle checks (shown with the evidence badge).
    scope: Optional[str] = None

    def __post_init__(self) -> None:
        _one_of(self.status, ORACLE_STATES, "oracle.status")
        if self.status == "present":
            _text(self.ref, "oracle.ref")
            _text(self.scope, "oracle.scope")
        else:
            _require(self.scope is None, "oracle.scope applies only to a present oracle")
        if self.ci_note is not None:
            _require(self.status == "present", "oracle.ciNote applies only to a present oracle")
            _text(self.ci_note, "oracle.ciNote")

    def to_dict(self) -> dict:
        return {"status": self.status, "ref": self.ref, "ciNote": self.ci_note, "scope": self.scope}


@dataclass(frozen=True)
class TestRefs:
    oracle: Oracle = field(default_factory=Oracle)
    schema: Optional[str] = None
    docs: Optional[str] = None

    def to_dict(self) -> dict:
        return {"schema": self.schema, "oracle": self.oracle.to_dict(), "docs": self.docs}


@dataclass(frozen=True)
class Evidence:
    emits: Tuple[str, ...]
    ceiling: str
    forbidden_claims: Tuple[str, ...]
    note: Optional[str] = None

    def __post_init__(self) -> None:
        _one_of(self.ceiling, EVIDENCE_TYPES, "evidence.ceiling")
        _unique(self.emits, "evidence.emits")
        for status in self.emits:
            _one_of(status, EVIDENCE_STATUSES, "evidence.emits")
            _require(within_ceiling(status, self.ceiling),
                     f"evidence.emits {status!r} exceeds ceiling {self.ceiling!r}")
        _unique(self.forbidden_claims, "evidence.forbiddenClaims")
        for claim in self.forbidden_claims:
            _one_of(claim, FORBIDDEN_CLAIM_KEYS, "evidence.forbiddenClaims")
        for claim in ALWAYS_FORBIDDEN_CLAIMS:
            _require(claim in self.forbidden_claims, f"evidence.forbiddenClaims must include {claim!r}")
        if self.ceiling != "measured":
            _require("measured" in self.forbidden_claims,
                     "'measured' must be forbidden unless the ceiling is measured")
        # TODO(maintainer-review): allowing "validated" at a validated-simulation
        # ceiling mixes numerical verification with experimental validation
        # (.orchestra/REVIEW-prep-opus-python.md, maintainer item 4).
        if self.ceiling not in ("measured", "validated-simulation"):
            _require("validated" in self.forbidden_claims,
                     "'validated' must be forbidden below a validated ceiling")

    def to_dict(self) -> dict:
        return {"emits": list(self.emits), "ceiling": self.ceiling,
                "forbiddenClaims": list(self.forbidden_claims), "note": self.note}


@dataclass(frozen=True)
class Lifecycle:
    background_work: str
    resources: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _one_of(self.background_work, BACKGROUND_WORK, "lifecycle.backgroundWork")
        _unique(self.resources, "lifecycle.resources")
        for resource in self.resources:
            _one_of(resource, LIFECYCLE_RESOURCES, "lifecycle.resources")

    def to_dict(self) -> dict:
        return {"backgroundWork": self.background_work, "resources": list(self.resources)}


@dataclass(frozen=True)
class View:
    component: str  # path under src/components/
    export: str

    def __post_init__(self) -> None:
        _require(isinstance(self.component, str) and self.component.startswith("src/components/")
                 and self.component.endswith(".tsx"), f"view.component must be src/components/*.tsx, got {self.component!r}")
        _require(isinstance(self.export, str) and bool(_KEY.match(self.export)), "view.export must be an identifier")

    def to_dict(self) -> dict:
        return {"component": self.component, "export": self.export}


# --- Module contract ---------------------------------------------------------

@dataclass(frozen=True)
class ModuleContract:
    id: str
    version: str
    owner: str
    workspace: str
    label: str
    description: str
    next: str
    maturity: str
    navigation: str
    view: View
    evidence: Evidence
    tests: TestRefs
    migration_state: str
    operations: Tuple[Operation, ...] = ()
    hidden_reason: Optional[str] = None
    validity_domain: Optional[ValidityDomain] = None
    lifecycle: Optional[Lifecycle] = None
    # Recorded facts about missing or non-authoritative behaviour (e.g. a route the
    # view calls that no server handles). Notes never raise a claim.
    legacy_notes: Tuple[str, ...] = ()
    # Repository files (optionally ``path:line`` or ``path:start-end``) the contract's
    # fields, limits and outputs were read from. Required once contracted; each must exist.
    source_refs: Tuple[str, ...] = ()
    # SEED_TEXT_FIELDS still copied unreviewed from the seed (all of them for legacy contracts).
    seed_derived: Tuple[str, ...] = SEED_TEXT_FIELDS

    def __post_init__(self) -> None:
        _require(isinstance(self.id, str) and bool(_MODULE_ID.match(self.id)), f"invalid module id {self.id!r}")
        _require(isinstance(self.version, str) and bool(_SEMVER.match(self.version)), f"{self.id}: version must be semver")
        _text(self.owner, f"{self.id}.owner")
        _one_of(self.workspace, WORKSPACES, f"{self.id}.workspace")
        _text(self.label, f"{self.id}.label")
        _text(self.description, f"{self.id}.description")
        _require(isinstance(self.next, str) and bool(_MODULE_ID.match(self.next)), f"{self.id}: invalid next")
        _one_of(self.maturity, MATURITY, f"{self.id}.maturity")
        _one_of(self.navigation, NAVIGATION, f"{self.id}.navigation")
        if self.navigation == "hidden":
            _text(self.hidden_reason, f"{self.id}.hiddenReason")
        else:
            _require(self.hidden_reason is None, f"{self.id}: hiddenReason only applies to hidden modules")
        _one_of(self.migration_state, MIGRATION_STATES, f"{self.id}.migrationState")
        _unique(tuple(op.id for op in self.operations), f"{self.id}.operations ids")
        _unique(self.legacy_notes, f"{self.id}.legacyNotes")
        for note in self.legacy_notes:
            _text(note, f"{self.id}.legacyNotes")
        if self.tests.oracle.status == "pending":
            _require(EVIDENCE_RANK[self.evidence.ceiling] >= EVIDENCE_RANK[PENDING_ORACLE_CEILING],
                     f"{self.id}: a pending oracle caps the ceiling at {PENDING_ORACLE_CEILING!r}")
        if any(op.quantities or op.observations for op in self.operations):
            # Every container states the envelope ceiling; it must not claim more than the contract ceiling.
            _require(within_ceiling(_envelope.MODULE_EVIDENCE_CEILING, self.evidence.ceiling),
                     f"{self.id}: envelope containers state {_envelope.MODULE_EVIDENCE_CEILING!r}, above the "
                     f"contract ceiling {self.evidence.ceiling!r}")
            _one_of(self.maturity, _envelope.MODULE_MATURITIES, f"{self.id}.maturity (container echo)")
        if self.migration_state == "contracted":
            _require(len(self.operations) > 0, f"{self.id}: contracted modules need operations")
            _require(all(op.output is not None for op in self.operations),
                     f"{self.id}: contracted operations must declare an output schema")
            # Remote operations declare their enforced deadline. A route-free local
            # store action has no runtime deadline; do not invent a numeric sentinel.
            _require(all(op.authority.timeout_ms is not None or
                         (op.authority.kind == "browser-local" and op.route is None and op.method is None)
                         for op in self.operations),
                     f"{self.id}: routed/remote contracted operations must declare authority.timeoutMs")
            # emits lists only statuses the code really emits: an output without a
            # status key emits none, and an output with one must declare what it emits.
            carries_status = any(op.output.status_key is not None for op in self.operations)
            if carries_status:
                _require(len(self.evidence.emits) > 0, f"{self.id}: contracted modules must declare emits")
            else:
                _require(len(self.evidence.emits) == 0,
                         f"{self.id}: emits must be empty when no operation output carries a status key")
                _text(self.evidence.note, f"{self.id}.evidence.note")
            _require(self.lifecycle is not None, f"{self.id}: contracted modules need a lifecycle")
            if self.tests.oracle.ci_note:
                _require(self.tests.oracle.ci_note in (self.evidence.note or ""),
                         f"{self.id}: evidence.note must state the oracle CI gap")
            _text(self.tests.schema, f"{self.id}.tests.schema")
            _text(self.tests.docs, f"{self.id}.tests.docs")
            _require(len(self.source_refs) > 0, f"{self.id}: contracted modules need sourceRefs")
            # Never a placeholder, never a claimed person: the explicit unassigned marker or a team id.
            _require(self.owner == OWNER_UNASSIGNED or self.owner.startswith("team:"),
                     f"{self.id}: contracted owner must be {OWNER_UNASSIGNED!r} or a 'team:' id")
        _unique(self.source_refs, f"{self.id}.sourceRefs")
        _unique(self.seed_derived, f"{self.id}.seedDerived")
        for name in self.seed_derived:
            _one_of(name, SEED_TEXT_FIELDS, f"{self.id}.seedDerived")
        for ref in self.source_refs:
            _text(ref, f"{self.id}.sourceRefs")

    def to_dict(self) -> dict:
        return {
            "id": self.id, "version": self.version, "owner": self.owner,
            "workspace": self.workspace, "label": self.label, "description": self.description,
            "next": self.next, "maturity": self.maturity, "navigation": self.navigation,
            "hiddenReason": self.hidden_reason, "view": self.view.to_dict(),
            "operations": [op.to_dict() for op in self.operations],
            "validityDomain": self.validity_domain.to_dict() if self.validity_domain else None,
            "evidence": self.evidence.to_dict(),
            "lifecycle": self.lifecycle.to_dict() if self.lifecycle else None,
            "tests": self.tests.to_dict(), "migrationState": self.migration_state,
            "legacyNotes": list(self.legacy_notes), "sourceRefs": list(self.source_refs),
            "seedDerived": list(self.seed_derived),
        }


# --- Round trip (generated JSON -> contract) ----------------------------------

def _field_from_dict(d: dict) -> InputField:
    options = d.get("unitOptions", {})
    _require(isinstance(options, dict), "input.unitOptions must be a JSON object")
    return InputField(key=d["key"], label=d["label"], unit=d["unit"], quantity_kind=d["quantityKind"],
                      min=d["min"], max=d["max"], default=d["default"], required=d["required"],
                      step=d["step"], display_units=tuple(d["displayUnits"]), enum=tuple(d["enum"]),
                      value_type=d["valueType"], note=d["note"],
                      unit_selector=d.get("unitSelector"), unit_options=tuple(options.items()))


def _output_from_dict(out: dict) -> OutputSchema:
    """Reject malformed JSON containers before converting immutable descriptors."""
    _require(isinstance(out, dict), "output must be a JSON object")
    _require(isinstance(out.get("fields"), list), "output.fields must be a JSON array")
    scalar = out.get("transportValues")
    objects = out.get("transportObjects", {})
    _require(isinstance(scalar, dict), "output.transportValues must be a JSON object")
    _require(isinstance(objects, dict), "output.transportObjects must be a JSON object")
    for key, values in scalar.items():
        _require(isinstance(values, list), f"output.transportValues[{key!r}] must be a JSON array")
    for key, members in objects.items():
        _require(isinstance(members, dict), f"output.transportObjects[{key!r}] must be a JSON object")
        for path, values in members.items():
            _require(isinstance(values, list), f"output.transportObjects[{key!r}][{path!r}] must be a JSON array")
    return OutputSchema(fields=tuple(out["fields"]), status_key=out["statusKey"],
                        transport_values=tuple((key, tuple(values)) for key, values in scalar.items()),
                        transport_objects=tuple((key, tuple((path, tuple(values)) for path, values in members.items()))
                                                for key, members in objects.items()))


def _operation_from_dict(d: dict) -> Operation:
    a = d["authority"]
    authority = Authority(kind=a["kind"], timeout_ms=a["timeoutMs"], gpu=a["gpu"], warm=a["warm"],
                          script=a["script"], worker_method=a["workerMethod"], exception_reason=a["exceptionReason"])
    out = d["output"]
    quantities = d.get("quantities", [])
    observations = d.get("observations", [])
    _require(isinstance(quantities, list) and isinstance(observations, list),
             "operation.quantities and operation.observations must be JSON arrays")
    return Operation(id=d["id"], route=d["route"], method=d["method"], authority=authority,
                     input=tuple(_field_from_dict(f) for f in d["input"]),
                     undeclared_input=tuple(d["undeclaredInput"]),
                     output=_output_from_dict(out) if out is not None else None,
                     quantities=tuple(QuantityDeclaration(
                         path=q["path"], definition=q["definition"], unit=q["unit"], statuses=tuple(q["statuses"]),
                         source_evidence_kinds=tuple(q["sourceEvidenceKinds"]), reason_codes=tuple(q["reasonCodes"]),
                         fraction_basis=q["fractionBasis"], leaf_role=q["leafRole"]) for q in quantities),
                     observations=tuple(ObservationDeclaration(
                         path=o["path"], observable=o["observable"],
                         source_evidence_kinds=tuple(o["sourceEvidenceKinds"])) for o in observations))


def contract_from_dict(d: dict) -> ModuleContract:
    """Rebuild (and so re-validate) a contract from its emitted dictionary."""
    vd = d["validityDomain"]
    lc = d["lifecycle"]
    t = d["tests"]
    ev = d["evidence"]
    return ModuleContract(
        id=d["id"], version=d["version"], owner=d["owner"], workspace=d["workspace"], label=d["label"],
        description=d["description"], next=d["next"], maturity=d["maturity"], navigation=d["navigation"],
        hidden_reason=d["hiddenReason"], view=View(component=d["view"]["component"], export=d["view"]["export"]),
        operations=tuple(_operation_from_dict(op) for op in d["operations"]),
        validity_domain=ValidityDomain(
            ranges=tuple(FieldRange(**r) for r in vd["ranges"]), source_refs=tuple(vd["sourceRefs"]),
            materials=tuple(vd["materials"]), regime_notes=tuple(vd["regimeNotes"])) if vd else None,
        evidence=Evidence(emits=tuple(ev["emits"]), ceiling=ev["ceiling"],
                          forbidden_claims=tuple(ev["forbiddenClaims"]), note=ev["note"]),
        lifecycle=Lifecycle(background_work=lc["backgroundWork"], resources=tuple(lc["resources"])) if lc else None,
        tests=TestRefs(oracle=Oracle(status=t["oracle"]["status"], ref=t["oracle"]["ref"],
                                     ci_note=t["oracle"]["ciNote"], scope=t["oracle"]["scope"]),
                       schema=t["schema"], docs=t["docs"]),
        migration_state=d["migrationState"], legacy_notes=tuple(d["legacyNotes"]),
        source_refs=tuple(d["sourceRefs"]), seed_derived=tuple(d["seedDerived"]),
    )


if __name__ == "__main__":
    # `python -m module_contract emit [--check]` (run from python/)
    # delegates to the registry emitter; scripts/emit-module-registry.py is equivalent.
    import sys

    from module_registry import main as _registry_main

    _args = sys.argv[1:]
    if not _args or _args[0] != "emit":
        print("usage: python -m module_contract emit [--check]", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(_registry_main(_args[1:]))
