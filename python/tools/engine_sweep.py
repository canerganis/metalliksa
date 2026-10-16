"""Read-only served-engine inventory; never import this tool from a manifest.

Each timed child calls the real Python function in-process (no HTTP, IPC daemon,
queue submission or served CLI). Children are serial, single-threaded and disposable.
Only the requested JSON output is durable; solver artifacts live in a temporary dir.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "python"
ALLOYS = ("Ti-6Al-4V", "AlSi10Mg", "IN718", "316L", "IN625")
IDS = dict(zip(ALLOYS, ("ti6al4v", "alsi10mg", "in718", "ss316l", "in625")))
NAMES = dict(zip(ALLOYS, ("Ti-6Al-4V", "AlSi10Mg", "Inconel 718", "316L Stainless Steel", "Inconel 625")))
# Fresh shared specimen defaults, not Python CLI defaults. IN625 has no shared
# preset: retain the fresh IN718 process vector and substitute identity only.
VECTORS = dict(zip(ALLOYS, ((240, 1200, 150), (350, 1300, 160), (280, 940, 200), (200, 850, 80), (280, 940, 200))))
COMPOSITIONS = {
    "Ti-6Al-4V": dict(Ti=89.2, Al=6.2, V=4.1, Fe=.25, O=.13, C=.05),
    "AlSi10Mg": dict(Al=89.5, Si=9.8, Mg=.45, Fe=.20, Mn=.05),
    "IN718": dict(Ni=52.5, Cr=19., Fe=18.5, Nb=5.15, Mo=3.05, Ti=.95, Al=.55, C=.04, Co=.35),
    "316L": dict(Fe=65.5, Cr=17.5, Ni=12., Mo=2.5, Mn=1.8, Si=.6, C=.02),
}
BAD_STATUSES = {"unavailable", "failed", "partial", "not-requested", "not_requested", "not-evaluated"}
FORBIDDEN = ("leis2021", "hyer2020", "aboulkhair2016", "ruckh2025", "gong2014", "ullah", "wimmer2020")


def operation(id, engine, target, screen, route, *, alloy=True, skip=None):
    return dict(id=id, engine=engine, target=target, screen=screen, route=route, alloy=alloy, skip=skip)


def inventory():
    """Audited against routes, bridge, RPC table and module contracts at ec14298d."""
    op = operation
    result = [
        op("calphad-minimize", "CALPHAD", "calphad_solver:compute_multi_component_equilibrium", "CALPHADMultiComponentStudio / phase-diagram", "/api/python/calphad-minimize (alias /api/calphad/minimize)"),
        op("calphad-databases", "CALPHAD", "calphad_solver:list_available_databases", "CALPHADMultiComponentStudio", "/api/python/calphad-databases (alias /api/calphad/databases)", alloy=False),
        op("lpbf-thermal-solver", "Melt pool", "lpbf_thermal_solver:calculate_meltpool_physics", "MeltPool3DCrossSectionLab / 3d-distortion-lab", "/api/python/lpbf-thermal-solver"),
        op("stl-slicer-build-time", "Slicer", "stl_slicer_build_time_solver:solve_slicer", "BasicSTLSlicerLab", "/api/python/stl-slicer-build-time"),
        op("lpbf-bayesian-optimize", "Bayesian optimizer", "lpbf_bayesian_optimizer:_run_from_payload", "LpbfOptimizerSearchPanel", "/api/python/lpbf-bayesian-optimize"),
        op("lpbf-calibrated-meltpool", "Calibrated melt pool", "lpbf_calibrated_meltpool:run", "CalibratedMeltpoolPanel / MeltPool3DCrossSectionLab", "/api/python/lpbf-calibrated-meltpool"),
        op("lpbf-process-window", "Process window", "lpbf_process_window:run_process_window", "LpbfProcessWindowMap / optimizer", "/api/python/lpbf-process-window", skip="MEASURED_ROWS: _overlay calls public-dataset / NIST Table 4 loaders; no overlay-off request switch"),
        op("lpbf-gr-solidification", "G/R solidification", "lpbf_gr_solidification:run_gr_solidification", "GrSolidificationMapCard / optimizer", "/api/python/lpbf-gr-solidification"),
        op("lpbf-machine-calibrated-meltpool", "Machine calibration", "lpbf_machine_calibrated_meltpool:run", "CalibratedMeltpoolPanel / useMachineDepth", "/api/python/lpbf-machine-calibrated-meltpool"),
        op("lpbf-machine-calibration-status", "Machine calibration", "lpbf_machine_calibrated_meltpool:status", "CalibratedMeltpoolPanel machine selector", "/api/python/lpbf-machine-calibration/status", alloy=False),
        op("lpbf-research-models", "P8 research", "lpbf_research_models:run", "ResearchModelPanel / melt-pool and build-job hosts", "/api/python/lpbf-research-models"),
        op("xrd-deconvolve", "XRD", "xrd_peak_deconvolution:deconvolve_peak_roi / solve_williamson_hall", "No mounted caller; service method deconvolveXRD only", "/api/python/xrd-deconvolve", alloy=False, skip="NO_UI_DEFAULT: requires user ROI points/peaks; no mounted caller or default spectrum; no synthetic spectrum invented"),
        op("solidification-microstructure", "Microstructure", "lpbf_worker_rpc:_rpc_solidification_microstructure", "SolidificationMicrostructureLab", "/api/python/lpbf-solidification-microstructure"),
        op("keyhole-raytracing", "Keyhole optics", "lpbf_keyhole_raytracing:compute_keyhole_raytracing", "KeyholeRaytracingLab", "/api/python/lpbf-keyhole-raytracing", alloy=False),
        op("estimate", "Job estimate", "lpbf_worker_rpc:_estimate", "LpbfEngineeringSimulation", "/api/lpbf/estimate"),
        op("submit", "Transient thermal", "lpbf_simulation:run", "LpbfEngineeringSimulation (standard/reference CPU)", "/api/lpbf/jobs"),
        op("submit:build-job", "Build job", "lpbf_build_job_solver:solve_lpbf_build_job", "IndustrialLPBFDecisionLab / Build rail", "/api/lpbf/jobs jobType=build-job"),
        op("submit:in625-bareplate-field", "IN625 bounded field", "lpbf_worker:_run_in625_bareplate_job", "In625BareplatePanel", "/api/lpbf/jobs jobType=in625-bareplate-field", alloy=False),
        op("submit:gpu-thermal-pilot", "GPU pilot", "lpbf_gpu_thermal:run_queued_pilot / lpbf_gpu_warp_pilot:run_queued_warp_pilot", "GpuThermalPilotPanel", "/api/lpbf/jobs jobType=gpu-thermal-pilot", skip="GPU_FORBIDDEN: Torch/Warp CUDA execution"),
    ]
    for id, target, route, reason in (
        ("capabilities", "lpbf_worker:_capabilities_response", "GET /api/lpbf/capabilities", "GPU_PROBE: capabilities probes GPU/OpenFOAM inventory; no solver output"),
        ("submit-repeat", "Queue.submit(execution_scope=repeat)", "POST /api/lpbf/jobs/repeat", "LIFECYCLE: same physics as submit; would write queue/archive identity"),
        ("get", "Queue.get", "GET /api/lpbf/jobs/:id", "LIFECYCLE: needs existing job id; no independent physics"),
        ("cancel", "Queue.cancel", "DELETE /api/lpbf/jobs/:id", "LIFECYCLE: mutates an existing job"),
        ("artifact", "Queue.artifact", "GET /api/lpbf/jobs/:id/artifacts/:name", "LIFECYCLE: needs existing job artifact"),
        ("archive-capture", "Queue.archive_capture", "LpbfRunArchiveService -> captureForArchive", "ARCHIVE: existing job/source binding; no independent physics"),
        ("nist-comparison", "lpbf_nist_in718_comparison", "POST /api/lpbf/runs/:runId/nist-comparison (+ restored alias)", "MEASURED_ROWS: exact archived Table 4 measurement binding"),
        ("proxy-campaign-validation", "lpbf_nist_proxy_campaign:validate_proxy_campaign", "POST /api/lpbf/runs/proxy-campaigns[/preview]", "MEASURED_ROWS: existing run/source observations; no default archive"),
        ("proxy-section-rederive", "lpbf_nist_proxy_sections:rederive_rectangular_corridor_sections", "archive/campaign validation -> server/lpbfProxyCampaignBinding.ts", "ARCHIVE: needs captured NPZ bytes/result; no default artifact"),
    ):
        result.append(op(id, "Infrastructure / archive", target, "LpbfEngineeringSimulation / LpbfRunArchivePanel", route, alloy=False, skip=reason))
    return result


def payload(op, alloy=None, variant="default"):
    a = alloy or "IN718"
    p, v, t = VECTORS[a]
    common = dict(material=NAMES[a], laserPower_W=p, scanSpeed_mm_s=v, beamDiameter_um=80,
                  preheatTemp_C=t, layerThickness_um=40, hatchSpacing_um=100, laserWavelength="IR_1064nm")
    id = op["id"]
    if id == "lpbf-thermal-solver":
        return dict(common, heatSource="goldak", sulfur_ppm=15)
    if id == "calphad-minimize":
        if a not in COMPOSITIONS:
            return None  # No IN625 UI composition: do not invent a nominal chemistry.
        lo, hi, step = (600, 1750, 25) if a == "Ti-6Al-4V" else (400, 750, 10) if a == "AlSi10Mg" else (500, 1550, 25)
        return dict(name=a, elements=COMPOSITIONS[a], literatureAlloyId=IDS[a] if a == "IN718" else None,
                    unit="wt_pct", tMin=lo, tMax=hi, tStep=step,
                    adaptiveGrid=False, boundaryRefinement=False, minRefineStep=.5, scheil=False)
    if id == "lpbf-bayesian-optimize":
        return dict(alloyId=IDS[a], paramBounds=dict(laserPower_W=[100., 500.], scanSpeed_mms=[200., 2000.], hatch_um=[60., 200.], layer_um=[20., 80.]),
                    nIterations=20, nWarmup=5, seed=42, beamDiameter_um=80, preheatTemp_C=80)
    if id == "lpbf-gr-solidification":
        # Only IN718 has populated UI axes. Reuse those axes for other identities
        # as explicit coverage probes, not as invented alloy-specific defaults.
        return dict(mode="map", alloyId=IDS[a], beamDiameter_um=80, layer_um=40, hatch_um=110, preheatTemp_C=80,
                    powers=[60 + i*65 for i in range(7)], speeds=[275 + i*(1225/6) for i in range(7)])
    if id == "lpbf-research-models":
        process = {k: common[k] for k in ("material", "laserPower_W", "scanSpeed_mm_s", "beamDiameter_um", "preheatTemp_C", "laserWavelength")}
        process["absorptionModel"] = "flat-plate"
        answer = dict(schemaVersion="p8-research-request-v1", supersedeKey="p8-research:melt-pool", clientRequestId="engine-sweep",
                      stage=variant, process=process, propertyContext=dict(kind="nominal"), sender="research-panel",
                      researchOptions=dict(marangoni={}, surfaceBalance={}, ranges=dict(marangoni={}, surfaceBalance={})))
        if variant == "band":
            answer["timeBudgetMs"] = 1500
        return answer
    if id == "solidification-microstructure":
        return dict(params=dict(materialName=NAMES[a], power_W=p, speed_mm_s=v, beamDiameter_um=80,
                                preheat_C=t, layerThickness_um=40, hatch_um=100, heatSource="rosenthal"))
    if id in ("estimate", "submit"):
        return dict(material=NAMES[a], power_W=p, speed_mm_s=v, beamDiameter_um=80, preheat_C=t,
                    layer_um=40, hatch_um=100, mode="standard", backend="reference", strategy="stripe",
                    stripeWidth_um=500, islandSize_um=200, mesh_um=20, maxDt_s=1e-6, tracks=1, layers=1,
                    trackLength_um=600, dwell_s=.0002, cooling_s=.0005, packingFraction=.55,
                    powderConductivityRatio=.12, convection_W_m2K=20, timeout_s=300,
                    scanAngle_deg=0, layerRotation_deg=67, study="none")
    if id == "submit:build-job":
        return dict(common, alloyId=IDS[a], thermalMaterial=NAMES[a], slicerMaterial=NAMES[a], preset="nozzle",
                    customTriangles=None, cadAssetName="", processSeed=42, scanStrategy="stripe", stripeWidth_mm=5,
                    scanRotation_deg=67, hatchDwell_ms=0, inclineAngle_deg=0, enableUq=False, uqSamples=96, includeAmbench=False)
    if id == "stl-slicer-build-time":
        common.pop("scanSpeed_mm_s")
        return dict(common, scanSpeed_mms=v, preset="nozzle", recoatTimePerLayer_s=9.5, hatchStrategy="meander_67",
                    contourSkinPasses=2, customTriangles=None, cadAssetName="")
    if id == "lpbf-calibrated-meltpool":
        return dict(common, calibrationMode=True)
    if id == "keyhole-raytracing":
        return dict(nx=64, ny=64, dx=240e-6/63, dy=240e-6/63, power_W=280, beam_radius_um=40,
                    keyhole_depth_um=120, base_absorption=.35, max_bounces=5, num_rays=4096, seed=0, device="cpu", ui_ray_limit=150)
    if id == "submit:in625-bareplate-field":
        return dict(jobType="in625-bareplate-field", backend="cpu", config=dict(shapeXYZ=[16, 12, 6], cellSizeM=[.00025]*3,
                    initialTemperatureK=298.15, dtS=1e-5, steps=10, absorbedPowerW=20, spotSigmaM=.0004,
                    scanStartXM=.001, scanYM=.0015, scanVelocityXMS=0))
    return common if op["alloy"] else {}


def findings(value, path="$", inherited=()):
    """Every null or unavailable-status leaf, plus unavailable containers with no scalar value.

    One record per JSON pointer/path; nearest explicit reason travels to children.
    No code is fabricated when a served response has only prose or no explanation.
    """
    out = []
    if isinstance(value, dict):
        reasons = {k: v for k, v in value.items() if v is not None and ("reason" in k.lower() or k in ("unavailableKind", "errorKind", "code", "codes", "missingInputs"))}
        context = (*inherited, {"path": path, **reasons}) if reasons else inherited
        bad = any(isinstance(v, str) and (v.lower() in BAD_STATUSES or v.lower().startswith("unavailable-"))
                  for k, v in value.items() if "status" in k.lower() or k == "state")
        bad = bad or value.get("available") is False
        if bad:
            out.append(dict(path=path, kind="status-container", status=value.get("status", value.get("state", "unavailable")), reasons=list(context)))
        for k, v in value.items():
            out.extend(findings(v, path+"."+k, context))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            out.extend(findings(v, f"{path}[{i}]", inherited))
    elif value is None or (isinstance(value, str) and (value.lower() in BAD_STATUSES or value.lower().startswith("unavailable-"))):
        out.append(dict(path=path, kind="null" if value is None else "status-leaf", value=value, reasons=list(inherited)))
    return out


class SweepBlocked(RuntimeError):
    pass


def install_guards():
    """Fail closed on external-data, measured loaders, networking and child executables."""
    blocked_modules = {"lpbf_public_datasets", "lpbf_meltpool_literature"}
    def audit(event, args):
        if event == "import" and str(args[0]).split(".")[0] in blocked_modules:
            raise SweepBlocked("measured-row module import blocked: " + str(args[0]))
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            name = "/" + os.fsdecode(args[0]).lower().replace("\\", "/").lstrip("/")
            if ".orchestra/external-data" in name or any(x in name for x in FORBIDDEN):
                raise SweepBlocked("forbidden data path: " + name)
        if event in ("socket.connect", "socket.bind", "socket.getaddrinfo", "subprocess.Popen", "os.system"):
            raise SweepBlocked("external operation blocked: " + event)
    sys.addaudithook(audit)


def invoke(op, data, folder):
    module_name, function = op["target"].split(":", 1)
    module = importlib.import_module(module_name)
    fn = getattr(module, function)
    id = op["id"]
    if id in ("calphad-databases", "lpbf-machine-calibration-status"):
        return fn()
    if id == "calphad-minimize":
        result = fn(name=data["name"], elements=data["elements"], unit=data["unit"],
                    t_min_c=data["tMin"], t_max_c=data["tMax"], t_step_c=data["tStep"],
                    adaptive_grid=False, boundary_refinement=False, min_refine_step_c=.5, scheil=False)
        module.attach_literature_solidification(result, data["literatureAlloyId"])
        constants = importlib.import_module("physical_constants")
        result["provenance"] = dict(constantsVersion=constants.CONSTANTS_VERSION,
                                    gasConstantR_J_molK=module.GAS_CONSTANT_R,
                                    atomicWeightsSource=constants.CIAAW_SOURCE,
                                    **module._domain_data_provenance())
        return result
    if id == "lpbf-thermal-solver":
        return fn(data["material"], data["laserPower_W"], data["scanSpeed_mm_s"], data["beamDiameter_um"],
                  data["preheatTemp_C"], data["layerThickness_um"], data["hatchSpacing_um"], data["laserWavelength"],
                  heat_source=data["heatSource"], sulfur_ppm=data["sulfur_ppm"])
    if id == "lpbf-research-models":
        answer, code = fn(json.dumps(data), module.default_dependencies())
        return json.loads(answer)
    if id == "solidification-microstructure":
        return fn(dict(payload=data))
    if id == "estimate":
        return fn(dict(payload=data))
    if id == "submit":
        return fn(data, artifact_dir=Path(folder), capabilities={})
    if id == "submit:in625-bareplate-field":
        return fn(data, Path(folder))
    return fn(data)


def child(request):
    sys.path.insert(0, str(PYTHON))
    install_guards()
    # Warp is allowed on CPU; prohibit CUDA discovery/compilation as well as use.
    try:
        import warp
        warp.config.enable_cuda = False
        warp.config.kernel_cache_dir = str(Path(request["folder"]) / "warp-cache")
    except ImportError:
        pass
    started = time.perf_counter()
    log = io.StringIO()
    try:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            answer = invoke(request["operation"], request["input"], request["folder"])
        error = None
        if isinstance(answer, dict) and (answer.get("success") is False or answer.get("error")):
            error = dict(className="ReturnedError", message=str(answer.get("error", answer.get("reasonCode", answer.get("reason", answer.get("errorKind", "success=false"))))))
        result = dict(outcome="error" if error else "ok", error=error, findings=findings(answer),
                      topLevelStatus=answer.get("status") if isinstance(answer, dict) else None,
                      outputKeys=list(answer) if isinstance(answer, dict) else [],
                      errorKind=answer.get("errorKind") if isinstance(answer, dict) else None)
    except Exception as exc:
        envelope = exc.envelope() if callable(getattr(exc, "envelope", None)) else None
        result = dict(outcome="error", error=dict(className=type(exc).__name__, message=str(exc)),
                      findings=findings(envelope) if envelope else [])
    result.update(wall_s=round(time.perf_counter()-started, 6), log=log.getvalue()[-12000:])
    Path(request["result"]).write_text(json.dumps(result, ensure_ascii=False, default=str), encoding="utf-8")


def run_call(op, alloy, variant, timeout):
    data = payload(op, alloy, variant)
    record = dict(operation=op["id"], alloy=alloy, variant=variant, input=data)
    reason = op["skip"]
    if data is None:
        reason = "NO_UI_DEFAULT: IN625 has no UI composition preset; chemistry not invented"
    if reason:
        return dict(record, outcome="skipped", skipReason=reason, wall_s=0, findings=[])
    env = dict(os.environ)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        env[name] = "1"
    env.update(CUDA_VISIBLE_DEVICES="", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    with tempfile.TemporaryDirectory(prefix="metalliksa-engine-sweep-") as folder:
        result = str(Path(folder)/"result.json")
        request = dict(operation=op, input=data, folder=folder, result=result)
        started = time.perf_counter()
        try:
            done = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--child"],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding="utf-8", env=env, cwd=folder,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                stdout, stderr = done.communicate(json.dumps(request), timeout=timeout)
            except subprocess.TimeoutExpired:
                # Windows venv python.exe is a redirector; killing only its PID
                # leaves the actual interpreter alive, holding pipes and CPU.
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(done.pid), "/T", "/F"], capture_output=True, check=False)
                else:
                    done.kill()
                done.communicate()
                raise
            if Path(result).exists():
                record.update(json.loads(Path(result).read_text(encoding="utf-8")))
            else:
                record.update(outcome="error", error=dict(className="ChildProcessError", message=stderr[-4000:]), findings=[])
        except subprocess.TimeoutExpired:
            record.update(outcome="error", error=dict(className="TimeoutError", message=f"per-call budget {timeout:g}s exceeded"), findings=[])
        record["processWall_s"] = round(time.perf_counter()-started, 6)
        record.setdefault("wall_s", record["processWall_s"])
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    if args.child:
        child(json.load(sys.stdin))
        return
    if args.timeout <= 0 or args.output is None:
        parser.error("positive --timeout and --output are required")
    catalog = inventory()
    records = []
    for op in catalog:
        if args.only and op["id"] not in args.only:
            continue
        for alloy in ALLOYS if op["alloy"] else (None,):
            for variant in ("describe", "nominal", "band") if op["id"] == "lpbf-research-models" else ("default",):
                result = run_call(op, alloy, variant, args.timeout)
                records.append(result)
                print(f"{op['id']} {alloy or '-'} {variant}: {result['outcome']} {result['wall_s']:.3f}s ({len(result['findings'])} findings)", flush=True)
    checkpoint = args.output.with_suffix(args.output.suffix + ".tmp")
    checkpoint.write_text(json.dumps(dict(schemaVersion=1, interpreter=sys.executable, timeout_s=args.timeout,
        catalog=catalog, records=records), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    checkpoint.replace(args.output)


if __name__ == "__main__":
    main()
