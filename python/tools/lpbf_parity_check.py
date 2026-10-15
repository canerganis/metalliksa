#!/usr/bin/env python3
"""LPBF 5c parity harness: bit-equality goldens for the planned fingerprint bump.

Design: docs/LPBF_5C_FINGERPRINT_BUMP_DESIGN_2026-10-04.md, section 2, stage P (P2 parity
harness, P3 material and case-generation goldens) and section 8. The goldens were first
recorded at 7482697c... (before the 5c bump) and re-recorded, observations unchanged, at
edddf0dc... (B5 step 2); they are the "before" side of the next bump and are never
re-recorded in the same commit as a manifest edit. After every bump commit ``--check``
must stay green: bit-equal, or drifting only where --expect-drift allows it.

What "bit-equal" means (design 2.1):
- A run() result is compared after removing provenance.createdAt, runtime_s
  (top level or provenance), the worker-only fields provenance.executionRuntime,
  runKind and the input.json / capabilities.json artifact entries. Everything
  else is hashed as canonical JSON (sort_keys=True, allow_nan=False) AND as an
  insertion-ordered, type-tagged tree (int vs float, tuple vs list, exact float
  bits), so key order and Python types are pinned as well.
- provenance.implementationHash is compared separately: it must equal the CURRENT
  implementation_fingerprint(), which in turn must equal the pinned
  python/lpbf_implementation_fingerprint.expected value. On the bump branch
  (B1-B5, before B6 re-pins) pass --expect-unpinned: the pin mismatch is then a
  warning, every other check still fails. The hash is the only value that may
  differ from the golden, and only at the bump.
- Every artifact file written by run() is compared by SHA-256; every NPZ is also
  compared array by array (dtype, shape, bytes).

Cases (design 2.3 matrix): G1..G16 plus an NPZ determinism check; G17-G19 (B5 step 2)
document today's non-IN718 evaporation L_v, IN625 latent heats and the emissivity echo
so the corrected-physics bump has measurable drift. G2 (the in-repo
real bare-plate 100 W fixture) takes about 106 s on the reference machine and is
opt-in (--slow or --case). Everything else runs in about one minute.

Usage (from python/, locked interpreter, PYTHONDONTWRITEBYTECODE=1):
    python -B tools/lpbf_parity_check.py --list
    python -B tools/lpbf_parity_check.py --check [--slow] [--case ID ...] [--expect-unpinned]
        [--expect-drift CASE[:KEY_GLOB][,...]]
    python -B tools/lpbf_parity_check.py --record --force [--twice] [--slow] [--case ID ...]

--expect-drift (corrected-physics bump), entries CASE or CASE:KEY_GLOB (fnmatch on the
observation key), comma-separated or repeated:
- Only matched observations may differ; they are reported as DRIFT with a before -> after
  line (floats with float.hex()) plus leaf-level raw before -> after values when the golden
  recorded them (rawValues: the pre-hash value of small digest observations).
- Any other diff fails; implementation-hash, pin and golden problems always fail; an entry
  that matches no drifted observation, or a case that is not selected, fails (stale).
- Identity digests (*materialRevisionSha256*, *materialSha256*, *inputSha256*) fail in
  every case unless an entry names that exact key.
- The reference transient cases g1/g2/g4 are refused as whole cases and refuse every
  glob: only exact CASE:KEY entries (no * ? [ characters) are accepted for them. Their
  numerics (metrics, thermalHistory, energyBalance, field*, artifacts, NPZ, fixture equality,
  peakInterpolatedMeltPool, midTrack*, massBalance, numericalDiagnostics, phaseAudit,
  settings, discretization, scanPath) fail whatever the allowlist.
- Honesty observations (validationStatus, productionReady, coreContract.solverId, confidence,
  effectiveMode, experimentalValidation, experimentalComparison, unresolvedPhysics,
  opticalOperatorMatched, each with or without .key., and the G9 observation
  in625.validateScreeningAdmission) never drift in ANY case, whatever the allowlist.
- Error rule (integration contract 6.1, gate P02): value to error never passes, under any entry.
  This covers {"error": text}, G11's run keys, G16's *.error, per-item ["error", text] in each()
  raw lists, and reject.* plain-string refusals. A refusal becoming NO-ERROR never passes.
  Changed errors, error to value, new error keys and removals need the exact observation key;
  protected honesty and reference-numerics observations retain their stricter rules.
- With --allow-environment-mismatch a drift run ends DIAGNOSTIC (exit 3), never PASS.

--record refuses to overwrite an existing golden without --force, and refuses to
record at all unless implementation_fingerprint() equals the pinned .expected
value (so goldens are never captured from an unpinned implementation). --twice
runs every case twice in different work directories and refuses to write unless
both runs are identical (determinism and work-directory independence).

Reference machine only: the goldens are bit-exact results of ONE environment,
recorded in each golden as recordedEnvironment (Python, numpy, OS, the locked
runtime directory, CPU brand, numpy SIMD baseline/dispatch/found features, BLAS).
--check is valid only there: when environment() differs, every case is reported
"SKIP ... NOT VERIFIED" and the command exits 3 (never PASS);
--allow-environment-mismatch compares anyway, for diagnostics only. This harness
is therefore NOT part of CI; CI runs the environment-independent pin, source
identity and closure tests. G10 file trees are hashed with CRLF -> LF and POSIX
names, so their digests do not depend on the writer's platform newlines.
"""

from __future__ import annotations

import argparse
import copy
import fnmatch
import hashlib
import io
import json
import math
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

PYTHON_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

import numpy as np  # noqa: E402
from lpbf_fingerprint_pin import EXPECTED_FINGERPRINT_FILE, read_pinned_fingerprint  # noqa: E402

GOLDEN_DIR = PYTHON_DIR / "golden" / "lpbf_parity"
DEFAULT_WORK_ROOT = PYTHON_DIR / ".tmp-lpbf-parity"  # ignored by /python/.tmp-*/
GOLDEN_SCHEMA = "lpbf-parity-golden-1"
FIXTURE_CAPTURE = REPO_ROOT / "tests" / "fixtures" / "lpbf-real-bare-plate-100W-capture.json"
FIXTURE_NPZ = REPO_ROOT / "tests" / "fixtures" / "lpbf-real-bare-plate-100W-section-fields.npz"
CORRIDOR_NPZ = "rectangular-corridor-section-fields.npz"
# Raw pre-hash values (drift-report context, never compared): collected by remember_raw()
# while execute() runs a case, up to RAW_VALUE_LIMIT characters of JSON per observation.
RAW_VALUE_LIMIT = 4096
_RAW_SINK: Optional[Dict[str, Any]] = None
LAST_RAW_VALUES: Dict[str, Any] = {}
# Artifact entries added by the worker (lpbf_worker.py), never by run() itself.
WORKER_ONLY_ARTIFACTS = ("capabilities.json", "input.json")

# V1 acceptance case, byte-exact inputJson of archived run 318937f610074c1b8d43ea93273b87eb
# (066b6b9 PHASE2 bundle; replayed for V1 as job 50a98fa4...). sha256 = fc8325d9...
V1_INPUT_JSON = (
    '{"absorptivity":0.38,"backend":"reference","barePlateGeometry":"square","beamDiameter_um":80,'
    '"convection_W_m2K":20,"cooling_s":0.0005,"dwell_s":0.0002,"emissivity":0.35,'
    '"evaporationModel":false,"hatch_um":80,"islandSize_um":200,"layerRotation_deg":67,'
    '"layer_um":20,"layers":1,"marangoniMultiplier":2.2,"material":"Inconel 718","maxDt_s":1e-06,'
    '"mesh_um":20,"mode":"standard","opticalObserver":null,"packingFraction":0.55,'
    '"powderConductivityRatio":0.12,"powderGridPolicy":"layer-conforming","power_W":60,'
    '"preheat_C":200,"scanAngle_deg":0,"sourcePenetration_um":null,"speed_mm_s":1200,'
    '"strategy":"stripe","stripeWidth_um":500,"study":"none","surfaceMode":"powder-layer",'
    '"timeout_s":300,"trackLength_um":600,"tracks":1}'
)
V1_INPUT_SHA256 = "fc8325d91b01ca02043cf0fa963396a58f6a4dab428559b63f732f46538db6da"
# strip_result() canonical digest of that archived run's resultJson (resultJson bytes sha256
# a9761a1a4464714ef2fbd4da1ceb54265d96e8f06ae511f14e55b2d0b7270ab9, worker run at 066b6b9,
# implementationHash 7482697c...). A direct run() at the pre-bump HEAD reproduces it exactly.
V1_ARCHIVED_RESULT_STRIPPED_SHA256 = "3eed50effcb82e8cffce55f2a24816cee37e634bb92aa4127be46f1c23a88f83"

# Small powder case shared with test_lpbf_engineering.CASE.
SMALL = dict(mode="standard", backend="reference", power_W=40, mesh_um=40, trackLength_um=200,
             cooling_s=.0001, dwell_s=0)
# Observer case shared with test_lpbf_fixed_event_time_history_observer.SMALL_CASE.
# P7b (2026-10-14): at the IN718 authority 0.32 this 60 W synthetic point no longer melts (peak 1596.6 K, liquidus
# 1609.15 K), so the peak-field, phase-slice and temperature-slice observers would never fire and G8 / G15 would stop
# exercising them. The case keeps the absorptivity it was recorded with (0.38, explicit, like LAYERED): the observer
# numerics stay bit equal and only the re-identified material digests drift (named exactly).
OBSERVER_CASE = {"mode": "standard", "backend": "reference", "material": "Inconel 718", "absorptivity": 0.38,
                 "power_W": 60, "speed_mm_s": 1200, "mesh_um": 40, "maxDt_s": 2e-7,
                 "layer_um": 80, "trackLength_um": 100, "cooling_s": 0, "dwell_s": 0}
# Layered-plate case shared with test_lpbf_layered_plate_solver.LAYERED.
# P7b (2026-10-14): the reference layered-plate replay carries its absorptivity explicitly (0.38, the value it was
# recorded with), as the archived G1 and G2 inputs do, so the reference numerics stay bit equal while the material
# authority (0.32 for Inconel 718) moves the default of every non-reference case; the material identity of the replay
# is re-identified by lpbf_material_registry.reidentify and drifts as a named identity observation.
LAYERED = dict(
    mode="standard", backend="reference", surfaceMode="bare-plate", absorptivity=0.38,
    barePlateGeometry="square", study="none", layers=1, tracks=1,
    scanAngle_deg=0, mesh_um=20, beamDiameter_um=20, trackLength_um=100,
    power_W=50, speed_mm_s=10000, maxDt_s=1e-5, sourcePenetration_um=20,
    thermalModelId="layered-plate-enthalpy-v1", plateThickness_um=20,
    supportThickness_um=20, contactResistance_m2K_W=1e-4,
    supportBottomBoundary="adiabatic", incidenceAngle_deg=10,
    incidenceAzimuth_deg=0,
    beamProfileModelId="assumed-oblique-gaussian-normal-plane-v1",
)


