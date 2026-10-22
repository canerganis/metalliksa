import React, { useState } from "react";
import { AlertTriangle, Download, FileUp } from "lucide-react";
import {
  LPBF_EXPERIMENT_PLAN_LABEL,
  ExperimentPlanError,
  machineFitCommand,
  measurementTemplateCsv,
  parseExperimentPlan,
  plateLayoutCsv,
  printPlanCsv,
  type ExperimentPlanDocument,
} from "../data/lpbfExperimentPlan";

// Read-only view of a plan.json written by python/tools/lpbf_next_experiment.py. The ranking and the plate layout are
// computed in Python; this panel loads the file in the browser (no network request, no worker call), shows it and
// writes CSV downloads. Screening: experiment proposal; not a print recommendation.

const MAX_PLAN_FILE_BYTES = 2_000_000;
const PLAN_COMMAND =
  'python -B python/tools/lpbf_next_experiment.py plan --material "316L Stainless Steel" --power 100 400 --speed 400 1600 --spots 70,100 --layer-um 40 --preheat-c 80 --n 12 --seed 1 --plate-x-mm 120 --plate-y-mm 120 --out-dir .runtime/next-experiment/run1';

const fmt = (v: number | null, digits = 3): string => (v === null ? "n/a" : v.toFixed(digits));

/** SVG of the plate: a to-scale outline with one line per track (read from the plan, nothing recomputed). */
export function PlateSvg({ plan }: { plan: ExperimentPlanDocument }) {
  const { x_mm: X, y_mm: Y } = plan.plate;
  return (
    <svg
      viewBox={`0 0 ${X} ${Y}`} role="img" data-testid="plate-svg" className="w-full max-w-2xl rounded border border-slate-700 bg-slate-950"
      aria-label={`Plate layout, ${X} by ${Y} millimetres, ${plan.points.length} proposed tracks`}
    >
      <rect x={0} y={0} width={X} height={Y} fill="none" stroke="#64748b" strokeWidth={0.4} />
      {plan.points.map(p => (
        <g key={p.trackId}>
          <line x1={p.layout.x_start_mm} y1={p.layout.y_mm} x2={p.layout.x_end_mm} y2={p.layout.y_mm} stroke="#38bdf8" strokeWidth={0.9} />
          <text x={p.layout.x_start_mm} y={p.layout.y_mm - 1.1} fontSize={2.4} fill="#e2e8f0">{p.trackId} #{p.layout.printOrder}</text>
        </g>
      ))}
    </svg>
  );
}

