import { useState } from 'react';
import { WarningNotes } from './SolidificationEstimates';
import { useVisiblePolling } from '../hooks/useVisiblePolling';
import {
  proxyEvaporativeApi, type ProxyEvaporativeJob, type ProxyEvaporativeResult,
} from '../services/lpbfSimulationService';
import {
  PROXY_ALLOY_PROFILES, PROXY_EVAPORATIVE_TRACK_UM, buildProxyEvaporativeInput, proxyAlloyFor,
  proxyEvaporativeAvailability, type ProxySurfaceMode,
} from '../utils/proxyEvaporativeModel';

const fmt = (value: number | null | undefined) => value === null || value === undefined || !Number.isFinite(value) ? 'null' : Number(value.toPrecision(6)).toString();

export interface ProxyProcessInput { power_W: number; speed_mm_s: number; beamDiameter_um: number; preheat_C: number }

const processKey = (p: ProxyProcessInput) => JSON.stringify([p.power_W, p.speed_mm_s, p.beamDiameter_um, p.preheat_C]);

/** Settings the completed result was actually computed with, read from its own provenance. */
export function proxyResultSettings(result: ProxyEvaporativeResult): ProxyProcessInput {
  const i = result.provenance.inputs;
  return { power_W: Number(i.power_W), speed_mm_s: Number(i.speed_mm_s), beamDiameter_um: Number(i.beamDiameter_um), preheat_C: Number(i.preheat_C) };
}

/** True when the shared process inputs (or the selected alloy) differ from the ones the shown result was computed with. */
export function proxyResultIsStale(result: ProxyEvaporativeResult | undefined, current: ProxyProcessInput, material?: string): boolean {
  if (!result) return false;
  if (material !== undefined && proxyAlloyFor(material) !== result.alloy) return true;
  return processKey(proxyResultSettings(result)) !== processKey(current);
}

const settingsText = (p: ProxyProcessInput) => `${fmt(p.power_W)} W, ${fmt(p.speed_mm_s)} mm/s, ${fmt(p.beamDiameter_um)} µm beam, ${fmt(p.preheat_C)} °C preheat`;

/** Job status line plus the submitted settings, so a running or finished job is never shown as if it used the current inputs. */
export function ProxyRunStatus({ job, submitted, process }: { job: ProxyEvaporativeJob; submitted?: ProxyProcessInput; process: ProxyProcessInput }) {
  const active = job.status === 'queued' || job.status === 'running';
  const settings = job.status === 'completed' && job.result ? proxyResultSettings(job.result) : submitted;
  const changed = !!settings && processKey(settings) !== processKey(process);
  return <>
    <p role="status" className="text-xs text-slate-400">Job {job.id} · {job.status}{active ? ` · ${Math.round(job.progress * 100)}%` : ''}</p>
    {settings && (active || changed) && <p className="text-xs text-slate-400">Submitted settings: {settingsText(settings)}.{changed ? ` The inputs above now read ${settingsText(process)}.` : ''}</p>}
  </>;
}

/** Plain explanation placed before the solver's own error text, which is kept verbatim. */
export function proxyEvaporativeErrorHint(message: string): string {
  if (!/exceeds finite enthalpy\/scenario range/.test(message)) return '';
  return 'At these settings the surface temperature leaves the model\'s declared range (up to 5000 K), so the run stops instead of clipping values. Lower the laser power or raise the scan speed and run again. Solver message: ';
}

/** The output evidence label and, when Unresolved, the scenario inputs that make it so. */
export function ProxyEvidenceNote({ result }: { result: ProxyEvaporativeResult }) {
  const ev = result.evidence;
  return <p className="rounded-lg border border-amber-400/40 p-3 text-sm text-amber-200" aria-label="Output evidence label">
    Evidence label: <strong>{ev.label}</strong>. {ev.summary}
    {ev.unresolvedInputs.length > 0 && <> Unresolved inputs: {ev.unresolvedInputs.join(', ')}.</>}
    {ev.userInputs.length > 0 && <> User inputs: {ev.userInputs.join(', ')}.</>}
  </p>;
}

export function ProxyEvaporativeResultView({ result, stale }: { result: ProxyEvaporativeResult; stale?: boolean }) {
  const g = result.geometry;
  const e = result.energy;
  const refused = !result.gate.geometryAvailable;
  const extent = (label: string, value: number | null, unit: string) => <div key={label}>
    <dt className="text-xs text-slate-400">{label}</dt>
    <dd className="mt-1 tabular-nums">{value === null ? <>null <span className="text-xs text-amber-200">(not available: {g.refusalReason ?? 'no reason returned'})</span></> : <>{fmt(value)} {unit}</>}</dd>
  </div>;
  return <div className="space-y-4" aria-label={`${result.alloy} evaporative result`}>
    {stale && <p role="status" className="rounded-lg border border-amber-400/40 p-3 text-sm text-amber-200">Inputs changed after this run. The result below is the executed snapshot, not the current inputs. Rerun to update it.</p>}
    <p className="text-sm text-amber-200">{result.researchLabel} · {result.tier} · {result.modelId} · experimentalValidation={String(result.experimentalValidation)} · productionReady={String(result.productionReady)}</p>
    <ProxyEvidenceNote result={result} />
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
    <WarningNotes className="text-xs text-slate-400" warnings={result.warnings.filter(w => w !== result.disclosure && w !== result.evidence.summary)} />
  </div>;
}

