import React, { useEffect, useState } from "react";
import { DepthBiasNotice } from "../DepthBiasNotice";
import { pythonComputationService, type LPBFCalibratedMeltpoolResult } from "../../services/pythonComputationService";
import {
  COMMITTED_CALIBRATION_ARTEFACT,
  enabledCellsFor,
  type CalibrationArtefactSummary,
} from "../../data/lpbfCalibrationArtefact";
import {
  MACHINE_BAND_SENTENCE, MACHINE_OFFSET_SENTENCE, MACHINE_PRIVACY_SENTENCE, MACHINE_SECTION_TITLE, MACHINE_VERDICT_SENTENCE,
  isMachineCalibratedBadge, machineEvidenceBadge, methodFieldText,
  type MachineArtefactSummary, type MachineCalibratedBlock, type MachineCalibrationStatus,
} from "../../data/lpbfMachineCalibration";
import { useMachineCalibrationStore } from "../../store/useMachineCalibrationStore";
import { refusedBlockFor, useMachineDepth, type MachineSolve } from "./useMachineDepth";

// Opt-in calibrated mode for the Melt Pool lab. SCREENING ONLY, NOT VALIDATION: effective absorptivity fitted to
// published tracks outside the frozen kernels, served only for cells that passed the held-out gate.
//
// - The control is NOT rendered (not greyed out) while no cell is enabled for the chosen kernel and alloy: a permanently
//   disabled control would itself be a claim. The scorecard link stays.
// - Default OFF, never persisted. OFF issues no request at all; the lab's own screening request path is untouched.
// - When only one quantity is served, nothing is derived from a mix of calibrated and screening values
//   (no depth/width, length/width, aspect ratio): those cells show a dash with the reason.

export const SCORECARD_HASH = "#/lpbf-calibration-scorecard";

export type CalibratedRequest = Parameters<typeof pythonComputationService.solveLPBFCalibratedMeltpool>[0];

/** The only rule that triggers a calibrated request: the user opted in AND an enabled cell exists. */
export function shouldRequestCalibrated(optedIn: boolean, enabledCellCount: number): boolean {
  return optedIn && enabledCellCount > 0;
}

function fmt(value: number | null | undefined, digits = 1): string {
  return value === null || value === undefined ? "—" : value.toFixed(digits);
}

function Dash({ reason }: { reason: string }) {
  return <span title={reason}>— <span className="text-[10px] text-slate-400">({reason})</span></span>;
}

