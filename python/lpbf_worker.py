"""Persistent JSON-lines RPC worker, SQLite queue and isolated cancellable job processes.

Normally launched inside WSL by the Node bridge. No browser-supplied shell commands.
"""
import hashlib
import base64
import ctypes
import json
import math
import os
from pathlib import Path
import re
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from lpbf_material_registry import catalog
from lpbf_simulation import run, validate, fingerprint
from lpbf_request_errors import (LpbfRequestRefusal, validate_thermal_request,
                                 validate_build_job_request, run_thermal_request,
                                 refusal_frame, execution_refusal as _execution_refusal)
from lpbf_openfoam import BINARY
from lpbf_evidence import enforce_thermal_balances
from lpbf_run_capture import capture_run
import lpbf_worker_rpc

ROOT = Path(os.environ.get("METALLIKSA_JOB_ROOT", str(Path(__file__).resolve().parents[1]/".lpbf-jobs")))
DEFAULT_JOB_TIMEOUT_S = 300.0
IN625_BAREPLATE_JOB_TYPE = "in625-bareplate-field"
IN625_BAREPLATE_MODEL_ID = "in625-bareplate-enthalpy-conduction-v1"
IN625_BAREPLATE_SOLVER_ID = "in625-bareplate-field-v1"
IN625_BAREPLATE_SOLVER_REVISION = "1"
IN625_BAREPLATE_ARTIFACT = "in625-temperature-field-f64le.bin"
IN625_BAREPLATE_MAX_CELLS = 1_000_000
IN625_BAREPLATE_MAX_CELL_STEPS = 2_000_000
IN625_BAREPLATE_MAX_STEPS = 25_000


def _is_allowed_artifact_name(name):
    return isinstance(name, str) and (
        name in ("temperature-slice.svg", "phase-slice.svg", "thermal-history.csv",
                 "field-series.json", "field-coordinates.bin", IN625_BAREPLATE_ARTIFACT)
        or re.fullmatch(r"field-frame-[0-9]{3}\.bin", name) is not None
    )


def _is_partial_artifact_candidate(name):
    # peak-field.npz is an execution intermediate used to render completed previews;
    # it is retained as local diagnostic output but is never directly downloadable.
    return _is_allowed_artifact_name(name) or name == "peak-field.npz"


def _validate_in625_bareplate_request(raw):
    """Strictly normalize the worker API payload for the bounded IN625 solver."""
    from in625_bareplate_field import BareplateConfig, _validate

    if not isinstance(raw, dict) or raw.get("jobType") != IN625_BAREPLATE_JOB_TYPE:
        raise ValueError("Invalid IN625 bareplate job type")
    if set(raw) - {"jobType", "backend", "config"}:
        raise ValueError("Unknown IN625 bareplate request fields")
    backend = raw.get("backend")
    if backend != "cpu" and (not isinstance(backend, str) or not re.fullmatch(r"cuda:[0-9]+", backend)):
        raise ValueError("backend must be 'cpu' or an explicit CUDA device such as 'cuda:0'")
    config_raw = raw.get("config", {})
    if not isinstance(config_raw, dict):
        raise ValueError("config must be an object")
    defaults = BareplateConfig()
    aliases = {
        "shape_xyz": "shapeXYZ", "cell_size_m": "cellSizeM",
        "initial_temperature_K": "initialTemperatureK", "dt_s": "dtS",
        "steps": "steps", "absorbed_power_W": "absorbedPowerW",
        "spot_sigma_m": "spotSigmaM", "scan_start_x_m": "scanStartXM",
        "scan_y_m": "scanYM", "scan_velocity_x_m_s": "scanVelocityXMS",
    }
    # The worker-facing API is camelCase; reject accidental snake_case aliases.
    allowed = set(aliases.values())
    if set(config_raw) - allowed:
        raise ValueError("Unknown IN625 bareplate config fields")
    config_values = {}
    for field_name, api_name in aliases.items():
        value = config_raw.get(api_name, getattr(defaults, field_name))
        if field_name in ("shape_xyz", "cell_size_m"):
            if not isinstance(value, (list, tuple)) or len(value) != 3:
                raise ValueError(f"{api_name} must contain exactly three values")
            if field_name == "shape_xyz":
                if any(type(v) is not int or v < 2 for v in value):
                    raise ValueError("shapeXYZ must contain integers >= 2")
                config_values[field_name] = tuple(value)
            else:
                if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in value):
                    raise ValueError("cellSizeM must contain positive finite numbers")
                config_values[field_name] = tuple(float(v) for v in value)
        else:
            if field_name == "steps":
                if type(value) is not int or value < 1:
                    raise ValueError("steps must be a positive integer")
            elif type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"{api_name} must be a finite number")
            config_values[field_name] = value
    config = BareplateConfig(**config_values)
    cells = math.prod(config.shape_xyz)
    if cells > IN625_BAREPLATE_MAX_CELLS:
        raise ValueError(f"IN625 bareplate cell count exceeds {IN625_BAREPLATE_MAX_CELLS}")
    if config.steps > IN625_BAREPLATE_MAX_STEPS:
        raise ValueError(f"IN625 bareplate step count exceeds {IN625_BAREPLATE_MAX_STEPS}")
    if cells * config.steps > IN625_BAREPLATE_MAX_CELL_STEPS:
        raise ValueError(f"IN625 bareplate work exceeds {IN625_BAREPLATE_MAX_CELL_STEPS} cell-steps")
    _validate(config)
    normalized_config = {api_name: (list(config_values[field_name]) if field_name in ("shape_xyz", "cell_size_m")
                                     else config_values[field_name])
                         for field_name, api_name in aliases.items()}
    request = {"jobType": IN625_BAREPLATE_JOB_TYPE, "backend": backend, "config": normalized_config}
    return request, config


def _check_in625_bareplate_cuda_device(device):
    """Preflight the exact requested CUDA device; never substitute a backend."""
    try:
        import torch
    except ImportError as error:
        raise RuntimeError("PyTorch is required for the explicit CUDA path") from error
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; explicit CUDA path cannot run")
    index = int(device.split(":", 1)[1])
    if index >= torch.cuda.device_count():
        raise ValueError(f"requested CUDA device index is unavailable: {device}")


def _write_deterministic_bareplate_field(path, result):
    """Write final temperature as deterministic little-endian float64 raw bytes."""
    import numpy as np
    temperature = result.temperature_K
    if hasattr(temperature, "detach"):
        temperature = temperature.detach().to(device="cpu").numpy()
    np.asarray(temperature, dtype="<f8", order="C").tofile(path)


