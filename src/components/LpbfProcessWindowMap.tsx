import React, { useEffect, useRef, useState } from "react";
import { AlertTriangle, Grid3x3, Info, RefreshCw } from "lucide-react";
import {
  LpbfProcessWindowRequestError,
  pythonComputationService,
  type LpbfProcessWindowCell,
  type LpbfProcessWindowDataset,
  type LpbfProcessWindowResponse,
} from "../services/pythonComputationService";
import { useMaterialSpecimenStore } from "../store/useMaterialSpecimenStore";
import { LITERATURE_PV_WINDOWS } from "../utils/lpbfFourAlloySchema";
import { resolveOptimizerAlloy } from "../utils/lpbfOptimizerAlloy";
import { COMMITTED_ERROR_BANDS, bandSubjectFromProcessWindowCell, type ErrorBandsSummary } from "../data/lpbfErrorBands";
import { THIN_SPACE, formatSignificant } from "../utils/numberFormat";
import { PublishedTrackBands } from "./PublishedTrackBands";
import { IS_STATIC_DEMO } from "../demo/flag.ts";
import { DEMO_LOCK } from "../demo/demoGate.ts";

// Static demo: the grid feeds a recorded snapshot, so its axes are locked to the recorded values (compile-time constant).
const lock: { disabled?: boolean; title?: string } = IS_STATIC_DEMO ? DEMO_LOCK : {};
import {
  HATCH_PATTERN_ID,
  PROCESS_WINDOW_BEAM_TOLERANCE_PCT,
  PROCESS_WINDOW_DEFAULT_AXIS,
  PROCESS_WINDOW_MAX_CELLS,
  PROCESS_WINDOW_MAX_POWER_W,
  PROCESS_WINDOW_MAX_SPEED_MM_S,
  PROCESS_WINDOW_MS_PER_CELL,
  axisFraction,
  axisFractionClamped,
  cellAriaLabel,
  cellAt,
  checkedProcessWindow,
  defaultAxisRange,
  inputsKey,
  isStale,
  legendEntries,
  memoGet,
  memoSet,
  moveCell,
  noPrintableNoteText,
  cellGateSentences,
  parseAxis,
  verdictStyle,
  type CellPosition,
  type ProcessWindowInputs,
} from "../data/lpbfProcessWindow";

const GRID_KEYS = new Set(["ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown", "Home", "End", "PageUp", "PageDown"]);
const MARKER_COLORS = ["#38bdf8", "#c4b5fd", "#67e8f9", "#f0abfc"];

export type ProcessWindowSource = "computed" | "engine-cache" | "browser-memo";

/** Display only (3 significant digits, shared formatter). The exact value is in the cell tooltip and in the engine response. */
const fmt = (value: number | null | undefined, digits = 3): string =>
  value === null || value === undefined ? "not computed" : formatSignificant(value, digits);
/** Hover text of a map cell: P and v with units, the verdict, and width / depth in µm when the model resolved them. */
const cellTooltip = (cell: LpbfProcessWindowCell): string => {
  const base = `${cell.power_W}${THIN_SPACE}W, ${cell.speed_mm_s}${THIN_SPACE}mm/s: ${verdictStyle(cell.verdict).label}`;
  if (cell.verdict === "error" || cell.width_um === null || cell.depth_um === null) return base;
  return `${base}. Width ${formatSignificant(cell.width_um, 3)}${THIN_SPACE}µm, depth ${formatSignificant(cell.depth_um, 3)}${THIN_SPACE}µm.`;
};
const exactTitle = (value: number | null | undefined, unit: string): string | undefined =>
  value === null || value === undefined ? undefined : `Exact value: ${value} ${unit}`;

// ---------------------------------------------------------------------------------------------------------
// Always-visible honesty banner
// ---------------------------------------------------------------------------------------------------------
export const ProcessWindowHonestyBanner: React.FC<{ provenance?: LpbfProcessWindowResponse["provenance"] | null }> = ({ provenance }) => (
  <section aria-label="Evidence and limits" data-testid="pw-honesty-banner" className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-100">
    <p className="font-semibold">Screening only. This map is not a validation, not a qualified process window and not a print recommendation.</p>
    <ul className="mt-1 list-disc space-y-0.5 pl-5">
      <li data-testid="pw-banner-model">
        {provenance ? (
          <>Model <span className="font-mono">{provenance.modelId}</span>, solver revision <span className="font-mono">{provenance.solverRevision}</span>, implementation hash <span className="font-mono break-all">{provenance.implementationHash}</span>.</>
        ) : (
          <>Model, solver revision and implementation hash come from the engine response and are shown after Compute.</>
        )}
      </li>
      <li data-testid="pw-banner-absorptivity">Verdicts assume flat-plate absorptivity{provenance?.absorptionModel ? <> (engine reports <span className="font-mono">{provenance.absorptionModel}</span>)</> : null}; no powder-layer absorptivity enhancement is modelled.</li>
      <li data-testid="pw-banner-inconclusive">Inconclusive (hatched grey, ?) means the melt-pool geometry was not resolved. It is never a printable result.</li>
      <li data-testid="pw-banner-measurements">Hollow markers are published single-track measurements: geometry, not print outcomes. They carry no verdict.</li>
    </ul>
  </section>
);

// ---------------------------------------------------------------------------------------------------------
// Legend
// ---------------------------------------------------------------------------------------------------------
const Swatch: React.FC<{ verdict: LpbfProcessWindowCell["verdict"] }> = ({ verdict }) => {
  const style = verdictStyle(verdict);
  return (
    <svg width="22" height="18" viewBox="0 0 22 18" aria-hidden="true" focusable="false">
      <rect x="1" y="1" width="20" height="16" rx="2"
        fill={style.hatched ? `url(#${HATCH_PATTERN_ID}-legend)` : style.fill}
        stroke={style.stroke} strokeWidth={style.outlined ? 2 : 1} strokeDasharray={style.outlined ? "3 2" : undefined} />
      <text x="11" y="13" textAnchor="middle" fontSize="11" fontWeight="700" fill={style.textColor}>{style.letter}</text>
    </svg>
  );
};