export function CalibratedResultView({ result }: { result: LPBFCalibratedMeltpoolResult }) {
  const c = result.calibrated;
  const cal = result.calibration;
  const dim = result.outsideTrainingEnvelope ? "opacity-50" : "";
  const bothServed = c.width_um !== null && c.depth_um !== null;
  return (
    <div data-testid="calibrated-result" className="space-y-2 text-xs">
      <p className="rounded-lg border border-sky-500/40 bg-sky-500/10 p-2 text-[11px] text-sky-100">
        <span data-testid="calibrated-badge" className="mr-1.5 rounded border border-sky-400/60 px-1.5 py-0.5 font-bold text-sky-200">Screening only</span>
        Calibrated mode · Screening only (not validation).
        {cal ? <> Effective absorptivity fitted on: <span data-testid="fitted-on">{cal.fittedOn.join("; ")}</span>.</> : null}
        {cal && Object.keys(cal.heldOutScore).length ? <> Held-out score: {Object.entries(cal.heldOutScore).map(([q, text]) => `${q}: ${text}`).join(" | ")}.</> : null}
        {" "}<a className="underline" href={SCORECARD_HASH}>Open scorecard</a>
      </p>
      {!c.available ? <p data-testid="calibrated-unavailable" className="text-amber-300">Calibrated values are not available: {c.reason ?? "no enabled cell"}.</p> : (
        <div className={`grid grid-cols-2 gap-2 rounded-xl border border-slate-800 bg-[#050810] p-2 ${dim}`}>
          <div>
            <span className="block text-[10px] text-slate-400">Calibrated width (W)</span>
            <strong data-testid="cal-width" className="text-sm text-emerald-300">{c.width_um !== null ? `${fmt(c.width_um)} µm` : <Dash reason={c.widthReason ?? "not served"} />}</strong>
            {c.width_pi90_um ? <span data-testid="cal-width-pi90" className="block text-[10px] text-slate-400">PI 90 %: [{fmt(c.width_pi90_um[0], 0)}, {fmt(c.width_pi90_um[1], 0)}] µm{c.width_pi90_notInformative ? <strong data-testid="cal-width-not-informative" className="ml-1 text-amber-300">(not informative: wider than ×2.5)</strong> : null}</span> : null}
          </div>
          <div>
            <span className="block text-[10px] text-slate-400">Calibrated depth (D)</span>
            <strong data-testid="cal-depth" className="text-sm text-amber-300">{c.depth_um !== null ? `${fmt(c.depth_um)} µm` : <Dash reason={c.depthReason ?? "not served"} />}</strong>
            {c.depth_pi90_um ? <span data-testid="cal-depth-pi90" className="block text-[10px] text-slate-400">PI 90 %: [{fmt(c.depth_pi90_um[0], 0)}, {fmt(c.depth_pi90_um[1], 0)}] µm{c.depth_pi90_notInformative ? <strong data-testid="cal-depth-not-informative" className="ml-1 text-amber-300">(not informative: wider than ×2.5)</strong> : null}</span> : null}
          </div>
          <div data-testid="cal-ratio">
            <span className="block text-[10px] text-slate-400">Depth-to-width (D/W)</span>
            {bothServed && c.depthOverWidth !== null && c.depthOverWidth !== undefined
              ? <strong className="text-sm text-white">{fmt(c.depthOverWidth, 2)}</strong>
              : <Dash reason={c.depthOverWidthReason ?? "needs both quantities served"} />}
          </div>
          <div data-testid="cal-aspect">
            <span className="block text-[10px] text-slate-400">Length-to-width (L/W)</span>
            <Dash reason="no calibrated length; never mixed with calibrated W" />
          </div>
        </div>
      )}
      {c.available ? <p data-testid="cal-regime" className="text-[11px] text-slate-400">Regime label (screening, at the default absorptivity, unchanged): <strong className="text-slate-200">{c.regimeLabel ?? "—"}</strong></p> : null}
      {c.available ? <DepthBiasNotice geometry={result.screening?.meltPoolGeometry} material={result.screening?.material} heatSource={result.screening?.processParameters?.heatSource} className="mt-1" /> : null}
      {result.outsideTrainingEnvelope ? <p data-testid="envelope-warning" className="text-amber-300">Outside the training envelope, calibrated numbers greyed: {result.envelopeNotes.join("; ")}.</p> : null}
    </div>
  );
}

interface PublishedPanelProps {
  readonly heatSource: "goldak" | "eagar-tsai" | "rosenthal";
  readonly material: string;
  readonly request: Omit<CalibratedRequest, "heatSource" | "material">;
  readonly summary?: CalibrationArtefactSummary | null;
  /** injected in tests; defaults to the shared service */
  readonly solve?: (payload: CalibratedRequest, signal?: AbortSignal) => Promise<LPBFCalibratedMeltpoolResult>;
}

function PublishedCalibratedMeltpoolPanel({
  heatSource, material, request, summary = COMMITTED_CALIBRATION_ARTEFACT,
  solve = (p, s) => pythonComputationService.solveLPBFCalibratedMeltpool(p, s),
}: PublishedPanelProps) {
  const cells = enabledCellsFor(summary, heatSource, material);
  const [optedIn, setOptedIn] = useState(false); // default OFF; never persisted beyond this component's lifetime
  const [result, setResult] = useState<LPBFCalibratedMeltpoolResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestKey = JSON.stringify([heatSource, material, request]);
  const active = shouldRequestCalibrated(optedIn, cells.length);

  useEffect(() => {
    if (!active) { setResult(null); setError(null); return; }
    const controller = new AbortController();
    setError(null);
    solve({ ...request, heatSource, material }, controller.signal)
      .then((r) => { if (!controller.signal.aborted) setResult(r); })
      .catch((e: unknown) => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "Calibrated request failed."); });
    return () => controller.abort();
  }, [active, requestKey]);

  if (cells.length === 0) {
    return (
      <p data-testid="calibration-link-only" className="text-[11px] text-slate-400">
        No calibrated mode is offered for this kernel and alloy: no cell passes the held-out gate. <a className="underline" href={SCORECARD_HASH}>Calibration scorecard</a>
      </p>
    );
  }
  return (
    <section data-testid="calibrated-panel" aria-label="Calibrated mode" className="space-y-2 rounded-xl border border-[#162032] bg-[#090e18] p-3">
      <label className="flex items-center gap-2 text-xs font-semibold text-white">
        <input data-testid="calibrated-toggle" type="checkbox" checked={optedIn} onChange={(e) => setOptedIn(e.target.checked)} />
        Calibrated mode (opt-in)
      </label>
      {optedIn && error ? <p role="alert" className="text-xs text-rose-300">{error}</p> : null}
      {optedIn && result ? <CalibratedResultView result={result} /> : null}
      {!optedIn ? <p className="text-[11px] text-slate-400">Off: only the unchanged screening result is shown. <a className="underline" href={SCORECARD_HASH}>Calibration scorecard</a></p> : null}
    </section>
  );
}