def _bareplate_result_to_json(raw, config, output, folder):
    """Adapt BareplateResult into a bounded, finite JSON result and archive artifact."""
    import numpy as np
    from in625_thermal_material import in625_lpbf_thermal_snapshot

    snapshot = in625_lpbf_thermal_snapshot()
    def array(value):
        if hasattr(value, "detach"):
            value = value.detach().to(device="cpu").numpy()
        result = np.asarray(value, dtype=np.float64)
        if not np.isfinite(result).all():
            raise ValueError("IN625 bareplate solver returned nonfinite values")
        return result

    temperature = array(output.temperature_K)
    enthalpy = array(output.specific_enthalpy_J_kg)
    times = array(output.time_s)
    total = array(output.total_enthalpy_J)
    peaks = array(output.peak_temperature_K)
    residuals = array(output.energy_residual_J)
    if temperature.shape != (config.shape_xyz[2], config.shape_xyz[1], config.shape_xyz[0]):
        raise ValueError("IN625 bareplate final field shape mismatch")
    if enthalpy.shape != temperature.shape or any(v.ndim != 1 or len(v) != config.steps
                                                    for v in (times, total, peaks, residuals)):
        raise ValueError("IN625 bareplate history shape mismatch")
    if not (np.diff(times) > 0).all() or (temperature < 273.15).any() or (temperature > 1623.15).any():
        raise ValueError("IN625 bareplate field or time history is outside its model bounds")

    artifact_path = Path(folder) / IN625_BAREPLATE_ARTIFACT
    _write_deterministic_bareplate_field(artifact_path, output)
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), allow_nan=False)
    input_hash = hashlib.sha256(canonical.encode()).hexdigest()
    material = snapshot
    device = raw["backend"]
    device_evidence = {"selected": device, "thermalEvolution": device, "noCpuFallback": True}
    if device.startswith("cuda:"):
        import torch
        cuda_index = int(device.split(":", 1)[1])
        actual = torch.device(device)
        torch.cuda.synchronize(actual)
        properties = torch.cuda.get_device_properties(actual)
        device_evidence.update(name=properties.name, index=cuda_index,
                               computeCapability=list(torch.cuda.get_device_capability(actual)),
                               torch=torch.__version__, cudaRuntime=torch.version.cuda,
                               synchronizedAfterSolve=True)
    else:
        device_evidence.update(name="NumPy CPU", index=None, synchronizedAfterSolve=True)

    initial_total = float(total[0] - config.absorbed_power_W * config.dt_s)
    input_energy = float(config.absorbed_power_W * config.dt_s * config.steps)
    stored_energy = float(total[-1] - initial_total)
    energy_relative_error = abs(stored_energy-input_energy) / max(input_energy, 1e-30)
    if energy_relative_error > 0.01:
        raise ValueError(f"IN625 bareplate energy closure failed ({energy_relative_error:.6g})")
    digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    return {
        "schemaVersion": 1,
        "jobType": IN625_BAREPLATE_JOB_TYPE,
        "runKind": "bounded-material-screening",
        "requestedMode": "screening",
        "effectiveMode": "screening",
        "fallbackReason": None,
        "settings": raw,
        "material": material,
        "solver": {"id": IN625_BAREPLATE_SOLVER_ID, "modelId": IN625_BAREPLATE_MODEL_ID,
                   "revision": IN625_BAREPLATE_SOLVER_REVISION, "actualBackend": device,
                   "device": device, "dtype": "float64"},
        "validationStatus": "unvalidated-literature-model-screening",
        "productionReady": False,
        "confidence": "low",
        "label": "IN625 bare-substrate conduction screening",
        "modelScope": "3D bounded enthalpy conduction on bare substrate; all faces adiabatic; no powder, melt pool, absorptivity, vapor, flow, or free-surface physics",
        "metrics": {"cells": int(temperature.size), "peakTemperature_K": float(temperature.max()),
                    "finalTime_s": float(times[-1]), "finalEnthalpy_J": float(total[-1]),
                    "energyResidual_J": float(residuals[-1]),
                    "minimumSourceCaptureFraction": float(output.metadata["sourceCaptureFractionMinimum"])},
        "energyHistory": [{"time_s": float(t), "totalEnthalpy_J": float(e),
                           "peakTemperature_K": float(p), "energyResidual_J": float(r)}
                          for t, e, p, r in zip(times, total, peaks, residuals)],
        "energyBalance": {"input_J": input_energy, "losses_J": 0.0, "stored_J": stored_energy,
                          "relativeError": energy_relative_error,
                          "scope": "adiabatic bareplate enthalpy accounting; not melt-pool or interface closure"},
        "field": {"artifact": IN625_BAREPLATE_ARTIFACT, "shapeXYZ": list(config.shape_xyz),
                  "dtype": "float64", "encoding": "little-endian",
                  "byteOrder": "little-endian", "arrayOrder": "z,y,x", "sha256": digest,
                  "scope": "final cell-centered temperature field only; no interface interpolation"},
        "numericalDiagnostics": {"sourceCaptureFractionMinimum": float(output.metadata["sourceCaptureFractionMinimum"]),
                                 "temperatureBounds_K": [273.15, 1623.15],
                                 "density_kg_m3": output.metadata["density_kg_m3"],
                                 "densityBasis": output.metadata["densityBasis"]},
        "provenance": {"inputSha256": input_hash,
                       "implementationIdentity": {"modelId": IN625_BAREPLATE_MODEL_ID,
                                                   "solverRevision": IN625_BAREPLATE_SOLVER_REVISION,
                                                   "materialRevisionSha256": snapshot["materialRevisionSha256"],
                                                   "backend": device, "device": device},
                       "deviceEvidence": device_evidence},
        "artifacts": [],
        "assumptions": ["Constant 8440 kg/m^3 supplier-bulletin density assumption; not lot-matched.",
                        "Source input is absorbed power in W; no optical absorptivity is inferred.",
                        "Constitutive law is bounded to 273.15..1623.15 K and remains unvalidated literature-model screening."],
    }


def _enforce_bareplate_result(result, settings, folder=None):
    """Verify queue/cache identity and the custom bareplate result contract."""
    from in625_thermal_material import in625_lpbf_thermal_snapshot

    if (not isinstance(result, dict) or not isinstance(settings, dict)
            or result.get("jobType") != IN625_BAREPLATE_JOB_TYPE
            or result.get("settings") != settings or result.get("validationStatus") != "unvalidated-literature-model-screening"
            or result.get("productionReady") is not False):
        raise ValueError("Invalid IN625 bareplate result identity")
    backend = settings.get("backend")
    material = result.get("material")
    solver = result.get("solver")
    provenance = result.get("provenance")
    field = result.get("field")
    if not isinstance(solver, dict) or not isinstance(provenance, dict) or not isinstance(field, dict):
        raise ValueError("IN625 bareplate result is missing solver/provenance/field identity")
    identity = provenance.get("implementationIdentity")
    expected = in625_lpbf_thermal_snapshot()
    if (material != expected or solver.get("id") != IN625_BAREPLATE_SOLVER_ID
            or solver.get("modelId") != IN625_BAREPLATE_MODEL_ID
            or solver.get("revision") != IN625_BAREPLATE_SOLVER_REVISION
            or solver.get("actualBackend") != backend
            or identity != {"modelId": IN625_BAREPLATE_MODEL_ID,
                            "solverRevision": IN625_BAREPLATE_SOLVER_REVISION,
                            "materialRevisionSha256": expected["materialRevisionSha256"],
                            "backend": backend, "device": backend}
            or field.get("artifact") != IN625_BAREPLATE_ARTIFACT):
        raise ValueError("IN625 bareplate model/material/backend identity mismatch")
    energy = result.get("energyBalance", {})
    if not isinstance(energy, dict):
        raise ValueError("Invalid IN625 bareplate energy accounting")
    values = [energy.get(name) for name in ("input_J", "losses_J", "stored_J", "relativeError")]
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
        raise ValueError("Invalid IN625 bareplate energy accounting")
    if values[1] != 0 or values[3] < 0 or values[3] > 0.01:
        raise ValueError("IN625 bareplate energy closure failed")
    if folder is not None:
        refs = result.get("artifacts")
        if (not isinstance(refs, list) or any(not isinstance(item, dict)
                                              or set(item) != {"path", "size_bytes", "sha256"}
                                              for item in refs)):
            raise ValueError("IN625 bareplate artifact manifest missing")
        entry = next((item for item in refs if item.get("path") == IN625_BAREPLATE_ARTIFACT), None)
        path = Path(folder) / IN625_BAREPLATE_ARTIFACT
        if (not entry or not path.is_file() or path.stat().st_size != entry.get("size_bytes")
                or hashlib.sha256(path.read_bytes()).hexdigest() != entry.get("sha256")
                or entry.get("sha256") != field.get("sha256")):
            raise ValueError("IN625 bareplate field artifact integrity failed")


