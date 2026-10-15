import React, { useMemo, useState } from "react";
import { FileSearch } from "lucide-react";
import {
  absorptivitySensitivityCells,
  type ComparisonErrorStats,
  type ComparisonRow,
  type LpbfDatasetComparisonDocument,
} from "../../data/lpbfDatasetComparison";
import { SpentDatasetPanel } from "./SpentDatasetPanel";

// Read-only view of the Python-generated record docs/LPBF_DATASET_COMPARISON_2026-10-05.view.json.
// Every number below is read from that JSON: no physics and no statistics are computed here.
// The only derived display facts are point counts of what is plotted and axis scales.

type SlotProps = { children: React.ReactNode; className?: string };
const Card = ({ children, className = "" }: SlotProps) => <section className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>{children}</section>;
const CardHeader = ({ children, className = "" }: SlotProps) => <header className={`border-b border-slate-100 bg-slate-50 p-4 ${className}`}>{children}</header>;
const CardContent = ({ children, className = "" }: SlotProps) => <div className={`p-4 ${className}`}>{children}</div>;
const CardTitle = ({ children, className = "" }: SlotProps) => <h2 className={`font-semibold text-slate-800 ${className}`}>{children}</h2>;

// Darkest shades: white chip text on these is >= 4.5:1 and they read on a light card as text too.
export const REGIME_COLORS = ["#1d4ed8", "#b45309", "#b91c1c", "#6d28d9", "#0f766e"] as const;
const KERNEL_LABELS: Readonly<Record<string, string>> = {
  rosenthal: "Rosenthal",
  "eagar-tsai": "Eagar–Tsai v2",
  goldak: "Goldak v3",
};

/** One decimal place for every displayed error figure (the record carries more digits). */
export function fmt1(value: number): string {
  const text = value.toFixed(1);
  return text === "-0.0" ? "0.0" : text;
}

const DEPTH_REFERENCE_NOTE = /depth reference line/i;
const POWDER_LAYER_NOTE = "The screening kernels ignore the powder-layer thickness (identical predictions for 0/30/60 µm layers); any powder-layer trend is in the measurements only.";
const SENSITIVITY_SENTENCE = "Sensitivity, not a calibration: included row counts differ per column (only rows where the kernel resolves an extent are counted), and width and depth errors pull in opposite directions.";
const DEFAULT_LIMITS: readonly string[] = [
  "Rosenthal conduction rests on rows selected by its own output (extent resolved).",
  "Eagar–Tsai and Goldak keyhole depths are identical because both add the same Fabbro depth term (not independent evidence).",
  "No confidence intervals are computed.",
  "Replicate rows (same parameter set) are not independent.",
  "Balling-flagged rows are included in the pooled headline.",
];

export function doiHref(doi: string): string {
  return /^https?:\/\//.test(doi) ? doi : `https://doi.org/${doi}`;
}

type Metric = "width" | "depth";

interface ScatterPoint {
  readonly key: string;
  readonly x: number;
  readonly y: number;
  readonly color: string;
  readonly hollow: boolean;
  readonly square: boolean;
  readonly tip: string;
}

