import { useEffect, useRef, useState } from 'react';
import { WarningNotes } from './SolidificationEstimates';
import { HowCalculated } from './HowCalculated';
import { useVisiblePolling } from '../hooks/useVisiblePolling';
import {
  ti64EvaporativeApi, type Ti64EvaporativeJob, type Ti64EvaporativeResult,
} from '../services/lpbfSimulationService';
import {
  TI64_EVAPORATION_SCENARIO, TI64_EVAPORATIVE_LABEL, TI64_SURFACE_NOTE, TI64_EVAPORATIVE_TRACK_UM, buildTi64EvaporativeInput, ti64EvaporativeAvailability,
} from '../utils/ti64EvaporativeModel';
import {
  P8_BELOW_ONSET_NOTE, P8_HYPOTHESIS_NOTE, P8_NO_FORWARDING_NOTE, P8_ROW_TITLE, P8_UNAVAILABLE_SUFFIX, W1_CRITERION_NOTE,
  fetchP8Depth, p8PairingApplies, p8PairingKey, type P8DepthView,
} from '../utils/ti64EvaporativeResearchDepth';

const fmt = (value: number | null | undefined) => value === null || value === undefined || !Number.isFinite(value) ? 'null' : Number(value.toPrecision(6)).toString();
const surface = 'rounded-xl border border-slate-700/50 bg-slate-900/40 p-4';

export interface Ti64ProcessInput { power_W: number; speed_mm_s: number; beamDiameter_um: number; preheat_C: number }

/**
 * Plain explanation placed before the solver's own error text (which is kept verbatim). The solver refuses rather than
 * clips when the surface temperature leaves the declared scenario range (TI64_EVAPORATION_SCENARIO.maxTemperature_K).
 */
export function evaporativeErrorHint(message: string): string {
  if (!/exceeds finite enthalpy\/scenario range/.test(message)) return '';
  return `At these settings the surface temperature leaves the model's declared range (up to ${TI64_EVAPORATION_SCENARIO.maxTemperature_K} K), so the run stops instead of clipping values. Lower the laser power or raise the scan speed and run again. Solver message: `;
}

export function P8PairedRow({ view }: { view: P8DepthView | 'loading' | 'error' }) {
  if (view === 'loading') return <section aria-label={P8_ROW_TITLE} className={surface}><h5 className="font-medium">{P8_ROW_TITLE}</h5><p role="status" className="mt-2 text-sm text-slate-400">Requesting the independent P8 research scenario…</p></section>;
  if (view === 'error') return <section aria-label={P8_ROW_TITLE} className={surface}><h5 className="font-medium">{P8_ROW_TITLE}</h5><p className="mt-2 text-sm text-amber-200">P8 linked depth is unavailable: REQUEST_FAILED The research request did not complete. {P8_UNAVAILABLE_SUFFIX}</p></section>;
  const band = view.band && view.band.completeness !== 'pending' ? view.band : null;
  return <section aria-label={P8_ROW_TITLE} className={surface} data-testid="p8-paired-row">
    <h5 className="font-medium">{P8_ROW_TITLE}</h5>
    {view.status === 'available' && view.linked
      ? <>
        <p className="mt-2 text-2xl tabular-nums">{fmt(view.linked.value as number)} <span className="text-sm text-slate-400">{view.linked.unit}</span></p>
        <p className="mt-1 text-xs text-slate-400">Field meltDepthLink.linkedMeltDepth_um · model {view.modelId} · power / onset power P/P* {fmt(view.powerOverOnset)}</p>
        <p className="mt-2 text-sm text-slate-200">{P8_HYPOTHESIS_NOTE}</p>
        {view.atOrBelowOnset && <p className="mt-2 text-sm text-amber-200">{P8_BELOW_ONSET_NOTE}</p>}
        {band
          ? <p className="mt-2 text-xs text-slate-300">Scenario envelope ({band.completeness}): min {fmt(band.min.value as number)} · nominal {fmt(band.nominal.value as number)} · max {fmt(band.max.value as number)} {band.unit}. {view.bandCaption}</p>
          : <p className="mt-2 text-xs text-slate-400" role="status">Scenario envelope pending or not returned.</p>}
        {view.warnings.length > 0 && <p className="mt-2 text-xs text-amber-200">P8 warnings: {view.warnings.join(', ')}</p>}
        {view.consistencySentence && <p className="mt-2 text-xs text-slate-300">P8 consistency note: {view.consistencySentence}</p>}
        <p className="mt-2 text-xs text-amber-200">{view.validationStatus}</p>
      </>
      : <>
        <p className="mt-2 text-sm text-amber-200">P8 linked depth is unavailable: {view.reason?.code} {view.reason?.text}. {P8_UNAVAILABLE_SUFFIX}</p>
        {view.validationStatus && <p className="mt-2 text-xs text-amber-200">{view.validationStatus}</p>}
      </>}
    <p className="mt-2 text-xs text-slate-400">{P8_NO_FORWARDING_NOTE}</p>
  </section>;
}