# --------------------------------------------------------------------------- digests

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_sha256(value: Any) -> str:
    """Design 2.1 comparison form: canonical JSON, sort_keys=True, allow_nan=False."""
    return sha256_bytes(json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8"))


def typed_tree(value: Any) -> Any:
    """Insertion-ordered, type-tagged tree: pins key order, int/float, tuple/list, float bits."""
    kind = type(value)
    if value is None:
        return None
    if kind is bool:
        return {"bool": value}
    if kind is int:
        return {"int": str(value)}
    if kind is float:
        return {"float": value.hex()}
    if kind is str:
        return {"str": value}
    if kind is dict:
        return {"dict": [[typed_tree(k), typed_tree(v)] for k, v in value.items()]}
    if kind is list:
        return {"list": [typed_tree(v) for v in value]}
    if kind is tuple:
        return {"tuple": [typed_tree(v) for v in value]}
    if isinstance(value, types.MappingProxyType):
        return {"mappingproxy": [[typed_tree(k), typed_tree(v)] for k, v in value.items()]}
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        return {"ndarray": [array.dtype.str, list(array.shape), sha256_bytes(array.tobytes())]}
    if isinstance(value, np.generic):
        return {"numpy-scalar": [value.dtype.str, value.tobytes().hex()]}
    if isinstance(value, (set, frozenset)):
        items = sorted((typed_tree(v) for v in value), key=lambda item: json.dumps(item, sort_keys=True))
        return {kind.__name__: items}
    tag = f"{kind.__module__}.{kind.__qualname__}"
    if isinstance(value, dict):
        return {tag: [[typed_tree(k), typed_tree(v)] for k, v in value.items()]}
    if isinstance(value, (list, tuple)):
        return {tag: [typed_tree(v) for v in value]}
    if isinstance(value, (int, float, str)):
        return {tag: repr(value)}
    raise TypeError(f"No typed parity encoding for {tag}")


def typed_sha256(value: Any) -> str:
    return sha256_bytes(json.dumps(typed_tree(value), separators=(",", ":"),
                                   ensure_ascii=True, allow_nan=False).encode("ascii"))


def error_text(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def capture_call(function: Callable[[], Any]) -> Tuple[str, Any]:
    """Return ("ok", value) or ("error", "Type: message"); errors are observations too."""
    try:
        return "ok", function()
    except Exception as exc:  # noqa: BLE001 - the error text itself is pinned
        return "error", error_text(exc)


def observe_value(observations: Dict[str, Any], key: str, function: Callable[[], Any]) -> None:
    status, value = capture_call(function)
    observations[key] = typed_sha256(value) if status == "ok" else {"error": value}
    if status == "ok":
        remember_raw(key, value)


def each(function: Callable[[Any], Any], items) -> List[Any]:
    """Per-item [status, value]: one out-of-range point must not hide the others."""
    return [list(capture_call(lambda item=item: function(item))) for item in items]


# --------------------------------------------------------------------------- result handling

def strip_result(result: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    """Remove the design-2.1 volatile and worker-only fields; return (stripped, implementationHash)."""
    stripped = copy.deepcopy(result)
    implementation = None
    provenance = stripped.get("provenance")
    if isinstance(provenance, dict):
        implementation = provenance.pop("implementationHash", None)
        for key in ("createdAt", "runtime_s", "executionRuntime"):
            provenance.pop(key, None)
    stripped.pop("runtime_s", None)
    stripped.pop("runKind", None)
    if isinstance(stripped.get("artifacts"), list):
        stripped["artifacts"] = [item for item in stripped["artifacts"]
                                 if not (isinstance(item, dict) and item.get("path") in WORKER_ONLY_ARTIFACTS)]
    return stripped, implementation


def npz_observations(path: Path, prefix: str) -> Dict[str, Any]:
    observations: Dict[str, Any] = {}
    with np.load(path, allow_pickle=False) as archive:
        observations[f"{prefix}.arrayNames"] = list(archive.files)
        for name in archive.files:
            array = np.ascontiguousarray(archive[name])
            observations[f"{prefix}.array.{name}"] = [array.dtype.str, list(array.shape),
                                                      sha256_bytes(array.tobytes())]
    return observations


def artifact_observations(artifact_dir: Path) -> Dict[str, Any]:
    observations: Dict[str, Any] = {}
    files = sorted(p for p in artifact_dir.rglob("*") if p.is_file())
    names = [p.relative_to(artifact_dir).as_posix() for p in files]
    observations["artifacts.files"] = [n for n in names if n not in WORKER_ONLY_ARTIFACTS]
    for path, name in zip(files, names):
        if name in WORKER_ONLY_ARTIFACTS:
            continue
        data = path.read_bytes()
        observations[f"artifact.{name}"] = [len(data), sha256_bytes(data)]
        if name.endswith(".npz"):
            observations.update(npz_observations(path, f"npz.{name}"))
    return observations


def result_observations(result: Dict[str, Any], artifact_dir: Optional[Path],
                        prefix: str = "result") -> Tuple[Dict[str, Any], Optional[str]]:
    stripped, implementation = strip_result(result)
    observations: Dict[str, Any] = {
        f"{prefix}.canonicalSha256": canonical_json_sha256(stripped),
        f"{prefix}.orderedTypedSha256": typed_sha256(stripped),
        f"{prefix}.topLevelKeys": list(stripped),
    }
    for key, value in stripped.items():
        observations[f"{prefix}.key.{key}"] = canonical_json_sha256(value)
        remember_raw(f"{prefix}.key.{key}", value)
    contract = stripped.get("coreContract")
    if isinstance(contract, dict):
        for key in ("inputSha256", "materialSha256", "solverId", "modelId"):
            if key in contract:
                observations[f"{prefix}.coreContract.{key}"] = contract[key]
    material = stripped.get("material")
    if isinstance(material, dict) and "materialRevisionSha256" in material:
        observations[f"{prefix}.material.materialRevisionSha256"] = material["materialRevisionSha256"]
    for key in ("validationStatus", "productionReady", "effectiveMode", "label", "confidence"):
        if key in stripped:
            observations[f"{prefix}.{key}"] = stripped[key]
    # The fingerprint must live only in provenance.implementationHash; if it were embedded
    # anywhere else the stripped digests would move at the bump for a non-numerical reason.
    if implementation:
        observations[f"{prefix}.implementationHashOccurrencesAfterStrip"] = json.dumps(
            stripped, allow_nan=False).count(implementation)
    if artifact_dir is not None:
        artifacts = artifact_observations(artifact_dir)
        observations.update({f"{prefix}.{k}" if prefix != "result" else k: v for k, v in artifacts.items()})
        listed = {item["path"]: item.get("sha256") for item in stripped.get("artifacts", [])
                  if isinstance(item, dict) and "path" in item}
        on_disk = {name: hashlib.sha256((artifact_dir / name).read_bytes()).hexdigest()
                   for name in listed if (artifact_dir / name).is_file()}
        observations[f"{prefix}.artifactsListedMatchDisk"] = (on_disk == listed)
        if implementation:
            needle = implementation.encode("ascii")
            observations[f"{prefix}.artifactsImplementationHashOccurrences"] = sum(
                path.read_bytes().count(needle) for path in artifact_dir.rglob("*") if path.is_file())
    return observations, implementation


# --------------------------------------------------------------------------- case context

class CaseSkipped(Exception):
    """A case that cannot be checked here; reported as SKIP with its reason, never as PASS."""


class CaseContext:
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.implementation_hashes: List[str] = []
        self.notes: List[str] = []

    def new_dir(self, name: str) -> Path:
        path = self.work_dir / name
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
        return path

    def run_case(self, raw: Dict[str, Any], *, artifacts: bool = False, prefix: str = "result",
                 **kwargs) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        from lpbf_simulation import run
        artifact_dir = self.new_dir(prefix.replace(".", "-")) if artifacts else None
        result = run(copy.deepcopy(raw), artifact_dir=artifact_dir, **kwargs)
        observations, implementation = result_observations(result, artifact_dir, prefix)
        if implementation is not None:
            self.implementation_hashes.append(implementation)
        return result, observations


# --------------------------------------------------------------------------- cases

def case_g1_v1_60w(ctx: CaseContext) -> Dict[str, Any]:
    if sha256_bytes(V1_INPUT_JSON.encode("utf-8")) != V1_INPUT_SHA256:
        raise AssertionError("embedded V1 inputJson no longer matches its archived sha256")
    _, observations = ctx.run_case(json.loads(V1_INPUT_JSON), artifacts=True)
    observations["v1Archive.strippedResultEqual"] = (
        observations["result.canonicalSha256"] == V1_ARCHIVED_RESULT_STRIPPED_SHA256)
    return observations


def _fixture() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    capture = json.loads(FIXTURE_CAPTURE.read_text(encoding="utf-8"))
    return capture, json.loads(capture["resultJson"])


# Top-level result labels added after the bare-plate fixture was captured. They carry no numerics:
# the Wave B LT-3 solidificationResolution label only counts cells across the already pinned melt pool.
# The fixture comparison drops ONLY these names and only when the fixture lacks them, so every key the
# fixture has is still compared bit-exact; the label itself is pinned by result.key.<name> in the golden.
FIXTURE_POST_CAPTURE_LABEL_KEYS = ("solidificationResolution",)


MATERIAL_IDENTITY_KEYS = ("materialRevisionSha256", "materialAuthorityRevisionSha256")


def _without_material_identity(stripped: Dict[str, Any]) -> Dict[str, Any]:
    """The stripped result minus the material identity digests (the material's own numbers stay)."""
    out = copy.deepcopy(stripped)
    material = out.get("material")
    if isinstance(material, dict):
        for key in MATERIAL_IDENTITY_KEYS:
            material.pop(key, None)
    contract = out.get("coreContract")
    if isinstance(contract, dict):
        contract.pop("materialSha256", None)
    return out


def case_g2_bare_plate_fixture(ctx: CaseContext) -> Dict[str, Any]:
    """Real bare-plate 100 W corridor job 7ec9dc57...: rerun and compare with the in-repo fixture."""
    capture, reference = _fixture()
    result, observations = ctx.run_case(json.loads(capture["inputJson"]), artifacts=True)
    artifact_dir = ctx.work_dir / "result"
    run_stripped, _ = strip_result(result)
    reference_stripped, reference_hash = strip_result(reference)
    for key in FIXTURE_POST_CAPTURE_LABEL_KEYS:
        if key not in reference_stripped:
            run_stripped.pop(key, None)
    observations["fixture.strippedResultEqual"] = (
        canonical_json_sha256(run_stripped) == canonical_json_sha256(reference_stripped))
    # P7b (2026-10-14): the material authority moved, so the capture's material identity (materialRevisionSha256,
    # materialAuthorityRevisionSha256, coreContract.materialSha256) can no longer equal a rerun's. This observation
    # compares everything else bit-exact (the physics numerics of the replay; the capture's explicit absorptivity 0.38
    # is still what the rerun uses) so the replay claim survives an identity move that is named exactly.
    observations["fixture.strippedResultEqualExceptMaterialIdentity"] = (
        canonical_json_sha256(_without_material_identity(run_stripped))
        == canonical_json_sha256(_without_material_identity(reference_stripped)))
    # No ordered/typed comparison with the fixture: the worker passed the original request
    # dict, whose key order (not the implementation) sets the order of extra settings keys,
    # and the fixture went through JSON (tuples become lists). Canonical equality is the
    # design-2.1 criterion; the ordered/typed digest of this direct run is pinned above.
    observations["fixture.recordedImplementationHash"] = reference_hash
    compared, mismatched = 0, []
    for item in reference.get("artifacts", []):
        name = item["path"]
        if name in WORKER_ONLY_ARTIFACTS:
            continue
        compared += 1
        path = artifact_dir / name
        if not path.is_file() or sha256_bytes(path.read_bytes()) != item["sha256"]:
            mismatched.append(name)
    observations["fixture.artifactsCompared"] = compared
    observations["fixture.artifactsMismatched"] = mismatched
    observations["fixture.fieldArtifactsCompared"] = sum(
        1 for item in reference.get("artifacts", [])
        if item["path"] not in WORKER_ONLY_ARTIFACTS and item["path"] != CORRIDOR_NPZ)
    observations["fixture.npzBytesEqual"] = (
        (artifact_dir / CORRIDOR_NPZ).read_bytes() == FIXTURE_NPZ.read_bytes())
    observations["fixture.inputSha256Equal"] = (
        result["coreContract"]["inputSha256"] == reference["coreContract"]["inputSha256"])
    observations["fixture.materialSha256Equal"] = (
        result["coreContract"]["materialSha256"] == reference["coreContract"]["materialSha256"])
    return observations


def case_g3_powder_stripe_multilayer(ctx: CaseContext) -> Dict[str, Any]:
    raw = {**SMALL, "strategy": "stripe", "tracks": 2, "layers": 2, "stripeWidth_um": 100,
           "dwell_s": 2e-5, "scanAngle_deg": 35, "layerRotation_deg": 67}
    _, observations = ctx.run_case(raw, artifacts=True)
    return observations


def case_g3_powder_island(ctx: CaseContext) -> Dict[str, Any]:
    raw = {**SMALL, "strategy": "island", "islandSize_um": 100, "tracks": 2, "layers": 1,
           "dwell_s": 1e-5}
    _, observations = ctx.run_case(raw)
    return observations


def case_g4_layered_plate(ctx: CaseContext) -> Dict[str, Any]:
    _, observations = ctx.run_case(LAYERED, artifacts=True)
    return observations


def case_g5_evaporation(ctx: CaseContext) -> Dict[str, Any]:
    _, observations = ctx.run_case({**SMALL, "power_W": 80, "evaporationModel": True}, artifacts=True)
    # Proof that the opt-in path is exercised: the same case without it must differ.
    # At 80 W the baseline stops at the boiling validity limit (fail closed); that error text
    # is pinned too, so this case also covers the boiling STOP message.
    status, baseline = capture_call(lambda: ctx.run_case(
        {**SMALL, "power_W": 80, "evaporationModel": False}, prefix="baseline")[1])
    observations["baseline"] = (baseline["baseline.canonicalSha256"] if status == "ok"
                                else {"error": baseline})
    observations["evaporation.differsFromBaseline"] = (
        status != "ok" or observations["result.canonicalSha256"] != baseline["baseline.canonicalSha256"])
    return observations


def case_g6_screening_and_fallback(ctx: CaseContext) -> Dict[str, Any]:
    observations: Dict[str, Any] = {}
    for prefix, raw in (("screening", {"mode": "screening"}),
                        ("highFidelityFallback", {"mode": "high-fidelity"}),
                        ("screeningTi64", {"mode": "screening", "material": "Ti-6Al-4V",
                                           "power_W": 180, "speed_mm_s": 900})):
        _, part = ctx.run_case(raw, prefix=prefix)
        observations.update(part)
    # The fallback reason differs when the worker reports an installed OpenFOAM.
    _, part = ctx.run_case({"mode": "high-fidelity"}, prefix="highFidelityFallbackWithOpenfoam",
                           capabilities={"openfoamVersion": "14", "openfoamThermal": False})
    observations.update(part)
    return observations


def case_g7_mesh_study(ctx: CaseContext) -> Dict[str, Any]:
    _, observations = ctx.run_case({**SMALL, "power_W": 10, "study": "mesh"}, artifacts=True)
    return observations


def case_g7_timestep_study(ctx: CaseContext) -> Dict[str, Any]:
    """study='timestep': the legacy 2x / sqrt(2)x maxDt protocol."""
    _, observations = ctx.run_case({**SMALL, "power_W": 10, "study": "timestep"})
    return observations


def case_g3_powder_meander_unidirectional(ctx: CaseContext) -> Dict[str, Any]:
    observations: Dict[str, Any] = {}
    for prefix, strategy in (("meander", "meander"), ("unidirectional", "unidirectional")):
        _, part = ctx.run_case({**SMALL, "strategy": strategy, "tracks": 2, "hatch_um": 80,
                                "dwell_s": 1e-5}, prefix=prefix)
        observations.update(part)
    return observations


def case_g14_calibration_measurements(ctx: CaseContext) -> Dict[str, Any]:
    """mode='calibration' with a matched and an unmatched (process vector) measurement."""
    from lpbf_simulation import validate
    from lpbf_evidence import PROCESS_KEYS
    raw = {**SMALL, "mode": "calibration"}
    row = dict(width_um=50., depth_um=45., source="Synthetic parity fixture (not a measurement)")
    p, _ = validate({**raw, "measurements": [row]})
    matched = dict(row, processVector={k: p[k] for k in PROCESS_KEYS},
                   uncertainty_um=dict(width_um=2., depth_um=3.), independentHoldout=False)
    observations: Dict[str, Any] = {}
    for prefix, rows in (("matched", [matched]), ("unmatched", [row])):
        _, part = ctx.run_case({**raw, "measurements": rows}, prefix=prefix)
        observations.update(part)
    status, value = capture_call(lambda: ctx.run_case({**raw, "mode": "calibration"}))
    observations["reject.calibrationWithoutMeasurements"] = value if status == "error" else "NO-ERROR"
    return observations


def case_g15_bare_plate_square_optical_observer(ctx: CaseContext) -> Dict[str, Any]:
    """Square bare plate (G2 is the corridor) with a non-null opticalObserver setting."""
    # P7b (2026-10-14): explicit absorptivity 0.38 (the recorded value) so the 60 W plate still melts and the optical
    # observer artifacts stay exercised at the IN718 authority 0.32 (see OBSERVER_CASE); identity digests drift, named.
    raw = {"mode": "standard", "backend": "reference", "surfaceMode": "bare-plate", "absorptivity": 0.38,
           "barePlateGeometry": "square", "sourcePenetration_um": 40, "power_W": 60,
           "mesh_um": 40, "trackLength_um": 200, "cooling_s": 1e-4, "dwell_s": 0,
           "opticalObserver": "nist-six-section"}
    _, observations = ctx.run_case(raw, artifacts=True)
    return observations


def case_g16_non_in718_transient(ctx: CaseContext) -> Dict[str, Any]:
    observations: Dict[str, Any] = {}
    for prefix, name in (("ti6al4v", "Ti-6Al-4V"), ("ss316l", "316L Stainless Steel"),
                         ("alsi10mg", "AlSi10Mg")):
        status, value = capture_call(lambda name=name, prefix=prefix: ctx.run_case(
            {**SMALL, "material": name}, prefix=prefix)[1])
        if status == "ok":
            observations.update(value)
        else:
            observations[f"{prefix}.error"] = value
    return observations


def value_hex(value: Any) -> Any:
    """Value-level observation: floats as [value, float.hex()] so a drift report shows both."""
    if type(value) is float:
        return [value, value.hex()]
    return value


# Non-IN718 evaporationModel=True cases (B5 step 2). They document TODAY's behaviour so the
# corrected-physics bump has measurable drift: lpbf_simulation passes
# m.get("latent_heat_vap_J_kg", 6.4e6) to the enthalpy inversion, and material() never
# carries that key, so every alloy uses IN718's 6.4e6 J/kg (FABLE-B5-OPINION D1).
# All three use the default Marangoni multiplier (2.2) and speed. AlSi10Mg needs 500 W to
# reach its boiling enthalpy on the SMALL grid (400 W: no inversion call; 600 W saturates the
# vapour fraction at 1.0 for both L_v values, 500 W does not, so its maxVaporFraction stays
# sensitive to L_v).
EVAPORATION_CASES = {
    "ti6al4v": ("Ti-6Al-4V", {**SMALL, "material": "Ti-6Al-4V", "power_W": 80, "evaporationModel": True}),
    # P7b gate (2026-10-14): the 316L case keeps the absorptivity it was recorded with (0.42, explicit, like G8 and
    # G15) so the inversion and its L_v 6.25e6 stay exercised at the authority 0.30 (at 0.30 the 80 W case no
    # longer boils); the request re-identifies the material, so its identity digests drift, named exactly.
    "ss316l": ("316L Stainless Steel", {**SMALL, "material": "316L Stainless Steel", "power_W": 80,
                                         "absorptivity": 0.42, "evaporationModel": True}),
    "alsi10mg": ("AlSi10Mg", {**SMALL, "material": "AlSi10Mg", "power_W": 500, "evaporationModel": True}),
}


def _recorded_evaporation_run(ctx: CaseContext, raw: Dict[str, Any], prefix: str,
                              substitute_latent_heat_vap: Optional[float] = None):
    """Run with the boiling-cap inversion wrapped: record the L_v it receives, change nothing
    (or, with substitute_latent_heat_vap, pass that value instead: a harness-side probe).

    The wrapper knows today's call shape (L_v as 5th positional or latent_heat_vap_j_kg
    keyword). Any other shape is recorded as a readable note, so a changed call drifts these
    observations instead of aborting the whole --check run; the bump that changes the call
    must update this wrapper in the same branch."""
    import lpbf_evaporation_marangoni as evaporation
    calls: List[Tuple[Any, Any]] = []
    original = evaporation.invert_enthalpy_with_boiling_cap
    keyword = "latent_heat_vap_j_kg"

    def recording(*args, **kwargs):
        args = list(args)
        known = len(args) > 4 or keyword in kwargs
        if substitute_latent_heat_vap is not None and known:
            if len(args) > 4:
                args[4] = substitute_latent_heat_vap
            else:
                kwargs[keyword] = substitute_latent_heat_vap
        result = original(*args, **kwargs)
        if not known:
            used: Any = (f"unrecognised call shape: {len(args)} positional, "
                         f"keywords {sorted(kwargs)}")
        else:
            used = float(args[4] if len(args) > 4 else kwargs[keyword])
        try:
            temperature, vapor_fraction = result
            fraction: Any = float(np.max(vapor_fraction))
        except (TypeError, ValueError):
            fraction = f"unrecognised return shape: {type(result).__name__}"
        calls.append((used, fraction))
        return result

    evaporation.invert_enthalpy_with_boiling_cap = recording
    try:
        _, observations = ctx.run_case(raw, artifacts=True, prefix=prefix)
    finally:
        evaporation.invert_enthalpy_with_boiling_cap = original
    return observations, calls


def _distinct(values) -> List[Any]:
    """Distinct values, floats first (sorted, as [value, hex]), then notes (sorted text)."""
    values = set(values)
    floats = sorted(v for v in values if type(v) is float)
    return [value_hex(v) for v in floats] + sorted(str(v) for v in values if type(v) is not float)


def _maximum(values) -> Any:
    values = list(values)
    floats = [v for v in values if type(v) is float]
    if len(floats) != len(values):
        return sorted({str(v) for v in values if type(v) is not float})
    return value_hex(max(floats, default=None))


def _evaporation_case(ctx: CaseContext, key: str) -> Dict[str, Any]:
    import four_alloy_materials as fam
    import lpbf_material_registry as registry
    name, raw = EVAPORATION_CASES[key]
    observations, calls = _recorded_evaporation_run(ctx, raw, "result")
    authority = fam.thermal_props(name)["latent_heat_vap_J_kg"]
    observations["evaporation.inversionCalls"] = len(calls)
    observations["evaporation.latentHeatVapUsed_J_kg"] = _distinct(c[0] for c in calls)
    observations["evaporation.maxVaporFraction"] = _maximum(c[1] for c in calls)
    observations["evaporation.authorityLatentHeatVap_J_kg"] = value_hex(float(authority))
    observations["evaporation.materialSnapshotHasLatentHeatVap"] = "latent_heat_vap_J_kg" in registry.material(name)
    # Harness-side probe (no implementation change): the same run with the authority L_v
    # substituted. Equal digests mean today's result does not depend on L_v (the inversion's
    # vapour fraction is discarded); the corrected bump may legitimately change that.
    probe, probe_calls = _recorded_evaporation_run(ctx, raw, "authorityLatentHeatVap",
                                                   substitute_latent_heat_vap=float(authority))
    observations["evaporation.authorityProbe.latentHeatVapUsed_J_kg"] = _distinct(c[0] for c in probe_calls)
    observations["evaporation.authorityProbe.maxVaporFraction"] = _maximum(c[1] for c in probe_calls)
    observations["evaporation.authorityProbe.resultCanonicalEqual"] = (
        probe["authorityLatentHeatVap.canonicalSha256"] == observations["result.canonicalSha256"])
    observations["evaporation.authorityProbe.artifactsEqual"] = all(
        probe.get(f"authorityLatentHeatVap.{k}") == v for k, v in observations.items()
        if k.startswith(("artifact.", "npz.")))
    return observations


def case_g17_evaporation_ti6al4v(ctx: CaseContext) -> Dict[str, Any]:
    return _evaporation_case(ctx, "ti6al4v")


def case_g17_evaporation_316l(ctx: CaseContext) -> Dict[str, Any]:
    return _evaporation_case(ctx, "ss316l")


def case_g17_evaporation_alsi10mg(ctx: CaseContext) -> Dict[str, Any]:
    return _evaporation_case(ctx, "alsi10mg")


IN625_MELTPOOL_PAYLOAD = dict(material_name="Inconel 625", laser_power_W=200.0, scan_speed_mm_s=800.0,
                              beam_diameter_um=80.0, preheat_temp_C=80.0, layer_thickness_um=40.0,
                              hatch_spacing_um=100.0, heat_source="rosenthal")
# The three IN625 fusion latent heats in the code base (FABLE-B5-OPINION D5): 227 kJ/kg
# (Mills, transient specification), 260 kJ/kg (lpbf_thermal_solver secondary table,
# Rosenthal melt-pool path), 290 kJ/kg (Sabau, bounded thermal screening snapshot).
IN625_LATENT_HEAT_CANDIDATES = (227000.0, 260000.0, 290000.0)


def _meltpool_geometry_um(value: Dict[str, Any]) -> List[Any]:
    """[width, depth, length, keyhole vapour cavity depth] in um of a calculate_meltpool_physics result."""
    geometry = value["meltPoolGeometry"]
    return [geometry[key] for key in ("width_um", "depth_um", "length_um", "keyholeVaporCavityDepth_um")]


# Since the 2026-10-06 tier-2 bump calculate_meltpool_physics touches the GPU modules only on explicit
# request (absorption_model="powder-raytrace" or thermal_slice_backend="warp"); no G11/G18 payload makes
# that request, so their results no longer depend on whether warp is importable. G11/G18 used to be
# skipped on warp hosts; they now run everywhere with the two GPU modules blocked, so a silent GPU
# path would raise ImportError (a FAIL) instead of drifting or being skipped.
_GPU_MELTPOOL_MODULES = ("powder_bed_raytracer", "warp_thermal_solver")
_GPU_MELTPOOL_OPTIONS = ("absorption_model", "thermal_slice_backend")


def _cpu_meltpool_only(observe):
    """Run observe() with the GPU melt-pool modules made unimportable (see _GPU_MELTPOOL_MODULES)."""
    import sys
    from unittest import mock
    with mock.patch.dict(sys.modules, {name: None for name in _GPU_MELTPOOL_MODULES}):
        return observe()


def _require_cpu_meltpool_payloads(payloads) -> None:
    for payload in payloads:
        requested = sorted(set(payload) & set(_GPU_MELTPOOL_OPTIONS))
        if requested:
            raise ValueError(f"G11/G18 payloads must not request the GPU melt-pool path: {requested}")


def case_g18_in625_latent_heat(ctx: CaseContext) -> Dict[str, Any]:
    """Which IN625 fusion latent heat each path uses today (value level)."""
    _require_cpu_meltpool_payloads([IN625_MELTPOOL_PAYLOAD])
    return _cpu_meltpool_only(lambda: _g18_observations(ctx))


def _g18_observations(ctx: CaseContext) -> Dict[str, Any]:
    import lpbf_material_registry as registry
    import in625_thermal_material as in625
    from lpbf_thermal_solver import calculate_meltpool_physics, SECONDARY_THERMOPHYSICAL_DB
    from four_alloy_materials import resolve_alloy_id

    observations: Dict[str, Any] = {}
    status, plain = capture_call(lambda: calculate_meltpool_physics(**IN625_MELTPOOL_PAYLOAD))
    observations["meltpool.in625"] = typed_sha256(plain) if status == "ok" else {"error": plain}
    if status == "ok":
        remember_raw("meltpool.in625", plain)
    if status == "ok":
        observations["meltpool.in625.materialEvidence"] = plain.get("materialEvidence")
        # Small companion of the digest above (its raw value exceeds RAW_VALUE_LIMIT), so a
        # drift report carries raw before/after melt-pool dimensions (review pb-r2 S2).
        observe_value(observations, "meltpool.in625.geometry_um", lambda: _meltpool_geometry_um(plain))
    # prop_overrides merge onto the resolved table: the result is bit-equal to the plain run
    # exactly for the latent heat the path already uses, and differs for the others.
    for value in IN625_LATENT_HEAT_CANDIDATES:
        status_o, overridden = capture_call(lambda value=value: calculate_meltpool_physics(
            **IN625_MELTPOOL_PAYLOAD, prop_overrides={"latent_heat_fusion_J_kg": value}))
        observations[f"meltpool.in625.equalWithLatentHeatFusion.{value:.0f}"] = (
            typed_sha256(overridden) == observations["meltpool.in625"] if status_o == "ok"
            else {"error": overridden})
    table = SECONDARY_THERMOPHYSICAL_DB["Inconel 625"]
    observations["meltpool.in625.table.latent_heat_fusion_J_kg"] = value_hex(table["latent_heat_fusion_J_kg"])
    observations["meltpool.in625.table.latent_heat_vap_J_kg"] = value_hex(table["latent_heat_vap_J_kg"])
    status_b, value_b = capture_call(lambda: resolve_alloy_id("Inconel 625"))
    observations["buildJob.resolveAlloyId.Inconel 625"] = value_b if status_b == "ok" else {"error": value_b}
    for name in ("Inconel 625", "IN625"):
        status_s, screening = capture_call(lambda name=name: registry.thermal_screening_material(name))
        observations[f"thermalScreening.{name}.latentHeat_J_kg"] = (
            value_hex(screening["latentHeat_J_kg"]) if status_s == "ok" else {"error": screening})
    observations["in625.snapshot.latentHeat_J_kg"] = value_hex(in625.in625_lpbf_thermal_snapshot()["latentHeat_J_kg"])
    observations["in625.transientSpecification.latentHeat_J_kg"] = value_hex(
        in625.in625_transient_material_specification()["latentHeat_J_kg"])
    status_r, value_r = capture_call(lambda: registry.material("Inconel 625"))
    observations["registry.material.Inconel 625"] = (
        value_hex(value_r.get("latentHeat_J_kg")) if status_r == "ok" else {"error": value_r})
    return observations


def case_g19_emissivity_echo(ctx: CaseContext) -> Dict[str, Any]:
    """Emissivity: one registry literal (0.35) for every alloy, echoed into p and used in the
    top-surface radiation term (lpbf_simulation reference transient); FABLE-B5-OPINION D6."""
    import lpbf_material_registry as registry
    from lpbf_simulation import validate

    observations: Dict[str, Any] = {}
    names = [item["name"] for item in registry.catalog()]
    for name in names:
        status, value = capture_call(lambda name=name: registry.material(name)["emissivity"])
        observations[f"registry.material.{name}.emissivity"] = value_hex(value) if status == "ok" else {"error": value}
        status, value = capture_call(lambda name=name: validate({"mode": "standard", "material": name}))
        observations[f"validate.{name}.emissivity"] = (
            [value_hex(value[0]["emissivity"]), value_hex(value[1]["emissivity"])] if status == "ok"
            else {"error": value})
    for override in (0.35, 0.5, 0, 1, 1.5, True):
        status, value = capture_call(lambda override=override: validate(
            {"mode": "standard", "material": "Inconel 718", "emissivity": override}))
        observations[f"validate.override.{override!r}.emissivity"] = (
            [value_hex(value[0]["emissivity"]), value_hex(value[1]["emissivity"])] if status == "ok"
            else {"error": value})
    _, implicit = ctx.run_case(SMALL, prefix="implicit")
    observations.update(implicit)
    _, explicit = ctx.run_case({**SMALL, "emissivity": 0.35}, prefix="explicit")
    observations["explicit0.35.canonicalEqualsImplicit"] = (
        explicit["explicit.canonicalSha256"] == implicit["implicit.canonicalSha256"])
    # Explicit overrides are accepted, become part of the material identity, and change the run digest.
    override = 0.36
    status, value = capture_call(lambda: ctx.run_case({**SMALL, "emissivity": override}, prefix="override")[1])
    observations[f"run.override{override!r}"] = (value["override.canonicalSha256"] if status == "ok"
                                                 else {"error": value})
    return observations


def case_g13_source_quadrature_refinement(ctx: CaseContext) -> Dict[str, Any]:
    """Direct integrated_source calls with long intervals: the N-vs-2N refinement branch.

    The CPU scheduler keeps beam travel per accepted step <= 0.25 radius, so no transient
    case reaches this branch; it is still the shared source integral (GPU pilots use the
    same tolerance), and B commits must not change it.
    """
    import lpbf_core_physics as core
    observations: Dict[str, Any] = {}
    dx = 20e-6
    axis = (np.arange(64) + .5) * dx - 32 * dx
    z = -(np.arange(6) + .5) * dx
    segment = {"start_s": 0.0, "end_s": 1.25e-3, "start": [-500e-6, 0.0], "end": [500e-6, 0.0],
               "layer": 0, "track": 0, "island": None}
    original_rule = core.source_gauss_rule
    for dt in (1.25e-4, 2.5e-4, 5e-4, 1e-3, 1.25e-3):
        orders: List[int] = []

        def rule(order, orders=orders):
            orders.append(order)
            return original_rule(order)
        core.source_gauss_rule = rule
        try:
            status, value = capture_call(lambda dt=dt: core.integrated_source(
                axis, z, dx, segment, 0.0, dt, 0.0, 40e-6, 40e-6, 100.0))
        finally:
            core.source_gauss_rule = original_rule
        key = f"integratedSource.dt{dt:.3e}"
        observe_value(observations, f"{key}.quadrature",
                      lambda dt=dt: core.source_time_quadrature(segment, dt, 40e-6))
        observations[f"{key}.orders"] = orders
        observations[key] = typed_sha256(value) if status == "ok" else {"error": value}
        if status == "ok":
            remember_raw(key, value)
    observations["integratedSource.refinementReached"] = any(
        len(v) > 1 for k, v in observations.items() if k.endswith(".orders"))
    return observations


def _observer_rejections() -> Dict[str, Any]:
    from lpbf_simulation import run, validate, scan_segments
    from lpbf_run_progress import CpuRunProgress

    def sink(_payload):
        return None

    p, _ = validate(OBSERVER_CASE)
    event = scan_segments(p)[0][0]["end_s"]
    bare = {"mode": "standard", "backend": "reference", "surfaceMode": "bare-plate",
            "sourcePenetration_um": 40, "mesh_um": 40, "trackLength_um": 100}
    attempts = {
        "finalState.screening": lambda: run({"mode": "screening"}, final_state_observer=sink),
        "finalState.meshStudy": lambda: run({**OBSERVER_CASE, "study": "mesh"}, final_state_observer=sink),
        "finalState.barePlate": lambda: run(bare, final_state_observer=sink),
        "finalState.layered": lambda: run(LAYERED, final_state_observer=sink),
        "finalState.notCallable": lambda: run(OBSERVER_CASE, final_state_observer=123),
        "finalStateBeforeSelectedTime.screening": lambda: run(
            {"mode": "screening"}, final_state_observer=sink, selected_time_observer=sink,
            selected_time_s=event),
        "selectedTime.barePlate": lambda: run(bare, selected_time_observer=sink, selected_time_s=event),
        "selectedTime.notEvent": lambda: run(OBSERVER_CASE, selected_time_observer=sink,
                                             selected_time_s=event * 0.5),
        "selectedTime.withoutObserver": lambda: run(OBSERVER_CASE, selected_time_s=event),
        "selectedTime.notCallable": lambda: run(OBSERVER_CASE, selected_time_observer="x",
                                                selected_time_s=event),
        "localHistory.screening": lambda: run({"mode": "screening"}, local_history_observer=sink,
                                              local_history_indices_ijk=[(0, 0, 0)]),
        "localHistory.indicesWithoutObserver": lambda: run(OBSERVER_CASE,
                                                           local_history_indices_ijk=[(0, 0, 0)]),
        "localHistory.missingIndices": lambda: run(OBSERVER_CASE, local_history_observer=sink),
        "localHistory.duplicateIndices": lambda: run(OBSERVER_CASE, local_history_observer=sink,
                                                     local_history_indices_ijk=[(0, 0, 0), (0, 0, 0)]),
        "localHistory.badTriple": lambda: run(OBSERVER_CASE, local_history_observer=sink,
                                              local_history_indices_ijk=[(0, 0)]),
        "runProgress.screening": lambda: run({"mode": "screening"}, run_progress=CpuRunProgress()),
        "runProgress.openfoam": lambda: run({**OBSERVER_CASE, "backend": "openfoam-thermal"},
                                            run_progress=CpuRunProgress()),
        "runProgress.meshStudy": lambda: run({**OBSERVER_CASE, "study": "mesh"},
                                             run_progress=CpuRunProgress()),
        "validate.cfdBackend": lambda: run({"backend": "openfoam-cfd"}),
        "validate.unknownField": lambda: run({"notAField": 1}),
    }
    observations: Dict[str, Any] = {}
    for label, attempt in attempts.items():
        status, value = capture_call(attempt)
        observations[f"reject.{label}"] = value if status == "error" else "NO-ERROR"
    return observations


def case_g8_observers(ctx: CaseContext) -> Dict[str, Any]:
    from lpbf_simulation import validate, scan_segments
    from lpbf_run_progress import CpuRunProgress

    p, _ = validate(OBSERVER_CASE)
    event = scan_segments(p)[0][0]["end_s"]
    final_states: List[Any] = []
    selected: List[Any] = []
    history_digest = hashlib.sha256()
    history_count = [0]
    progress_digest = hashlib.sha256()
    progress_count = [0]

    def history(record):
        history_count[0] += 1
        history_digest.update(typed_sha256(record).encode("ascii"))

    def progress(snapshot):
        progress_count[0] += 1
        progress_digest.update(typed_sha256(snapshot).encode("ascii"))

    tracker = CpuRunProgress(observer=progress)
    _, observations = ctx.run_case(
        OBSERVER_CASE, artifacts=True, final_state_observer=final_states.append,
        selected_time_observer=selected.append, selected_time_s=event,
        local_history_observer=history, local_history_indices_ijk=[(0, 0, 0), (1, 0, 1)],
        run_progress=tracker)
    observations["observer.finalState.count"] = len(final_states)
    observations["observer.finalState.typedSha256"] = [typed_sha256(item) for item in final_states]
    observations["observer.selectedTime.count"] = len(selected)
    observations["observer.selectedTime.typedSha256"] = [typed_sha256(item) for item in selected]
    observations["observer.localHistory.count"] = history_count[0]
    observations["observer.localHistory.chainSha256"] = history_digest.hexdigest()
    observations["observer.runProgress.count"] = progress_count[0]
    observations["observer.runProgress.chainSha256"] = progress_digest.hexdigest()
    observations["observer.runProgress.finalSnapshot"] = typed_sha256(tracker.snapshot())
    # Plain run of the same case: observers must not change the result.
    _, plain = ctx.run_case(OBSERVER_CASE, prefix="plain")
    observations["plain.canonicalSha256"] = plain["plain.canonicalSha256"]
    # The plain run's analytical-comparison digest (its raw value is small, so remember_raw
    # keeps it): the one block that moves under the corrected-physics bump (review pb-r2 S2).
    observations["plain.key.analyticalComparison"] = plain["plain.key.analyticalComparison"]
    observations.update(_observer_rejections())
    return observations


def case_g9_material_snapshots(ctx: CaseContext) -> Dict[str, Any]:
    import four_alloy_materials as fam
    import lpbf_material_registry as registry
    import in625_thermal_material as in625
    import in625_gpu_thermal_material as in625_gpu
    import lpbf_ss304_support_material as ss304
    from lpbf_core_physics import enthalpy_table, property_at

    observations: Dict[str, Any] = {}
    names = [item["name"] for item in registry.catalog()]
    observe_value(observations, "registry.catalog", registry.catalog)
    observations["registry.VERSION"] = registry.VERSION
    for name in names + ["IN625", "inconel 718", "ti64", "Unobtainium"]:
        observe_value(observations, f"registry.material.{name}", lambda name=name: registry.material(name))
        status, value = capture_call(lambda name=name: registry.material(name))
        if status == "ok":
            observations[f"registry.material.{name}.json"] = sha256_bytes(
                json.dumps(value, allow_nan=False).encode("utf-8"))
            if "materialRevisionSha256" in value:
                observations[f"registry.material.{name}.materialRevisionSha256"] = value["materialRevisionSha256"]
            observe_value(observations, f"core.enthalpyTable.{name}", lambda value=value: enthalpy_table(value))
            grid = np.linspace(250.0, 3600.0, 61)
            for column in (1, 2, 3, 4):
                observe_value(observations, f"core.propertyAt.{name}.{column}",
                              lambda value=value, column=column: property_at(value, grid, column))
    for name in ("Inconel 625", "IN625"):
        observe_value(observations, f"registry.thermalScreeningMaterial.{name}",
                      lambda name=name: registry.thermal_screening_material(name))
        observe_value(observations, f"registry.thermalScreeningAt.{name}",
                      lambda name=name: [registry.thermal_screening_at(name, t) for t in (300.0, 1000.0, 1600.0)])
    for constant in ("FOUR_ALLOY_IDS", "MATERIAL_AUTHORITY", "MATERIAL_AUTHORITY_SCHEMA_VERSION",
                     "THERMAL_NAME", "SLICER_NAME", "ALLOY_MATERIALS", "LITERATURE_PV_WINDOWS",
                     "LITERATURE_MELT_POOL_CASES", "FOUR_ALLOY_U95_BUDGET"):
        observe_value(observations, f"fam.{constant}", lambda constant=constant: getattr(fam, constant))
    observe_value(observations, "fam.four_alloy_thermophysical_db", fam.four_alloy_thermophysical_db)
    observations["fam.four_alloy_thermophysical_db.json"] = sha256_bytes(
        json.dumps(fam.four_alloy_thermophysical_db(), allow_nan=False).encode("utf-8"))
    probe_names = sorted({*fam.FOUR_ALLOY_IDS, *fam.THERMAL_NAME.values(), *fam.SLICER_NAME.values(),
                          "Ti64", "316L", "Inconel 625", "unknown-alloy"})
    for name in probe_names:
        observe_value(observations, f"fam.resolve_alloy_id.{name}", lambda name=name: fam.resolve_alloy_id(name))
        for function in ("thermal_props", "slicer_props", "marangoni_props", "inherent_strain_props"):
            observe_value(observations, f"fam.{function}.{name}",
                          lambda name=name, function=function: getattr(fam, function)(name))
        observe_value(observations, f"fam.canonical_material_source.{name}",
                      lambda name=name: fam.canonical_material_source(name))
    for alloy in fam.FOUR_ALLOY_IDS:
        observations[f"fam.canonical_material_source.{alloy}.sha256"] = fam.canonical_material_source(alloy)[1]
        for prop in ("rho", "cp", "k", "latent", "viscosity", "unknown"):
            observe_value(observations, f"fam.u95.{alloy}.{prop}",
                          lambda alloy=alloy, prop=prop: each(
                              lambda t: fam.four_alloy_u95_at_temperature(alloy, prop, t),
                              (300.0, 900.0, 1500.0, 1600.0, 1700.0, 1950.0, 2500.0)))
        observe_value(observations, f"fam.evaluate_literature_pv.{alloy}",
                      lambda alloy=alloy: [fam.evaluate_literature_pv(alloy, power, speed)
                                           for power in (100.0, 150, 200.0, 300, 400.0)
                                           for speed in (500, 800.0, 1000, 1500.0)])
    observe_value(observations, "fam.evaluate_literature_pv.unknownDefaultsToIn718",
                  lambda: fam.evaluate_literature_pv("unknown", 200, 800))
    observe_value(observations, "fam.regime_family",
                  lambda: [fam.regime_family(r) for r in ("Keyhole", "transition", "conduction", None, 3)])
    observe_value(observations, "in625.snapshot", in625.in625_lpbf_thermal_snapshot)
    observations["in625.snapshot.materialRevisionSha256"] = in625.in625_lpbf_thermal_snapshot().get(
        "materialRevisionSha256")
    observe_value(observations, "in625.transientSpecification", in625.in625_transient_material_specification)
    observe_value(observations, "in625.validateScreeningAdmission", in625.validate_in625_screening_admission)
    observe_value(observations, "in625.solidAtCelsius",
                  lambda: [in625.in625_solid_thermal_at_celsius(t) for t in (-18.0, 20.0, 500.0, 982.0)])
    for function in ("in625_lpbf_thermal_at_kelvin", "in625_extended_thermal_at_kelvin"):
        observe_value(observations, f"in625.{function}",
                      lambda function=function: each(getattr(in625, function),
                                                     (300.0, 900.0, 1563.15, 1590.0, 1623.15, 2500.0)))
    observe_value(observations, "in625.U95_BUDGET", lambda: in625.IN625_U95_BUDGET)
    for prop in ("density", "conductivity", "viscosity", "cp"):
        observe_value(observations, f"in625.u95.{prop}",
                      lambda prop=prop: each(lambda t: in625.in625_u95_uncertainty_at_kelvin(t, prop),
                                             (300.0, 1590.0, 2000.0, 3500.0)))
    observe_value(observations, "in625gpu.cpuThermal",
                  lambda: in625_gpu.in625_cpu_thermal_at_kelvin(np.linspace(300.0, 2500.0, 23)))
    observe_value(observations, "ss304.snapshot", ss304.ss304_support_thermal_snapshot)
    observe_value(observations, "ss304.atKelvin",
                  lambda: [ss304.ss304_support_thermal_at_kelvin(t) for t in (273.15, 600.0, 1473.15)])
    observe_value(observations, "ss304.fields",
                  lambda: ss304.ss304_support_thermal_fields(np.linspace(273.15, 1473.15, 13)))
    return observations


def _cfd_case_module():
    """B1 moves the test-only setup functions to lpbf_cfd_cases; resolve by name either way."""
    try:
        import lpbf_cfd_cases as module  # type: ignore[import-not-found]
        return module
    except ModuleNotFoundError as exc:
        if exc.name != "lpbf_cfd_cases":
            raise  # a broken lpbf_cfd_cases (missing dependency) must not fall back silently
        import lpbf_cfd as module
        return module


def _tree_observations(root: Path, prefix: str) -> Dict[str, Any]:
    """File tree digest with platform-neutral names (POSIX) and newlines (CRLF -> LF).

    The case writers use Path.write_text, i.e. platform newlines; normalising them keeps
    the G10 goldens about content, not about the OS that wrote them.
    """
    observations: Dict[str, Any] = {}
    files = sorted(p for p in root.rglob("*") if p.is_file())
    observations[f"{prefix}.files"] = [p.relative_to(root).as_posix() for p in files]
    for path in files:
        data = path.read_bytes().replace(b"\r\n", b"\n")
        if str(root).encode() in data or root.as_posix().encode() in data:
            raise AssertionError(f"{path.name} embeds the absolute case directory")
        observations[f"{prefix}.file.{path.relative_to(root).as_posix()}"] = [len(data), sha256_bytes(data)]
    return observations


def case_g10_openfoam_case_generation(ctx: CaseContext) -> Dict[str, Any]:
    import lpbf_cfd
    import lpbf_openfoam
    from lpbf_simulation import validate

    cases_module = _cfd_case_module()
    observations: Dict[str, Any] = {}
    for name in ("setup_droplet_case", "setup_stefan_case", "setup_darcy_damping_case",
                 "setup_thermal_parity_case", "setup_marangoni_case", "setup_recoil_case",
                 "setup_laser_case"):
        folder = ctx.new_dir(f"cfd-{name}")
        status, value = capture_call(lambda name=name, folder=folder: getattr(cases_module, name)(folder))
        observations[f"cfd.{name}.return"] = typed_sha256(_relative(value, folder)) if status == "ok" else {"error": value}
        observations.update(_tree_observations(folder, f"cfd.{name}"))
    observe_value(observations, "cfd.stefan_analytical_solution",
                  lambda: [cases_module.stefan_analytical_solution(t) for t in (1e-7, 1e-6, 5e-6, 1e-5)])
    observe_value(observations, "cfd.knight_analytical_recoil_pressure",
                  lambda: [cases_module.knight_analytical_recoil_pressure(t) for t in (2500.0, 3000.0, 3560.0, 4000.0)])
    p, m = validate({**SMALL, "tracks": 2, "layers": 1})
    folder = ctx.new_dir("cfd-multiphysics")
    status, value = capture_call(lambda: lpbf_cfd.setup_cfd_multiphysics_case(p, m, folder))
    observations["cfd.setup_cfd_multiphysics_case.return"] = (
        typed_sha256(_relative(value, folder)) if status == "ok" else {"error": value})
    observations.update(_tree_observations(folder, "cfd.setup_cfd_multiphysics_case"))
    for label, raw in (("powder", {**SMALL, "backend": "openfoam-thermal"}),
                       ("powderMultilayer", {**SMALL, "backend": "openfoam-thermal", "tracks": 2,
                                             "layers": 2, "dwell_s": 2e-5})):
        p, m = validate(raw)
        folder = ctx.new_dir(f"openfoam-{label}")
        status, value = capture_call(lambda p=p, m=m, folder=folder: lpbf_openfoam.generate_case(p, m, folder))
        observations[f"openfoam.generate_case.{label}.return"] = (
            typed_sha256(value) if status == "ok" else {"error": value})
        observations.update(_tree_observations(folder, f"openfoam.generate_case.{label}"))
    return observations


def _relative(value: Any, folder: Path) -> Any:
    """Replace the absolute work folder in returned values so goldens are location-independent."""
    text = str(folder)
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        return value.replace(text, "<CASE>").replace(folder.as_posix(), "<CASE>")
    if isinstance(value, dict):
        return {k: _relative(v, folder) for k, v in value.items()}
    if isinstance(value, list):
        return [_relative(v, folder) for v in value]
    if isinstance(value, tuple):
        return tuple(_relative(v, folder) for v in value)
    return value


G11_PAYLOADS = (
    dict(material_name="Inconel 718", laser_power_W=200.0, scan_speed_mm_s=800.0, beam_diameter_um=80.0,
         preheat_temp_C=80.0, layer_thickness_um=40.0, hatch_spacing_um=100.0, heat_source="rosenthal"),
    dict(material_name="Ti-6Al-4V", laser_power_W=280.0, scan_speed_mm_s=1200.0, beam_diameter_um=70.0,
         preheat_temp_C=200.0, layer_thickness_um=30.0, hatch_spacing_um=120.0, heat_source="eagar-tsai",
         sulfur_ppm=40.0),
    dict(material_name="316L Stainless Steel", laser_power_W=370.0, scan_speed_mm_s=600.0,
         beam_diameter_um=60.0, preheat_temp_C=25.0, layer_thickness_um=50.0, hatch_spacing_um=90.0,
         heat_source="goldak", incline_angle_deg=15.0),
)


def case_g11_build_job_meltpool(ctx: CaseContext) -> Dict[str, Any]:
    _require_cpu_meltpool_payloads(G11_PAYLOADS)
    return _cpu_meltpool_only(lambda: _g11_observations(ctx))


def _g11_observations(ctx: CaseContext) -> Dict[str, Any]:
    from lpbf_thermal_solver import calculate_meltpool_physics, classify_enthalpy_regime, THERMOPHYSICAL_DB

    observations: Dict[str, Any] = {}
    for index, payload in enumerate(G11_PAYLOADS):
        status, value = capture_call(lambda payload=payload: calculate_meltpool_physics(**payload))
        if status == "ok":
            observations[f"meltpool.{index}.typedSha256"] = typed_sha256(value)
            observations[f"meltpool.{index}.canonicalSha256"] = canonical_json_sha256(value)
            remember_raw(f"meltpool.{index}.typedSha256", value)
            # Small companions of the digests above (the full value exceeds RAW_VALUE_LIMIT),
            # so a drift report carries raw before/after values (review pb-r2 S2).
            observe_value(observations, f"meltpool.{index}.geometry_um", lambda value=value: _meltpool_geometry_um(value))
            observe_value(observations, f"meltpool.{index}.peakTemperature_C",
                          lambda value=value: value["hydrodynamicsAndRecoil"]["peakTemperature_C"])
        else:
            observations[f"meltpool.{index}"] = {"error": value}
    observe_value(observations, "thermalSolver.THERMOPHYSICAL_DB", lambda: THERMOPHYSICAL_DB)
    observe_value(observations, "thermalSolver.THERMOPHYSICAL_DB.in625.latent_heat_fusion_J_kg",
                  lambda: THERMOPHYSICAL_DB["Inconel 625"]["latent_heat_fusion_J_kg"])
    observe_value(observations, "thermalSolver.classify_enthalpy_regime",
                  lambda: [classify_enthalpy_regime(x) for x in (0.0, 14.99, 15.0, 29.99, 30.0, 80.0)])
    return observations


def case_g12_analytical_modules(ctx: CaseContext) -> Dict[str, Any]:
    import eagar_tsai_solver
    import fabbro_keyhole
    import goldak_solver
    import marangoni_screening
    import solidification_front
    import powder_packer
    from lpbf_thermal_solver import rosenthal_temperature_C

    observations: Dict[str, Any] = {}
    xs = np.linspace(-200e-6, 100e-6, 7)
    ys = np.linspace(0.0, 80e-6, 3)
    zs = np.linspace(-60e-6, 0.0, 3)
    grid = [(float(x), float(y), float(z)) for x in xs for y in ys for z in zs]
    observe_value(observations, "eagarTsai.temperature",
                  lambda: [eagar_tsai_solver.eagar_tsai_temperature_C(x, y, z, 80.0, 76.0, 25.0, 0.8,
                                                                       5.5e-6, 40e-6) for x, y, z in grid])
    observe_value(observations, "rosenthal.temperature",
                  lambda: [rosenthal_temperature_C(x, y, z, 80.0, 76.0, 25.0, 0.8, 5.5e-6, 5e-6)
                           for x, y, z in grid])

    def goldak():
        axes = goldak_solver.seed_goldak_axes(40e-6)
        field = goldak_solver.GoldakField(80.0, 76.0, 8190.0, 435.0, 5.5e-6, **axes).bind_speed(0.8)
        return {"axes": axes, "fractions": goldak_solver.goldak_fractions(40e-6, 80e-6),
                "q": goldak_solver.goldak_q_parameter_W(76.0),
                "temperature": [field.temperature_C(x, y, z) for x, y, z in grid]}
    observe_value(observations, "goldak.field", goldak)
    observe_value(observations, "fabbro.depth",
                  lambda: [fabbro_keyhole.fabbro_keyhole_depth_m(p, v, 80e-6, 25.0, 5.5e-6, 2900.0, 80.0, 0.4, h)
                           for p, v, h in ((100.0, 1.0, 10.0), (200.0, 0.8, 20.0), (370.0, 0.5, 45.0))])
    observe_value(observations, "marangoni.heipleRoper",
                  lambda: [marangoni_screening.heiple_roper_d_gamma_dT(-3.7e-4, s) for s in (0.0, 15.0, 30.0, 45.0, 60.0, 90.0)])
    observe_value(observations, "marangoni.screening",
                  lambda: [marangoni_screening.marangoni_screening(-3.7e-4, 5e-3, 5.5e-6, 7400.0, 50e-6, t, 1336.0, s)
                           for t in (1500.0, 2500.0) for s in (5.0, 45.0, 80.0)])
    # SOL-A1 (2026-10-15, solidification integration contract 6.2 and 6.3): the four legacy helper observations
    # (solidification.hunt, .pdas, .sdas, .phaseNote) are retired with their helpers, and solidification.evaluate
    # calls the front without the ignored legacy keywords. solidification.pdasAdmission pins the five named (G, R)
    # pairs of 6.3 through pdas_band_um for in625, in718 and ti6al4v: only pair 1 lies on the source line G = 1e7 K/m;
    # pairs 2 and 3 are refused by the line rule alone (x, cooling, Vcs and Vab all pass), 4 is also below Vcs and 5
    # above Vab, so a mutant that keeps the old x/cooling box and adds only Vcs and Vab gives a band for pairs 2 and 3
    # and drifts. solidification.defaultBlock is the blanket-null container of the five canonical IDs on this
    # Eagar-Tsai field at each alloy's served liquidus; solidification.unknownAlias records the refusals as values with
    # reason codes, never as error observations (an error never passes --expect-drift, 6.1).
    from lpbf_thermal_solver import THERMOPHYSICAL_DB

    field = eagar_tsai_solver.EagarTsaiField(80.0, 76.0, 25.0, 5.5e-6, 40e-6).bind_speed(0.8)

    def front(material_name: str, liquidus_C: float) -> Dict[str, Any]:
        return solidification_front.evaluate_solidification(
            field.temperature_C, T_liq=liquidus_C, v_scan=0.8, x_rear=-150e-6, search_depth=80e-6, r_beam=40e-6,
            material_name=material_name, authority_liquidus_C=liquidus_C)

    observe_value(observations, "solidification.evaluate", lambda: front("Inconel 718", 1336.0))
    pdas_pairs = ((1e7, 0.05), (2e7, 0.01), (5e6, 0.05), (5e7, 0.0012), (1e6, 1.5))
    observe_value(observations, "solidification.pdasAdmission",
                  lambda: {alloy: [solidification_front.pdas_band_um(g, r, alloy) for g, r in pdas_pairs]
                           for alloy in ("in625", "in718", "ti6al4v")})
    served_names = (("ti6al4v", "Ti-6Al-4V"), ("alsi10mg", "AlSi10Mg"), ("in718", "Inconel 718"),
                    ("in625", "Inconel 625"), ("ss316l", "316L Stainless Steel"))
    observe_value(observations, "solidification.defaultBlock",
                  lambda: {alloy: front(alloy, THERMOPHYSICAL_DB[name]["liquidus_C"]) for alloy, name in served_names})
    observe_value(observations, "solidification.unknownAlias",
                  lambda: {"evaluate": front("inconel", 1336.0),
                           "pdasBandServedName": solidification_front.pdas_band_um(1e7, 0.05, "Inconel 718"),
                           "canonicalAlloyId": {name: solidification_front.canonical_alloy_id(name)
                                                for name in ("Inconel 625", "IN625", "Inconel 718", "inconel",
                                                             "Ti-6Al-4V", "AlSi10Mg", "316L Stainless Steel",
                                                             "CoCrMo")}})
    # powder_bed_raytracer and warp_thermal_solver import warp at module import; they are
    # GPU-only (design 2.3: GPU numerics are not verifiable here) and are not covered.

    def packing():
        spheres = powder_packer.generate_powder_bed(300e-6, 200e-6, 40e-6, target_packing=0.5, seed=7)
        return {"spheres": spheres,
                "statistics": powder_packer.compute_powder_bed_statistics(spheres, 300e-6, 200e-6, 40e-6),
                "validation": powder_packer.validate_powder_bed(spheres, 300e-6, 200e-6, 40e-6)}
    observe_value(observations, "powderPacker.seeded", packing)
    return observations


def case_npz_determinism(ctx: CaseContext) -> Dict[str, Any]:
    """np.savez_compressed writes the 1980 zip timestamp: identical bytes across time."""
    with np.load(FIXTURE_NPZ, allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    first = io.BytesIO()
    np.savez_compressed(first, **arrays)
    time.sleep(2.1)  # zip timestamps have a 2 s resolution
    second = io.BytesIO()
    np.savez_compressed(second, **arrays)
    observations: Dict[str, Any] = {
        "npz.resaveTwiceEqual": first.getvalue() == second.getvalue(),
        "npz.resaveEqualsFixtureBytes": first.getvalue() == FIXTURE_NPZ.read_bytes(),
        "npz.resaveSha256": sha256_bytes(first.getvalue()),
        "npz.fixtureSha256": sha256_bytes(FIXTURE_NPZ.read_bytes()),
    }
    observations.update(npz_observations(FIXTURE_NPZ, "npz.fixture"))
    return observations


class Case:
    def __init__(self, case_id: str, group: str, function: Callable[[CaseContext], Dict[str, Any]],
                 description: str, *, slow: bool = False, runs_solver: bool = True):
        self.id, self.group, self.function, self.description = case_id, group, function, description
        self.slow, self.runs_solver = slow, runs_solver


CASES: Tuple[Case, ...] = (
    Case("g1_v1_60w_in718", "G1", case_g1_v1_60w,
         "V1 acceptance case from the archived inputJson (fc8325d9...), with all artifacts"),
    Case("g2_bare_plate_100w_corridor", "G2", case_g2_bare_plate_fixture,
         "Real bare-plate 100 W corridor job 7ec9dc57...; compared with the in-repo fixture (~106 s)",
         slow=True),
    Case("g3_powder_stripe_multilayer", "G3", case_g3_powder_stripe_multilayer,
         "Two-track two-layer stripe powder run with dwell, scan angle and layer rotation"),
    Case("g3_powder_island", "G3", case_g3_powder_island, "Two-track island powder run with dwell"),
    Case("g4_layered_plate", "G4", case_g4_layered_plate, "layered-plate-enthalpy-v1 with SS304 support"),
    Case("g5_evaporation", "G5", case_g5_evaporation, "evaporationModel=True short powder track"),
    Case("g6_screening_and_fallback", "G6", case_g6_screening_and_fallback,
         "Screening (Goldak/Rosenthal) and the honest high-fidelity fallback"),
    Case("g7_mesh_study", "G7", case_g7_mesh_study, "Smallest layer-aligned three-grid mesh study"),
    Case("g7_timestep_study", "G7", case_g7_timestep_study, "study='timestep' (2x and sqrt(2)x maxDt)"),
    Case("g3_powder_meander_unidirectional", "G3", case_g3_powder_meander_unidirectional,
         "Two-track meander and unidirectional powder runs"),
    Case("g13_source_quadrature_refinement", "G13", case_g13_source_quadrature_refinement,
         "integrated_source N-vs-2N refinement branch (unreachable from the CPU transient)",
         runs_solver=False),
    Case("g14_calibration_measurements", "G14", case_g14_calibration_measurements,
         "mode='calibration' with matched/unmatched measurements; measurementComparison"),
    Case("g15_bare_plate_square_optical_observer", "G15", case_g15_bare_plate_square_optical_observer,
         "Square bare plate with opticalObserver='nist-six-section', all artifacts"),
    Case("g16_non_in718_transient", "G16", case_g16_non_in718_transient,
         "Standard transient for Ti-6Al-4V, 316L and AlSi10Mg"),
    Case("g17_evaporation_ti6al4v", "G17", case_g17_evaporation_ti6al4v,
         "evaporationModel=True Ti-6Al-4V 80 W: L_v passed to the inversion (today IN718's 6.4e6)"),
    Case("g17_evaporation_316l", "G17", case_g17_evaporation_316l,
         "evaporationModel=True 316L 80 W: L_v passed to the inversion (today IN718's 6.4e6)"),
    Case("g17_evaporation_alsi10mg", "G17", case_g17_evaporation_alsi10mg,
         "evaporationModel=True AlSi10Mg 500 W: L_v passed to the inversion (today IN718's 6.4e6)"),
    Case("g18_in625_latent_heat", "G18", case_g18_in625_latent_heat,
         "IN625 fusion latent heat per path: Rosenthal melt pool (260 kJ/kg), screening (290), transient spec (227)",
         runs_solver=False),
    Case("g19_emissivity_echo", "G19", case_g19_emissivity_echo,
         "Registry emissivity literal 0.35 echoed into p/m per alloy; accepted overrides including 0.36"),
    Case("g8_observers", "G8", case_g8_observers,
         "final-state, selected-time, local-history observers and CpuRunProgress; rejection messages"),
    Case("g9_material_snapshots", "G9", case_g9_material_snapshots,
         "Material snapshots, four-alloy tables, IN625 and SS304, typed and key-ordered", runs_solver=False),
    Case("g10_openfoam_case_generation", "G10", case_g10_openfoam_case_generation,
         "OpenFOAM case writers (CFD setup_*_case, multiphysics, thermal) file-tree SHA-256", runs_solver=False),
    Case("g11_build_job_meltpool", "G11", case_g11_build_job_meltpool,
         "lpbf_thermal_solver.calculate_meltpool_physics for three fixed payloads", runs_solver=False),
    Case("g12_analytical_modules", "G12", case_g12_analytical_modules,
         "Eagar-Tsai, Rosenthal, Goldak, Fabbro, Marangoni, solidification front", runs_solver=False),
    Case("npz_determinism", "NPZ", case_npz_determinism,
         "np.savez_compressed bytes are time-independent (fixture arrays, 2.1 s apart)", runs_solver=False),
)
CASE_BY_ID = {case.id: case for case in CASES}

# Paths the goldens do NOT cover (design 5c review). B commits that touch these need their
# own evidence; a green --check says nothing about them.
NOT_COVERED = (
    "GPU numerics: lpbf_gpu_thermal.py, lpbf_gpu_thermal_warp.py, lpbf_transient_3d_gpu.py, "
    "lpbf_gpu_pilot_*.py, warp_thermal_solver.py, powder_bed_raytracer.py and the IN625 CUDA "
    "adapter (no CUDA/Warp here; design rule: do not edit them in the bump)",
    "OpenFOAM execution: lpbf_openfoam.thermal(), cfd_multiphysics() and metalliksaThermal.C "
    "(only case generation is pinned, G10); backend='auto' with openfoamThermal capability",
    "setup_cfd_multiphysics_case beyond the powder-packer NotImplementedError (G10 pins the error "
    "and the files written before it)",
    "User-supplied material properties (validate 'properties' / material(name, supplied))",
    "Layered plate with supportBottomBoundary='isothermal-at-preheat' and non-zero incidence azimuth",
    "Worker-side consumers of opticalObserver / NIST section operators (lpbf_worker.py, "
    "lpbf_nist_*; not in the manifest); G15 pins only that the setting passes through run()",
    "CpuRunProgress source-work budget failures (maximum_source_evaluations / _cell_steps)",
    "The opt-in GPU melt-pool paths (absorption_model='powder-raytrace', thermal_slice_backend='warp'); "
    "G11/G18 run with those modules blocked (see _cpu_meltpool_only)",
)


# --------------------------------------------------------------------------- record / check

def pinned_fingerprint() -> str:
    """The one strict pin parser shared with the pin test and the bump record."""
    return read_pinned_fingerprint(EXPECTED_FINGERPRINT_FILE)


def _git_head() -> Optional[str]:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _cpu_brand() -> str:
    try:
        if platform.system() == "Windows":
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.is_file():
            for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def _numpy_runtime() -> Dict[str, Any]:
    """numpy SIMD dispatch (what np.show_runtime() summarises) and the BLAS build."""
    info: Dict[str, Any] = {}
    try:
        from numpy._core._multiarray_umath import (__cpu_baseline__, __cpu_dispatch__,
                                                    __cpu_features__)
        info["simdBaseline"] = list(__cpu_baseline__)
        info["simdDispatch"] = list(__cpu_dispatch__)
        info["simdFound"] = sorted(name for name, found in __cpu_features__.items() if found)
    except ImportError as exc:
        info["simd"] = f"unavailable: {exc}"
    try:
        blas = np.show_config(mode="dicts")["Build Dependencies"]["blas"]
        info["blas"] = f"{blas.get('name')} {blas.get('version')}"
    except Exception as exc:  # noqa: BLE001 - informational only
        info["blas"] = f"unavailable: {type(exc).__name__}"
    return info


def environment() -> Dict[str, Any]:
    """Everything a bit-exact golden depends on besides the code: the goldens are valid
    only where this is equal (the reference machine with the locked runtime)."""
    return {"python": platform.python_version(), "numpy": np.__version__,
            "platform": platform.system(), "runtime": Path(sys.prefix).name,
            "cpu": _cpu_brand(), "numpyRuntime": _numpy_runtime()}


def environment_mismatch(recorded: Dict[str, Any]) -> Optional[str]:
    current = environment()
    if recorded == current:
        return None
    keys = sorted(k for k in set(recorded) | set(current) if recorded.get(k) != current.get(k))
    return ("environment differs from the recording in " + ", ".join(keys)
            + "; goldens are bit-exact only on the reference machine "
              "(rerun there, or pass --allow-environment-mismatch to compare anyway)")


def execute(case: Case, work_root: Path) -> Tuple[Dict[str, Any], List[str], float]:
    """Run one case; returns (observations, implementation hashes, seconds).

    Raw pre-hash values (small values and all each() lists, see remember_raw) are left in
    LAST_RAW_VALUES for reports and per-item error transitions. Bit equality still compares
    the observations; raw errors additionally constrain which planned drifts may pass.
    """
    global _RAW_SINK
    work_root.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix=f"{case.id}-", dir=str(work_root)))
    ctx = CaseContext(work_dir)
    raw: Dict[str, Any] = {}
    LAST_RAW_VALUES.clear()
    started = time.perf_counter()
    _RAW_SINK = raw
    try:
        observations = case.function(ctx)
    finally:
        _RAW_SINK = None
        elapsed = time.perf_counter() - started
        shutil.rmtree(work_dir, ignore_errors=True)
    # Round-trip through JSON so record and check compare the same value domain.
    observations = json.loads(json.dumps(observations, allow_nan=False))
    LAST_RAW_VALUES.update({key: value for key, value in sorted(raw.items())
                            if key in observations and observations[key] != value})
    return observations, ctx.implementation_hashes, elapsed


def golden_path(case: Case) -> Path:
    return GOLDEN_DIR / f"{case.id}.json"


def diff_keys(expected: Dict[str, Any], actual: Dict[str, Any]) -> List[str]:
    return [key for key in sorted(set(expected) | set(actual))
            if key not in expected or key not in actual or expected[key] != actual[key]]


def diff_observations(expected: Dict[str, Any], actual: Dict[str, Any]) -> List[str]:
    problems = []
    for key in diff_keys(expected, actual):
        if key not in actual:
            problems.append(f"missing observation {key}")
        elif key not in expected:
            problems.append(f"unexpected new observation {key}")
        else:
            problems.append(f"changed {key}: expected {json.dumps(expected[key])[:160]} "
                            f"got {json.dumps(actual[key])[:160]}")
    return problems


def pin_mismatch(pinned: str, current: str) -> Optional[str]:
    """The pin comparison, reported separately from the result checks."""
    if current != pinned:
        return f"implementation_fingerprint() {current} != pinned {pinned}"
    return None


def check_implementation(case: Case, hashes: List[str], pinned: str, current: str,
                         expect_unpinned: bool = False) -> Tuple[List[str], List[str]]:
    """Return (problems, warnings).

    A pin mismatch is a problem, except on a bump branch (--expect-unpinned), where every
    B1-B5 commit legitimately changes the fingerprint before B6 re-pins it: there it is a
    warning. A result whose provenance.implementationHash differs from the CURRENT
    implementation_fingerprint() is always a problem, and so are observation diffs.
    """
    problems: List[str] = []
    warnings: List[str] = []
    mismatch = pin_mismatch(pinned, current)
    if mismatch is not None:
        (warnings if expect_unpinned else problems).append(
            mismatch + (" (expected on the bump branch before B6)" if expect_unpinned else ""))
    elif expect_unpinned:
        warnings.append("--expect-unpinned given but the fingerprint still equals the pin")
    for value in hashes:
        if value != current:
            problems.append(f"result provenance.implementationHash {value} != implementation_fingerprint() {current}")
    if case.runs_solver and not hashes:
        problems.append("solver case produced no provenance.implementationHash")
    return problems, warnings


def selected_cases(args) -> List[Case]:
    if args.case:
        unknown = [c for c in args.case if c not in CASE_BY_ID]
        if unknown:
            raise SystemExit(f"unknown case(s): {', '.join(unknown)}")
        return [CASE_BY_ID[c] for c in args.case]
    return [case for case in CASES if args.slow or not case.slow]


def command_record(args) -> int:
    from lpbf_simulation import implementation_fingerprint, VERSION
    current, pinned = implementation_fingerprint(), pinned_fingerprint()
    if current != pinned:
        print(f"REFUSED: implementation_fingerprint() {current} != pinned {pinned}")
        return 2
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    failures = 0
    for case in selected_cases(args):
        path = golden_path(case)
        if path.exists() and not args.force:
            print(f"{case.id}: golden exists; use --force to overwrite")
            failures += 1
            continue
        try:
            observations, hashes, elapsed = execute(case, Path(args.work_root))
            raw_values = dict(LAST_RAW_VALUES)
        except CaseSkipped as skipped:
            print(f"{case.id}: NOT RECORDED (skipped: {skipped})")
            failures += 1
            continue
        problems, _ = check_implementation(case, hashes, pinned, current)
        runs = [round(elapsed, 1)]
        if args.twice:
            again, hashes_again, elapsed_again = execute(case, Path(args.work_root))
            runs.append(round(elapsed_again, 1))
            problems += check_implementation(case, hashes_again, pinned, current)[0]
            problems += [f"run 2 differs: {p}" for p in diff_observations(observations, again)]
            problems += [f"run 2 raw value differs: {key}" for key in diff_keys(raw_values, LAST_RAW_VALUES)]
        if problems:
            failures += 1
            print(f"{case.id}: NOT RECORDED")
            for problem in problems:
                print(f"    {problem}")
            continue
        golden = {
            "schema": GOLDEN_SCHEMA, "case": case.id, "group": case.group,
            "description": case.description, "slow": case.slow,
            "recordedImplementationHash": current, "recordedVersion": VERSION,
            "recordedGitHead": _git_head(), "recordedEnvironment": environment(),
            "recordedRuns_s": runs, "recordedTwice": bool(args.twice),
            "observations": observations,
            # Raw pre-hash values of small digest observations: drift-report context only,
            # never compared (the observations above are the evidence).
            "rawValues": raw_values,
        }
        path.write_text(json.dumps(golden, indent=1, sort_keys=False, allow_nan=False) + "\n",
                        encoding="utf-8", newline="\n")
        print(f"{case.id}: recorded {len(observations)} observations in {'/'.join(map(str, runs))} s")
    return 1 if failures else 0


def check_case(case: Case, work_root: Path, expect_unpinned: bool = False,
               allow_environment_mismatch: bool = False) -> Dict[str, Any]:
    """Run one case against its golden; returns problems, observations and timing."""
    from lpbf_simulation import implementation_fingerprint
    path = golden_path(case)
    outcome: Dict[str, Any] = {"case": case.id, "problems": [], "warnings": [], "elapsed_s": 0.0,
                               "observations": {}, "rawValues": {}, "golden": None, "skipped": None,
                               "comparedDespiteEnvironment": False}
    if not path.is_file():
        outcome["problems"] = [f"golden missing: {path}"]
        return outcome
    golden = json.loads(path.read_text(encoding="utf-8"))
    outcome["golden"] = golden
    if golden.get("schema") != GOLDEN_SCHEMA or golden.get("case") != case.id:
        outcome["problems"] = [f"golden {path.name} has the wrong schema or case id"]
        return outcome
    current, pinned = implementation_fingerprint(), pinned_fingerprint()
    mismatch = environment_mismatch(golden.get("recordedEnvironment", {}))
    if mismatch is not None and not allow_environment_mismatch:
        outcome["skipped"] = mismatch
        return outcome
    try:
        observations, hashes, elapsed = execute(case, work_root)
    except CaseSkipped as skipped:
        outcome["skipped"] = str(skipped)
        return outcome
    problems, warnings = check_implementation(case, hashes, pinned, current, expect_unpinned)
    implementation_problems = list(problems)
    diffs = diff_observations(golden["observations"], observations)
    problems += diffs
    if mismatch is not None:
        warnings.append(f"compared despite: {mismatch}")
    outcome.update(problems=problems, warnings=warnings, elapsed_s=elapsed, observations=observations,
                   rawValues=dict(LAST_RAW_VALUES), implementationHashes=sorted(set(hashes)),
                   implementationProblems=implementation_problems, observationDiffs=diffs,
                   comparedDespiteEnvironment=mismatch is not None)
    return outcome


# --------------------------------------------------------------------------- planned drift

# Reference transient cases (V1 replay, real bare-plate fixture, layered plate): never named
# as a whole in --expect-drift; only CASE:KEY entries, and never for their numerics below.
REFERENCE_CASES = ("g1_v1_60w_in718", "g2_bare_plate_100w_corridor", "g4_layered_plate")
# Identity observations: a change fails in EVERY case unless an entry names that exact key.
IDENTITY_PATTERNS = ("*materialRevisionSha256*", "*materialSha256*", "*inputSha256*")
# P7b (2026-10-14): the two G2 fixture booleans that compare the whole stripped result and the core-contract material
# digest with the real capture are identity-class, not numerics: they flip when the material authority moves while
# every numeric observation of the case stays protected (fixture.strippedResultEqualExceptMaterialIdentity carries the
# replay claim). They may drift only when named exactly, like every identity observation. The replay-claim observation
# fixture.strippedResultEqualExceptMaterialIdentity itself is recorded True and falls under the fixture.* never-drift
# rule (P7b gate ruling): it is the G2 replay claim, not an identity flag. Its first appearance against a golden that
# never recorded it is allowed by an entry naming it exactly (evaluate_drift), as any new observation is.
REFERENCE_IDENTITY_FLAGS = ("fixture.strippedResultEqual", "fixture.materialSha256Equal")
# Reference numerics: a change of a recorded value in a REFERENCE_CASES case always fails, whatever the allowlist.
# The one exception is a first appearance (a key the golden never recorded, so nothing recorded changes): it is
# allowed by an entry naming it exactly (evaluate_drift); honesty keys are never allowed, recorded or new.
REFERENCE_NUMERICS_PATTERNS = (
    "*.key.metrics", "*.key.thermalHistory", "*.key.energyBalance", "*.key.field*",
    "*.key.artifacts", "artifact.*", "artifacts.*", "npz.*", "*.artifact.*", "*.artifacts*",
    "*.npz.*", "fixture.*",
    "*.key.peakInterpolatedMeltPool", "*.key.midTrack*", "*.key.massBalance",
    "*.key.numericalDiagnostics", "*.key.phaseAudit", "*.key.settings", "*.key.discretization",
    "*.key.scanPath")
# Honesty observations: a change fails in EVERY case (not only the reference cases), whatever
# the allowlist. The bare names cover observation keys without a prefix.
HONESTY_PATTERNS = (
    "*.validationStatus", "*.key.validationStatus", "*.productionReady", "*.key.productionReady",
    "*.coreContract.solverId", "*.key.confidence", "*.confidence", "*.effectiveMode",
    "validationStatus", "productionReady", "confidence", "effectiveMode",
    # Review rr2 S2: the evidence-honesty flags and the G9 IN625 screening admission verdict.
    "*.experimentalValidation", "*.key.experimentalValidation",
    "*.experimentalComparison", "*.key.experimentalComparison",
    "*.unresolvedPhysics", "*.key.unresolvedPhysics",
    "*.opticalOperatorMatched", "*.key.opticalOperatorMatched",
    "in625.validateScreeningAdmission",
    "experimentalValidation", "experimentalComparison", "unresolvedPhysics", "opticalOperatorMatched")
GLOB_CHARACTERS = "*?["


class DriftEntry:
    """One --expect-drift entry: a whole case, or CASE:KEY_GLOB (fnmatch on observation keys)."""

    def __init__(self, case_id: str, pattern: Optional[str]):
        self.case_id, self.pattern = case_id, pattern

    @property
    def text(self) -> str:
        return self.case_id if self.pattern is None else f"{self.case_id}:{self.pattern}"

    def matches(self, key: str) -> bool:
        return self.pattern is None or fnmatch.fnmatchcase(key, self.pattern)


def parse_expect_drift(values: Optional[List[str]]) -> List[DriftEntry]:
    """--expect-drift a,b:KEY --expect-drift c -> entries; unknown, empty or refused names error."""
    entries: List[DriftEntry] = []
    for value in values or []:
        for item in value.split(","):
            item = item.strip()
            case_id, separator, pattern = item.partition(":")
            if not case_id or (separator and not pattern):
                raise SystemExit(f"--expect-drift: empty case or key in {item!r}")
            if case_id not in CASE_BY_ID:
                raise SystemExit(f"--expect-drift: unknown case {case_id}")
            if not separator and case_id in REFERENCE_CASES:
                raise SystemExit(f"--expect-drift: {case_id} is a reference transient case; name the "
                                 f"observations that may drift ({case_id}:KEY_GLOB), never the whole case")
            if separator and case_id in REFERENCE_CASES and any(c in pattern for c in GLOB_CHARACTERS):
                raise SystemExit(f"--expect-drift: {item!r} contains a glob character ({GLOB_CHARACTERS}); "
                                 f"{case_id} is a reference transient case, so only exact observation keys "
                                 f"({case_id}:EXACT.KEY) may be named")
            if all(e.text != item for e in entries):
                entries.append(DriftEntry(case_id, pattern if separator else None))
    return entries


# Error rule: five shapes, including each() raw lists and reject.* refusals. The gate makes
# new/changed/recovered errors exact-key only; value -> error remains forbidden under every entry.
_ABSENT = object()


def is_error_observation(value: Any) -> bool:
    """The observe_value / G11 error shape: a dict carrying an "error" member."""
    return isinstance(value, dict) and "error" in value


def is_error_key(key: str) -> bool:
    """The G16 error shape: the text of a failed sub-run under "<prefix>.error"."""
    return key == "error" or key.endswith(".error")


def error_items(key: str, value: Any) -> Dict[str, Any]:
    """Errors indexed by item path, so a pre-existing error cannot hide another item's failure."""
    if value is _ABSENT:
        return {}
    if is_error_observation(value):
        return {"": value["error"]}
    if is_error_key(key) or (key.startswith("reject.") and isinstance(value, str) and value != "NO-ERROR"):
        return {"": value}
    errors = {}
    if isinstance(value, list):
        for index, item in enumerate(value):
            if isinstance(item, list) and len(item) == 2 and item[0] == "error":
                errors[str(index)] = item[1]
    return errors


def error_rule_problem(key: str, before: Any, after: Any) -> Optional[str]:
    """Non-waivable transitions; new errors and changes/recoveries are checked for exact keys by the caller."""
    if after is _ABSENT:
        return None
    old, new = error_items(key, before), error_items(key, after)
    if key.startswith("reject.") and old and after == "NO-ERROR":
        return f"changed {key}: a refusal became NO-ERROR, which never passes under --expect-drift"
    if before is not _ABSENT and any(path not in old for path in new):
        return f"changed {key}: the value became an error observation, which never passes under --expect-drift"
    return None


def _protected_reason(case_id: str, key: str, entries: List[DriftEntry]) -> Optional[str]:
    if key in REFERENCE_IDENTITY_FLAGS:
        if not any(e.pattern == key for e in entries):
            return "identity observation: allowed only by an entry naming this exact key"
        return None
    if case_id in REFERENCE_CASES and any(fnmatch.fnmatchcase(key, p) for p in REFERENCE_NUMERICS_PATTERNS):
        return "reference-case numerics never drift under --expect-drift"
    if any(fnmatch.fnmatchcase(key, p) for p in HONESTY_PATTERNS):
        return "honesty observation never drifts under --expect-drift"
    if any(fnmatch.fnmatchcase(key, p) for p in IDENTITY_PATTERNS) and not any(e.pattern == key for e in entries):
        return "identity observation: allowed only by an entry naming this exact key"
    return None


def jsonable(value: Any) -> Any:
    """Plain JSON form of a raw observed value (numpy and tuples converted); TypeError if none."""
    if value is None or type(value) in (bool, int, float, str):
        return value
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, np.generic):
        return jsonable(value.item())
    if isinstance(value, (dict, types.MappingProxyType)):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted((jsonable(v) for v in value), key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, str):
        return str(value)
    raise TypeError(type(value).__name__)


def remember_raw(key: str, value: Any) -> None:
    """Keep the raw value behind a digest observation when it is small (<= RAW_VALUE_LIMIT
    characters of JSON), for drift reports. each() lists are always kept for the error rule."""
    if _RAW_SINK is None:
        return
    try:
        text = json.dumps(jsonable(value), allow_nan=False)
    except (TypeError, ValueError):
        return
    each_list = isinstance(value, list) and value and all(
        isinstance(item, list) and len(item) == 2 and item[0] in ("ok", "error") for item in value)
    if len(text) <= RAW_VALUE_LIMIT or each_list:
        _RAW_SINK[key] = json.loads(text)


def describe_value(value: Any) -> str:
    """Short value-level rendering for drift reports: floats with float.hex(), digests shortened."""
    if type(value) is float:
        return f"{value!r} ({value.hex()})"
    if isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value):
        return f"sha256 {value[:16]}"
    if (isinstance(value, list) and len(value) == 2 and type(value[0]) is float
            and isinstance(value[1], str) and value[1].startswith(("0x", "-0x"))):
        return f"{value[0]!r} ({value[1]})"
    if isinstance(value, list):
        return "[" + ", ".join(describe_value(item) for item in value[:8]) + (", ..." if len(value) > 8 else "") + "]"
    text = json.dumps(value, allow_nan=False)
    return text if len(text) <= 160 else text[:157] + "..."


