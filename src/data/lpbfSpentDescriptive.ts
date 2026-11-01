/**
 * Spent-set descriptive record (research hub spec 8.4): the Python-generated, slim view record
 * docs/LPBF_SPENT_DESCRIPTIVE_<date>.view.json. This module only validates and types it. Nothing is computed here.
 */

export const SPENT_DESCRIPTIVE_SCHEMA_PREFIX = "lpbf-spent-descriptive-view-";
export const SPENT_BADGE = "Not validation: data already seen";
/** Spec 8.1 item 2: ids that are never shown in this panel. */
export const SPENT_FORBIDDEN_IDS: readonly string[] = [
  "bitharas", "leis", "hyer", "aboulkhair", "ruckh", "gong", "ullah", "wimmer", "huang",
  "ku-leuven-in718", "hann", "nist-mds2-2923-in718", "cmu",
];
const FORBIDDEN_KEYS: readonly string[] = ["rank", "score", "pass", "fail"];

export interface SpentCurvePoint { readonly x: number; readonly depth_um: number | null; readonly index: number | null; readonly status: string }
export interface SpentMeasuredPoint {
  readonly rowId: string;
  readonly x: number;
  readonly measured_um: number | null;
  readonly measuredSd_um: number | null;
  readonly served_um: number | null;
  readonly index: number | null;
  readonly diffPct: number | null;
  readonly status: string;
}
export interface SpentGroup {
  readonly id: string;
  readonly beamRole: "primary" | "sensitivity";
  readonly fixed: Readonly<Record<string, number | string>>;
  readonly curve: readonly SpentCurvePoint[] | null;
  readonly points: readonly SpentMeasuredPoint[];
}
export interface SpentDeviationStats {
  readonly n: number;
  readonly failed: number;
  readonly unavailable: number;
  readonly median_pct: number | null;
  readonly p10_pct: number | null;
  readonly p90_pct: number | null;
}
export interface SpentDeviationBin extends SpentDeviationStats { readonly id: string; readonly label: string; readonly direction: string | null }
export interface SpentDeviation {
  readonly arm: string;
  readonly beamRole: "primary" | "sensitivity";
  readonly beam_um: number;
  readonly all: SpentDeviationStats;
  readonly bins: readonly SpentDeviationBin[];
}
export interface SpentNote { readonly code: string; readonly sentence: string; readonly source: string; readonly locator: string }
export interface SpentSet {
  readonly id: string;
  readonly title: string;
  readonly alloy: string;
  readonly observable: string;
  readonly curveAxis: "speed" | "power";
  readonly provenance: {
    readonly citation: string; readonly doi: string; readonly licence: string; readonly attribution: string;
    readonly licenceFile: string; readonly tableSha256: string; readonly rows: number; readonly locator: string;
    readonly loader: string; readonly datum: string; readonly substrate: string; readonly powerBasis: string;
    readonly transcription: string;
  };
  readonly spent: {
    readonly status: "SPENT";
    readonly spentBy: readonly { readonly event: string; readonly record: string; readonly date: string }[];
    readonly usedInServedDevelopment: boolean;
  };
  readonly beam: { readonly value_um: number; readonly status: string; readonly definition: string; readonly sensitivity_um: number | null };
  readonly measuredSource: { readonly label: "Measured"; readonly transcription: string; readonly locator: string };
  readonly servedSource: { readonly label: "Unresolved"; readonly reasonCode: string; readonly reasonText: string };
  readonly groups: readonly SpentGroup[];
  readonly deviation: readonly SpentDeviation[];
  readonly notes: readonly SpentNote[];
}
export interface SpentModelMapRow {
  readonly key: string;
  readonly setId: string;
  readonly label: string;
  readonly alsoSets: readonly string[];
  readonly bins: readonly { readonly id: string; readonly label: string; readonly direction: string | null; readonly n: number }[];
}
export interface LpbfSpentDescriptiveDocument {
  readonly schema: string;
  readonly generatedAt: string;
  readonly implementationHash: string;
  readonly servedIdentity: { readonly servedClosurePinSha256: string; readonly [key: string]: unknown };
  readonly research: { readonly requested: false; readonly reasonCode: string };
  readonly spentLedgerSha256: string;
  readonly reasonsCatalogSha256: string;
  readonly honesty: {
    readonly label: string; readonly statement: string; readonly experimentalValidation: false;
    readonly labelPromotionProposed: "none"; readonly evidenceKind: "screening-only"; readonly spentOnly: true;
  };
  readonly arms: readonly { readonly id: string; readonly label: string; readonly [key: string]: unknown }[];
  readonly sets: readonly SpentSet[];
  readonly modelMap: readonly SpentModelMapRow[];
  readonly directionRule: string;
  readonly deferred: readonly { readonly datasetId: string; readonly reason: string }[];
}

