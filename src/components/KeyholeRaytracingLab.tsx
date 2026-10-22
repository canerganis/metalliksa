import React, { useEffect, useState, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Line } from '@react-three/drei';
import * as THREE from 'three';
import { useMaterialSpecimenStore } from '../store/useMaterialSpecimenStore';
import { gpuCapability, GpuCapabilityError, type GpuCapability } from '../utils/gpuCapability';
import { GpuCapabilityNotice } from './GpuCapabilityNotice';

interface RaytracingResult {
  status: string;
  model_id: string;
  device: string;
  solve_time_ms: number;
  total_absorbed_W: number;
  total_escaped_W: number;
  total_truncated_W: number;
  total_missed_W: number;
  mesh_aperture_half_extent_um: number;
  absorption_efficiency: number;
  absorption_efficiency_of_intercepted: number | null;
  missed_fraction: number;
  energy_balance_relative_error: number;
  sampling: { seed: number; num_rays: number; absorption_efficiency_standard_error: number; uncertainty_scope: string };
  limitations: string[];
  mesh: { vertices: number[]; indices: number[] };
  ray_paths: { points: [number, number, number][]; powers: number[] }[];
}

const MESH_NODES = 64;
const MIN_MESH_SPACING_M = 2e-6;

/**
 * Mesh sized from the beam so the aperture half-extent is at least 3x the beam radius
 * (64 nodes; spacing never below the solver's 2 µm default). Without this the fixed
 * ±63 µm default mesh lets most of a wide beam miss the cavity.
 */
export function keyholeMeshForBeam(beamRadius_um: number): { nx: number; ny: number; dx: number; dy: number } {
  const spacing = Math.max(MIN_MESH_SPACING_M, (6 * beamRadius_um * 1e-6) / (MESH_NODES - 1));
  return { nx: MESH_NODES, ny: MESH_NODES, dx: spacing, dy: spacing };
}

/** Warning text when a noticeable share of the input never reaches the mesh, else null. */
export function missedPowerWarning(missedFraction: number): string | null {
  if (!Number.isFinite(missedFraction) || missedFraction <= 0.01) return null;
  return `${(missedFraction * 100).toFixed(1)}% of the input power falls outside the mesh and never reaches the cavity; absorption of total input is reduced by this geometry artefact.`;
}

