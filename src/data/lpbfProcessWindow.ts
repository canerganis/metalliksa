/**
 * Pure helpers for the LPBF process-window map (python/lpbf_process_window.py is the result authority).
 *
 * This module validates the shape and honesty flags of the engine response and provides view helpers (verdict
 * styling, keyboard grid movement, stale detection, a small client memo). It computes no physics: every verdict,
 * gate, width and depth shown by the view is read from the response. Screening only, not validation.
 */
import type {
  LpbfProcessWindowCell,
  LpbfProcessWindowCellVerdict,
  LpbfProcessWindowResponse,
} from "../services/pythonComputationService";

export const PROCESS_WINDOW_MIN_AXIS = 2;
export const PROCESS_WINDOW_MAX_AXIS = 15;
export const PROCESS_WINDOW_DEFAULT_AXIS = 11;
export const PROCESS_WINDOW_MAX_CELLS = 225;
export const PROCESS_WINDOW_MAX_POWER_W = 1500;
export const PROCESS_WINDOW_MAX_SPEED_MM_S = 10000;
export const PROCESS_WINDOW_BEAM_TOLERANCE_PCT = 10;
/** Measured by the engine lane: about 20 ms per cell (frozen screening model plus compose_verdict). */
export const PROCESS_WINDOW_MS_PER_CELL = 20;
export const PROCESS_WINDOW_DEFAULT_LOW_FACTOR = 0.5;
export const PROCESS_WINDOW_DEFAULT_HIGH_FACTOR = 1.5;

export const PROCESS_WINDOW_CELL_VERDICTS: readonly LpbfProcessWindowCellVerdict[] = [
  "printable", "risky", "do-not-print", "inconclusive", "error",
];

// ---------------------------------------------------------------------------------------------------------
// Verdict styling. Only "printable" may look printable (green + P); inconclusive is hatched grey, error is an
// outlined empty cell, so an unresolved or failed cell can never be mistaken for a printable one.
// ---------------------------------------------------------------------------------------------------------
export interface VerdictStyle {
  readonly verdict: LpbfProcessWindowCellVerdict;
  readonly letter: string;
  readonly label: string;
  readonly fill: string;
  readonly stroke: string;
  readonly textColor: string;
  readonly hatched: boolean;
  readonly outlined: boolean;
  readonly printableLooking: boolean;
}

export const HATCH_PATTERN_ID = "pw-hatch";

const STYLES: Record<LpbfProcessWindowCellVerdict, VerdictStyle> = {
  printable: { verdict: "printable", letter: "P", label: "Printable", fill: "#166534", stroke: "#052e16", textColor: "#dcfce7", hatched: false, outlined: false, printableLooking: true },
  risky: { verdict: "risky", letter: "R", label: "Risky", fill: "#b45309", stroke: "#451a03", textColor: "#fffbeb", hatched: false, outlined: false, printableLooking: false },
  "do-not-print": { verdict: "do-not-print", letter: "X", label: "Do not print", fill: "#991b1b", stroke: "#450a0a", textColor: "#fee2e2", hatched: false, outlined: false, printableLooking: false },
  inconclusive: { verdict: "inconclusive", letter: "?", label: "Inconclusive (geometry not resolved)", fill: "#475569", stroke: "#94a3b8", textColor: "#e2e8f0", hatched: true, outlined: false, printableLooking: false },
  error: { verdict: "error", letter: "!", label: "Solver error", fill: "none", stroke: "#fb7185", textColor: "#fda4af", hatched: false, outlined: true, printableLooking: false },
};

export function verdictStyle(verdict: string): VerdictStyle {
  const style = (STYLES as Record<string, VerdictStyle>)[verdict];
  if (!style) throw new Error(`unknown process-window verdict ${JSON.stringify(verdict)}`);
  return style;
}

// ---------------------------------------------------------------------------------------------------------
// Keyboard movement on the P x v grid. Rows are power (iP, drawn bottom to top), columns are speed (iV).
// ---------------------------------------------------------------------------------------------------------
export interface CellPosition { iP: number; iV: number }

