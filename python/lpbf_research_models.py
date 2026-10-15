"""P8 research route dispatch script: POST /api/python/lpbf-research-models (integration contract 2026-10-15,
sections 3.1 to 3.7, 13.9 and 13.10).

Reads one JSON request (schema p8-research-request-v1) on stdin, runs the request checks, the code-stale check and
the stage protocol (describe, nominal, band), serializes strictly and sets the exit code:

    request refused (422 through pythonDispatchStatus)       exit 2, errorKind "validation"
    request-scope research failure (HTTP 200 envelope)        exit 0, errorKind "research"
    success                                                   exit 0

Revision 3 (contract section 14): the optional ``sender`` (research-panel, blind-freeze, batch-client) and ``relay``
members with their supersedeKey and relay rules; every complete response carries ``digests`` (sha256 of the canonical
researchModels and labels), and a complete band response to a relay request carries ``relay.subsetJson``, the ASCII
canonical JSON of the closed projection BLIND_RELAY_V1, with its sha256 (at most 12,000 characters). Sender and
binding change neither requestKey nor any cache key.

It holds no module-level state: the IPC worker executes it in a fresh namespace per request, and every per-process
state (cache, identity, priority) lives in lpbf_research_cache. Heavy work runs only under __main__.

The physics evaluator is an injected engine (ResearchEngine below). The production default is supplied by lpbf_research_manifest
and lpbf_research_arm. Transport tests inject a deterministic fake engine
(python/test_lpbf_research_harness.py).

Research only: no served module may import this file, and it never calls calculate_meltpool_physics (R-ISO-1).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

import lpbf_research_cache as research_cache
import lpbf_research_codes as codes
import lpbf_research_context as research_context

REQUEST_SCHEMA_VERSION = "p8-research-request-v1"
RESPONSE_SCHEMA_VERSION = "p8-research-response-v1"
MAX_REQUEST_BYTES = 65536
MAX_RAW_REQUEST_BYTES = 1024 * 1024        # refused unparsed above this; the 65536 rule is on the compact encoding
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_ID_CHARS = 128
TIME_BUDGET_MIN_MS = 250
TIME_BUDGET_MAX_MS = 8000
MAX_ARMS_PER_MODULE = 80
BAND_METHOD_ID = "declared-ofat-envelope-v1"
STAGES = ("describe", "nominal", "band")
EXIT_OK = 0
EXIT_REFUSED = 2
VALIDATION_ERROR_KIND = "validation"       # the literal server/pythonDispatchStatus.ts maps to HTTP 422
RESEARCH_ERROR_KIND = "research"

# The seven containers, in the order of the P8 spec section 2 table.
CONTAINERS = ("keyholeCavity", "meltDepthLink", "alSi10MgIndexDisclosure", "alSi10MgVapourMgAware", "marangoni",
              "surfaceBalance", "unavailablePhysics")
# Contract 3.5 rule 2 (Rev. 1, R14): the fixed order uncached band arms are computed in.
BAND_ORDER = ("keyholeCavity", "meltDepthLink", "marangoni", "surfaceBalance", "alSi10MgVapourMgAware")
# Every module's arms are planned and evaluated in this order (banded modules first, then the nominal-only ones), so
# an upstream arm (the cavity arm a link arm reads) is always evaluated before its readers.
PLAN_ORDER = BAND_ORDER + tuple(m for m in CONTAINERS if m not in BAND_ORDER)
OPTION_MODULES = ("marangoni", "surfaceBalance")

_TOP_KEYS = ("schemaVersion", "supersedeKey", "clientRequestId", "stage", "timeBudgetMs", "process",
             "propertyContext", "researchOptions", "sender", "relay")
_REQUIRED_TOP_KEYS = ("schemaVersion", "supersedeKey", "clientRequestId", "stage", "process", "propertyContext")
_PROCESS_NUMBERS = ("laserPower_W", "scanSpeed_mm_s", "beamDiameter_um", "preheatTemp_C")
_POSITIVE_PROCESS_NUMBERS = ("laserPower_W", "scanSpeed_mm_s", "beamDiameter_um")
_PROCESS_KEYS = ("material",) + _PROCESS_NUMBERS + ("laserWavelength", "absorptionModel")
_SHA256_HEX = re.compile(r"[0-9a-f]{64}\Z")

# researchOptions member schema (P8 spec A1 with the renames of contract 7.1 and the members of 9.3 rule 8). Value
# types and enum membership are request checks; numeric limits, ranges, presets and modes are module checks (9.3).
OPTION_SCHEMA: Mapping[str, Mapping[str, tuple]] = {
    "marangoni": {
        "slopeMode": ("enum", ("direct", "fe-s-belton", "fe-o-belton")),
        "surfaceTensionSlope_N_mK": ("number", None),
        "length_m": ("number", None),
        "deltaTemperature_K": ("number", None),
        "referenceTemperature_K": ("number", None),
        "viscosity_Pa_s": ("number", None),
        "solubleSulfur_ppm": ("number", None),
        "solubleOxygen_ppm": ("number", None),
    },
    "surfaceBalance": {
        "vapourPreset": ("enum", ("gan-ti64", "pure-al-proxy", "o8-mg-inclusive", "melt-in625-raoult", "custom")),
        "vapourTemperature_K": ("number", None),
        "vapourLatentHeat_J_kg": ("number", None),
        "vapourMolarMass_kg_mol": ("number", None),
        "evaporationConvention": ("enum", ("accommodation-and-beta", "net-factor")),
        "evaporationAccommodation": ("number", None),
        "netEvaporationFactor": ("number", None),
        "recoilFraction": ("number", None),
        "emissivity": ("number", None),
    },
}


class ResearchEngine(Protocol):
    """The physics side of the protocol (phase C: lpbf_research_manifest and lpbf_research_arm; tests: a fake).

    ``manifest`` returns {"banded": bool, "declared": bool, "arms": [arm, ...]}; arms[0] is the module's nominal arm;
    an arm is {"armId": str, "inputs": <canonical module input tuple, 5.2>, "descriptor": <5.3 descriptor or None>,
    "dependsOn": [[module_id, arm_id], ...]} (dependencies on modules earlier in PLAN_ORDER only). ``evaluate_arm``
    returns an arm record {"values": {field: number | string | bool | None | list | dict}, "failures": {path: code},
    ...structural members}. ``aggregate`` builds the closed container from the arm records and the band envelopes
    the protocol computed. Containers are opaque to the protocol.
    """

    def module_revision(self, module_id: str) -> str: ...
    def method_settings(self, module_id: str) -> Mapping: ...
    def controls(self, context, options) -> list: ...
    def presets(self, context) -> Mapping: ...
    def option_rule_problems(self, module_id: str, context, options) -> list: ...
    def module_availability(self, module_id: str, context, options) -> Mapping: ...
    def manifest(self, module_id: str, context, options) -> Mapping: ...
    def evaluate_arm(self, module_id: str, context, options, arm: Mapping, upstream: Mapping) -> Mapping: ...
    def aggregate(self, module_id: str, context, options, manifest: Mapping, records: Mapping,
                  bands: Mapping | None) -> Mapping: ...
    def refused_container(self, module_id: str, context, code: str, problems: list) -> Mapping: ...
    def failed_container(self, module_id: str, context, code: str) -> Mapping: ...


@dataclass(frozen=True)
class Dependencies:
    engine: Any                         # ResearchEngine; tests may inject None to exercise the unavailable-engine guard
    properties: Any                     # lpbf_research_context.PropertyProvider
    identity: Any                       # .identity() -> {research, served}; .check() -> {"stale": bool, ...}
    cache: Any                          # lpbf_research_cache.ResearchLRU
    cache_instance_id: str
    label_table: Mapping[str, str]
    clock: Callable[[], float]          # seconds
    log: Callable[[str], None]          # one stderr line per call


def default_dependencies() -> Dependencies:
    from lpbf_research_arm import Engine
    return Dependencies(
        engine=Engine(),
        properties=research_context.served_property_provider(),
        identity=research_cache.IDENTITY,
        cache=research_cache.CACHE,
        cache_instance_id=research_cache.CACHE_INSTANCE_ID,
        label_table=codes.LEAF_LABELS,
        clock=time.perf_counter,
        log=lambda line: sys.stderr.write(line.rstrip("\n") + "\n"),
    )


class Refused(Exception):
    def __init__(self, code: str, problems: list, recycle: bool = False):
        super().__init__(code)
        self.code = code
        self.problems = problems
        self.recycle = recycle


class RequestScopeFailure(Exception):
    def __init__(self, code: str, detail: str, cause: str | None = None):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.cause = cause


# --- Request checks (contract 3.4 and 9.3, request scope) --------------------------------------------------------

def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _problem(pointer: str, rule: str, **kw) -> dict:
    return codes.option_problem(pointer, rule, **kw)


def _check_keys(obj: Mapping, allowed: tuple, base: str, problems: list) -> None:
    for key in obj:
        if key not in allowed:
            problems.append(_problem(f"{base}/{key}", "unknown-key", value=obj[key]))


def _check_id(request: Mapping, key: str, problems: list) -> None:
    value = request.get(key)
    if not isinstance(value, str) or not 1 <= len(value) <= MAX_ID_CHARS:
        problems.append(_problem(f"/{key}", "wrong-type", value=value, type="string of 1 to 128 characters"))


def _check_process(process: Any, provider, problems: list) -> None:
    if not isinstance(process, dict):
        problems.append(_problem("/process", "wrong-type", value=process, type="JSON object"))
        return
    _check_keys(process, _PROCESS_KEYS, "/process", problems)
    material = process.get("material")
    if not isinstance(material, str) or not material or provider.base_properties(material) is None:
        problems.append(_problem("/process/material", "wrong-type", value=material, type="served material name"))
    for key in _PROCESS_NUMBERS:
        pointer = f"/process/{key}"
        value = process.get(key)
        if not _is_number(value):
            problems.append(_problem(pointer, "wrong-type", value=value, type="number"))
        elif not math.isfinite(value):
            problems.append(_problem(pointer, "not-finite", value=value, label=codes.request_label(pointer)))
        elif key in _POSITIVE_PROCESS_NUMBERS and value <= 0:
            problems.append(_problem(pointer, "not-positive", value=value, limit=0))
    wavelength = process.get("laserWavelength")
    if wavelength not in provider.wavelengths:
        problems.append(_problem("/process/laserWavelength", "wrong-type", value=wavelength,
                                 type="served laser wavelength (" + ", ".join(provider.wavelengths) + ")"))
    model = process.get("absorptionModel")
    if model not in provider.absorption_models:
        problems.append(_problem("/process/absorptionModel", "wrong-type", value=model,
                                 type="served absorption model (" + ", ".join(provider.absorption_models) + ")"))


def _check_stage_and_budget(request: Mapping, problems: list) -> None:
    stage = request.get("stage")
    if stage not in STAGES:
        problems.append(_problem("/stage", "wrong-type", value=stage, type="stage (describe, nominal or band)"))
        return
    if stage == "band":
        if "timeBudgetMs" not in request:
            problems.append(_problem("/timeBudgetMs", "wrong-type", value=None,
                                     type="integer from 250 to 8000 or null (required in the band stage)"))
            return
        budget = request["timeBudgetMs"]
        if budget is None:
            return
        if not isinstance(budget, int) or isinstance(budget, bool):
            problems.append(_problem("/timeBudgetMs", "wrong-type", value=budget,
                                     type="integer from 250 to 8000 or null"))
        elif budget < TIME_BUDGET_MIN_MS:
            problems.append(_problem("/timeBudgetMs", "below-min", value=budget, limit=TIME_BUDGET_MIN_MS,
                                     min=TIME_BUDGET_MIN_MS, max=TIME_BUDGET_MAX_MS, unit="ms"))
        elif budget > TIME_BUDGET_MAX_MS:
            problems.append(_problem("/timeBudgetMs", "above-max", value=budget, limit=TIME_BUDGET_MAX_MS,
                                     min=TIME_BUDGET_MIN_MS, max=TIME_BUDGET_MAX_MS, unit="ms"))
    elif request.get("timeBudgetMs") is not None:
        problems.append(_problem("/timeBudgetMs", "wrong-type", value=request["timeBudgetMs"],
                                 type="null outside the band stage"))


def _check_property_context(context: Any, problems: list) -> None:
    if not isinstance(context, dict):
        problems.append(_problem("/propertyContext", "wrong-type", value=context, type="JSON object"))
        return
    kind = context.get("kind")
    if kind == "nominal":
        _check_keys(context, ("kind",), "/propertyContext", problems)
    elif kind == "build-job-snapshot":
        _check_keys(context, ("kind", "alloyId", "materialPropertySha256"), "/propertyContext", problems)
        if not isinstance(context.get("alloyId"), str) or not context.get("alloyId"):
            problems.append(_problem("/propertyContext/alloyId", "wrong-type", value=context.get("alloyId"),
                                     type="string"))
        sha = context.get("materialPropertySha256")
        if not isinstance(sha, str) or not _SHA256_HEX.match(sha):
            problems.append(_problem("/propertyContext/materialPropertySha256", "wrong-type", value=sha,
                                     type="64-character lowercase hex SHA-256"))
    else:
        problems.append(_problem("/propertyContext/kind", "wrong-type", value=kind,
                                 type="property context kind (nominal or build-job-snapshot)"))


def _check_option_value(module: str, key: str, value: Any, pointer: str, problems: list) -> None:
    kind, allowed = OPTION_SCHEMA[module][key]
    if kind == "number":
        if not _is_number(value):
            problems.append(_problem(pointer, "wrong-type", value=value, type="number"))
    elif not isinstance(value, str) or value not in allowed:
        problems.append(_problem(pointer, "wrong-type", value=value, type="string, one of " + ", ".join(allowed)))


def _check_research_options(options: Any, problems: list) -> None:
    if not isinstance(options, dict):
        problems.append(_problem("/researchOptions", "wrong-type", value=options, type="JSON object"))
        return
    _check_keys(options, OPTION_MODULES + ("ranges",), "/researchOptions", problems)
    for module in OPTION_MODULES:
        if module not in options:
            continue
        member, base = options[module], f"/researchOptions/{module}"
        if not isinstance(member, dict):
            problems.append(_problem(base, "wrong-type", value=member, type="JSON object"))
            continue
        _check_keys(member, tuple(OPTION_SCHEMA[module]), base, problems)
        for key, value in member.items():
            if key in OPTION_SCHEMA[module]:
                _check_option_value(module, key, value, f"{base}/{key}", problems)
    if "ranges" not in options:
        return
    ranges = options["ranges"]
    if not isinstance(ranges, dict):
        problems.append(_problem("/researchOptions/ranges", "wrong-type", value=ranges, type="JSON object"))
        return
    _check_keys(ranges, OPTION_MODULES, "/researchOptions/ranges", problems)
    for module in OPTION_MODULES:
        if module not in ranges:
            continue
        member, base = ranges[module], f"/researchOptions/ranges/{module}"
        if not isinstance(member, dict):
            problems.append(_problem(base, "wrong-type", value=member, type="JSON object"))
            continue
        numeric = tuple(k for k, (kind, _) in OPTION_SCHEMA[module].items() if kind == "number")
        _check_keys(member, numeric, base, problems)
        for key, endpoints in member.items():
            if key not in numeric:
                continue
            pointer = f"{base}/{key}"
            if not isinstance(endpoints, dict):
                problems.append(_problem(pointer, "wrong-type", value=endpoints, type="JSON object {min, max}"))
                continue
            _check_keys(endpoints, ("min", "max"), pointer, problems)
            for end in ("min", "max"):
                if not _is_number(endpoints.get(end)):
                    problems.append(_problem(f"{pointer}/{end}", "wrong-type", value=endpoints.get(end),
                                             type="number"))


def _parse(raw: str) -> Any:
    if len(raw.encode("utf-8")) > MAX_RAW_REQUEST_BYTES:
        raise Refused("RESEARCH_REQUEST_INVALID", [_problem("", "too-large", limit=MAX_REQUEST_BYTES)])
    try:
        request = json.loads(raw)
    except (ValueError, RecursionError):
        raise Refused("RESEARCH_REQUEST_INVALID",
                      [_problem("", "wrong-type", value=raw[:60], type="JSON object")]) from None
    compact = json.dumps(request, ensure_ascii=False, separators=(",", ":"), allow_nan=True)
    if len(compact.encode("utf-8")) > MAX_REQUEST_BYTES:
        raise Refused("RESEARCH_REQUEST_INVALID", [_problem("", "too-large", limit=MAX_REQUEST_BYTES)])
    return request


def _check_relay(relay: Any, problems: list) -> bool:
    """The closed relay member (14.1, R-REL-1); True when it is well formed."""
    if not isinstance(relay, dict):
        problems.append(_problem("/relay", "wrong-type", value=relay, type="JSON object"))
        return False
    before = len(problems)
    _check_keys(relay, ("kind", "previewSha256", "conditionOrdinal"), "/relay", problems)
    if relay.get("kind") != codes.RELAY_KIND:
        problems.append(_problem("/relay/kind", "wrong-type", value=relay.get("kind"), type=f"string {codes.RELAY_KIND}"))
    sha = relay.get("previewSha256")
    if not isinstance(sha, str) or not _SHA256_HEX.match(sha):
        problems.append(_problem("/relay/previewSha256", "wrong-type", value=sha,
                                 type="64-character lowercase hex SHA-256"))
    ordinal = relay.get("conditionOrdinal")
    if not isinstance(ordinal, int) or isinstance(ordinal, bool):
        problems.append(_problem("/relay/conditionOrdinal", "wrong-type", value=ordinal,
                                 type="integer from 0 to 1023"))
    elif ordinal < 0:
        problems.append(_problem("/relay/conditionOrdinal", "below-min", value=ordinal, limit=0, min=0,
                                 max=codes.RELAY_CONDITION_ORDINAL_MAX))
    elif ordinal > codes.RELAY_CONDITION_ORDINAL_MAX:
        problems.append(_problem("/relay/conditionOrdinal", "above-max", value=ordinal,
                                 limit=codes.RELAY_CONDITION_ORDINAL_MAX, min=0, max=codes.RELAY_CONDITION_ORDINAL_MAX))
    return len(problems) == before


def _check_sender_and_relay(request: Mapping, problems: list) -> None:
    """Revision 3 (14.1): the closed sender list, its supersedeKey prefix, and where a relay or options may appear."""
    sender = request.get("sender", codes.DEFAULT_SENDER)
    if sender not in codes.SENDERS:
        problems.append(_problem("/sender", "wrong-type", value=sender,
                                 type="sender (" + ", ".join(codes.SENDERS) + ")"))
        return
    has_relay = "relay" in request
    relay_ok = _check_relay(request["relay"], problems) if has_relay else False
    key = request.get("supersedeKey")
    if isinstance(key, str) and 1 <= len(key) <= MAX_ID_CHARS:
        preview = request["relay"]["previewSha256"] if relay_ok else None
        if not codes.supersede_key_matches(sender, key, preview):
            problems.append(_problem("/supersedeKey", "sender-key-mismatch", value=key, sender=sender,
                                     expected=codes.SUPERSEDE_KEY_RULES[sender]))
    if has_relay and sender == "research-panel":
        problems.append(_problem("/relay", "relay-sender-mismatch", value=request["relay"], sender=sender))
    if "researchOptions" in request and (has_relay or sender == "blind-freeze"):
        problems.append(_problem("/researchOptions", "relay-options-forbidden", value=request["researchOptions"],
                                 context="with a relay" if has_relay else "from sender blind-freeze"))
    if sender == "blind-freeze" and request.get("stage") == "band" and not has_relay:
        problems.append(_problem("/relay", "relay-required", value=None))


def check_request(raw: str, provider) -> dict:
    """Contract 3.4 request checks 1 to 8; raises Refused with every problem found, in check order."""
    request = _parse(raw)
    problems: list = []
    if not isinstance(request, dict):
        raise Refused("RESEARCH_REQUEST_INVALID", [_problem("", "wrong-type", value=request, type="JSON object")])
    _check_keys(request, _TOP_KEYS, "", problems)
    for key in _REQUIRED_TOP_KEYS:
        if key not in request:
            problems.append(_problem(f"/{key}", "wrong-type", value=None,
                                     type="JSON object" if key in ("process", "propertyContext") else "string"))
    if "schemaVersion" in request and request["schemaVersion"] != REQUEST_SCHEMA_VERSION:
        problems.append(_problem("/schemaVersion", "wrong-type", value=request["schemaVersion"],
                                 type=f"string {REQUEST_SCHEMA_VERSION}"))
    if "process" in request:
        _check_process(request["process"], provider, problems)
    if "stage" in request:
        _check_stage_and_budget(request, problems)
    for key in ("supersedeKey", "clientRequestId"):
        if key in request:
            _check_id(request, key, problems)
    if "propertyContext" in request:
        _check_property_context(request["propertyContext"], problems)
    if "researchOptions" in request:
        _check_research_options(request["researchOptions"], problems)
    _check_sender_and_relay(request, problems)
    if problems:
        raise Refused("RESEARCH_REQUEST_INVALID", problems)
    context = request["propertyContext"]
    if context["kind"] == "build-job-snapshot":
        alloy_id = provider.resolve_alloy_id(context["alloyId"])
        material = request["process"]["material"]
        if alloy_id is None or provider.alloy_thermal_name(alloy_id) != material:
            raise Refused("RESEARCH_REQUEST_INVALID", [_problem("/propertyContext/alloyId", "alloy-material-mismatch",
                                                                value=context["alloyId"], material=material)])
        _snapshot, sha = provider.material_snapshot(alloy_id)
        if sha != context["materialPropertySha256"]:
            raise Refused("PROPERTY_SNAPSHOT_MISMATCH", [_problem("/propertyContext/materialPropertySha256",
                                                                  "snapshot-hash-mismatch",
                                                                  value=context["materialPropertySha256"])])
    return request


def normalized_options(request: Mapping) -> dict:
    """researchOptions with every member present ({} when absent); a fresh copy the engine may read."""
    options = request.get("researchOptions") or {}
    ranges = options.get("ranges") or {}
    return {
        "marangoni": dict(options.get("marangoni") or {}),
        "surfaceBalance": dict(options.get("surfaceBalance") or {}),
        "ranges": {m: {k: dict(v) for k, v in (ranges.get(m) or {}).items()} for m in OPTION_MODULES},
    }


def _floats(value: Any) -> Any:
    """Key form of request numbers: every number as a float (200 and 200.0 are one request); a non-finite option
    value (refused per module, 9.3) is tagged, because the canonical encoding refuses NaN and infinity."""
    if _is_number(value):
        value = float(value)
        return value if math.isfinite(value) else {"nonFiniteNumber": repr(value)}
    if isinstance(value, Mapping):
        return {k: _floats(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_floats(v) for v in value]
    return value


# --- Module option checks (contract 9.3, module scope) -----------------------------------------------------------

def module_option_problems(engine, module: str, context, options: Mapping, controls: list) -> list:
    """Generic numeric checks driven by the engine's control table, then the engine's own mode and preset rules."""
    problems: list = []
    by_key = {c["key"]: c for c in controls if c.get("module") == module}
    base = f"/researchOptions/{module}"
    for key, value in options[module].items():
        control = by_key.get(key)
        if control is None or not _is_number(value):
            continue
        label, unit = control.get("label") or key, control.get("unit") or ""
        lo, hi = control.get("min"), control.get("max")
        pointer = f"{base}/{key}"
        if not math.isfinite(value):
            problems.append(_problem(pointer, "not-finite", value=value, label=label))
        elif lo is not None and value < lo:
            problems.append(_problem(pointer, "below-min", value=value, limit=lo, label=label, min=lo, max=hi,
                                     unit=unit))
        elif hi is not None and value > hi:
            problems.append(_problem(pointer, "above-max", value=value, limit=hi, label=label, min=lo, max=hi,
                                     unit=unit))
    for key, endpoints in options["ranges"][module].items():
        control = by_key.get(key)
        if control is None:
            continue
        label, unit = control.get("label") or key, control.get("unit") or ""
        lo, hi = control.get("min"), control.get("max")
        pointer = f"/researchOptions/ranges/{module}/{key}"
        bad = False
        for end in ("min", "max"):
            value = endpoints[end]
            if not math.isfinite(value):
                problems.append(_problem(f"{pointer}/{end}", "not-finite", value=value, label=label))
                bad = True
            elif lo is not None and value < lo:
                problems.append(_problem(f"{pointer}/{end}", "below-min", value=value, limit=lo, label=label,
                                         min=lo, max=hi, unit=unit))
                bad = True
            elif hi is not None and value > hi:
                problems.append(_problem(f"{pointer}/{end}", "above-max", value=value, limit=hi, label=label,
                                         min=lo, max=hi, unit=unit))
                bad = True
        if bad:
            continue
        if endpoints["min"] > endpoints["max"]:
            problems.append(_problem(pointer, "range-inverted", value=endpoints, label=label,
                                     min=endpoints["min"], max=endpoints["max"]))
            continue
        nominal = control.get("value")
        if nominal is None:
            problems.append(_problem(pointer, "range-without-nominal", value=endpoints, label=label))
        elif _is_number(nominal) and not endpoints["min"] <= nominal <= endpoints["max"]:
            problems.append(_problem(pointer, "range-excludes-nominal", value=endpoints, label=label,
                                     min=endpoints["min"], max=endpoints["max"], unit=unit, nominal=nominal))
    problems.extend(engine.option_rule_problems(module, context, options))
    return problems


# --- Non-finite handling (contract 3.7 item 4, 13.10) ------------------------------------------------------------

def _scrub(value: Any, path: str, failures: dict) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        failures[path] = "NONFINITE_RESULT"
        return None
    if isinstance(value, Mapping):
        return {k: _scrub(v, f"{path}.{k}" if path else str(k), failures) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub(v, f"{path}.{i}", failures) for i, v in enumerate(value)]
    return value


def sanitize_arm_record(record: Any) -> dict:
    """Arm-time pass (13.10 item 1): every non-finite numeric leaf becomes null with NONFINITE_RESULT, a
    field-specific failure of that arm, before the record is cached or aggregated. Raises on a malformed record."""
    if not isinstance(record, Mapping) or not isinstance(record.get("values"), Mapping):
        raise TypeError("an arm record must be a mapping with a 'values' mapping")
    found: dict = {}
    clean = _scrub(record, "", found)
    failures = dict(clean.get("failures") or {})
    for path, code in found.items():
        key = path[len("values."):] if path.startswith("values.") else path
        failures[key] = codes.winning_code([failures[key], code]) if key in failures else code
    clean["failures"] = failures
    for path, code in failures.items():
        if not isinstance(path, str) or code not in codes.REASON_CODES:
            raise ValueError(f"arm failure {path!r}: unregistered reason code {code!r}")
    research_cache.canonical(clean)  # refuses unsupported types: an evaluator bug, not a result
    return clean


def serialization_pass(value: Any) -> Any:
    """Second guard before serialization (3.7 item 4): any value, band or note slot that is non-finite becomes null;
    a ResearchField-like slot ({"value": ..., "reasonCode": ...}) also gets NONFINITE_RESULT."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Mapping):
        out = {k: serialization_pass(v) for k, v in value.items()}
        raw = value.get("value")
        if isinstance(raw, float) and not math.isfinite(raw) and "reasonCode" in out and out["reasonCode"] is None:
            out["reasonCode"] = "NONFINITE_RESULT"
        return out
    if isinstance(value, (list, tuple)):
        return [serialization_pass(v) for v in value]
    return value