export class SpentDescriptiveError extends Error {}

function fail(path: string, why: string): never {
  throw new SpentDescriptiveError(`${path}: ${why}`);
}
const isObj = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
function obj(v: unknown, path: string): Record<string, unknown> { return isObj(v) ? v : fail(path, "expected an object"); }
function arr(v: unknown, path: string): unknown[] { return Array.isArray(v) ? v : fail(path, "expected an array"); }
function str(v: unknown, path: string): string { return typeof v === "string" && v.length > 0 ? v : fail(path, "expected a non-empty string"); }
function num(v: unknown, path: string): number { return typeof v === "number" && Number.isFinite(v) ? v : fail(path, "expected a finite number"); }
function numOrNull(v: unknown, path: string): number | null { return v === null ? null : num(v, path); }
function lit<T>(v: unknown, expected: T, path: string): T { return v === expected ? expected : fail(path, `expected ${JSON.stringify(expected)}`); }

export function isForbiddenSpentId(id: string): boolean {
  const lower = id.toLowerCase();
  return SPENT_FORBIDDEN_IDS.some((f) => lower === f || lower.startsWith(`${f}-`) || new RegExp(`^${f}\\d`).test(lower));
}

function scanKeys(v: unknown, path: string): void {
  if (Array.isArray(v)) { v.forEach((x, i) => scanKeys(x, `${path}[${i}]`)); return; }
  if (!isObj(v)) return;
  for (const [k, x] of Object.entries(v)) {
    if (FORBIDDEN_KEYS.includes(k.toLowerCase())) fail(`${path}.${k}`, "key is not allowed in this record");
    scanKeys(x, `${path}.${k}`);
  }
}

function stats(v: unknown, path: string): void {
  const o = obj(v, path);
  num(o.n, `${path}.n`); num(o.failed, `${path}.failed`); num(o.unavailable, `${path}.unavailable`);
  numOrNull(o.median_pct, `${path}.median_pct`); numOrNull(o.p10_pct, `${path}.p10_pct`); numOrNull(o.p90_pct, `${path}.p90_pct`);
}