def _run_in625_bareplate_job(raw, folder):
    from in625_bareplate_field import run_cpu, run_cuda
    request, config = _validate_in625_bareplate_request(raw)
    output = run_cpu(config) if request["backend"] == "cpu" else run_cuda(config, request["backend"])
    result = _bareplate_result_to_json(request, config, output, folder)
    from lpbf_evidence import write_artifacts
    write_artifacts(result, folder)
    _enforce_bareplate_result(result, request, folder)
    return result


def _archive_run_kind(job_type, result=None):
    if job_type == "gpu-thermal-pilot":
        contract = result.get("gpuRunContract") if isinstance(result, dict) else None
        fields = result.get("gpuFieldArtifacts") if isinstance(result, dict) else None
        capture = contract.get("capture") if isinstance(contract, dict) else None
        if (isinstance(contract, dict) and contract.get("runKind") == job_type
                and isinstance(fields, dict)
                and isinstance(capture, dict)
                and ((contract.get("schemaVersion") == 1
                      and capture.get("contractStatus") == "gpu-pilot-v1-bound")
                     or (contract.get("schemaVersion") == 2
                         and capture.get("contractStatus") == "gpu-pilot-v2-warp-bound"
                         and capture.get("engineId") == "warp"))):
            return "gpu-thermal-pilot"
        return None  # Legacy pilot output remains view-only.
    if job_type == IN625_BAREPLATE_JOB_TYPE:
        return "bounded-material-screening"
    if job_type == "build-job":
        return "build-screening"
    if isinstance(result, dict):
        settings = result.get("settings")
        core_contract = result.get("coreContract")
        physics = result.get("resolvedPhysics")
        if not isinstance(physics, dict) and isinstance(core_contract, dict):
            physics = core_contract.get("resolvedPhysics")
        if (isinstance(settings, dict) and settings.get("mode") == "screening"
                and isinstance(physics, dict) and physics.get("transient") is False):
            return "analytical-screening"
    return "transient-thermal"