/** Values the P8 panel reads: the evaporative run's process inputs and the served P8 view; nothing is recomputed. */
export function p8ExplainerContext(result: Ti64EvaporativeResult, view: P8DepthView) {
  return {
    inputs: result.provenance.inputs,
    p8: {
      modelId: view.modelId, powerOverOnset: view.powerOverOnset, linkedMeltDepth_um: view.linked ? view.linked.value : null,
      uiSentence: view.uiSentence, consistencySentence: view.consistencySentence, validationStatus: view.validationStatus,
    },
  };
}

export function Ti64EvaporativeResultView({ result, p8, stale }: { result: Ti64EvaporativeResult; p8?: P8DepthView | 'loading' | 'error'; stale?: boolean }) {
  const g = result.geometry;
  const e = result.energy;
  const refused = !result.gate.geometryAvailable;
  const extent = (label: string, value: number | null, unit: string) => <div key={label}>
    <dt className="text-xs text-slate-400">{label}</dt>
    <dd className="mt-1 tabular-nums">{value === null ? <>null <span className="text-xs text-amber-200">(not available: {g.refusalReason ?? 'no reason returned'})</span></> : <>{fmt(value)} {unit}</>}</dd>
  </div>;
  return <div className="space-y-4" aria-label="Ti-6Al-4V evaporative result">
    {stale && <p role="status" className="rounded-lg border border-amber-400/40 p-3 text-sm text-amber-200">Inputs changed after this run. The result below is the executed snapshot; the paired P8 row is hidden until you rerun.</p>}
    <p className="text-sm text-amber-200">{result.tier} · {result.modelId} · experimentalValidation={String(result.experimentalValidation)} · productionReady={String(result.productionReady)}</p>
    <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div><dt className="text-xs text-slate-400">Peak temperature</dt><dd className="mt-1 tabular-nums">{fmt(result.peakTemperature_K)} K</dd><dd className="text-xs text-slate-400">{result.temperatureLabel}</dd></div>
      <div><dt className="text-xs text-slate-400">Width</dt><dd className="mt-1 tabular-nums">{fmt(g.width_um)} µm</dd><dd className="text-xs text-slate-400">{g.widthLabel}</dd></div>
      {extent('Depth', g.depth_um, 'µm')}{extent('Length', g.length_um, 'µm')}{extent('Volume', g.volume_um3, 'µm³')}
      <div><dt className="text-xs text-slate-400">Accepted time and steps</dt><dd className="mt-1 tabular-nums">{fmt(result.acceptedTime_s)} s · {result.acceptedStepCount} steps</dd></div>
      <div><dt className="text-xs text-slate-400">Declared track</dt><dd className="mt-1 tabular-nums">{fmt(Number(result.provenance.inputs.trackLength_um))} µm · mesh {fmt(Number(result.provenance.inputs.mesh_um))} µm</dd></div>
    </dl>
    {g.widthWarning && <p className="text-sm text-amber-200">{g.widthWarning}</p>}
    {refused && g.refusalReason && <p className="text-sm text-amber-200">Refusal: {g.refusalReason}</p>}
    {result.gate.onset && <p className="text-sm text-slate-200">{W1_CRITERION_NOTE}</p>}
    <table className="w-full max-w-xl text-left text-xs"><caption className="sr-only">Energy ledger</caption>
      <thead><tr><th scope="col">Term</th><th scope="col">Value (J)</th></tr></thead>
      <tbody>
        {([['Input', e.input_J], ['Evaporative loss', e.evaporative_J], ['Radiative and convective loss', e.radiativeConvective_J],
          ['Base loss', e.base_J], ['Stored', e.stored_J], ['Residual', e.residual_J]] as const).map(([k, v]) => <tr key={k}><th scope="row" className="font-normal">{k}</th><td className="tabular-nums">{fmt(v)}</td></tr>)}
        <tr><th scope="row" className="font-normal">Relative residual</th><td className="tabular-nums">{fmt(e.relativeResidual)}</td></tr>
      </tbody></table>
    <p className="text-xs text-slate-400">{result.diagnosticMassLabel}: {fmt(result.diagnosticEmittedMass_kg)} kg</p>
    <WarningNotes className="text-xs text-slate-400" warnings={result.warnings} />
    <HowCalculated explainerId="ti64-evaporation" result={result} />
    {p8 && !stale && <P8PairedRow view={p8} />}
    {p8 && !stale && typeof p8 !== 'string' && p8.status === 'available' && <HowCalculated explainerId="p8-linked-depth" result={p8ExplainerContext(result, p8)} />}
  </div>;
}

