import { QUANTITY_ENVELOPE } from "../generated/quantityEnvelope";
import { checkedEstimateContainer, checkedQuantityContainer } from "./quantityEnvelope";
import { checkedFront, quantityReason } from "../utils/solidificationDisplay";
/**
 * Pure helpers for the LPBF G/R solidification map card (python/lpbf_gr_solidification.py is the result authority).
 *
 * This module validates the shape and honesty flags of the engine response and provides view helpers (metric
 * extraction, colour scales, aria labels). It computes no physics: every G, R, band and bound shown by the view is
 * read from the response. Screening only, not validation.
 */
import type {
  GrCell,
  GrCellBody,
  GrCellStatus,
  GrSolidificationResponse,
} from "../services/lpbfGrSolidificationService";

export { moveCell } from "./lpbfProcessWindow";

export const GR_CELL_STATUSES: readonly GrCellStatus[] = QUANTITY_ENVELOPE.statuses;
export const GR_MIN_AXIS = 2;
export const GR_MAX_AXIS = 15;
export const GR_MAX_CELLS = 225;
export const GR_SCHEMA = "lpbf-gr-solidification-3";
/** CET block of a cell: the SOL-C Hunt/Durga projection at the cell's own front tuples (v2 envelope, Tier 2 at most). */
export const GR_CET_PROJECTION_ID = "sol-c-cet-projection-v1";
export const GR_CET_QUANTITIES: Readonly<Record<string, string>> = {
  class: "cet-class", equiaxedEnvelopeFraction: "equiaxed-envelope-fraction", planarStabilityIndex: "planar-stability-index",
};
export const GR_HATCH_PATTERN_ID = "gr-keyhole-hatch";

export type GrMetric = "goverr" | "cooling" | "laves";

export interface GrMetricSpec {
  readonly id: GrMetric;
  readonly label: string;
  readonly unit: string;
  readonly categorical: boolean;
  readonly log10: boolean;
}

export const METRICS: readonly GrMetricSpec[] = [
  { id: "goverr", label: "G/R at the median rear-arc point", unit: "log10 (K s/m^2)", categorical: false, log10: true },
  { id: "cooling", label: "Cooling rate G*R (median of the front samples)", unit: "log10 (K/s)", categorical: false, log10: true },
  { id: "laves", label: "Laves bound, trapping-adjusted (sampled arc)", unit: "fraction of liquid", categorical: false, log10: false },
];

/** Statuses whose derived numbers are a computed result. Others are drawn as outlined empty cells. */
export function isComputedStatus(status: GrCellStatus): boolean {
  return status === "computed" || status === "partial";
}

/** True when the cell lies outside the conduction regime of the G/R field (engine regimeNote, e.g. keyhole). */
export function isOutsideRegime(cell: GrCellBody): boolean {
  return typeof cell.regime === "string" && cell.regime.toLowerCase().includes("keyhole");
}

/** Numeric metric value of a cell (already log10 where the metric says so), or null when there is none. Never 0 for a missing value. */
export function metricValue(cell: GrCellBody, metric: GrMetric): number | null {
  if (!isComputedStatus(cell.status)) return null;
  switch (metric) {
    case "goverr": {
      const v = cell.front.quantities.gOverR.value;
      return typeof v === "number" && Number.isFinite(v) && v > 0 ? Math.log10(v) : null;
    }
    case "cooling": {
      const v = cell.front.quantities.coolingRate.value;
      return typeof v === "number" && Number.isFinite(v) && v > 0 ? Math.log10(v) : null;
    }
    case "laves": {
      const f = cell.laves.quantities.fraction.value;
      return typeof f === "number" && Number.isFinite(f) ? f : null;
    }
  }
}

// ---------------------------------------------------------------------------------------------------------
// Colour scales (colour-blind safe: a viridis-style sequential ramp and the Okabe-Ito palette for categories)
// ---------------------------------------------------------------------------------------------------------
export const SEQUENTIAL_STOPS: readonly string[] = ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"];

export interface GrCellStyle {
  readonly fill: string;
  readonly stroke: string;
  readonly textColor: string;
  readonly outlined: boolean;
  readonly noValue: boolean;
}