def gpu_device_inventories():
    """Return per-engine CUDA devices from the runtimes that execute each pilot."""
    inventories = {}
    try:
        import torch
        devices = []
        if torch.cuda.is_available():
            for ordinal in range(int(torch.cuda.device_count())):
                props = torch.cuda.get_device_properties(ordinal)
                devices.append(dict(
                    ordinal=ordinal, device=f"cuda:{ordinal}", name=str(props.name),
                    computeCapability=list(torch.cuda.get_device_capability(ordinal)),
                    memoryBytes=int(props.total_memory),
                ))
        inventories["torch"] = dict(runtimeAvailable=bool(devices), devices=devices)
    except Exception as exc:
        inventories["torch"] = dict(runtimeAvailable=False, devices=[], unavailableReason=str(exc)[:240])
    try:
        import warp as wp
        devices = []
        for device in wp.get_cuda_devices():
            arch = int(device.arch)
            devices.append(dict(
                ordinal=int(device.ordinal), device=str(device.alias), name=str(device.name),
                computeCapability=[arch // 10, arch % 10], memoryBytes=int(device.total_memory),
            ))
        inventories["warp"] = dict(runtimeAvailable=bool(devices), devices=devices)
    except Exception as exc:
        inventories["warp"] = dict(runtimeAvailable=False, devices=[], unavailableReason=str(exc)[:240])
    return inventories


def capabilities():
    foam = Path("/opt/openfoam14/etc/bashrc")
    version = None
    if foam.exists():
        try:
            r = subprocess.run(["bash", "-lc", "source /opt/openfoam14/etc/bashrc; foamVersion"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and "OpenFOAM-14" in r.stdout+r.stderr:
                version = "OpenFOAM-14"
        except (OSError, subprocess.TimeoutExpired):
            pass
    cuda = dict(selection="backend=cuda:N", availability="checked-on-submit", cpuAlternative="backend=cpu",
                evidenceScope="IN625 bareplate bounded enthalpy-conduction screening only")
    try:
        import torch
        cuda.update(runtimeAvailable=bool(torch.cuda.is_available()), deviceCount=int(torch.cuda.device_count()),
                    torchVersion=str(torch.__version__), cudaRuntime=torch.version.cuda)
    except ImportError:
        cuda.update(runtimeAvailable=False, deviceCount=0, torchVersion=None, cudaRuntime=None)
    return dict(openfoamVersion=version, openfoamThermal=bool(version and BINARY.is_file()),
                binaryHash=hashlib.sha256(BINARY.read_bytes()).hexdigest() if BINARY.is_file() else None,
                freeSurfaceSolver=bool(version and (Path(__file__).parent/"openfoam/bin/metalliksaMeltPoolFoam").is_file()), platform=sys.platform,
                thermalSolver=True, materials=catalog(),
                gpuDevices=gpu_device_inventories(),
                cudaThermalPilot=dict(selection="jobType=gpu-thermal-pilot; backend=cuda:N",
                    availability="checked-on-submit", cpuAlternative="backend=reference",
                    evidenceScope="same-model numerical parity only"),
                in625BareplateField=dict(jobType=IN625_BAREPLATE_JOB_TYPE, cpuAvailable=True,
                    cuda=cuda, alloyId="in625", modelId=IN625_BAREPLATE_MODEL_ID,
                    validationStatus="unvalidated-literature-model-screening", productionReady=False,
                    maximumCells=IN625_BAREPLATE_MAX_CELLS, maximumCellSteps=IN625_BAREPLATE_MAX_CELL_STEPS),
                limitation="No qualified LPBF free-surface CFD solver. High-Fidelity requests return explicitly labelled analytical screening.")


class _WindowsJobChild:
    """Windows child held in a kill-on-close Job Object for its whole lifetime."""
    def __init__(self, process_handle, job_handle, thread_handle, pid):
        self._process_handle, self._job_handle, self._thread_handle = process_handle, job_handle, thread_handle
        self.pid, self.returncode = pid, None

    def _close_handles(self):
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.CloseHandle.argtypes = [ctypes.c_void_p]
        api.CloseHandle.restype = ctypes.c_int
        # Keep the process handle until last so an intermediate close error can
        # be retried without losing the only handle that proves process exit.
        for name in ("_job_handle", "_thread_handle", "_process_handle"):
            handle = getattr(self, name)
            if handle:
                if not api.CloseHandle(handle):
                    raise ctypes.WinError(ctypes.get_last_error())
                setattr(self, name, None)

    def resume(self):
        if not self._thread_handle:
            return
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.ResumeThread.argtypes = [ctypes.c_void_p]
        api.ResumeThread.restype = ctypes.c_ulong
        if api.ResumeThread(self._thread_handle) == 0xFFFFFFFF:
            error = ctypes.get_last_error()
            api.TerminateJobObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            api.TerminateJobObject(self._job_handle, 1)
            api.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            api.WaitForSingleObject.restype = ctypes.c_ulong
            if api.WaitForSingleObject(self._process_handle, 5000) == 0x102:
                api.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
                api.TerminateProcess(self._process_handle, 1)
                api.WaitForSingleObject(self._process_handle, 5000)
            if api.WaitForSingleObject(self._process_handle, 0) == 0:
                self.poll()  # Reap and close every owned handle before surfacing setup failure.
            raise ctypes.WinError(error)
        api.CloseHandle.argtypes = [ctypes.c_void_p]
        if not api.CloseHandle(self._thread_handle):
            raise ctypes.WinError(ctypes.get_last_error())
        self._thread_handle = None

    def poll(self):
        if self.returncode is not None:
            return self.returncode
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        api.WaitForSingleObject.restype = ctypes.c_ulong
        api.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        api.GetExitCodeProcess.restype = ctypes.c_int
        state = api.WaitForSingleObject(self._process_handle, 0)
        if state == 0x102:
            return None
        if state != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        code = ctypes.c_ulong()
        if not api.GetExitCodeProcess(self._process_handle, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        returncode = ctypes.c_int32(code.value).value
        self._close_handles()
        self.returncode = returncode
        return returncode

    def wait(self, timeout=None):
        if self.returncode is not None:
            return self.returncode
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        api.WaitForSingleObject.restype = ctypes.c_ulong
        ms = 0xFFFFFFFF if timeout is None else max(0, min(0xFFFFFFFE, int(timeout * 1000)))
        state = api.WaitForSingleObject(self._process_handle, ms)
        if state == 0x102:
            raise subprocess.TimeoutExpired(str(self.pid), timeout)
        if state != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        return self.poll()

    def kill(self):
        if self.poll() is not None:
            return
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.TerminateJobObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        api.TerminateJobObject.restype = ctypes.c_int
        if not api.TerminateJobObject(self._job_handle, 1):
            error = ctypes.get_last_error()
            if error == 5 and self.poll() is not None:
                return
            raise ctypes.WinError(error)


def _spawn_windows_job_child(args, log):
    """Create suspended and atomically assign via JOB_LIST before returning."""
    if os.name != "nt":
        raise RuntimeError("Windows Job Object launcher is only available on Windows")
    from ctypes import wintypes

    class IoCounters(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class BasicLimit(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class ExtendedLimit(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BasicLimit), ("IoInfo", IoCounters),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    class StartupInfo(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR),
                    ("lpTitle", wintypes.LPWSTR), ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                    ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                    ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
                    ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                    ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)), ("hStdInput", wintypes.HANDLE),
                    ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]

    class StartupInfoEx(ctypes.Structure):
        _fields_ = [("StartupInfo", StartupInfo), ("lpAttributeList", ctypes.c_void_p)]

    class ProcessInfo(ctypes.Structure):
        _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                    ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]

    class SecurityAttributes(ctypes.Structure):
        _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                    ("bInheritHandle", wintypes.BOOL)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
        wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(StartupInfo),
        ctypes.POINTER(ProcessInfo)]
    kernel.CreateProcessW.restype = wintypes.BOOL
    kernel.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel.ResumeThread.restype = wintypes.DWORD
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateJobObject.restype = wintypes.BOOL
    kernel.DuplicateHandle.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE,
        ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.DuplicateHandle.restype = wintypes.BOOL
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(SecurityAttributes), wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                                          ctypes.POINTER(ctypes.c_size_t)]
    kernel.InitializeProcThreadAttributeList.restype = wintypes.BOOL
    kernel.UpdateProcThreadAttribute.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t,
        ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
    kernel.UpdateProcThreadAttribute.restype = wintypes.BOOL
    kernel.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
    kernel.DeleteProcThreadAttributeList.restype = None
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD

    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    process = thread = stdin_handle = attr_list = log_handle = None
    attr_initialized = False
    attr_storage = None
    try:
        limits = ExtendedLimit()
        limits.BasicLimitInformation.LimitFlags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())
        security = SecurityAttributes(ctypes.sizeof(SecurityAttributes), None, True)
        stdin_handle = kernel.CreateFileW("NUL", 0x80000000, 3, ctypes.byref(security), 3, 0x80, None)
        if ctypes.cast(stdin_handle, ctypes.c_void_p).value == ctypes.c_void_p(-1).value:
            stdin_handle = None
            raise ctypes.WinError(ctypes.get_last_error())
        import msvcrt
        current = ctypes.c_void_p(-1)
        duplicate = wintypes.HANDLE()
        if not kernel.DuplicateHandle(current, wintypes.HANDLE(msvcrt.get_osfhandle(log.fileno())),
                                      current, ctypes.byref(duplicate), 0, True, 0x2):
            raise ctypes.WinError(ctypes.get_last_error())
        log_handle = duplicate
        startup_ex = StartupInfoEx()
        startup = startup_ex.StartupInfo
        startup.cb, startup.dwFlags = ctypes.sizeof(startup_ex), 0x100  # STARTF_USESTDHANDLES
        startup.hStdInput, startup.hStdOutput, startup.hStdError = stdin_handle, log_handle, log_handle
        required = ctypes.c_size_t()
        kernel.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(required))
        if not required.value:
            raise ctypes.WinError(ctypes.get_last_error())
        attr_storage = ctypes.create_string_buffer(required.value)
        attr_list = ctypes.cast(attr_storage, ctypes.c_void_p)
        if not kernel.InitializeProcThreadAttributeList(attr_list, 2, 0, ctypes.byref(required)):
            raise ctypes.WinError(ctypes.get_last_error())
        attr_initialized = True
        startup_ex.lpAttributeList = attr_list
        job_list = (wintypes.HANDLE * 1)(job)
        # PROC_THREAD_ATTRIBUTE_JOB_LIST assigns the Job atomically as the
        # suspended process is created, removing a parent-death gap before assignment.
        if not kernel.UpdateProcThreadAttribute(attr_list, 0, 0x0002000D, ctypes.byref(job_list),
                                                ctypes.sizeof(job_list), None, None):
            raise ctypes.WinError(ctypes.get_last_error())
        inherited_handles = (wintypes.HANDLE * 2)(stdin_handle, log_handle)
        # Restrict inheritance to exactly the standard streams required by the child.
        if not kernel.UpdateProcThreadAttribute(attr_list, 0, 0x00020002,
                                                ctypes.byref(inherited_handles),
                                                ctypes.sizeof(inherited_handles), None, None):
            raise ctypes.WinError(ctypes.get_last_error())
        info = ProcessInfo()
        command = ctypes.create_unicode_buffer(subprocess.list2cmdline([str(arg) for arg in args]))
        if not kernel.CreateProcessW(str(args[0]), command, None, None, True, 0x00080004, None, None,
                                     ctypes.cast(ctypes.byref(startup_ex), ctypes.POINTER(StartupInfo)),
                                     ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        process, thread = info.hProcess, info.hThread
        child = _WindowsJobChild(process, job, thread, int(info.dwProcessId))
        process = job = thread = None
        return child
    finally:
        if attr_initialized:
            kernel.DeleteProcThreadAttributeList(attr_list)
        for handle in (thread, process, job, stdin_handle, log_handle):
            if handle:
                kernel.CloseHandle(handle)


def _spawn_execution_child(command, log):
    """Platform seam for a solver child; Windows requires Job Object ownership."""
    if os.name == "nt":
        return _spawn_windows_job_child(command, log)
    return subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True)