/** Arrow keys move one cell (no wrap), Home/End jump to the first/last speed, PageUp/PageDown to the highest/lowest power. */
export function moveCell(current: CellPosition, key: string, nP: number, nV: number): CellPosition {
  const clamp = (value: number, max: number) => Math.min(Math.max(value, 0), max - 1);
  const { iP, iV } = current;
  switch (key) {
    case "ArrowRight": return { iP, iV: clamp(iV + 1, nV) };
    case "ArrowLeft": return { iP, iV: clamp(iV - 1, nV) };
    case "ArrowUp": return { iP: clamp(iP + 1, nP), iV };
    case "ArrowDown": return { iP: clamp(iP - 1, nP), iV };
    case "Home": return { iP, iV: 0 };
    case "End": return { iP, iV: nV - 1 };
    case "PageUp": return { iP: nP - 1, iV };
    case "PageDown": return { iP: 0, iV };
    default: return { iP: clamp(iP, nP), iV: clamp(iV, nV) };
  }
}

/** Fractional cell index of a value on an axis (cell centres at integer indices, edges at -0.5 and n-0.5), or null when it is off the map. */
export function axisFraction(values: readonly number[], x: number): number | null {
  const n = values.length;
  if (n < 2 || !Number.isFinite(x)) return null;
  const lowEdge = values[0] - (values[1] - values[0]) / 2;
  const highEdge = values[n - 1] + (values[n - 1] - values[n - 2]) / 2;
  if (x < lowEdge || x > highEdge) return null;
  if (x <= values[0]) return -0.5 + (x - lowEdge) / (values[0] - lowEdge) * 0.5;
  if (x >= values[n - 1]) return n - 1 + (x - values[n - 1]) / (highEdge - values[n - 1]) * 0.5;
  for (let i = 0; i < n - 1; i++) {
    if (x >= values[i] && x <= values[i + 1]) return i + (x - values[i]) / (values[i + 1] - values[i]);
  }
  return null;
}

/** Clamp a box edge to the map: returns the fractional index, saturating at the map edge. */
export function axisFractionClamped(values: readonly number[], x: number): number {
  const n = values.length;
  const exact = axisFraction(values, x);
  if (exact !== null) return exact;
  return x < values[0] ? -0.5 : n - 0.5;
}

// ---------------------------------------------------------------------------------------------------------
// Inputs, axes and stale detection
// ---------------------------------------------------------------------------------------------------------
export interface ProcessWindowInputs {
  alloyId: string;
  beamDiameter_um: number;
  layer_um: number;
  hatch_um: number;
  preheatTemp_C: number;
  powers: number[];
  speeds: number[];
  overlayBeamTolerance_pct: number;
}

export function inputsKey(inputs: ProcessWindowInputs): string {
  return JSON.stringify([inputs.alloyId, inputs.beamDiameter_um, inputs.layer_um, inputs.hatch_um, inputs.preheatTemp_C,
    inputs.overlayBeamTolerance_pct, inputs.powers, inputs.speeds]);
}

/** The inputs the engine actually used, read from its echo (never from what the form currently shows). */
export function inputsFromResponse(response: LpbfProcessWindowResponse): ProcessWindowInputs {
  return {
    alloyId: response.request.alloyId,
    beamDiameter_um: response.request.beamDiameter_um,
    layer_um: response.request.layer_um,
    hatch_um: response.request.hatch_um,
    preheatTemp_C: response.request.preheatTemp_C,
    overlayBeamTolerance_pct: response.request.overlayBeamTolerance_pct,
    powers: [...response.grid.powers_W],
    speeds: [...response.grid.speeds_mm_s],
  };
}

/** True when the current form inputs differ from the inputs the displayed response was computed for. */
export function isStale(response: LpbfProcessWindowResponse | null, current: ProcessWindowInputs | null): boolean {
  if (!response) return false;
  if (!current) return true;
  return inputsKey(inputsFromResponse(response)) !== inputsKey(current);
}