/** Style of a cell that has no value to show: outlined and empty, never the low end of the scale. */
export const NO_VALUE_STYLE: GrCellStyle = { fill: "none", stroke: "#94a3b8", textColor: "#cbd5e1", outlined: true, noValue: true };

const hexToRgb = (hex: string): [number, number, number] => [
  parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16),
];
const rgbToHex = (rgb: number[]): string => `#${rgb.map(c => Math.round(c).toString(16).padStart(2, "0")).join("")}`;

/** Position t in [0, 1] on the sequential ramp (piecewise linear between the 5 stops). */
export function sequentialColor(t: number): string {
  const x = Math.min(1, Math.max(0, t)) * (SEQUENTIAL_STOPS.length - 1);
  const i = Math.min(SEQUENTIAL_STOPS.length - 2, Math.floor(x));
  const f = x - i;
  const a = hexToRgb(SEQUENTIAL_STOPS[i]);
  const b = hexToRgb(SEQUENTIAL_STOPS[i + 1]);
  return rgbToHex([0, 1, 2].map(k => a[k] + (b[k] - a[k]) * f));
}

const luminance = (hex: string): number => {
  const [r, g, b] = hexToRgb(hex).map(c => c / 255);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const readableText = (fill: string): string => (luminance(fill) > 0.45 ? "#0f172a" : "#f8fafc");

export interface ScaleRange { min: number; max: number }

/** Min and max of a numeric metric over a response's cells (null when no cell has a value). */
export function metricRange(cells: readonly GrCellBody[], metric: GrMetric): ScaleRange | null {
  let min = Infinity;
  let max = -Infinity;
  for (const cell of cells) {
    const v = metricValue(cell, metric);
    if (v === null) continue;
    if (v < min) min = v;
    if (v > max) max = v;
  }
  return Number.isFinite(min) ? { min, max } : null;
}

/** Fill, stroke and text colour for a numeric metric value. null maps to NO_VALUE_STYLE. */
export function scaleStyle(value: number | null, range: ScaleRange | null): GrCellStyle {
  if (value === null || !Number.isFinite(value) || range === null) return NO_VALUE_STYLE;
  const t = range.max > range.min ? (value - range.min) / (range.max - range.min) : 0.5;
  const fill = sequentialColor(t);
  return { fill, stroke: "#0f172a", textColor: readableText(fill), outlined: false, noValue: false };
}

export function cellStyle(cell: GrCellBody, metric: GrMetric, range: ScaleRange | null): GrCellStyle {
  return scaleStyle(metricValue(cell, metric), range);
}
export function cellGlyph(cell: GrCellBody, metric: GrMetric): string {
  return cell.status === "failed" ? "!" : metricValue(cell, metric) === null ? "-" : "";
}
/**
 * One sentence saying why a metric has no value on any cell of the map, or null when at least one cell has a value.
 * The reason text is the engine's own (first cell that carries one); nothing is invented here.
 */
export function noValueExplanation(cells: readonly GrCellBody[], metric: GrMetric): string | null {
  if (cells.length === 0 || metricRange(cells, metric) !== null) return null;
  const quantityOf = (cell: GrCellBody) => metric === "laves" ? cell.laves.quantities.fraction
    : metric === "cooling" ? cell.front.quantities.coolingRate : cell.front.quantities.gOverR;
  for (const cell of cells) {
    const q = quantityOf(cell);
    if (q.value === null && q.reasons.length > 0) return `No cell has a value for this metric. ${quantityReason(q)}`;
  }
  return "No cell has a value for this metric. Select a cell to see the reason.";
}
export const STATUS_LABELS: Readonly<Record<GrCellStatus, string>> = QUANTITY_ENVELOPE.statusLabels;

export function formatSci(value: number | null | undefined, digits = 3): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toExponential(digits) : "not available";
}

export function formatMetric(value: number | null, metric: GrMetric): string {
  if (value === null) return "no value";
  return metric === "laves" ? value.toFixed(4) : value.toFixed(2);
}