// ---- Machine calibration (user data) -------------------------------------------------------------------------------
// A second, independent section. Hidden (not greyed out) while no ready artefact exists for this alloy. Nothing is
// requested until the user selects an artefact; the selection is session-only. Only Rosenthal depth can be served, so
// every other cell shows why it is not (from the status document, no solver call). Screening only unless the backend
// itself returned the calibrated kind with the scope text and no missing method field (see machineEvidenceBadge).

// The machine factor was fitted on the flat-plate basis and the screening value on this line is computed flat-plate on the CPU,
// whichever absorption model the lab shows. Other absorption models are deliberately not forwarded.
export const MACHINE_SCREENING_DEPTH_LABEL = "Screening depth, unchanged (flat-plate basis used by the machine fit)";

export function MachineEvidenceBadge({ block }: { block: Pick<MachineCalibratedBlock, "available" | "evidenceKind" | "evidenceScope" | "missingMethodFields" | "experimentalValidation"> }) {
  const text = machineEvidenceBadge(block);
  const calibrated = isMachineCalibratedBadge(text);
  return (
    <span data-testid="machine-badge" className={`mr-1.5 rounded border px-1.5 py-0.5 font-bold ${calibrated ? "border-emerald-400/60 text-emerald-200" : "border-sky-400/60 text-sky-200"}`}>{text}</span>
  );
}

export function MachineResultView({ artefact, kernel, block, screeningDepth }: {
  artefact: MachineArtefactSummary; kernel: string; block: MachineCalibratedBlock; screeningDepth: number | null;
}) {
  const served = block.available && block.depth_um !== null;
  return (
    <div data-testid="machine-result" className="space-y-1.5 text-xs">
      <p className="rounded-lg border border-sky-500/40 bg-sky-500/10 p-2 text-[11px] text-sky-100">
        <MachineEvidenceBadge block={block} />
        Machine calibration · {artefact.machineCalibrationId} · {artefact.nTracks} tracks · {artefact.userSourceId}. Not validation.
      </p>
      {served ? (
        <div className="rounded-xl border border-slate-800 bg-[#050810] p-2">
          <span className="block text-[10px] text-slate-400">Machine depth (D), {kernel}</span>
          <strong data-testid="machine-depth" className="text-sm text-amber-300">{block.depth_um!.toFixed(1)} µm</strong>
          {block.factor !== undefined ? <span data-testid="machine-factor" className="block text-[10px] text-slate-300">Empirical machine offset: factor {block.factor.toFixed(3)}</span> : null}
          {block.depthBand_um ? (
            <span data-testid="machine-band" className="block text-[10px] text-slate-400">
              80 % band: [{block.depthBand_um[0].toFixed(0)}, {block.depthBand_um[1].toFixed(0)}] µm (not a tolerance)
              {block.bandNotInformative ? <strong className="ml-1 text-amber-300">(not informative: wider than ×2.5)</strong> : null}
            </span>
          ) : null}
          {screeningDepth !== null ? <span data-testid="machine-screening" className="block text-[10px] text-slate-400">{MACHINE_SCREENING_DEPTH_LABEL}: {screeningDepth.toFixed(1)} µm</span> : null}
          <span className="block text-[10px] text-slate-500">{MACHINE_BAND_SENTENCE}</span>
        </div>
      ) : (
        <div data-testid="machine-refused" className="rounded-xl border border-amber-500/30 bg-[#050810] p-2 text-[11px] text-amber-200">
          <strong>Machine calibration not served for this cell{block.status ? ` (${block.status})` : ""}.</strong>
          <ul className="mt-1 list-disc pl-4">
            {(block.reasonText.length ? block.reasonText : ["no reason reported"]).map((r) => <li key={r}>{r}</li>)}
          </ul>
          {screeningDepth !== null ? <span className="block text-[10px] text-slate-400">{MACHINE_SCREENING_DEPTH_LABEL}: {screeningDepth.toFixed(1)} µm</span> : null}
        </div>
      )}
      {block.missingMethodFields.length > 0 ? (
        <p data-testid="machine-missing-fields" className="text-[11px] text-amber-300">
          Shown as screening only because these method fields are missing on some of your tracks: {methodFieldText(block.missingMethodFields)}.
        </p>
      ) : null}
      {block.userTrackRangeNotes && block.userTrackRangeNotes.length > 0 ? <p className="text-[11px] text-amber-300">Outside the range of your tracks: {block.userTrackRangeNotes.join("; ")}.</p> : null}
      <p className="text-[10px] text-slate-500">{MACHINE_OFFSET_SENTENCE} {MACHINE_VERDICT_SENTENCE}</p>
      <p data-testid="machine-privacy" className="text-[10px] text-slate-500">{MACHINE_PRIVACY_SENTENCE}</p>
    </div>
  );
}

