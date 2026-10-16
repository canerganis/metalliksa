"""Conservative transient enthalpy finite-volume reference solver, SI internally.

Fixed material domain: no momentum, free surface, evaporation or shrinkage.
The boiling boundary is a validity STOP, never a clipped temperature result.
"""
import copy
import hashlib
import json
import math
import datetime
from pathlib import Path
import numpy as np
from lpbf_material_registry import contain_front_metrics, material, reidentify
from lpbf_run_progress import (current_progress, track_cpu_progress, track_cpu_run_boundary,
                               validate_cpu_progress)
from lpbf_source_identity import (CANONICAL_SCHEMA, RAW_SCHEMA, fingerprint_sources,
                                  fingerprint_manifest_entries, source_identity)
from lpbf_core_physics import property_at, enthalpy_table
from lpbf_core_physics import calculate_mesh_domain, scan_segments, thermal_si_inputs, SOURCE_INTEGRATION
from lpbf_core_contract import build_core_contract
from lpbf_verification import CELIK_MIN_REFINEMENT_RATIO, compare, convergence
from lpbf_heat_source import (MINIMUM_SOURCE_CAPTURE_FRACTION, require_source_capture,
                              source_limited_step, conduction_diagonal)
from lpbf_layered_conduction import conduction_heat_rate
from lpbf_ss304_support_material import (ss304_support_thermal_fields,
                                          ss304_support_thermal_snapshot,
                                          REFERENCE_TEMPERATURE_K,
                                          MAXIMUM_TEMPERATURE_K)
from lpbf_defect_diagnostics import defect_diagnostics
from lpbf_peak import (PeakMeltTracker, midtrack_bare_plate_section,
                       interpolated_midtrack_bare_plate_section,
                       rectangular_corridor_section_samples,
                       rectangular_corridor_section_observations,
                       write_rectangular_corridor_section_field_artifact)
from lpbf_overlap import FieldOverlapTracker, OVERLAP_MODEL_ID
from lpbf_evidence import finite_tree, measurement_evidence, resource_estimate, thermal_audits, enforce_thermal_balances, write_artifacts, FieldRecorder

VERSION = "enthalpy-fv-6"
IMPLEMENTATION_FINGERPRINT_SCHEMA = CANONICAL_SCHEMA
CACHE_FINGERPRINT_SCHEMA = "lpbf-thermal-cache-v2-canonical-production"
# Reviewed production closure for the shared thermal path and supported CPU,
# OpenFOAM, CUDA, and Warp implementations. Keep orchestration, tests, scratch
# scripts, and unrelated physics modules out of this numerical implementation ID.
IMPLEMENTATION_SOURCE_FILES = (
    "four_alloy_materials.py",
    "eagar_tsai_solver.py",
    "fabbro_keyhole.py",
    "goldak_solver.py",
    "in625_gpu_thermal_material.py",
    "in625_thermal_material.py",
    "lpbf_core_contract.py",
    "lpbf_core_physics.py",
    "lpbf_defect_diagnostics.py",
    "lpbf_evidence.py",
    "lpbf_evaporation_marangoni.py",
    "lpbf_gpu_pilot_artifacts.py",
    "lpbf_gpu_pilot_numerics.py",
    "lpbf_gpu_thermal.py",
    "lpbf_gpu_thermal_warp.py",
    "lpbf_heat_source.py",
    "lpbf_layered_conduction.py",
    "lpbf_material_registry.py",
    "marangoni_screening.py",
    "lpbf_openfoam.py",
    "lpbf_overlap.py",
    "lpbf_peak.py",
    "lpbf_run_progress.py",
    "lpbf_source_identity.py",
    "powder_packer.py",
    "powder_bed_raytracer.py",
    "lpbf_simulation.py",
    "lpbf_ss304_support_material.py",
    "lpbf_thermal_solver.py",
    "lpbf_transient_3d_gpu.py",
    "lpbf_verification.py",
    "solidification_front.py",
    "warp_thermal_solver.py",
    "openfoam/Make/files",
    "openfoam/Make/options",
    "openfoam/metalliksaThermal.C",
)
DEFAULTS = dict(mode="screening", material="Inconel 718", power_W=200., speed_mm_s=800.,
                beamDiameter_um=80., preheat_C=80., layer_um=40., hatch_um=100.,
                mesh_um=20., maxDt_s=1e-6, trackLength_um=600., tracks=1, layers=1,
                dwell_s=0.0002, cooling_s=0.0005, scanAngle_deg=0., layerRotation_deg=67.,
                strategy="meander", stripeWidth_um=500., islandSize_um=200., packingFraction=0.55, powderConductivityRatio=0.12,
                convection_W_m2K=20., timeout_s=300., study="none", backend="auto",
                surfaceMode="powder-layer", sourcePenetration_um=None,
                barePlateGeometry="square",
                evaporationModel=False, marangoniMultiplier=2.2,
                opticalObserver=None)
BOUNDS = dict(power_W=(10, 1500), speed_mm_s=(10, 10000), beamDiameter_um=(20, 500),
              preheat_C=(0, 1200), layer_um=(10, 150), hatch_um=(10, 1000), mesh_um=(5, 80),
              maxDt_s=(1e-9, 1e-4), trackLength_um=(100, 10000), tracks=(1, 8), layers=(1, 5),
              dwell_s=(0, .1), cooling_s=(0, .1), scanAngle_deg=(-360, 360),
              layerRotation_deg=(-360, 360), packingFraction=(.2, 1),
              stripeWidth_um=(20,3000), islandSize_um=(50,3000),
              powderConductivityRatio=(.01, 1), convection_W_m2K=(0, 1000), timeout_s=(10, 3600))


def summarize_accepted_timesteps(accepted_dt_s, requested_max_dt_s, source_limited_steps, source_retries):
    """Summarize realized positive steps without changing the solver schedule.

    ``eulerFirstOrderWeightedDt_s`` is the diagnostic scale sum(dt**2)/T for
    first-order local-error accumulation. It is descriptive, not an automatic
    convergence pass criterion; the step distribution must also be reviewed.
    """
    if (isinstance(requested_max_dt_s, bool) or not isinstance(requested_max_dt_s, (int, float))
            or not math.isfinite(requested_max_dt_s) or requested_max_dt_s <= 0
            or type(source_limited_steps) is not int or source_limited_steps < 0
            or type(source_retries) is not int or source_retries < source_limited_steps):
        raise ValueError("Invalid accepted-timestep summary inputs")
    dt = np.asarray(accepted_dt_s, dtype=np.float64)
    if (dt.ndim != 1 or dt.size == 0 or not np.isfinite(dt).all()
            or np.any(dt <= 0) or source_limited_steps > dt.size):
        raise ValueError("Accepted timesteps must be a nonempty finite positive sequence")
    total = float(np.sum(dt, dtype=np.float64))
    squared_total = float(np.dot(dt, dt))
    if not math.isfinite(total) or not math.isfinite(squared_total) or total <= 0:
        raise ValueError("Accepted timestep totals must be finite and positive")
    cap_tolerance = max(float(requested_max_dt_s) * 1e-12, 1e-30)
    at_requested_cap = np.abs(dt - float(requested_max_dt_s)) <= cap_tolerance
    return {
        "methodId": "accepted-timestep-distribution-v1",
        "count": int(dt.size),
        "total_s": total,
        "sumSquared_s2": squared_total,
        "mean_s": total / int(dt.size),
        "minimum_s": float(np.min(dt)),
        "p50_s": float(np.quantile(dt, .50)),
        "p90_s": float(np.quantile(dt, .90)),
        "p99_s": float(np.quantile(dt, .99)),
        "maximum_s": float(np.max(dt)),
        "eulerFirstOrderWeightedDt_s": squared_total / total,
        "requestedMaxDt_s": float(requested_max_dt_s),
        "requestedMaxDtHitFraction": float(np.count_nonzero(at_requested_cap) / dt.size),
        "sourceLimitedStepCount": source_limited_steps,
        "sourceTimestepRetries": source_retries,
    }


