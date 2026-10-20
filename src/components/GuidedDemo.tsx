import React, { useEffect, useRef, useState } from "react";
import { useMaterialSpecimenStore } from "../store/useMaterialSpecimenStore";
import { useEngineeringField, useLpbfEngineeringStore } from "../store/useLpbfEngineeringStore";
import { useLpbfResearchModelStore } from "../store/useLpbfResearchModelStore";
import { GUIDED_DEMO_STEPS, readGuidedDemoOutcome, useGuidedDemoStore, writeGuidedDemoOutcome, type GuidedDemoStep } from "../store/useGuidedDemoStore";
import { COMMITTED_CALIBRATION_SCORECARD } from "../data/lpbfCalibrationScorecardRecord";
import type { LpbfCalibrationScorecardDocument } from "../data/lpbfCalibrationScorecard";
import type { PythonEngineStatus } from "../services/pythonComputationService";
import type { SimulationJob } from "../services/lpbfSimulationService";
import { compareToMeasurement, demoCase, researchDepthForCase, scorecardStatementFor, type DemoCase } from "../utils/guidedDemo";
import { visibleModalOpen } from "../hooks/useCommandPaletteShortcut";
import { formatExactNumber } from "../utils/numberFormat";
import { IS_STATIC_DEMO } from "../demo/flag.ts";

const button = "mk-status px-3 py-2 text-xs";
const STEP_TITLES: Record<GuidedDemoStep, string> = { 1: "Material", 2: "Run", 3: "Compare", 4: "Scorecard" };
const fmt1 = (value: number) => value.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

type StorageLike = Pick<Storage, "getItem" | "setItem">;
export interface GuidedDemoProps {
  /** True on the Overview page (the first-run card shows only there). */
  home: boolean;
  engine: PythonEngineStatus | null;
  engineChecking: boolean;
  /** Test seam; defaults to localStorage. */
  storage?: StorageLike;
  scorecard?: LpbfCalibrationScorecardDocument | null;
}

/** First-run card, then the docked tour panel. Mounted lazily by App. */
export function GuidedDemo({ home, engine, engineChecking, storage, scorecard = COMMITTED_CALIBRATION_SCORECARD }: GuidedDemoProps) {
  const active = useGuidedDemoStore(s => s.active);
  const startError = useGuidedDemoStore(s => s.startError);
  if (active) return <TourPanel engine={engine} engineChecking={engineChecking} scorecard={scorecard} />;
  return <>
    <FirstRunCard home={home} storage={storage} />
    {startError && !home && <p role="alert" className="fixed bottom-4 right-4 z-40 max-w-sm rounded-xl border border-amber-500/50 bg-slate-950 p-3 text-xs text-amber-200 print:hidden">{startError}</p>}
  </>;
}

export function FirstRunCard({ home, storage }: { home: boolean; storage?: StorageLike }) {
  const [skipped, setSkipped] = useState(false);
  const error = useGuidedDemoStore(s => s.startError);
  if (!home || skipped || readGuidedDemoOutcome(storage) !== null) return null;
  const skip = () => { writeGuidedDemoOutcome("dismissed", storage); setSkipped(true); };
  const start = () => { void useGuidedDemoStore.getState().start(); };
  return <section role="region" aria-labelledby="guided-demo-card-title" className="mk-plate mb-5 px-4 py-3 text-sm text-slate-300 print:hidden">
    <h2 id="guided-demo-card-title" className="text-sm font-medium text-slate-100">New here? Take a 4-step tour</h2>
    <p className="mt-1 text-xs text-slate-400">Load one published NIST AMB2022-03 Inconel 718 track and run a screening job. See its analytical width and depth estimates beside the measurement, labelled Screening only, comparison not validation. Starting replaces the shared material and process values; you can restore them. Nothing runs without your confirmation.</p>
    {error && <p role="alert" className="mt-2 text-xs text-amber-200">{error}</p>}
    <div className="mt-3 flex flex-wrap gap-2"><button type="button" className={button} onClick={start}>Start tour</button><button type="button" className={button} onClick={skip}>Skip</button></div>
  </section>;
}

