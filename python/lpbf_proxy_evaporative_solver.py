"""Opt-in 3D fixed-surface enthalpy FV estimate for 316L and IN718 on sourced proxy profiles, CPU/JSON only.

Research models. 316L uses the Gan 2021 SS316 column; IN718 uses Fang 2021 thermal inputs
with a pure-Ni vapor law (lpbf_proxy_vapor_profiles). The registry's own 316L and IN718
transient tables are not used. Numerics, grid, source and gate mirror
lpbf_ti64_evaporative_solver and lpbf_alsi10mg_evaporative_solver; Ti64 geometry/table
helpers are imported unchanged. Diagnostic emitted mass does not change domain mass,
composition or geometry. The transition thresholds have no source for SS316 or Ni, so the
output label is Unresolved while they stay at their declared defaults.

The request must name its alloy in ``material`` ("316L Stainless Steel" or "Inconel 718").
"""
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
import sys
from types import MappingProxyType

import numpy as np

from lpbf_core_physics import property_at, scan_segments, thermal_si_inputs
from lpbf_heat_source import (source_limited_step, require_source_capture,
                              MINIMUM_SOURCE_CAPTURE_FRACTION)
from lpbf_material_registry import reidentify
from lpbf_simulation import (validate as _legacy_validate, implementation_fingerprint,
                             _conduction_rate_and_diagonal)
from lpbf_ti64_evaporative_solver import (SETTINGS as _TI64_SETTINGS, STEFAN_BOLTZMANN,
                                          _canonical, _fixed_surface_grid, _snapshot,
                                          _thermal_table)
from lpbf_proxy_evaporation import (scenario_evidence, surface_state, update_onset, validate_config)
from lpbf_proxy_vapor_profiles import IN718_PROFILE, SS316L_PROFILE


SETTINGS = dict(_TI64_SETTINGS)
ALLOYS = MappingProxyType({
    "316L Stainless Steel": MappingProxyType(dict(
        profile=SS316L_PROFILE, shortName="316L",
        modelId="ss316l-gan2021-ss316-proxy-fixed-surface-evaporation-v1",
        schema="lpbf-ss316l-evaporative-result-v1",
        researchLabel="Research model: 316L on a Gan 2021 SS316 proxy profile. Not experimentally validated.",
        materialId="proxy:gan2021-ss316-for-316l", provenanceClass="literature-proxy-ss316", proxyAlloy="SS316",
        profileLabel="a Gan 2021 SS316 proxy profile",
        massLabel=("Integrated effective Fe-rich species (SS316 proxy) emitted mass diagnostic; "
                   "not ablation or material removal"))),
    "Inconel 718": MappingProxyType(dict(
        profile=IN718_PROFILE, shortName="IN718",
        modelId="in718-fang2021-ni-proxy-fixed-surface-evaporation-v1",
        schema="lpbf-in718-evaporative-result-v1",
        researchLabel=("Research model: IN718 on a Fang 2021 thermal profile with a pure-Ni vapour proxy. "
                       "Not experimentally validated."),
        materialId="proxy:fang2021-in718-with-knapp2019-ni-vapour", provenanceClass="literature-proxy-in718-ni-vapour",
        proxyAlloy="pure Ni (vapour law only)",
        profileLabel="a Fang 2021 IN718 thermal profile with a pure-Ni vapour law",
        massLabel="Integrated Ni-species (pure Ni proxy) emitted mass diagnostic; not ablation or material removal")),
})
_PROCESS_DEFAULTS = dict(power_W=200., speed_mm_s=800., beamDiameter_um=80.,
                         preheat_C=80., mesh_um=20., maxDt_s=1e-6,
                         trackLength_um=600., cooling_s=.0005,
                         sourcePenetration_um=20., convection_W_m2K=20.)
_FIXED = dict(backend="reference", surfaceMode="bare-plate",
              mode="standard", layers=1, tracks=1, study="none")
_MODULES = ("lpbf_proxy_evaporative_solver.py", "lpbf_proxy_evaporation.py", "lpbf_proxy_vapor_profiles.py",
            "lpbf_ti64_evaporative_solver.py", "lpbf_ti64_evaporation.py")
# Presentation choice, not a physical threshold: the peak-temperature warning below is shown when the peak
# is within this many kelvin of the scenario ceiling maxTemperature_K. No source gives this margin.
PEAK_NEAR_CEILING_MARGIN_K = 500.0
REFUSAL_ONSET = ("The model's recoil/capillary onset criterion was exceeded; surface deformation "
                 "and keyhole geometry are not resolved, so depth, length and volume are not reported.")
REFUSAL_UNRESOLVED = ("Melt geometry needs a keyhole-onset check. Supply surface tension, "
                      "chamber pressure, beam radius and a compatible recoil model.")


