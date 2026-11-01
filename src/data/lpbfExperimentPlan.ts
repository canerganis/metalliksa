/**
 * Typed, read-only loader for the Python-generated next-experiment plan
 * (plan.json, schema "lpbf-next-experiment-plan-1", written by python/tools/lpbf_next_experiment.py).
 *
 * Python is the authority for the ranking and the plate layout (python/lpbf_next_experiment.py). This module
 * validates the shape and the honesty fields of a plan file the user loads and formats it as CSV for download; it
 * computes no physics, no score and no layout. Screening: experiment proposal; not a print recommendation.
 */

export const LPBF_EXPERIMENT_PLAN_SCHEMA = "lpbf-next-experiment-plan-1";
export const LPBF_EXPERIMENT_PLAN_LABEL = "Screening: experiment proposal; not a print recommendation";
export const LPBF_EXPERIMENT_PLAN_MAX_POINTS = 48;

export interface ExperimentPlanLayout {
  readonly printOrder: number;
  readonly x_start_mm: number;
  readonly x_end_mm: number;
  readonly y_mm: number;
}

export interface ExperimentPlanScore {
  readonly total: number;
  readonly base: number;
  readonly disagreement: { readonly raw: number | null; readonly sdLnW: number | null; readonly sdLnD: number | null; readonly nResolvedKernels: number };
  readonly intervalWidth: { readonly lnHiOverLo: number | null; readonly note: string };
  readonly coverage: { readonly regimeClass: string; readonly classUnderCovered: boolean; readonly nearestDistanceStd: number | null; readonly value: number };
}

export interface ExperimentPlanPoint {
  readonly trackId: string;
  readonly rank: number;
  readonly power_W: number;
  readonly speed_mm_s: number;
  readonly beamDiameter_um: number;
  readonly layer_um: number;
  readonly preheat_C: number;
  readonly regimeClass: string;
  readonly score: ExperimentPlanScore;
  readonly layout: ExperimentPlanLayout;
}

export interface ExperimentPlanDocument {
  readonly schema: typeof LPBF_EXPERIMENT_PLAN_SCHEMA;
  readonly label: string;
  readonly evidenceKind: "screening-only";
  readonly material: string;
  readonly configSha256: string;
  readonly calibration: { readonly available: boolean; readonly contentSha256?: string; readonly configSha256?: string; readonly calibrationId?: string; readonly reason?: string };
  readonly intervalWidth: { readonly lnHiOverLo: number | null; readonly note: string };
  readonly candidates?: { readonly trainingPoints?: number; readonly trainingNote?: string | null };
  readonly plate: { readonly x_mm: number; readonly y_mm: number; readonly pitch_mm: number; readonly trackLength_mm: number; readonly edgeMargin_mm: number };
  readonly points: readonly ExperimentPlanPoint[];
  readonly commands: readonly string[];
  readonly limits: string;
  /** Set to "machine-calibration" by `plan --for-machine-calibration`; absent for an ordinary plan. */
  readonly purpose?: typeof LPBF_MACHINE_CALIBRATION_PURPOSE | null;
  /** Soft checks (for example regime coverage); never a constraint on the selection. */
  readonly warnings?: readonly string[];
  /** Extra measurement_template.csv columns (method fields) for a machine-calibration plan. */
  readonly methodColumns?: readonly string[];
}

export const LPBF_MACHINE_CALIBRATION_PURPOSE = "machine-calibration";
/** The fit command Python appends to plan.commands for a machine-calibration plan. */
export const MACHINE_FIT_COMMAND_MARKER = "lpbf_machine_calibration.py fit";
export const machineFitCommand = (plan: ExperimentPlanDocument): string | null =>
  plan.purpose === LPBF_MACHINE_CALIBRATION_PURPOSE ? (plan.commands.find(c => c.includes(MACHINE_FIT_COMMAND_MARKER)) ?? null) : null;

type Obj = Record<string, unknown>;

export class ExperimentPlanError extends Error {
  constructor(message: string) {
    super(`lpbf experiment plan rejected: ${message}`);
    this.name = "ExperimentPlanError";
  }
}

const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const fail = (msg: string): never => { throw new ExperimentPlanError(msg); };