export interface MachineCalibrationSectionProps {
  readonly heatSource: "goldak" | "eagar-tsai" | "rosenthal";
  readonly material: string;
  readonly request: Omit<CalibratedRequest, "heatSource" | "material">;
  /** injected in tests; when undefined the status is fetched once from the server */
  readonly status?: MachineCalibrationStatus | null;
  readonly solve?: MachineSolve;
  /** test seam: overrides the session selection */
  readonly selectedId?: string | null;
}

export function MachineCalibrationSection({
  heatSource, material, request, status, solve, selectedId: injectedId,
}: MachineCalibrationSectionProps) {
  const storeSelected = useMachineCalibrationStore((s) => s.selectedId);
  const selectedId = injectedId !== undefined ? injectedId : storeSelected;
  const select = useMachineCalibrationStore((s) => s.select);
  const { artefacts, artefact, cell, wantsSolve, result, error } = useMachineDepth({ heatSource, material, request, status, solve, selectedId });
  if (artefacts.length === 0) return null; // hidden, never greyed out
  return (
    <section data-testid="machine-calibration-section" aria-label={MACHINE_SECTION_TITLE} className="space-y-2 rounded-xl border border-[#162032] bg-[#090e18] p-3">
      <h4 className="text-xs font-semibold text-white">{MACHINE_SECTION_TITLE}</h4>
      <label className="flex flex-wrap items-center gap-2 text-xs text-slate-200">
        Machine calibration
        <select data-testid="machine-select" className="rounded border border-slate-600 bg-slate-950 px-2 py-1 text-xs text-slate-100 focus-visible:outline-2 focus-visible:outline-sky-300"
          value={selectedId ?? ""} onChange={(e) => select(e.target.value === "" ? null : e.target.value)}>
          <option value="">None (screening only)</option>
          {artefacts.map((a) => <option key={a.machineCalibrationId} value={a.machineCalibrationId}>{a.machineCalibrationId} · {a.userSourceId} · {a.nTracks} tracks</option>)}
        </select>
      </label>
      {!artefact ? <p className="text-[11px] text-slate-400">Off: only the unchanged screening result is shown. {MACHINE_OFFSET_SENTENCE}</p> : null}
      {artefact && error ? <p role="alert" className="text-xs text-rose-300">{error}</p> : null}
      {artefact && !wantsSolve ? <MachineResultView artefact={artefact} kernel={heatSource} block={refusedBlockFor(cell)} screeningDepth={null} /> : null}
      {artefact && wantsSolve && result ? <MachineResultView artefact={artefact} kernel={heatSource} block={result.machineCalibrated} screeningDepth={result.screening?.meltPoolGeometry?.depth_um ?? null} /> : null}
    </section>
  );
}

export interface CalibratedMeltpoolPanelProps extends PublishedPanelProps {
  /** injected in tests; undefined means "fetch the status once" */
  readonly machineStatus?: MachineCalibrationStatus | null;
  readonly solveMachine?: MachineSolve;
}

export function CalibratedMeltpoolPanel({ machineStatus, solveMachine, ...rest }: CalibratedMeltpoolPanelProps) {
  return (
    <>
      <PublishedCalibratedMeltpoolPanel {...rest} />
      <MachineCalibrationSection heatSource={rest.heatSource} material={rest.material} request={rest.request} status={machineStatus} solve={solveMachine} />
    </>
  );
}