# --- Band envelopes (A1, 5.4, 13.10 item 3) ----------------------------------------------------------------------

def _arm_field(record: Mapping, field: str) -> tuple:
    """(value, failure code) of one field in one arm record."""
    arm_failure = record.get("armFailure")
    if arm_failure is not None:
        return None, arm_failure
    value = record["values"].get(field)
    if value is None:
        return None, record.get("failures", {}).get(field) or "RESEARCH_EVALUATION_FAILED"
    return value, None


def numeric_envelope(field: str, arm_ids: list, records: Mapping) -> dict:
    """Min, nominal and max over finite arm values by an explicit loop in manifest order: the extreme is the first
    arm strictly below (above) the running extreme, ties counted; failed arms never set an extreme."""
    lo = hi = None
    lo_id = hi_id = None
    lo_ties = hi_ties = 0
    successful = 0
    failed: list = []
    nominal = nominal_code = None
    for index, arm_id in enumerate(arm_ids):
        value, code = _arm_field(records[arm_id], field)
        ok = _is_number(value) and math.isfinite(value)
        if index == 0:
            nominal = value if ok else None
            nominal_code = None if ok else (code or "RESEARCH_EVALUATION_FAILED")
        if not ok:
            failed.append({"armId": arm_id, "reasonCode": code or "RESEARCH_EVALUATION_FAILED"})
            continue
        successful += 1
        if lo is None or value < lo:
            lo, lo_id, lo_ties = value, arm_id, 1
        elif value == lo:
            lo_ties += 1
        if hi is None or value > hi:
            hi, hi_id, hi_ties = value, arm_id, 1
        elif value == hi:
            hi_ties += 1
    if successful == 0:
        completeness, reason = "unavailable", "BAND_NO_SUCCESSFUL_ARM"
    else:
        completeness, reason = ("partial" if failed else "complete"), None
    return {"completeness": completeness, "reasonCode": reason, "method": BAND_METHOD_ID,
            "min": lo, "nominal": nominal, "max": hi, "nominalReasonCode": nominal_code,
            "minArmId": lo_id, "maxArmId": hi_id,
            "minArmTies": lo_ties if successful else None, "maxArmTies": hi_ties if successful else None,
            "successfulArms": successful, "totalArms": len(arm_ids), "failedArms": failed}