function useCase(): { demo: DemoCase | null; error: string } {
  try { return { demo: demoCase(), error: "" }; } catch (reason) { return { demo: null, error: reason instanceof Error ? reason.message : "Case unavailable." }; }
}

export function TourPanel({ engine, engineChecking, scorecard }: { engine: PythonEngineStatus | null; engineChecking: boolean; scorecard: LpbfCalibrationScorecardDocument | null }) {
  const step = useGuidedDemoStore(s => s.step);
  const previous = useGuidedDemoStore(s => s.previousSpecimen);
  const { next, back, exit, finish, restorePrevious } = useGuidedDemoStore.getState();
  const heading = useRef<HTMLHeadingElement>(null);
  const [restored, setRestored] = useState(false);
  const { demo, error } = useCase();
  const panel = useRef<HTMLElement>(null);

  useEffect(() => { heading.current?.focus(); }, [step]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented || visibleModalOpen()) return;
      const target = event.target instanceof HTMLElement ? event.target : null;
      const insidePanel = !!target && !!panel.current?.contains(target);
      const editable = !!target && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
      if (!insidePanel && editable) return;
      useGuidedDemoStore.getState().exit();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return <section ref={panel} role="region" aria-labelledby="guided-demo-title"
    className={`${step === 2 ? "relative mb-5 rounded-xl" : "fixed inset-x-0 bottom-0 z-40 h-[50vh] rounded-t-xl sm:inset-x-auto sm:bottom-4 sm:right-4 sm:h-auto sm:max-h-[80vh] sm:w-[26rem] sm:rounded-xl"} flex flex-col overflow-hidden border border-slate-600 bg-slate-950 p-4 text-sm text-slate-300 shadow-xl print:hidden`}>
    <p className="text-[11px] uppercase tracking-widest text-sky-300">{`Guided tour · Step ${step} of ${GUIDED_DEMO_STEPS}`}</p>
    <h2 id="guided-demo-title" ref={heading} tabIndex={-1} className="mt-1 text-base font-medium text-slate-100">{STEP_TITLES[step]}</h2>
    <div className="mt-2 min-h-0 flex-1 space-y-2 overflow-y-auto text-xs leading-5">
      {!demo ? <p role="alert" className="text-amber-200">{error}</p>
        : step === 1 ? <MaterialStep demo={demo} />
        : step === 2 ? <RunStep engine={engine} engineChecking={engineChecking} />
        : step === 3 ? <CompareStep demo={demo} />
        : <ScorecardStep scorecard={scorecard} />}
    </div>
    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-700 pt-3">
      <button type="button" className={button} onClick={back} disabled={step === 1}>Back</button>
      {step < GUIDED_DEMO_STEPS ? <button type="button" className={button} onClick={next}>Next</button> : <button type="button" className={button} onClick={finish}>Finish</button>}
      <button type="button" className={button} onClick={exit} aria-keyshortcuts="Escape">Exit (Esc)</button>
      {(previous || restored) && <button type="button" className={button} disabled={!previous} onClick={() => { restorePrevious(); setRestored(true); }}>Restore my previous material</button>}
    </div>
    {restored && !previous && <p role="status" className="mt-2 text-xs text-slate-400">Your previous material and process values were restored.</p>}
  </section>;
}

function Cite({ demo }: { demo: DemoCase }) {
  return <p className="text-slate-400">Source: {demo.source}. DOI <span className="font-mono">{demo.doi}</span>. Case {demo.id}.</p>;
}

