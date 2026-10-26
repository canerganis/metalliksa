import { useState } from 'react';
import { WarningNotes } from './SolidificationEstimates';
import { useVisiblePolling } from '../hooks/useVisiblePolling';
import {
  alsi10mgEvaporativeApi, type AlSi10MgEvaporativeJob, type AlSi10MgEvaporativeResult,
} from '../services/lpbfSimulationService';
import {
  ALSI10MG_EVAPORATION_SCENARIO, ALSI10MG_EVAPORATIVE_LABEL, ALSI10MG_EVAPORATIVE_TRACK_UM, ALSI10MG_PROXY_DISCLOSURE,
  alsi10mgEvaporativeAvailability, buildAlSi10MgEvaporativeInput, type AlSi10MgSurfaceMode,
} from '../utils/alsi10mgEvaporativeModel';

const fmt = (value: number | null | undefined) => value === null || value === undefined || !Number.isFinite(value) ? 'null' : Number(value.toPrecision(6)).toString();

export interface AlSi10MgProcessInput { power_W: number; speed_mm_s: number; beamDiameter_um: number; preheat_C: number }

/** Plain explanation placed before the solver's own error text, which is kept verbatim. */
export function alsi10mgEvaporativeErrorHint(message: string): string {
  if (!/exceeds finite enthalpy\/scenario range/.test(message)) return '';
  return `At these settings the surface temperature leaves the model's declared range (up to ${ALSI10MG_EVAPORATION_SCENARIO.maxTemperature_K} K), so the run stops instead of clipping values. Lower the laser power or raise the scan speed and run again. Solver message: `;
}

export function AlSi10MgEvaporativeResultView({ result }: { result: AlSi10MgEvaporativeResult }) {
  const g = result.geometry;
  const e = result.energy;
  const refused = !result.gate.geometryAvailable;
  const extent = (label: string, value: number | null, unit: string) => <div key={label}>
    <dt className="text-xs text-slate-400">{label}</dt>
    <dd className="mt-1 tabular-nums">{value === null ? <>null <span className="text-xs text-amber-200">(not available: {g.refusalReason ?? 'no reason returned'})</span></> : <>{fmt(value)} {unit}</>}</dd>
  </div>;
  return <div className="space-y-4" aria-label="AlSi10Mg evaporative result">
    <p className="text-sm text-amber-200">{result.researchLabel} · {result.tier} · {result.modelId} · experimentalValidation={String(result.experimentalValidation)} · productionReady={String(result.productionReady)}</p>
    <p className="text-xs text-amber-200">{result.disclosure}</p>
    <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div><dt className="text-xs text-slate-400">Peak temperature</dt><dd className="mt-1 tabular-nums">{fmt(result.peakTemperature_K)} K</dd><dd className="text-xs text-slate-400">{result.temperatureLabel}</dd></div>
      <div><dt className="text-xs text-slate-400">Width</dt><dd className="mt-1 tabular-nums">{fmt(g.width_um)} µm</dd><dd className="text-xs text-slate-400">{g.widthLabel}</dd></div>
      {extent('Depth', g.depth_um, 'µm')}{extent('Length', g.length_um, 'µm')}{extent('Volume', g.volume_um3, 'µm³')}
      <div><dt className="text-xs text-slate-400">Accepted time and steps</dt><dd className="mt-1 tabular-nums">{fmt(result.acceptedTime_s)} s · {result.acceptedStepCount} steps</dd></div>
      <div><dt className="text-xs text-slate-400">Declared track</dt><dd className="mt-1 tabular-nums">{fmt(Number(result.provenance.inputs.trackLength_um))} µm · mesh {fmt(Number(result.provenance.inputs.mesh_um))} µm</dd></div>
    </dl>
    {g.widthWarning && <p className="text-sm text-amber-200">{g.widthWarning}</p>}
    {refused && g.refusalReason && <p className="text-sm text-amber-200">Refusal: {g.refusalReason}</p>}
    <table className="w-full max-w-xl text-left text-xs"><caption className="sr-only">Energy ledger</caption>
      <thead><tr><th scope="col">Term</th><th scope="col">Value (J)</th></tr></thead>
      <tbody>
        {([['Input', e.input_J], ['Evaporative loss', e.evaporative_J], ['Radiative and convective loss', e.radiativeConvective_J],
          ['Base loss', e.base_J], ['Stored', e.stored_J], ['Residual', e.residual_J]] as const).map(([k, v]) => <tr key={k}><th scope="row" className="font-normal">{k}</th><td className="tabular-nums">{fmt(v)}</td></tr>)}
        <tr><th scope="row" className="font-normal">Relative residual</th><td className="tabular-nums">{fmt(e.relativeResidual)}</td></tr>
      </tbody></table>
    <p className="text-xs text-slate-400">{result.diagnosticMassLabel}: {fmt(result.diagnosticEmittedMass_kg)} kg</p>
    <WarningNotes className="text-xs text-slate-400" warnings={result.warnings.filter(w => w !== result.disclosure)} />
  </div>;
}