def placeholder_envelope(field: str, nominal_record: Mapping, completeness: str, reason: str) -> dict:
    """Pending (3.5 rule 1) or not-declared (13.14 item 1) form: min and max null with the band code, counts null."""
    value, code = _arm_field(nominal_record, field)
    ok = _is_number(value) and math.isfinite(value)
    return {"completeness": completeness, "reasonCode": reason, "method": BAND_METHOD_ID,
            "min": None, "nominal": value if ok else None, "max": None,
            "nominalReasonCode": None if ok else (code or "RESEARCH_EVALUATION_FAILED"),
            "minArmId": None, "maxArmId": None, "minArmTies": None, "maxArmTies": None,
            "successfulArms": None, "totalArms": None, "failedArms": []}


def categorical_support(field: str, arm_ids: list, records: Mapping) -> list:
    """{value, count} in first-appearance (manifest) order; failed arms are not counted."""
    counts: dict = {}
    order: list = []
    for arm_id in arm_ids:
        value, _ = _arm_field(records[arm_id], field)
        if value is None:
            continue
        key = (type(value).__name__, value)
        if key not in counts:
            counts[key] = 0
            order.append((key, value))
        counts[key] += 1
    return [{"value": value, "count": counts[key]} for key, value in order]


def _field_kinds(records: list) -> tuple:
    numeric, categorical = set(), set()
    for record in records:
        for field, value in record.get("values", {}).items():
            if isinstance(value, (str, bool)):
                categorical.add(field)
            elif _is_number(value) or value is None:
                numeric.add(field)
    numeric -= categorical
    seen_structured = {f for r in records for f, v in r.get("values", {}).items() if isinstance(v, (list, dict))}
    return sorted(numeric - seen_structured), sorted(categorical - seen_structured)