export function linspace(min: number, max: number, n: number): number[] {
  return Array.from({ length: n }, (_, i) => Math.round((min + ((max - min) * i) / (n - 1)) * 100) / 100);
}

// Plain shape (not a discriminated union): the project tsconfig is not strict, so boolean discriminants do not narrow.
export interface AxisParse { ok: boolean; values: number[]; reason: string | null }

/** Build one axis from text fields. Mirrors the engine's limits so a request that would be refused is not sent. */
export function parseAxis(minText: string, maxText: string, nText: string, name: string, unit: string, cap: number): AxisParse {
  const num = (text: string) => (text.trim() === "" ? NaN : Number(text));
  const min = num(minText);
  const max = num(maxText);
  const n = num(nText);
  if (!Number.isFinite(min) || !Number.isFinite(max)) return { ok: false, values: [], reason: `${name} minimum and maximum must be numbers.` };
  if (!(min > 0)) return { ok: false, values: [], reason: `${name} minimum must be greater than 0 ${unit}.` };
  if (!(max > min)) return { ok: false, values: [], reason: `${name} maximum must be greater than the minimum.` };
  if (max > cap) return { ok: false, values: [], reason: `${name} maximum must be at most ${cap} ${unit}.` };
  if (!Number.isInteger(n) || n < PROCESS_WINDOW_MIN_AXIS || n > PROCESS_WINDOW_MAX_AXIS) {
    return { ok: false, values: [], reason: `${name} point count must be an integer from ${PROCESS_WINDOW_MIN_AXIS} to ${PROCESS_WINDOW_MAX_AXIS}.` };
  }
  const values = linspace(min, max, n);
  if (values.some((v, i) => i > 0 && v <= values[i - 1])) {
    return { ok: false, values: [], reason: `${name} range is too narrow for ${n} distinct points at 0.01 ${unit} resolution.` };
  }
  return { ok: true, values, reason: null };
}

export function defaultAxisRange(box: { min: number; max: number }): { min: number; max: number } {
  return {
    min: Math.round(box.min * PROCESS_WINDOW_DEFAULT_LOW_FACTOR * 100) / 100,
    max: Math.round(box.max * PROCESS_WINDOW_DEFAULT_HIGH_FACTOR * 100) / 100,
  };
}

// ---------------------------------------------------------------------------------------------------------
// Client memo: identical inputs reuse the last responses of this browser session (never persisted).
// ---------------------------------------------------------------------------------------------------------
const MEMO_MAX = 8;
const memo = new Map<string, LpbfProcessWindowResponse>();

export function memoGet(key: string): LpbfProcessWindowResponse | null {
  const hit = memo.get(key);
  if (!hit) return null;
  memo.delete(key);
  memo.set(key, hit);
  return hit;
}

export function memoSet(key: string, response: LpbfProcessWindowResponse): void {
  memo.delete(key);
  memo.set(key, response);
  while (memo.size > MEMO_MAX) memo.delete(memo.keys().next().value as string);
}

export function memoClear(): void { memo.clear(); }
export function memoSize(): number { return memo.size; }

// ---------------------------------------------------------------------------------------------------------
// Legend
// ---------------------------------------------------------------------------------------------------------
export interface LegendEntry { verdict: LpbfProcessWindowCellVerdict; count: number; style: VerdictStyle }

export function legendEntries(response: LpbfProcessWindowResponse): LegendEntry[] {
  return PROCESS_WINDOW_CELL_VERDICTS.map(verdict => ({ verdict, count: response.counts[verdict], style: verdictStyle(verdict) }));
}

export function cellAt(response: LpbfProcessWindowResponse, iP: number, iV: number): LpbfProcessWindowCell {
  return response.cells[iP * response.grid.nV + iV];
}

export function cellAriaLabel(cell: LpbfProcessWindowCell): string {
  const base = `Power ${cell.power_W} W, speed ${cell.speed_mm_s} mm/s: ${verdictStyle(cell.verdict).label}`;
  return cell.verdict === "error" ? `${base}: ${cell.error}` : base;
}

