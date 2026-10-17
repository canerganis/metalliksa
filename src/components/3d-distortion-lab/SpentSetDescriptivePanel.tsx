import React, { useEffect, useRef, useState } from "react";
import { FileSearch } from "lucide-react";
import {
  type LpbfSpentDescriptiveDocument,
  type SpentGroup,
  type SpentSet,
} from "../../data/lpbfSpentDescriptive";
import { loadCommittedSpentDescriptive } from "../../data/lpbfSpentDescriptiveRecord";
import { useResearchStore } from "../../store/useResearchStore";
import { doiHref } from "./LpbfDatasetComparisonLab";

// Read-only view of the Python-generated record docs/LPBF_SPENT_DESCRIPTIVE_<date>.view.json (research hub spec 8.4).
// Nothing is computed here: every figure is read from the record and carries data-source with its field path.
// The only derived facts are axis scales and the absolute value of a signed median for the chip wording.

const EMPTY_TEXT = "No spent-set descriptive record is committed yet.";
const NO_EXPLANATION = "No catalogued explanation";
const AXIS_LABEL = { speed: "scan speed (mm/s), log scale", power: "laser power (W), log scale" } as const;

/** Compact display number with 3 significant digits. */
function fmt(value: number): string {
  return String(Number(value.toPrecision(3)));
}
function fmtOrDash(value: number | null): string {
  return value === null ? "none" : fmt(value);
}

function logTicks(lo: number, hi: number): number[] {
  const out: number[] = [];
  const first = Math.floor(Math.log10(lo));
  const last = Math.ceil(Math.log10(hi));
  for (let e = first; e <= last; e += 1) {
    for (const m of [1, 2, 5]) {
      const t = m * 10 ** e;
      if (t >= lo && t <= hi) out.push(t);
    }
  }
  return out;
}

/** Index cut values named by the record's own bin ids (for example below-15, 15-to-20, at-or-above-20). */
function cutsOf(set: SpentSet): number[] {
  const found = new Set<number>();
  for (const bin of set.deviation[0]?.bins ?? []) {
    for (const m of bin.id.match(/\d+(?:\.\d+)?/g) ?? []) found.add(Number(m));
  }
  return Array.from(found).sort((a, b) => a - b);
}

function groupLabel(g: SpentGroup, axis: SpentSet["curveAxis"]): string {
  const fixedKey = axis === "speed" ? "power_W" : "speed_mm_s";
  const role = g.beamRole === "primary" ? "beam reading" : "beam sensitivity reading";
  return `${role} ${g.fixed.beam_um} µm, ${fixedKey === "power_W" ? "power" : "speed"} ${g.fixed[fixedKey]} ${fixedKey === "power_W" ? "W" : "mm/s"}, ${g.points.length} rows`;
}

interface ChartProps {
  readonly set: SpentSet;
  readonly setIndex: number;
  readonly group: SpentGroup;
  readonly groupIndex: number;
  readonly xMode: "process" | "index";
}