def band_envelopes(state: str, arm_ids: list, records: Mapping) -> dict:
    nominal_record = records[arm_ids[0]]
    present = [records[a] for a in arm_ids if a in records]
    numeric_fields, categorical_fields = _field_kinds(present)
    if state == "computed":
        numeric = {f: numeric_envelope(f, arm_ids, records) for f in numeric_fields}
        categorical = {f: categorical_support(f, arm_ids, records) for f in categorical_fields}
        failed = [{"armId": a, "reasonCode": records[a]["armFailure"]} for a in arm_ids
                  if records[a].get("armFailure") is not None]
    else:
        completeness, reason = (("pending", "BAND_PENDING") if state == "pending"
                                else ("unavailable", "BAND_MANIFEST_NOT_DECLARED"))
        numeric = {f: placeholder_envelope(f, nominal_record, completeness, reason) for f in numeric_fields}
        categorical = {f: [] for f in categorical_fields}
        failed = []
    return {"state": state, "method": BAND_METHOD_ID, "armIds": list(arm_ids), "numeric": numeric,
            "categorical": categorical, "failedArms": failed}


# --- Stage protocol (contract 3.5, 3.6) --------------------------------------------------------------------------

@dataclass
class _ModulePlan:
    module: str
    status: str                      # "planned" | "refused" | "failed"
    code: str | None = None
    problems: list | None = None
    manifest: Mapping | None = None
    arm_keys: list | None = None     # [(armId, armKey)] in manifest order
    arm_specs: dict | None = None    # armId -> arm


