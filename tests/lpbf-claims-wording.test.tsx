import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { keyholeMeshForBeam, missedPowerWarning } from "../src/components/KeyholeRaytracingLab";
import { DISTORTION_HEURISTIC_NOTE, STRESS_UNAVAILABLE_NOTE, stressValueText } from "../src/utils/distortionHeuristic";

const read = (path: string) => readFileSync(resolve(import.meta.dirname, "..", path), "utf8");

test("solidification status dot pulses only while loading", () => {
  const src = read("src/components/SolidificationMicrostructureLab.tsx");
  assert.match(src, /\$\{isLoading \? 'animate-pulse' : ''\}/);
  assert.doesNotMatch(src, /isLoading \? '' : 'animate-pulse'/);
});

test("stress and distortion are labelled unavailable (P7a) and keyhole missed power is labelled", () => {
  // P7a (2026-10-11): the 0.72 / 40 um / 420 MPa heuristic is gone; the note states the unavailability and its source.
  assert.equal(DISTORTION_HEURISTIC_NOTE, STRESS_UNAVAILABLE_NOTE);
  assert.match(STRESS_UNAVAILABLE_NOTE, /no sourced stress model/);
  assert.match(STRESS_UNAVAILABLE_NOTE, /Mercelis and Kruth 2006/);
  assert.match(STRESS_UNAVAILABLE_NOTE, /no longer served/);
  assert.equal(stressValueText(null, "r"), "n/a (r)");
  assert.equal(stressValueText(12.5), "12.5");
  // Pin to the frozen solver source: the formula is deleted and the served values are null.
  const solver = read("python/lpbf_thermal_solver.py");
  assert.doesNotMatch(solver, /elastic_stress_max_mpa \* 0\.72/);
  assert.doesNotMatch(solver, /delta_t_stress = max\(10\.0, T_sol - T_preheat\)/);
  assert.match(solver, /"effectiveResidualStress_MPa": None/);
  assert.match(solver, /"distortionIndex": None/);
  assert.match(read("src/components/3d-distortion-lab/MeltPool3DCrossSectionLab.tsx"), /DISTORTION_HEURISTIC_NOTE/);
  const keyhole = read("src/components/KeyholeRaytracingLab.tsx");
  assert.match(keyhole, /Missed power \(outside mesh\)/);
  assert.match(keyhole, /total_missed_W/);
});

test("keyhole: mesh aperture spans at least 3x the beam radius across the UI range", () => {
  for (let diameter = 40; diameter <= 300; diameter += 2) {
    const r = diameter / 2;
    const mesh = keyholeMeshForBeam(r);
    const halfExtent_um = ((mesh.nx - 1) * mesh.dx) / 2 * 1e6;
    assert.ok(halfExtent_um >= 3 * r - 1e-9, `d=${diameter}: ±${halfExtent_um} um`);
    assert.equal(mesh.dx, mesh.dy);
    assert.ok(mesh.dx >= 2e-6 && mesh.dx <= 1e-3, "within solver bounds");
    assert.ok(mesh.nx >= 2 && mesh.nx <= 256);
  }
  assert.equal(missedPowerWarning(0), null);
  assert.equal(missedPowerWarning(0.005), null);
  assert.match(missedPowerWarning(0.64) ?? "", /64\.0% of the input power falls outside the mesh/);
  const src = read("src/components/KeyholeRaytracingLab.tsx");
  assert.match(src, /Absorption \(of total input\)/);
  assert.match(src, /Absorption \(of intercepted power\)/);
  assert.match(src, /\.\.\.keyholeMeshForBeam\(beamRadius_um\)/);
  assert.doesNotMatch(read("python/lpbf_keyhole_raytracing.py"), /enlarge the mesh/);
});