export function SpentChart({ set, setIndex, group, groupIndex, xMode }: ChartProps) {
  const W = 560;
  const H = 300;
  const m = { l: 56, r: 16, t: 14, b: 44 };
  const pw = W - m.l - m.r;
  const ph = H - m.t - m.b;
  const base = `sets[${setIndex}].groups[${groupIndex}]`;
  const xOf = (x: number, index: number | null) => (xMode === "process" ? x : index);
  const pts = group.points.flatMap((p, i) => {
    const x = xOf(p.x, p.index);
    return x !== null && x > 0 && p.measured_um !== null ? [{ p, i, x }] : [];
  });
  const cur = (group.curve ?? []).map((c, i) => ({ c, i, x: xOf(c.x, c.index) }));
  const cuts = xMode === "index" ? cutsOf(set) : [];
  const xs = [...pts.map((q) => q.x), ...cur.flatMap((q) => (q.x !== null && q.x > 0 ? [q.x] : [])), ...cuts];
  const ys = [...pts.map((q) => q.p.measured_um as number), ...cur.flatMap((q) => (q.c.depth_um === null ? [] : [q.c.depth_um]))];
  if (xs.length < 2 || ys.length < 1) {
    return <p className="text-xs text-slate-500" data-testid="chart-empty">Nothing to plot for this group.</p>;
  }
  const xlo = Math.min(...xs);
  const xhi = Math.max(...xs);
  const yhi = Math.max(...ys) * 1.1;
  const sx = (v: number) => m.l + ((Math.log(v) - Math.log(xlo)) / (Math.log(xhi) - Math.log(xlo) || 1)) * pw;
  const sy = (v: number) => m.t + ph - (v / (yhi || 1)) * ph;
  const xt = logTicks(xlo, xhi);
  const yt = [0, 0.25, 0.5, 0.75, 1].map((f) => f * yhi);
  // Break the served line at calls that returned no depth.
  const segments: { x: number; y: number }[][] = [[]];
  for (const q of cur) {
    if (q.c.depth_um === null || q.x === null || q.x <= 0) {
      if (segments[segments.length - 1].length) segments.push([]);
    } else {
      segments[segments.length - 1].push({ x: q.x, y: q.c.depth_um });
    }
  }
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`Melt pool depth against ${xMode === "index" ? "the served index" : set.curveAxis}, measured points and the served curve`}
      className="w-full max-w-2xl"
      data-testid="spent-chart"
    >
      <rect x={m.l} y={m.t} width={pw} height={ph} fill="var(--mk-paper)" stroke="var(--mk-chart-axis)" />
      {yt.map((t) => (
        <g key={`y${t}`}>
          <line x1={m.l} x2={m.l + pw} y1={sy(t)} y2={sy(t)} stroke="var(--mk-chart-axis)" strokeOpacity="0.4" />
          <text x={m.l - 6} y={sy(t) + 3} fontSize="9" textAnchor="end" fill="var(--mk-text-dim)">{Math.round(t)}</text>
        </g>
      ))}
      {xt.map((t) => (
        <g key={`x${t}`}>
          <line x1={sx(t)} x2={sx(t)} y1={m.t} y2={m.t + ph} stroke="var(--mk-chart-axis)" strokeOpacity="0.4" />
          <text x={sx(t)} y={m.t + ph + 14} fontSize="9" textAnchor="middle" fill="var(--mk-text-dim)">{fmt(t)}</text>
        </g>
      ))}
      {cuts.map((c, i) => (
        <g key={`cut${c}`} data-cut={c}>
          <line x1={sx(c)} x2={sx(c)} y1={m.t} y2={m.t + ph} stroke="var(--mk-text-strong)" strokeDasharray="2 3" />
          <text x={sx(c) + 3} y={m.t + 10 + i * 10} fontSize="9" fill="var(--mk-text-strong)" data-source={`sets[${setIndex}].deviation[0].bins`}>{`index ${c}`}</text>
        </g>
      ))}
      {segments.filter((s) => s.length > 1).map((s, i) => (
        <polyline
          key={`seg${i}`}
          data-line="served"
          data-source={`${base}.curve`}
          points={s.map((q) => `${sx(q.x).toFixed(1)},${sy(q.y).toFixed(1)}`).join(" ")}
          fill="none"
          stroke="var(--mk-text-strong)"
          strokeWidth="2"
        />
      ))}
      {pts.map((q) => (
        <g key={q.p.rowId} data-point="measured">
          <title>{`Measured, row ${q.p.rowId}`}</title>
          {q.p.measuredSd_um !== null ? (
            <line
              x1={sx(q.x)} x2={sx(q.x)}
              y1={sy((q.p.measured_um as number) + q.p.measuredSd_um)} y2={sy(Math.max(0, (q.p.measured_um as number) - q.p.measuredSd_um))}
              stroke="var(--mk-text-dim)" data-source={`${base}.points[${q.i}].measuredSd_um`}
            />
          ) : null}
          <circle cx={sx(q.x)} cy={sy(q.p.measured_um as number)} r={4} fill="var(--mk-text-strong)" fillOpacity="0.35" stroke="var(--mk-text-strong)" strokeWidth="1.4" data-source={`${base}.points[${q.i}].measured_um`} />
        </g>
      ))}
      <text x={m.l + pw / 2} y={H - 6} fontSize="10" textAnchor="middle" fill="var(--mk-text-strong)">
        {xMode === "index" ? "served index (unrounded), log scale" : AXIS_LABEL[set.curveAxis]}
      </text>
      <text x={12} y={m.t + ph / 2} fontSize="10" textAnchor="middle" fill="var(--mk-text-strong)" transform={`rotate(-90 12 ${m.t + ph / 2})`}>melt pool depth (µm)</text>
    </svg>
  );
}