export const ProcessWindowLegend: React.FC<{ result: LpbfProcessWindowResponse }> = ({ result }) => (
  <div data-testid="pw-legend" className="space-y-2">
    <svg width="0" height="0" aria-hidden="true" focusable="false" className="absolute">
      <defs>
        <pattern id={`${HATCH_PATTERN_ID}-legend`} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="5" height="5" fill="#334155" /><line x1="0" y1="0" x2="0" y2="5" stroke="#94a3b8" strokeWidth="2" />
        </pattern>
      </defs>
    </svg>
    <ul className="grid grid-cols-1 gap-1 text-xs text-slate-300 sm:grid-cols-2">
      {legendEntries(result).map(entry => (
        <li key={entry.verdict} className="flex items-center gap-2" data-testid={`pw-legend-${entry.verdict}`} data-count={entry.count}>
          <Swatch verdict={entry.verdict} />
          <span>{entry.style.label}</span>
          <span className="ml-auto font-mono text-slate-100">{entry.count}</span>
        </li>
      ))}
    </ul>
    <p className="text-xs text-slate-400">
      Overlays: dashed rectangle = literature P-v box; cross-hair = current P/v of the active specimen; hollow circle, diamond and triangle = published single-track measurements (one shape per dataset).
    </p>
  </div>
);

// ---------------------------------------------------------------------------------------------------------
// Heat map (SVG, role=grid, one tab stop)
// ---------------------------------------------------------------------------------------------------------
interface HeatmapProps {
  result: LpbfProcessWindowResponse;
  selected: CellPosition | null;
  onSelect?: (position: CellPosition) => void;
  current?: { power_W: number; speed_mm_s: number } | null;
  stale?: boolean;
}

const M = { left: 70, right: 14, top: 14, bottom: 58 };
const PLOT_W = 640;
const PLOT_H = 400;