export function ProxyEvaporativePanel({ material, process }: { material: string; process: ProxyProcessInput }) {
  const [surfaceMode, setSurfaceMode] = useState<ProxySurfaceMode>('bare-plate');
  const [optIn, setOptIn] = useState(false);
  const [job, setJob] = useState<ProxyEvaporativeJob>();
  const [submitted, setSubmitted] = useState<ProxyProcessInput>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const availability = proxyEvaporativeAvailability(material, surfaceMode);
  const alloy = proxyAlloyFor(material);
  const profile = alloy ? PROXY_ALLOY_PROFILES[alloy] : undefined;
  const name = profile?.shortName ?? '316L / IN718';
  const active = job?.status === 'queued' || job?.status === 'running';
  const result = job?.status === 'completed' ? job.result : undefined;
  const stale = proxyResultIsStale(result, process, material);

  useVisiblePolling(async (isLive) => {
    if (!job) return null;
    try {
      const next = await proxyEvaporativeApi.get(job.id);
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
    const snapshot = { ...process };
    try { const next = await proxyEvaporativeApi.submit(buildProxyEvaporativeInput(availability.alloy, snapshot)); setSubmitted(snapshot); setJob(next); }
    catch (e) { setError(e instanceof Error ? e.message : 'Evaporative job submission failed'); }
    finally { setBusy(false); }
  };
  const cancel = async () => {
    if (!job || !active) return;
    try { setJob(await proxyEvaporativeApi.cancel(job.id)); }
    catch (e) { setError(e instanceof Error ? e.message : 'Cancellation failed'); }
  };
  const reasonId = 'proxy-evap-reason';

  return <section className="rounded-2xl border border-amber-400/30 bg-slate-900/50 p-4 md:p-5 space-y-4" aria-label={`${name} evaporative surface model`}>
    <div>
      <h3 className="font-medium">Thermal model choice ({name})</h3>
      <p className="mt-2 text-xs leading-5 text-amber-200">Opt-in research model. Fixed-surface conduction with vapour energy loss on a bare plate only. Uncalibrated, not experimentally validated. The default Standard simulation is unchanged.</p>
      {profile && <p className="mt-2 text-xs leading-5 text-amber-200">{profile.disclosure}</p>}
      {profile && <p className="mt-2 text-xs leading-5 text-amber-200">Output label: Unresolved. No source gives the vaporization transition thresholds for this alloy; the run uses declared defaults transitionLow_K = {profile.scenario.transitionLow_K} K and transitionHigh_K = {profile.scenario.transitionHigh_K} K.</p>}
    </div>
    <fieldset className="space-y-2">
      <legend className="text-xs text-slate-400">Surface</legend>
      <label className="mr-6 text-sm"><input type="radio" name="proxy-evap-surface" className="mr-2 accent-sky-400" checked={surfaceMode === 'bare-plate'} onChange={() => setSurfaceMode('bare-plate')} />Bare plate</label>
      <label className="text-sm"><input type="radio" name="proxy-evap-surface" className="mr-2 accent-sky-400" checked={surfaceMode === 'powder-layer'} onChange={() => setSurfaceMode('powder-layer')} />Powder layer</label>
    </fieldset>
    <label className="flex items-start gap-3 text-sm">
      <input type="checkbox" aria-describedby={reasonId} className="mt-1 accent-sky-400" checked={optIn && availability.available} disabled={!availability.available || busy || active} onChange={e => setOptIn(e.currentTarget.checked)} />
      <span>{profile?.label ?? 'Evaporative surface proxy model (research)'}</span>
    </label>
    <p id={reasonId} className="text-xs text-slate-400" role="status">
      {!('reason' in availability) ? `Runs a ${PROXY_EVAPORATIVE_TRACK_UM} µm declared track at the shared power, speed, beam diameter and preheat (${profile?.runtime ?? ''} on the reference CPU).` : availability.reason}
    </p>
    <div className="flex flex-wrap gap-3">
      <button className="rounded-lg border border-slate-500 px-3 py-2 text-sm disabled:opacity-40" disabled={busy || active || !availability.available || !optIn} onClick={submit}>Run {name} evaporative surface model</button>
      {active && <button className="rounded-lg border border-slate-500 px-3 py-2 text-sm" onClick={cancel}>Cancel</button>}
    </div>
    {job && <ProxyRunStatus job={job} submitted={submitted} process={process} />}
    {(error || job?.error) && <p role="alert" className="rounded-xl border border-red-400/30 p-3 text-sm text-red-200 whitespace-pre-wrap">{proxyEvaporativeErrorHint(error || job?.error || '')}{error || job?.error}</p>}
    {result && <ProxyEvaporativeResultView result={result} stale={stale} />}
  </section>;
}