class _Protocol:
    def __init__(self, deps: Dependencies, context, options: dict, identity: dict, t0: float,
                 sender: str = codes.DEFAULT_SENDER):
        self.deps = deps
        self.sender = sender
        self.engine = deps.engine
        self.context = context
        self.options = options
        self.identity = identity
        self.t0 = t0
        self.local: dict = {}        # armKey -> (record, transient); held until aggregation (3.5 rule 10)
        self.hits = 0
        self.computed = 0
        self.plans: dict = {}

    def prefix(self, module: str) -> dict:
        return {**self.identity, "researchSchemaVersion": research_cache.RESEARCH_SCHEMA_VERSION,
                "moduleRevision": self.engine.module_revision(module)}

    # planning
    def plan(self, refused: Mapping) -> None:
        for module in PLAN_ORDER:
            if module in refused:
                code, problems = refused[module]
                self.plans[module] = _ModulePlan(module, "refused", code, problems)
                continue
            try:
                self.plans[module] = self._plan_module(module)
            except Exception:
                self.deps.log(f"[lpbf_research_models] manifest failed: sender={self.sender} module={module} "
                              + traceback.format_exc().strip().replace("\n", " | "))
                self.plans[module] = _ModulePlan(module, "failed", "RESEARCH_EVALUATION_FAILED")

    def _plan_module(self, module: str) -> _ModulePlan:
        manifest = self.engine.manifest(module, self.context, self.options)
        arms = list(manifest["arms"])
        if not arms:
            raise ValueError(f"{module}: a manifest needs at least its nominal arm")
        if len(arms) > MAX_ARMS_PER_MODULE:
            return _ModulePlan(module, "refused", "RESEARCH_ARM_LIMIT_EXCEEDED", [])
        ids = [arm["armId"] for arm in arms]
        if len(set(ids)) != len(ids) or not all(isinstance(i, str) and i for i in ids):
            raise ValueError(f"{module}: arm ids must be unique non-empty strings")
        prefix = self.prefix(module)
        settings = self.engine.method_settings(module)
        keys, specs = [], {}
        for arm in arms:
            dep_keys = []
            for dep_module, dep_arm in arm.get("dependsOn") or []:
                dep_plan = self.plans.get(dep_module)
                if dep_plan is None or dep_plan.status != "planned":
                    raise ValueError(f"{module}/{arm['armId']} depends on unplanned module {dep_module}")
                dep_key = dict(dep_plan.arm_keys).get(dep_arm)
                if dep_key is None:
                    raise ValueError(f"{module}/{arm['armId']} depends on unknown arm {dep_module}/{dep_arm}")
                dep_keys.append([dep_module, dep_arm, dep_key])
            key = research_cache.canonical_sha256({"kind": "arm", "prefix": prefix, "module": module,
                                                   "inputs": arm["inputs"], "methodSettings": settings,
                                                   "dependencies": dep_keys})
            keys.append((arm["armId"], key))
            specs[arm["armId"]] = arm
        return _ModulePlan(module, "planned", manifest=manifest, arm_keys=keys, arm_specs=specs)

    def planned(self) -> list:
        return [self.plans[m] for m in PLAN_ORDER if self.plans[m].status == "planned"]

    def arms_total(self) -> int:
        return sum(len(p.arm_keys) for p in self.planned())

    # arm records
    def lookup(self, key: str) -> bool:
        if key in self.local:
            return True
        record = self.deps.cache.get(key)
        if record is None:
            return False
        self.hits += 1
        self.local[key] = (record, False)
        return True

    def compute(self, plan: _ModulePlan, arm_id: str, key: str) -> None:
        arm = plan.arm_specs[arm_id]
        upstream, upstream_transient = {}, False
        for dep_module, dep_arm in arm.get("dependsOn") or []:
            dep_key = dict(self.plans[dep_module].arm_keys)[dep_arm]
            if not self.lookup(dep_key):
                raise RuntimeError(f"upstream arm {dep_module}/{dep_arm} unavailable for {plan.module}/{arm_id}")
            record, transient = self.local[dep_key]
            upstream[f"{dep_module}/{dep_arm}"] = record
            upstream_transient = upstream_transient or transient
        try:
            record = sanitize_arm_record(self.engine.evaluate_arm(plan.module, self.context, self.options, arm,
                                                                  upstream))
        except Exception:
            self.deps.log(f"[lpbf_research_models] arm failed: sender={self.sender} module={plan.module} "
                          f"arm={arm_id} "
                          + traceback.format_exc().strip().replace("\n", " | "))
            record = {"values": {}, "failures": {}, "armFailure": "RESEARCH_EVALUATION_FAILED"}
        transient = (upstream_transient or record.get("armFailure") in codes.TRANSIENT_CODES
                     or any(code in codes.TRANSIENT_CODES for code in record["failures"].values()))
        self.local[key] = (record, transient)
        self.computed += 1
        if not transient:
            self.deps.cache.put(key, record)

    def records(self, plan: _ModulePlan) -> dict:
        return {arm_id: self.local[key][0] for arm_id, key in plan.arm_keys if key in self.local}

    def transient(self, plan: _ModulePlan) -> bool:
        return any(self.local[key][1] for _, key in plan.arm_keys)

    def elapsed_ms(self) -> float:
        return (self.deps.clock() - self.t0) * 1000.0

    # containers
    def container(self, plan: _ModulePlan, state: str | None) -> dict:
        if plan.status == "refused":
            return self._guarded(plan.module, lambda: self.engine.refused_container(
                plan.module, self.context, plan.code, list(plan.problems or [])))
        if plan.status == "failed":
            return self._failed(plan.module, plan.code)
        manifest = plan.manifest
        banded = bool(manifest.get("banded"))
        records = self.records(plan)
        arm_ids = [a for a, _ in plan.arm_keys]
        if banded and state == "computed" and not manifest.get("declared", True):
            state = "not-declared"
        if not banded:
            state = None
        use_ids = arm_ids if state in ("computed",) else arm_ids[:1]
        agg_key = None
        if state != "pending":
            agg_key = research_cache.canonical_sha256({
                "kind": "aggregate", "prefix": self.prefix(plan.module), "module": plan.module,
                "bandMethod": BAND_METHOD_ID, "state": state, "arms": [[a, k] for a, k in plan.arm_keys],
                "manifest": [arm.get("descriptor") for arm in manifest["arms"]]})
            cached = self.deps.cache.get(agg_key)
            if cached is not None:
                return cached

        def build():
            bands = None if state is None else band_envelopes(state, use_ids, records)
            return self.engine.aggregate(plan.module, self.context, self.options, manifest,
                                         {a: records[a] for a in use_ids}, bands)
        try:
            container = serialization_pass(build())
            research_cache.canonical(container)
        except Exception:
            self.deps.log(f"[lpbf_research_models] module assembly failed: sender={self.sender} "
                          f"module={plan.module} "
                          + traceback.format_exc().strip().replace("\n", " | "))
            return self._failed(plan.module, "RESEARCH_EVALUATION_FAILED")
        if agg_key is not None and not self.transient(plan):
            self.deps.cache.put(agg_key, container)
        return container

    def _failed(self, module: str, code: str) -> dict:
        return self._guarded(module, lambda: self.engine.failed_container(module, self.context, code))

    def _guarded(self, module: str, make: Callable[[], Mapping]) -> dict:
        try:
            container = serialization_pass(make())
            research_cache.canonical(container)
            return container
        except Exception as exc:
            raise RequestScopeFailure("RESEARCH_EVALUATION_FAILED",
                                      f"unavailable container for {module} failed: {exc!r}") from exc

    def block(self, state: str) -> dict:
        block = {"schemaVersion": research_cache.RESEARCH_SCHEMA_VERSION}
        for module in CONTAINERS:
            block[module] = self.container(self.plans[module], state)
        return block

    # stages
    def nominal_stage(self) -> tuple:
        for plan in self.planned():
            arm_id, key = plan.arm_keys[0]
            if not self.lookup(key):
                self.compute(plan, arm_id, key)
        done = sum(1 for plan in self.planned() for _, key in plan.arm_keys
                   if key in self.local or key in self.deps.cache)
        return self.block("pending"), {"armsTotal": self.arms_total(), "armsDone": done, "complete": False}

    def band_stage(self, budget_ms: int | None) -> tuple:
        computed_here = 0
        stopped = False
        for plan in self.planned():
            for arm_id, key in plan.arm_keys:
                if self.lookup(key):
                    continue
                if stopped or (budget_ms is not None and computed_here > 0 and self.elapsed_ms() >= budget_ms):
                    stopped = True
                    continue
                self.compute(plan, arm_id, key)
                computed_here += 1
        done = sum(1 for plan in self.planned() for _, key in plan.arm_keys if key in self.local)
        total = self.arms_total()
        complete = done == total
        progress = {"armsTotal": total, "armsDone": done, "complete": complete}
        return (self.block("computed") if complete else None), progress