def alloy_spec(material):
    if not isinstance(material, str) or material not in ALLOYS:
        raise ValueError("material must be '316L Stainless Steel' or 'Inconel 718' for this solver")
    return ALLOYS[material]


def _proxy_material(registry_material, spec):
    """Relabel the registry snapshot built from the supplied proxy table; never the registry's own table."""
    m = dict(registry_material)
    profile = spec["profile"]
    m.update(quality="literature-proxy-unvalidated", provenanceClass=spec["provenanceClass"],
             materialId=spec["materialId"], proxyOf=profile.targetAlloy, proxyAlloy=spec["proxyAlloy"],
             proxySourceId=profile.sourceProfile["sourceId"], proxyDisclosure=profile.disclosure)
    return reidentify(m)


def _request(raw):
    """Reject unused legacy flags before touching its broader validator."""
    allowed = set(_PROCESS_DEFAULTS) | set(_FIXED) | {"material", "evaporation"}
    if not isinstance(raw, dict) or set(raw)-allowed:
        raise ValueError("Unknown or unsupported evaporative solver input fields")
    spec = alloy_spec(raw.get("material"))
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
    fixed = {**_FIXED, "material": raw["material"]}
    profile = spec["profile"]
    p, m = _legacy_validate({**process, **fixed, "dwell_s": 0., "scanAngle_deg": 0.,
                             "strategy": "unidirectional", "barePlateGeometry": "square",
                             "properties": profile.materialProperties()})
    m = _proxy_material(m, spec)
    evaporation = validate_config(raw["evaporation"], m["liquidus_K"], profile)
    normalized_evaporation = {key: getattr(evaporation, key) for key in (
        "transitionLow_K", "transitionHigh_K", "ambientPressure_Pa", "returnFraction", "maxTemperature_K")}
    if evaporation.surfaceTension_N_m is not None:
        normalized_evaporation["surfaceTension_N_m"] = evaporation.surfaceTension_N_m
    normalized = {**process, **fixed, "evaporation": normalized_evaporation}
    return normalized, p, m, evaporation


def _accepted_step(temperature, enthalpy, requested_dt_s, *, dx, rho, cp,
                   conductivity, temperatures, enthalpies, reference_h,
                   ambient_K, evaporation, convection, emissivity,
                   base_boundary=True, source_factory=None):
    """Same admitted-candidate kernel as the Ti64 and AlSi10Mg solvers, with the bound proxy surface law.

    Computed from immutable accepted fields; rejection cannot commit any ledger.
    """
    passive, diagonal = _conduction_rate_and_diagonal(
        temperature, conductivity, np.ones_like(temperature, dtype=bool), dx)
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


def _identity(normalized, material):
    spec = alloy_spec(normalized["material"])
    profile = spec["profile"]
    root = Path(__file__).parent
    modules = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in _MODULES}
    default_hash = implementation_fingerprint()
    implementation_hash = hashlib.sha256(_canonical(dict(modelId=spec["modelId"],
        defaultImplementationHash=default_hash, moduleSha256=modules, settings=SETTINGS)).encode()).hexdigest()
    request_hash = hashlib.sha256(_canonical(dict(inputs=normalized, material=material,
                                                   implementationHash=implementation_hash)).encode()).hexdigest()
    return dict(implementationHash=implementation_hash,
                implementationFingerprintSchema="proxy-evaporative-dependency-closure-v1",
                defaultImplementationHash=default_hash, moduleSha256=modules,
                requestSha256=request_hash, inputs=normalized, settings=dict(SETTINGS),
                material=material, vaporSource=json.loads(_canonical(dict(profile.sourceProfile))),
                thermalContinuation=dict(method="constant-last-row-of-source-table",
                    starts_K=material["table"][-1][0], ends_K=normalized["evaporation"]["maxTemperature_K"],
                    endpointDensity_kg_m3=material["table"][-1][1],
                    endpointConductivity_W_mK=material["table"][-1][2],
                    endpointCp_J_kgK=material["table"][-1][3],
                    densityMethod="fixed reference density at preheat for volumetric enthalpy",
                    status=profile.sourceProfile["thermalContinuation"]),
                proxyNote=f"Single proxy profile for {spec['shortName']}: {spec['profileLabel']}")