function MaterialStep({ demo }: { demo: DemoCase }) {
  const lpbf = useMaterialSpecimenStore(s => s.activeSpecimen.lpbf);
  const name = useMaterialSpecimenStore(s => s.activeSpecimen.name);
  return <>
    <p>The tour loaded the {demo.material} preset and set the process values of the published NIST case: {formatExactNumber(demo.laserPower_W)} W, {formatExactNumber(demo.scanSpeed_mm_s)} mm/s, beam diameter {formatExactNumber(demo.beamDiameter_um)} µm (D4σ), preheat {formatExactNumber(demo.preheatTemp_C)} °C. Measured: width {formatExactNumber(demo.publishedWidth_um)} ± {formatExactNumber(demo.widthStdDev_um)} µm, depth {formatExactNumber(demo.publishedDepth_um)} ± {formatExactNumber(demo.depthStdDev_um)} µm (n = {demo.measurementCount}).</p>
    <p>Shared material now: <strong className="text-slate-100">{name}</strong> · {formatExactNumber(lpbf.laserPower_W)} W · {formatExactNumber(lpbf.scanSpeed_mms)} mm/s · beam {formatExactNumber(lpbf.beamDiameter_um)} µm · preheat {formatExactNumber(lpbf.preheatTemp_C)} °C.</p>
    <p className="text-amber-200">The NIST case is a bare plate with no powder layer. The preset's layer {formatExactNumber(lpbf.layer_um)} µm and hatch {formatExactNumber(lpbf.hatch_um)} µm remain in the process vector and are not part of the case.</p>
    <p className="text-amber-200">NIST reports the beam as D4σ; the solver takes a 1/e² diameter. The two are equal only for an ideal Gaussian beam, which is not verified for this beam.</p>
    <Cite demo={demo} />
  </>;
}

function jobLine(job: SimulationJob | undefined, error: string): string {
  if (!job) return "No job in this session.";
  return `Job ${job.id.slice(0, 8)}: ${job.status}${job.error ? ` (${job.error})` : ""}${error ? `. ${error}` : ""}`;
}

function RunStep({ engine, engineChecking }: { engine: PythonEngineStatus | null; engineChecking: boolean }) {
  const job = useLpbfEngineeringStore(s => s.job);
  const [mode, setMode] = useEngineeringField("mode");
  const error = useLpbfEngineeringStore(s => s.error);
  const engineText = IS_STATIC_DEMO ? "Engine: static snapshot (no engine)." : engineChecking ? "Checking the Python engine…" : engine?.online ? "Python engine: available." : "Python engine: unavailable. A run cannot start until it is reachable; no result is faked.";
  return <>
    <p><strong className="text-slate-100">Quick Screening</strong> is preselected on the Thermal Simulation stage below. Press Run simulation yourself. The tour never submits a run.</p>
    <p>Selected mode: <span className="font-mono text-slate-100">{mode}</span>. <button type="button" className="underline" disabled={mode === "screening"} onClick={() => setMode("screening")}>Preselect Screening</button></p>
    <p className="text-amber-200">A new run replaces the current result{job ? ` (currently ${job.status})` : ""}.</p>
    <p role="status" aria-live="polite">{jobLine(job, error)}</p>
    <p role="status" className={engine?.online ? "text-slate-300" : "text-amber-200"}>{engineText}</p>
  </>;
}

