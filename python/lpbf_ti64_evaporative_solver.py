"""Opt-in 3D fixed-surface Ti64 enthalpy FV estimate, CPU/JSON only.

The legacy thermal authority is retained, with explicitly declared endpoint
continuation. Ti-species evaporation removes energy at the fixed top face;
diagnostic emitted mass does not change domain mass, composition or geometry.
"""
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
import sys
import time as clock

import numpy as np

from lpbf_core_physics import (calculate_mesh_domain, enthalpy_table, property_at,
                               scan_segments, thermal_si_inputs, SOURCE_INTEGRATION)
from lpbf_heat_source import (source_limited_step, require_source_capture,
                              MINIMUM_SOURCE_CAPTURE_FRACTION)
from lpbf_simulation import (validate as _legacy_validate, implementation_fingerprint,
                             _conduction_rate_and_diagonal)
from lpbf_ti64_evaporation import (validate_config, surface_state, update_onset,
                                   SOURCE_PROFILE)


MODEL_ID = "ti64-fixed-surface-evaporation-v1"
SCHEMA = "lpbf-ti64-evaporative-result-v1"
STEFAN_BOLTZMANN = 5.670374419e-8
SETTINGS = dict(stepMethod="explicit-Euler-conservative-enthalpy-FV",
                conduction="shared-harmonic-interior-faces",
                sourceIntegration=SOURCE_INTEGRATION,
                stabilitySafety=.9, sourceIncrementLimit_K=25.,
                maxCandidateRetries=20, maximumAcceptedSteps=2000000,
                maximumCells=600000, timeout_s=300.,
                bottomBoundary="isothermal-at-preheat-half-cell",
                lateralBoundary="adiabatic", surface="fixed-top-face",
                geometry="instantaneous-liquidus-extent-at-peak-melt-volume-snapshot",
                minimumSourceCapture=MINIMUM_SOURCE_CAPTURE_FRACTION,
                radiationConstant_W_m2K4=STEFAN_BOLTZMANN)
_PROCESS_DEFAULTS = dict(power_W=200., speed_mm_s=800., beamDiameter_um=80.,
                         preheat_C=80., mesh_um=20., maxDt_s=1e-6,
                         trackLength_um=600., cooling_s=.0005,
                         sourcePenetration_um=20., convection_W_m2K=20.)
_FIXED = dict(material="Ti-6Al-4V", backend="reference", surfaceMode="bare-plate",
              mode="standard", layers=1, tracks=1, study="none")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _request(raw):
    """Reject unused legacy flags before touching its broader validator."""
    if not isinstance(raw, dict) or set(raw)-set(_PROCESS_DEFAULTS)-set(_FIXED)-{"evaporation"}:
        raise ValueError("Unknown or unsupported evaporative solver input fields")
    if "evaporation" not in raw:
        raise ValueError("An explicit evaporation object is required")
    for key, expected in _FIXED.items():
        if key in raw and (type(raw[key]) is not type(expected) or raw[key] != expected):
            raise ValueError(f"{key} must be {expected!r} for this solver")
    process = {**_PROCESS_DEFAULTS, **{key: raw[key] for key in _PROCESS_DEFAULTS if key in raw}}
    for key, value in process.items():
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite real number")
        process[key] = float(value)
    # End laser-on exactly at one track's end; no unused deposition/dwell flags.
    p, m = _legacy_validate({**process, **_FIXED, "dwell_s": 0., "scanAngle_deg": 0.,
                             "strategy": "unidirectional", "barePlateGeometry": "square"})
    evaporation = validate_config(raw["evaporation"], m["liquidus_K"])
    normalized_evaporation = {key: getattr(evaporation, key) for key in (
        "transitionLow_K", "transitionHigh_K", "ambientPressure_Pa", "returnFraction", "maxTemperature_K")}
    if evaporation.surfaceTension_N_m is not None:
        normalized_evaporation["surfaceTension_N_m"] = evaporation.surfaceTension_N_m
    normalized = {**process, **_FIXED, "evaporation": normalized_evaporation}
    return normalized, p, m, evaporation


def _thermal_table(material, maximum_K):
    """Extend the returned authority enthalpy law; never change its material."""
    temperatures, enthalpies = enthalpy_table(material)
    endpoint_cp = float(material["table"][-1][3])
    if endpoint_cp <= 0 or not math.isfinite(endpoint_cp):
        raise ValueError("Continuation requires a positive finite endpoint heat capacity")
    if maximum_K > temperatures[-1]:
        return (np.r_[temperatures, maximum_K],
                np.r_[enthalpies, enthalpies[-1]+endpoint_cp*(maximum_K-temperatures[-1])])
    value = np.interp(maximum_K, temperatures, enthalpies)
    keep = temperatures < maximum_K
    return np.r_[temperatures[keep], maximum_K], np.r_[enthalpies[keep], value]