def run(raw, report=lambda *args: None):
    """Solve one bare-plate track; return a distinct finite, unvalidated research schema."""
    import time as clock
    normalized, p, material, evaporation = _request(raw)
    spec = alloy_spec(normalized["material"])
    profile = spec["profile"]
    evidence = scenario_evidence(normalized["evaporation"], profile)
    provenance = _identity(normalized, material)
    domain, axes = _fixed_surface_grid(p)
    nx, ny, nz = (domain[key] for key in ("nx", "ny", "nz"))
    if nx*ny*nz > SETTINGS["maximumCells"]:
        raise ValueError("Evaporative CPU mesh exceeds 600000 cells")
    dx, radius = (domain[key] for key in ("dx", "radius"))
    thermal = thermal_si_inputs(p, material)
    ambient = thermal["preheat_K"]
    tt, hh = _thermal_table(material, evaporation.maxTemperature_K)
    if not tt[0] <= ambient <= tt[-1]:
        raise ValueError("Initial state is outside the enthalpy/scenario range")
    reference_h = float(np.interp(ambient, tt, hh))
    rho = float(property_at(material, ambient, 1))
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
    reason = (REFUSAL_ONSET if gate["onset"] else REFUSAL_UNRESOLVED if gate["unresolvedGeometry"] else None)
    width_warning = ("The model's recoil/capillary onset criterion was exceeded. This width is a "
                     "fixed-surface isotherm scenario and may not represent the melt pool."
                     if gate["onset"] else None)
    warnings = [
        profile.disclosure,
        evidence["summary"],
        f"Uncalibrated estimate of temperature and liquidus isotherm geometry for {spec['shortName']} "
        f"from the stated transient model on {spec['profileLabel']}. Uncertainty is unknown "
        "and may be large. Calibrate to your machine for better accuracy.",
        "The surface is held fixed. Evaporation removes energy, but melt flow, surface "
        "recession and changes in alloy composition are not resolved.",
        "This is the liquidus isotherm envelope of the selected temperature model. "
        "The envelope uses the reported instantaneous peak-melt-volume snapshot.",
    ]
    ceiling_gap = evaporation.maxTemperature_K-peak
    if ceiling_gap <= PEAK_NEAR_CEILING_MARGIN_K:
        warnings.append(
            f"The peak temperature {peak:.0f} K is {ceiling_gap:.0f} K below the scenario ceiling "
            f"{evaporation.maxTemperature_K:.0f} K. The ceiling is the scenario's computational limit, not a "
            "physical validity limit. The peak is sensitive to unmodelled surface motion, melt flow and plume. "
            f"This warning appears within {PEAK_NEAR_CEILING_MARGIN_K:.0f} K of the ceiling, a presentation "
            "choice and not a physical threshold.")
    if emitted_mass > 0:
        warnings.append("Active evaporation is present. Surface recession, expelled liquid, "
                        "plume shielding, convective redistribution and advective "
                        "redistribution are not resolved.")
    if width_warning is not None:
        warnings.append(width_warning)
    if reason is not None:
        warnings.append(reason)
    geometry = dict(snapshot)
    geometry.pop("moltenCellCount")
    if not gate["geometryAvailable"]:
        for key in ("depth_um", "length_um", "volume_um3"):
            geometry[key] = None
    geometry.update(basis="instantaneous liquidus extent at peak-melt-volume snapshot; cell bounds",
                    label="Uncalibrated fixed-surface isotherm estimate",
                    widthLabel="Conditional fixed-surface liquidus width estimate",
                    widthWarning=width_warning,
                    refusalReason=reason, liquidus_K=material["liquidus_K"],
                    cellResolution_um=dx*1e6)
    result = dict(schema=spec["schema"], modelId=spec["modelId"], status="completed",
        alloy=normalized["material"], researchLabel=spec["researchLabel"], disclosure=profile.disclosure,
        evidenceLabel=evidence["label"], evidence=evidence,
        experimentalValidation=False, productionReady=False, tier="Uncalibrated estimate",
        provenance=provenance, acceptedStepCount=accepted, acceptedTime_s=time_s,
        timesteps=dict(minimum_s=min_dt, maximum_s=max_dt, rejectedCandidates=rejected,
                       sourceRetries=source_retries), energy=energies,
        diagnosticEmittedMass_kg=emitted_mass, diagnosticMassLabel=spec["massLabel"],
        peakTemperature_K=peak, temperatureLabel="Conditional fixed-surface temperature estimate",
        geometry=geometry, gate=gate, warnings=warnings,
        fieldSummary=dict(shape=[nx, ny, nz], dx_m=dx,
                          minimumFinalTemperature_K=float(temperature.min()),
                          maximumFinalTemperature_K=float(temperature.max()),
                          minimumSourceCapture=capture))
    _canonical(result)  # Reject all nonfinite JSON, including derived provenance.
    return result


def main():
    raw = None
    try:
        raw = json.load(sys.stdin)
        result = run(raw)
    except (ValueError, TypeError, OverflowError) as exc:
        material = raw.get("material") if isinstance(raw, dict) else None
        spec = ALLOYS.get(material) if isinstance(material, str) else None
        print(json.dumps(dict(schema=spec["schema"] if spec else "lpbf-proxy-evaporative-error-v1",
                              modelId=spec["modelId"] if spec else None, status="error", error=str(exc)),
                         allow_nan=False))
        return 1
    print(_canonical(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