export function cellAriaLabel(cell: GrCellBody & { power_W: number; speed_mm_s: number }, metric: GrMetric): string {
  const base = `Power ${cell.power_W} W, speed ${cell.speed_mm_s} mm/s: ${STATUS_LABELS[cell.status]}`;
  const value = metricValue(cell, metric);
  const shown = value === null ? "no value" : typeof value === "string" ? value : formatMetric(value, metric);
  const outside = isOutsideRegime(cell) ? ", outside the conduction regime (keyhole)" : "";
  return `${base}, ${metric}: ${shown}${outside}`;
}

// ---------------------------------------------------------------------------------------------------------
// Response validator
// ---------------------------------------------------------------------------------------------------------
const fail = (reason: string): never => { throw new Error(`lpbf G/R solidification response rejected: ${reason}`); };
const isObject = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === "object" && !Array.isArray(v);
const isFiniteNumber = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
function checkBody(where: string, body: unknown): void {
  if (!isObject(body)) return fail(`${where} is not an object`);
  if (!(GR_CELL_STATUSES as readonly unknown[]).includes(body.status)) return fail(`${where} has unknown status`);
  for (const retired of ["morphology", "rosenthalCenterline", "reason"]) if (Object.hasOwn(body, retired)) return fail(`${where}.${retired} retired`);
  checkedFront(body.front);
  const cet = checkedEstimateContainer(body.cet);
  const laves = checkedQuantityContainer(body.laves);
  const cetBody = body.cet as Record<string, unknown>;
  if (cetBody.projectionId !== GR_CET_PROJECTION_ID || !(GR_CELL_STATUSES as readonly unknown[]).includes(cetBody.status)) return fail(`${where}.cet identity invalid`);
  if (cet.quantities.class?.quantityDefinition !== "cet-class"
    || Object.entries(cet.quantities).some(([name, q]) => GR_CET_QUANTITIES[name] !== q.quantityDefinition)) return fail(`${where}.cet quantities invalid`);
  if (Object.keys(laves.quantities).length !== 1 || laves.quantities.fraction?.quantityDefinition !== "laves-trapped-scheil-fraction") return fail(`${where}.laves quantities invalid`);
}
function checkSourceChecks(raw: unknown): void {
  if (!isObject(raw)) return fail("missing sourceChecks");
  for (const [key, values] of Object.entries({ equationRead: ["read", "not-read"], algebraReproduced: ["reproduced", "not-reproduced", "not-attempted"], printedLimitComparison: ["agrees", "disagrees", "not-available", "not-attempted"] })) {
    const item = raw[key];
    if (!isObject(item) || !values.includes(String(item.status))) return fail(`sourceChecks.${key} invalid`);
    if (key === "equationRead" && item.locator !== null && typeof item.locator !== "string") return fail("equationRead locator invalid");
    if (key === "algebraReproduced" && item.test !== null && typeof item.test !== "string") return fail("algebraReproduced test invalid");
    if (key === "printedLimitComparison") {
      for (const name of ["printed", "computed"]) if (item[name] !== null && !(Array.isArray(item[name]) && (item[name] as unknown[]).every(isFiniteNumber))) return fail(`printedLimitComparison.${name} invalid`);
      if (item.tolerance !== null && !isFiniteNumber(item.tolerance)) return fail("printedLimitComparison tolerance invalid");
    }
  }
}

