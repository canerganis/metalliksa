/**
 * SolidificationMicrostructureLab.tsx — Phase 8
 * Screening-field LPBF solidification: G/R map, dendrite spacing, morphology tendency and diagnostics.
 * Every number comes from Python (lpbf_thermal_solver thermal.solidificationKinetics for the selected heat
 * source; with Rosenthal and the Build Job's inputs they equal the Build Job projection, Goldak/Eagar–Tsai
 * fields give different G/R) through pythonComputationService. The lab sends the alloy name and visible process
 * inputs only; Python looks the alloy up, nothing is defaulted or substituted. Status-labelled screening:
 * not in-situ front tracking, not validated.
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { SolidificationQuantities } from './SolidificationQuantities';
import { useMaterialSpecimenStore } from '../store/useMaterialSpecimenStore';
import { pythonComputationService } from '../services/pythonComputationService';
import type { SolidificationMicrostructureAvailable } from '../services/pythonComputationService';
import { SolidificationEstimates } from './SolidificationEstimates';
import { GrSolidificationMapCard } from './GrSolidificationMapCard';
import { solidificationOutcome } from '../utils/solidificationOutcome';
import { createLatestRequestGate, settleLatestRequest } from '../utils/solidificationRequest';
import {
  authorityAlloy, authorityThermalProvenance, solidificationMaterialInputs, type AuthorityAlloyId, type SolidificationMaterialInputs,
} from '../data/lpbfMaterialAuthority';

// Preset label -> alloy id. The label is mapped to the Python thermophysical name (authority thermalName) that
// is sent as materialName; the displayed k/liquidus/absorptivity read the Python authority
// (src/generated/lpbfMaterialAuthority.json) for display only. No alloy numbers here. Pinned by
// tests/lpbf-material-authority.test.ts.
export const SOLIDIFICATION_PRESETS = {
  'Inconel 718': 'in718',
  'Ti-6Al-4V': 'ti6al4v',
  'AlSi10Mg': 'alsi10mg',
  '316L SS': 'ss316l',
} as const satisfies Record<string, AuthorityAlloyId>;

function solidificationPresetAlloyId(label: string): AuthorityAlloyId {
  if (!Object.prototype.hasOwnProperty.call(SOLIDIFICATION_PRESETS, label)) {
    throw new Error(`Unknown material preset "${label}"; no surrogate alloy is substituted.`);
  }
  return SOLIDIFICATION_PRESETS[label as keyof typeof SOLIDIFICATION_PRESETS];
}

/** Display-only authority row for a preset label; an unknown label throws (no surrogate alloy). */
export function solidificationPresetInputs(label: string): SolidificationMaterialInputs {
  return solidificationMaterialInputs(solidificationPresetAlloyId(label));
}

export type SolidificationHeatSource = 'rosenthal' | 'eagar-tsai' | 'goldak';
export const SOLIDIFICATION_HEAT_SOURCES: Record<SolidificationHeatSource, string> = {
  rosenthal: 'Rosenthal (default)',
  'eagar-tsai': 'Eagar–Tsai',
  goldak: 'Goldak',
};

export interface SolidificationProcessInputs {
  power_W: number;
  speed_mm_s: number;
  beamDiameter_um: number;
  preheat_C: number;
  layerThickness_um: number;
  hatch_um: number;
  heatSource: SolidificationHeatSource;
}

/**
 * The exact payload the lab hands to computeSolidificationMicrostructure: the Python material name plus the
 * visible process inputs. No k/liquidus/absorptivity is sent; Python is the authority for the alloy.
 */
export function solidificationRequest(
  label: string,
  process: SolidificationProcessInputs,
): { params: Record<string, number | string> } {
  const materialName = authorityAlloy(solidificationPresetAlloyId(label)).thermalName;
  return { params: { materialName, ...process } };
}

const panelClass = 'rounded-2xl border border-white/10 bg-[#111b25]';

interface Props {
  onSendToModule?: (moduleId: string, data: unknown) => void;
}