function CompareStep({ demo }: { demo: DemoCase }) {
  const job = useLpbfEngineeringStore(s => s.job);
  const researchHosts = useLpbfResearchModelStore(s => s.hosts);
  const comparison = compareToMeasurement(demo, job);
  const researchDepth = comparison.available && comparison.screeningOnly
    ? researchDepthForCase(demo, researchHosts["melt-pool"]) ?? researchDepthForCase(demo, researchHosts["build-job"])
    : null;
  return <>
    <p className="font-medium text-slate-100">One published case. A comparison, not validation.</p>
    {"rows" in comparison ? <>
      {comparison.screeningOnly && <p className="text-amber-200">Screening is an analytical estimate, not a closed liquidus isotherm. Differences below are descriptive, not a validation score.</p>}
      <div className="overflow-x-auto"><table className="w-full text-left text-[11px]">
        <caption className={comparison.screeningOnly ? "mb-2 text-left font-medium text-amber-200" : "sr-only"}>{comparison.screeningOnly ? "Screening only, comparison not validation" : "Predicted versus measured melt pool, NIST case 0"}</caption>
        <thead><tr><th scope="col">Quantity</th><th scope="col">{comparison.screeningOnly ? "Screening" : "Predicted"} (µm)</th><th scope="col">Measured ± SD (µm)</th><th scope="col">Diff (µm)</th><th scope="col">Diff (%)</th>{!comparison.screeningOnly && <th scope="col">Within 1 SD</th>}</tr></thead>
        <tbody>{comparison.rows.map(row => <tr key={row.quantity}><th scope="row">{row.quantity}</th><td>{fmt1(row.predicted_um)}</td><td>{fmt1(row.measured_um)} ± {fmt1(row.sd_um)}</td><td>{fmt1(row.diff_um)}</td><td>{fmt1(row.diff_pct)}</td>{!comparison.screeningOnly && <td>{row.withinOneSd ? "yes" : "no"}</td>}</tr>)}</tbody>
      </table></div>
      {researchDepth && <div className="rounded border border-amber-500/30 p-2 text-amber-200">
        <p className="font-medium">P8 conditional linked melt-depth scenario (research): {fmt1(researchDepth.depth.value as number)} {researchDepth.depth.unit}</p>
        <p>Independent quasi-steady cavity/conduction hypothesis for the same incident power, scan speed, Gaussian 1/e² diameter and preheat, separate from the Screening estimate. It does not resolve surface motion or melt flow. Linked depth is a liquidus envelope below the original surface, not vapour-cavity depth. Not experimentally validated; research diagnostic/model only.</p>
        {researchDepth.atOrBelowOnset && <p>P8 is at or below its own modeled onset. Any available linked depth is its Gaussian conduction envelope, not a keyhole-depth result.</p>}
        <p>Model <span className="font-mono">{researchDepth.module.modelId}</span>. {researchDepth.module.uiSentence} {researchDepth.depth.uiSentence}</p>
      </div>}
      {comparison.surface.bareTrack
        ? <p>The run used a bare plate, like the measurement.</p>
        : <p className="text-amber-200">Caveat: the run used a powder layer{comparison.surface.layer_um !== null ? ` (layer ${fmt1(comparison.surface.layer_um)} µm` : ""}{comparison.surface.hatch_um !== null ? `, hatch ${fmt1(comparison.surface.hatch_um)} µm)` : comparison.surface.layer_um !== null ? ")" : ""}, while the NIST measurement is a single track on a bare plate. The two are not the same configuration.</p>}
      <p>Measured: mean of n = {comparison.n} cross-sections; SD is the published spread, not a model uncertainty. Diff = predicted - measured.</p>
      <p>Solver <span className="font-mono">{comparison.solverId}</span> · implementation hash <span className="font-mono break-all">{comparison.implementationHash ?? "not reported"}</span></p>
    </> : <>
      <p role="status" className="text-amber-200">Comparison unavailable. {comparison.reason}</p>
      <p className="text-slate-400">Screening runs currently do not report a melt-pool extent status, so this comparison is expected to stay unavailable until the solver reports one. The tour shows no numbers in that case.</p>
    </>}
    <Cite demo={demo} />
  </>;
}

function ScorecardStep({ scorecard }: { scorecard: LpbfCalibrationScorecardDocument | null }) {
  return <>
    <p role="status">{scorecardStatementFor("Inconel 718", scorecard)}</p>
    <p className="text-slate-400">The scorecard is open behind this panel. Restore my previous material is available here until you finish or exit; a page reload discards the saved snapshot.</p>
  </>;
}