def _accepted_step(temperature, enthalpy, requested_dt_s, *, dx, rho, cp,
                   conductivity, temperatures, enthalpies, reference_h,
                   ambient_K, evaporation, convection, emissivity,
                   base_boundary=True, source_factory=None):
    """Compute one admitted candidate from immutable accepted fields.

    The same conservative kernel serves the real field and manufactured tests.
    source_factory(dt, passive_rate, capacity) follows source_limited_step's
    return contract and is re-evaluated after every rejected candidate. No clock,
    gate or cumulative ledger lives in this function, so rejection cannot commit.
    """
    active = np.ones_like(temperature, dtype=bool)
    passive, diagonal = _conduction_rate_and_diagonal(temperature, conductivity, active, dx)
    top = temperature[:, :, -1]
    vapor = surface_state(top, evaporation)
    radiative_convective = (convection*(top-ambient_K)
                            +emissivity*STEFAN_BOLTZMANN*(top**4-ambient_K**4))
    bottom = (2*conductivity[:, :, 0]*(temperature[:, :, 0]-ambient_K)/dx
              if base_boundary else np.zeros_like(top))
    passive[:, :, 0] -= bottom/dx
    passive[:, :, -1] -= (radiative_convective+vapor["heat_flux_W_m2"])/dx
    if base_boundary:
        diagonal[:, :, 0] += 2*conductivity[:, :, 0]/dx**2
    diagonal[:, :, -1] += (convection+4*emissivity*STEFAN_BOLTZMANN*top**3
                            +vapor["heat_flux_derivative_W_m2K"])/dx
    # Conservative lower capacity across phase changes, not the mushy apparent cp.
    capacity = rho*cp
    dt = min(requested_dt_s, float(np.min(SETTINGS["stabilitySafety"]*capacity/
                                           np.maximum(diagonal, 1e-300))))
    source_retries = 0
    for rejected in range(SETTINGS["maxCandidateRetries"]+1):
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError("No positive finite candidate timestep")
        if source_factory is None:
            source, rate, capture = np.zeros_like(temperature), passive, 1.
        else:
            dt, source, rate, capture, retries = source_factory(dt, passive, capacity)
            source_retries += retries
        require_source_capture(capture, MINIMUM_SOURCE_CAPTURE_FRACTION)
        candidate_H = enthalpy+dt*rate
        candidate_h = candidate_H/rho+reference_h
        valid = (np.isfinite(candidate_h).all() and
                 float(candidate_h.min()) >= enthalpies[0] and
                 float(candidate_h.max()) <= enthalpies[-1])
        if valid:
            candidate_T = np.interp(candidate_h, enthalpies, temperatures)
            valid = (np.isfinite(candidate_T).all() and np.all(candidate_T > 0)
                     and float(candidate_T.max()) <= evaporation.maxTemperature_K)
        if valid:
            return dict(temperature=candidate_T, enthalpy=candidate_H, dt_s=dt,
                        input_J=float(source.sum())*dx**3*dt,
                        base_J=float(bottom.sum())*dx**2*dt,
                        radiativeConvective_J=float(radiative_convective.sum())*dx**2*dt,
                        evaporative_J=float(vapor["heat_flux_W_m2"].sum())*dx**2*dt,
                        diagnosticMass_kg=float(vapor["mass_flux_kg_m2_s"].sum())*dx**2*dt,
                        minimumCapture=float(capture), rejectedCandidates=rejected,
                        sourceRetries=source_retries)
        dt *= .5
    raise ValueError("Thermal candidate exceeds finite enthalpy/scenario range after bounded retries; no clipping")


def _snapshot(temperature, axes, dx, liquidus_K, time_s):
    melt = temperature >= liquidus_K
    indices = np.where(melt)
    count = int(melt.sum())
    if count:
        x, y, z = (axis[index] for axis, index in zip(axes, indices))
        length, width = float(np.ptp(x)+dx)*1e6, float(np.ptp(y)+dx)*1e6
        depth = float(-np.min(z)+dx/2)*1e6
    else:
        length = width = depth = 0.
    return dict(time_s=float(time_s), moltenCellCount=count, width_um=width,
                depth_um=depth, length_um=length, volume_um3=count*dx**3*1e18,
                truncated=bool(melt[0].any() or melt[-1].any() or melt[:, 0].any()
                               or melt[:, -1].any() or melt[:, :, 0].any()))