def raw_changes(before: Any, after: Any, path: str = "", limit: int = 24) -> List[str]:
    """Leaf-level before -> after lines between two raw values (dict keys / list indices)."""
    lines: List[str] = []

    def walk(b: Any, a: Any, where: str) -> None:
        if len(lines) >= limit or b == a and type(b) is type(a):
            return
        if isinstance(b, dict) and isinstance(a, dict):
            for k in list(b) + [k for k in a if k not in b]:
                walk(b.get(k, "<absent>"), a.get(k, "<absent>"), f"{where}.{k}" if where else str(k))
        elif isinstance(b, list) and isinstance(a, list) and len(b) == len(a):
            for i, (x, y) in enumerate(zip(b, a)):
                walk(x, y, f"{where}[{i}]")
        else:
            lines.append(f"{where or '<value>'}: {describe_value(b)} -> {describe_value(a)}")

    walk(before, after, path)
    if len(lines) >= limit:
        lines.append("... (more raw changes)")
    return lines


def drift_records(golden: Dict[str, Any], outcome: Dict[str, Any], keys: List[str]) -> List[Dict[str, Any]]:
    """Machine-readable drift report: before/after observation and, when recorded, raw values."""
    expected, actual = golden.get("observations", {}), outcome["observations"]
    raw_before, raw_after = golden.get("rawValues", {}), outcome.get("rawValues", {})
    records = []
    for key in keys:
        record: Dict[str, Any] = {"key": key, "before": expected.get(key, "<missing>"),
                                  "after": actual.get(key, "<missing>")}
        if key in raw_before or key in raw_after:
            record["rawBefore"] = raw_before.get(key, "<not recorded>")
            record["rawAfter"] = raw_after.get(key, "<not recorded>")
            record["rawChanges"] = raw_changes(record["rawBefore"], record["rawAfter"])
        records.append(record)
    return records