class Queue:
    def __init__(self, root=ROOT, start=True):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root/"queue.sqlite"
        self.caps = capabilities()
        self.lock = threading.RLock()
        self.children = {}
        self.pending_child_failures = {}
        self.closed = threading.Event()
        self.thread = None
        with self.connect() as c:
            c.execute("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, cache_key TEXT, status TEXT, progress REAL, log TEXT, error TEXT, created REAL)")
            c.execute("UPDATE jobs SET status='failed',error='Worker restarted during execution' WHERE status='running'")
        if start:
            self.thread = threading.Thread(target=self.work, daemon=True)
            self.thread.start()

    def close(self):
        self.closed.set()
        if self.thread:
            self.thread.join(timeout=6)

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db, timeout=10)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def update(self, job, **values):
        with self.connect() as c:
            c.execute("UPDATE jobs SET "+",".join(k+"=?" for k in values)+" WHERE id=?", [*values.values(), job])

    def finish_running(self, job, **values):
        # Atomic terminal transition: a cancellation winning the race stays cancelled.
        with self.lock, self.connect() as c:
            c.execute("UPDATE jobs SET "+",".join(k+"=?" for k in values)+" WHERE id=? AND status='running'",
                      [*values.values(), job])

    def terminate_child(self, job, child):
        """Kill and reap a registered child once; concurrent cancel/poll paths converge here."""
        with self.lock:
            if self.children.get(job) is not child:
                return
            reaped = False

            def kill_or_confirm_exit():
                try:
                    child.kill()
                except OSError as error:
                    code = getattr(error, "winerror", None) or getattr(error, "errno", None)
                    if os.name != "nt" or code != 5 or child.poll() is None:
                        raise

            try:
                if child.poll() is None:
                    if os.name == "nt":
                        kill_or_confirm_exit()
                    else:
                        try:
                            os.killpg(child.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            kill_or_confirm_exit()
                wait = getattr(child, "wait", None)
                if not callable(wait):
                    raise RuntimeError("Execution child cannot be waited and reaped")
                try:
                    wait(timeout=5)
                except subprocess.TimeoutExpired:
                    kill_or_confirm_exit()
                    try:
                        wait(timeout=5)
                    except subprocess.TimeoutExpired as error:
                        raise RuntimeError("Execution child did not exit within the termination deadline") from error
                if child.poll() is None:
                    raise RuntimeError("Execution child is still running after termination")
                reaped = True
            finally:
                if reaped and self.children.get(job) is child:
                    self.children.pop(job, None)

    def _record_execution_failure(self, job, error):
        child = self.children.get(job)
        if child is None:
            self.finish_running(job, status="failed", error=str(error))
            return
        try:
            self.terminate_child(job, child)
        except Exception as cleanup_error:
            # A terminal record must not outlive an unconfirmed child. Keep its
            # handles and registry entry so the worker can retry bounded cleanup.
            self.pending_child_failures[job] = (child, f"{error}; child cleanup pending: {cleanup_error}")
            return
        self.finish_running(job, status="failed", error=str(error))

    def _retry_pending_child_failures(self):
        for job, (child, error) in list(self.pending_child_failures.items()):
            try:
                self.terminate_child(job, child)
            except Exception:
                continue
            self.pending_child_failures.pop(job, None)
            self.finish_running(job, status="failed", error=error)

    def get(self, job):
        if not isinstance(job, str) or len(job) != 32 or any(ch not in "0123456789abcdef" for ch in job):
            raise ValueError("Invalid job id")
        with self.connect() as c:
            row = c.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
        if row is None:
            raise ValueError("Job not found")
        out = dict(row)
        settings = json.loads((self.root/job/"input.json").read_text())
        out["requestSummary"] = {k:settings.get(k) for k in ("jobType","mode","backend","material")}
        if settings.get("jobType") == "gpu-thermal-pilot" and settings.get("executionEngine") == "warp":
            out["requestSummary"]["executionEngine"] = "warp"
        if settings.get("jobType") == IN625_BAREPLATE_JOB_TYPE:
            out["requestSummary"] = {k:settings.get(k) for k in ("jobType", "backend", "config")}
        if out["status"] == "completed":
            try:
                out["result"] = json.loads((self.root/job/"result.json").read_text())
                if settings.get("jobType") == "gpu-thermal-pilot":
                    if settings.get("executionEngine") == "warp":
                        from lpbf_gpu_warp_pilot import enforce_gpu_warp_pilot_result
                        enforce_result = enforce_gpu_warp_pilot_result
                    else:
                        from lpbf_gpu_thermal import enforce_gpu_pilot_result
                        enforce_result = enforce_gpu_pilot_result
                    from lpbf_core_contract import _verify_material_revision
                    material = out["result"].get("material") if isinstance(out["result"], dict) else None
                    if not isinstance(material, dict) or "materialRevisionSha256" not in material:
                        raise ValueError("CUDA pilot material revision snapshot is required")
                    _verify_material_revision(material)
                    enforce_result(out["result"], artifact_dir=self.root/job)
                    # The pilot guard binds a result to its own settings;
                    # also bind it to the separately persisted submitted job.
                    submitted_hash = hashlib.sha256(
                        json.dumps(settings, sort_keys=True, allow_nan=False).encode()).hexdigest()
                    if out["result"]["provenance"]["inputHash"] != submitted_hash:
                        raise ValueError("CUDA pilot result does not match submitted settings")
                elif settings.get("jobType") == IN625_BAREPLATE_JOB_TYPE:
                    _enforce_bareplate_result(out["result"], settings, self.root/job)
                else:
                    enforce_thermal_balances(out["result"])
            except (OSError, ValueError) as error:
                out.pop("result", None)
                out.update(status="failed", error=f"Saved result integrity failed: {error}")
                self.update(job, status=out["status"], error=out["error"])
        if out["status"] in ("failed", "cancelled", "timed_out"):
            if out["status"] == "failed":
                refused = _execution_refusal(out["log"])
                if refused is not None:
                    out.update(error=refused["message"], errorKind="validation", refusal=refused)
            out["partialArtifacts"] = self._partial_artifact_summary(self.root/job)
            if out["partialArtifacts"] is None:
                del out["partialArtifacts"]
        return out

    @staticmethod
    def _partial_artifact_summary(folder):
        """Report retained terminal-job outputs as incomplete, without exposing bytes."""
        count = 0
        total_bytes = 0
        try:
            is_junction = getattr(folder, "is_junction", None)
            if (folder.is_symlink() or (callable(is_junction) and is_junction())
                    or not folder.is_dir()):
                return {"status": "inventory-unavailable"}
            with os.scandir(folder) as entries:
                for entry in entries:
                    if not _is_partial_artifact_candidate(entry.name):
                        continue
                    if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                        return {"status": "inventory-unavailable"}
                    size = entry.stat(follow_symlinks=False).st_size
                    if type(size) is not int or size < 0:
                        return {"status": "inventory-unavailable"}
                    count += 1
                    total_bytes += size
        except OSError:
            return {"status": "inventory-unavailable"}
        if count == 0:
            return None
        return {"status": "retained-unverified", "fileCount": count,
                "totalBytes": total_bytes}

    def purge_unverified_artifacts(self, job=None, older_than_seconds=0, dry_run=False):
        """Safely clean up partial, unverified artifact files from terminal non-completed jobs.

        Completed jobs and running/queued jobs are never modified.
        If a child process is active for a job, cleanup is refused.
        """
        with self.lock:
            if job is not None:
                if not isinstance(job, str) or len(job) != 32 or any(ch not in "0123456789abcdef" for ch in job):
                    raise ValueError("Invalid job id")
                if job in self.children:
                    raise RuntimeError("Cannot purge artifacts while child execution is active")
                with self.connect() as c:
                    row = c.execute("SELECT status, created FROM jobs WHERE id=?", (job,)).fetchone()
                if row is None:
                    raise ValueError("Job not found")
                if row["status"] not in ("failed", "cancelled", "timed_out"):
                    raise ValueError(f"Cannot purge artifacts from job with status '{row['status']}'")
                job_ids = [job]
            else:
                with self.connect() as c:
                    rows = c.execute(
                        "SELECT id FROM jobs WHERE status IN ('failed', 'cancelled', 'timed_out')"
                    ).fetchall()
                job_ids = [r["id"] for r in rows if r["id"] not in self.children]

            purged_files = 0
            freed_bytes = 0
            purged_jobs = 0
            now = time.time()

            for jid in job_ids:
                folder = self.root / jid
                is_junction = getattr(folder, "is_junction", None)
                if (folder.is_symlink() or (callable(is_junction) and is_junction())
                        or not folder.is_dir()):
                    continue
                job_purged = 0
                try:
                    with os.scandir(folder) as entries:
                        for entry in entries:
                            if not (_is_partial_artifact_candidate(entry.name) or entry.name.endswith(".tmp")):
                                continue
                            if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                                continue
                            stat = entry.stat(follow_symlinks=False)
                            if older_than_seconds > 0 and (now - stat.st_mtime) < older_than_seconds:
                                continue
                            size = stat.st_size
                            if not dry_run:
                                os.unlink(entry.path)
                            purged_files += 1
                            freed_bytes += size
                            job_purged += 1
                except OSError:
                    continue
                if job_purged > 0:
                    purged_jobs += 1

            return {
                "status": "dry-run" if dry_run else "purged",
                "purgedJobs": purged_jobs,
                "purgedFiles": purged_files,
                "freedBytes": freed_bytes,
            }

    def capture(self, job):
        with self.lock:
            state = self.get(job)
            if state['status'] != 'completed':
                raise ValueError('Only completed jobs can be captured')
            return capture_run(self.root/job, job)

    def archive_capture(self, job):
        # Internal RPC only: Node maps this root; HTTP never supplies a path.
        return dict(capture=self.capture(job), root=str(self.root.absolute()), platform=sys.platform)

    def artifact(self, payload):
        state = self.get(payload["id"])
        name = payload.get("name")
        allowed = _is_allowed_artifact_name(name)
        if state["status"] != "completed" or not allowed:
            raise ValueError("Artifact unavailable")
        entry = next((a for a in state["result"].get("artifacts",[]) if a["path"] == name),None)
        if not entry or entry["size_bytes"] > 8_000_000: raise ValueError("Artifact unavailable or too large")
        path = self.root/payload["id"]/name
        if path.stat().st_size != entry["size_bytes"]: raise ValueError("Artifact size mismatch")
        content = path.read_bytes()
        if len(content) != entry["size_bytes"] or hashlib.sha256(content).hexdigest() != entry["sha256"]: raise ValueError("Artifact integrity failed")
        return dict(content=base64.b64encode(content).decode(),type="image/svg+xml" if name.endswith(".svg") else "application/octet-stream" if name.endswith(".bin") else "application/json" if name.endswith(".json") else "text/csv")

    def submit(self, raw, *, execution_scope="deduplicated"):
        if execution_scope not in ("deduplicated", "repeat"):
            raise ValueError("Invalid execution scope")
        job_type = raw.get("jobType")
        if job_type == "build-job":
            validate_build_job_request(raw)
            p, m = raw, raw
        elif job_type == "gpu-thermal-pilot":
            if raw.get("executionEngine") == "warp":
                from lpbf_gpu_warp_pilot import validate_warp_pilot_request
                p, m = validate_warp_pilot_request(raw)
            elif "executionEngine" in raw:
                raise ValueError("Unsupported GPU pilot execution engine")
            else:
                from lpbf_gpu_thermal import validate_pilot_request
                p, m = validate_pilot_request(raw)
        elif job_type == IN625_BAREPLATE_JOB_TYPE:
            p, _ = _validate_in625_bareplate_request(raw)
            if p["backend"].startswith("cuda:"):
                _check_in625_bareplate_cuda_device(p["backend"])
            from in625_thermal_material import in625_lpbf_thermal_snapshot
            m = in625_lpbf_thermal_snapshot()
        else:
            p, m = validate_thermal_request(raw)
        # A rebuilt binary must invalidate a long-lived worker's cache identity.
        self.caps["binaryHash"] = hashlib.sha256(BINARY.read_bytes()).hexdigest() if BINARY.is_file() else None
        self.caps["openfoamThermal"] = bool(self.caps["openfoamVersion"] and self.caps["binaryHash"])
        if job_type == IN625_BAREPLATE_JOB_TYPE:
            identity = {"request": p, "materialRevisionSha256": m["materialRevisionSha256"],
                        "modelId": IN625_BAREPLATE_MODEL_ID,
                        "solverRevision": IN625_BAREPLATE_SOLVER_REVISION,
                        "backend": p["backend"], "device": p["backend"], "capabilities": self.caps}
            key_payload = json.dumps(identity, sort_keys=True, separators=(",", ":"), allow_nan=False)
        else:
            key_payload = fingerprint(p, m)+json.dumps(self.caps, sort_keys=True)
        key = hashlib.sha256(key_payload.encode()).hexdigest()
        with self.lock, self.connect() as c:
            row = None if execution_scope == "repeat" else c.execute(
                "SELECT id FROM jobs WHERE cache_key=? AND status IN ('queued','running','completed') ORDER BY created DESC LIMIT 1", (key,)).fetchone()
            if row:
                try:
                    cached = self.get(row["id"])
                    if cached["status"] not in ("queued", "running", "completed"):
                        raise ValueError("Cached result no longer usable")
                    if cached["status"] == "completed":
                        for artifact in cached["result"].get("artifacts", []):
                            folder = (self.root/row["id"]).resolve()
                            path = (folder/artifact["path"]).resolve()
                            if folder not in path.parents:
                                raise ValueError("Cached artifact escapes job directory")
                            if not path.is_file() or path.stat().st_size != artifact["size_bytes"]:
                                raise ValueError("Cached artifact missing or size changed")
                            digest = hashlib.sha256()
                            with path.open("rb") as stream:
                                for chunk in iter(lambda: stream.read(1024*1024), b""): digest.update(chunk)
                            if digest.hexdigest() != artifact["sha256"]:
                                raise ValueError("Cached artifact checksum mismatch")
                    return {**cached, "cacheHit": cached["status"] == "completed",
                            "deduplicated": cached["status"] != "completed"}
                except (OSError, ValueError, KeyError):
                    c.execute("UPDATE jobs SET status='failed',error='Cached result/artifacts unavailable or corrupt' WHERE id=?", (row["id"],))
            if c.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0] >= 16:
                raise ValueError("Queue full (16 jobs)")
            job = uuid.uuid4().hex
            folder = self.root/job; folder.mkdir()
            (folder/"input.json").write_text(json.dumps(p, allow_nan=False))
            (folder/"capabilities.json").write_text(json.dumps(self.caps))
            c.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?)", (job, key, "queued", 0., "", None, time.time()))
        return {**self.get(job), "cacheHit": False}

    def cancel(self, job):
        with self.lock:
            state = self.get(job)
            if state["status"] in ("queued", "running"):
                child = self.children.get(job)
                if child is not None:
                    # Keep the persisted state non-terminal until the child is
                    # confirmed dead, so concurrent pollers cannot stop early.
                    self.terminate_child(job, child)
                self.update(job, status="cancelled", error="Cancelled by user")
        return self.get(job)

    def work(self):
        while not self.closed.is_set():
            row = None
            try:
                self._retry_pending_child_failures()
                with self.lock, self.connect() as c:
                    row = c.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
                    if row:
                        c.execute("UPDATE jobs SET status='running' WHERE id=?", (row["id"],))
                if not row:
                    time.sleep(.1); continue
                self.execute(row["id"])
            except Exception as e:
                if row:
                    self._record_execution_failure(row["id"], e)
                time.sleep(.1)

    def execute(self, job):
        folder = self.root/job
        params = json.loads((folder/"input.json").read_text())
        timeout_s = params.get("timeout_s", DEFAULT_JOB_TIMEOUT_S)
        with (folder/"progress.log").open("w") as log:
            # Serialize the status check, spawn and registration against cancel().
            # This prevents cancellation from acknowledging while an untracked
            # child is being launched between the two operations.
            with self.lock:
                if self.get(job)["status"] != "running":
                    return
                command = [sys.executable, str(Path(__file__).resolve()), "--execute", str(folder)]
                child = _spawn_execution_child(command, log)
                self.children[job] = child
                if isinstance(child, _WindowsJobChild):
                    try:
                        # The queue owns the Job Object before execution can begin.
                        child.resume()
                    except Exception:
                        self.terminate_child(job, child)
                        raise
            started = time.monotonic()
            try:
                while child.poll() is None:
                    state = self.get(job)["status"]
                    timed_out = time.monotonic()-started > timeout_s
                    if state == "cancelled" or timed_out or self.closed.is_set():
                        self.terminate_child(job, child)
                        if state == "cancelled":
                            pass
                        elif timed_out:
                            self.finish_running(job, status="timed_out", error="Simulation timeout")
                        elif self.closed.is_set():
                            self.finish_running(job, status="failed", error="Worker stopped during execution")
                        return
                    text = (folder/"progress.log").read_text(errors="replace")[-16000:]
                    progress = self.get(job)["progress"]
                    for line in text.splitlines():
                        try:
                            event = json.loads(line)
                            progress = max(progress, min(.99, event.get("progress", 0.)))
                        except (ValueError, AttributeError, TypeError):
                            pass
                    self.update(job, progress=progress, log=text)
                    time.sleep(.15)
                with self.lock:
                    if self.get(job)["status"] == "cancelled":
                        return
                    final_log = (folder/"progress.log").read_text(errors="replace")[-16000:]
                    if time.monotonic()-started > timeout_s or self.closed.is_set():
                        self.finish_running(job, status="timed_out" if not self.closed.is_set() else "failed",
                                            error="Simulation timeout" if not self.closed.is_set() else "Worker stopped during execution", log=final_log)
                        return
                    if child.returncode == 0 and (folder/"result.json").exists():
                        result = json.loads((folder/"result.json").read_text())
                        if params.get("jobType") == "gpu-thermal-pilot":
                            if params.get("executionEngine") == "warp":
                                from lpbf_gpu_warp_pilot import enforce_gpu_warp_pilot_result
                                enforce_gpu_warp_pilot_result(result, artifact_dir=folder)
                            else:
                                from lpbf_gpu_thermal import enforce_gpu_pilot_result
                                enforce_gpu_pilot_result(result, artifact_dir=folder)
                        elif params.get("jobType") == IN625_BAREPLATE_JOB_TYPE:
                            _enforce_bareplate_result(result, params, folder)
                        else:
                            enforce_thermal_balances(result)
                        self.finish_running(job, status="completed", progress=1., log=final_log)
                    else:
                        self.finish_running(job, status="failed", error=_execution_failure_message(final_log, child.returncode), log=final_log)
            finally:
                self.terminate_child(job, child)