// ---------------------------------------------------------------------------------------------------------
// Response validator
// ---------------------------------------------------------------------------------------------------------
const fail = (reason: string): never => { throw new Error(`lpbf process window response rejected: ${reason}`); };
const isObject = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === "object" && !Array.isArray(v);
const isFiniteNumber = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const isNumberOrNull = (v: unknown) => v === null || isFiniteNumber(v);
const isStringArray = (v: unknown): v is string[] => Array.isArray(v) && v.every(x => typeof x === "string");

export function checkedProcessWindow(raw: unknown): LpbfProcessWindowResponse {
  if (!isObject(raw)) return fail("not an object");
  if (raw.success !== true) return fail("success is not true");
  const evidence = raw.evidence;
  if (!isObject(evidence)) return fail("missing evidence");
  if (evidence.kind !== "screening-only") return fail(`evidence.kind must be "screening-only" (got ${JSON.stringify(evidence.kind)})`);
  if (evidence.experimentalValidation !== false) return fail("evidence.experimentalValidation must be exactly false");
  if (typeof evidence.statement !== "string" || !evidence.statement) return fail("evidence.statement missing");
  const provenance = raw.provenance;
  if (!isObject(provenance)) return fail("missing provenance");
  for (const key of ["modelId", "solverRevision", "implementationHash"]) {
    if (typeof provenance[key] !== "string" || !provenance[key]) return fail(`provenance.${key} missing`);
  }
  if (provenance.absorptionModel !== null && typeof provenance.absorptionModel !== "string") return fail("provenance.absorptionModel invalid");
  const request = raw.request;
  if (!isObject(request) || typeof request.alloyId !== "string") return fail("missing request echo");
  for (const key of ["beamDiameter_um", "layer_um", "hatch_um", "preheatTemp_C", "overlayBeamTolerance_pct"]) {
    if (!isFiniteNumber(request[key])) return fail(`request.${key} is not a number`);
  }
  const grid = raw.grid;
  if (!isObject(grid)) return fail("missing grid");
  const powers = grid.powers_W;
  const speeds = grid.speeds_mm_s;
  if (!Array.isArray(powers) || !powers.every(isFiniteNumber)) return fail("grid.powers_W invalid");
  if (!Array.isArray(speeds) || !speeds.every(isFiniteNumber)) return fail("grid.speeds_mm_s invalid");
  const nP = powers.length;
  const nV = speeds.length;
  if (nP < PROCESS_WINDOW_MIN_AXIS || nP > PROCESS_WINDOW_MAX_AXIS || nV < PROCESS_WINDOW_MIN_AXIS || nV > PROCESS_WINDOW_MAX_AXIS) {
    return fail(`axis lengths ${nP} x ${nV} outside ${PROCESS_WINDOW_MIN_AXIS}..${PROCESS_WINDOW_MAX_AXIS}`);
  }
  if (grid.nP !== nP || grid.nV !== nV || grid.nCells !== nP * nV) return fail("grid.nP/nV/nCells do not match the axes");
  if (nP * nV > PROCESS_WINDOW_MAX_CELLS) return fail("more than 225 cells");
  const increasing = (a: number[]) => a.every((x, i) => i === 0 || x > a[i - 1]);
  if (!increasing(powers) || !increasing(speeds)) return fail("axes must be strictly increasing");
  const box = grid.literatureBox;
  if (!isObject(box) || !["powerMin_W", "powerMax_W", "speedMin_mm_s", "speedMax_mm_s"].every(k => isFiniteNumber(box[k]))) {
    return fail("grid.literatureBox invalid");
  }
  const basis = grid.rangeBasis;
  if (!isObject(basis) || !isObject(basis.power) || !isObject(basis.speed)) return fail("grid.rangeBasis missing");
  const cells = raw.cells;
  if (!Array.isArray(cells) || cells.length !== nP * nV) return fail(`cell count ${Array.isArray(cells) ? cells.length : "n/a"} does not equal ${nP} x ${nV}`);
  const tally: Record<string, number> = { printable: 0, risky: 0, "do-not-print": 0, inconclusive: 0, error: 0 };
  cells.forEach((cell: unknown, index: number) => {
    const where = `cells[${index}]`;
    if (!isObject(cell)) return fail(`${where} is not an object`);
    const verdict = cell.verdict;
    if (typeof verdict !== "string" || !(PROCESS_WINDOW_CELL_VERDICTS as readonly string[]).includes(verdict)) {
      return fail(`${where} has unknown verdict ${JSON.stringify(verdict)}`);
    }
    const iP = Math.floor(index / nV);
    const iV = index % nV;
    if (cell.iP !== iP || cell.iV !== iV) return fail(`${where} index does not match its position`);
    if (cell.power_W !== powers[iP] || cell.speed_mm_s !== speeds[iV]) return fail(`${where} P/v does not match the grid axes`);
    for (const key of ["blockingGates", "riskGates", "advisoryGates", "unavailableGates", "reasons"]) {
      if (!isStringArray(cell[key])) return fail(`${where}.${key} is not a string array`);
    }
    if (typeof cell.headline !== "string") return fail(`${where}.headline missing`);
    if (!isNumberOrNull(cell.width_um) || !isNumberOrNull(cell.depth_um)) return fail(`${where} width/depth is not a number or null`);
    if (!isNumberOrNull(cell.normalizedEnthalpy)) return fail(`${where}.normalizedEnthalpy invalid`);
    if (verdict === "error") {
      if (typeof cell.error !== "string" || !cell.error) return fail(`${where} is an error cell without an error message`);
      if (cell.width_um !== null || cell.depth_um !== null) return fail(`${where} is an error cell but carries width/depth`);
    } else {
      if (cell.error !== null) return fail(`${where} has an error message but verdict ${verdict}`);
      if (typeof cell.extentStatus !== "string") return fail(`${where}.extentStatus missing`);
      if (cell.extentStatus !== "computed" && (cell.width_um !== null || cell.depth_um !== null)) {
        return fail(`${where} carries width/depth although extentStatus is ${JSON.stringify(cell.extentStatus)}`);
      }
      if (verdict !== "inconclusive" && cell.extentStatus !== "computed") return fail(`${where} is ${verdict} without a computed extent`);
    }
    tally[verdict] += 1;
  });
  const counts = raw.counts;
  if (!isObject(counts)) return fail("missing counts");
  for (const verdict of PROCESS_WINDOW_CELL_VERDICTS) {
    if (counts[verdict] !== tally[verdict]) return fail(`counts.${verdict} (${String(counts[verdict])}) does not match the cells (${tally[verdict]})`);
  }
  if (!Array.isArray(raw.gridAdvisories)) return fail("gridAdvisories missing");
  const overlay = raw.overlay;
  if (!isObject(overlay) || !Array.isArray(overlay.datasets)) return fail("overlay missing");
  for (const dataset of overlay.datasets as unknown[]) {
    if (!isObject(dataset) || typeof dataset.id !== "string") return fail("overlay dataset invalid");
    if (dataset.status !== "available" && dataset.status !== "unavailable") return fail(`dataset ${dataset.id} has an unknown status`);
    if (dataset.status === "unavailable" && (typeof dataset.reason !== "string" || !dataset.reason)) return fail(`dataset ${dataset.id} is unavailable without a reason`);
    if (!Array.isArray(dataset.points)) return fail(`dataset ${dataset.id} points missing`);
    for (const point of dataset.points as unknown[]) {
      if (!isObject(point) || !isFiniteNumber(point.power_W) || !isFiniteNumber(point.speed_mm_s)) return fail(`dataset ${dataset.id} has an invalid point`);
      const mv = point.modelVerdict;
      if (!isObject(mv) || typeof mv.verdict !== "string" || !(PROCESS_WINDOW_CELL_VERDICTS as readonly string[]).includes(mv.verdict)) {
        return fail(`dataset ${dataset.id} has a point with an unknown model verdict`);
      }
      if (!isNumberOrNull(point.measuredWidth_um) || !isNumberOrNull(point.measuredDepth_um)) return fail(`dataset ${dataset.id} point width/depth invalid`);
    }
  }
  const cache = raw.cache;
  if (!isObject(cache) || typeof cache.hit !== "boolean") return fail("cache.hit missing");
  if (!isFiniteNumber(raw.computeMs)) return fail("computeMs missing");
  return raw as unknown as LpbfProcessWindowResponse;
}