def _labels(block: Mapping | None, table: Mapping[str, str]) -> dict:
    if block is None:
        return {}
    paths = []
    for module in CONTAINERS:
        fields = (block.get(module) or {}).get("fields")
        if isinstance(fields, Mapping):
            paths.extend(f"{module}.{name}" for name in fields)
            for name in fields:
                prefix = f"{module}.{name}."
                paths.extend(path for path in table if path.startswith(prefix))
    return {path: table[path] for path in sorted(paths) if path in table}


def _canonical_property_context(request: Mapping, context) -> dict:
    prop_context = dict(request["propertyContext"])
    if prop_context.get("kind") == "build-job-snapshot":
        prop_context["alloyId"] = context.alloyId or prop_context["alloyId"]
    return prop_context


def request_key(identity: Mapping, request: Mapping, context, options: Mapping, engine) -> str:
    """Contract 3.6: identity prefix, canonical process subset, propertyContext, propertySetSha256 and canonical
    researchOptions (a follow flag is the absence of its key, so it is part of the options)."""
    process = request["process"]
    prop_context = _canonical_property_context(request, context)
    return research_cache.canonical_sha256({
        "kind": "request",
        "prefix": {**identity, "researchSchemaVersion": research_cache.RESEARCH_SCHEMA_VERSION,
                   "moduleRevisions": {m: engine.module_revision(m) for m in CONTAINERS}},
        "process": {key: _floats(process[key]) for key in _PROCESS_KEYS},
        "propertyContext": prop_context,
        "propertySetSha256": context.propertySetSha256,
        "researchOptions": _floats(options),
    })