def _execution_failure_message(final_log, returncode):
    """Keep diagnostic lines verbatim; omit only typed child progress frames."""
    refused = _execution_refusal(final_log)
    if refused is not None:
        return refused["message"]
    def unique_object(pairs):
        value = dict(pairs)
        if len(value) != len(pairs):
            raise ValueError("Duplicate JSON fields are not a progress frame")
        return value

    retained = []
    for line in final_log.splitlines(keepends=True):
        try:
            event = json.loads(line, object_pairs_hook=unique_object)
            if (isinstance(event, dict) and set(event) == {"progress", "message"}
                    and type(event["progress"]) in (int, float)
                    and 0 <= event["progress"] <= 1 and math.isfinite(event["progress"])
                    and isinstance(event["message"], str)):
                continue
        except (ValueError, TypeError, RecursionError):
            pass
        retained.append(line)
    diagnostic = "".join(retained)
    return diagnostic[-4000:] if diagnostic.strip() else f"Solver exit {returncode}"


def _cpu_run_progress_for(settings, capabilities=None):
    """Track supported CPU candidates without changing automatic dispatch."""
    from lpbf_run_progress import CpuRunProgress, cpu_reference_progress_supported
    if not cpu_reference_progress_supported(settings, capabilities):
        return None
    return CpuRunProgress()