function ScatterPlot({ metric, points, axisMax }: { metric: Metric; points: readonly ScatterPoint[]; axisMax: number }) {
  const size = 340;
  const m = { l: 48, r: 14, t: 12, b: 40 };
  const w = size - m.l - m.r;
  const h = size - m.t - m.b;
  const sx = (v: number) => m.l + (v / axisMax) * w;
  const sy = (v: number) => m.t + h - (v / axisMax) * h;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * axisMax);
  const upper = Math.min(axisMax, axisMax / 1.3);
  const lower = axisMax * 0.7;
  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={`Predicted versus measured ${metric} scatter with 1:1 line and plus or minus 30 percent band`}
      className="w-full max-w-md"
    >
      <rect x={m.l} y={m.t} width={w} height={h} fill="var(--mk-paper)" stroke="var(--mk-chart-axis)" />
      {ticks.map((t) => (
        <g key={t}>
          <line x1={sx(t)} x2={sx(t)} y1={m.t} y2={m.t + h} stroke="var(--mk-chart-axis)" strokeOpacity="0.5" />
          <line x1={m.l} x2={m.l + w} y1={sy(t)} y2={sy(t)} stroke="var(--mk-chart-axis)" strokeOpacity="0.5" />
          <text x={sx(t)} y={m.t + h + 14} fontSize="9" textAnchor="middle" fill="var(--mk-text-dim)">{Math.round(t)}</text>
          <text x={m.l - 6} y={sy(t) + 3} fontSize="9" textAnchor="end" fill="var(--mk-text-dim)">{Math.round(t)}</text>
        </g>
      ))}
      {/* +30 % and -30 % guides: predicted = 1.3 x measured and 0.7 x measured */}
      <line data-guide="band-upper" x1={sx(0)} y1={sy(0)} x2={sx(upper)} y2={sy(axisMax)} stroke="var(--mk-text-dim)" strokeDasharray="4 3" />
      <line data-guide="band-lower" x1={sx(0)} y1={sy(0)} x2={sx(axisMax)} y2={sy(lower)} stroke="var(--mk-text-dim)" strokeDasharray="4 3" />
      <line data-guide="one-to-one" x1={sx(0)} y1={sy(0)} x2={sx(axisMax)} y2={sy(axisMax)} stroke="var(--mk-text-strong)" />
      {points.map((p) => {
        const common = p.hollow
          ? { fill: "none", stroke: p.color, strokeWidth: 1.6 }
          : { fill: p.color, stroke: p.color, strokeWidth: 1.6, fillOpacity: 0.85 };
        return (
          <g key={p.key} data-point={p.hollow ? "excluded" : "included"}>
            <title>{p.tip}</title>
            {p.square
              ? <rect x={sx(p.x) - 4} y={sy(p.y) - 4} width={8} height={8} {...common} />
              : <circle cx={sx(p.x)} cy={sy(p.y)} r={4.5} {...common} />}
          </g>
        );
      })}
      <text x={m.l + w / 2} y={size - 6} fontSize="10" textAnchor="middle" fill="var(--mk-text-strong)">{`measured ${metric} (µm)`}</text>
      <text x={12} y={m.t + h / 2} fontSize="10" textAnchor="middle" fill="var(--mk-text-strong)" transform={`rotate(-90 12 ${m.t + h / 2})`}>{`predicted ${metric} (µm)`}</text>
    </svg>
  );
}

/** The record stores within-band fractions in [0, 1]; the page shows them as whole percents. */
export function formatFraction(fraction: number): string {
  return `${Math.round(fraction * 1000) / 10}`;
}

function Interval({ ci }: { ci?: readonly [number, number] }) {
  return ci ? <span className="text-slate-500">{` (95 % CI ${fmt1(ci[0])}–${fmt1(ci[1])})`}</span> : null;
}

function StatLine({ label, cell }: { label: string; cell: ComparisonErrorStats | null }) {
  if (cell === null) {
    return (
      <div>
        <div className="text-xs font-medium text-slate-600">{label}</div>
        <p className="text-xs text-slate-500" data-empty-slot={label}>no included rows</p>
      </div>
    );
  }
  return (
    <div>
      <div className="text-xs font-medium text-slate-600">{label}</div>
      <dl className="grid grid-cols-2 gap-x-3 text-xs text-slate-700">
        <dt>bias</dt><dd>{`${fmt1(cell.bias_pct)} %`}<Interval ci={cell.bias_pct_ci95} /></dd>
        <dt>MAPE</dt><dd>{`${fmt1(cell.mape_pct)} %`}<Interval ci={cell.mape_pct_ci95} /></dd>
        <dt>RMSE</dt><dd>{`${fmt1(cell.rmse_um)} µm`}</dd>
        <dt>within ±30 %</dt><dd>{`${formatFraction(cell.within30pct)} %`}</dd>
        {typeof cell.withinFactor2 === "number" ? <><dt>within ×0.5–2</dt><dd>{`${formatFraction(cell.withinFactor2)} %`}</dd></> : null}
      </dl>
    </div>
  );
}