function num(o: Obj, key: string, where: string, opts: { positive?: boolean; nullable?: boolean } = {}): number | null {
  const v = o[key];
  if (v === null && opts.nullable) return null;
  if (typeof v !== "number" || !Number.isFinite(v)) return fail(`${where}.${key} must be a finite number`);
  if (opts.positive && v <= 0) return fail(`${where}.${key} must be positive`);
  return v;
}

function str(o: Obj, key: string, where: string): string {
  const v = o[key];
  if (typeof v !== "string" || v.length === 0) return fail(`${where}.${key} must be a non-empty string`);
  return v;
}

function obj(o: Obj, key: string, where: string): Obj {
  const v = o[key];
  if (!isObj(v)) return fail(`${where}.${key} must be an object`);
  return v;
}

const REGIME = new Set(["conduction", "transition", "keyhole"]);

function checkPoint(raw: unknown, i: number): ExperimentPlanPoint {
  const where = `points[${i}]`;
  if (!isObj(raw)) return fail(`${where} is not an object`);
  str(raw, "trackId", where);
  const regimeClass = str(raw, "regimeClass", where);
  if (!REGIME.has(regimeClass)) fail(`${where}.regimeClass ${regimeClass} is not a regime class`);
  for (const k of ["power_W", "speed_mm_s", "beamDiameter_um", "layer_um"]) num(raw, k, where, { positive: true });
  num(raw, "preheat_C", where);
  num(raw, "rank", where, { positive: true });
  const score = obj(raw, "score", where);
  num(score, "total", `${where}.score`);
  num(score, "base", `${where}.score`);
  const dis = obj(score, "disagreement", `${where}.score`);
  num(dis, "raw", `${where}.score.disagreement`, { nullable: true });
  num(dis, "sdLnW", `${where}.score.disagreement`, { nullable: true });
  num(dis, "sdLnD", `${where}.score.disagreement`, { nullable: true });
  num(dis, "nResolvedKernels", `${where}.score.disagreement`);
  const iv = obj(score, "intervalWidth", `${where}.score`);
  num(iv, "lnHiOverLo", `${where}.score.intervalWidth`, { nullable: true });
  str(iv, "note", `${where}.score.intervalWidth`);
  const cov = obj(score, "coverage", `${where}.score`);
  if (typeof cov.classUnderCovered !== "boolean") fail(`${where}.score.coverage.classUnderCovered must be a boolean`);
  num(cov, "nearestDistanceStd", `${where}.score.coverage`, { nullable: true });
  num(cov, "value", `${where}.score.coverage`);
  str(cov, "regimeClass", `${where}.score.coverage`);
  const layout = obj(raw, "layout", where);
  for (const k of ["printOrder", "x_start_mm", "x_end_mm", "y_mm"]) num(layout, k, `${where}.layout`);
  return raw as unknown as ExperimentPlanPoint;
}