def _identity(normalized, material):
    root = Path(__file__).parent
    modules = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
               ("lpbf_ti64_evaporative_solver.py", "lpbf_ti64_evaporation.py")}
    default_hash = implementation_fingerprint()
    implementation_hash = hashlib.sha256(_canonical(dict(modelId=MODEL_ID,
        defaultImplementationHash=default_hash, moduleSha256=modules, settings=SETTINGS)).encode()).hexdigest()
    request_hash = hashlib.sha256(_canonical(dict(inputs=normalized, material=material,
                                                   implementationHash=implementation_hash)).encode()).hexdigest()
    return dict(implementationHash=implementation_hash,
                implementationFingerprintSchema="ti64-evaporative-dependency-closure-v1",
                defaultImplementationHash=default_hash, moduleSha256=modules,
                requestSha256=request_hash, inputs=normalized, settings=dict(SETTINGS),
                material=material, vaporSource=dict(SOURCE_PROFILE),
                thermalContinuation=dict(method="constant-liquid-endpoint-properties",
                    starts_K=material["table"][-1][0], ends_K=normalized["evaporation"]["maxTemperature_K"],
                    endpointDensity_kg_m3=material["table"][-1][1],
                    endpointConductivity_W_mK=material["table"][-1][2],
                    endpointCp_J_kgK=material["table"][-1][3],
                    densityMethod="fixed reference density at preheat for volumetric enthalpy",
                    status="declared model assumption, not new data or source validity extension"),
                mixedSourceNote="Registry Ti64 boiling endpoint 3560.15 K retained; independent Gan Ti vapor reference 3560 K; no reconciliation or Ti64 species evolution")