function pointsFor(
  rows: readonly ComparisonRow[],
  kernel: string,
  metric: Metric,
  regimeColor: (label: string) => string,
  datasetIndex: (id: string) => number,
): ScatterPoint[] {
  const out: ScatterPoint[] = [];
  for (const row of rows) {
    const prediction = row.predictions?.[kernel];
    if (!prediction) continue;
    const measured = row.measured[metric === "width" ? "width_um" : "depth_um"];
    const predicted = prediction[metric === "width" ? "width_um" : "depth_um"];
    if (typeof measured !== "number" || typeof predicted !== "number") continue;
    const hollow = !prediction.included;
    const base = `${row.dataset} ${row.rowId}: measured ${measured} µm, predicted ${predicted} µm, regime ${row.regime.label}`;
    const tip = hollow
      ? `${base}. Excluded, extentStatus ${prediction.extentStatus}${prediction.extentNote ? `: ${prediction.extentNote}` : ""}`
      : base;
    out.push({
      key: `${row.dataset}/${row.rowId}`,
      x: measured,
      y: predicted,
      color: regimeColor(row.regime.label),
      hollow,
      square: datasetIndex(row.dataset) % 2 === 1,
      tip,
    });
  }
  // Excluded (hollow) markers are drawn after the included ones so they stay visible.
  return [...out.filter((p) => !p.hollow), ...out.filter((p) => p.hollow)];
}