function ModelMap({ doc, selectSet }: { doc: LpbfSpentDescriptiveDocument; selectSet: (id: string) => void }) {
  return (
    <div className="overflow-x-auto" data-testid="model-map">
      <table className="w-full text-left text-xs text-slate-700">
        <caption className="mb-1 text-left text-sm font-semibold text-slate-700">Model map, by served index bin</caption>
        <thead>
          <tr className="border-b border-slate-200 text-slate-600">
            <th scope="col" className="py-1 pr-3">Set</th>
            <th scope="col" className="pr-3">Served index bin</th>
            <th scope="col" className="pr-3">Direction</th>
            <th scope="col" className="pr-3 text-right">n</th>
          </tr>
        </thead>
        <tbody>
          {doc.modelMap.map((row, i) => row.bins.map((b, j) => (
            <tr key={`${row.key}/${b.id}`} className="border-b border-slate-100" data-map-row={`${row.key}/${b.id}`}>
              {j === 0 ? (
                <th scope="row" rowSpan={row.bins.length} className="py-1 pr-3 align-top font-medium text-slate-800">
                  <button type="button" className="text-left text-blue-700 underline" onClick={() => selectSet(row.setId)}>{row.label}</button>
                  {row.alsoSets.length ? <div className="font-normal text-slate-500">{`Same experiments: ${row.alsoSets.join(", ")}`}</div> : null}
                </th>
              ) : null}
              <td className="pr-3">{b.label}</td>
              <td className="pr-3" data-source={`modelMap[${i}].bins[${j}].direction`}>{b.direction ?? "no rows"}</td>
              <td className="pr-3 text-right" data-source={`modelMap[${i}].bins[${j}].n`}>{b.n}</td>
            </tr>
          )))}
        </tbody>
      </table>
      <p className="mt-1 text-xs text-slate-500" data-source="directionRule">{`Direction rule: ${doc.directionRule}.`}</p>
    </div>
  );
}