export function checkedGrSolidification(raw: unknown): GrSolidificationResponse {
  if (!isObject(raw)) return fail("not an object");
  if (raw.success !== true) return fail("success is not true");
  const evidence = raw.evidence;
  if (!isObject(evidence)) return fail("missing evidence");
  if (evidence.kind !== "screening-only") return fail(`evidence.kind must be "screening-only" (got ${JSON.stringify(evidence.kind)})`);
  if (evidence.experimentalValidation !== false) return fail("evidence.experimentalValidation must be exactly false");
  if (typeof evidence.statement !== "string" || !evidence.statement) return fail("evidence.statement missing");
  if (raw.schema !== GR_SCHEMA) return fail(`schema must be ${GR_SCHEMA}`);
  if (raw.mode !== "point" && raw.mode !== "map") return fail("mode invalid");
  if (!(QUANTITY_ENVELOPE.canonicalAlloyIds as readonly unknown[]).includes(raw.alloyId)) return fail("alloyId invalid");
  const request = raw.request;
  if (!isObject(request)) return fail("missing request echo");
  for (const key of ["beamDiameter_um", "layer_um", "hatch_um", "preheatTemp_C"]) {
    if (!isFiniteNumber(request[key])) return fail(`request.${key} is not a number`);
  }
  const provenance = raw.provenance;
  if (!isObject(provenance) || typeof provenance.solidificationModelId !== "string" || typeof provenance.buildJobSolverRevision !== "string") {
    return fail("missing provenance");
  }
  if (!Array.isArray(raw.limits) || !raw.limits.every(x => typeof x === "string")) return fail("limits missing");
  const cet = raw.cet;
  if (!isObject(cet) || typeof cet.equation !== "string" || Object.hasOwn(cet, "equationVerified")) return fail("cet criterion view missing");
  checkSourceChecks(cet.sourceChecks);
  if (!isObject(cet.constantsStatus) || !Array.isArray(cet.constantsStatus.sets)) return fail("cet constants missing");
  for (const set of cet.constantsStatus.sets) {
    if (!isObject(set) || Object.hasOwn(set, "equationVerified")) return fail("cet source invalid");
    checkSourceChecks(set.sourceChecks);
  }
  if (raw.computeMs !== undefined && !isFiniteNumber(raw.computeMs)) return fail("computeMs missing");

  let bodies: unknown[];
  if (raw.mode === "point") {
    if (raw.point === undefined) return fail("point missing");
    checkBody("point", raw.point);
    bodies = [raw.point];
  } else {
    const grid = raw.grid;
    if (!isObject(grid)) return fail("missing grid");
    const powers = grid.powers_W;
    const speeds = grid.speeds_mm_s;
    if (!Array.isArray(powers) || !powers.every(isFiniteNumber)) return fail("grid.powers_W invalid");
    if (!Array.isArray(speeds) || !speeds.every(isFiniteNumber)) return fail("grid.speeds_mm_s invalid");
    const nP = powers.length;
    const nV = speeds.length;
    if (nP < GR_MIN_AXIS || nP > GR_MAX_AXIS || nV < GR_MIN_AXIS || nV > GR_MAX_AXIS) return fail(`axis lengths ${nP} x ${nV} out of range`);
    if (grid.nP !== nP || grid.nV !== nV || grid.nCells !== nP * nV) return fail("grid.nP/nV/nCells do not match the axes");
    if (nP * nV > GR_MAX_CELLS) return fail("more than 225 cells");
    const increasing = (a: number[]) => a.every((x, i) => i === 0 || x > a[i - 1]);
    if (!increasing(powers) || !increasing(speeds)) return fail("axes must be strictly increasing");
    const cells = raw.cells;
    if (!Array.isArray(cells) || cells.length !== nP * nV) return fail(`cell count ${Array.isArray(cells) ? cells.length : "n/a"} does not equal ${nP} x ${nV}`);
    cells.forEach((cell: unknown, index: number) => {
      const where = `cells[${index}]`;
      checkBody(where, cell);
      const c = cell as Record<string, unknown>;
      if (c.iP !== Math.floor(index / nV) || c.iV !== index % nV) fail(`${where} index does not match its position`);
      if (c.power_W !== powers[c.iP as number] || c.speed_mm_s !== speeds[c.iV as number]) fail(`${where} P/v does not match the grid axes`);
    });
    bodies = cells;
  }
  const counts = raw.counts;
  if (!isObject(counts)) return fail("missing counts");
  for (const status of GR_CELL_STATUSES) {
    const n = bodies.filter(b => (b as Record<string, unknown>).status === status).length;
    if (counts[status] !== n) return fail(`counts.${status} (${String(counts[status])}) does not match the cells (${n})`);
  }
  return raw as unknown as GrSolidificationResponse;
}

export function cellAt(response: GrSolidificationResponse, iP: number, iV: number): GrCell {
  const cells = response.cells ?? [];
  const nV = response.grid?.nV ?? 0;
  return cells[iP * nV + iV];
}