export function DatasetComparisonView({ document }: { document: LpbfDatasetComparisonDocument }) {
  const kernels = document.kernels;
  const regimeLabels = useMemo(
    () => Array.from(new Set(Object.values(document.summary).flatMap((byRegime) =>
      Object.keys(byRegime).filter((label) => label !== "all" && label !== "common")))),
    [document.summary],
  );
  const [kernel, setKernel] = useState<string>(kernels[0] ?? "");
  const [enabled, setEnabled] = useState<readonly string[]>(regimeLabels);

  const regimeColor = (label: string) => REGIME_COLORS[Math.max(0, regimeLabels.indexOf(label)) % REGIME_COLORS.length];
  const datasetIndex = (id: string) => document.datasets.findIndex((d) => d.id === id);
  const shownRows = document.rows.filter((r) => enabled.includes(r.regime.label));

  const widthPoints = pointsFor(shownRows, kernel, "width", regimeColor, datasetIndex);
  const depthPoints = pointsFor(shownRows, kernel, "depth", regimeColor, datasetIndex);
  const axisFor = (metric: Metric) => {
    // Scale only: common axis across all kernels so switching kernels does not rescale the plot.
    let max = 0;
    for (const row of document.rows) {
      const mv = row.measured[metric === "width" ? "width_um" : "depth_um"];
      if (typeof mv === "number") max = Math.max(max, mv);
      for (const prediction of Object.values(row.predictions ?? {})) {
        const pv = prediction[metric === "width" ? "width_um" : "depth_um"];
        if (typeof pv === "number") max = Math.max(max, pv);
      }
    }
    return Math.max(1, Math.ceil(max / 50) * 50);
  };

  const excludedRows = shownRows.filter((r) => {
    const prediction = r.predictions?.[kernel];
    return prediction ? !prediction.included : Boolean(r.predictionExclusion);
  });
  const compactExclusions = (document.predictionExclusions ?? []).filter((entry) => enabled.includes(entry.regime));
  const excludedCount = Object.entries(document.summary[kernel] ?? {})
    .filter(([regime]) => regime !== "all" && regime !== "common" && enabled.includes(regime))
    .reduce((total, [, cell]) => total + cell.nExcluded, 0);
  const excludedStatuses = Array.from(new Set([
    ...excludedRows.map((r) => r.predictions?.[kernel]?.extentStatus ?? r.predictionExclusion ?? "excluded"),
    ...compactExclusions.map((entry) => entry.status),
  ]));
  const summaryEntries = Object.entries(document.summary[kernel] ?? {})
    .filter(([regime]) => regime === "all" || regime === "common" || enabled.includes(regime))
    .sort(([a], [b]) => (a === "all" ? -1 : b === "all" ? 1 : a === "common" ? -1 : b === "common" ? 1 : 0));
  const sensitivityKernels = kernels.filter((k) => absorptivitySensitivityCells(document, k) !== null);
  const depthReferenceUnstated = document.datasets.some((d) => d.notes.some((note) => DEPTH_REFERENCE_NOTE.test(note)));
  const limits = document.limits ?? DEFAULT_LIMITS;
  const pooledN = kernels.flatMap((k) => {
    const pooled = document.summary[k]?.all;
    return pooled ? [`${KERNEL_LABELS[k] ?? k} n ${pooled.n}`] : [];
  });

  const toggleRegime = (label: string) =>
    setEnabled((current) => (current.includes(label) ? current.filter((l) => l !== label) : [...current, label]));

  return (
    <div className="space-y-4 p-4">
      <Card>
        <CardHeader>
          <CardTitle>Dataset Comparison (LPBF)</CardTitle>
          <p className="mt-1 text-sm font-medium text-amber-800" data-testid="honesty-statement">{document.honesty.statement}</p>
          {document.absorption?.path ? <p className="mt-1 text-xs text-slate-600" data-testid="absorption-path">{`Absorption path: ${document.absorption.path}`}</p> : null}
          <p className="mt-1 text-xs text-slate-500">
            {`Python-generated record, ${document.generatedAt}, implementation ${document.implementationHash}. Regime rule: ${document.regimeFilter.rule}`}
          </p>
        </CardHeader>
        <CardContent>
          <h3 className="mb-2 text-sm font-semibold text-slate-700">Dataset provenance</h3>
          <div className="grid gap-3 md:grid-cols-2">
            {document.datasets.map((d, index) => (
              <div key={d.id} className="rounded-lg border border-slate-200 p-3 text-xs text-slate-700" data-dataset={d.id}>
                <div className="font-medium text-slate-800">{`${d.id} (${index % 2 === 1 ? "square" : "circle"} markers)`}</div>
                <div>{d.citation}</div>
                <div>DOI: <a className="text-blue-700 underline" href={doiHref(d.doi)} rel="noreferrer noopener" target="_blank">{d.doi}</a></div>
                <div>{`License: ${d.license}`}</div>
                <div className="break-all">{`sha256: ${d.sha256}`}</div>
                <div>{`Rows in dataset: ${d.rows}`}</div>
                {d.notes.length > 0 ? (
                  <ul className="mt-1 list-disc space-y-0.5 pl-4 text-slate-500" data-testid={`notes-${d.id}`}>
                    {d.notes.map((note, i) => <li key={i}>{note}</li>)}
                  </ul>
                ) : null}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-wrap items-end gap-4">
          <label className="text-xs text-slate-600">
            <span className="block">Kernel</span>
            <select
              aria-label="Kernel"
              className="rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
              value={kernel}
              onChange={(event) => setKernel(event.target.value)}
            >
              {kernels.map((k) => <option key={k} value={k}>{KERNEL_LABELS[k] ?? k}</option>)}
            </select>
          </label>
          <div>
            <span className="block text-xs text-slate-600">Regime</span>
            <div className="flex flex-wrap gap-2">
              {regimeLabels.map((label) => {
                const on = enabled.includes(label);
                return (
                  <button
                    key={label}
                    type="button"
                    aria-pressed={on}
                    onClick={() => toggleRegime(label)}
                    className={`rounded-full border px-3 py-1 text-xs ${on ? "text-white" : "bg-white"}`}
                    style={{ borderColor: regimeColor(label), backgroundColor: on ? regimeColor(label) : undefined, color: on ? undefined : regimeColor(label) }}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
          <p className="basis-full text-xs text-slate-600" data-testid="powder-layer-note">{POWDER_LAYER_NOTE}</p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        {(["width", "depth"] as const).map((metric) => (
          <Card key={metric}>
            <CardHeader><CardTitle className="text-sm">{`Predicted vs measured ${metric}: ${KERNEL_LABELS[kernel] ?? kernel}`}</CardTitle></CardHeader>
            <CardContent>
              <ScatterPlot metric={metric} points={metric === "width" ? widthPoints : depthPoints} axisMax={axisFor(metric)} />
              <p className="mt-2 text-xs text-slate-500">Solid line: 1:1. Dashed lines: ±30 %. Hollow markers: rows excluded from the statistics.</p>
              {metric === "depth" && depthReferenceUnstated ? (
                <p className="mt-1 text-xs text-slate-600" data-testid="depth-reference-caption">Totis depth reference line not stated (substrate vs powder surface); 25 µm powder layer over a printed base.</p>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </div>
      <p className="text-xs text-slate-600" data-testid="excluded-caption">
        {excludedCount === 0
          ? "0 excluded rows for this kernel and regime selection."
          : `${excludedCount} excluded: extentStatus ${excludedStatuses.join(", ")} (hover a hollow marker for the kernel's extentNote).`}
      </p>

      <Card>
        <CardHeader><CardTitle className="text-sm">{`Summary by regime: ${KERNEL_LABELS[kernel] ?? kernel}`}</CardTitle></CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {summaryEntries.map(([regime, cell]) => (
              <div key={regime} className="rounded-lg border border-slate-200 p-3" data-summary={`${kernel}/${regime}`}>
                <div className="text-sm font-semibold" style={{ color: regime === "all" || regime === "common" ? undefined : regimeColor(regime) }}>
                  {regime === "all" ? "all regimes (pooled, independent of the chip filter)" : regime === "common" ? "common subset (rows where all kernels are computed)" : regime}
                </div>
                <div className="mb-2 text-xs text-slate-500">{`n ${cell.n}, excluded ${cell.nExcluded}`}</div>
                <div className="grid grid-cols-2 gap-3">
                  <StatLine label="width" cell={cell.width} />
                  <StatLine label="depth" cell={cell.depth} />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 text-xs text-slate-600" data-testid="summary-limits">
            <p className="font-medium">Limits of this summary</p>
            <ul className="list-disc space-y-0.5 pl-4">
              <li data-testid="pooled-n">{`Kernels are compared on different included subsets (pooled n: ${pooledN.join(", ")}).`}</li>
              {limits.map((limit, i) => <li key={i}>{limit}</li>)}
            </ul>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Absorptivity bracket: sensitivity, not calibration</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="text-xs text-slate-700" data-testid="sensitivity-table">
            <caption className="mb-1 text-left text-slate-500">
              {document.absorptivitySensitivity.label ? <span data-testid="sensitivity-label">{document.absorptivitySensitivity.label} </span> : null}
              Width MAPE, depth MAPE and included rows n per kernel at each assumed absorptivity. Sensitivity, not calibration: no value is fitted.
            </caption>
            <thead>
              <tr>
                <th className="pr-4 text-left">kernel</th>
                {document.absorptivitySensitivity.values.map((v) => <th key={v} className="pr-4 text-right">{`A = ${v}`}</th>)}
              </tr>
            </thead>
            <tbody>
              {sensitivityKernels.map((k) => (
                <tr key={k} className="align-top">
                  <td className="pr-4">{KERNEL_LABELS[k] ?? k}</td>
                  {(absorptivitySensitivityCells(document, k) ?? []).map((c) => (
                    <td key={c.value} className="pr-4 text-right" data-sensitivity={`${k}/${c.value}`}>
                      <div>{`width ${c.widthMape === null ? "n/a" : `${fmt1(c.widthMape)} %`}`}</div>
                      <div>{`depth ${c.depthMape === null ? "n/a" : `${fmt1(c.depthMape)} %`}`}</div>
                      <div>{`n ${c.nIncluded === null ? "n/a" : c.nIncluded}`}</div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-slate-600" data-testid="sensitivity-sentence">{SENSITIVITY_SENTENCE}</p>
        </CardContent>
      </Card>

      {document.referenceTransient?.note ? (
        <p className="text-xs text-slate-600" data-testid="reference-transient-note">{`Reference transient: ${document.referenceTransient.note}`}</p>
      ) : null}
    </div>
  );
}

export function NoComparisonRecord() {
  return (
    <div className="p-4">
      <Card>
        <CardHeader>
          <CardTitle>Dataset Comparison (LPBF)</CardTitle>
        </CardHeader>
        <CardContent className="flex items-start gap-3 text-sm text-slate-700" data-testid="no-record">
          <FileSearch aria-hidden="true" className="mt-0.5 h-5 w-5 text-slate-400" />
          <div>
            <p className="font-medium">No comparison record committed yet.</p>
            <p className="text-xs text-slate-500">
              This page only displays the Python-generated file docs/LPBF_DATASET_COMPARISON_2026-10-05.view.json; nothing is
              computed in the browser. Nothing is shown until that file exists.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function LpbfDatasetComparisonLab({ document }: { document?: LpbfDatasetComparisonDocument | null }) {
  if (document === undefined) return <SpentDatasetPanel />;
  return document ? <DatasetComparisonView document={document} /> : <NoComparisonRecord />;
}