function Chips({ set, setIndex }: { set: SpentSet; setIndex: number }) {
  return (
    <div className="space-y-2" data-testid="deviation-chips">
      {set.deviation.map((dev, d) => (
        <div key={dev.beamRole} data-deviation={dev.beamRole}>
          <div className="text-xs font-medium text-slate-600">{`${dev.beamRole === "primary" ? "Beam reading" : "Beam sensitivity reading"} ${dev.beam_um} µm`}</div>
          <ul className="mt-1 flex flex-wrap gap-2">
            {dev.bins.map((b, j) => {
              const path = `sets[${setIndex}].deviation[${d}].bins[${j}]`;
              return (
                <li key={b.id} className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-700" data-bin={b.id}>
                  <span className="font-medium text-slate-800">{b.label}</span>
                  {": "}
                  {b.median_pct === null ? (
                    <span data-source={`${path}.n`}>no rows</span>
                  ) : (
                    <span data-chip="deviation" data-source={`${path}.median_pct`}>
                      {`model ${b.median_pct >= 0 ? "deeper" : "shallower"} by about ${Math.round(Math.abs(b.median_pct))} % (n ${b.n})`}
                    </span>
                  )}
                  {b.median_pct !== null ? (
                    <span className="ml-2 text-slate-500" data-source={`${path}.p10_pct`}>{`p10 ${Math.round(b.p10_pct as number)} %, p90 ${Math.round(b.p90_pct as number)} %`}</span>
                  ) : null}
                  {b.failed + b.unavailable > 0 ? (
                    <span className="ml-2 text-slate-500" data-source={`${path}.failed`}>{`no served depth: ${b.failed}, no usable pair: ${b.unavailable}`}</span>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}

function DataTable({ set, setIndex, researchText }: { set: SpentSet; setIndex: number; researchText: string }) {
  return (
    <details className="mt-3 rounded-lg border border-slate-200 p-3" data-testid="data-table-fallback">
      <summary className="cursor-pointer text-sm font-medium text-slate-700">Data table</summary>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-700">
          <thead>
            <tr className="border-b border-slate-200 text-slate-600">
              <th scope="col" className="pr-3">Group</th>
              <th scope="col" className="pr-3">{set.curveAxis === "speed" ? "Speed (mm/s)" : "Power (W)"}</th>
              <th scope="col" className="pr-3">Depth, Measured (µm)</th>
              <th scope="col" className="pr-3">Read spread (µm)</th>
              <th scope="col" className="pr-3">Depth, served, Unresolved (µm)</th>
              <th scope="col" className="pr-3">Served index</th>
              <th scope="col" className="pr-3">Difference (%)</th>
              <th scope="col" className="pr-3">Research model</th>
            </tr>
          </thead>
          <tbody>
            {set.groups.flatMap((g, gi) => g.points.map((p, pi) => {
              const path = `sets[${setIndex}].groups[${gi}].points[${pi}]`;
              return (
                <tr key={`${g.id}/${p.rowId}`} className="border-b border-slate-100" data-row={`${g.id}/${p.rowId}`}>
                  <td className="pr-3">{g.id}</td>
                  <td className="pr-3" data-source={`${path}.x`}>{fmt(p.x)}</td>
                  <td className="pr-3" data-source={`${path}.measured_um`} data-source-label="Measured">{fmtOrDash(p.measured_um)}</td>
                  <td className="pr-3" data-source={`${path}.measuredSd_um`}>{fmtOrDash(p.measuredSd_um)}</td>
                  <td className="pr-3" data-source={`${path}.served_um`} data-source-label="Unresolved">{fmtOrDash(p.served_um)}</td>
                  <td className="pr-3" data-source={`${path}.index`}>{fmtOrDash(p.index)}</td>
                  <td className="pr-3" data-source={`${path}.diffPct`}>{p.diffPct === null ? "none" : String(Math.round(p.diffPct))}</td>
                  <td className="pr-3">{researchText}</td>
                </tr>
              );
            }))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export function SetCard({ doc, set, setIndex }: { doc: LpbfSpentDescriptiveDocument; set: SpentSet; setIndex: number }) {
  const defaultGroup = Math.max(0, set.groups.findIndex((g) => g.curve !== null));
  const [groupIndex, setGroupIndex] = useState(defaultGroup);
  const [xMode, setXMode] = useState<"process" | "index">("process");
  const group = set.groups[Math.min(groupIndex, set.groups.length - 1)];
  const gi = set.groups.indexOf(group);
  const p = set.provenance;
  const base = `sets[${setIndex}]`;
  const researchText = `unavailable: ${doc.research.reasonCode}`;
  return (
    <div className="space-y-3" data-set-card={set.id}>
      <div className="rounded-lg border border-slate-200 p-3 text-xs text-slate-700" data-testid="provenance-card">
        <div className="text-sm font-medium text-slate-800">{set.title}</div>
        <div>{p.citation}</div>
        <div>DOI: <a className="text-blue-700 underline" href={doiHref(p.doi)} rel="noreferrer noopener" target="_blank">{p.doi}</a></div>
        <div>{`Licence: ${p.licence}`}</div>
        <div>{`Attribution: ${p.attribution}`}</div>
        <div className="break-all" data-source={`${base}.provenance.tableSha256`}>{`Table sha256: ${p.tableSha256}`}</div>
        <div data-source={`${base}.provenance.rows`}>{`Rows: ${p.rows}`}</div>
        <div data-source={`${base}.spent.status`}>{`Status: ${set.spent.status}`}</div>
        <ul className="list-disc pl-4 text-slate-600">
          {set.spent.spentBy.map((s, i) => <li key={i} data-source={`${base}.spent.spentBy[${i}]`}>{`Spent by: ${s.event} (${s.date})`}</li>)}
        </ul>
        <div>{`Observable: ${set.observable}. Depth datum: ${p.datum}`}</div>
        <div data-source={`${base}.beam.value_um`}>{`Beam reading: ${set.beam.value_um} µm, ${set.beam.status}. ${set.beam.definition}`}</div>
        {set.beam.sensitivity_um !== null ? <div data-source={`${base}.beam.sensitivity_um`}>{`Sensitivity reading: ${set.beam.sensitivity_um} µm`}</div> : null}
        <div>{`Substrate: ${p.substrate}. Power basis: ${p.powerBasis}`}</div>
        <div data-source={`${base}.measuredSource`}>{`Measured values: label ${set.measuredSource.label}, ${set.measuredSource.transcription} transcription, ${set.measuredSource.locator}`}</div>
        <div data-source={`${base}.servedSource`}>{`Served values: label ${set.servedSource.label}, ${set.servedSource.reasonCode}. ${set.servedSource.reasonText}`}</div>
      </div>

      {group ? (
        <div>
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-700">
            <label className="flex items-center gap-1">
              <span>Curve group</span>
              <select className="rounded border border-slate-300 bg-white px-1 py-0.5" value={gi} onChange={(e) => setGroupIndex(Number(e.target.value))}>
                {set.groups.map((g, i) => <option key={g.id} value={i}>{groupLabel(g, set.curveAxis)}</option>)}
              </select>
            </label>
            <div role="group" aria-label="Horizontal axis" className="flex gap-1">
              <button type="button" aria-pressed={xMode === "process"} className={`rounded border px-2 py-0.5 ${xMode === "process" ? "border-slate-700 bg-slate-100" : "border-slate-300"}`} onClick={() => setXMode("process")}>{set.curveAxis === "speed" ? "Scan speed" : "Laser power"}</button>
              <button type="button" aria-pressed={xMode === "index"} className={`rounded border px-2 py-0.5 ${xMode === "index" ? "border-slate-700 bg-slate-100" : "border-slate-300"}`} onClick={() => setXMode("index")}>Served index</button>
            </div>
          </div>
          <SpentChart set={set} setIndex={setIndex} group={group} groupIndex={gi} xMode={xMode} />
          <ul className="mt-1 space-y-0.5 text-xs text-slate-600" data-testid="chart-legend">
            <li>Dots: Measured depth, with its read spread where the table lists one.</li>
            <li>Solid line: served model depth, Unresolved source. {set.servedSource.reasonText}</li>
            <li>Dashed vertical lines (index view only): the cuts that define the index bins.</li>
            <li data-testid="research-column">{`Research model: ${researchText}`}</li>
          </ul>
        </div>
      ) : null}

      <Chips set={set} setIndex={setIndex} />

      <div data-testid="notes">
        <h4 className="text-sm font-semibold text-slate-700">Notes</h4>
        {set.notes.length === 0 ? (
          <p className="text-xs text-slate-500">{NO_EXPLANATION}</p>
        ) : (
          <ul className="list-disc space-y-1 pl-4 text-xs text-slate-700">
            {set.notes.map((n, i) => (
              <li key={n.code} data-note={n.code} data-source={`${base}.notes[${i}]`}>
                {n.sentence}
                <span className="block text-slate-500">{`Source: ${n.source}, ${n.locator}`}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <DataTable set={set} setIndex={setIndex} researchText={researchText} />
    </div>
  );
}

function openBlindTest(): void {
  const store = useResearchStore.getState();
  // The 'blind-test' tab id is added to the research store by the user blind test work. Cast until the type lists it.
  store.setActiveTab("blind-test" as unknown as Parameters<typeof store.setActiveTab>[0]);
  window.dispatchEvent(new CustomEvent("metallix-navigate-tab", { detail: { tabId: "research-hub" } }));
}

export function SpentSetDescriptivePanel({ document: given }: { document?: LpbfSpentDescriptiveDocument | null }) {
  const [loaded, setLoaded] = useState<LpbfSpentDescriptiveDocument | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState(0);
  const radios = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    if (given !== undefined) return;
    let live = true;
    loadCommittedSpentDescriptive().then(
      (doc) => { if (live) setLoaded(doc); },
      (err: unknown) => { if (live) setError(err instanceof Error ? err.message : "The committed record could not be read."); },
    );
    return () => { live = false; };
  }, [given]);

  const doc = given !== undefined ? given : loaded;
  const heading = <h2 className="font-semibold text-slate-800">Spent sets, descriptive</h2>;

  if (error) {
    return <section className="mx-4 mb-4 rounded-xl border border-slate-200 bg-white p-4" data-testid="spent-error">{heading}<p className="text-sm text-slate-700">{`The committed record could not be read: ${error}`}</p></section>;
  }
  if (doc === undefined) {
    return <section className="mx-4 mb-4 rounded-xl border border-slate-200 bg-white p-4" data-testid="spent-loading">{heading}<p className="text-sm text-slate-500">Loading the spent-set record.</p></section>;
  }
  if (doc === null || doc.sets.length === 0) {
    return (
      <section className="mx-4 mb-4 rounded-xl border border-slate-200 bg-white p-4" aria-labelledby="spent-heading" data-testid="spent-empty">
        <div className="flex items-start gap-3 text-sm text-slate-700">
          <FileSearch aria-hidden="true" className="mt-0.5 h-5 w-5 text-slate-400" />
          <div>
            <h2 id="spent-heading" className="font-semibold text-slate-800">Spent sets, descriptive</h2>
            <p className="font-medium">{EMPTY_TEXT}</p>
            <p className="text-xs text-slate-500">This panel only displays a Python-generated file under docs. Nothing is computed in the browser.</p>
          </div>
        </div>
      </section>
    );
  }

  const index = Math.min(selected, doc.sets.length - 1);
  const set = doc.sets[index];
  const select = (i: number) => {
    const next = (i + doc.sets.length) % doc.sets.length;
    setSelected(next);
    radios.current[next]?.focus();
  };
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") { e.preventDefault(); select(index + 1); }
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); select(index - 1); }
    else if (e.key === "Home") { e.preventDefault(); select(0); }
    else if (e.key === "End") { e.preventDefault(); select(doc.sets.length - 1); }
  };

  return (
    <section className="mx-4 mb-4 space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm" aria-labelledby="spent-heading" data-testid="spent-panel">
      <header className="space-y-2">
        <h2 id="spent-heading" className="font-semibold text-slate-800">Spent sets, descriptive</h2>
        <p>
          <span className="inline-block rounded-full border border-amber-700 px-2 py-0.5 text-xs font-medium text-amber-900" data-testid="spent-badge" data-source="honesty.label">{doc.honesty.label}</span>
        </p>
        <p className="text-sm font-medium text-amber-800" data-testid="spent-statement" data-source="honesty.statement">{doc.honesty.statement}</p>
        <p className="text-xs text-slate-500" data-source="generatedAt">{`Python-generated record, ${doc.generatedAt}, implementation ${doc.implementationHash}.`}</p>
        <p className="text-xs text-slate-500" data-source="research.reasonCode">{`Research model: unavailable: ${doc.research.reasonCode}`}</p>
        <details className="text-sm text-slate-700">
          <summary className="cursor-pointer font-medium">How to read this</summary>
          <div className="mt-2 space-y-1 text-xs text-slate-600">
            <p>Every set here was already used while the model was developed or checked. The dots are published measurements. The solid line is what the served model gives for the same settings.</p>
            <p>The chips describe how far the served depth sits from the measured depth, as a median of signed differences with the spread of the middle 80 percent of rows. They describe a gap. They do not say how the model does on data it has not seen.</p>
            <p>The served index is the normalized enthalpy of the served call. The index bins group rows by that index. The notes are candidate explanations from a fixed catalogue. None of them was tested.</p>
          </div>
        </details>
      </header>

      <ModelMap doc={doc} selectSet={(id) => { const i = doc.sets.findIndex((s) => s.id === id); if (i >= 0) setSelected(i); }} />

      <div>
        <div id="spent-set-label" className="mb-1 text-sm font-semibold text-slate-700">Set</div>
        <div role="radiogroup" aria-labelledby="spent-set-label" className="flex flex-wrap gap-2" onKeyDown={onKeyDown}>
          {doc.sets.map((s, i) => (
            <button
              key={s.id}
              ref={(el) => { radios.current[i] = el; }}
              type="button"
              role="radio"
              aria-checked={i === index}
              tabIndex={i === index ? 0 : -1}
              className={`rounded-lg border px-3 py-1 text-xs ${i === index ? "border-slate-800 bg-slate-100 font-medium" : "border-slate-300"}`}
              onClick={() => setSelected(i)}
            >
              {s.title.split(" (")[0]}
            </button>
          ))}
        </div>
      </div>

      <SetCard key={set.id} doc={doc} set={set} setIndex={index} />

      {doc.deferred.length > 0 ? (
        <details className="text-xs text-slate-600" data-testid="deferred">
          <summary className="cursor-pointer font-medium">Sets left out of this record</summary>
          <ul className="mt-1 list-disc pl-4">
            {doc.deferred.map((d, i) => <li key={d.datasetId} data-source={`deferred[${i}]`}>{`${d.datasetId}: ${d.reason}`}</li>)}
          </ul>
        </details>
      ) : null}

      <p>
        <button type="button" className="text-sm text-blue-700 underline" onClick={openBlindTest}>Test the model on your own tracks</button>
      </p>
    </section>
  );
}

export default SpentSetDescriptivePanel;