// ---------------------------------------------------------------------------------------------------------
// Plain-language gate explanations (presentation only: every gate id, list and count is read from the cells)
// ---------------------------------------------------------------------------------------------------------
const KEYHOLE_GATE = "keyhole";
const TANG_GATE = "lof_tang";

const GATE_NAMES: Readonly<Record<string, string>> = {
  [KEYHOLE_GATE]: "the keyhole risk gate",
  [TANG_GATE]: "the Tang overlap screen",
  lof_wh: "the width-over-hatch diagnostic",
  lof_dt: "the depth-over-layer diagnostic",
  balling: "the balling aspect-ratio screen",
  literature_pv: "the literature P-v box check",
  keyhole_level30: "the legacy porosity level",
  downskin: "the downskin overhang check",
  recoater: "the recoater check",
  distortion: "the distortion check",
};

const gateName = (gate: string): string => GATE_NAMES[gate] ?? `gate ${gate}`;

/** True for the IN625 alloy ids: its keyhole cut is derived per alloy, so the transferred-threshold sentence does not apply. */
const isIn625 = (alloyId: string | null | undefined): boolean => /625/.test(alloyId ?? "");

/** The keyhole gate's cut and provenance in one clause, worded for the alloy that was computed. */
export function keyholeGateClause(alloyId: string | null | undefined): string {
  return isIn625(alloyId)
    ? "the keyhole risk gate (dH/hs at or above the keyhole cut of this alloy)"
    : "the keyhole risk gate (dH/hs at or above 20, a threshold transferred from 316L and Ti-6Al-4V and not derived for this alloy)";
}