function checkSet(v: unknown, path: string): void {
  const s = obj(v, path);
  const id = str(s.id, `${path}.id`);
  if (isForbiddenSpentId(id)) fail(`${path}.id`, `set ${id} is on the forbidden list`);
  str(s.title, `${path}.title`); str(s.alloy, `${path}.alloy`); str(s.observable, `${path}.observable`);
  if (s.curveAxis !== "speed" && s.curveAxis !== "power") fail(`${path}.curveAxis`, "expected speed or power");
  const spent = obj(s.spent, `${path}.spent`);
  lit(spent.status, "SPENT", `${path}.spent.status`);
  arr(spent.spentBy, `${path}.spent.spentBy`);
  if (typeof spent.usedInServedDevelopment !== "boolean") fail(`${path}.spent.usedInServedDevelopment`, "expected a boolean");
  const prov = obj(s.provenance, `${path}.provenance`);
  for (const k of ["citation", "doi", "licence", "attribution", "tableSha256", "locator", "datum", "substrate", "powerBasis", "transcription"]) str(prov[k], `${path}.provenance.${k}`);
  num(prov.rows, `${path}.provenance.rows`);
  const beam = obj(s.beam, `${path}.beam`);
  num(beam.value_um, `${path}.beam.value_um`); str(beam.status, `${path}.beam.status`); numOrNull(beam.sensitivity_um, `${path}.beam.sensitivity_um`);
  lit(obj(s.measuredSource, `${path}.measuredSource`).label, "Measured", `${path}.measuredSource.label`);
  const served = obj(s.servedSource, `${path}.servedSource`);
  lit(served.label, "Unresolved", `${path}.servedSource.label`); str(served.reasonCode, `${path}.servedSource.reasonCode`); str(served.reasonText, `${path}.servedSource.reasonText`);
  arr(s.groups, `${path}.groups`).forEach((gv, i) => {
    const g = obj(gv, `${path}.groups[${i}]`);
    str(g.id, `${path}.groups[${i}].id`);
    if (g.beamRole !== "primary" && g.beamRole !== "sensitivity") fail(`${path}.groups[${i}].beamRole`, "expected primary or sensitivity");
    obj(g.fixed, `${path}.groups[${i}].fixed`);
    if (g.curve !== null) arr(g.curve, `${path}.groups[${i}].curve`).forEach((p, j) => {
      const c = obj(p, `${path}.groups[${i}].curve[${j}]`);
      num(c.x, `${path}.groups[${i}].curve[${j}].x`); numOrNull(c.depth_um, `${path}.groups[${i}].curve[${j}].depth_um`); numOrNull(c.index, `${path}.groups[${i}].curve[${j}].index`);
    });
    arr(g.points, `${path}.groups[${i}].points`).forEach((p, j) => {
      const m = obj(p, `${path}.groups[${i}].points[${j}]`);
      str(m.rowId, `${path}.groups[${i}].points[${j}].rowId`); num(m.x, `${path}.groups[${i}].points[${j}].x`);
      for (const k of ["measured_um", "measuredSd_um", "served_um", "index", "diffPct"]) numOrNull(m[k], `${path}.groups[${i}].points[${j}].${k}`);
    });
  });
  arr(s.deviation, `${path}.deviation`).forEach((dv, i) => {
    const d = obj(dv, `${path}.deviation[${i}]`);
    str(d.arm, `${path}.deviation[${i}].arm`); num(d.beam_um, `${path}.deviation[${i}].beam_um`);
    stats(d.all, `${path}.deviation[${i}].all`);
    arr(d.bins, `${path}.deviation[${i}].bins`).forEach((b, j) => {
      stats(b, `${path}.deviation[${i}].bins[${j}]`);
      const bin = b as Record<string, unknown>;
      str(bin.id, `${path}.deviation[${i}].bins[${j}].id`); str(bin.label, `${path}.deviation[${i}].bins[${j}].label`);
    });
  });
  arr(s.notes, `${path}.notes`).forEach((nv, i) => {
    const n = obj(nv, `${path}.notes[${i}]`);
    str(n.code, `${path}.notes[${i}].code`); str(n.source, `${path}.notes[${i}].source`); str(n.locator, `${path}.notes[${i}].locator`);
    if (!str(n.sentence, `${path}.notes[${i}].sentence`).startsWith("Candidate explanation, not tested:")) fail(`${path}.notes[${i}].sentence`, "a note must start with the candidate explanation prefix");
  });
}

/** Validates a spent-descriptive view record; throws SpentDescriptiveError on anything off-contract. */
export function checkedSpentDescriptive(raw: unknown): LpbfSpentDescriptiveDocument {
  const d = obj(raw, "record");
  if (!str(d.schema, "schema").startsWith(SPENT_DESCRIPTIVE_SCHEMA_PREFIX)) fail("schema", `expected prefix ${SPENT_DESCRIPTIVE_SCHEMA_PREFIX}`);
  scanKeys(d, "record");
  str(d.generatedAt, "generatedAt"); str(d.implementationHash, "implementationHash");
  str(obj(d.servedIdentity, "servedIdentity").servedClosurePinSha256, "servedIdentity.servedClosurePinSha256");
  const research = obj(d.research, "research");
  lit(research.requested, false, "research.requested"); str(research.reasonCode, "research.reasonCode");
  str(d.spentLedgerSha256, "spentLedgerSha256"); str(d.reasonsCatalogSha256, "reasonsCatalogSha256");
  const h = obj(d.honesty, "honesty");
  str(h.label, "honesty.label"); str(h.statement, "honesty.statement");
  lit(h.experimentalValidation, false, "honesty.experimentalValidation");
  lit(h.labelPromotionProposed, "none", "honesty.labelPromotionProposed");
  lit(h.evidenceKind, "screening-only", "honesty.evidenceKind");
  lit(h.spentOnly, true, "honesty.spentOnly");
  arr(d.arms, "arms");
  arr(d.sets, "sets").forEach((s, i) => checkSet(s, `sets[${i}]`));
  arr(d.modelMap, "modelMap").forEach((mv, i) => {
    const m = obj(mv, `modelMap[${i}]`);
    str(m.setId, `modelMap[${i}].setId`); arr(m.bins, `modelMap[${i}].bins`); arr(m.alsoSets, `modelMap[${i}].alsoSets`);
  });
  str(d.directionRule, "directionRule");
  arr(d.deferred, "deferred");
  return d as unknown as LpbfSpentDescriptiveDocument;
}
