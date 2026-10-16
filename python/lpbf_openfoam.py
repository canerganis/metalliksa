"""OpenFOAM 14 case generation and field-derived results. Thermal capability only."""
import math
import json
import os
from pathlib import Path
import subprocess
import tempfile
import numpy as np
from lpbf_core_physics import enthalpy_table, property_at, calculate_mesh_domain, thermal_si_inputs, SOURCE_INTEGRATION
from lpbf_evidence import thermal_audits
from lpbf_peak import PeakMeltTracker, PEAK_EXTRACTION
from lpbf_material_registry import contain_front_metrics

BINARY = Path(__file__).parent/"openfoam/bin/metalliksaThermal"
HEADER = 'FoamFile { version 2.0; format ascii; class dictionary; object %s; }\n'


def generate_case(p, m, folder):
    from lpbf_simulation import scan_segments
    folder = Path(folder); (folder/"system").mkdir(parents=True, exist_ok=True)
    (folder/"constant").mkdir(exist_ok=True)
    segments, end = scan_segments(p)
    thermal_inputs = thermal_si_inputs(p, m)
    domain = calculate_mesh_domain(p)
    radius, span, nxy, nz, dx, bottom = domain["radius"], domain["span"], domain["nxy"], domain["nz"], domain["dx"], -domain["substrate_depth"]
    if p["mode"] == "standard" and p["surfaceMode"] == "powder-layer":
        if p.get("powderGridPolicy") != "layer-conforming":
            raise ValueError("Standard OpenFOAM powder runs require a layer-conforming grid")
        layer_m = thermal_inputs["layer_m"]
        layer_cells = layer_m/dx
        base_face = (0.0-bottom)/dx
        if (not math.isclose(layer_cells, round(layer_cells), rel_tol=0, abs_tol=1e-10)
                or not math.isclose(base_face, round(base_face), rel_tol=0, abs_tol=1e-10)):
            raise ValueError("OpenFOAM powder grid does not align layer surfaces with cell faces")
    if nxy*nxy*nz > 600000: raise ValueError("OpenFOAM thermal cell budget exceeded")
    z = bottom+(np.arange(nz)+.5)*dx
    counts = [int(np.sum(z < layer*thermal_inputs["layer_m"])) for layer in range(int(p["layers"])+1)]
    if any(b <= a for a,b in zip(counts,counts[1:])):
        raise ValueError("Mesh cannot resolve each powder layer; reduce mesh spacing below layer thickness")
    top = bottom+nz*dx
    corners = [(x, y, z) for z in (bottom, top) for x, y in ((-span/2, -span/2), (span/2, -span/2), (span/2, span/2), (-span/2, span/2))]
    vertices = "\n".join("(%s %s %s)" % point for point in corners)
    mesh = HEADER % "blockMeshDict"+f'''convertToMeters 1;
vertices ({vertices});
blocks (hex (0 1 2 3 4 5 6 7) ({nxy} {nxy} {nz}) simpleGrading (1 1 1));
edges ();
boundary ( walls {{ type wall; faces ((0 3 2 1) (4 5 6 7) (0 1 5 4) (1 2 6 5) (2 3 7 6) (3 0 4 7)); }} );
mergePatchPairs ();
'''
    (folder/"system/blockMeshDict").write_text(mesh)
    (folder/"system/controlDict").write_text(HEADER % "controlDict"+f"application metalliksaThermal; startFrom startTime; startTime 0; stopAt endTime; endTime {end}; deltaT {p['maxDt_s']}; writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 12; runTimeModifiable false;\n")
    (folder/"system/fvSchemes").write_text(HEADER % "fvSchemes"+"ddtSchemes { default Euler; } gradSchemes { default Gauss linear; } divSchemes { default none; } laplacianSchemes { default Gauss linear orthogonal; } interpolationSchemes { default linear; } snGradSchemes { default orthogonal; }\n")
    (folder/"system/fvSolution").write_text(HEADER % "fvSolution"+"solvers {}\n")
    tt, hh = enthalpy_table(m)
    table = np.column_stack([tt, hh, *[property_at(m, tt, i) for i in (1, 2, 3, 4)]])
    config = [end, p["maxDt_s"], thermal_inputs["preheat_K"], m["solidus_K"], m["liquidus_K"], m["boiling_K"],
              thermal_inputs["absorbed_power_W"], radius, thermal_inputs["layer_m"],
              p["packingFraction"], p["powderConductivityRatio"], p["convection_W_m2K"], m["emissivity"], dx, thermal_inputs["speed_m_s"]]
    with (folder/"thermalInput.dat").open("w") as stream:
        stream.write(" ".join(map(str, config))+"\n"+str(len(table))+"\n")
        np.savetxt(stream, table, fmt="%.17g")
        stream.write(str(len(segments))+"\n")
        for s in segments:
            stream.write(" ".join(map(str, [s["start_s"], s["end_s"], *s["start"], *s["end"], (s["layer"]+1)*thermal_inputs["layer_m"], s["track"], s["layer"]]))+"\n")
    return dx, segments