/**
 * Since the Tang bump (2026-10-27) a Tang overlap index above 1.0 on modelled melt-pool geometry makes a cell risky (a risk
 * gate, never blocking). A stored result in which lof_tang is still a blocking gate was computed by an earlier solver
 * revision: it is described as a legacy result, never as the current policy.
 */
export const TANG_RISK_SENTENCE =
  "The Tang overlap index exceeds 1.0 on modelled melt-pool geometry, which makes this cell risky: modelled geometry indicates possible lack of fusion; not an experimentally established defect.";
export const FUSION_NOT_ESTABLISHED_NOTE = "Screening result; fusion adequacy is not established.";

/** The Tang index line shown for a selected cell (null when the payload has no index). */
export function tangIndexLine(tangIndex: number | null | undefined): string | null {
  if (tangIndex === null || tangIndex === undefined || !Number.isFinite(tangIndex)) return null;
  return `Tang overlap index ${tangIndex} on modelled melt-pool geometry (risk above 1.0). ${FUSION_NOT_ESTABLISHED_NOTE}`;
}
const TANG_LEGACY_SENTENCE =
  "Legacy result: an earlier solver revision made this cell do-not-print on the Tang overlap index (modelled melt-pool geometry); the current screen reports an index above 1.0 as a risk (risky), never do-not-print. Re-run the map for the current verdict.";
const TANG_LEGACY_CLAUSE = "the Tang overlap index (modelled melt-pool geometry)";