def validate(raw):
    layered_fields = {"thermalModelId", "plateThickness_um", "supportThickness_um",
                      "contactResistance_m2K_W", "supportBottomBoundary",
                      "incidenceAngle_deg", "incidenceAzimuth_deg", "beamProfileModelId",
                      "sourcePenetration_um"}
    if not isinstance(raw, dict) or set(raw)-set(DEFAULTS)-{"properties", "measurements", "absorptivity", "emissivity", "corridorWidth_um", "powderGridPolicy", "evaporationModel", "marangoniMultiplier", "opticalObserver"}-layered_fields:
        raise ValueError("Unknown simulation input fields")
    finite_tree(raw)
    p = {**DEFAULTS, **raw}
    layered = "thermalModelId" in raw
    if layered:
        required_layered = layered_fields
        if ((set(raw) & layered_fields) != required_layered
                or raw.get("thermalModelId") != "layered-plate-enthalpy-v1"):
            raise ValueError("Layered-plate model requires all explicit versioned sensitivity inputs")
        if (p["mode"] != "standard" or p["backend"] != "reference"
                or p["surfaceMode"] != "bare-plate" or p["barePlateGeometry"] != "square"
                or p["study"] != "none" or p["layers"] != 1 or p["tracks"] != 1
                or p["scanAngle_deg"] != 0 or p.get("measurements")):
            raise ValueError("Layered-plate sensitivity requires standard/reference bare-plate single +X track without measurements or study")
        numeric_layered = ("plateThickness_um", "supportThickness_um",
                           "contactResistance_m2K_W", "incidenceAngle_deg", "incidenceAzimuth_deg")
        limits = {"plateThickness_um": (5., 10000.), "supportThickness_um": (5., 10000.),
                  "contactResistance_m2K_W": (0., 1.), "incidenceAngle_deg": (0., 90.),
                  "incidenceAzimuth_deg": (0., 360.)}
        for key in numeric_layered:
            value = raw[key]
            lo, hi = limits[key]
            upper_ok = value < hi if key in ("incidenceAngle_deg", "incidenceAzimuth_deg") else value <= hi
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not lo <= value or not upper_ok):
                raise ValueError(f"{key} must be finite in [{lo}, {hi}]")
        if raw["beamProfileModelId"] != "assumed-oblique-gaussian-normal-plane-v1":
            raise ValueError("Unsupported layered-plate beam profile model")
        if raw["supportBottomBoundary"] not in ("adiabatic", "isothermal-at-preheat"):
            raise ValueError("Unknown support bottom boundary")
    if p["backend"] not in ("auto", "reference", "openfoam-thermal"):
        raise ValueError("Unknown thermal backend")
    for k, (lo, hi) in BOUNDS.items():
        if isinstance(p[k], bool) or not isinstance(p[k], (int, float)) or not math.isfinite(p[k]) or not lo <= p[k] <= hi:
            raise ValueError(f"{k} must be finite in [{lo}, {hi}]")
        if k in ("tracks", "layers") and int(p[k]) != p[k]:
            raise ValueError(f"{k} must be integer")
    if p["trackLength_um"] > 3000 and not (
            p["surfaceMode"] == "bare-plate" and p["barePlateGeometry"] == "rectangular-corridor"):
        raise ValueError("trackLength_um above 3000 is supported only by the opt-in bare-plate rectangular-corridor geometry")
    if p["mode"] not in ("screening", "standard", "high-fidelity", "calibration") or p["strategy"] not in ("meander", "unidirectional", "stripe", "island") or p["study"] not in ("none", "mesh", "timestep"):
        raise ValueError("Unknown mode, strategy or study")
    if p["surfaceMode"] not in ("powder-layer", "bare-plate"):
        raise ValueError("Unknown LPBF surface mode")
    if p["barePlateGeometry"] not in ("square", "rectangular-corridor"):
        raise ValueError("barePlateGeometry must be 'square' or 'rectangular-corridor'")
    if "powderGridPolicy" in raw:
        if raw["powderGridPolicy"] != "layer-conforming":
            raise ValueError("powderGridPolicy must be 'layer-conforming'")
        if (p["surfaceMode"] != "powder-layer" or p["mode"] != "standard"
                or p["backend"] not in ("reference", "openfoam-thermal")):
            raise ValueError("layer-conforming powder grid requires standard reference or OpenFOAM powder-layer mode")
    elif (p["surfaceMode"] == "powder-layer" and p["mode"] == "standard"
          and p["backend"] in ("reference", "openfoam-thermal")):
        # Standard powder transients align every powder-layer top surface with
        # a cell face on both supported thermal backends. Legacy archived
        # results retain their original settings and model identity.
        p["powderGridPolicy"] = "layer-conforming"
    if p["barePlateGeometry"] == "rectangular-corridor" and p["surfaceMode"] != "bare-plate":
        raise ValueError("rectangular-corridor geometry is only supported for bare-plate mode")
    if "corridorWidth_um" in raw and p["barePlateGeometry"] != "rectangular-corridor":
        raise ValueError("corridorWidth_um is only supported for rectangular-corridor geometry")
    if p["barePlateGeometry"] == "rectangular-corridor":
        width = p.get("corridorWidth_um")
        if width is None:
            # Preserve the historical fixed-frame width: twelve beam radii total.
            width = 6 * p["beamDiameter_um"]
        if (isinstance(width, bool) or not isinstance(width, (int, float))
                or not math.isfinite(width) or width <= 0):
            raise ValueError("corridorWidth_um must be a positive finite number")
        p["corridorWidth_um"] = float(width)
    if p["surfaceMode"] == "bare-plate":
        penetration = p["sourcePenetration_um"]
        if (p["mode"] != "standard" or p["backend"] != "reference" or p["layers"] != 1
                or p["tracks"] != 1 or p["scanAngle_deg"] != 0 or p.get("measurements")):
            raise ValueError("Bare-plate pilot requires standard/reference single +X track and no measurements")
        if type(penetration) not in (int, float) or not math.isfinite(penetration) or not 5 <= penetration <= 150:
            raise ValueError("Bare-plate sourcePenetration_um must be finite in [5, 150]")
    elif p["sourcePenetration_um"] is not None:
        raise ValueError("sourcePenetration_um is only supported for bare-plate mode")
    m = material(p["material"], p.get("properties"))
    if layered and m.get("materialId") != "in718":
        raise ValueError("Layered-plate sensitivity currently requires Inconel 718")
    if p["preheat_C"]+273.15 >= m["solidus_K"]:
        raise ValueError("Baseplate preheat must be below solidus")
    overridden = False
    if "absorptivity" in p:
        a = p["absorptivity"]
        if isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) or not 0 < a <= 1:
            raise ValueError("absorptivity must be in (0,1]")
        overridden = overridden or m["absorptivity"] != a
        m["absorptivity"] = a
    if "emissivity" in p:
        e = p["emissivity"]
        if type(e) not in (int, float) or not math.isfinite(e) or not 0 <= e <= 1:
            raise ValueError("emissivity must be in [0,1]")
        overridden = overridden or m["emissivity"] != e
        m["emissivity"] = e
    if overridden:
        # P7b (2026-10-14): a request value that differs from the registry snapshot changes the material, so its
        # identity is recomputed (the core contract verifies materialRevisionSha256 against the served dict).
        m = reidentify(m)
    p["absorptivity"], p["emissivity"] = m["absorptivity"], m["emissivity"]
    measurement_evidence(p.get("measurements", []), p)
    if p["mode"] == "calibration" and not p.get("measurements"):
        raise ValueError("Calibration requires measured dimensions and source")
    return p, m


def fingerprint(p, m):
    # Nonthermal jobs retain the broad source closure used by their existing dispatch.
    if p.get("jobType") is not None:
        return _legacy_broad_cache_fingerprint(p, m)
    implementation = implementation_fingerprint()
    payload = json.dumps([VERSION, p, m], sort_keys=True, allow_nan=False).encode()
    h = hashlib.sha256()
    h.update((CACHE_FINGERPRINT_SCHEMA + "\0" + implementation + "\0").encode())
    h.update(len(payload).to_bytes(8, "big")); h.update(payload)
    return h.hexdigest()


def _legacy_broad_cache_fingerprint(p, m):
    # Keep the historical algorithm byte-identical for build/GPU pilot jobs.
    root = Path(__file__).parent
    h = hashlib.sha256()
    for f in sorted(root.glob("*.py")):
        h.update(f.name.encode()); h.update(f.read_bytes())
    for f in sorted((root/"openfoam").glob("*.C")):
        h.update(f.name.encode()); h.update(f.read_bytes())
    for f in sorted((root/"openfoam/Make").glob("*")):
        if f.is_file(): h.update(f.name.encode()); h.update(f.read_bytes())
    h.update(json.dumps([VERSION, p, m], sort_keys=True, allow_nan=False).encode())
    return h.hexdigest()


def implementation_fingerprint(*, schema=CANONICAL_SCHEMA):
    """Hash the reviewed closure using an explicit versioned source-byte policy."""
    return _fingerprint_implementation_sources(Path(__file__).parent,
                                               IMPLEMENTATION_SOURCE_FILES, VERSION, schema=schema)


def implementation_source_identity():
    """Inspection metadata; raw-v2 here identifies current bytes, not old records."""
    return source_identity(Path(__file__).parent, IMPLEMENTATION_SOURCE_FILES, VERSION)


def _fingerprint_implementation_sources(root, source_files, version, *, schema=CANONICAL_SCHEMA):
    return fingerprint_sources(root, source_files, version, schema=schema)


def _fingerprint_manifest_entries(entries, version, *, schema=CANONICAL_SCHEMA):
    return fingerprint_manifest_entries(entries, version, schema=schema)


def screening(p, m):
    from goldak_solver import GoldakField, seed_goldak_axes
    t0 = p["preheat_C"]
    rho, k, cp = [float(property_at(m, t0+273.15, i)) for i in (1, 2, 3)]
    alpha = k/(rho*cp)
    power, speed = p["power_W"]*m["absorptivity"], p["speed_mm_s"]*1e-3
    goldak = GoldakField(t0, power, rho, cp, alpha, **seed_goldak_axes(p["beamDiameter_um"]*.5e-6)).bind_speed(speed)
    def rosenthal(x, y, z):
        r = np.maximum(np.sqrt(x*x+y*y+z*z), 1e-12)
        return t0+power/(2*math.pi*k*r)*np.exp(-speed*(x+r)/(2*alpha))
    out = {}
    # Fixed analytical scan grid, independent of the transient mesh.
    ax = np.linspace(-.003, .0005, 301)
    transverse = np.linspace(0, .001, 121)
    x, y = np.meshgrid(ax, transverse, indexing="ij")
    for model, field in (("rosenthal", rosenthal), ("goldak", goldak.temperature_C)):
        top = field(x, y, 0) >= m["liquidus_K"]-273.15
        cross = field(x, 0, y) >= m["liquidus_K"]-273.15
        ix, iy = np.where(top)
        iz = np.where(cross)[1]
        out[model] = dict(width_um=float(2*transverse[iy].max()*1e6) if len(iy) else 0.,
                          depth_um=float(transverse[iz].max()*1e6) if len(iz) else 0.,
                          length_um=float(np.ptp(ax[ix])*1e6) if len(ix) else 0.,
                          gridResolution_um=[float(np.diff(ax)[0]*1e6), float(np.diff(transverse)[0]*1e6)],
                          truncated=bool(top[0].any() or top[-1].any() or top[:, -1].any() or cross[:, -1].any()),
                          assumptions="Constant preheat properties; conduction only; discrete liquidus extent; no keyhole correction.")
    return out