export const ProcessWindowHeatmap: React.FC<HeatmapProps> = ({ result, selected, onSelect, current, stale }) => {
  const { nP, nV, powers_W, speeds_mm_s, literatureBox } = result.grid;
  const cw = PLOT_W / nV;
  const ch = PLOT_H / nP;
  const gridRef = useRef<SVGGElement | null>(null);
  const [focused, setFocused] = useState(false);
  const x = (fraction: number) => M.left + (fraction + 0.5) * cw;
  const y = (fraction: number) => M.top + PLOT_H - (fraction + 0.5) * ch;
  const box = {
    x0: x(axisFractionClamped(speeds_mm_s, literatureBox.speedMin_mm_s)),
    x1: x(axisFractionClamped(speeds_mm_s, literatureBox.speedMax_mm_s)),
    y0: y(axisFractionClamped(powers_W, literatureBox.powerMax_W)),
    y1: y(axisFractionClamped(powers_W, literatureBox.powerMin_W)),
  };
  const boxVisible = box.x1 > box.x0 && box.y1 > box.y0;
  const crossFx = current ? axisFraction(speeds_mm_s, current.speed_mm_s) : null;
  const crossFy = current ? axisFraction(powers_W, current.power_W) : null;
  const crossVisible = crossFx !== null && crossFy !== null;
  const fontSize = Math.max(9, Math.min(cw, ch) * 0.42);
  const tickEvery = (n: number) => (n > 10 ? 2 : 1);
  const activeId = selected ? `pw-cell-${selected.iP}-${selected.iV}` : undefined;

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (!GRID_KEYS.has(event.key) || !onSelect) return;
    event.preventDefault();
    onSelect(moveCell(selected ?? { iP: 0, iV: 0 }, event.key, nP, nV));
  };

  const datasets = result.overlay.datasets.filter(d => d.status === "available");
  return (
    <div data-testid="pw-heatmap" data-stale={stale ? "true" : "false"} className={stale ? "opacity-60" : undefined}>
      <svg viewBox={`0 0 ${M.left + PLOT_W + M.right} ${M.top + PLOT_H + M.bottom}`} className="h-auto w-full" role="group" aria-label={`Process window heat map for ${result.alloyId}: speed on the horizontal axis, power on the vertical axis`}>
        <defs>
          <pattern id={HATCH_PATTERN_ID} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="6" height="6" fill="#334155" /><line x1="0" y1="0" x2="0" y2="6" stroke="#94a3b8" strokeWidth="2" />
          </pattern>
        </defs>
        <g
          ref={gridRef}
          role="grid"
          tabIndex={0}
          aria-label="Process window cells. Use the arrow keys to move between cells, Home and End for the first and last speed, Page Up and Page Down for the highest and lowest power."
          aria-rowcount={nP}
          aria-colcount={nV}
          aria-activedescendant={activeId}
          data-testid="pw-grid"
          onKeyDown={onKeyDown}
          onFocus={() => { setFocused(true); if (!selected && onSelect) onSelect({ iP: 0, iV: 0 }); }}
          onBlur={() => setFocused(false)}
          style={{ outline: "none" }}
        >
          {Array.from({ length: nP }, (_, rowFromBottom) => {
            const iP = nP - 1 - rowFromBottom; // highest power first, drawn at the top
            return (
              <g key={iP} role="row" aria-rowindex={rowFromBottom + 1}>
                {Array.from({ length: nV }, (_, iV) => {
                  const cell = cellAt(result, iP, iV);
                  const style = verdictStyle(cell.verdict);
                  const px = x(iV - 0.5);
                  const py = y(iP + 0.5);
                  const isSelected = selected?.iP === iP && selected?.iV === iV;
                  return (
                    <g
                      key={iV}
                      id={`pw-cell-${iP}-${iV}`}
                      role="gridcell"
                      aria-colindex={iV + 1}
                      aria-selected={isSelected}
                      aria-label={cellAriaLabel(cell)}
                      data-testid={`pw-cell-${iP}-${iV}`}
                      data-verdict={cell.verdict}
                      onClick={() => { onSelect?.({ iP, iV }); gridRef.current?.focus(); }}
                      style={{ cursor: onSelect ? "pointer" : undefined }}
                    >
                      <title>{cellTooltip(cell)}</title>
                      <rect
                        x={px} y={py} width={cw} height={ch}
                        fill={style.hatched ? `url(#${HATCH_PATTERN_ID})` : style.fill}
                        stroke={style.outlined ? style.stroke : "#0f172a"}
                        strokeWidth={style.outlined ? 2 : 1}
                        strokeDasharray={style.outlined ? "4 3" : undefined}
                      />
                      <text x={px + cw / 2} y={py + ch / 2 + fontSize * 0.35} textAnchor="middle" fontSize={fontSize} fontWeight={700} fill={style.textColor} aria-hidden="true">{style.letter}</text>
                    </g>
                  );
                })}
              </g>
            );
          })}
          {selected && (
            <rect
              data-testid="pw-active-ring" x={x(selected.iV - 0.5)} y={y(selected.iP + 0.5)} width={cw} height={ch}
              fill="none" stroke={focused ? "#38bdf8" : "#e2e8f0"} strokeWidth={focused ? 4 : 2.5} pointerEvents="none"
            />
          )}
        </g>
        {boxVisible && (
          <rect data-testid="pw-literature-box" x={box.x0} y={box.y0} width={box.x1 - box.x0} height={box.y1 - box.y0}
            fill="none" stroke="#f8fafc" strokeWidth={2} strokeDasharray="7 5" pointerEvents="none">
            <title>{`Literature P-v box: ${literatureBox.powerMin_W}-${literatureBox.powerMax_W} W, ${literatureBox.speedMin_mm_s}-${literatureBox.speedMax_mm_s} mm/s`}</title>
          </rect>
        )}
        {crossVisible && current && (
          <g data-testid="pw-crosshair" pointerEvents="none" stroke="#f8fafc" strokeWidth={2.5}>
            <line x1={x(crossFx!)} x2={x(crossFx!)} y1={M.top} y2={M.top + PLOT_H} />
            <line y1={y(crossFy!)} y2={y(crossFy!)} x1={M.left} x2={M.left + PLOT_W} />
            <title>{`Current specimen P/v: ${current.power_W} W, ${current.speed_mm_s} mm/s`}</title>
          </g>
        )}
        {datasets.map((dataset, di) => (
          <g key={dataset.id} data-testid={`pw-markers-${dataset.id}`} pointerEvents="none" aria-hidden="true">
            {dataset.points.map(point => {
              const fx = axisFraction(speeds_mm_s, point.speed_mm_s);
              const fy = axisFraction(powers_W, point.power_W);
              if (fx === null || fy === null) return null;
              const cx = x(fx);
              const cy = y(fy);
              const color = MARKER_COLORS[di % MARKER_COLORS.length];
              const r = Math.max(4, Math.min(cw, ch) * 0.16);
              const common = { fill: "none", stroke: color, strokeWidth: 2.2, "data-testid": "pw-marker" } as const;
              const shape = di % 3 === 0
                ? <circle {...common} cx={cx} cy={cy} r={r} />
                : di % 3 === 1
                  ? <rect {...common} x={cx - r} y={cy - r} width={2 * r} height={2 * r} transform={`rotate(45 ${cx} ${cy})`} />
                  : <polygon {...common} points={`${cx},${cy - r * 1.2} ${cx + r * 1.1},${cy + r} ${cx - r * 1.1},${cy + r}`} />;
              return <g key={point.rowId}>{shape}<title>{`${dataset.label}: ${point.power_W} W, ${point.speed_mm_s} mm/s (measured geometry)`}</title></g>;
            })}
          </g>
        ))}
        <g fontSize="11" fill="#cbd5e1" aria-hidden="true">
          {speeds_mm_s.map((v, iV) => iV % tickEvery(nV) === 0 && (
            <text key={`vx${iV}`} x={x(iV)} y={M.top + PLOT_H + 16} textAnchor="middle">{v}</text>
          ))}
          {powers_W.map((p, iP) => iP % tickEvery(nP) === 0 && (
            <text key={`py${iP}`} x={M.left - 8} y={y(iP) + 4} textAnchor="end">{p}</text>
          ))}
          <text x={M.left + PLOT_W / 2} y={M.top + PLOT_H + 42} textAnchor="middle" fontSize="12" fill="#e2e8f0">Scan speed v (mm/s)</text>
          <text transform={`translate(16 ${M.top + PLOT_H / 2}) rotate(-90)`} textAnchor="middle" fontSize="12" fill="#e2e8f0">Laser power P (W)</text>
        </g>
      </svg>
    </div>
  );
};

// ---------------------------------------------------------------------------------------------------------
// Detail panel, tables
// ---------------------------------------------------------------------------------------------------------
const gateList = (gates: string[]): string => (gates.length ? gates.join(", ") : "none");

