"""Fake-evaluator harness for the P8 research transport tests (integration contract 2026-10-15, 10.3 and 13.11).

Test support only, no test cases. It provides a deterministic fake engine (no physics), a stubbed identity provider
(constant research and served hashes), a stubbed property provider (one fixed synthetic property set, so
propertySetSha256 is constant), a fixed label table, a fake clock, the guard that makes every research test fail on
a call of the served solver (minor note 10), and the R-TR-11 fixture request.

None of the fake values is physics: they are exact arithmetic on the request so transport behaviour (stages, cache,
bands, non-finite handling) can be checked byte for byte. The fixture they produce describes transport shape only
and does not change when the phase C evaluator lands.

Regenerate the transport fixture (only when the transport shape changes deliberately):
    python -B test_lpbf_research_harness.py --write-fixture
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import sys
import unittest
from pathlib import Path
from typing import Any, Mapping
from unittest import mock

import lpbf_research_cache as research_cache
import lpbf_research_codes as codes
import lpbf_research_context as research_context
import lpbf_research_models as models

PYTHON_DIR = Path(__file__).resolve().parent
REPO_ROOT = PYTHON_DIR.parent
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "lpbf-research-response-v1.json"

SYNTHETIC_MATERIAL = "P8-Synthetic-Alloy"
SYNTHETIC_ALLOY_ID = "p8synthetic"
SYNTHETIC_PROPERTIES = {
    "base": "Syn",
    "density_kg_m3": 5000.0,
    "thermal_conductivity_W_mK": 20.0,
    "specific_heat_J_kgK": 625.0,
    "liquidus_C": 1500.0,
    "absorptivity_IR": 0.375,
    "absorptivity_index_IR": 0.25,
    "absorptivity_Green": 0.5,
}
# A second synthetic material, so request-key tests can change the material.
SYNTHETIC_MATERIAL_B = "P8-Synthetic-Alloy-B"
SYNTHETIC_PROPERTIES_B = {**SYNTHETIC_PROPERTIES, "thermal_conductivity_W_mK": 25.0, "liquidus_C": 1450.0}
STUB_RESEARCH_SHA256 = hashlib.sha256(b"p8-stub-research-implementation").hexdigest()
STUB_SERVED_FINGERPRINT = hashlib.sha256(b"p8-stub-served-implementation").hexdigest()
FIXTURE_CACHE_INSTANCE_ID = "0123456789abcdef0123456789abcdef"

FAKE_FIELDS = {
    "keyholeCavity": ("syntheticDepth_um", "syntheticRatio", "syntheticRegime"),
    "meltDepthLink": ("syntheticLinkedDepth_um", "syntheticLeg"),
    "marangoni": ("syntheticVelocity_m_s", "syntheticDirection"),
    "surfaceBalance": ("syntheticFlux_W_m2", "syntheticTemperature_K"),
    "alSi10MgVapourMgAware": ("syntheticScenario_K",),
    "alSi10MgIndexDisclosure": ("syntheticIndexRatio",),
    "unavailablePhysics": ("syntheticClosure",),
}
FIXED_LABELS = {f"{module}.{field}": f"Synthetic {field} (fake evaluator, not physics)"
                for module, fields in FAKE_FIELDS.items() for field in fields}

# Declared arms per banded module: (armId, {input: multiplier}). The first is the nominal arm.
DEFAULT_DECLARED_ARMS = {
    "cavity": (("nominal", {}), ("absorptance_low", {"A": 0.875}), ("absorptance_high", {"A": 1.125}),
               ("power_minus5", {"P": 0.95}), ("power_plus5", {"P": 1.05}), ("diameter_plus5", {"d": 1.05})),
    "marangoni": (("nominal", {}), ("slope_transfer", {"slope": 1.25}), ("length_short", {"L": 0.5})),
    "surfaceBalance": (("nominal", {}), ("emissivity_alt", {"eps": 1.5}), ("power_plus5", {"P": 1.05})),
}


class FakeClock:
    """Deterministic seconds; the fake engine advances it per evaluated arm."""

    def __init__(self, start: float = 1000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class StubIdentity:
    """Constant identity; ``stale`` can be switched on to emulate changed code."""

    def __init__(self, research: str = STUB_RESEARCH_SHA256, served: str = STUB_SERVED_FINGERPRINT):
        self.research = research
        self.served = served
        self.stale = False
        self.checks = 0

    def identity(self) -> dict:
        return {"researchImplementationSha256": self.research, "servedImplementationFingerprint": self.served}

    def check(self) -> dict:
        self.checks += 1
        return {"stale": self.stale, "rehashed": False, "changed": [], "elapsedMs": 0.0}


def synthetic_property_provider() -> research_context.PropertyProvider:
    def base_properties(material):
        table = {SYNTHETIC_MATERIAL: SYNTHETIC_PROPERTIES, SYNTHETIC_MATERIAL_B: SYNTHETIC_PROPERTIES_B}
        return dict(table[material]) if material in table else None

    def resolve_alloy_id(name):
        key = str(name).strip().lower()
        return SYNTHETIC_ALLOY_ID if key in (SYNTHETIC_ALLOY_ID, SYNTHETIC_MATERIAL.lower()) else None

    def alloy_thermal_name(alloy_id):
        return SYNTHETIC_MATERIAL if alloy_id == SYNTHETIC_ALLOY_ID else None

    def material_snapshot(alloy_id):
        snapshot = {"schemaVersion": 1, "alloyId": alloy_id, "thermal": dict(SYNTHETIC_PROPERTIES)}
        return snapshot, research_cache.canonical_sha256(snapshot)

    def conduction_kernel(material, props, overrides, preheat_C):
        return (float(props["thermal_conductivity_W_mK"]), float(props["specific_heat_J_kgK"]),
                float(props["density_kg_m3"]), "synthetic-constant", "synthetic", "synthetic", None)

    def index_absorptivity(wavelength, base, overrides, material):
        merged = dict(base)
        merged.update(overrides or {})
        return float(merged["absorptivity_index_IR"])

    return research_context.PropertyProvider(
        base_properties=base_properties, resolve_alloy_id=resolve_alloy_id, alloy_thermal_name=alloy_thermal_name,
        material_snapshot=material_snapshot, conduction_kernel=conduction_kernel,
        index_absorptivity=index_absorptivity, wavelengths=("IR_1064nm", "Green_515nm"),
        absorption_models=("flat-plate", "powder-raytrace"))


def _provenance(kind: str, label: str, default: Any, follows: str | None = None) -> dict:
    return {"kind": kind, "label": label, "sourceId": f"fake:{kind}", "sourceLocator": None,
            "declarationLocator": "test_lpbf_research_harness.py", "source": None, "scope": "synthetic",
            "status": "inRange", "sourceEvidenceKind": "Unresolved", "defaultValue": default,
            "defaultKind": "declaredAssumption", "followsInput": follows,
            "followState": "following" if follows else None, "dependsOn": [follows] if follows else [],
            "phase": None, "referenceTemperature_K": None, "sourceRange_K": None}


class FakeEngine:
    """Deterministic stand-in for the phase C engine. Knobs inject non-finite values, exceptions, deterministic
    failures, oversize containers and arbitrary declared-arm tables; ``evaluations`` logs every evaluated arm."""

    def __init__(self, *, declared: Mapping | None = None, clock: FakeClock | None = None,
                 seconds_per_arm: float = 0.0, nonfinite: Mapping | None = None, raise_in_arm=(),
                 raise_in_aggregate=(), failures: Mapping | None = None, oversize: bool = False,
                 o8_declared: bool = False):
        self.declared = {k: tuple(v) for k, v in (declared or DEFAULT_DECLARED_ARMS).items()}
        self.clock = clock
        self.seconds_per_arm = seconds_per_arm
        self.nonfinite = dict(nonfinite or {})          # (module, armId, field) -> float
        self.raise_in_arm = set(raise_in_arm)           # (module, armId)
        self.raise_in_aggregate = set(raise_in_aggregate)
        self.failures = dict(failures or {})            # (module, armId, field) -> reason code
        self.oversize = oversize
        self.o8_declared = o8_declared
        self.evaluations: list = []
        self.aggregations: list = []

    # identity and settings
    def module_revision(self, module_id):
        return f"fake-{module_id}-rev1"

    def method_settings(self, module_id):
        return {"fakeTolerance": 1e-9, "fakeSamples": 16}

    # controls (describe) and option rules
    def _defaults(self, context, options):
        mar, sur = options["marangoni"], options["surfaceBalance"]
        delta = mar.get("deltaTemperature_K", 500.0)
        return {
            "surfaceTensionSlope_N_mK": mar.get("surfaceTensionSlope_N_mK", -1.9e-4),
            "length_m": mar.get("length_m", context.beamDiameter_m),
            "deltaTemperature_K": delta,
            "referenceTemperature_K": mar.get("referenceTemperature_K", context.conduction.liquidus_K + delta / 2),
            "emissivity": sur.get("emissivity", 0.3),
            "evaporationAccommodation": sur.get("evaporationAccommodation", 1.0),
            "recoilFraction": sur.get("recoilFraction", 0.6),
        }

    def controls(self, context, options):
        values = self._defaults(context, options)
        specs = (
            ("marangoni", "surfaceTensionSlope_N_mK", "Synthetic slope", "N/(m K)", -0.003, 0.003, None),
            ("marangoni", "length_m", "Synthetic length", "m", 1e-6, 0.01, "beamDiameter_m"),
            ("marangoni", "deltaTemperature_K", "Synthetic temperature difference", "K", 0.0, 10000.0, None),
            ("marangoni", "referenceTemperature_K", "Synthetic reference temperature", "K", 300.0, 10000.0,
             "deltaTemperature_K"),
            ("surfaceBalance", "emissivity", "Synthetic emissivity", "1", 0.0, 1.0, None),
            ("surfaceBalance", "evaporationAccommodation", "Synthetic accommodation", "1", 0.0, 1.0, None),
            ("surfaceBalance", "recoilFraction", "Synthetic recoil fraction", "1", 0.0, 1.0, None),
        )
        out = []
        for module, key, label, unit, lo, hi, follows in specs:
            user = key in options[module]
            kind = "userInput" if user else ("followsInput" if follows else "declaredAssumption")
            out.append({"key": key, "module": module, "label": label, "help": f"{label} (fake evaluator).",
                        "unit": unit, "displayUnits": {unit: 1.0}, "valueType": "number", "enumValues": None,
                        "min": lo, "max": hi, "enabled": True, "value": values[key],
                        "provenance": _provenance(kind, kind, None if user else values[key],
                                                  None if user else follows),
                        "rangeAdmitted": True, "resetLabel": None if not user else "Reset to declared assumption"})
        return out

    def presets(self, context):
        return {"vapourPreset": [{"id": "custom", "label": "Custom vapour triple", "admitted": True,
                                  "reasonCode": None}],
                "slopeMode": [{"id": "direct", "label": "Direct slope"}]}

    def option_rule_problems(self, module_id, context, options):
        mar = options["marangoni"]
        if module_id == "marangoni" and mar.get("slopeMode", "direct") != "direct" \
                and "surfaceTensionSlope_N_mK" in mar:
            return [codes.option_problem("/researchOptions/marangoni/surfaceTensionSlope_N_mK", "mode-field-ignored",
                                         value=mar["surfaceTensionSlope_N_mK"], label="Synthetic slope",
                                         mode=mar["slopeMode"])]
        return []

    def module_availability(self, module_id, context, options):
        if module_id == "alSi10MgIndexDisclosure":
            return {"status": "not-applicable", "reasonCode": "ALLOY_NOT_ALSI10MG"}
        if module_id == "unavailablePhysics":
            return {"status": "unavailable", "reasonCode": "KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE"}
        return {"status": "available", "reasonCode": None}

    # manifests
    def _arms(self, table: str, base_inputs: Mapping, user_ranges: Mapping, module: str) -> list:
        arms = []
        for arm_id, changes in self.declared[table]:
            inputs = dict(base_inputs)
            for name, factor in changes.items():
                if name in inputs:
                    inputs[name] = inputs[name] * factor
            arms.append({"armId": arm_id, "inputs": sorted([k, v, f"fake:{arm_id}" if k in changes else "fake:nominal"]
                                                           for k, v in inputs.items()),
                         "descriptor": {"armId": arm_id, "family": "nominal" if arm_id == "nominal" else "process",
                                        "label": arm_id, "changes": sorted(changes)},
                         "dependsOn": [], "_values": inputs})
        for key in sorted(user_ranges):
            for end in ("min", "max"):
                inputs = dict(base_inputs)
                inputs[key] = float(user_ranges[key][end])
                arm_id = f"user:{module}:{key}:{'low' if end == 'min' else 'high'}"
                arms.append({"armId": arm_id, "inputs": sorted([k, v, "fake:user" if k == key else "fake:nominal"]
                                                               for k, v in inputs.items()),
                             "descriptor": {"armId": arm_id, "family": "user-endpoint", "label": arm_id,
                                            "changes": [key]},
                             "dependsOn": [], "_values": inputs})
        return arms

    def manifest(self, module_id, context, options):
        c = context.conduction
        cavity = {"P": context.power_W, "v": context.speed_m_s, "d": context.beamDiameter_m, "T0": context.preheat_K,
                  "K": c.conductivity_W_mK, "alpha": c.diffusivity_m2_s, "A": c.wallAbsorptance}
        if module_id in ("keyholeCavity", "meltDepthLink"):
            arms = self._arms("cavity", cavity, {}, module_id)
            if module_id == "meltDepthLink":
                for arm in arms:
                    arm["dependsOn"] = [["keyholeCavity", arm["armId"]]]
            return {"banded": True, "declared": True, "arms": arms}
        if module_id == "marangoni":
            d = self._defaults(context, options)
            base = {"slope": d["surfaceTensionSlope_N_mK"], "L": d["length_m"], "dT": d["deltaTemperature_K"]}
            ranges = {k: v for k, v in options["ranges"]["marangoni"].items()}
            renamed = {{"surfaceTensionSlope_N_mK": "slope", "length_m": "L", "deltaTemperature_K": "dT"}.get(k, k): v
                       for k, v in ranges.items()}
            return {"banded": True, "declared": True, "arms": self._arms("marangoni", base, renamed, module_id)}
        if module_id == "surfaceBalance":
            d = self._defaults(context, options)
            base = {"P": context.power_W, "eps": d["emissivity"], "acc": d["evaporationAccommodation"],
                    "A": c.wallAbsorptance}
            ranges = {{"emissivity": "eps", "evaporationAccommodation": "acc"}.get(k, k): v
                      for k, v in options["ranges"]["surfaceBalance"].items()}
            return {"banded": True, "declared": True, "arms": self._arms("surfaceBalance", base, ranges, module_id)}
        nominal = {"armId": "nominal", "inputs": [["Tl", c.liquidus_K, "fake:nominal"]], "descriptor": None,
                   "dependsOn": [], "_values": {"Tl": c.liquidus_K}}
        if module_id == "alSi10MgVapourMgAware":
            return {"banded": True, "declared": self.o8_declared, "arms": [nominal]}
        return {"banded": False, "declared": False, "arms": [nominal]}

    # arms
    def evaluate_arm(self, module_id, context, options, arm, upstream):
        arm_id = arm["armId"]
        self.evaluations.append((module_id, arm_id))
        if self.clock is not None:
            self.clock.advance(self.seconds_per_arm)
        if (module_id, arm_id) in self.raise_in_arm:
            raise RuntimeError(f"injected failure in {module_id}/{arm_id}")
        x = arm["_values"]
        if module_id == "keyholeCavity":
            values = {"syntheticDepth_um": x["P"] * x["A"] / (x["d"] * 1e4),
                      "syntheticRatio": x["P"] / 100.0 + x["alpha"] * 1e3,
                      "syntheticRegime": "above" if x["P"] * x["A"] > 70.0 else "below"}
        elif module_id == "meltDepthLink":
            cavity = upstream[f"keyholeCavity/{arm_id}"]
            depth = cavity["values"].get("syntheticDepth_um")
            values = {"syntheticLinkedDepth_um": None if depth is None else depth * 1.5 + 10.0,
                      "syntheticLeg": "conditional-link" if depth and depth > 90.0 else "conduction"}
        elif module_id == "marangoni":
            values = {"syntheticVelocity_m_s": abs(x["slope"]) * x["dT"] / (x["L"] * 1e3),
                      "syntheticDirection": "outward" if x["slope"] < 0 else "inward"}
        elif module_id == "surfaceBalance":
            values = {"syntheticFlux_W_m2": x["P"] * x["A"] * 1e6, "syntheticTemperature_K": 3000.0 - 500.0 * x["eps"]}
        elif module_id == "alSi10MgVapourMgAware":
            values = {"syntheticScenario_K": x["Tl"] + 777.0}
        elif module_id == "alSi10MgIndexDisclosure":
            values = {"syntheticIndexRatio": context.conduction.wallAbsorptance / context.indexAbsorptance}
        else:
            values = {"syntheticClosure": None}
        failures = {"syntheticClosure": "KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE"} if module_id == "unavailablePhysics" \
            else {}
        for (mod, aid, field), bad in self.nonfinite.items():
            if mod == module_id and aid == arm_id:
                values[field] = bad
        for (mod, aid, field), code in self.failures.items():
            if mod == module_id and aid == arm_id:
                values[field] = None
                failures[field] = code
        return {"values": values, "failures": failures}

    # containers
    def _field(self, value, code, band) -> dict:
        return {"value": value, "unit": "1", "reasonCode": code, "band": band}

    def aggregate(self, module_id, context, options, manifest, records, bands):
        self.aggregations.append(module_id)
        if module_id in self.raise_in_aggregate:
            raise RuntimeError(f"injected assembly failure in {module_id}")
        nominal_id = manifest["arms"][0]["armId"]
        nominal = records[nominal_id]
        fields = {}
        for name in FAKE_FIELDS[module_id]:
            value = nominal["values"].get(name)
            code = None if value is not None else nominal["failures"].get(name, "RESEARCH_EVALUATION_FAILED")
            band = None if bands is None else bands["numeric"].get(name)
            fields[name] = self._field(value, code, band)
        status, rc = "available", None
        if module_id == "alSi10MgIndexDisclosure":
            status, rc = "not-applicable", "ALLOY_NOT_ALSI10MG"
        elif module_id == "unavailablePhysics":
            status, rc = "unavailable", "KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE"
        container = {"modelId": f"fake-{module_id}-v1", "status": status, "reasonCode": rc, "fields": fields,
                     "band": None if bands is None else {
                         "state": bands["state"], "method": bands["method"],
                         "manifest": [{"armId": a, "label": a} for a in bands["armIds"]],
                         "categoricalSupport": [{"field": f, "value": e["value"], "count": e["count"]}
                                                for f, entries in sorted(bands["categorical"].items())
                                                for e in entries],
                         "failedArms": bands["failedArms"]}}
        if self.oversize and module_id == "keyholeCavity":
            container["padding"] = "x" * (5 * 1024 * 1024)
        return container

    def refused_container(self, module_id, context, code, problems):
        return {"modelId": f"fake-{module_id}-v1", "status": "unavailable", "reasonCode": code, "fields": {},
                "band": None, "problems": problems}

    def failed_container(self, module_id, context, code):
        return {"modelId": f"fake-{module_id}-v1", "status": "unavailable", "reasonCode": code, "fields": {},
                "band": None}


def make_dependencies(engine: FakeEngine | None = None, *, cache=None, identity=None, clock=None,
                      cache_instance_id: str = FIXTURE_CACHE_INSTANCE_ID, labels=None, log=None,
                      properties=None) -> models.Dependencies:
    lines = [] if log is None else log
    return models.Dependencies(
        engine=engine if engine is not None else FakeEngine(),
        properties=properties or synthetic_property_provider(),
        identity=identity or StubIdentity(),
        cache=cache if cache is not None else research_cache.ResearchLRU(),
        cache_instance_id=cache_instance_id,
        label_table=dict(FIXED_LABELS if labels is None else labels),
        clock=clock or FakeClock(),
        log=lines.append,
    )


def request(stage: str = "nominal", *, budget: Any = "absent", options: Mapping | None = None,
            process: Mapping | None = None, property_context: Mapping | None = None, client_id: str = "melt-pool:1",
            material: str = SYNTHETIC_MATERIAL) -> dict:
    body = {
        "schemaVersion": "p8-research-request-v1",
        "supersedeKey": "p8-research:melt-pool",
        "clientRequestId": client_id,
        "stage": stage,
        "process": {"material": material, "laserPower_W": 200, "scanSpeed_mm_s": 800, "beamDiameter_um": 80,
                    "preheatTemp_C": 20, "laserWavelength": "IR_1064nm", "absorptionModel": "flat-plate"},
        "propertyContext": dict(property_context or {"kind": "nominal"}),
    }
    if process:
        body["process"].update(process)
    if stage == "band":
        body["timeBudgetMs"] = None if budget == "absent" else budget
    elif budget != "absent":
        body["timeBudgetMs"] = budget
    if options is not None:
        body["researchOptions"] = options
    return body


def call(deps: models.Dependencies, body: Any) -> tuple:
    """(parsed stdout, exit code, stdout text) of one dispatch-script run."""
    raw = body if isinstance(body, str) else json.dumps(body)
    text, code = models.run(raw, deps)
    return json.loads(text), code, text


FIXTURE_OPTIONS = {"marangoni": {"deltaTemperature_K": 400},
                   "ranges": {"surfaceBalance": {"emissivity": {"min": 0.25, "max": 0.375}}}}


def fixture_request() -> dict:
    return request("band", budget=None, options=FIXTURE_OPTIONS, client_id="fixture:1")


def fixture_response() -> dict:
    """R-TR-11: fake engine, stubbed identity and properties, fixed arm and label tables, injected cacheInstanceId,
    cold cache; computeMs removed."""
    deps = make_dependencies(FakeEngine(), cache=research_cache.ResearchLRU())
    parsed, code, _text = call(deps, fixture_request())
    if code != 0:
        raise RuntimeError(f"fixture request failed with exit {code}: {parsed}")
    parsed.pop("computeMs", None)
    return parsed


def fixture_text(response: Mapping) -> str:
    return json.dumps(response, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n"


@contextlib.contextmanager
def forbid_served_solver():
    """Every research test runs with calculate_meltpool_physics patched to raise (contract 10.3, minor note 10), on
    the solver module and on every loaded module that bound it by name."""
    import lpbf_thermal_solver

    original = lpbf_thermal_solver.calculate_meltpool_physics

    def refuse(*_args, **_kwargs):
        raise AssertionError("research code called calculate_meltpool_physics")
    patches = [mock.patch.object(lpbf_thermal_solver, "calculate_meltpool_physics", refuse)]
    for name, module in list(sys.modules.items()):
        if module is not None and module is not lpbf_thermal_solver \
                and getattr(module, "calculate_meltpool_physics", None) is original:
            patches.append(mock.patch.object(module, "calculate_meltpool_physics", refuse))
    with contextlib.ExitStack() as stack:
        for patch in patches:
            stack.enter_context(patch)
        yield refuse


class ResearchTestCase(unittest.TestCase):
    """Base class of every research test: calculate_meltpool_physics raises while a test runs. A test that needs
    the served solver itself (R-CTX-2) calls ``self.served_calculate_meltpool_physics``, the original function."""

    def setUp(self):
        import lpbf_thermal_solver
        super().setUp()
        self.served_calculate_meltpool_physics = lpbf_thermal_solver.calculate_meltpool_physics
        guard = forbid_served_solver()
        guard.__enter__()
        self.addCleanup(guard.__exit__, None, None, None)


def is_finite_json(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(is_finite_json(v) for v in value.values())
    if isinstance(value, list):
        return all(is_finite_json(v) for v in value)
    return True


def strict_loads(text: str) -> Any:
    """A strict parser: NaN, Infinity and -Infinity tokens are refused."""
    def refuse(token):
        raise ValueError(f"non-standard JSON token {token}")
    return json.loads(text, parse_constant=refuse)


if __name__ == "__main__":
    if sys.argv[1:] != ["--write-fixture"]:
        print(__doc__)
        sys.exit(2)
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(fixture_text(fixture_response()), encoding="utf-8", newline="\n")
    print(f"wrote {FIXTURE_PATH}")