/** Validate a parsed plan.json; throws ExperimentPlanError (never returns a partially checked plan). */
export function checkedExperimentPlan(raw: unknown): ExperimentPlanDocument {
  if (!isObj(raw)) return fail("not an object");
  if (raw.schema !== LPBF_EXPERIMENT_PLAN_SCHEMA) fail(`schema must be ${LPBF_EXPERIMENT_PLAN_SCHEMA}`);
  if (raw.label !== LPBF_EXPERIMENT_PLAN_LABEL) fail("label is not the screening proposal label");
  if (raw.evidenceKind !== "screening-only") fail("evidenceKind must be screening-only");
  str(raw, "material", "plan");
  if (typeof raw.configSha256 !== "string" || !/^[0-9a-f]{64}$/.test(raw.configSha256)) fail("configSha256 must be a sha256 hex string");
  const cal = obj(raw, "calibration", "plan");
  if (typeof cal.available !== "boolean") fail("calibration.available must be a boolean");
  if (cal.available === true) {
    for (const k of ["contentSha256", "configSha256"]) {
      if (typeof cal[k] !== "string" || !/^[0-9a-f]{64}$/.test(cal[k] as string)) fail(`calibration.${k} must be a sha256 hex string`);
    }
  } else {
    str(cal, "reason", "calibration");
  }
  const iv = obj(raw, "intervalWidth", "plan");
  num(iv, "lnHiOverLo", "intervalWidth", { nullable: true });
  str(iv, "note", "intervalWidth");
  if (raw.candidates !== undefined) {
    const cand = obj(raw, "candidates", "plan");
    if (cand.trainingNote !== undefined && cand.trainingNote !== null && typeof cand.trainingNote !== "string") fail("candidates.trainingNote must be a string or null");
  }
  const plate = obj(raw, "plate", "plan");
  for (const k of ["x_mm", "y_mm", "pitch_mm", "trackLength_mm", "edgeMargin_mm"]) num(plate, k, "plate", { positive: true });
  if (!Array.isArray(raw.points) || raw.points.length === 0) return fail("points must be a non-empty array");
  if (raw.points.length > LPBF_EXPERIMENT_PLAN_MAX_POINTS) fail(`more than ${LPBF_EXPERIMENT_PLAN_MAX_POINTS} points`);
  const points = raw.points.map(checkPoint);
  const ids = new Set(points.map(p => p.trackId));
  if (ids.size !== points.length) fail("track ids must be unique");
  if (!Array.isArray(raw.commands) || raw.commands.some(c => typeof c !== "string")) fail("commands must be an array of strings");
  str(raw, "limits", "plan");
  if (raw.purpose !== undefined && raw.purpose !== null && raw.purpose !== LPBF_MACHINE_CALIBRATION_PURPOSE) fail(`purpose must be ${LPBF_MACHINE_CALIBRATION_PURPOSE} when present`);
  for (const k of ["warnings", "methodColumns"]) {
    const v = raw[k];
    if (v !== undefined && (!Array.isArray(v) || v.some(x => typeof x !== "string"))) fail(`${k} must be an array of strings`);
  }
  return raw as unknown as ExperimentPlanDocument;
}

/** Parse the text of a plan file; JSON errors become ExperimentPlanError too. */
export function parseExperimentPlan(text: string): ExperimentPlanDocument {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    return fail(`not valid JSON (${error instanceof Error ? error.message : "parse error"})`);
  }
  return checkedExperimentPlan(parsed);
}

// ---- client-side CSV (same columns as the Python outputs; no network, no worker) ------------------------------

export function csvCell(value: string | number): string {
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function toCsv(header: readonly string[], rows: readonly (readonly (string | number)[])[]): string {
  return [header, ...rows].map(r => r.map(csvCell).join(",")).join("\n") + "\n";
}

const byPrintOrder = (plan: ExperimentPlanDocument): ExperimentPlanPoint[] =>
  [...plan.points].sort((a, b) => a.layout.printOrder - b.layout.printOrder);

export function printPlanCsv(plan: ExperimentPlanDocument): string {
  return toCsv(
    ["print_order", "track_id", "rank", "power_W", "speed_mm_s", "spot_um", "layer_um", "preheat_C", "regime_class", "note"],
    byPrintOrder(plan).map(p => [p.layout.printOrder, p.trackId, p.rank, p.power_W, p.speed_mm_s, p.beamDiameter_um, p.layer_um, p.preheat_C, p.regimeClass, "screening experiment proposal; not a print recommendation"]),
  );
}

export function plateLayoutCsv(plan: ExperimentPlanDocument): string {
  return toCsv(
    ["print_order", "track_id", "x_start_mm", "x_end_mm", "y_mm", "power_W", "speed_mm_s", "spot_um"],
    byPrintOrder(plan).map(p => [p.layout.printOrder, p.trackId, p.layout.x_start_mm, p.layout.x_end_mm, p.layout.y_mm, p.power_W, p.speed_mm_s, p.beamDiameter_um]),
  );
}

/** Blank width/depth columns: the user fills them in; blank rows are excluded on import, never imputed. */
export function measurementTemplateCsv(plan: ExperimentPlanDocument): string {
  // A machine-calibration plan adds the method columns (same names and order as the Python template).
  const extra = plan.purpose === LPBF_MACHINE_CALIBRATION_PURPOSE ? [...(plan.methodColumns ?? [])] : [];
  return toCsv(
    ["track_id", "power_W", "speed_mm_s", "spot_um", "width_um", "depth_um", "notes", ...extra],
    byPrintOrder(plan).map(p => [p.trackId, p.power_W, p.speed_mm_s, p.beamDiameter_um, "", "", "", ...extra.map(() => "")]),
  );
}