def run(raw, report=lambda *args: None):
    """Solve one bare-plate track; return a distinct finite, unvalidated schema."""
    normalized, p, material, evaporation = _request(raw)
    provenance = _identity(normalized, material)
    domain = calculate_mesh_domain(p)
    nx, ny, nz = (domain[key] for key in ("nx", "ny", "nz"))
    if nx*ny*nz > SETTINGS["maximumCells"]:
        raise ValueError("Evaporative CPU mesh exceeds 600000 cells")
    dx, radius, substrate = (domain[key] for key in ("dx", "radius", "substrate_depth"))
    axes = ((np.arange(nx)+.5)*dx-domain["span"]/2,
            (np.arange(ny)+.5)*dx-ny*dx/2,
            (np.arange(nz)+.5)*dx-substrate)
    thermal = thermal_si_inputs(p, material)
    ambient = thermal["preheat_K"]
    tt, hh = _thermal_table(material, evaporation.maxTemperature_K)
    if not tt[0] <= ambient <= tt[-1]:
        raise ValueError("Initial state is outside the enthalpy/scenario range")
    reference_h = float(np.interp(ambient, tt, hh))
    rho = float(property_at(material, ambient, 1))
    # Explicit table continuation avoids relying on np.interp's silent endpoint clipping.
    extended_material = dict(material)
    extended_material["table"] = [list(row) for row in material["table"]]
    if evaporation.maxTemperature_K > material["table"][-1][0]:
        extended_material["table"].append([evaporation.maxTemperature_K, *material["table"][-1][1:]])
    temperature = np.full((nx, ny, nz), ambient)
    H = np.zeros_like(temperature)
    cp_floor = min(row[3] for row in material["table"])
    segments, end = scan_segments(p)
    gate = update_onset(None, surface_state(temperature[:, :, -1], evaporation), evaporation, radius, 0.)
    snapshot = _snapshot(temperature, axes, dx, material["liquidus_K"], 0.)
    peak = ambient
    time_s = 0.
    accepted, rejected, source_retries = 0, 0, 0
    energies = {key: 0. for key in ("input_J", "base_J", "radiativeConvective_J", "evaporative_J")}
    emitted_mass = 0.
    capture = 1.
    min_dt, max_dt = math.inf, 0.
    started = clock.monotonic()
    while time_s < end:
        if accepted >= SETTINGS["maximumAcceptedSteps"] or clock.monotonic()-started > SETTINGS["timeout_s"]:
            raise ValueError("Evaporative CPU solve exceeded declared resource bound")
        segment = segments[0] if time_s < segments[0]["end_s"] else None
        dt = min(p["maxDt_s"], radius/(4*thermal["speed_m_s"]), end-time_s)
        if segment is not None:
            dt = min(dt, segment["end_s"]-time_s)
        k = property_at(extended_material, temperature, 2)
        def source(candidate_dt, passive, capacity):
            return source_limited_step(axes[0], axes[2], dx, segment, time_s,
                candidate_dt, 0., radius, p["sourcePenetration_um"]*1e-6,
                thermal["absorbed_power_W"], passive, capacity, axis_y=axes[1])
        candidate = _accepted_step(temperature, H, dt, dx=dx, rho=rho,
            cp=np.full_like(temperature, cp_floor), conductivity=k,
            temperatures=tt, enthalpies=hh, reference_h=reference_h,
            ambient_K=ambient, evaporation=evaporation,
            convection=p["convection_W_m2K"], emissivity=material["emissivity"],
            source_factory=source)
        new_time = time_s+candidate["dt_s"]
        if new_time <= time_s:
            raise ValueError("Accepted timestep cannot advance the representable clock")
        # Candidate gate is constructed only after enthalpy/range admission.
        new_gate = update_onset(gate, surface_state(candidate["temperature"][:, :, -1], evaporation),
                                 evaporation, radius, new_time)
        temperature, H, gate = candidate["temperature"], candidate["enthalpy"], new_gate
        time_s = new_time
        accepted += 1
        for key in energies:
            energies[key] += candidate[key]
        emitted_mass += candidate["diagnosticMass_kg"]
        rejected += candidate["rejectedCandidates"]
        source_retries += candidate["sourceRetries"]
        capture = min(capture, candidate["minimumCapture"])
        min_dt, max_dt = min(min_dt, candidate["dt_s"]), max(max_dt, candidate["dt_s"])
        peak = max(peak, float(temperature.max()))
        molten_count = int(np.count_nonzero(temperature >= material["liquidus_K"]))
        if molten_count > snapshot["moltenCellCount"]:
            snapshot = _snapshot(temperature, axes, dx, material["liquidus_K"], time_s)
        if accepted % 100 == 0:
            report("progress", dict(acceptedStepCount=accepted, time_s=time_s))
    stored = float(H.sum())*dx**3
    loss = energies["base_J"]+energies["radiativeConvective_J"]+energies["evaporative_J"]
    residual = energies["input_J"]-loss-stored
    scale = max(abs(energies["input_J"]), abs(loss), abs(stored), 1e-12)
    energies.update(stored_J=stored, residual_J=residual, relativeResidual=abs(residual)/scale)
    reason = ("Recoil capillary onset latched; fixed-surface depth/length/volume unavailable"
              if gate["onset"] else
              "Active evaporation with missing surface tension; geometry unresolved"
              if gate["unresolvedGeometry"] else None)
    geometry = dict(snapshot)
    geometry.pop("moltenCellCount")
    if not gate["geometryAvailable"]:
        for key in ("depth_um", "length_um", "volume_um3"):
            geometry[key] = None
    geometry.update(basis="instantaneous liquidus extent at peak-melt-volume snapshot; cell bounds",
                    label="Uncalibrated fixed-surface isotherm estimate",
                    widthLabel="Conditional fixed-surface liquidus width estimate",
                    refusalReason=reason, liquidus_K=material["liquidus_K"],
                    cellResolution_um=dx*1e6)
    result = dict(schema=SCHEMA, modelId=MODEL_ID, status="completed",
        experimentalValidation=False, productionReady=False, tier="Uncalibrated estimate",
        provenance=provenance, acceptedStepCount=accepted, acceptedTime_s=time_s,
        timesteps=dict(minimum_s=min_dt, maximum_s=max_dt, rejectedCandidates=rejected,
                       sourceRetries=source_retries), energy=energies,
        diagnosticEmittedMass_kg=emitted_mass,
        diagnosticMassLabel="Integrated Ti-species emitted mass diagnostic; not ablation or material removal",
        peakTemperature_K=peak, temperatureLabel="Conditional fixed-surface temperature estimate",
        geometry=geometry, gate=gate,
        fieldSummary=dict(shape=[nx, ny, nz], dx_m=dx,
                          minimumFinalTemperature_K=float(temperature.min()),
                          maximumFinalTemperature_K=float(temperature.max()),
                          minimumSourceCapture=capture))
    _canonical(result)  # Reject all nonfinite JSON, including derived provenance.
    return result


def main():
    try:
        raw = json.load(sys.stdin)
        result = run(raw)
    except (ValueError, TypeError, OverflowError) as exc:
        print(json.dumps(dict(schema=SCHEMA, modelId=MODEL_ID, status="error", error=str(exc)), allow_nan=False))
        return 1
    print(_canonical(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
