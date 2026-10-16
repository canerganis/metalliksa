"""RPC dispatch table for the LPBF worker (method name -> handler)."""

from lpbf_evidence import resource_estimate
from lpbf_request_errors import validate_thermal_request as validate
from lpbf_fatigue_fracture import MurakamiFatigueEngine
from lpbf_solidification_microstructure import (
    compute_screening_field_microstructure,
    compute_solidification_microstructure,
)


def _rpc_solidification_microstructure(request):
    # Phase 8
    payload = request["payload"]
    p = payload.get("params", {})
    cfd = payload.get("cfdResult", None)
    if "cfdResult" in payload:
        # Legacy CFD path, only when a cfdResult is supplied (no UI caller does today).
        m = payload.get("material", {})
        return compute_solidification_microstructure(p, m, cfd)
    # Screening-field path: Python (lpbf_thermal_solver) is the authority for every number;
    # material k/liquidus/absorptivity are looked up there, never taken from the payload.
    # Unusable inputs return status "unavailable" with a reason instead of raising.
    return compute_screening_field_microstructure(p)


def _rpc_fatigue_fracture(request):
    # Phase 13
    payload = request["payload"]
    alloy = payload.get("alloyName", "Ti-6Al-4V")
    engine = MurakamiFatigueEngine(alloy)
    sqrt_area = float(payload.get("sqrtArea_um", 45.0))
    location = payload.get("location", "internal")
    r_ratio = float(payload.get("stressRatio_R", -1.0))
    calc_type = payload.get("type", "full")

    fatigue_res = engine.calculate_fatigue_limit(sqrt_area, location, r_ratio)
    kt_curve = engine.generate_kitagawa_takahashi_curve(location, r_ratio, n_points=30)
    paris_res = engine.simulate_paris_crack_growth(
        initial_defect_sqrt_area_um=sqrt_area,
        cyclic_stress_amplitude_MPa=float(payload.get("stressAmplitude_MPa", 220.0)),
        stress_ratio_R=r_ratio,
        location=location,
    )
    data = {
        "fatigue_limit": fatigue_res,
        "kitagawa_takahashi_curve": kt_curve,
        "paris_crack_growth": paris_res
    }
    return data


def _rpc_keyhole_raytracing(request):
    # Phase 26
    from lpbf_keyhole_raytracing import compute_keyhole_raytracing
    data = compute_keyhole_raytracing(request.get("payload", {}))
    return data


# Pure research endpoints: handler(request) -> data.
RESEARCH_HANDLERS = {
    "solidification-microstructure": _rpc_solidification_microstructure,
    "fatigue-fracture": _rpc_fatigue_fracture,
    "keyhole-raytracing": _rpc_keyhole_raytracing,
}


# Methods served by the job queue: handler(queue, request) -> data.
QUEUE_HANDLERS = {
    "submit": lambda queue, request: queue.submit(request["payload"]),
    "submit-repeat": lambda queue, request: queue.submit(request["payload"], execution_scope="repeat"),
    "artifact": lambda queue, request: queue.artifact(request["payload"]),
    "capture": lambda queue, request: queue.capture(request["payload"]),
    "archive-capture": lambda queue, request: queue.archive_capture(request["payload"]),
    "get": lambda queue, request: queue.get(request["payload"]),
    "cancel": lambda queue, request: queue.cancel(request["payload"]),
    "purge-unverified-artifacts": lambda queue, request: _purge_unverified_artifacts(queue, request),
}


def _purge_unverified_artifacts(queue, request):
    payload = request.get("payload", {})
    return queue.purge_unverified_artifacts(
        job=payload.get("job"),
        older_than_seconds=float(payload.get("olderThanSeconds", 0)),
        dry_run=bool(payload.get("dryRun", False))
    )


def _estimate(request):
    p, m = validate(request["payload"])
    return resource_estimate(p, m)


def method_names():
    """Every RPC method name the worker serves."""
    return {"capabilities", "estimate", *QUEUE_HANDLERS, *RESEARCH_HANDLERS}


def dispatch(request, queue, capabilities_handler):
    """Resolve request["method"] and return its data; unknown methods raise ValueError."""
    method = request["method"]
    if not isinstance(method, str):
        raise ValueError("Unknown method")
    if method == "capabilities":
        return capabilities_handler(queue)
    if method == "estimate":
        return _estimate(request)
    if method in QUEUE_HANDLERS:
        return QUEUE_HANDLERS[method](queue, request)
    if method in RESEARCH_HANDLERS:
        return RESEARCH_HANDLERS[method](request)
    raise ValueError("Unknown method")