def conduction_rate(T, k, active, dx):
    """Conservative harmonic internal-face conduction, W/m^3, insulated exterior."""
    rate = np.zeros_like(T)
    for axis_id in range(3):
        left,right = [slice(None)]*3,[slice(None)]*3
        left[axis_id],right[axis_id] = slice(None,-1),slice(1,None)
        a,b = tuple(left),tuple(right)
        face_k = 2*k[a]*k[b]/(k[a]+k[b])
        flux = face_k*(T[b]-T[a])/dx**2*(active[a]&active[b])
        rate[a] += flux; rate[b] -= flux
    return rate


def _conduction_rate_and_diagonal(T, k, active, dx):
    """Return conductive rate [W/m^3] and row-sum diagonal [W/m^3/K].

    The transient reference path needs both quantities for every accepted
    timestep. Compute each harmonic face conductance once and reuse it for the
    conservative flux and explicit-stability bound.
    """
    rate = np.zeros_like(T)
    diagonal = np.zeros_like(k)
    for axis_id in range(3):
        left, right = [slice(None)] * 3, [slice(None)] * 3
        left[axis_id], right[axis_id] = slice(None, -1), slice(1, None)
        a, b = tuple(left), tuple(right)
        face_k = 2 * k[a] * k[b] / (k[a] + k[b])
        face_mask = active[a] & active[b]
        flux = face_k * (T[b] - T[a]) / dx**2 * face_mask
        face_diagonal = face_k / dx**2 * face_mask
        rate[a] += flux
        rate[b] -= flux
        diagonal[a] += face_diagonal
        diagonal[b] += face_diagonal
    return rate, diagonal


def active_gradient_components(T, active, dx):
    """Average active face differences; one-sided at deposition boundaries.

    Inactive future powder is not a temperature boundary condition. Including
    its preheat temperature would contaminate the extracted G and R.
    """
    components = []
    for axis in range(3):
        left, right = [slice(None)]*3, [slice(None)]*3
        left[axis], right[axis] = slice(None, -1), slice(1, None)
        a, b = tuple(left), tuple(right)
        valid = active[a] & active[b]
        difference = (T[b]-T[a])/dx*valid
        gradient, count = np.zeros_like(T), np.zeros_like(T)
        gradient[a] += difference; gradient[b] += difference
        count[a] += valid; count[b] += valid
        components.append(gradient/np.maximum(count, 1))
    return np.stack(components)


def active_gradient(T, active, dx):
    return np.linalg.norm(active_gradient_components(T, active, dx), axis=0)


def liquidus_crossing_sums(old, new, active, dx, dt, liquidus):
    """Equal event sums of G [K/m], R [m/s], cooling [K/s], and count.

    Reconstruct gradient vectors at each cell's cooling liquidus crossing,
    not at the end of the step. Thermal evolution remains first-order.
    """
    crossing = active & (old >= liquidus) & (new < liquidus)
    if not crossing.any():
        return None
    drop = old[crossing]-new[crossing]
    theta = (old[crossing]-liquidus)/drop
    before = active_gradient_components(old, active, dx)[:, crossing]
    after = active_gradient_components(new, active, dx)[:, crossing]
    grad = np.linalg.norm(before+(after-before)*theta, axis=0)
    cooling = drop/dt
    good = grad > 1e-6
    if not good.any():
        return None
    return [float(grad[good].sum()), float((cooling[good]/grad[good]).sum()),
            float(cooling[good].sum()), int(good.sum())]


def _require_reference_powder_observer(p, message, thermal_solver=None):
    """Shared gate of the final-state, selected-time and local-history observers.

    They support standard reference powder-layer runs only: no study and not the
    layered-plate model. run() also passes its selected thermal_solver, which must be
    the NumPy transient. Raises ValueError(message); same clauses and order as the
    former inline copies (design 5c, B3).
    """
    if (p["mode"] != "standard" or p["backend"] != "reference" or p["study"] != "none"
            or p["surfaceMode"] != "powder-layer"
            or (thermal_solver is not None and thermal_solver is not transient)
            or p.get("thermalModelId") == "layered-plate-enthalpy-v1"):
        raise ValueError(message)