export const SolidificationMicrostructureLab: React.FC<Props> = () => {
  const lpbf = useMaterialSpecimenStore(s => s.activeSpecimen.lpbf);
  const updateLpbfProcess = useMaterialSpecimenStore(s => s.updateLpbfProcess);
  const laserPower = lpbf.laserPower_W, scanSpeed = lpbf.scanSpeed_mms, hatch = lpbf.hatch_um;
  const layerThickness = lpbf.layer_um, beamDiameter = lpbf.beamDiameter_um, preheat = lpbf.preheatTemp_C;
  const setLaserPower = (value: number) => updateLpbfProcess({ laserPower_W: value });
  const setScanSpeed = (value: number) => updateLpbfProcess({ scanSpeed_mms: value });
  const setHatch = (value: number) => updateLpbfProcess({ hatch_um: value });
  const setLayerThickness = (value: number) => updateLpbfProcess({ layer_um: value });
  const setBeamDiameter = (value: number) => updateLpbfProcess({ beamDiameter_um: value });
  const setPreheat = (value: number) => updateLpbfProcess({ preheatTemp_C: value });
  const [heatSource, setHeatSource] = useState<SolidificationHeatSource>('rosenthal');
  const [selectedAlloy, setSelectedAlloy] = useState('Inconel 718');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<SolidificationMicrostructureAvailable | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unavailableReason, setUnavailableReason] = useState<string | null>(null);
  const [degenerate, setDegenerate] = useState(false);
  const requestGate = useRef(createLatestRequestGate());
  const [inputSensitivity, setInputSensitivity] = useState(false);
  // On by default (maintainer decision 2026-10-16): a labelled conduction-only scenario, never a keyhole front.
  const [conductionSurrogate, setConductionSurrogate] = useState(true);
  const [estimates, setEstimates] = useState<unknown>(null);
  const [estimatesLoading, setEstimatesLoading] = useState(false);
  const [estimatesError, setEstimatesError] = useState<string | null>(null);
  const estimateGate = useRef(createLatestRequestGate());

  useEffect(() => () => { requestGate.current.invalidate(); estimateGate.current.invalidate(); }, []);

  const alloyProps = solidificationPresetInputs(selectedAlloy);
  const alloyQuality = authorityThermalProvenance(SOLIDIFICATION_PRESETS[selectedAlloy as keyof typeof SOLIDIFICATION_PRESETS]).quality;
  const invalidateResult = () => {
    requestGate.current.invalidate();
    setIsLoading(false);
    setResult(null);
    setError(null);
    setUnavailableReason(null);
    setDegenerate(false);
    estimateGate.current.invalidate();
    setEstimatesLoading(false);
    setEstimates(null);
    setEstimatesError(null);
  };

  useEffect(() => { invalidateResult(); }, [laserPower, scanSpeed, hatch, layerThickness, beamDiameter, preheat]);

  const handleCompute = useCallback(async () => {
    const generation = requestGate.current.begin();
    setIsLoading(true);
    setError(null);
    setUnavailableReason(null);
    setDegenerate(false);
    setResult(null);
    await settleLatestRequest(requestGate.current, generation, () =>
      pythonComputationService.computeSolidificationMicrostructure(solidificationRequest(selectedAlloy, {
        power_W: laserPower,
        speed_mm_s: scanSpeed,
        hatch_um: hatch,
        layerThickness_um: layerThickness,
        beamDiameter_um: beamDiameter,
        preheat_C: preheat,
        heatSource,
      })), {
        onSuccess: res => {
          const outcome = solidificationOutcome(res);
          if ('error' in outcome) {
            setUnavailableReason(outcome.error);
            setDegenerate(outcome.degenerate === true);
            return;
          }
          setResult(outcome.result);
        },
        onError: (e: unknown) => setError(e instanceof Error ? e.message : 'Computation failed. Check the service and try again.'),
        onFinally: () => setIsLoading(false),
      });
  }, [laserPower, scanSpeed, hatch, layerThickness, beamDiameter, preheat, heatSource, selectedAlloy]);

  const handleComputeEstimates = useCallback(async () => {
    const generation = estimateGate.current.begin();
    setEstimatesLoading(true);
    setEstimatesError(null);
    setEstimates(null);
    await settleLatestRequest(estimateGate.current, generation, () =>
      pythonComputationService.computeSolidificationEstimates({
        params: solidificationRequest(selectedAlloy, {
          power_W: laserPower, speed_mm_s: scanSpeed, hatch_um: hatch, layerThickness_um: layerThickness,
          beamDiameter_um: beamDiameter, preheat_C: preheat, heatSource,
        }).params,
        options: { inputSensitivity, conductionSurrogate },
      }), {
        onSuccess: res => setEstimates(res),
        onError: (e: unknown) => setEstimatesError(e instanceof Error ? e.message : 'Estimate computation failed. Check the service and try again.'),
        onFinally: () => setEstimatesLoading(false),
      });
  }, [laserPower, scanSpeed, hatch, layerThickness, beamDiameter, preheat, heatSource, selectedAlloy, inputSensitivity, conductionSurrogate]);

  const numberField = (label: string, value: number, min: number, max: number, step: number, unit: string, update: (value: number) => void) => (
    <label className="block min-w-0">
      <span className="mb-2 flex items-center justify-between gap-2 text-xs font-medium text-slate-300">
        <span>{label}</span><span className="text-[10px] font-normal text-slate-500">{unit}</span>
      </span>
      <input
        type="number" value={value} min={min} max={max} step={step}
        aria-label={`${label} (${unit})`}
        onChange={event => {
          if (event.target.value === '') return;
          const next = Number(event.target.value);
          update(Number.isFinite(next) ? next : min);
          invalidateResult();
        }}
        onBlur={event => {
          const next = Number(event.target.value);
          const bounded = Number.isFinite(next) ? Math.min(max, Math.max(min, next)) : min;
          if (bounded !== value) {
            update(bounded);
            invalidateResult();
          }
        }}
        className="w-full rounded-lg border border-white/10 bg-[#0b141d] px-3 py-2.5 font-mono text-sm text-slate-100 outline-none transition focus:border-cyan-300/60 focus:ring-2 focus:ring-cyan-300/10"
      />
      <span className="mt-1.5 block text-[10px] text-slate-500">{min}–{max} {unit}</span>
    </label>
  );

  return (
    <div className="flex h-full min-h-0 flex-col gap-5 overflow-y-auto bg-[#0a1118] p-4 text-slate-100 sm:p-6 lg:p-7">
      <header className={`${panelClass} relative isolate overflow-hidden p-5 sm:p-7`}>
        <div aria-hidden="true" className="pointer-events-none absolute -right-20 -top-32 -z-10 h-80 w-80 rounded-full border border-cyan-200/10 bg-[radial-gradient(circle_at_center,rgba(90,195,214,.16),rgba(90,195,214,0)_68%)]" />
        <div aria-hidden="true" className="pointer-events-none absolute bottom-0 right-[8%] -z-10 h-px w-2/5 bg-gradient-to-l from-cyan-200/40 to-transparent" />
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-cyan-100/15 bg-cyan-100/[.06] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[.19em] text-cyan-100/80">Phase 08 · Microstructure</span>
              <span className="text-[10px] uppercase tracking-[.15em] text-slate-500">LPBF process study</span>
            </div>
            <h1 className="font-serif text-3xl font-medium tracking-tight text-white sm:text-4xl">Solidification atlas</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400 sm:text-[15px]">
              Screening conduction-field G/R from the Python thermal solver, read as dendrite spacing and morphology tendency.
              Status-labelled screening: not in-situ front tracking, not validated.
            </p>
          </div>
          <div className="flex min-w-[152px] items-center gap-3 rounded-xl border border-white/[.08] bg-black/15 px-3 py-2.5">
            {/* Animate only while the solver is running; idle is a static neutral dot. */}
            <span data-testid="solidification-status-dot" className={`relative flex h-2.5 w-2.5 ${isLoading ? 'animate-pulse' : ''}`}>
              <span className={`absolute inline-flex h-full w-full rounded-full ${isLoading ? 'bg-amber-300/50' : result ? 'bg-cyan-200/30' : 'bg-slate-400/30'}`} />
              <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${isLoading ? 'bg-amber-300' : result ? 'bg-cyan-200' : 'bg-slate-400'}`} />
            </span>
            <div>
              <div className="text-xs font-semibold text-slate-200">{isLoading ? 'Solver running' : result ? 'Analysis ready' : 'Ready to analyse'}</div>
              <div className="mt-0.5 text-[10px] text-slate-500">{result ? `${result.heatSourceModel ?? 'screening field'} · ${result.status}` : 'Configure the process below'}</div>
            </div>
          </div>
        </div>
        <div className="mt-6 grid max-w-3xl grid-cols-3 gap-2 border-t border-white/[.08] pt-4 sm:gap-6">
          {[
            ['01', 'CONDUCTION FIELD'], ['02', 'DENDRITE SCALE'], ['03', 'MORPHOLOGY TENDENCY'],
          ].map(([step, title]) => (
            <div key={step} className="flex items-center gap-2 sm:gap-3">
              <span className="font-mono text-xs text-cyan-200/75">{step}</span>
              <span className="text-[9px] font-semibold tracking-[.09em] text-slate-500 sm:text-[10px]">{title}</span>
            </div>
          ))}
        </div>
      </header>

      <section className={`${panelClass} p-4 sm:p-5`} aria-labelledby="process-heading">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="mb-1 text-[10px] font-semibold uppercase tracking-[.17em] text-cyan-200/70">01 / Process definition</div>
            <h2 id="process-heading" className="text-lg font-semibold tracking-tight text-slate-100">Set the operating point</h2>
          </div>
          <p className="max-w-md text-xs leading-5 text-slate-500">Changing a setting clears the previous result and ignores any pending response for the old inputs.</p>
        </div>

        <div className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2 xl:grid-cols-6">
          <label className="block min-w-0 xl:col-span-2">
            <span className="mb-2 flex items-center justify-between text-xs font-medium text-slate-300"><span>Material preset</span><span className="text-[10px] text-slate-500">PYTHON LOOKUP</span></span>
            <select
              aria-label="Material preset"
              className="w-full rounded-lg border border-white/10 bg-[#0b141d] px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-cyan-300/60 focus:ring-2 focus:ring-cyan-300/10"
              value={selectedAlloy}
              onChange={event => { setSelectedAlloy(event.target.value); invalidateResult(); }}
            >
              {Object.keys(SOLIDIFICATION_PRESETS).map(alloy => <option key={alloy} value={alloy}>{alloy}</option>)}
            </select>
            <span className="mt-1.5 block text-[10px] text-slate-500">Sends the alloy name; Python looks up its properties</span>
          </label>
          {numberField('Laser power', laserPower, 50, 1000, 5, 'W', setLaserPower)}
          {numberField('Scan speed', scanSpeed, 100, 3000, 10, 'mm/s', setScanSpeed)}
          {numberField('Hatch spacing', hatch, 50, 300, 5, 'µm', setHatch)}
          {numberField('Layer thickness', layerThickness, 20, 120, 5, 'µm', setLayerThickness)}
          {numberField('Beam diameter', beamDiameter, 20, 500, 5, 'µm', setBeamDiameter)}
          {numberField('Preheat', preheat, 20, 800, 5, '°C', setPreheat)}
          <label className="block min-w-0 xl:col-span-2">
            <span className="mb-2 flex items-center justify-between text-xs font-medium text-slate-300"><span>Heat source</span><span className="text-[10px] text-slate-500">CONDUCTION FIELD</span></span>
            <select
              aria-label="Heat source"
              className="w-full rounded-lg border border-white/10 bg-[#0b141d] px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-cyan-300/60 focus:ring-2 focus:ring-cyan-300/10"
              value={heatSource}
              onChange={event => { setHeatSource(event.target.value as SolidificationHeatSource); invalidateResult(); }}
            >
              {(Object.entries(SOLIDIFICATION_HEAT_SOURCES) as [SolidificationHeatSource, string][]).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
            </select>
            <span className="mt-1.5 block text-[10px] text-slate-500">Always sent explicitly: {SOLIDIFICATION_HEAT_SOURCES[heatSource]} is selected (Python alone would default to Rosenthal if it were absent)</span>
          </label>
        </div>

        <div className="mt-5 flex flex-col-reverse gap-3 border-t border-white/[.07] pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[11px] leading-5 text-slate-500">Python authority row (display only): <span className="font-mono text-slate-400">k {alloyProps.k_WmK} W/m·K</span><span className="mx-2 text-slate-700">·</span><span className="font-mono text-slate-400">Tₗ {Math.round(alloyProps.liquidus_K)} K</span><span className="mx-2 text-slate-700">·</span><span className="font-mono text-slate-400">A {alloyProps.absorptivity}</span><span className="mx-2 text-slate-700">·</span><span className="text-slate-500">{alloyQuality}</span></p>
          <button
            type="button" onClick={handleCompute} disabled={isLoading}
            className="group inline-flex min-h-11 items-center justify-center gap-3 rounded-lg border border-cyan-100/20 bg-gradient-to-r from-cyan-200/15 to-blue-300/10 px-5 text-sm font-semibold text-cyan-50 shadow-[0_8px_24px_rgba(26,156,180,.08)] transition hover:border-cyan-100/40 hover:from-cyan-200/20 hover:to-blue-300/15 disabled:cursor-wait disabled:opacity-60"
          >
            <span aria-hidden="true" className={isLoading ? 'animate-spin' : ''}>{isLoading ? '◌' : '↗'}</span>
            {isLoading ? 'Calculating field…' : 'Run solidification analysis'}
          </button>
        </div>
      </section>

      {error && (
        <section role="alert" className="flex items-start gap-3 rounded-xl border border-rose-300/20 bg-rose-400/[.07] px-4 py-3.5 text-sm text-rose-100">
          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-rose-200/30 text-xs">!</span>
          <div className="min-w-0"><h2 className="font-semibold">Analysis could not be completed</h2><p className="mt-1 break-words text-xs leading-5 text-rose-100/70">{error}</p></div>
        </section>
      )}

      {unavailableReason && !isLoading && (
        <section role="status" data-solidification-status={degenerate ? 'degenerate-floor' : 'unavailable'} className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/[.04] px-4 py-3.5 text-sm text-slate-200">
          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-white/20 text-xs">i</span>
          <div className="min-w-0">
            <h2 className="font-semibold">{degenerate ? 'No computed solidification result' : 'Unavailable'}</h2>
            <p className="mt-1 break-words text-xs leading-5 text-slate-400">{unavailableReason}</p>
          </div>
        </section>
      )}

      {isLoading && (
        <section role="status" aria-live="polite" className={`${panelClass} flex min-h-48 flex-col items-center justify-center gap-4 px-5 py-8 text-center`}>
          <div className="relative flex h-12 w-12 items-center justify-center rounded-full border border-cyan-100/20">
            <span className="absolute inset-1 animate-spin rounded-full border border-transparent border-t-cyan-200/80" />
            <span className="h-2 w-2 rounded-full bg-cyan-100 shadow-[0_0_18px_5px_rgba(103,221,232,.3)]" />
          </div>
          <div><h2 className="font-medium text-slate-100">Evaluating the screening conduction field…</h2></div>
          <div className="h-1 w-48 overflow-hidden rounded-full bg-white/[.07]"><div className="h-full w-2/3 animate-pulse rounded-full bg-gradient-to-r from-cyan-300/30 via-cyan-200 to-blue-300/30" /></div>
        </section>
      )}

      {!result && !isLoading && !error && !unavailableReason && (
        <section className={`${panelClass} relative flex min-h-56 items-center overflow-hidden px-5 py-8 sm:min-h-64 sm:px-10`}>
          <div aria-hidden="true" className="pointer-events-none absolute inset-y-0 right-0 hidden w-2/5 opacity-70 sm:block">
            <div className="absolute right-12 top-1/2 h-48 w-48 -translate-y-1/2 rounded-full border border-cyan-100/[.08]" />
            <div className="absolute right-20 top-1/2 h-32 w-32 -translate-y-1/2 rounded-full border border-cyan-100/[.12]" />
            <div className="absolute right-28 top-1/2 h-16 w-16 -translate-y-1/2 rounded-full border border-cyan-100/[.2] bg-[radial-gradient(circle,rgba(96,210,222,.2),rgba(96,210,222,0)_70%)]" />
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 420 220" fill="none" aria-hidden="true">
              <path d="M5 173C76 170 82 48 156 53s79 119 143 98 66-87 116-91" stroke="rgba(111,215,224,.42)" strokeWidth="1.3" />
              <path d="M10 195c70-2 85-100 145-95 65 5 79 82 136 68 53-13 79-68 123-71" stroke="rgba(111,215,224,.18)" strokeWidth="1" strokeDasharray="3 6" />
              <path d="M80 26v166M164 26v166M248 26v166M332 26v166" stroke="rgba(255,255,255,.045)" />
            </svg>
          </div>
          <div className="relative max-w-lg">
            <div className="mb-3 text-[10px] font-semibold uppercase tracking-[.18em] text-cyan-100/70">Your analysis canvas</div>
            <h2 className="text-xl font-semibold tracking-tight text-slate-100 sm:text-2xl">Screening operating point</h2>
            <p className="mt-2 max-w-md text-sm leading-6 text-slate-400">Choose a material and operating point, then run the analysis to reveal the screening G–R regime, dendrite scales and morphology tendency.</p>
            <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-[11px] text-slate-500"><span><b className="mr-1.5 text-cyan-100/70">01</b>Conduction field</span><span><b className="mr-1.5 text-cyan-100/70">02</b>Cell spacing</span><span><b className="mr-1.5 text-cyan-100/70">03</b>Morphology tendency</span></div>
          </div>
        </section>
      )}

      {result && !isLoading && <section aria-label="Analysis summary" data-solidification-status={result.status} className={panelClass}>
        <SolidificationQuantities container={result} />
      </section>}
      <section className={`${panelClass} p-4 sm:p-5`} aria-labelledby="estimates-heading">
        <h2 id="estimates-heading" className="text-lg font-semibold tracking-tight text-slate-100">Solidification estimates</h2>
        <p className="mt-1 text-xs leading-5 text-slate-400">Opt-in estimate channel. Values are uncalibrated physics-model estimates unless marked Estimated; nothing here changes the Build Job or the process verdict.</p>
        <div className="mt-3 flex flex-col gap-2 text-xs text-slate-300">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={inputSensitivity} onChange={e => { setInputSensitivity(e.target.checked); invalidateResult(); }} />
            <span>Input sensitivity sweep (11 field runs, slower)</span>
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={conductionSurrogate} onChange={e => { setConductionSurrogate(e.target.checked); invalidateResult(); }} />
            <span>Conduction-field surrogate when the keyhole leg sets the depth (on by default)</span>
          </label>
        </div>
        <button type="button" onClick={handleComputeEstimates} disabled={estimatesLoading}
          className="mt-3 inline-flex min-h-11 items-center justify-center rounded-lg border border-cyan-100/20 bg-cyan-200/10 px-5 text-sm font-semibold text-cyan-50 transition hover:border-cyan-100/40 disabled:cursor-wait disabled:opacity-60">
          {estimatesLoading ? 'Computing estimates…' : 'Compute solidification estimates'}
        </button>
        {estimatesLoading && <p role="status" aria-live="polite" className="mt-3 text-xs text-slate-400">Evaluating the estimate channel…</p>}
        {estimatesError && <div role="alert" className="mt-3 rounded-xl border border-rose-300/20 bg-rose-400/[.07] px-4 py-3 text-sm text-rose-100">
          <h3 className="font-semibold">Estimates could not be computed</h3><p className="mt-1 break-words text-xs leading-5 text-rose-100/70">{estimatesError}</p>
        </div>}
        {estimates !== null && !estimatesLoading && <div className="mt-3"><SolidificationEstimates payload={estimates} /></div>}
      </section>
      <GrSolidificationMapCard />
    </div>
  );
};

export default SolidificationMicrostructureLab;