def _refused_modules(deps: Dependencies, context, options: dict) -> tuple:
    controls = deps.engine.controls(context, options)
    refused, all_problems = {}, []
    for module in OPTION_MODULES:
        problems = module_option_problems(deps.engine, module, context, options, controls)
        if problems:
            refused[module] = (codes.option_problem_code(problems), problems)
            all_problems.extend(problems)
    return controls, refused, all_problems


def _describe(deps: Dependencies, request: Mapping, context, options: dict, identity: dict, key: str) -> dict:
    controls, refused, problems = _refused_modules(deps, context, options)
    availability = {}
    for module in CONTAINERS:
        if module in refused:
            availability[module] = {"status": "unavailable", "reasonCode": refused[module][0]}
        else:
            entry = deps.engine.module_availability(module, context, options)
            availability[module] = {"status": entry["status"], "reasonCode": entry.get("reasonCode")}
    return {
        "success": True,
        "schemaVersion": RESPONSE_SCHEMA_VERSION,
        "stage": "describe",
        "clientRequestId": request["clientRequestId"],
        "requestKey": key,
        "controls": controls,
        "presets": deps.engine.presets(context),
        "labels": dict(sorted(deps.label_table.items())),
        "problems": problems,
        "moduleAvailability": availability,
        "identity": _response_identity(identity, context),
    }


def _response_identity(identity: Mapping, context) -> dict:
    return {**identity, "researchSchemaVersion": research_cache.RESEARCH_SCHEMA_VERSION,
            "propertySetSha256": context.propertySetSha256, "propertyContextKind": context.propertyContextKind}


def canonical_sha256_json(value: Any) -> str:
    """sha256 of the canonical JSON of 14.3 item 1 (UTF-8 of an ASCII text)."""
    return hashlib.sha256(codes.canonical_json(value).encode("utf-8")).hexdigest()


def _path_value(block: Mapping, path: str) -> Any:
    """A dotted path into researchModels; None when the block does not carry it."""
    ids_only = path.endswith("[].id")
    parts = (path[:-len("[].id")] if ids_only else path).split(".")
    node: Any = block
    for part in parts:
        if not isinstance(node, Mapping) or part not in node:
            return None
        node = node[part]
    if ids_only:
        return [item.get("id") for item in node if isinstance(item, Mapping)] if isinstance(node, list) else None
    return node


def _hash_manifests(value: Any) -> Any:
    """14.3 item 4: a band's manifest is replaced by manifestSha256 (canonical descriptor list) and manifestLength."""
    if isinstance(value, Mapping):
        out = {}
        for key, item in value.items():
            if key == "manifest" and isinstance(item, list):
                out["manifestSha256"] = canonical_sha256_json(item)
                out["manifestLength"] = len(item)
            else:
                out[key] = _hash_manifests(item)
        return out
    if isinstance(value, list):
        return [_hash_manifests(item) for item in value]
    return value