def _cpu_failure_progress_message(error):
    """Format verified counters from the failed solver, never infer them from a log."""
    progress = getattr(error, "progress", None)
    if (not isinstance(progress, dict) or type(progress.get("schemaVersion")) is not int
            or progress.get("schemaVersion") != 1
            or progress.get("scope") != "cpu-reference" or progress.get("stage") != "failed"):
        return None
    count_names = ("acceptedSteps", "attemptedSourceEvaluations", "sourceEvaluationRetries",
                   "attemptedSourceCellSteps", "sourceEvaluationFailures")
    if any(type(progress.get(name)) is not int or not 0 <= progress[name] <= 2**53-1
           for name in count_names):
        return None
    accepted, evaluations = progress["acceptedSteps"], progress["attemptedSourceEvaluations"]
    if (accepted > evaluations or progress["sourceEvaluationRetries"] > evaluations
            or progress["sourceEvaluationFailures"] > evaluations):
        return None
    for name in ("lastAcceptedTime_s", "lastAcceptedSchedulerTime_s"):
        value = progress.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            return None
    dt, cells = progress.get("lastAcceptedDt_s"), progress.get("cells")
    if accepted == 0:
        if dt is not None or progress["lastAcceptedTime_s"] != 0 or progress["lastAcceptedSchedulerTime_s"] != 0:
            return None
    elif (isinstance(dt, bool) or not isinstance(dt, (int, float)) or not math.isfinite(dt)
          or dt <= 0 or dt > progress["lastAcceptedTime_s"] or progress["lastAcceptedSchedulerTime_s"] <= 0):
        return None
    if cells is None:
        if evaluations or progress["attemptedSourceCellSteps"]:
            return None
    elif (type(cells) is not int or cells < 1
          or progress["attemptedSourceCellSteps"] != evaluations*cells):
        return None
    return (f"Last valid CPU state: {accepted} accepted steps at {progress['lastAcceptedTime_s']:.9g} s. "
            f"Source work: {evaluations} source evaluations, {progress['sourceEvaluationRetries']} retries, "
            f"{progress['attemptedSourceCellSteps']} source cell-evaluations "
            "(excludes conduction and other solver work). No completed result.")