def drift_lines(records: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for record in records:
        lines.append(f"{record['key']}: {describe_value(record['before'])} -> {describe_value(record['after'])}")
        lines.extend(f"    raw {line}" for line in record.get("rawChanges", []))
    return lines


def evaluate_drift(case: Case, outcome: Dict[str, Any], entries: List[DriftEntry]) -> Dict[str, Any]:
    """Apply the --expect-drift entries for one checked case.

    Returns {"status": PASS|DRIFT|FAIL, "problems": [...], "drift": [records]}. Without an
    entry for the case this is the plain check. With entries, only observation diffs that an
    entry matches and that are not protected may drift; implementation, pin and golden
    problems always fail; an entry that matches no drifted observation is stale. The error
    rule (error_rule_problem) comes first and no entry overrides it; removals, new errors,
    changed errors and recoveries pass only by an entry naming that exact key.
    """
    mine = [entry for entry in entries if entry.case_id == case.id]
    if not mine:
        return {"status": "FAIL" if outcome["problems"] else "PASS", "problems": list(outcome["problems"]),
                "drift": []}
    if "observationDiffs" not in outcome:  # missing or wrong golden: nothing was compared
        return {"status": "FAIL", "problems": list(outcome["problems"]), "drift": []}
    golden = outcome["golden"]
    problems = list(outcome["implementationProblems"])
    allowed: List[str] = []
    for key in diff_keys(golden["observations"], outcome["observations"]):
        before = golden["observations"].get(key, _ABSENT)
        after = outcome["observations"].get(key, _ABSENT)
        # Raw each() items retain their status; comparing just the digest would hide failures.
        error_before = golden.get("rawValues", {}).get(key, before)
        error_after = outcome.get("rawValues", {}).get(key, after)
        error_problem = error_rule_problem(key, error_before, error_after)
        if error_problem is not None:
            problems.append(error_problem)
            continue
        exact = any(entry.pattern == key for entry in mine)
        if after is _ABSENT and not exact:
            problems.append(f"removed {key}: a removal is allowed only by an entry naming this exact key")
            continue
        if (error_items(key, error_before) or error_items(key, error_after)) and not exact:
            problems.append(f"changed {key}: a recorded error that changes is allowed only by an entry naming "
                            "this exact key")
            continue
        if key not in golden["observations"]:
            # A first appearance (the golden never recorded this key) is not a drift of a recorded value. An
            # ordinary key is allowed by any matching entry (a new artifact frame under a glob); a key of a
            # protected class (reference numerics, identity) is allowed only by an entry naming it exactly, and an
            # honesty key never (P7b gate: the G2 replay claim fixture.strippedResultEqualExceptMaterialIdentity is
            # new on this tree and protected by fixture.* from then on).
            # The honesty test comes first and is made directly on HONESTY_PATTERNS: in a reference case
            # _protected_reason reports the reference-numerics reason before the honesty one, so a new honesty key
            # under fixture.*, artifact.*, npz.* or *.artifacts* must not pass by its exact entry (final gate).
            if any(fnmatch.fnmatchcase(key, p) for p in HONESTY_PATTERNS):
                problems.append(f"new observation {key}: honesty observation never drifts under --expect-drift")
                continue
            reason = _protected_reason(case.id, key, mine)
            if reason is not None and not any(entry.pattern == key for entry in mine):
                problems.append(f"new observation {key}: allowed only by an entry naming this exact key")
            elif not any(entry.matches(key) for entry in mine):
                problems.append(f"new observation {key}: not named by --expect-drift "
                                f"({', '.join(entry.text for entry in mine)})")
            else:
                allowed.append(key)
            continue
        reason = _protected_reason(case.id, key, mine)
        if reason is not None:
            problems.append(f"changed {key}: {reason}")
        elif not any(entry.matches(key) for entry in mine):
            problems.append(f"changed {key}: not named by --expect-drift "
                            f"({', '.join(entry.text for entry in mine)})")
        else:
            allowed.append(key)
    for entry in mine:
        if not any(entry.matches(key) for key in allowed):
            problems.append(f"stale --expect-drift entry {entry.text}: no allowed observation drifted")
    records = drift_records(golden, outcome, allowed)
    return {"status": "FAIL" if problems else ("DRIFT" if records else "PASS"), "problems": problems,
            "drift": records}


def command_check(args) -> int:
    from lpbf_simulation import implementation_fingerprint
    current, pinned = implementation_fingerprint(), pinned_fingerprint()
    print(f"implementation_fingerprint() = {current}  pinned = {pinned}")
    if args.expect_unpinned:
        print("bump-branch mode (--expect-unpinned): a pin mismatch is a WARNING; observation diffs and "
              "result implementationHash != implementation_fingerprint() still FAIL")
    entries = parse_expect_drift(args.expect_drift)
    cases = selected_cases(args)
    failures = skips = 0
    drifted: List[str] = []
    off_reference = False
    if entries:
        print(f"planned-drift mode (--expect-drift): only {', '.join(e.text for e in entries)} may differ "
              "from the goldens; any other diff, identity or reference-case numerics, an implementation "
              "problem, or an entry without drift FAILS")
        selected = {case.id for case in cases}
        not_run = sorted({e.case_id for e in entries if e.case_id not in selected})
        for name in not_run:
            print(f"FAIL {name}: named in --expect-drift but not selected (add --slow or --case {name})")
        failures += len(not_run)
    for case in cases:
        outcome = check_case(case, Path(args.work_root), args.expect_unpinned,
                             args.allow_environment_mismatch)
        if outcome["skipped"] is not None:
            skips += 1
            print(f"SKIP {case.id} [{case.group}] NOT VERIFIED: {outcome['skipped']}")
            continue
        verdict = evaluate_drift(case, outcome, entries)
        problems, status = verdict["problems"], verdict["status"]
        lines = drift_lines(verdict["drift"])
        golden = outcome["golden"] or {}
        recorded = golden.get("recordedImplementationHash")
        suffix = (f" (implementationHash differs from the recording {str(recorded)[:12]}: bump)"
                  if recorded not in (None, current) and not problems else "")
        if status == "DRIFT":
            suffix += f" ({len(verdict['drift'])} observation(s) drifted, allowed by --expect-drift)"
        print(f"{status} {case.id} [{case.group}] {len(outcome['observations'])} observations, "
              f"{outcome['elapsed_s']:.1f} s{suffix}")
        for warning in outcome["warnings"]:
            print(f"    WARNING {warning}")
        for problem in problems[:40]:
            print(f"    {problem}")
        if len(problems) > 40:
            print(f"    ... {len(problems) - 40} more")
        for line in lines:
            print(f"    DRIFT {line}")
        if status == "DRIFT":
            drifted.append(case.id)
        off_reference |= bool(outcome.get("comparedDespiteEnvironment"))
        failures += status == "FAIL"
    if failures:
        print(f"RESULT: FAIL ({failures} case(s))" + (f", {skips} skipped" if skips else ""))
        return 1
    if skips:
        # A skipped case proves nothing: exit 3 so a gate never mistakes it for a pass.
        print(f"RESULT: INCOMPLETE ({skips} case(s) skipped, not verified)")
        return 3
    if drifted and off_reference:
        # A drift report from another environment is a diagnostic, never bump evidence.
        print(f"RESULT: DIAGNOSTIC (planned drift in {', '.join(drifted)} compared off the reference "
              "environment; not evidence)")
        return 3
    print("RESULT: PASS" + (f" (planned drift in {', '.join(drifted)})" if drifted else ""))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--record", action="store_true", help="write goldens at the pinned implementation")
    mode.add_argument("--check", action="store_true", help="compare the current implementation with the goldens")
    mode.add_argument("--list", action="store_true", help="list cases")
    parser.add_argument("--case", action="append", help="case id (repeatable); default: all non-slow cases")
    parser.add_argument("--slow", action="store_true", help="include slow cases (G2 bare plate, ~106 s)")
    parser.add_argument("--force", action="store_true", help="overwrite existing goldens when recording")
    parser.add_argument("--twice", action="store_true", help="record: run twice and require identical observations")
    parser.add_argument("--work-root", default=str(DEFAULT_WORK_ROOT), help="scratch root for artifacts")
    parser.add_argument("--allow-environment-mismatch", action="store_true",
                        help="check: compare even when environment() differs from the recording "
                             "(diagnostics only; a PASS there is not the reference-machine proof)")
    parser.add_argument("--expect-unpinned", action="store_true",
                        help="check: bump-branch mode (B1-B5), a fingerprint != pin mismatch is only a warning")
    parser.add_argument("--expect-drift", action="append", metavar="CASE[:KEY_GLOB][,...]",
                        help="check: planned-drift allowlist; only these cases (or, with :KEY_GLOB, only "
                             "these observations) may differ from their goldens, reported as DRIFT with "
                             "before -> after values; any other diff fails, identity digests and "
                             "reference-case numerics stay protected, a value that turns into an error "
                             "never passes, removals need exact keys, and an entry without drift fails; "
                             "g1/g2/g4 accept only CASE:KEY_GLOB entries")
    args = parser.parse_args(argv)
    if args.expect_drift and not args.check:
        parser.error("--expect-drift is only valid with --check")
    if args.list:
        for case in CASES:
            print(f"{case.id:40s} {case.group:4s} {'slow' if case.slow else 'fast'}  {case.description}")
        print("\nNOT COVERED by these goldens:")
        for gap in NOT_COVERED:
            print(f"  - {gap}")
        return 0
    if args.record:
        return command_record(args)
    return command_check(args)


if __name__ == "__main__":
    sys.exit(main())