export const ProcessWindowCellDetail: React.FC<{
  cell: LpbfProcessWindowCell | null;
  advisories: LpbfProcessWindowResponse["gridAdvisories"];
  /** Alloy, engine model and beam of the result the cell belongs to, so the published-track error of the selected cell can be printed. */
  bandContext?: { alloyId: string; modelId: string | null | undefined; beamDiameter_um: number } | null;
  bandSummary?: ErrorBandsSummary | null;
}> = ({ cell, advisories, bandContext = null, bandSummary = COMMITTED_ERROR_BANDS }) => {
  if (!cell) {
    return <p data-testid="pw-detail-empty" className="text-sm text-slate-400">Select a cell (click it, or Tab to the grid and use the arrow keys) to see its gates and reasons.</p>;
  }
  const style = verdictStyle(cell.verdict);
  const gateSentences = cellGateSentences(cell, bandContext?.alloyId);
  return (
    <div data-testid="pw-detail" aria-live="polite" className="space-y-2 text-sm text-slate-300">
      <h3 className="flex items-center gap-2 font-semibold text-slate-100">
        <span className="inline-flex h-6 w-6 items-center justify-center rounded border text-xs font-bold" style={{ background: style.hatched ? "#475569" : style.fill === "none" ? "transparent" : style.fill, color: style.textColor, borderColor: style.stroke, borderStyle: style.outlined ? "dashed" : "solid" }} aria-hidden="true">{style.letter}</span>
        {style.label}: {cell.power_W} W, {cell.speed_mm_s} mm/s
      </h3>
      {cell.verdict === "error" ? (
        <p role="alert" className="rounded border border-rose-500/40 bg-rose-500/10 p-2 text-rose-200" data-testid="pw-detail-error">
          The solver raised an error for this cell: {cell.error}. No verdict exists for it.
        </p>
      ) : (
        <>
          <p data-testid="pw-detail-headline">{cell.headline}</p>
          {gateSentences.length > 0 && (
            <ul className="list-disc space-y-1 pl-5 text-xs text-slate-200" data-testid="pw-detail-gate-sentences" aria-label="Why this verdict">{gateSentences.map(sentence => <li key={sentence}>{sentence}</li>)}</ul>
          )}
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
            <dt className="text-slate-500">Dominant gate</dt><dd className="font-mono">{cell.dominantGate ?? "none"}</dd>
            <dt className="text-slate-500">Failing gates (do-not-print)</dt><dd className="font-mono">{gateList(cell.blockingGates)}</dd>
            <dt className="text-slate-500">Risk gates (risky)</dt><dd className="font-mono">{gateList(cell.riskGates)}</dd>
            <dt className="text-slate-500">Advisory gates (no verdict effect)</dt><dd className="font-mono">{gateList(cell.advisoryGates)}</dd>
            <dt className="text-slate-500">Unavailable gates</dt><dd className="font-mono">{gateList(cell.unavailableGates)}</dd>
            <dt className="text-slate-500">Melt-pool extent</dt><dd className="font-mono">{cell.extentStatus}</dd>
            <dt className="text-slate-500">Width / depth (µm)</dt>
            <dd className="font-mono" data-testid="pw-detail-wd" title={[exactTitle(cell.width_um, "µm"), exactTitle(cell.depth_um, "µm")].filter(Boolean).join(" / ") || undefined}>{cell.width_um === null ? "not computed" : fmt(cell.width_um)} / {cell.depth_um === null ? "not computed" : fmt(cell.depth_um)}</dd>
            <dt className="text-slate-500">Normalised enthalpy</dt><dd className="font-mono">{cell.normalizedEnthalpy ?? "not reported"}</dd>
            <dt className="text-slate-500">Balling band</dt><dd className="font-mono">{cell.ballingBand ?? "not available"}</dd>
            <dt className="text-slate-500">Inside literature P-v box</dt><dd className="font-mono">{cell.insideLiteratureBox ? "yes" : "no"}</dd>
          </dl>
          {bandContext && <PublishedTrackBands subject={bandSubjectFromProcessWindowCell(cell, bandContext)} summary={bandSummary} testIdPrefix="pw-band" />}
          {cell.reasons.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400">Reasons (verbatim from the engine)</p>
              <ul className="list-disc space-y-1 pl-5 text-xs" data-testid="pw-detail-reasons">{cell.reasons.map((reason, i) => <li key={i}>{reason}</li>)}</ul>
            </div>
          )}
        </>
      )}
      {advisories.length > 0 && (
        <div className="border-t border-slate-800 pt-2 text-xs text-slate-400" data-testid="pw-grid-advisories">
          <p className="font-semibold">Advisory in every cell of this grid (not shown per cell)</p>
          <ul className="list-disc pl-5">{advisories.map(a => <li key={a.gate}><span className="font-mono">{a.gate}</span>: {a.note}</li>)}</ul>
        </div>
      )}
    </div>
  );
};