def thermal(p, m, report=lambda *args: None, artifact_dir=None):
    if os.name == "nt" or not BINARY.is_file():
        raise ValueError("OpenFOAM thermal executable unavailable in worker; build with wmake in WSL")
    if artifact_dir is None:
        with tempfile.TemporaryDirectory(prefix="metalliksa-thermal-") as tmp:
            return thermal(p, m, report, tmp)
    folder = Path(artifact_dir)/"openfoam-case"
    dx, segments = generate_case(p, m, folder)
    diagnostic_path = folder/"numerical-diagnostics.json"
    # A reused case must prove the current executable, never a previous run.
    diagnostic_path.unlink(missing_ok=True)
    (folder/"peak-state.dat").unlink(missing_ok=True)
    (folder/"track-melt.dat").unlink(missing_ok=True)
    # Shell program is constant; all paths are separate positional arguments.
    script = 'source /opt/openfoam14/etc/bashrc; blockMesh -case "$1" && checkMesh -case "$1" && "$2" -case "$1"'
    child = subprocess.Popen(["bash", "-lc", script, "metalliksa", str(folder.resolve()), str(BINARY.resolve())],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    with (folder/"solver.log").open("w") as log:
        for line in child.stdout:
            log.write(line)
            if line.startswith("THERMAL_PROGRESS"):
                report(float(line.split()[1]), line.strip())
        code = child.wait()
        child.stdout.close()
    if code:
        raise ValueError("OpenFOAM thermal failed: "+(folder/"solver.log").read_text()[-2500:])
    from lpbf_overlap import FieldOverlapTracker, OVERLAP_MODEL_ID
    if not diagnostic_path.is_file():
        raise ValueError("OpenFOAM binary is outdated: rebuild metalliksaThermal for cell-integrated heating")
    diagnostics = json.loads(diagnostic_path.read_text())
    if p.get("powderGridPolicy") == "layer-conforming":
        surface_offset_um = diagnostics.get("maximumSurfaceOffset_um")
        if (isinstance(surface_offset_um, bool) or not isinstance(surface_offset_um, (int, float))
                or not math.isfinite(surface_offset_um) or abs(surface_offset_um) > 1e-6):
            raise ValueError("OpenFOAM layer-conforming surface alignment check failed; rebuild solver")
    minimum_capture = diagnostics.get("minimumCapturedSourceFraction")
    if (isinstance(minimum_capture, bool) or not isinstance(minimum_capture, (int, float))
            or not math.isfinite(minimum_capture) or minimum_capture < 1/1.01):
        raise ValueError("OpenFOAM Gaussian source capture is below the 1/1.01 minimum; rebuild solver")
    if diagnostics.get("sourceIntegration") != SOURCE_INTEGRATION:
        raise ValueError("OpenFOAM source integration contract mismatch; rebuild solver")
    if diagnostics.get("solidificationExtraction") != "linear-liquidus-crossing-v1":
        raise ValueError("OpenFOAM solidification extraction contract mismatch; rebuild solver")
    if diagnostics.get("meltPoolExtraction") != PEAK_EXTRACTION:
        raise ValueError("OpenFOAM melt pool extraction contract mismatch; rebuild solver")
    if diagnostics.get("overlapExtraction") != OVERLAP_MODEL_ID:
        raise ValueError("OpenFOAM overlap extraction contract mismatch; rebuild solver")
    coords = np.loadtxt(folder/"coordinates.csv", delimiter=",")
    samples = np.loadtxt(folder/"snapshots.dat", ndmin=2)
    if not np.isfinite(samples).all() or samples.shape[1] != len(coords)+14:
        raise ValueError("Invalid OpenFOAM field output")
    from lpbf_evidence import FieldRecorder
    recorder = FieldRecorder(artifact_dir, coords[:, :3], dx, m, p)
    history = []
    tracker = PeakMeltTracker(coords[:, :3], dx, m)
    peak_state = np.loadtxt(folder/"peak-state.dat", ndmin=1)
    if not np.isfinite(peak_state).all() or len(peak_state) < 4:
        raise ValueError("Invalid OpenFOAM peak field output")
    peak_time, peak_surface, peak_step, peak_count = peak_state[:4]
    if peak_count != int(peak_count) or peak_count < 0 or peak_step != int(peak_step):
        raise ValueError("Invalid OpenFOAM peak field metadata")
    if peak_count:
        if len(peak_state) != len(coords)+4 or not (0 < peak_step <= samples[-1, 5]) or not (0 < peak_time <= samples[-1, 0]):
            raise ValueError("Invalid OpenFOAM peak field extent or time")
        # Surface belongs to the accepted step, not the next layer starting at t.
        layer = round(peak_surface/(p["layer_um"]*1e-6))-1
        tracker.observe(peak_state[4:], peak_surface,
                        p["scanAngle_deg"]+layer*p["layerRotation_deg"], peak_time, peak_step)
        if tracker.count != peak_count:
            raise ValueError("OpenFOAM peak field molten count mismatch")
    elif len(peak_state) != 4 or peak_step != 0 or peak_time != 0:
        raise ValueError("Invalid OpenFOAM zero-melt output")
    for row in samples:
        t, ei, eo, stored, dt, steps, surface, peak = row[:8]; T = row[14:]
        recorder.record(t, T, surface)
        count = int(np.count_nonzero((T >= m["liquidus_K"]) & (coords[:, 2] < surface)))
        tracker.sampled_count = max(tracker.sampled_count, count)
        history.append(dict(time_s=t, peak_K=float(T.max()), storedEnergy_J=stored, inputEnergy_J=ei, lossEnergy_J=eo))
    if tracker.sampled_count > tracker.count:
        raise ValueError("OpenFOAM peak field is smaller than a sampled field")
    best, peak_diagnostics = tracker.finish(artifact_dir, int(samples[-1, 5]))
    diagnostics.update(peak_diagnostics)

    # Process field-based track overlap
    track_melt_path = folder/"track-melt.dat"
    if not track_melt_path.is_file():
        raise ValueError("OpenFOAM track melt output missing; rebuild solver")
    overlap_tracker = FieldOverlapTracker(coords[:, :3], dx, m, p)
    with track_melt_path.open() as tm_f:
        header = tm_f.readline().split()
        if header:
            num_segs, total_cells = int(header[0]), int(header[1])
            for _ in range(num_segs):
                line = tm_f.readline().split()
                if not line:
                    break
                trk, lyr, cnt = int(line[0]), int(line[1]), int(line[2])
                key = (lyr, trk)
                if key not in overlap_tracker.track_melt:
                    overlap_tracker.track_melt[key] = np.zeros(len(coords), dtype=bool)
                if cnt > 0 and len(line) >= 3 + cnt:
                    indices = [int(x) for x in line[3:3 + cnt]]
                    overlap_tracker.track_melt[key][indices] = True
                    overlap_tracker.ever_melted[indices] = True
    overlap_metrics = overlap_tracker.finish(artifact_dir)

    row = samples[-1]; balance = abs(row[1]-row[2]-row[3])/max(row[1], 1e-12)
    if balance > .01: raise ValueError("OpenFOAM energy balance failed")
    w = best["width_um"]*1e-6
    alpha = float(property_at(m, m["liquidus_K"], 2)/(property_at(m, m["liquidus_K"], 1)*property_at(m, m["liquidus_K"], 3)))
    best.update(peakTemperature_K=float(row[7]), thermalGradient_K_m=float(row[8]/row[11]) if row[11] else None,
                solidificationRate_m_s=float(row[9]/row[11]) if row[11] else None,
                coolingRate_K_s=float(row[10]/row[11]) if row[11] else None,
                keyholeDepth_um=None, recoilPressure_Pa=None,
                marangoniNumber=abs(m["dGamma_dT"])*max(0, row[7]-m["liquidus_K"])*w/(float(property_at(m, row[7], 4))*alpha),
                pecletNumber=p["speed_mm_s"]*.001*w/alpha, aspectRatio=best["depth_um"]/best["width_um"] if w else None,
                trackOverlapRatio=overlap_metrics["trackOverlapRatio"],
                remeltingRatio=overlap_metrics["globalRemeltRatio"] if row[12] else 0.)
    # D13 field identity: producer and extraction rule only (no served implementation fingerprint).
    best, transient_front = contain_front_metrics(
        best, m, p, "metalliksaThermal-OpenFOAM14-6:linear-liquidus-crossing-event-means-v1")
    return dict(metrics=best, transientFrontDiagnostics=transient_front, thermalHistory=history, fieldSeries=recorder.finish(), scanPath=segments,
                numericalDiagnostics=diagnostics, fieldOverlapDiagnostics=overlap_metrics,
                energyBalance=dict(input_J=float(row[1]), losses_J=float(row[2]), stored_J=float(row[3]), relativeError=float(balance)),
                discretization=dict(cells=len(coords), mesh_m=dx, minimumDt_s=float(row[4]), meanDt_s=float(row[0]/row[5]), steps=int(row[5])),
                **thermal_audits(coords[:,:3],coords[:,3],p,m,np.clip((samples[-1,14:]-m["solidus_K"])/(m["liquidus_K"]-m["solidus_K"]),0,1)),
                fieldHistory="openfoam-case/snapshots.dat", extractionNote="Dimensions and peak field selected at the earliest maximum molten-cell volume over every accepted timestep; playback remains sparse. Global-x slice area is not scan-normal for rotated tracks. Sampling loss measures playback decimation only, not timestep or mesh error. G/R/cooling are event means at linearly reconstructed cooling liquidus crossings over every timestep; gradient vectors are interpolated before taking their magnitude, G <= 1e-6 K/m excluded. Remelting and inter-track overlap tracked from 3D field every step.")