export function AlSi10MgEvaporativePanel({ material, process }: { material: string; process: AlSi10MgProcessInput }) {
  const [surfaceMode, setSurfaceMode] = useState<AlSi10MgSurfaceMode>('bare-plate');
  const [optIn, setOptIn] = useState(false);
  const [job, setJob] = useState<AlSi10MgEvaporativeJob>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const availability = alsi10mgEvaporativeAvailability(material, surfaceMode);
  const active = job?.status === 'queued' || job?.status === 'running';
  const result = job?.status === 'completed' ? job.result : undefined;

  useVisiblePolling(async (isLive) => {
    if (!job) return null;
    try {
      const next = await alsi10mgEvaporativeApi.get(job.id);
      if (!isLive()) return null;
      setJob(next); setError('');
      return next.status === 'queued' || next.status === 'running' ? 1500 : null;
    } catch (e) {
      if (!isLive()) return null;
      setError(e instanceof Error ? e.message : 'Evaporative job polling failed');
      return 3000;
    }
  }, !!job && active, `${job?.id}:${job?.status}`);

  const submit = async () => {
    if (busy || active || !availability.available || !optIn) return;
    setBusy(true); setError('');
    try { setJob(await alsi10mgEvaporativeApi.submit(buildAlSi10MgEvaporativeInput(process))); }
    catch (e) { setError(e instanceof Error ? e.message : 'Evaporative job submission failed'); }
    finally { setBusy(false); }
  };
  const cancel = async () => {
    if (!job || !active) return;
    try { setJob(await alsi10mgEvaporativeApi.cancel(job.id)); }
    catch (e) { setError(e instanceof Error ? e.message : 'Cancellation failed'); }
  };

  return <section className="rounded-2xl border border-amber-400/30 bg-slate-900/50 p-4 md:p-5 space-y-4" aria-label="AlSi10Mg evaporative surface model">
    <div>
      <h3 className="font-medium">Thermal model choice (AlSi10Mg)</h3>
      <p className="mt-2 text-xs leading-5 text-amber-200">Opt-in research model. Fixed-surface conduction with Al vapour energy loss on a bare plate only. Uncalibrated, not experimentally validated. The default Standard simulation is unchanged.</p>
      <p className="mt-2 text-xs leading-5 text-amber-200">{ALSI10MG_PROXY_DISCLOSURE}</p>
    </div>
    <fieldset className="space-y-2">
      <legend className="text-xs text-slate-400">Surface</legend>
      <label className="mr-6 text-sm"><input type="radio" name="alsi10mg-surface" className="mr-2 accent-sky-400" checked={surfaceMode === 'bare-plate'} onChange={() => setSurfaceMode('bare-plate')} />Bare plate</label>
      <label className="text-sm"><input type="radio" name="alsi10mg-surface" className="mr-2 accent-sky-400" checked={surfaceMode === 'powder-layer'} onChange={() => setSurfaceMode('powder-layer')} />Powder layer</label>
    </fieldset>
    <label className="flex items-start gap-3 text-sm">
      <input type="checkbox" aria-describedby="alsi10mg-evap-reason" className="mt-1 accent-sky-400" checked={optIn && availability.available} disabled={!availability.available || busy || active} onChange={e => setOptIn(e.currentTarget.checked)} />
      <span>{ALSI10MG_EVAPORATIVE_LABEL}</span>
    </label>
    <p id="alsi10mg-evap-reason" className="text-xs text-slate-400" role="status">
      {!('reason' in availability) ? `Runs a ${ALSI10MG_EVAPORATIVE_TRACK_UM} µm declared track at the shared power, speed, beam diameter and preheat (about 16 s on the reference CPU).` : (availability as { reason: string }).reason}
    </p>
    <div className="flex flex-wrap gap-3">
      <button className="rounded-lg border border-slate-500 px-3 py-2 text-sm disabled:opacity-40" disabled={busy || active || !availability.available || !optIn} onClick={submit}>Run AlSi10Mg evaporative surface model</button>
      {active && <button className="rounded-lg border border-slate-500 px-3 py-2 text-sm" onClick={cancel}>Cancel</button>}
    </div>
    {job && <p role="status" className="text-xs text-slate-400">Job {job.id} · {job.status}{active ? ` · ${Math.round(job.progress * 100)}%` : ''}</p>}
    {(error || job?.error) && <p role="alert" className="rounded-xl border border-red-400/30 p-3 text-sm text-red-200 whitespace-pre-wrap">{alsi10mgEvaporativeErrorHint(error || job?.error || '')}{error || job?.error}</p>}
    {result && <AlSi10MgEvaporativeResultView result={result} />}
  </section>;
}