/** One plain sentence per gate that touched the cell: failing, risk, advisory and unavailable gates in that order. */
export function cellGateSentences(cell: LpbfProcessWindowCell, alloyId?: string | null): string[] {
  if (cell.verdict === "error") return [];
  const out: string[] = [];
  const clause = (gate: string): string => (gate === KEYHOLE_GATE ? keyholeGateClause(alloyId) : gateName(gate));
  const cap = (text: string): string => text.charAt(0).toUpperCase() + text.slice(1);
  for (const gate of cell.blockingGates) out.push(gate === TANG_GATE ? TANG_LEGACY_SENTENCE : `${cap(clause(gate))} fails here, which makes this cell do-not-print.`);
  for (const gate of cell.riskGates) out.push(gate === TANG_GATE ? TANG_RISK_SENTENCE : `${cap(clause(gate))} flags this cell, which makes it risky.`);
  for (const gate of cell.advisoryGates) out.push(`${cap(gateName(gate))} gives an advisory only and does not change the verdict.`);
  for (const gate of cell.unavailableGates) out.push(`${cap(gateName(gate))} could not be evaluated for this cell.`);
  return out;
}

export interface NoPrintableExplanation {
  total: number;
  /** Cells where the keyhole gate is a risk gate. */
  keyholeRiskCells: number;
  /** Cells where the Tang overlap index is a risk gate (current results: possible lack of fusion, never blocking). */
  tangRiskCells: number;
  /** Legacy results only: cells where an earlier solver revision made lof_tang a blocking gate. */
  legacyTangBlockedCells: number;
  /** Cells with an inconclusive or error verdict (no gate decided them). */
  unresolvedCells: number;
}

/**
 * When no cell is printable: how many cells each risk gate (keyhole, Tang) flags and, for a legacy stored result only,
 * how many an earlier revision blocked on Tang; counted from the returned cell gate data (a cell may count under both
 * risk gates). Returns null when at least one cell is printable or the grid is empty.
 */
export function noPrintableExplanation(result: Pick<LpbfProcessWindowResponse, "cells">): NoPrintableExplanation | null {
  const cells = result.cells;
  if (cells.length === 0 || cells.some(c => c.verdict === "printable")) return null;
  return {
    total: cells.length,
    keyholeRiskCells: cells.filter(c => c.riskGates.includes(KEYHOLE_GATE)).length,
    tangRiskCells: cells.filter(c => c.riskGates.includes(TANG_GATE)).length,
    legacyTangBlockedCells: cells.filter(c => c.blockingGates.includes(TANG_GATE)).length,
    unresolvedCells: cells.filter(c => c.verdict === "inconclusive" || c.verdict === "error").length,
  };
}

const cellsText = (n: number): string => `${n} cell${n === 1 ? "" : "s"}`;

/** The single note shown above the map when no cell is printable; every number comes from `noPrintableExplanation`. */
export function noPrintableNoteText(result: Pick<LpbfProcessWindowResponse, "cells" | "alloyId">): string | null {
  const x = noPrintableExplanation(result);
  if (!x) return null;
  const parts: string[] = [];
  if (x.keyholeRiskCells > 0) parts.push(`${keyholeGateClause(result.alloyId)} flags ${cellsText(x.keyholeRiskCells)} of ${x.total} as a keyhole risk`);
  if (x.legacyTangBlockedCells > 0) parts.push(`legacy result: an earlier solver revision made ${cellsText(x.legacyTangBlockedCells)} of ${x.total} do-not-print on ${TANG_LEGACY_CLAUSE}, which the current screen reports as a risk (risky), never do-not-print (re-run the map for current verdicts)`);
  if (x.tangRiskCells > 0) parts.push(`the Tang overlap index (above 1.0 on modelled geometry) flags ${cellsText(x.tangRiskCells)} of ${x.total} as a possible lack-of-fusion risk, not an experimentally established defect`);
  if (x.unresolvedCells > 0) parts.push(`${cellsText(x.unresolvedCells)} of ${x.total} could not be resolved`);
  const lead = "No cell in this P-v range is printable.";
  if (parts.length === 0) return `${lead} Select a cell to see which gates held it back.`;
  return `${lead} ${parts.map((p, i) => (i === 0 ? p.charAt(0).toUpperCase() + p.slice(1) : p)).join("; ")}.`;
}