export const KeyholeRaytracingLab: React.FC = () => {
  const process = useMaterialSpecimenStore(state => state.activeSpecimen.lpbf);
  const updateProcess = useMaterialSpecimenStore(state => state.updateLpbfProcess);
  const [optics, setOptics] = useState({ keyhole_depth_um: 120, base_absorption: 0.35, max_bounces: 5, num_rays: 4096, seed: 0, device: 'cpu' });
  const [reply, setReply] = useState<{ request: string; data: RaytracingResult } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [capability, setCapability] = useState<GpuCapability | null>(null);
  const [loading, setLoading] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const beamRadius_um = process.beamDiameter_um / 2;
  const request = JSON.stringify({ ...optics, ...keyholeMeshForBeam(beamRadius_um), power_W: process.laserPower_W, beam_radius_um: beamRadius_um, ui_ray_limit: 150 });
  // Hide old results in the same render that changes the inputs.
  const result = reply?.request === request ? reply.data : null;

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setReply(null);
    setError(null);
    setCapability(null);
    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const response = await fetch('/api/python/lpbf-keyhole-raytracing', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: request, signal: controller.signal,
        });
        const data = await response.json();
        const unavailable = gpuCapability(data.capability);
        if (!response.ok && unavailable) throw new GpuCapabilityError(unavailable);
        if (!response.ok || data.status !== 'success') throw new Error(data.error || 'Ray tracing failed');
        if (active) setReply({ request, data });
      } catch (failure) {
        if (active) {
          if (failure instanceof GpuCapabilityError) setCapability(failure.capability);
          else setError(failure instanceof Error ? failure.message : 'Ray tracing failed');
        }
      } finally {
        if (active) setLoading(false);
      }
    }, 300);
    // HTTP abort discards stale responses; cancelling worker computation still
    // requires queue integration, tracked separately in the Phase 0 audit.
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  }, [request, attempt]);

  const geometry = useMemo(() => {
    if (!result) return null;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(result.mesh.vertices, 3));
    geo.setIndex(result.mesh.indices);
    geo.computeVertexNormals();
    return geo;
  }, [result]);
  useEffect(() => () => { geometry?.dispose(); }, [geometry]);

  const numberControl = (label: string, value: number, min: number, max: number, step: number, change: (value: number) => void) => (
    <label className="flex flex-col gap-1 text-xs text-gray-300">
      {label}
      <input aria-label={label} type="number" value={value} min={min} max={max} step={step}
        className="rounded border border-gray-600 bg-gray-800 p-2 text-white"
        onChange={event => { const next = event.currentTarget.valueAsNumber; if (Number.isFinite(next)) change(next); }} />
    </label>
  );

  return (
    <div className="grid min-h-[700px] grid-cols-1 gap-4 lg:grid-cols-[340px_1fr]">
      <section className="mk-plate space-y-4 p-5" aria-label="Keyhole optics controls and results">
        <h1 className="text-xl font-semibold">Keyhole Laser Absorption</h1>
        <p className="text-sm text-gray-400">Prescribed cavity, not a solved free surface; the absorption law is empirical and not calibrated. Power and beam diameter use the shared LPBF process.</p>
        <div className="grid grid-cols-2 gap-3">
          {numberControl('Laser power (W)', process.laserPower_W, 0, 1000, 10, value => updateProcess({ laserPower_W: value }))}
          {numberControl('Beam diameter (µm, 1/e²)', process.beamDiameter_um, 40, 300, 2, value => updateProcess({ beamDiameter_um: value }))}
          {numberControl('Cavity depth (µm)', optics.keyhole_depth_um, 0, 300, 5, value => setOptics(old => ({ ...old, keyhole_depth_um: value })))}
          {numberControl('Base absorption', optics.base_absorption, 0, 1, 0.01, value => setOptics(old => ({ ...old, base_absorption: value })))}
          {numberControl('Maximum bounces', optics.max_bounces, 1, 32, 1, value => setOptics(old => ({ ...old, max_bounces: value })))}
          {numberControl('Rays', optics.num_rays, 32, 100000, 256, value => setOptics(old => ({ ...old, num_rays: value })))}
          {numberControl('Random seed', optics.seed, 0, 4294967295, 1, value => setOptics(old => ({ ...old, seed: value })))}
          <label className="flex flex-col gap-1 text-xs text-gray-300">Backend
            <select aria-label="Backend" value={optics.device} className="rounded border border-gray-600 bg-gray-800 p-2" onChange={event => setOptics(old => ({ ...old, device: event.target.value }))}>
              <option value="cpu">Warp CPU</option><option value="cuda:0">Warp CUDA 0</option>
            </select>
          </label>
        </div>
        <p role="status" className="text-sm text-gray-400">{loading ? 'Computing ray paths…' : result ? `Computed on ${result.device}` : 'No computed result'}</p>
        {capability && <GpuCapabilityNotice capability={capability} />}
        {error && <div role="alert" className="rounded border border-red-700 p-3 text-sm text-red-300">{error}<button className="ml-3 underline" onClick={() => setAttempt(value => value + 1)}>Retry</button></div>}
        {result && <>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt>Absorption (of total input)</dt><dd>{(result.absorption_efficiency * 100).toFixed(2)}%</dd>
            <dt>Absorption (of intercepted power)</dt><dd>{result.absorption_efficiency_of_intercepted == null ? 'unavailable: no ray reached the mesh' : `${(result.absorption_efficiency_of_intercepted * 100).toFixed(2)}%`}</dd>
            <dt>Absorbed power</dt><dd>{result.total_absorbed_W.toFixed(3)} W</dd>
            <dt>Escaped power (reflected out)</dt><dd>{result.total_escaped_W.toFixed(3)} W</dd>
            <dt>Missed power (outside mesh)</dt><dd>{result.total_missed_W.toFixed(3)} W</dd>
            <dt>Bounce-limited power</dt><dd>{result.total_truncated_W.toFixed(3)} W</dd>
            <dt>Energy closure error</dt><dd>{(result.energy_balance_relative_error * 100).toExponential(2)}%</dd>
            <dt>Sampling standard error</dt><dd>{(result.sampling.absorption_efficiency_standard_error * 100).toFixed(3)} pp</dd>
            <dt>Solve time</dt><dd>{result.solve_time_ms.toFixed(1)} ms</dd>
          </dl>
          {missedPowerWarning(result.missed_fraction) && <p role="alert" className="rounded border border-amber-700 bg-amber-900/30 p-2 text-xs text-amber-200">{missedPowerWarning(result.missed_fraction)}</p>}
          <p className="text-xs text-gray-400">Mesh is sized from the beam: aperture ±{result.mesh_aperture_half_extent_um.toFixed(0)} µm for beam radius {beamRadius_um.toFixed(0)} µm (at least 3x the radius, 64 x 64 nodes). Rays starting outside the aperture never reach the cavity and are counted as missed, not escaped.</p>
          <p className="text-xs text-gray-400">{result.model_id} · seed {result.sampling.seed} · {result.sampling.num_rays} rays</p>
          <p className="text-xs text-gray-400">{result.sampling.uncertainty_scope}</p>
          <ul className="list-disc space-y-1 pl-4 text-xs text-amber-300">{result.limitations.map(limit => <li key={limit}>{limit}</li>)}</ul>
        </>}
      </section>
      <div className="mk-labglass mk-hud min-h-[500px]" aria-label="Computed ray paths and prescribed cavity">
        <Canvas camera={{ position: [0.0003, 0.0003, 0.0002], fov: 45, near: 0.000001, far: 0.01 }}>
          {/* Light lab-glass viewport (porcelain): pearl background, graphite grid, cobalt cavity, laser-orange rays. */}
          <color attach="background" args={['#eef0f3']} />
          <ambientLight intensity={0.8} />
          <directionalLight position={[1, 1, 1]} intensity={1.5} />
          <OrbitControls target={[0, 0, -0.00005]} makeDefault />
          {geometry && <mesh geometry={geometry}><meshStandardMaterial color="#2346b0" transparent opacity={0.55} roughness={0.35} metalness={0.2} side={THREE.DoubleSide} /></mesh>}
          {result?.ray_paths.filter(path => path.points.length > 1).map((path, index) => (
            <Line key={index} points={path.points} color="#ff5b1f" lineWidth={1} transparent opacity={0.55} />
          ))}
          <gridHelper args={[0.001, 20, '#9aa1ab', '#c9ced6']} rotation={[Math.PI / 2, 0, 0]} />
        </Canvas>
      </div>
    </div>
  );
};