@track_cpu_progress
def transient(p, m, report=lambda *args: None, artifact_dir=None, final_state_observer=None,
              selected_time_observer=None, selected_time_s=None,
              local_history_observer=None, local_history_indices_ijk=None, run_progress=None):
    if final_state_observer is not None:
        if not callable(final_state_observer):
            raise ValueError("Final state observer must be callable")
        _require_reference_powder_observer(p, "Final state capture supports standard reference powder-layer runs only")
    segments, end = scan_segments(p)
    if selected_time_observer is not None:
        if not callable(selected_time_observer):
            raise ValueError("Selected-time observer must be callable")
        _require_reference_powder_observer(p, "Selected-time capture supports standard reference powder-layer runs only")
        if (isinstance(selected_time_s, bool) or not isinstance(selected_time_s, (int, float))
                or not math.isfinite(selected_time_s) or selected_time_s <= 0
                or not any(selected_time_s == segment["end_s"] for segment in segments)):
            raise ValueError("Selected time must be an existing scan-segment end event")
    elif selected_time_s is not None:
        raise ValueError("Selected time requires a selected-time observer")
    if local_history_observer is None:
        if local_history_indices_ijk is not None:
            raise ValueError("Local history indices require an observer")
        local_indices = ()
    else:
        if not callable(local_history_observer):
            raise ValueError("Local history observer must be callable")
        _require_reference_powder_observer(p, "Local history supports standard reference powder-layer runs only")
        if (not isinstance(local_history_indices_ijk, (tuple, list))
                or not 1 <= len(local_history_indices_ijk) <= 32):
            raise ValueError("Local history needs 1 to 32 selected cell indices")
        local_indices = []
        for index in local_history_indices_ijk:
            if (not isinstance(index, (tuple, list)) or len(index) != 3
                    or any(type(value) is not int for value in index)):
                raise ValueError("Local history indices must be integer (x,y,z) triples")
            local_indices.append(tuple(index))
        if len(set(local_indices)) != len(local_indices):
            raise ValueError("Local history indices must be unique")
    thermal_inputs = thermal_si_inputs(p, m)
    layer_m = thermal_inputs["layer_m"]
    speed_m_s = thermal_inputs["speed_m_s"]
    absorbed_power_W = thermal_inputs["absorbed_power_W"]
    dx_requested = p["mesh_um"]*1e-6
    layered = p.get("thermalModelId") == "layered-plate-enthalpy-v1"
    domain = calculate_mesh_domain(p)
    if layered:
        plate_cells = max(1, int(math.ceil(p["plateThickness_um"]*1e-6/domain["dx"]-1e-12)))
        support_cells = max(1, int(math.ceil(p["supportThickness_um"]*1e-6/domain["dx"]-1e-12)))
        domain["plate_cells"], domain["support_cells"] = plate_cells, support_cells
        domain["plate_depth"] = plate_cells*domain["dx"]
        domain["support_depth"] = support_cells*domain["dx"]
        domain["substrate_depth"] = domain["plate_depth"]+domain["support_depth"]
        domain["nz"] = plate_cells+support_cells
    radius, span, nx, ny, nz, dx, substrate = (domain[k] for k in ("radius", "span", "nx", "ny", "nz", "dx", "substrate_depth"))
    if any(not (0 <= i < nx and 0 <= j < ny and 0 <= k_index < nz)
           for i, j, k_index in local_indices):
        raise ValueError("Local history cell index exceeds the resolved grid")
    cell_count = nx*ny*nz
    progress = current_progress()
    if progress is not None:
        progress.set_cells(cell_count)
    if cell_count > 600000:
        geometry = "rectangular corridor" if p["barePlateGeometry"] == "rectangular-corridor" else "square"
        raise ValueError(f"{geometry.capitalize()} mesh requires {cell_count:,} cells, above the 600000-cell reference solver limit; reduce the scan length or use a coarser mesh")
    axis = (np.arange(nx)+.5)*dx-span/2
    axis_y = (np.arange(ny)+.5)*dx-ny*dx/2
    z = (np.arange(nz)+.5)*dx-substrate
    bare = p["surfaceMode"] == "bare-plate"
    if not bare:
        layer_counts = [int(np.sum(z < layer*layer_m)) for layer in range(int(p["layers"])+1)]
        if any(b <= a for a,b in zip(layer_counts,layer_counts[1:])):
            raise ValueError("Mesh cannot resolve each powder layer; reduce mesh spacing below layer thickness")
    x, y, zz = np.meshgrid(axis, axis_y, z, indexing="ij")
    t0 = thermal_inputs["preheat_K"]
    T = np.full(x.shape, t0)
    tt, hh = enthalpy_table(m)
    h0 = np.interp(t0, tt, hh)
    # Fixed reference mass: avoids nonconservative rho(T)*h update on an immobile grid.
    rho = float(property_at(m, t0, 1))*np.where(zz > 0, p["packingFraction"], 1.)
    support_cells = domain.get("support_cells", 0)
    support_mask = np.broadcast_to((np.arange(nz) < support_cells)[None, None, :], T.shape) if layered else None
    in718_mask = ~support_mask if layered else None
    if layered:
        rho = np.where(support_mask, 7920.0, rho)
        _, ss_cp_table, _, ss_h_table = ss304_support_thermal_fields(
            np.linspace(REFERENCE_TEMPERATURE_K, MAXIMUM_TEMPERATURE_K, 4097))
        ss_t_table = np.linspace(REFERENCE_TEMPERATURE_K, MAXIMUM_TEMPERATURE_K, 4097)
        h0_ss = float(np.interp(t0, ss_t_table, ss_h_table))
        h0_field = np.where(support_mask, h0_ss, h0)
    else:
        h0_field = h0
    H = np.zeros_like(T)
    ever = np.zeros_like(T, dtype=bool)
    midpoint_plane = int(np.argmin(np.abs(axis))) if bare else None
    midpoint_temperature_max = np.full((ny, nz), t0) if bare else None
    rectangular_corridor = bare and p["barePlateGeometry"] == "rectangular-corridor"
    corridor_section_samples = (rectangular_corridor_section_samples(
        axis, segments[0]["start"][0], p["trackLength_um"]*1e-6)
        if rectangular_corridor else None)
    corridor_peak_planes = ({index: np.full((ny, nz), t0) for index in sorted({
        plane for sample in corridor_section_samples if sample["status"] == "pending"
        for plane in sample["sourcePlaneIndices"]})} if rectangular_corridor else None)
    remelt = np.zeros_like(ever)
    previous_melt = np.zeros_like(ever)
    energy_in = energy_out = 0.
    history, fronts = [], []
    peak_tracker = PeakMeltTracker(np.column_stack([x.ravel(), y.ravel(), zz.ravel()]), dx, m)
    overlap_tracker = None if bare else FieldOverlapTracker(np.column_stack([x.ravel(), y.ravel(), zz.ravel()]), dx, m, p)
    peak = t0
    time, step, next_sample = 0., 0, 0.
    recorder = FieldRecorder(artifact_dir, np.column_stack([x.ravel(), y.ravel(), zz.ravel()]), dx, m, p)
    min_dt = p["maxDt_s"]
    max_dt = max_increment = surface_offset = 0.
    minimum_capture, source_retries = 1., 0
    source_limited_steps = 0
    accepted_dt_s = []
    accepted_clock_s = 0.
    selected_time_captured = False
    cp_floor = min(row[3] for row in m["table"])
    if layered:
        cp_floor = min(cp_floor, float(np.min(ss_cp_table)))
        interface_z = np.zeros((nz-1, ny, nx), dtype=bool)
        interface_z[support_cells-1, :, :] = True
        support_snapshot = ss304_support_thermal_snapshot()
    # Loop-invariant enthalpy limits (design 5c B4): tt, hh and m are fixed for the run;
    # hoisted unchanged from the step body, so every value and message is bit-identical.
    minimum_allowed_h = float(hh[0])-1e-8
    boiling_enthalpy = float(np.interp(m["boiling_K"], tt, hh))
    # evaporationModel=True is a BOILING CAP, not an evaporation model: the inversion clips T at
    # T_boil and keeps the excess enthalpy in the cell (nothing leaves the domain). These counters
    # make the cap visible in the result (boilingCap block); flag-false runs never touch them.
    boiling_cap = bool(p.get("evaporationModel", False))
    cap_steps = 0
    cap_max_excess_h = 0.
    cap_max_vapor_fraction_proxy = 0.
    cap_latent_heat_vap = None
    if boiling_cap:
        from four_alloy_materials import thermal_props
        # D1: L_v from the material authority for the four alloys; no literal and no other-alloy
        # fallback. Snapshot bytes are untouched (material() does not carry this key).
        authority = thermal_props(m["materialId"]) if m.get("provenanceClass") == "estimated-legacy" else None
        if authority is None or "latent_heat_vap_J_kg" not in authority:
            cause = ("user-supplied material properties" if m.get("provenanceClass") != "estimated-legacy"
                     else f"material {m.get('materialId')!r} has no latent_heat_vap_J_kg in four_alloy_materials")
            raise ValueError(f"evaporationModel (boiling cap) requires a sourced latent heat of vaporization: {cause}; "
                             "no literal and no other-alloy value is substituted")
        cap_latent_heat_vap = float(authority["latent_heat_vap_J_kg"])
    while time < end:
        seg = next((s for s in segments if s["start_s"] <= time+1e-14 and time < s["end_s"]-1e-14), None)
        active_layer = max([s["layer"] for s in segments if s["start_s"] <= time+1e-14] or [0])
        surface = 0. if bare else (active_layer+1)*layer_m
        active = zz < surface
        top_index = int(np.flatnonzero(z < surface)[-1])
        k = property_at(m, T, 2)*np.where((zz > 0)&~ever, p["powderConductivityRatio"], 1.)
        if p.get("evaporationModel", False):
            from lpbf_evaporation_marangoni import calculate_keff_marangoni
            liquidus_t = float(m["liquidus_K"])
            solidus_t = float(m["solidus_K"])
            fraction = np.clip((T - solidus_t) / max(1e-6, liquidus_t - solidus_t), 0.0, 1.0)
            lambda_m = float(p.get("marangoniMultiplier", 2.2))
            k = calculate_keff_marangoni(k, fraction, lambda_marangoni=lambda_m)
        cp = property_at(m, T, 3)
        if layered:
            ss_rho, ss_cp, ss_k, _ = ss304_support_thermal_fields(T[support_mask])
            k[support_mask] = ss_k
            cp[support_mask] = ss_cp
        dt = min(p["maxDt_s"], .12*dx*dx/float(np.max(k/(rho*cp))), radius/(4*speed_m_s), end-time)
        # End exactly on scan/deposition events: never smear laser-on into a dwell.
        events = [s[v]-time for s in segments for v in ("start_s", "end_s") if s[v] > time+1e-14]
        if events:
            dt = min(dt, min(events))
        if layered:
            face_power = conduction_heat_rate(T.transpose(2, 1, 0), k.transpose(2, 1, 0), dx,
                contact_resistance_m2K_W=p["contactResistance_m2K_W"],
                interface_z=interface_z, active_cells=active.transpose(2, 1, 0))
            rate = face_power.transpose(2, 1, 0)/dx**3
            diagonal = conduction_diagonal(k, active, dx)
        else:
            rate, diagonal = _conduction_rate_and_diagonal(T, k, active, dx)
        if local_history_observer is not None:
            local_conduction = [float(rate[index]) for index in local_indices]
        # Explicit support-base boundary; legacy v1 retains its fixed-temperature base.
        bottom = np.zeros((nx, ny))
        isothermal_bottom = (not layered or p["supportBottomBoundary"] == "isothermal-at-preheat")
        if isothermal_bottom:
            bottom = 2*k[:, :, 0]*(T[:, :, 0]-t0)/dx**2
            rate[:, :, 0] -= bottom
        surface_loss = (p["convection_W_m2K"]*(T[:, :, top_index]-t0)
                        +m["emissivity"]*5.670374419e-8*(T[:, :, top_index]**4-t0**4))/dx
        rate[:, :, top_index] -= surface_loss
        # A local row-sum bound includes heterogeneous faces and boundary cooling.
        # The table minimum cp is a lower bound on enthalpy capacity across a step.
        if isothermal_bottom:
            diagonal[:, :, 0] += 2*k[:, :, 0]/dx**2
        top_temperature = T[:, :, top_index]
        diagonal[:, :, top_index] += (p["convection_W_m2K"]+m["emissivity"]*5.670374419e-8
            *(top_temperature+t0)*(top_temperature**2+t0**2))/dx
        dt = min(dt, float(np.min(.9*rho*cp_floor/np.maximum(diagonal, 1e-30))))
        dt, source, rate, capture, retries = source_limited_step(
            axis, z, dx, seg, time, dt, surface, radius,
            p["sourcePenetration_um"]*1e-6 if bare else layer_m,
            absorbed_power_W, rate, rho*cp, axis_y=axis_y,
            incidence_angle_deg=p.get("incidenceAngle_deg", 0.),
            incidence_azimuth_deg=p.get("incidenceAzimuth_deg", 0.))
        source_limited_steps += int(retries > 0)
        require_source_capture(capture, MINIMUM_SOURCE_CAPTURE_FRACTION)
        min_dt = min(min_dt, dt)
        max_dt = max(max_dt, dt)
        max_increment = max(max_increment, float(np.max(dt*np.abs(rate)/(rho*cp))))
        minimum_capture = min(minimum_capture, capture)
        source_retries += retries
        surface_offset = max(surface_offset, abs(z[top_index]+dx/2-surface)*1e6)
        old = T.copy()
        H += dt*rate
        h = H/rho+h0_field
        if layered:
            if (not np.isfinite(h).all() or float(h[~support_mask].min()) < hh[0]-1e-8
                    or float(h[~support_mask].max()) >= boiling_enthalpy
                    or float(h[support_mask].min()) < ss_h_table[0]-1e-8
                    or float(h[support_mask].max()) > ss_h_table[-1]):
                raise ValueError("Thermal model validity exceeded (IN718 boiling or SS304 fit range)")
            T[~support_mask] = np.interp(h[~support_mask], hh, tt)
            T[support_mask] = np.interp(h[support_mask], ss_h_table, ss_t_table)
        else:
            if not np.isfinite(h).all():
                raise ValueError("Thermal model validity exceeded (non-finite specific enthalpy)")
            minimum_h, maximum_h = float(h.min()), float(h.max())
            if minimum_h < minimum_allowed_h:
                raise ValueError(
                    "Thermal model validity exceeded below the property-table range "
                    f"(specific enthalpy {minimum_h:.9g} J/kg; minimum {minimum_allowed_h:.9g} J/kg "
                    f"at {float(tt[0]):.6g} K)"
                )
            if maximum_h >= boiling_enthalpy:
                if boiling_cap:
                    from lpbf_evaporation_marangoni import invert_enthalpy_with_boiling_cap
                    T, vapor_proxy = invert_enthalpy_with_boiling_cap(h, hh, tt, m["boiling_K"], cap_latent_heat_vap)
                    cap_steps += 1
                    cap_max_excess_h = max(cap_max_excess_h, maximum_h-boiling_enthalpy)
                    cap_max_vapor_fraction_proxy = max(cap_max_vapor_fraction_proxy, float(np.max(vapor_proxy)))
                else:
                    hot_cell = np.unravel_index(int(np.argmax(h)), h.shape)
                    cell_density = float(rho[hot_cell])
                    cell_rate = float(rate[hot_cell])
                    prior_specific_h = maximum_h-dt*cell_rate/cell_density
                    raise ValueError(
                        "Thermal model validity exceeded at or above the material boiling limit "
                        f"(specific enthalpy {maximum_h:.9g} J/kg; limit {boiling_enthalpy:.9g} J/kg "
                        f"at {m['boiling_K']:.6g} K; cell={hot_cell}, previous T={float(old[hot_cell]):.6g} K, "
                        f"previous specific enthalpy={prior_specific_h:.9g} J/kg, dt={dt:.9g} s, "
                        f"source rate={float(source[hot_cell]):.9g} W/m³, "
                        f"net rate={cell_rate:.9g} W/m³); evaporation/free-surface CFD required"
                    )
            else:
                T = np.interp(h, hh, tt)
        # Only candidates passing capture, enthalpy and inversion validity are accepted.
        accepted_dt_s.append(dt)
        accepted_clock_s += dt
        previous_time = time
        time += dt
        end_roundoff = min(1e-14, 2*math.ulp(end)*(step+1))
        if end-time <= end_roundoff:
            time = end
        if progress is not None:
            progress.accept(dt, accepted_clock_s, time)
        if (selected_time_observer is not None and not selected_time_captured
                and previous_time <= selected_time_s + end_roundoff
                and time >= selected_time_s - end_roundoff):
            difference_s = float(selected_time_s - accepted_clock_s)
            sample_tolerance_s = min(1e-14, 2*math.ulp(float(selected_time_s))*(step+1))
            if abs(difference_s) > sample_tolerance_s:
                raise ValueError("Accepted selected-time state missed the requested event beyond roundoff")
            selected_time_observer({
                "coordinates_m": np.column_stack((x.ravel(), y.ravel(), zz.ravel())).copy(),
                "temperature_K": T.ravel().copy(),
                "enthalpy_J_m3": H.ravel().copy(),
                "density_kg_m3": rho.ravel().copy(),
                "accepted_dt_s": np.asarray(accepted_dt_s, dtype=np.float64).copy(),
                "target_time_s": float(selected_time_s),
                "time_s": float(accepted_clock_s),
                "scheduler_time_s": float(time),
                "time_difference_s": difference_s,
                "roundoff_tolerance_s": sample_tolerance_s,
                "step": int(step+1),
                "initial_temperature_K": float(t0),
                "cell_volume_m3": float(dx**3),
            })
            selected_time_captured = True
        step += 1
        energy_in += float(source.sum())*dx**3*dt
        energy_out += (float(bottom.sum())+float(surface_loss.sum()))*dx**3*dt
        melt = (T >= m["liquidus_K"])&active
        if layered:
            melt &= in718_mask
        remelt |= melt&ever&~previous_melt
        if local_history_observer is not None:
            local_ever_before = [bool(ever[index]) for index in local_indices]
        ever |= melt
        if local_history_observer is not None:
            local_history_observer({
                "step": int(step), "time_s": float(accepted_clock_s),
                "acceptedDt_s": float(dt), "schedulerTime_s": float(time),
                "cell_indices_ijk": [list(index) for index in local_indices],
                "cells": [{
                    "coordinate_m": [float(axis[index[0]]), float(axis_y[index[1]]),
                                     float(z[index[2]])],
                    "temperature_K": float(T[index]),
                    "enthalpy_J_m3": float(H[index]),
                    "everLiquidusBefore": before,
                    "everLiquidusAfter": bool(ever[index]),
                    "effectiveConductivity_W_mK": float(k[index]),
                    "sourceRate_W_m3": float(source[index]),
                    "conductionRate_W_m3": conduction,
                    "passiveRate_W_m3": float(rate[index]-source[index]),
                } for index, before, conduction in zip(
                    local_indices, local_ever_before, local_conduction)],
            })
        if bare:
            np.maximum(midpoint_temperature_max, T[midpoint_plane], out=midpoint_temperature_max)
            if rectangular_corridor:
                for plane, maximum in corridor_peak_planes.items():
                    np.maximum(maximum, T[plane], out=maximum)
        front = liquidus_crossing_sums(old, T, active, dx, dt, m["liquidus_K"])
        if front is not None:
            fronts.append(front)
        previous_melt = melt
        # One reduction per accepted step, reused by the sampled history and report (B4).
        temperature_max = float(T.max())
        peak = max(peak, temperature_max)
        sampled = time >= next_sample or time >= end
        peak_tracker.observe(T, surface, p["scanAngle_deg"]+active_layer*p["layerRotation_deg"],
                             time, step, sampled=sampled)
        active_track = seg["track"] if seg is not None else (
            max([s["track"] for s in segments if s["layer"] == active_layer and s["end_s"] <= time + 1e-14] or [0])
        )
        if overlap_tracker is not None:
            overlap_tracker.observe(T, surface, active_layer, active_track)
        if sampled:
            recorder.record(time, T, surface)
            history.append(dict(time_s=time, peak_K=temperature_max, center_K=float(T[nx//2, ny//2, top_index]),
                                storedEnergy_J=float(H.sum())*dx**3, inputEnergy_J=energy_in, lossEnergy_J=energy_out))
            report(time/end, f"step={step} t={time:.7g}s peak={temperature_max:.1f}K cells={T.size}")
            next_sample = time+end/60
        if step > 250000:
            raise ValueError("Reference solver step budget exceeded")
    if selected_time_observer is not None and not selected_time_captured:
        raise ValueError("Selected-time event was not reached by an accepted timestep")
    stored = float(H.sum())*dx**3
    balance = abs(energy_in-energy_out-stored)/max(energy_in, 1e-12)
    if balance > .01:
        raise ValueError(f"Energy balance failed: {balance:.3%}")
    if final_state_observer is not None:
        final_state_observer({
            "coordinates_m": np.column_stack((x.ravel(), y.ravel(), zz.ravel())).copy(),
            "temperature_K": T.ravel().copy(),
            "enthalpy_J_m3": H.ravel().copy(),
            "density_kg_m3": rho.ravel().copy(),
            "accepted_dt_s": np.asarray(accepted_dt_s, dtype=np.float64).copy(),
            "time_s": float(time),
            "initial_temperature_K": float(t0),
            "cell_volume_m3": float(dx**3),
        })
    discretization = dict(cells=int(T.size), mesh_m=dx, minimumDt_s=min_dt, meanDt_s=end/step, steps=step)
    timestep_diagnostics = summarize_accepted_timesteps(
        accepted_dt_s, p["maxDt_s"], source_limited_steps, source_retries)
    if layered:
        discretization.update(requestedPlateThickness_um=p["plateThickness_um"],
            effectivePlateThickness_um=domain["plate_depth"]*1e6,
            requestedSupportThickness_um=p["supportThickness_um"],
            effectiveSupportThickness_um=domain["support_depth"]*1e6,
            plateCells=int(domain["plate_cells"]), supportCells=int(domain["support_cells"]))
    if rectangular_corridor:
        discretization.update(requestedCorridorWidth_um=p["corridorWidth_um"],
                              effectiveCorridorWidth_um=domain["effective_span_y"]*1e6)
    G, R, cooling = (np.sum(fronts, axis=0)[:3]/np.sum(fronts, axis=0)[3]).tolist() if fronts else (None, None, None)
    best, peak_diagnostics = peak_tracker.finish(artifact_dir, step)
    interpolated_peak = peak_diagnostics.pop("interpolatedPeakMeltPool")
    overlap_metrics = overlap_tracker.finish(artifact_dir) if overlap_tracker is not None else None
    width = best["width_um"]*1e-6
    alpha = float(property_at(m, m["liquidus_K"], 2)/(property_at(m, m["liquidus_K"], 1)*property_at(m, m["liquidus_K"], 3)))
    best.update(peakTemperature_K=peak, thermalGradient_K_m=G, solidificationRate_m_s=R,
                coolingRate_K_s=cooling, keyholeDepth_um=None, recoilPressure_Pa=None,
                marangoniNumber=abs(m["dGamma_dT"])*max(0, peak-m["liquidus_K"])*width/(float(property_at(m, peak, 4))*alpha),
                pecletNumber=p["speed_mm_s"]*1e-3*width/alpha,
                aspectRatio=best["depth_um"]/best["width_um"] if width else None,
                trackOverlapRatio=overlap_metrics["trackOverlapRatio"] if overlap_metrics else None,
                remeltingRatio=overlap_metrics["globalRemeltRatio"] if overlap_metrics else None)
    # D13 field identity: the producer and its extraction rule, never the served implementation fingerprint (that
    # lives only in provenance.implementationHash; the parity harness counts any other occurrence).
    best, transient_front = contain_front_metrics(
        best, m, p, f"lpbf-transient:{p.get('thermalModelId') or VERSION}:linear-liquidus-crossing-v1")
    # LT-3: G, R and cooling rate come from one mesh. Report how many cells span the pool (a top-level
    # result label, not part of numericalDiagnostics, which the reference parity cases pin bit-exact); the
    # gradient at a liquidus crossing averages the two adjacent face differences (a 2-cell stencil,
    # active_gradient_components), so a pool fewer than 2 cells deep or wide puts the whole stencil
    # across the pool boundary. No literature cell-count threshold is claimed.
    cells_w = round(best["width_um"]*1e-6/dx, 6) if best.get("width_um") else 0.0
    cells_d = round(best["depth_um"]*1e-6/dx, 6) if best.get("depth_um") else 0.0
    solidification_resolution = dict(
        methodId="melt-pool-cell-count-v1", mesh_um=dx*1e6,
        cellsAcrossWidth=cells_w, cellsAcrossDepth=cells_d, gradientStencilCells=2,
        meshVerified=False,
        status=("not-available" if G is None else
                "stencil-spans-melt-pool" if min(cells_w, cells_d) < 2 else "single-mesh-unverified"),
        note=("thermalGradient_K_m, solidificationRate_m_s and coolingRate_K_s are single-mesh values; "
              "discretisation error is unbounded until a three-grid study (Celik et al. 2008, "
              "J. Fluids Eng. 130:078001) converges for them."))
    bare_plate_section_observations = (rectangular_corridor_section_observations(
        axis_y, z, corridor_peak_planes, corridor_section_samples, dx, m["liquidus_K"])
        if rectangular_corridor else None)
    section_field_artifact = None
    if rectangular_corridor and artifact_dir is not None:
        if all(row.get("status") == "thermal-proxy"
               for row in bare_plate_section_observations):
            section_field_path = "rectangular-corridor-section-fields.npz"
            write_rectangular_corridor_section_field_artifact(
                Path(artifact_dir) / section_field_path, axis, axis_y, z,
                bare_plate_section_observations, corridor_peak_planes, dx,
                m["liquidus_K"], int(step))
            section_field_artifact = {
                "schemaVersion": 1,
                "status": "captured",
                "path": section_field_path,
                "binding": "accepted-step-maximum-per-source-X-plane",
            }
        else:
            section_field_artifact = {
                "schemaVersion": 1,
                "status": "unavailable",
                "path": None,
                "reason": "Both 4.9 mm and 6.0 mm sections must have supported thermal-proxy fields; "
                          + "; ".join(f"{row.get('recordId')}={row.get('status')}"
                                       for row in bare_plate_section_observations),
            }
    return dict(metrics=best, transientFrontDiagnostics=transient_front, thermalHistory=history, fieldSeries=recorder.finish(),
                **({"boilingCap": dict(
                    modelId="boiling-cap-v1", active=True, cappedSteps=cap_steps,
                    maxExcessEnthalpy_J_kg=cap_max_excess_h,
                    maxVaporFractionProxy=cap_max_vapor_fraction_proxy,
                    latentHeatVap_J_kg=cap_latent_heat_vap, energyLeavesDomain=False,
                    isReferenceSolution=False, isEvaporationModel=False,
                    note="Diagnostic of the boiling cap: the inversion clips T at T_boil and keeps the excess "
                         "enthalpy in the cell; the vapor-fraction proxy excess_h/L_v is not a mass loss and is "
                         "not conserved. Not an evaporation model.")} if boiling_cap else {}),
                peakInterpolatedMeltPool=interpolated_peak,
                fieldOverlapDiagnostics=overlap_metrics,
                midTrackCrossSection=midtrack_bare_plate_section(axis, z, ever, dx, axis_y=axis_y) if bare else None,
                midTrackInterpolatedCrossSection=interpolated_midtrack_bare_plate_section(
                    axis_y, z, midpoint_temperature_max, dx, m["liquidus_K"], axis[midpoint_plane]
                ) if bare else None,
                # A single transient execution does not retain independently
                # simulated track fields. Do not label repeated final-field
                # slices as a three-track six-section observation.
                **({"barePlateSectionObservations": bare_plate_section_observations}
                   if rectangular_corridor else {}),
                **({"barePlateSectionFieldArtifact": section_field_artifact}
                   if section_field_artifact is not None else {}),
                solidificationResolution=solidification_resolution,
                numericalDiagnostics=dict(**peak_diagnostics, overlapExtraction=OVERLAP_MODEL_ID if overlap_metrics else None, sourceIntegration=SOURCE_INTEGRATION, solidificationExtraction="linear-liquidus-crossing-v1",
                    stabilityLimit="local-conductance-row-sum", minimumCapturedSourceFraction=minimum_capture,
                    maximumSourceRenormalization=1/minimum_capture, maximumSurfaceOffset_um=surface_offset,
                    maximumTimestep_s=max_dt, maximumEnthalpyIncrement_K=max_increment,
                    sourceTimestepRetries=source_retries,
                    acceptedTimestepDistribution=timestep_diagnostics),
                energyBalance=dict(input_J=energy_in, losses_J=energy_out, stored_J=stored, relativeError=balance),
                discretization=discretization,
                scanPath=segments,
                **({"supportMaterial": support_snapshot,
                    "supportDiagnostics": dict(maximumTemperature_K=float(np.max(T[support_mask])),
                        storedThermalEnergy_J=float(H[support_mask].sum())*dx**3,
                        supportCellsExcludedFromMeltGeometry=True),
                    "layeredSensitivity": dict(interfaceModelId="planar-series-resistance-v1",
                        contactResistance_m2K_W=p["contactResistance_m2K_W"],
                        supportBottomBoundary=p["supportBottomBoundary"],
                        beamProfileModelId=p["beamProfileModelId"],
                        evidenceNote="Explicit sensitivity assumptions; not AMB2022-03 measured contact, support boundary, or irradiance-map evidence.")}
                   if layered else {}),
                **thermal_audits(np.column_stack([x.ravel(),y.ravel(),zz.ravel()]), np.full(T.size,dx**3), p,m,
                    (np.clip((T-m["solidus_K"])/(m["liquidus_K"]-m["solidus_K"]),0,1)*active).ravel()))


def _layer_aligned_mesh_levels(p, min_ratio=CELIK_MIN_REFINEMENT_RATIO):
    """Three layer-aligned cells-per-layer levels containing the request, adjacent ratios >= min_ratio.

    Celik et al. 2008 Step 2 asks for r = h_coarse/h_fine > 1.3 per refinement; consecutive counts
    (n-1, n, n+1) give r -> 1 + 1/n and fall below that for n >= 4, so the counts are spread instead.
    The request is the medium level when both neighbours fit, otherwise the coarse or fine level.
    """
    layer_um = p["layer_um"]
    n = max(1, int(math.ceil(layer_um / p["mesh_um"] - 1e-12)))
    max_cells = int(math.floor(layer_um / BOUNDS["mesh_um"][0] + 1e-12))

    def finer(c):
        return int(math.ceil(c * min_ratio - 1e-12))

    def coarser(c):
        return int(math.floor(c / min_ratio + 1e-12))

    candidates = []
    if coarser(n) >= 1 and finer(n) <= max_cells:
        candidates.append((coarser(n), n, finer(n)))
    if finer(finer(n)) <= max_cells:
        candidates.append((n, finer(n), finer(finer(n))))
    if coarser(coarser(n)) >= 1:
        candidates.append((coarser(coarser(n)), coarser(n), n))
    if not candidates:
        return None
    cells = candidates[0]
    return tuple((c, layer_um / c) for c in cells)


@track_cpu_run_boundary
def run(raw, report=lambda *args: None, artifact_dir=None, capabilities=None,
        final_state_observer=None, selected_time_observer=None, selected_time_s=None,
        local_history_observer=None, local_history_indices_ijk=None, run_progress=None):
    requested_p, requested_m = validate(raw)
    requested_backend = requested_p["backend"]
    p, m = requested_p, requested_m
    # Standard powder-layer reference execution uses the layer-conforming grid.
    # Mesh studies and auto-dispatched standard powder runs use the NumPy
    # reference even when another backend could be selected automatically.
    layer_mesh_study = (p["study"] == "mesh" and p["mode"] == "standard"
                        and p["surfaceMode"] == "powder-layer"
                        and requested_backend in ("auto", "reference"))
    automatic_reference_powder = (p["mode"] == "standard" and p["surfaceMode"] == "powder-layer"
                                  and p["backend"] == "auto")
    if ((layer_mesh_study or automatic_reference_powder)
            and p.get("powderGridPolicy") != "layer-conforming"):
        execution_input = dict(raw)
        execution_input.update(backend="reference", powderGridPolicy="layer-conforming")
        p, m = validate(execution_input)
    bare = p["surfaceMode"] == "bare-plate"
    analytical = None if bare else screening(p, m)
    fallback = p["mode"] == "high-fidelity"
    use_foam = p["backend"] == "openfoam-thermal" or (p["backend"] == "auto" and (capabilities or {}).get("openfoamThermal"))
    thermal_solver = transient
    if use_foam:
        from lpbf_openfoam import thermal
        thermal_solver = thermal
    validate_cpu_progress(run_progress, p)
    if run_progress is not None and thermal_solver is not transient:
        raise ValueError("Run progress supports standard reference CPU runs without a study only")
    if final_state_observer is not None:
        if not callable(final_state_observer):
            raise ValueError("Final state observer must be callable")
        _require_reference_powder_observer(p, "Final state capture supports standard reference powder-layer runs only", thermal_solver)
    if selected_time_observer is not None:
        if not callable(selected_time_observer):
            raise ValueError("Selected-time observer must be callable")
        _require_reference_powder_observer(p, "Selected-time capture supports standard reference powder-layer runs only", thermal_solver)
        segments, _ = scan_segments(p)
        if (isinstance(selected_time_s, bool) or not isinstance(selected_time_s, (int, float))
                or not math.isfinite(selected_time_s) or selected_time_s <= 0
                or not any(selected_time_s == segment["end_s"] for segment in segments)):
            raise ValueError("Selected time must be an existing scan-segment end event")
    elif selected_time_s is not None:
        raise ValueError("Selected time requires a selected-time observer")
    if local_history_observer is not None or local_history_indices_ijk is not None:
        if local_history_observer is None or not callable(local_history_observer):
            raise ValueError("Local history observer must be callable")
        _require_reference_powder_observer(p, "Local history supports standard reference powder-layer runs only", thermal_solver)
    result = dict(schemaVersion=1, requestedMode=p["mode"], effectiveMode="screening" if fallback else p["mode"],
                  solver=dict(id=("layered-enthalpy-fv-1" if p.get("thermalModelId") == "layered-plate-enthalpy-v1"
                                  else "rosenthal+goldak" if p["mode"] == "screening" or fallback else VERSION),
                              version=VERSION, openfoam=(capabilities or {}).get("openfoamVersion")),
                  settings=p, material=m, requestedBackend=requested_backend,
                  confidence="low", validationStatus="unvalidated", productionReady=False,
                  label=("Screening only" if p["mode"] == "screening" or fallback
                         else "Unvalidated transient thermal (boiling-capped: temperature clipped at T_boil, excess enthalpy retained in-cell; not an evaporation model)"
                         if p.get("evaporationModel", False) else "Unvalidated transient thermal"),
                  provenance=dict(inputHash=hashlib.sha256(json.dumps(requested_p, sort_keys=True, allow_nan=False).encode()).hexdigest(),
                                  executionInputHash=hashlib.sha256(json.dumps(p, sort_keys=True, allow_nan=False).encode()).hexdigest(),
                                  implementationHash=implementation_fingerprint(),
                                  implementationFingerprintSchema=IMPLEMENTATION_FINGERPRINT_SCHEMA, materialVersion=m["version"],
                                  solverBinaryHash=(capabilities or {}).get("binaryHash"),
                                  createdAt=datetime.datetime.now(datetime.timezone.utc).isoformat()),
                  analyticalComparison=analytical,
                  assumptions=["SI internal units; beam diameter is 1/e^2 intensity diameter.",
                               ("evaporationModel=true: no resolved momentum, Marangoni flow, evaporation, recoil, VOF, keyhole or pores. "
                                "Above the boiling enthalpy the inversion caps T at T_boil and keeps the excess enthalpy in the cell; "
                                "no mass or energy leaves the domain (see boilingCap). Liquid conductivity is multiplied by "
                                "1+(marangoniMultiplier-1)*f_liq, an isotropic surrogate (estimated, uncited)."
                                if p.get("evaporationModel", False) else
                                "No resolved momentum, Marangoni flow, evaporation, recoil, VOF, keyhole or pores."),
                               "Estimated material laws; fixed reference density conserves mass on a stationary grid.",
                               ("Homogeneous solid bare plate; no powder or deposited layer."
                                if bare else "Uniform effective powder, irreversible conductivity densification; no resolved powder particles."),
                               ("Gaussian penetration is an explicit model input, independent of mesh; cell-integrated source uses two time quadrature nodes and first-order Euler. Absorbed power is normalized over the represented domain."
                                if bare else "Gaussian penetration equals layer thickness, independent of mesh. Cell-integrated source uses two time quadrature nodes; thermal evolution remains first-order Euler. Absorbed power normalized over represented domain."
                                if p["mode"] in ("standard", "calibration") else "Analytical screening has no resolved transient heat source or time integration."),
                               ("Bare surface is fixed at z=0 with whole cells below it; no cut-cell interface."
                                if bare else "Transient layer activation uses whole cells selected by their centers; source surface clipping does not implement cut-cell mass or conduction. Inspect numerical resolution diagnostics when available."),
                               "Geometry is the molten-domain extent at the earliest maximum volume over accepted timesteps; playback is sparse and multi-track pools may be disconnected. Sampling loss does not bound timestep or mesh error.",
                               ("Bare-plate W/D is the ever-liquidus cell extent on the YZ plane nearest the +X track midpoint; it is a thermal proxy for the optical cross section."
                                if bare else "Cross section is the largest scan-normal slab of liquidus cells at the peak-volume step (slab one projected cell wide, cell volume over slab thickness); within about 6 % of pi/4*W*D on a fine grid, coarse-grid voxel scatter remains."),
                               "R = -dT/dt / |grad T| at linearly reconstructed cooling liquidus crossings; gradient vectors are interpolated in time. G, R, G×R are separately event-averaged; G <= 1e-6 K/m is excluded.",
                               "Ma and laser-travel Pe are screening numbers, not resolved velocities.",
                               "Thermal history is input for subsequent mechanics; no residual stress, distortion or cracking prediction."],
                  fallbackReason=("OpenFOAM is installed but a qualified free-surface LPBF solver is not registered."
                                  if (capabilities or {}).get("openfoamVersion") else "OpenFOAM / a qualified free-surface LPBF solver is unavailable in this worker.") if fallback else None)
    if p["mode"] in ("standard", "calibration"):
        n_runs = 1 if p["study"] == "none" else 3
        if run_progress is not None:
            thermal_result = thermal_solver(
                p, m, lambda f, msg: report(f/n_runs, msg), artifact_dir,
                final_state_observer=final_state_observer,
                selected_time_observer=selected_time_observer, selected_time_s=selected_time_s,
                local_history_observer=local_history_observer,
                local_history_indices_ijk=local_history_indices_ijk, run_progress=run_progress)
        elif local_history_observer is not None:
            thermal_result = thermal_solver(
                p, m, lambda f, msg: report(f/n_runs, msg), artifact_dir,
                final_state_observer=final_state_observer,
                selected_time_observer=selected_time_observer, selected_time_s=selected_time_s,
                local_history_observer=local_history_observer,
                local_history_indices_ijk=local_history_indices_ijk)
        elif final_state_observer is None and selected_time_observer is None:
            thermal_result = thermal_solver(p, m, lambda f, msg: report(f/n_runs, msg), artifact_dir)
        elif selected_time_observer is None:
            thermal_result = thermal_solver(p, m, lambda f, msg: report(f/n_runs, msg), artifact_dir,
                                            final_state_observer=final_state_observer)
        elif final_state_observer is None:
            thermal_result = thermal_solver(
                p, m, lambda f, msg: report(f/n_runs, msg), artifact_dir,
                selected_time_observer=selected_time_observer, selected_time_s=selected_time_s)
        else:
            thermal_result = thermal_solver(
                p, m, lambda f, msg: report(f/n_runs, msg), artifact_dir,
                final_state_observer=final_state_observer,
                selected_time_observer=selected_time_observer, selected_time_s=selected_time_s)
        result.update(thermal_result)
        if use_foam:
            result["solver"]["id"] = "metalliksaThermal-OpenFOAM14-6"
        if p["study"] != "none":
            trials = []
            level_errors = []
            key = "mesh_um" if p["study"] == "mesh" else "maxDt_s"
            if layer_mesh_study:
                plan = _layer_aligned_mesh_levels(p)
                level_specs = ([dict(level=name, requested=spacing, cellsPerLayer=count)
                                for name, (count, spacing) in zip(("coarse", "medium", "fine"), plan)]
                               if plan else [])
                requested_spacing = p["mesh_um"]
                if not plan:
                    level_errors.append(dict(level="mesh-plan", requested=requested_spacing,
                        reason="Three layer-aligned meshes with refinement ratio >= 1.3 do not fit between one cell per layer and the 5 um minimum spacing."))
                # The requested solve is one member of the sorted three-grid
                # sequence; run the other two with identical model/material.
                ordered_results = [None, None, None]
                if plan:
                    base_cells = max(1, int(math.ceil(p["layer_um"] / requested_spacing - 1e-12)))
                    base_index = next((i for i, (count, _) in enumerate(plan) if count == base_cells), None)
                    if base_index is None:
                        level_errors.append(dict(level="mesh-plan", requested=requested_spacing,
                            reason="The requested mesh is outside the selected three-level layer-aligned window."))
                    else:
                        ordered_results[base_index] = result
                        completed_solves = 1
                        for index, spec in enumerate(level_specs):
                            if index == base_index:
                                continue
                            q = copy.deepcopy(p)
                            q[key] = spec["requested"]
                            progress_slot = completed_solves
                            try:
                                ordered_results[index] = thermal_solver(
                                    q, m, lambda f, msg, i=progress_slot: report((i+f)/3, msg))
                            except Exception as exc:
                                level_errors.append(dict(level=spec["level"], requested=spec["requested"],
                                    reason=str(exc)[:500] or type(exc).__name__))
                            completed_solves += 1
                trials = ordered_results
            elif key == "maxDt_s":
                # The explicit step is dt = min(maxDt, 0.12 dx^2/alpha, r_beam/(4 v), events, row-sum
                # bound); coarsening maxDt above those caps changes nothing. Refine BELOW the realised
                # mean step instead: the requested run is the coarse level, the medium and fine levels
                # cap dt at meanDt/sqrt(2) and meanDt/2 (ratio sqrt(2) >= 1.3, Celik et al. 2008).
                trials.append(result)
                base_dt = result["discretization"]["meanDt_s"]
                for index, scale in enumerate((math.sqrt(2.), 2.)):
                    q = copy.deepcopy(p); q[key] = max(BOUNDS["maxDt_s"][0], base_dt / scale)
                    try:
                        trial = thermal_solver(q, m, lambda f, msg, i=index: report((i+1+f)/3, msg))
                    except Exception as exc:
                        trials.append(None)
                        level_errors.append(dict(level=("medium", "fine")[index],
                                                 requested=q[key], reason=str(exc)[:500] or type(exc).__name__))
                        continue
                    trials.append(trial)
            else:
                # Explicitly selected non-reference mesh protocols keep the legacy coarsening levels.
                for index, scale in enumerate((2., math.sqrt(2.))):
                    q = copy.deepcopy(p); q[key] *= scale
                    try:
                        trial = thermal_solver(q, m, lambda f, msg: report((index+1+f)/3, msg))
                    except Exception as exc:
                        trials.append(None)
                        level_errors.append(dict(level=("coarse", "medium")[index],
                                                 requested=q[key], reason=str(exc)[:500] or type(exc).__name__))
                        continue
                    trials.append(trial)
                trials.append(result)
            resolution_key = "mesh_m" if key == "mesh_um" else "meanDt_s"
            actual = [v["discretization"][resolution_key] if v is not None else None for v in trials]
            metric_key = "midTrackCrossSection" if bare else "metrics"
            metric_names = (("width_um", "depth_um") if bare else
                            ("width_um", "depth_um", "volume_um3", "thermalGradient_K_m",
                             "solidificationRate_m_s", "coolingRate_K_s"))
            checks = ({k: dict(status="failed", reason="Invalid study levels: " + "; ".join(
                            f"{v['level']}: {v['reason']}" for v in level_errors)) for k in metric_names}
                      if level_errors else
                      {k: convergence([v[metric_key][k] for v in trials], actual) for k in metric_names})
            result["convergenceStudy"] = dict(kind=p["study"], spacings=actual,
                metricSource=metric_key,
                results=[v[metric_key] if v is not None else None for v in trials], checks=checks,
                status="failed" if level_errors else "complete",
                failedLevels=level_errors)
            if layer_mesh_study:
                result["convergenceStudy"].update(
                    protocol="layer-aligned-three-grid-cpu-reference-v2-celik-ratio",
                    gridPolicy="layer-conforming",
                    requestedBackend=requested_backend,
                    executionBackend="reference",
                    cellsPerLayer=[spec["cellsPerLayer"] for spec in level_specs],
                    requestedMesh_um=requested_p["mesh_um"])
            if bare:
                targets = dict(energyRelativeErrorMax=.01, finestPairWidthDepthRelativeChangeMax=.05,
                               minimumLevels=3, source="docs/DIGITAL_TWIN_MASTER_PLAN_2026-09-21.md#11")
                if level_errors:
                    reason = "Invalid study levels: " + "; ".join(
                        f"{v['level']}: {v['reason']}" for v in level_errors)
                    verdicts = {name: dict(status="failed", reason=reason) for name in metric_names}
                else:
                    verdicts = {}
                    for name in metric_names:
                        values = [v[metric_key][name] for v in trials]
                        change = abs(values[-1]-values[-2])/values[-1] if all(x > 0 for x in values) else None
                        location_resolved = all(v[metric_key]["midpointResolvedWithinQuarterCell"] for v in trials)
                        status = ("inconclusive" if change is None else "failed" if change > .05 else
                                  "inconclusive" if not location_resolved else
                                  "pass" if checks[name]["status"] == "numerically-converging" else "inconclusive")
                        verdicts[name] = dict(status=status, finestPairRelativeChange=change,
                                             midpointLocationResolved=location_resolved)
                energies = [v["energyBalance"]["relativeError"] for v in trials if v is not None]
                energy_status = "pass" if all(e <= .01 for e in energies) else "failed"
                states = [energy_status, *(v["status"] for v in verdicts.values())]
                result["convergenceStudy"]["acceptance"] = dict(targets=targets, metrics=verdicts,
                    energyStatus=energy_status, maximumEnergyRelativeError=max(energies) if energies else None,
                    status="failed" if "failed" in states else "inconclusive" if "inconclusive" in states else "pass")
    else:
        result["metrics"] = analytical["goldak"]
    g = result["metrics"]
    w, d, length = g["width_um"], g["depth_um"], g["length_um"]
    result["geometricDefectScreen"] = None if bare else defect_diagnostics(w, d, length, p["hatch_um"], p["layer_um"],
        aggregate=p["tracks"] > 1 and p["mode"] in ("standard", "calibration"))
    lof = w <= p["hatch_um"] or d <= p["layer_um"]
    kh = d/max(w, 1e-12) > .5
    result["regime"] = "keyhole-risk (screening)" if kh else "conduction assumption"
    # No balling mainRisk here: the balling screen (lpbf_defect_diagnostics.balling_screen) is calibrated on the
    # Eagar-Tsai liquidus L/W, which this path does not compute (the former length > pi*W rule is retired).
    result["mainRisk"] = "lack-of-fusion" if lof else "keyhole (screening)" if kh else "not established"
    result["recommendation"] = "Reduce hatch/layer spacing; verify penetration experimentally." if lof else "Reduce power or increase speed; verify with free-surface CFD." if kh else "Compare with measured tracks before changing process parameters."
    result["riskScope"] = "Geometric screening only; no probability, density qualification or solidification cracking assessment."
    if bare:
        result.update(regime="bare-plate conduction assumption", mainRisk="not assessed",
                      recommendation="Use the midpoint section only after beam and material conditions are resolved.",
                      riskScope="Bare-plate thermal proxy; no powder defect, flow, porosity, or experimental qualification.",
                      beamConvention=dict(input="1/e2 intensity diameter", nistReported="D4sigma second-moment diameter",
                          idealGaussianRelation="For I(r)=I0 exp(-2r^2/w^2), sigma_x=w/2; D4sigma=4sigma_x=2w=1/e2 diameter.",
                          mappingStatus="conditional ideal-Gaussian identity; actual measured profile not established",
                          nistSource="https://www.nist.gov/document/amb2022-03-measurement-and-challenge-descriptions-version-101"),
                      experimentalComparison=dict(status="unavailable", reason=(
                          "NIST AMB2022-03 uses a 10 mm bare track and reports D4sigma. "
                          "The ideal-Gaussian diameter identity does not establish the actual beam profile; "
                          "the bounded reference mesh also cannot solve the full-length midpoint. "
                          "The thermal section is not the mean of six etched optical sections from three tracks at 4.9 and 6.0 mm.")))
    if p["tracks"] > 1 and p["mode"] in ("standard", "calibration"):
        field_overlap = result.get("fieldOverlapDiagnostics")
        if field_overlap and field_overlap.get("hasInterTrackGap"):
            result["mainRisk"] = "lack-of-fusion (field-resolved inter-track gap)"
            result["regime"] = "conduction assumption; field-resolved inter-track lack-of-fusion"
            result["recommendation"] = "Reduce hatch spacing; simulated melt pools leave unmelted powder gap between adjacent tracks."
        elif field_overlap and field_overlap.get("interTrackLackOfFusion"):
            result["mainRisk"] = "lack-of-fusion (insufficient inter-track penetration)"
            result["regime"] = "conduction assumption; marginal inter-track penetration"
            result["recommendation"] = "Increase power or decrease speed; inter-track penetration does not reach layer thickness."
        elif field_overlap:
            result["mainRisk"] = "keyhole (screening)" if kh else "continuous inter-track fusion"
            result["regime"] = "conduction assumption; continuous inter-track fusion"
            result["recommendation"] = "Field-resolved inter-track fusion verified; verify penetration and porosity with free-surface CFD or experiment."
        else:
            result["mainRisk"] = "not assessed from aggregate multi-track extents"
            result["regime"] = "conduction assumption; local flow regime unresolved"
            result["recommendation"] = "Inspect saved temperature fields and remelting history; aggregate width cannot establish inter-track fusion."
            g["trackOverlapRatio"] = None
    if p.get("measurements"):
        result["measurementComparison"] = {key: compare([g[key]]*len(p["measurements"]), [row[key] for row in p["measurements"]]) for key in ("width_um", "depth_um")}
    result["resourceEstimate"] = resource_estimate(p,m)
    result["unresolvedPhysics"] = dict(freeSurface=None, velocity=None, evaporationMassFlux=None,
        evaporationLoss=None, recoilPressure=None, keyholeDepth=None, porosityProbability=None, residualStress=None)
    if p.get("measurements"):
        result["measurementEvidence"] = measurement_evidence(p["measurements"],p)
        result["experimentalValidation"] = "Experimental validation pending"
        if any(v["sameProcessVector"] != "matched" for v in result["measurementEvidence"]):
            for value in result["measurementComparison"].values():
                value["calibrationFactor"] = None
                value["note"] += " Process vector unverified; calibration factor withheld."
    result["confidenceReason"] = f"{m['quality']} material data and unresolved flow; no independent experimental validation."
    if any(isinstance(v,(int,float)) and (not math.isfinite(v) or v < 0) for v in g.values()):
        raise ValueError("Nonfinite or negative physical result")
    result["coreContract"] = build_core_contract(p, m, result["solver"]["id"], result["effectiveMode"])
    enforce_thermal_balances(result)
    write_artifacts(result, artifact_dir)
    json.dumps(result, allow_nan=False)
    return result


if __name__ == "__main__":
    import sys
    print(json.dumps(run(json.load(sys.stdin)), allow_nan=False))