def _capabilities_response(queue):
    data = dict(queue.caps)
    data["gpuDevices"] = gpu_device_inventories()
    return data


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--execute":
        folder = Path(sys.argv[2])
        if os.name != "nt":
            parent_pid = os.getppid()
            def monitor_parent():
                while True:
                    time.sleep(.5)
                    if os.getppid() != parent_pid:
                        os.killpg(os.getpgrp(), signal.SIGKILL)
            threading.Thread(target=monitor_parent, daemon=True).start()
        def report(progress, message):
            print(json.dumps(dict(progress=progress, message=message)), flush=True)
        run_progress = None
        try:
            execution_start = time.monotonic()
            input_data = json.loads((folder/"input.json").read_text())
            job_type = input_data.get("jobType")

            if job_type == "gpu-thermal-pilot":
                if input_data.get("executionEngine") == "warp":
                    from lpbf_gpu_warp_pilot import run_queued_warp_pilot
                    result = run_queued_warp_pilot(input_data, artifact_dir=folder)
                else:
                    from lpbf_gpu_thermal import run_queued_pilot
                    result = run_queued_pilot(input_data, artifact_dir=folder)
            elif job_type == IN625_BAREPLATE_JOB_TYPE:
                result = _run_in625_bareplate_job(input_data, folder)
            elif job_type == "build-job":
                from lpbf_build_job_solver import solve_lpbf_build_job
                result = solve_lpbf_build_job(input_data)
                if "provenance" not in result:
                    result["provenance"] = {}
                result["settings"] = input_data
                result["material"] = {
                    "id": result.get("alloyId"),
                    "propertySha256": result.get("materialPropertySha256"),
                }
                from lpbf_evidence import write_artifacts
                write_artifacts(result, folder)
            else:
                execution_capabilities = json.loads((folder/"capabilities.json").read_text())
                run_progress = _cpu_run_progress_for(input_data, execution_capabilities)
                options = {"run_progress": run_progress} if run_progress is not None else {}
                result = run_thermal_request(input_data, report, folder,
                             execution_capabilities, solver=run, **options)

            run_kind = _archive_run_kind(job_type, result)
            if run_kind is not None:
                result["runKind"] = run_kind
            result["provenance"]["runtime_s"] = time.monotonic()-execution_start
            import platform
            import numpy
            result["provenance"]["executionRuntime"] = dict(
                executable=sys.executable, python=platform.python_version(),
                platform=platform.platform(), numpy=numpy.__version__)
            (folder/"result.tmp").write_text(json.dumps(result, allow_nan=False))
            (folder/"result.tmp").replace(folder/"result.json")
        except Exception as e:
            # A valid thermal solve can still fail result audits or artifact writes.
            # Preserve its work counts at the job boundary without publishing a result.
            if run_progress is not None and getattr(e, "progress", None) is None:
                state = run_progress.snapshot()
                if state["cells"] is not None:
                    run_progress.fail(e, failure_stage=(
                        "postprocessing" if state["stage"] == "completed" else None))
            print(str(e), flush=True)
            if isinstance(e, LpbfRequestRefusal):
                print(refusal_frame(e), flush=True)
            detail = _cpu_failure_progress_message(e)
            if detail is not None:
                print(detail, flush=True)
            sys.exit(1)
        return
    ROOT.mkdir(parents=True, exist_ok=True)
    # OS-held lock prevents a second worker from invalidating live running jobs.
    instance_lock = (ROOT/"worker.lock").open("a+b")
    try:
        if os.name == "nt":
            import msvcrt
            instance_lock.seek(0); instance_lock.write(b"0"); instance_lock.flush(); instance_lock.seek(0)
            msvcrt.locking(instance_lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(instance_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Another LPBF worker owns this job root", file=sys.stderr); sys.exit(2)
    queue = Queue()
    for line in sys.stdin:
        request = {}
        try:
            if len(line) > RPC_MAX_LINE_CHARS:
                request = {"id": _leading_request_id(line)}
                raise ValueError(f"RPC payload too large ({len(line)} characters; limit {RPC_MAX_LINE_CHARS})")
            request = json.loads(line)
            method = request["method"]
            data = lpbf_worker_rpc.dispatch(request, queue, _capabilities_response)
            response = dict(id=request["id"], data=data)
        except Exception as e:
            response = rpc_error_response(request, e)
        print(json.dumps(response, allow_nan=False), flush=True)
    queue.close()


RPC_MAX_LINE_CHARS = 1000000
_LEADING_ID = re.compile(r'\s*\{\s*"id"\s*:\s*(-?\d+|"(?:[^"\\]|\\.){0,128}")\s*,')


def _leading_request_id(line):
    """Request id of an RPC line without parsing the whole (oversized) line. The Node bridge serialises
    {id, method, payload} with the id first; anything else yields None."""
    match = _LEADING_ID.match(line[:256])
    return None if match is None else json.loads(match.group(1))


def rpc_error_response(request, error):
    """RPC error reply. A Phase 6a input_validation.ValidationError (e.g. the fatigue
    UNKNOWN_ALLOY) also carries the stdout-style envelope, which the Node bridge maps to
    HTTP 422 like the other migrated solvers. input_validation is looked up in
    sys.modules: such an error can only exist once that module is loaded, so this adds
    no import to the worker."""
    response = dict(id=request.get("id") if isinstance(request, dict) else None, error=str(error))
    if isinstance(error, LpbfRequestRefusal):
        response.update(errorKind="validation", validation=error.envelope())
    validation = sys.modules.get("input_validation")
    if validation is not None and isinstance(error, validation.ValidationError):
        response.update(errorKind="validation", validation=validation.validation_envelope(error))
    return response


if __name__ == "__main__":
    main()