export const ProcessWindowTable: React.FC<{ result: LpbfProcessWindowResponse }> = ({ result }) => (
  <details className="rounded-lg border border-slate-800 bg-slate-900/40 p-3" data-testid="pw-table-fallback">
    <summary className="cursor-pointer text-sm font-semibold text-slate-200">Table view of all {result.cells.length} cells</summary>
    <div className="mt-2 max-h-96 overflow-auto" tabIndex={0} role="region" aria-label="All process window cells (scrollable)">
      <table className="w-full whitespace-nowrap text-xs text-slate-300 [&_td]:pr-3 [&_th]:pr-3">
        <caption className="sr-only">Screening verdict for every power and speed combination of the grid</caption>
        <thead className="text-left text-slate-500">
          <tr><th scope="col">P (W)</th><th scope="col">v (mm/s)</th><th scope="col">Verdict</th><th scope="col">Dominant gate</th><th scope="col">Extent</th><th scope="col">Width (µm)</th><th scope="col">Depth (µm)</th><th scope="col">Normalised enthalpy</th></tr>
        </thead>
        <tbody>
          {result.cells.map(cell => {
            const style = verdictStyle(cell.verdict);
            return (
              <tr key={`${cell.iP}-${cell.iV}`} className="border-t border-slate-800" data-testid="pw-table-row" data-verdict={cell.verdict}>
                <td className="font-mono">{cell.power_W}</td><td className="font-mono">{cell.speed_mm_s}</td>
                <td><span className="font-mono">{style.letter}</span> {style.label}{cell.error ? `: ${cell.error}` : ""}</td>
                <td className="font-mono">{cell.dominantGate ?? "none"}</td>
                <td className="font-mono">{cell.extentStatus ?? "n/a"}</td>
                <td className="font-mono" title={exactTitle(cell.width_um, "µm")}>{cell.width_um === null ? "not computed" : fmt(cell.width_um)}</td>
                <td className="font-mono" title={exactTitle(cell.depth_um, "µm")}>{cell.depth_um === null ? "not computed" : fmt(cell.depth_um)}</td>
                <td className="font-mono">{cell.normalizedEnthalpy ?? "n/a"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  </details>
);

const DatasetNotes: React.FC<{ dataset: LpbfProcessWindowDataset; tolerancePct: number }> = ({ dataset, tolerancePct }) => (
  <li data-testid={`pw-dataset-${dataset.id}`} className="space-y-0.5">
    <p className="font-semibold text-slate-200">{dataset.label}</p>
    {dataset.status === "unavailable" ? (
      <p role="alert" className="text-amber-300" data-testid="pw-dataset-unavailable">Unavailable: {dataset.reason}. The map above is unaffected.</p>
    ) : (
      <p>
        {dataset.nRows} rows: {dataset.nShown} shown, {dataset.hiddenByBeam} hidden by the beam-diameter filter (outside {"±"}{tolerancePct} % of the request),
        {" "}{dataset.hiddenOutsideRange} outside the mapped P/v range{dataset.hiddenNoBeam ? `, ${dataset.hiddenNoBeam} without a beam diameter` : ""}.
        {dataset.doi ? <> DOI <span className="font-mono">{dataset.doi}</span>.</> : null}
      </p>
    )}
    {dataset.caveats && dataset.caveats.length > 0 && (
      <details className="text-slate-400"><summary className="cursor-pointer">Dataset caveats ({dataset.caveats.length})</summary>
        <ul className="list-disc pl-5">{dataset.caveats.map((c, i) => <li key={i}>{c}</li>)}</ul></details>
    )}
  </li>
);

export const ProcessWindowMeasurements: React.FC<{ result: LpbfProcessWindowResponse }> = ({ result }) => {
  const rows = result.overlay.datasets.flatMap(dataset => dataset.points.map(point => ({ dataset, point })));
  return (
    <section data-testid="pw-measurements" aria-label="Measurement overlay" className="space-y-2 rounded-lg border border-slate-800 bg-slate-900/40 p-3">
      <h3 className="text-sm font-semibold text-slate-200">Measurements (geometry, not print outcomes)</h3>
      <p className="text-xs text-slate-400">
        Published single-track width and depth, filtered to a beam diameter within {"±"}{result.overlay.beamTolerance_pct} % of {result.request.beamDiameter_um}{THIN_SPACE}µm
        ({result.overlay.beamWindow_um[0]}-{result.overlay.beamWindow_um[1]}{THIN_SPACE}µm). The model verdict is computed at each point{"'"}s P/v with this request{"'"}s beam, layer, hatch and preheat, not at the experiment{"'"}s own layer and preheat.
      </p>
      {result.overlay.note && <p className="text-xs text-amber-300" data-testid="pw-overlay-note">{result.overlay.note}</p>}
      <ul className="space-y-2 text-xs text-slate-400">{result.overlay.datasets.map(d => <DatasetNotes key={d.id} dataset={d} tolerancePct={result.overlay.beamTolerance_pct} />)}</ul>
      {rows.length > 0 ? (
        <div className="max-h-80 overflow-auto" tabIndex={0} role="region" aria-label="Measurement points (scrollable)">
          <table className="w-full whitespace-nowrap text-xs text-slate-300 [&_td]:pr-3 [&_th]:pr-3">
            <caption className="sr-only">Published single-track measurements inside the mapped range with the model verdict at their P and v</caption>
            <thead className="text-left text-slate-500">
              <tr><th scope="col">Dataset</th><th scope="col">Row</th><th scope="col">P (W)</th><th scope="col">v (mm/s)</th><th scope="col">Beam (µm)</th><th scope="col">Measured width (µm)</th><th scope="col">Measured depth (µm)</th><th scope="col">Model verdict here</th><th scope="col">Model width / depth (µm)</th></tr>
            </thead>
            <tbody>
              {rows.map(({ dataset, point }) => (
                <tr key={`${dataset.id}-${point.rowId}`} className="border-t border-slate-800" data-testid="pw-measurement-row">
                  <td>{dataset.id}</td><td className="font-mono">{point.rowId}</td>
                  <td className="font-mono">{point.power_W}</td><td className="font-mono">{point.speed_mm_s}</td>
                  <td className="font-mono">{point.beamDiameter_um ?? "n/a"}</td>
                  <td className="font-mono" title={exactTitle(point.measuredWidth_um, "µm")}>{point.measuredWidth_um === null ? "not available" : fmt(point.measuredWidth_um)}</td>
                  <td className="font-mono" title={exactTitle(point.measuredDepth_um, "µm")}>{point.measuredDepth_um === null ? "not available" : fmt(point.measuredDepth_um)}</td>
                  <td><span className="font-mono">{verdictStyle(point.modelVerdict.verdict).letter}</span> {verdictStyle(point.modelVerdict.verdict).label}</td>
                  <td className="font-mono">{point.modelVerdict.modelWidth_um === null ? "not computed" : fmt(point.modelVerdict.modelWidth_um)} / {point.modelVerdict.modelDepth_um === null ? "not computed" : fmt(point.modelVerdict.modelDepth_um)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-xs text-slate-400" data-testid="pw-no-measurements">No measurement point falls inside this map and beam window.</p>
      )}
    </section>
  );
};

// ---------------------------------------------------------------------------------------------------------
// Status line for a displayed result
// ---------------------------------------------------------------------------------------------------------
export const ProcessWindowResultStatus: React.FC<{ result: LpbfProcessWindowResponse; source: ProcessWindowSource; stale: boolean }> = ({ result, source, stale }) => (
  <div className="space-y-1" data-testid="pw-result-status">
    {stale && (
      <p role="status" data-testid="pw-stale" className="rounded border border-amber-500/40 bg-amber-500/10 p-2 text-xs text-amber-200">
        The inputs have changed since this map was computed. The map shows the old inputs (dimmed) and may not match the form. Press Compute to update it.
      </p>
    )}
    {source === "engine-cache" && (
      <p role="status" data-testid="pw-cache-engine" className="text-xs text-sky-300">
        Served from the engine cache (per Python worker process): an identical request, solver revision and implementation hash was already computed
        {result.originalComputeMs != null ? ` (${result.originalComputeMs} ms originally)` : ""}; nothing was recomputed.
      </p>
    )}
    {source === "browser-memo" && (
      <p role="status" data-testid="pw-cache-memo" className="text-xs text-sky-300">
        Reused from this browser session: the inputs are identical to an earlier Compute, so no request was sent.
      </p>
    )}
    {source === "computed" && IS_STATIC_DEMO && <p className="text-xs text-slate-400" data-testid="pw-computed">Recorded snapshot ({result.grid.nCells} cells); compute time not recorded.</p>}
    {source === "computed" && !IS_STATIC_DEMO && <p className="text-xs text-slate-400" data-testid="pw-computed">Computed in {result.computeMs} ms ({result.grid.nCells} cells).</p>}
  </div>
);

// ---------------------------------------------------------------------------------------------------------
// Result view: everything below the inputs for one response
// ---------------------------------------------------------------------------------------------------------
export interface ProcessWindowResultViewProps {
  result: LpbfProcessWindowResponse;
  selected: CellPosition | null;
  onSelect?: (position: CellPosition) => void;
  current?: { power_W: number; speed_mm_s: number } | null;
  source?: ProcessWindowSource;
  stale?: boolean;
}

export const ProcessWindowResultView: React.FC<ProcessWindowResultViewProps> = ({ result, selected, onSelect, current, source = "computed", stale = false }) => {
  const basis = result.grid.rangeBasis;
  const cell = selected ? cellAt(result, selected.iP, selected.iV) : null;
  const noPrintableNote = noPrintableNoteText(result);
  const crosshairOutside = !!current
    && (axisFraction(result.grid.speeds_mm_s, current.speed_mm_s) === null || axisFraction(result.grid.powers_W, current.power_W) === null);
  return (
    <div className="space-y-4" data-testid="pw-result">
      <ProcessWindowResultStatus result={result} source={source} stale={stale} />
      <p className="text-xs text-slate-400" data-testid="pw-range-basis">
        Range: P {basis.power.min_W}-{basis.power.max_W} W ({basis.power.n} points, {basis.power.basis === "default" ? basis.power.rule : "requested"}); v {basis.speed.min_mm_s}-{basis.speed.max_mm_s} mm/s
        ({basis.speed.n} points, {basis.speed.basis === "default" ? basis.speed.rule : "requested"}). Alloy {result.alloyId}, beam {result.request.beamDiameter_um}{THIN_SPACE}µm, layer {result.request.layer_um}{THIN_SPACE}µm, hatch {result.request.hatch_um}{THIN_SPACE}µm, preheat {result.request.preheatTemp_C}{THIN_SPACE}°C.
      </p>
      {noPrintableNote && <p role="status" data-testid="pw-no-printable-note" className="rounded border border-amber-500/40 bg-amber-500/10 p-2 text-xs text-amber-100">{noPrintableNote}</p>}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="space-y-3">
          <ProcessWindowHeatmap result={result} selected={selected} onSelect={onSelect} current={current} stale={stale} />
          {crosshairOutside && current ? (
            <p className="text-xs text-slate-400" data-testid="pw-crosshair-outside">The current specimen P/v ({current.power_W} W, {current.speed_mm_s} mm/s) is outside the mapped range, so no cross-hair is drawn.</p>
          ) : null}
          <ProcessWindowLegend result={result} />
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
          <ProcessWindowCellDetail cell={cell} advisories={result.gridAdvisories}
            bandContext={{ alloyId: result.alloyId, modelId: result.provenance.modelId, beamDiameter_um: result.request.beamDiameter_um }} />
        </div>
      </div>
      <ProcessWindowTable result={result} />
      <ProcessWindowMeasurements result={result} />
    </div>
  );
};

// ---------------------------------------------------------------------------------------------------------
// Container
// ---------------------------------------------------------------------------------------------------------
export type ProcessWindowPhase =
  | { kind: "idle" }
  | { kind: "loading"; cells: number }
  | { kind: "ready"; result: LpbfProcessWindowResponse; source: ProcessWindowSource }
  | { kind: "refused"; message: string }
  | { kind: "unavailable"; message: string }
  | { kind: "invalid"; message: string };

export const ProcessWindowPhaseNotice: React.FC<{ phase: ProcessWindowPhase; alloySupported: boolean }> = ({ phase, alloySupported }) => (
  <>
    <div aria-live="polite">
      {phase.kind === "idle" && alloySupported && <p className="text-sm text-slate-400" data-testid="pw-idle">No map yet. Review the inputs and press Compute.</p>}
      {phase.kind === "loading" && (
        <p role="status" data-testid="pw-loading" className="flex items-center gap-2 text-sm text-slate-300">
          <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />Computing {phase.cells} cells (typically about {Math.max(1, Math.round((phase.cells * PROCESS_WINDOW_MS_PER_CELL) / 1000))} s plus the overlay)...
        </p>
      )}
    </div>
    {phase.kind === "unavailable" && (
      <div role="alert" data-testid="pw-unavailable" className="flex items-start gap-3 rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
        <AlertTriangle className="h-5 w-5 shrink-0" aria-hidden="true" />
        <p>Engine unavailable: {phase.message}. No map is shown; nothing was estimated in the browser.</p>
      </div>
    )}
    {phase.kind === "refused" && (
      <div role="alert" data-testid="pw-refusal" className="flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
        <Info className="h-5 w-5 shrink-0" aria-hidden="true" />
        <p>The engine refused this request: {phase.message}{/[.!?]$/.test(phase.message) ? "" : "."} Nothing was clamped or substituted.</p>
      </div>
    )}
    {phase.kind === "invalid" && (
      <div role="alert" data-testid="pw-invalid" className="flex items-start gap-3 rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
        <AlertTriangle className="h-5 w-5 shrink-0" aria-hidden="true" />
        <p>The engine response failed validation and is not shown: {phase.message}</p>
      </div>
    )}
  </>
);

export const ProcessWindowUnsupportedAlloy: React.FC<{ reason: string | null }> = ({ reason }) => (
  <p role="alert" data-testid="pw-unsupported-alloy" className="rounded border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-200">
    Unsupported alloy: {reason} No map can be computed for this material.
  </p>
);

export function openMaterialAndParameters(): void {
  try {
    const url = new URL(window.location.href);
    url.searchParams.set("lpbfStage", "material");
    url.searchParams.delete("lpbfSubTab");
    window.history.replaceState(null, "", url);
  } catch { /* navigation below still works without the URL hint */ }
  window.dispatchEvent(new CustomEvent("metallix-navigate-tab", { detail: { tabId: "3d-distortion-lab", lpbfStage: "material" } }));
}

const textFrom = (n: number) => String(n);

export const LpbfProcessWindowMap: React.FC = () => {
  const specimen = useMaterialSpecimenStore(s => s.activeSpecimen);
  const alloy = resolveOptimizerAlloy(specimen.name);
  const lpbf = specimen.lpbf;
  const box = alloy.ok && alloy.alloyKey ? LITERATURE_PV_WINDOWS[alloy.alloyKey] : null;

  const [pMin, setPMin] = useState("");
  const [pMax, setPMax] = useState("");
  const [pN, setPN] = useState(textFrom(PROCESS_WINDOW_DEFAULT_AXIS));
  const [vMin, setVMin] = useState("");
  const [vMax, setVMax] = useState("");
  const [vN, setVN] = useState(textFrom(PROCESS_WINDOW_DEFAULT_AXIS));
  const [phase, setPhase] = useState<ProcessWindowPhase>({ kind: "idle" });
  const [selected, setSelected] = useState<CellPosition | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // The default range follows the alloy (0.5 x literature-box minimum to 1.5 x maximum); editing is free afterwards.
  useEffect(() => {
    if (!box) return;
    const p = defaultAxisRange({ min: box.powerMin_W, max: box.powerMax_W });
    const v = defaultAxisRange({ min: box.speedMin_mm_s, max: box.speedMax_mm_s });
    setPMin(String(p.min)); setPMax(String(p.max)); setVMin(String(v.min)); setVMax(String(v.max));
  }, [alloy.alloyKey]);
  useEffect(() => () => abortRef.current?.abort(), []);

  const powerAxis = parseAxis(pMin, pMax, pN, "Power", "W", PROCESS_WINDOW_MAX_POWER_W);
  const speedAxis = parseAxis(vMin, vMax, vN, "Speed", "mm/s", PROCESS_WINDOW_MAX_SPEED_MM_S);
  const defP = box ? defaultAxisRange({ min: box.powerMin_W, max: box.powerMax_W }) : null;
  const defV = box ? defaultAxisRange({ min: box.speedMin_mm_s, max: box.speedMax_mm_s }) : null;
  const powersAreDefault = !!defP && powerAxis.ok && Number(pMin) === defP.min && Number(pMax) === defP.max && Number(pN) === PROCESS_WINDOW_DEFAULT_AXIS;
  const speedsAreDefault = !!defV && speedAxis.ok && Number(vMin) === defV.min && Number(vMax) === defV.max && Number(vN) === PROCESS_WINDOW_DEFAULT_AXIS;
  const processProblems: string[] = [];
  const positive = (value: number, name: string) => { if (!(Number.isFinite(value) && value > 0)) processProblems.push(`${name} must be a positive number (Material & Parameters).`); };
  positive(lpbf.beamDiameter_um, "Beam diameter");
  positive(lpbf.layer_um, "Layer thickness");
  positive(lpbf.hatch_um, "Hatch spacing");
  if (!(Number.isFinite(lpbf.preheatTemp_C) && lpbf.preheatTemp_C >= 0)) processProblems.push("Preheat must be a number, 0 C or higher (Material & Parameters).");
  const axisProblems = [powerAxis, speedAxis].flatMap(a => (a.ok || a.reason === null ? [] : [a.reason]));
  const cellCount = powerAxis.ok && speedAxis.ok ? powerAxis.values.length * speedAxis.values.length : 0;
  if (cellCount > PROCESS_WINDOW_MAX_CELLS) axisProblems.push(`At most ${PROCESS_WINDOW_MAX_CELLS} cells are allowed.`);
  const problems = alloy.ok ? [...processProblems, ...axisProblems] : [];

  const currentInputs: ProcessWindowInputs | null =
    alloy.ok && alloy.alloyKey && problems.length === 0 && powerAxis.ok && speedAxis.ok
      ? {
          alloyId: alloy.alloyKey, beamDiameter_um: lpbf.beamDiameter_um, layer_um: lpbf.layer_um, hatch_um: lpbf.hatch_um,
          preheatTemp_C: lpbf.preheatTemp_C, powers: powerAxis.values, speeds: speedAxis.values,
          overlayBeamTolerance_pct: PROCESS_WINDOW_BEAM_TOLERANCE_PCT,
        }
      : null;

  const compute = async () => {
    if (!currentInputs) return;
    abortRef.current?.abort();
    const key = inputsKey(currentInputs);
    const remembered = memoGet(key);
    if (remembered) {
      setSelected(null);
      setPhase({ kind: "ready", result: remembered, source: "browser-memo" });
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    setSelected(null);
    setPhase({ kind: "loading", cells: currentInputs.powers.length * currentInputs.speeds.length });
    try {
      const raw = await pythonComputationService.runLpbfProcessWindow({
        alloyId: currentInputs.alloyId, beamDiameter_um: currentInputs.beamDiameter_um, layer_um: currentInputs.layer_um,
        hatch_um: currentInputs.hatch_um, preheatTemp_C: currentInputs.preheatTemp_C,
        // Axes still holding the alloy default are omitted so the engine reports its own default rule.
        ...(powersAreDefault ? {} : { powers: currentInputs.powers }),
        ...(speedsAreDefault ? {} : { speeds: currentInputs.speeds }),
        overlayBeamTolerance_pct: currentInputs.overlayBeamTolerance_pct,
      }, controller.signal);
      let result: LpbfProcessWindowResponse;
      try {
        result = checkedProcessWindow(raw);
      } catch (err) {
        setPhase({ kind: "invalid", message: err instanceof Error ? err.message : "The engine response failed validation." });
        return;
      }
      memoSet(key, result);
      setPhase({ kind: "ready", result, source: result.cache.hit ? "engine-cache" : "computed" });
    } catch (err) {
      if (controller.signal.aborted) return;
      if (err instanceof LpbfProcessWindowRequestError && err.kind === "validation") setPhase({ kind: "refused", message: err.message });
      else setPhase({ kind: "unavailable", message: err instanceof Error ? err.message : "The engine did not answer." });
    }
  };

  const result = phase.kind === "ready" ? phase.result : null;
  const stale = isStale(result, currentInputs);
  const current = Number.isFinite(lpbf.laserPower_W) && Number.isFinite(lpbf.scanSpeed_mms) ? { power_W: lpbf.laserPower_W, speed_mm_s: lpbf.scanSpeed_mms } : null;
  const defaulted = (key: string) => (lpbf.defaultsApplied as readonly string[] | undefined)?.includes(key) ?? false;
  const loading = phase.kind === "loading";
  const blocked = !currentInputs;
  const input = "aero-input w-full";

  return (
    <div className="space-y-4" data-testid="pw-root">
      <div>
        <h2 className="flex items-center gap-2 text-xl font-bold text-slate-100"><Grid3x3 className="h-5 w-5 text-sky-400" aria-hidden="true" />Process-window map</h2>
        <p className="mt-1 text-sm text-slate-400">
          Screening verdict of the frozen melt-pool model on a power x speed grid, with published single-track measurements overlaid. Nothing is computed until you press Compute.
        </p>
      </div>

      <ProcessWindowHonestyBanner provenance={result?.provenance ?? null} />

      {!alloy.ok && <ProcessWindowUnsupportedAlloy reason={alloy.reason} />}

      <div className="grid gap-4 lg:grid-cols-3">
        <section aria-label="Fixed process inputs" className="space-y-2 rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-sm">
          <h3 className="font-semibold text-slate-200">From the active specimen (read-only)</h3>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-300" data-testid="pw-fixed-inputs">
            <dt className="text-slate-500">Alloy</dt>
            <dd className="font-mono" data-testid="pw-alloy">{alloy.ok ? alloy.alloyKey : "unsupported"} <span className="text-slate-500">({specimen.name})</span></dd>
            <dt className="text-slate-500">Beam diameter</dt><dd className="font-mono">{lpbf.beamDiameter_um}{THIN_SPACE}µm{defaulted("beamDiameter_um") ? " (default, not specified)" : ""}</dd>
            <dt className="text-slate-500">Layer thickness</dt><dd className="font-mono">{lpbf.layer_um}{THIN_SPACE}µm{defaulted("layer_um") ? " (default, not specified)" : ""}</dd>
            <dt className="text-slate-500">Hatch spacing</dt><dd className="font-mono">{lpbf.hatch_um}{THIN_SPACE}µm{defaulted("hatch_um") ? " (default, not specified)" : ""}</dd>
            <dt className="text-slate-500">Preheat</dt><dd className="font-mono">{lpbf.preheatTemp_C}{THIN_SPACE}°C{defaulted("preheatTemp_C") ? " (default, not specified)" : ""}</dd>
            <dt className="text-slate-500">Overlay beam tolerance</dt><dd className="font-mono">{"±"}{PROCESS_WINDOW_BEAM_TOLERANCE_PCT} %</dd>
          </dl>
          <button type="button" onClick={openMaterialAndParameters} className="text-xs text-sky-300 underline" data-testid="pw-open-material">Change these in Material &amp; Parameters</button>
        </section>

        <section aria-label="Grid range" className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-sm lg:col-span-2">
          <h3 className="font-semibold text-slate-200">Grid</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <fieldset className="space-y-1">
              <legend className="mb-1 text-slate-400">Laser power (W)</legend>
              <div className="flex gap-2">
                <input {...lock} aria-label="Power minimum (W)" type="number" inputMode="decimal" value={pMin} onChange={e => setPMin(e.target.value)} className={input} />
                <input {...lock} aria-label="Power maximum (W)" type="number" inputMode="decimal" value={pMax} onChange={e => setPMax(e.target.value)} className={input} />
                <input {...lock} aria-label="Power points" type="number" min={2} max={15} value={pN} onChange={e => setPN(e.target.value)} className="aero-input w-20" />
              </div>
            </fieldset>
            <fieldset className="space-y-1">
              <legend className="mb-1 text-slate-400">Scan speed (mm/s)</legend>
              <div className="flex gap-2">
                <input {...lock} aria-label="Speed minimum (mm/s)" type="number" inputMode="decimal" value={vMin} onChange={e => setVMin(e.target.value)} className={input} />
                <input {...lock} aria-label="Speed maximum (mm/s)" type="number" inputMode="decimal" value={vMax} onChange={e => setVMax(e.target.value)} className={input} />
                <input {...lock} aria-label="Speed points" type="number" min={2} max={15} value={vN} onChange={e => setVN(e.target.value)} className="aero-input w-20" />
              </div>
            </fieldset>
          </div>
          <p className="text-xs text-slate-500">
            Each axis: minimum, maximum, number of points (2-15). The default range is 0.5 x the literature-box minimum to 1.5 x its maximum for this alloy. At most {PROCESS_WINDOW_MAX_CELLS} cells; about {PROCESS_WINDOW_MS_PER_CELL} ms per cell was measured.
          </p>
          {problems.length > 0 && <ul role="alert" className="list-disc pl-5 text-xs text-amber-300" data-testid="pw-input-problems">{problems.map((p, i) => <li key={i}>{p}</li>)}</ul>}
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button" onClick={compute} disabled={blocked || loading} data-testid="pw-compute"
              className="flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500 disabled:opacity-50"
            >
              {loading ? <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Grid3x3 className="h-4 w-4" aria-hidden="true" />}
              Compute
            </button>
            {cellCount > 0 && <span className="text-xs text-slate-400">{cellCount} cells</span>}
          </div>
        </section>
      </div>

      <ProcessWindowPhaseNotice phase={phase} alloySupported={alloy.ok} />
      {phase.kind === "ready" && (
        <ProcessWindowResultView result={phase.result} selected={selected} onSelect={setSelected} current={current} source={phase.source} stale={stale} />
      )}
    </div>
  );
};