export function Ti64EvaporativePanel({ material, process }: { material: string; process: Ti64ProcessInput }) {
  const [optIn, setOptIn] = useState(false);
  const [job, setJob] = useState<Ti64EvaporativeJob>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [p8, setP8] = useState<P8DepthView | 'loading' | 'error'>();
  const availability = ti64EvaporativeAvailability(material);
  const active = job?.status === 'queued' || job?.status === 'running';
  const result = job?.status === 'completed' ? job.result : undefined;
  const currentKey = JSON.stringify(['Ti-6Al-4V', process.power_W, process.speed_mm_s, process.beamDiameter_um, process.preheat_C]);
  const stale = !!result && p8PairingKey(result) !== currentKey;
  const p8For = useRef('');

  useEffect(() => {
    if (!result || !p8PairingApplies(result) || job === undefined || p8For.current === job.id) return;
    p8For.current = job.id;
    const controller = new AbortController();
    setP8('loading');
    fetchP8Depth(result, view => { if (!controller.signal.aborted) setP8(view); }, controller.signal)
      .catch(err => { if (!(err instanceof Error && err.name === 'AbortError') && !controller.signal.aborted) setP8('error'); });
    return () => { controller.abort(); p8For.current = ''; };
  }, [result, job]);

  useVisiblePolling(async (isLive) => {
    if (!job) return null;
    try {
      const next = await ti64EvaporativeApi.get(job.id);
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
    setBusy(true); setError(''); setP8(undefined); p8For.current = '';
    try { setJob(await ti64EvaporativeApi.submit(buildTi64EvaporativeInput(process))); }
    catch (e) { setError(e instanceof Error ? e.message : 'Evaporative job submission failed'); }
    finally { setBusy(false); }
  };
  const cancel = async () => {
    if (!job || !active) return;
    try { setJob(await ti64EvaporativeApi.cancel(job.id)); }
    catch (e) { setError(e instanceof Error ? e.message : 'Cancellation failed'); }
  };

  return <section className="rounded-2xl border border-amber-400/30 bg-slate-900/50 p-4 md:p-5 space-y-4" aria-label="Ti-6Al-4V evaporative surface model">
    <div>
      <h3 className="font-medium">Thermal model choice</h3>
      <p className="mt-2 text-xs leading-5 text-amber-200">Opt-in research model. Fixed-surface conduction with Ti vapour energy loss on a bare plate. Uncalibrated, not experimentally validated. The default Standard simulation is unchanged.</p>
    </div>
    <label className="flex items-start gap-3 text-sm">
      <input type="checkbox" aria-describedby="ti64-evap-reason" className="mt-1 accent-sky-400" checked={optIn && availability.available} disabled={!availability.available || busy || active} onChange={e => setOptIn(e.currentTarget.checked)} />
      <span>{TI64_EVAPORATIVE_LABEL}</span>
    </label>
    <p id="ti64-evap-reason" className="text-xs text-slate-400" role="status">
      {!('reason' in availability) ? `Runs a ${TI64_EVAPORATIVE_TRACK_UM} µm declared track at the shared power, speed, beam diameter and preheat (about 20 s on the reference CPU).` : (availability as {reason:string}).reason}
    </p>
    <p className="text-sm text-slate-200">{TI64_SURFACE_NOTE}</p>
    <div className="flex flex-wrap gap-3">
      <button className="rounded-lg border border-sky-400 bg-sky-500/20 px-4 py-2 text-sm font-medium text-slate-100 disabled:opacity-40" disabled={busy || active || !availability.available || !optIn} onClick={submit}>Run Ti-6Al-4V evaporative model</button>
      {active && <button className="rounded-lg border border-slate-500 px-3 py-2 text-sm" onClick={cancel}>Cancel</button>}
    </div>
    {job && <p role="status" className="text-xs text-slate-400">Job {job.id} · {job.status}{active ? ` · ${Math.round(job.progress * 100)}%` : ''}</p>}
    {(error || job?.error) && <p role="alert" className="rounded-xl border border-red-400/30 p-3 text-sm text-red-200 whitespace-pre-wrap">{evaporativeErrorHint(error || job?.error || '')}{error || job?.error}</p>}
    {result && <Ti64EvaporativeResultView result={result} p8={p8} stale={stale} />}
  </section>;
}