def blind_relay_subset(request: Mapping, context, request_key: str, identity: Mapping, digests: Mapping,
                       block: Mapping, labels: Mapping) -> dict:
    """The closed projection BLIND_RELAY_V1 of a complete block (14.3 item 4); no volatile member enters it."""
    spec = codes.BLIND_RELAY_V1
    relay = request["relay"]
    subset: dict = {
        "relaySchemaVersion": codes.RELAY_KIND,
        "relayPathsSha256": codes.RELAY_PATHS_SHA256,
        "binding": {"previewSha256": relay["previewSha256"], "conditionOrdinal": relay["conditionOrdinal"]},
        "request": {
            "process": {key: _floats(request["process"][key]) for key in codes.RELAY_PROCESS_KEYS},
            "si": {"power_W": context.power_W, "speed_m_s": context.speed_m_s,
                   "beamDiameter_m": context.beamDiameter_m, "preheat_K": context.preheat_K},
            "propertyContext": _canonical_property_context(request, context),
            "sender": request.get("sender", codes.DEFAULT_SENDER),
        },
        "requestKey": request_key,
        "identity": {key: identity[key] for key in spec["identity"]},
        "digests": dict(digests),
    }
    field_paths = []
    for section in ("scored", "context", "support", "notes", "statements"):
        values = {}
        for path in spec[section]:
            value = _path_value(block, path)
            # Numeric bands refer to their container's one manifest (A1/5.3).
            # Materialize that reference only for the relay's hash projection.
            if section in ("scored", "context") and isinstance(value, Mapping) and isinstance(value.get("band"), Mapping):
                manifest = _path_value(block, path.split(".")[0] + ".band.manifest")
                if "manifest" not in value["band"] and isinstance(manifest, list):
                    value = {**value, "band": {**value["band"], "manifest": manifest}}
            values[path] = _hash_manifests(value) if section in ("scored", "context") else value
            if section in ("scored", "context"):
                module, _fields, name = path.split(".")
                field_paths.append(f"{module}.{name}")
        subset[section] = values
    subset["labels"] = {path: labels[path] for path in sorted(field_paths) if path in labels}
    return subset


def _respond(deps: Dependencies, raw: str, t0: float) -> dict:
    stale = deps.identity.check()
    if stale.get("stale"):
        raise Refused("RESEARCH_CODE_STALE", [], recycle=True)
    request = check_request(raw, deps.properties)
    if deps.engine is None:
        raise RequestScopeFailure("RESEARCH_EVALUATION_FAILED",
                                  "the P8 physics evaluator is not installed in this build (phase C)")
    try:
        context = research_context.resolve(request, deps.properties)
    except Exception as exc:
        raise RequestScopeFailure("RESEARCH_EVALUATION_FAILED", f"research context: {exc!r}") from exc
    options = normalized_options(request)
    identity = dict(deps.identity.identity())
    key = request_key(identity, request, context, options, deps.engine)
    stage = request["stage"]
    if stage == "describe":
        return _describe(deps, request, context, options, identity, key)
    _controls, refused, _problems = _refused_modules(deps, context, options)
    protocol = _Protocol(deps, context, options, identity, t0, request.get("sender", codes.DEFAULT_SENDER))
    protocol.plan(refused)
    if stage == "nominal":
        block, progress = protocol.nominal_stage()
    else:
        block, progress = protocol.band_stage(request.get("timeBudgetMs"))
    response = {
        "success": True,
        "schemaVersion": RESPONSE_SCHEMA_VERSION,
        "clientRequestId": request["clientRequestId"],
        "requestKey": key,
        "stage": stage,
        "progress": progress,
        "researchModels": block,
        "labels": _labels(block, deps.label_table),
        "identity": _response_identity(identity, context),
        "cache": {"cacheInstanceId": deps.cache_instance_id, "armsHit": protocol.hits,
                  "armsComputed": protocol.computed},
    }
    if block is not None:
        # Revision 3 (14.3 items 1 and 2): digests on every complete response; the relay on a complete band
        # response to a relay request. Both are computed on exactly the values that are serialized.
        block = serialization_pass(block)
        labels = response["labels"]
        digests = {"researchModelsSha256": canonical_sha256_json(block), "labelsSha256": canonical_sha256_json(labels)}
        response["researchModels"] = block
        response["digests"] = digests
        if stage == "band" and progress["complete"] and "relay" in request:
            subset = blind_relay_subset(request, context, key, response["identity"], digests, block, labels)
            subset_json = codes.canonical_json(subset)
            if len(subset_json) > codes.RELAY_SUBSET_MAX_CHARS:
                raise RequestScopeFailure("RESEARCH_RESPONSE_TOO_LARGE",
                                          f"relay subsetJson has {len(subset_json)} characters "
                                          f"(cap {codes.RELAY_SUBSET_MAX_CHARS})", cause="relay")
            response["relay"] = {"kind": codes.RELAY_KIND, "subsetJson": subset_json,
                                 "subsetSha256": hashlib.sha256(subset_json.encode("ascii")).hexdigest()}
    return response


def _dumps(value: Any) -> str:
    return codes.canonical_json(value)


def _failure_text(code: str, cause: str | None = None) -> str:
    body = {"success": False, "errorKind": RESEARCH_ERROR_KIND, "reasonCode": code}
    if cause is not None:
        body["cause"] = cause
    return _dumps(body)


def run(raw: str, deps: Dependencies) -> tuple:
    """One request: (stdout text, exit code). Never raises for a request; an internal bug outside any module becomes
    the RESEARCH_EVALUATION_FAILED envelope with its traceback on stderr only."""
    t0 = deps.clock()
    try:
        response = _respond(deps, raw, t0)
    except Refused as refused:
        body = {"success": False, "errorKind": VALIDATION_ERROR_KIND, "reasonCode": refused.code,
                "problems": serialization_pass(refused.problems)}
        if refused.recycle:
            body["recycleWorker"] = True
        return _dumps(body), EXIT_REFUSED
    except RequestScopeFailure as failure:
        deps.log(f"[lpbf_research_models] {failure.code}: {failure.detail}")
        return _failure_text(failure.code, failure.cause), EXIT_OK
    except Exception:
        deps.log("[lpbf_research_models] RESEARCH_EVALUATION_FAILED: "
                 + traceback.format_exc().strip().replace("\n", " | "))
        return _failure_text("RESEARCH_EVALUATION_FAILED"), EXIT_OK
    if "computeMs" not in response and response.get("stage") != "describe":
        response["computeMs"] = round((deps.clock() - t0) * 1000.0, 1)
    try:
        text = _dumps(serialization_pass(response))
    except (TypeError, ValueError):
        deps.log("[lpbf_research_models] RESEARCH_SERIALIZATION_FAILED: "
                 + traceback.format_exc().strip().replace("\n", " | "))
        return _failure_text("RESEARCH_SERIALIZATION_FAILED"), EXIT_OK
    if len(text.encode("utf-8")) > MAX_RESPONSE_BYTES:
        deps.log(f"[lpbf_research_models] RESEARCH_RESPONSE_TOO_LARGE: {len(text)} bytes")
        return _failure_text("RESEARCH_RESPONSE_TOO_LARGE"), EXIT_OK
    return text, EXIT_OK


def main() -> int:
    research_cache.lower_process_priority_once()
    raw = sys.stdin.read()
    text, code = run(raw, default_dependencies())
    sys.stdout.write(text + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