export function downloadText(filename: string, text: string): void {
  const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function ExperimentPlanView({ plan }: { plan: ExperimentPlanDocument }) {
  const rows = [...plan.points].sort((a, b) => a.rank - b.rank);
  const fitCommand = machineFitCommand(plan);
  return (
    <div className="space-y-4" data-testid="plan-view">
      <p className="text-sm text-slate-300">
        <span className="font-semibold text-slate-100">{plan.material}</span>, {plan.points.length} proposed tracks. Plate {plan.plate.x_mm} x {plan.plate.y_mm} mm, pitch {plan.plate.pitch_mm} mm, track length {plan.plate.trackLength_mm} mm. Configuration sha256 <code className="break-all text-xs">{plan.configSha256}</code>.
      </p>
      <p className="text-xs text-slate-400" data-testid="plan-calibration">
        {plan.calibration.available
          ? `Calibration artefact ${plan.calibration.calibrationId ?? ""} (content sha256 ${plan.calibration.contentSha256}).`
          : `Calibration artefact not used: ${plan.calibration.reason}.`}{" "}
        Calibration interval width: {plan.intervalWidth.lnHiOverLo === null ? "not available (null)" : `ln(hi/lo) = ${fmt(plan.intervalWidth.lnHiOverLo)}`} - {plan.intervalWidth.note}
      </p>
      {plan.candidates?.trainingNote ? (
        <p className="text-xs text-amber-200" role="status" data-testid="plan-training-note">{plan.candidates.trainingNote}</p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {([
          ["print_plan.csv", () => printPlanCsv(plan)],
          ["plate_layout.csv", () => plateLayoutCsv(plan)],
          ["measurement_template.csv", () => measurementTemplateCsv(plan)],
        ] as const).map(([name, make]) => (
          <button
            key={name} type="button" onClick={() => downloadText(name, make())}
            className="inline-flex items-center gap-2 rounded border border-slate-600 px-3 py-1.5 text-sm text-slate-100 hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            Download {name}
          </button>
        ))}
      </div>
      <div className="max-h-96 overflow-auto" tabIndex={0} role="region" aria-label="Proposed tracks (scrollable)">
        <table className="w-full whitespace-nowrap text-xs text-slate-300 [&_td]:pr-3 [&_th]:pr-3 [&_th]:text-left" data-testid="plan-table">
          <caption className="sr-only">Proposed single tracks ranked by information score</caption>
          <thead>
            <tr>
              <th scope="col">Rank</th><th scope="col">Track</th><th scope="col">Print order</th><th scope="col">Power (W)</th><th scope="col">Speed (mm/s)</th>
              <th scope="col">Spot (µm)</th><th scope="col">Regime class</th><th scope="col">Score</th><th scope="col">Kernel disagreement</th>
              <th scope="col">Interval width</th><th scope="col">Coverage</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(p => (
              <tr key={p.trackId}>
                <td>{p.rank}</td><td>{p.trackId}</td><td>{p.layout.printOrder}</td><td>{p.power_W}</td><td>{p.speed_mm_s}</td>
                <td>{p.beamDiameter_um}</td><td>{p.regimeClass}</td><td>{fmt(p.score.total)}</td>
                <td>{fmt(p.score.disagreement.raw)} ({p.score.disagreement.nResolvedKernels} kernels)</td>
                <td>{p.score.intervalWidth.lnHiOverLo === null ? "n/a (no enabled cell)" : fmt(p.score.intervalWidth.lnHiOverLo)}</td>
                <td>{fmt(p.score.coverage.value)}{p.score.coverage.classUnderCovered ? " (class under-covered)" : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <PlateSvg plan={plan} />
      <section aria-label="Command line steps" className="space-y-2">
        <h4 className="text-sm font-semibold text-slate-100">After printing and measuring</h4>
        <p className="text-xs text-slate-400">
          Fill width_um and depth_um in measurement_template.csv (leave a cell blank to exclude a track; nothing is imputed), then run these commands. Imported rows are labelled Measured (user-supplied) and stay your own data; the scorecard run is private and writes only to the directory you give.
        </p>
        <pre className="overflow-x-auto rounded bg-slate-950 p-3 text-xs text-slate-200" tabIndex={0} aria-label="Command line steps for the import and the private scorecard run" data-testid="plan-commands">{plan.commands.join("\n")}</pre>
        {fitCommand ? (
          <div className="space-y-2" data-testid="plan-machine-calibration">
            <h5 className="text-sm font-semibold text-slate-100">Machine calibration (user data)</h5>
            <p className="text-xs text-slate-400">
              After the import, this fits an empirical machine offset to your own tracks. It stays on this computer and is screening only, not validation. Fill the method columns in the template ({(plan.methodColumns ?? []).join(", ") || "none listed"}) on every track, otherwise a served value is shown as screening only.
            </p>
            {(plan.warnings ?? []).length > 0 ? (
              <ul className="list-disc pl-5 text-xs text-amber-200" role="status" data-testid="plan-machine-warnings">{(plan.warnings ?? []).map(w => <li key={w}>{w}</li>)}</ul>
            ) : null}
            <pre className="overflow-x-auto rounded bg-slate-950 p-3 text-xs text-slate-200" tabIndex={0} aria-label="Command line step for the machine calibration fit" data-testid="plan-fit-command">{fitCommand}</pre>
          </div>
        ) : null}
      </section>
      <p className="text-xs text-slate-400">{plan.limits}.</p>
    </div>
  );
}

/** Third tab of the Process Parameter Search lab: load a plan.json, show it, download CSV. */
export const LpbfExperimentPlanPanel: React.FC = () => {
  const [plan, setPlan] = useState<ExperimentPlanDocument | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const onFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    if (file.size > MAX_PLAN_FILE_BYTES) {
      setPlan(null);
      setError(`lpbf experiment plan rejected: file is larger than ${MAX_PLAN_FILE_BYTES} bytes`);
      return;
    }
    try {
      const checked = parseExperimentPlan(await file.text());
      setPlan(checked);
      setError(null);
    } catch (e) {
      setPlan(null);
      setError(e instanceof ExperimentPlanError ? e.message : "lpbf experiment plan rejected: the file could not be read");
    }
  };

  return (
    <section className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4" aria-label="Plan experiments">
      <header className="space-y-1">
        <h3 className="text-base font-semibold text-slate-100">Plan experiments</h3>
        <p className="text-sm text-amber-200" data-testid="plan-label">{LPBF_EXPERIMENT_PLAN_LABEL}</p>
        <p className="text-xs text-slate-400">
          Candidates are ranked by disagreement between the three frozen screening kernels and by how far they sit from the existing training data. The calibration interval width is reported for context only: it is constant per material (null when no calibrated cell is enabled) and does not change the order. The plan is computed on the command line; this panel only loads and displays it. It does not run the solver and makes no network or worker call.
        </p>
      </header>
      <div className="space-y-2">
        <p className="text-xs text-slate-400">Create a plan (no default plate size: you must give one):</p>
        <pre className="overflow-x-auto rounded bg-slate-950 p-3 text-xs text-slate-200" tabIndex={0} aria-label="Command that creates a plan" data-testid="make-plan-command">{PLAN_COMMAND}</pre>
        <label className="inline-flex cursor-pointer items-center gap-2 rounded border border-slate-600 px-3 py-1.5 text-sm text-slate-100 focus-within:ring-2 focus-within:ring-sky-400 hover:bg-slate-800">
          <FileUp className="h-4 w-4" aria-hidden="true" />
          <span>Load plan.json</span>
          <input type="file" accept=".json,application/json" onChange={onFile} className="sr-only" data-testid="plan-file-input" />
        </label>
        {fileName && <span className="ml-2 text-xs text-slate-400">{fileName}</span>}
      </div>
      {error && (
        <div role="alert" className="flex items-start gap-2 rounded border border-rose-500/50 bg-rose-950/40 p-3 text-sm text-rose-100" data-testid="plan-error">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
      {plan ? <ExperimentPlanView plan={plan} /> : !error && <p className="text-sm text-slate-400" data-testid="no-plan">No plan loaded.</p>}
    </section>
  );
};
