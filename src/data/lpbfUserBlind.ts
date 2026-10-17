/**
 * Types, closed validators, header-only file checks, text-cell neutralising and templates of the user blind test
 * (docs/research/SPEC_research_hub_data_2026-10-14.md sections 3.4, 4.2, 4.4, 4.7). TypeScript renders and formats:
 * every number, status and label comes from the Python documents. The vocabularies, alias tables, unit tables, regexes
 * and template headers come from data/blind/lpbf-user-blind-protocol-v1.json; sentences from the wording table.
 * Nothing here makes a network request.
 */
import protocol from "../../data/blind/lpbf-user-blind-protocol-v1.json";
import wording from "../../data/blind/lpbf-user-blind-wording-v1.json";
import metadataTemplateFile from "../../data/blind/templates/blind_metadata_v1.json";
import { csvCell, toCsv } from "./lpbfExperimentPlan";
import type { ExperimentPlanDocument } from "./lpbfExperimentPlan";

export const BLIND_PROTOCOL = protocol;
export const BLIND_WORDING = wording.wording;

export class BlindDocumentError extends Error {
  constructor(message: string) {
    super(`lpbf user blind rejected: ${message}`);
    this.name = "BlindDocumentError";
  }
}
const fail = (message: string): never => { throw new BlindDocumentError(message); };

// ------------------------------------------------------------------------------------------------ small checks
type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const HEX64 = /^[0-9a-f]{64}$/;

function obj(v: unknown, path: string): Obj { return isObj(v) ? v : fail(`${path} must be an object`); }
function str(v: unknown, path: string): string { return typeof v === "string" ? v : fail(`${path} must be text`); }
function strOrNull(v: unknown, path: string): string | null { return v === null ? null : str(v, path); }
function bool(v: unknown, path: string): boolean { return typeof v === "boolean" ? v : fail(`${path} must be true or false`); }
function int(v: unknown, path: string): number {
  return typeof v === "number" && Number.isInteger(v) ? v : fail(`${path} must be a whole number`);
}
function num(v: unknown, path: string): number {
  return typeof v === "number" && Number.isFinite(v) ? v : fail(`${path} must be a finite number`);
}
function arr(v: unknown, path: string): unknown[] { return Array.isArray(v) ? v : fail(`${path} must be a list`); }
function hex64(v: unknown, path: string): string {
  return typeof v === "string" && HEX64.test(v) ? v : fail(`${path} must be 64 lower-case hex characters`);
}
function oneOf<T extends string>(v: unknown, allowed: readonly T[], path: string): T {
  return typeof v === "string" && (allowed as readonly string[]).includes(v) ? (v as T) : fail(`${path} has an unknown word`);
}
function closed(v: unknown, path: string, required: readonly string[], optional: readonly string[] = []): Obj {
  const o = obj(v, path);
  for (const k of Object.keys(o)) if (!required.includes(k) && !optional.includes(k)) fail(`${path} has an unknown key '${k}'`);
  for (const k of required) if (!(k in o)) fail(`${path} lacks '${k}'`);
  return o;
}
function strList(v: unknown, path: string): string[] { return arr(v, path).map((x, i) => str(x, `${path}[${i}]`)); }
function sha64OrNull(v: unknown, path: string): string | null { return v === null ? null : hex64(v, path); }

export const BLIND_STATUS_WORDS = protocol.statusWords as readonly string[];
export const BLIND_BLINDNESS_WORDS = protocol.blindness as readonly string[];
export const BLIND_ARM_IDS = protocol.arms as readonly string[];
export const BLIND_ARTIFACT_NAMES = protocol.artifactNames as readonly string[];
export const BLIND_REVEAL_PHRASE: string = protocol.revealPhrase;
export const BLIND_REQUEST_SCHEMA: string = protocol.requestSchema;
export const BLIND_METADATA_SCHEMA: string = protocol.metadataSchema;
export const BLIND_ACKNOWLEDGEMENTS = protocol.acknowledgements as readonly string[];
const STATE_WORDS = ["frozen", "revealed", "scored", "unreadable"] as const;

/** Exact label strings that the interface must show (task and spec 14.6, 14.7). */
export const USER_VALUE_LABEL = "Measured (user-supplied)";
export const USER_TIER_LABEL = "Trust tier: Declared";
export const SERVED_VALUE_LABEL = "Unresolved";
export const MODULE_CEILING_BADGE = "Screening only";

// ------------------------------------------------------------------------------------------------ honesty block
export type BlindHonesty = typeof protocol.honesty;

/** Throws on any honesty literal mismatch. `experimentalValidation` must be the boolean false. */
export function checkedBlindHonesty(value: unknown, path = "honesty"): BlindHonesty {
  const h = closed(value, path, Object.keys(protocol.honesty));
  if (h.experimentalValidation !== false) fail(`${path}.experimentalValidation must be the boolean false`);
  if (h.appValidation !== false) fail(`${path}.appValidation must be false`);
  if (h.labelPromotionProposed !== "none") fail(`${path}.labelPromotionProposed must be "none"`);
  if (h.evidenceKind !== "screening-only") fail(`${path}.evidenceKind must be "screening-only"`);
  if (h.dataLabel !== USER_VALUE_LABEL) fail(`${path}.dataLabel must be "${USER_VALUE_LABEL}"`);
  if (h.resultScope !== protocol.honesty.resultScope) fail(`${path}.resultScope differs`);
  if (h.protocolId !== protocol.protocolId) fail(`${path}.protocolId differs`);
  if (h.notG3oRecord !== true) fail(`${path}.notG3oRecord must be true`);
  if (h.g3Satisfied !== false) fail(`${path}.g3Satisfied must be false`);
  if (h.n3Counted !== false) fail(`${path}.n3Counted must be false`);
  const never = closed(h.neverEnters, `${path}.neverEnters`, Object.keys(protocol.honesty.neverEnters));
  for (const k of Object.keys(never)) if (never[k] !== true) fail(`${path}.neverEnters.${k} must be true`);
  return h as unknown as BlindHonesty;
}

// ------------------------------------------------------------------------------------------------ prediction-like keys
export const PREDICTION_LIKE_KEYS = ["pred", "value_um", "depth_um", "width_um", "D_obs_um", "D_pred_um", "trackDepths_um", "ledger", "rel"] as const;
const EXEMPT_SUBTREES = new Set(["predictorIdentity", "scorerIdentity"]);

/** Throws when a prediction-like key sits anywhere outside the predictor and scorer identity subtrees. */
export function assertNoPredictionKeys(value: unknown, path = "document"): void {
  if (Array.isArray(value)) { value.forEach((v, i) => assertNoPredictionKeys(v, `${path}[${i}]`)); return; }
  if (!isObj(value)) return;
  for (const [k, v] of Object.entries(value)) {
    if ((PREDICTION_LIKE_KEYS as readonly string[]).includes(k)) fail(`${path} carries the prediction-like key '${k}'`);
    if (EXEMPT_SUBTREES.has(k)) continue;
    assertNoPredictionKeys(v, `${path}.${k}`);
  }
}

// ------------------------------------------------------------------------------------------------ shared pieces
export interface BlindCounts { conditions: number; rows: number; sections: number; tracks: number }
function counts(v: unknown, path: string): BlindCounts {
  const o = closed(v, path, ["conditions", "rows", "sections", "tracks"]);
  return { conditions: int(o.conditions, `${path}.conditions`), rows: int(o.rows, `${path}.rows`), sections: int(o.sections, `${path}.sections`), tracks: int(o.tracks, `${path}.tracks`) };
}
export interface BlindGrades { power: string; beam: string; block: string }
function grades(v: unknown, path: string): BlindGrades {
  const o = closed(v, path, ["power", "beam", "block"]);
  return { power: str(o.power, `${path}.power`), beam: str(o.beam, `${path}.beam`), block: str(o.block, `${path}.block`) };
}
export interface BlindDesignChecks {
  nConditions: number; nMinMet: boolean;
  leverage: { cut: number | null; nBelow: number | null; nAtOrAbove20: number | null; ok: boolean | string };
  resolution: { evaluable: boolean; reason: string | null };
  uMNote: string | null;
}
function designChecks(v: unknown, path: string): BlindDesignChecks {
  const o = closed(v, path, ["nConditions", "nMinMet", "leverage", "resolution", "uMNote"]);
  const lev = closed(o.leverage, `${path}.leverage`, ["cut", "nBelow", "nAtOrAbove20", "ok"]);
  const res = closed(o.resolution, `${path}.resolution`, ["evaluable", "reason"]);
  const optNum = (x: unknown, p: string) => (x === null ? null : num(x, p));
  return {
    nConditions: int(o.nConditions, `${path}.nConditions`), nMinMet: bool(o.nMinMet, `${path}.nMinMet`),
    leverage: { cut: optNum(lev.cut, `${path}.leverage.cut`), nBelow: optNum(lev.nBelow, `${path}.leverage.nBelow`), nAtOrAbove20: optNum(lev.nAtOrAbove20, `${path}.leverage.nAtOrAbove20`), ok: typeof lev.ok === "string" ? lev.ok : bool(lev.ok, `${path}.leverage.ok`) },
    resolution: { evaluable: bool(res.evaluable, `${path}.resolution.evaluable`), reason: strOrNull(res.reason, `${path}.resolution.reason`) },
    uMNote: strOrNull(o.uMNote, `${path}.uMNote`),
  };
}
export interface BlindBlockIssue { code: string; text: string; fix: string }
function blockIssueObjects(v: unknown, path: string): BlindBlockIssue[] {
  return arr(v, path).map((x, i) => {
    const o = closed(x, `${path}[${i}]`, ["code", "text", "fix"]);
    return { code: str(o.code, `${path}[${i}].code`), text: str(o.text, `${path}[${i}].text`), fix: str(o.fix, `${path}[${i}].fix`) };
  });
}
export interface BlindDocumentRef { name: string; attempt: number | null }
function documentRefs(v: unknown, path: string): BlindDocumentRef[] {
  return arr(v, path).map((x, i) => {
    const o = closed(x, `${path}[${i}]`, ["name", "attempt"]);
    const name = oneOf(o.name, BLIND_ARTIFACT_NAMES, `${path}[${i}].name`);
    return { name, attempt: o.attempt === null ? null : int(o.attempt, `${path}[${i}].attempt`) };
  });
}
function statusMap(v: unknown, path: string): Record<string, string> {
  const o = obj(v, path);
  const out: Record<string, string> = {};
  for (const [k, w] of Object.entries(o)) {
    if (k === "blindness") out[k] = oneOf(w, BLIND_BLINDNESS_WORDS, `${path}.${k}`);
    else { oneOf(k, BLIND_ARM_IDS, `${path} arm`); out[k] = oneOf(w, BLIND_STATUS_WORDS, `${path}.${k}`); }
  }
  return out;
}

// ------------------------------------------------------------------------------------------------ preview
export interface BlindParsedInput {
  condition: string; P_W: number; v_mm_s: number; beamDeclared_um: number; beamQuantity: string; beamDefinition: string;
  d_1e2_um: number; tracks: number; rows: number;
}
export interface BlindUnitRead { header: string; unitRead: string | null; factor: number }
export interface BlindPreview {
  schema: "lpbf-user-blind-preview-1"; previewSha256: string; overlapSha256: string; metadataSha256: string; inputsSha256: string;
  protocolSha256: string; columns: string[]; aliases: { header: string; canonical: string; unit: string | null; factor: number }[];
  dialect: string; counts: BlindCounts; excludedInputs: unknown[]; grades: BlindGrades; blockIssues: BlindBlockIssue[]; labels: string[];
  designChecks: BlindDesignChecks;
  overlap: { earlierTests: { freezeKey: string; kind: string; nConditions: number }[]; publishedSets: { datasetId: string; nConditions: number }[]; calibrationStores: { storeId: string; kind: string; nConditions: number }[]; buildJobHistory: { nConditions: number }[] };
  bestReachable: { status: string; reasons: string[] };
  acknowledgementsRequired: string[];
  budget: { conditions: number; solverCalls: number; cap: number; estimate_s: number; queueNote: string };
  divergences: string[]; parsedInputs: BlindParsedInput[]; units: Record<string, BlindUnitRead>;
  predictorPinned: boolean; predictorUnpinnedFiles: string[];
  research: { requested: boolean; reasonCode: string; text: string };
  honesty: BlindHonesty; protocolId: string;
}
const PREVIEW_KEYS = ["schema", "protocolId", "previewSha256", "metadataSha256", "inputsSha256", "protocolSha256", "overlapSha256", "columns", "aliases", "dialect", "counts", "excludedInputs", "grades", "blockIssues", "labels", "designChecks", "overlap", "bestReachable", "acknowledgementsRequired", "budget", "divergences", "parsedInputs", "units", "predictorPinned", "predictorUnpinnedFiles", "research", "honesty"];

export function checkedBlindPreview(value: unknown): BlindPreview {
  const o = closed(value, "preview", PREVIEW_KEYS);
  if (o.schema !== "lpbf-user-blind-preview-1") fail("preview.schema differs");
  if (o.protocolId !== protocol.protocolId) fail("preview.protocolId differs");
  checkedBlindHonesty(o.honesty, "preview.honesty");
  assertNoPredictionKeys(o, "preview");
  hex64(o.previewSha256, "preview.previewSha256"); hex64(o.overlapSha256, "preview.overlapSha256");
  hex64(o.metadataSha256, "preview.metadataSha256"); hex64(o.inputsSha256, "preview.inputsSha256"); hex64(o.protocolSha256, "preview.protocolSha256");
  strList(o.columns, "preview.columns");
  arr(o.aliases, "preview.aliases").forEach((a, i) => {
    const e = closed(a, `preview.aliases[${i}]`, ["header", "canonical", "unit", "factor"]);
    str(e.header, "alias.header"); str(e.canonical, "alias.canonical"); strOrNull(e.unit, "alias.unit"); num(e.factor, "alias.factor");
  });
  oneOf(o.dialect, protocol.enums.csvDialect, "preview.dialect");
  counts(o.counts, "preview.counts"); arr(o.excludedInputs, "preview.excludedInputs");
  grades(o.grades, "preview.grades");
  blockIssueObjects(o.blockIssues, "preview.blockIssues");
  strList(o.labels, "preview.labels");
  designChecks(o.designChecks, "preview.designChecks");
  const ov = closed(o.overlap, "preview.overlap", ["earlierTests", "publishedSets", "calibrationStores", "buildJobHistory"]);
  arr(ov.earlierTests, "overlap.earlierTests").forEach((e, i) => { const x = closed(e, `overlap.earlierTests[${i}]`, ["freezeKey", "kind", "nConditions"]); hex64(x.freezeKey, "overlap.freezeKey"); str(x.kind, "kind"); int(x.nConditions, "nConditions"); });
  arr(ov.publishedSets, "overlap.publishedSets").forEach((e, i) => { const x = closed(e, `overlap.publishedSets[${i}]`, ["datasetId", "nConditions"]); str(x.datasetId, "datasetId"); int(x.nConditions, "nConditions"); });
  arr(ov.calibrationStores, "overlap.calibrationStores").forEach((e, i) => { const x = closed(e, `overlap.calibrationStores[${i}]`, ["storeId", "kind", "nConditions"]); str(x.storeId, "storeId"); str(x.kind, "kind"); int(x.nConditions, "nConditions"); });
  arr(ov.buildJobHistory, "overlap.buildJobHistory").forEach((e, i) => { const x = closed(e, `overlap.buildJobHistory[${i}]`, ["nConditions"]); int(x.nConditions, "nConditions"); });
  const best = closed(o.bestReachable, "preview.bestReachable", ["status", "reasons"]);
  oneOf(best.status, BLIND_STATUS_WORDS, "preview.bestReachable.status"); strList(best.reasons, "bestReachable.reasons");
  strList(o.acknowledgementsRequired, "preview.acknowledgementsRequired").forEach(a => oneOf(a, BLIND_ACKNOWLEDGEMENTS, "acknowledgementsRequired"));
  const b = closed(o.budget, "preview.budget", ["conditions", "solverCalls", "cap", "estimate_s", "queueNote"]);
  int(b.conditions, "budget.conditions"); int(b.solverCalls, "budget.solverCalls"); int(b.cap, "budget.cap"); num(b.estimate_s, "budget.estimate_s"); str(b.queueNote, "budget.queueNote");
  strList(o.divergences, "preview.divergences");
  arr(o.parsedInputs, "preview.parsedInputs").forEach((p, i) => {
    const x = closed(p, `preview.parsedInputs[${i}]`, ["condition", "P_W", "v_mm_s", "beamDeclared_um", "beamQuantity", "beamDefinition", "d_1e2_um", "tracks", "rows"]);
    str(x.condition, "condition"); for (const k of ["P_W", "v_mm_s", "beamDeclared_um", "d_1e2_um"]) num(x[k], k);
    str(x.beamQuantity, "beamQuantity"); str(x.beamDefinition, "beamDefinition"); int(x.tracks, "tracks"); int(x.rows, "rows");
  });
  for (const [k, u] of Object.entries(obj(o.units, "preview.units"))) {
    const x = closed(u, `preview.units.${k}`, ["header", "unitRead", "factor"]);
    str(x.header, "units.header"); strOrNull(x.unitRead, "units.unitRead"); num(x.factor, "units.factor");
  }
  bool(o.predictorPinned, "preview.predictorPinned"); strList(o.predictorUnpinnedFiles, "preview.predictorUnpinnedFiles");
  const r = closed(o.research, "preview.research", ["requested", "reasonCode", "text"]);
  bool(r.requested, "research.requested"); str(r.reasonCode, "research.reasonCode"); str(r.text, "research.text");
  return o as unknown as BlindPreview;
}

// ------------------------------------------------------------------------------------------------ receipt
export interface BlindArmFrozen { id: string; available: number; of: number; reasonCodes: string[] }
export interface BlindReceipt {
  schema: "lpbf-user-blind-receipt-1"; freezeKey: string; freezeSha256: string; predictionsSha256: string; inputsSha256: string;
  metadataSha256: string; previewSha256: string; targetCommitmentSha256: string | null; createdAt: string; alreadyFrozen: boolean;
  blockLabel: string; alloy: string; counts: BlindCounts; acknowledgements: Record<string, true>; excludedInputs: unknown[];
  designChecks: BlindDesignChecks; grades: BlindGrades; blockIssues: unknown[]; labels: string[]; armsFrozen: BlindArmFrozen[];
  predictorIdentity: Obj; scorerIdentity: Obj; ledgerSeq: number; ledgerEntryHash: string; predictionsWithheld: true;
  receiptLine: string; anchorAdvice: string; honesty: BlindHonesty; documents?: BlindDocumentRef[]; provenance?: Obj; runKind?: unknown;
}
const RECEIPT_REQUIRED = ["schema", "freezeKey", "freezeSha256", "predictionsSha256", "inputsSha256", "metadataSha256", "previewSha256", "targetCommitmentSha256", "createdAt", "alreadyFrozen", "blockLabel", "alloy", "counts", "acknowledgements", "excludedInputs", "designChecks", "grades", "blockIssues", "labels", "armsFrozen", "predictorIdentity", "scorerIdentity", "ledgerSeq", "ledgerEntryHash", "predictionsWithheld", "receiptLine", "anchorAdvice", "honesty"];
const RECEIPT_OPTIONAL = ["documents", "provenance", "runKind"];

export function checkedBlindReceipt(value: unknown, path = "receipt"): BlindReceipt {
  const o = closed(value, path, RECEIPT_REQUIRED, RECEIPT_OPTIONAL);
  if (o.schema !== "lpbf-user-blind-receipt-1") fail(`${path}.schema differs`);
  checkedBlindHonesty(o.honesty, `${path}.honesty`);
  assertNoPredictionKeys(o, path);
  for (const k of ["freezeKey", "freezeSha256", "predictionsSha256", "inputsSha256", "metadataSha256", "previewSha256", "ledgerEntryHash"]) hex64(o[k], `${path}.${k}`);
  sha64OrNull(o.targetCommitmentSha256, `${path}.targetCommitmentSha256`);
  str(o.createdAt, `${path}.createdAt`); bool(o.alreadyFrozen, `${path}.alreadyFrozen`); str(o.blockLabel, `${path}.blockLabel`);
  oneOf(o.alloy, protocol.enums.alloy, `${path}.alloy`);
  counts(o.counts, `${path}.counts`);
  const acks = obj(o.acknowledgements, `${path}.acknowledgements`);
  for (const [k, v] of Object.entries(acks)) { oneOf(k, BLIND_ACKNOWLEDGEMENTS, `${path}.acknowledgements`); if (v !== true) fail(`${path}.acknowledgements.${k} must be true`); }
  arr(o.excludedInputs, `${path}.excludedInputs`);
  designChecks(o.designChecks, `${path}.designChecks`); grades(o.grades, `${path}.grades`);
  arr(o.blockIssues, `${path}.blockIssues`); strList(o.labels, `${path}.labels`);
  arr(o.armsFrozen, `${path}.armsFrozen`).forEach((a, i) => {
    const x = closed(a, `${path}.armsFrozen[${i}]`, ["id", "available", "of", "reasonCodes"]);
    oneOf(x.id, BLIND_ARM_IDS, "armsFrozen.id"); int(x.available, "available"); int(x.of, "of"); strList(x.reasonCodes, "reasonCodes");
  });
  obj(o.predictorIdentity, `${path}.predictorIdentity`); obj(o.scorerIdentity, `${path}.scorerIdentity`);
  int(o.ledgerSeq, `${path}.ledgerSeq`);
  if (o.predictionsWithheld !== true) fail(`${path}.predictionsWithheld must be true`);
  str(o.receiptLine, `${path}.receiptLine`); str(o.anchorAdvice, `${path}.anchorAdvice`);
  if ("documents" in o) documentRefs(o.documents, `${path}.documents`);
  if ("provenance" in o) obj(o.provenance, `${path}.provenance`);
  return o as unknown as BlindReceipt;
}

// ------------------------------------------------------------------------------------------------ report
export interface BlindArmStats {
  n: number; median: number | string | null; p75: number | string | null; p90: number | string | null; meanSigned: number | string | null; maxApe: number | string | null;
  nFailed: number; nNotFormed: number; thresholdsMet: Record<string, boolean>; allThresholdsMet: boolean;
}
export interface BlindArm {
  status: string; sentence: string; reason: string | null; coverage: { k: number; n: number; unavailable: number };
  stats: BlindArmStats | null; unavailableConditions: string[]; bootstrap95?: Obj; marginal?: string[]; servedBins?: Obj;
}
export type BlindRel = number | "inf" | "-inf" | null;
export interface BlindLedgerPred { value_um: number | null; status: string; reasonCode: string | null; rel: BlindRel; sourceEvidenceKind?: string; sourceReason?: string; sourceLocator?: unknown }
export interface BlindLedgerRow {
  condition: string; P_W: number; v_mm_s: number; d_1e2_um: number; indexBin: string; nTracks: number; trackDepths_um: number[];
  D_obs_um: number | null; observed: { sourceEvidenceKind: string; tier: string; sourceLocator: Obj }; notFormed: boolean;
  pred: Record<string, BlindLedgerPred>; widthObs_um: number | null; widthModel_um: number | null;
  inputSensitivityRange_um: { min_um: number; max_um: number; note: string } | null;
}
export interface BlindReport {
  schema: "lpbf-user-blind-report-1"; protocolId: string; title: string; banner: string; freezeKey: string; freezeSha256: string; targetsSha256: string;
  commitment: { declared: boolean; matched: boolean | null }; attempt: { n: number; earlierTargetsSha256: string[] };
  blindness: { status: string; sentence: string; reasons: string[]; revealEvents: unknown[]; overlap?: unknown[]; exposuresAfterCommitment: unknown[]; statuses?: unknown[] };
  predictor: Obj; scorer: Obj; divergences: { id: string; melt: string; rule: string; applied: boolean }[]; wordingSha256: string;
  thresholds: Obj; grades: BlindGrades; blockIssues: string[]; resolution: Obj; leverage: Obj; arms: Record<string, BlindArm>;
  commonSubset: Obj; labels: string[]; fragile: Obj; ledger: BlindLedgerRow[];
  excluded: { inputs: unknown[]; targets: { row: number; condition: string; track: string | null; section: string | null; status: string }[] };
  exclusions: { sections: string; tracks: string; conditions: string }; lostConditions: string[]; notFormed: { conditions: string[] };
  userValueLabel: { sourceEvidenceKind: string; tier: string };
  servedValueLabel: { sourceEvidenceKind: string; reason: string; text: string };
  honesty: BlindHonesty;
}
const REPORT_KEYS = ["schema", "protocolId", "title", "banner", "freezeKey", "freezeSha256", "targetsSha256", "commitment", "attempt", "blindness", "predictor", "scorer", "divergences", "wordingSha256", "thresholds", "grades", "blockIssues", "resolution", "leverage", "arms", "commonSubset", "labels", "fragile", "ledger", "excluded", "exclusions", "lostConditions", "notFormed", "userValueLabel", "servedValueLabel", "honesty"];
const PRED_ARMS = [...protocol.arms] as string[];
const numOrWord = (v: unknown, p: string) => (v === null || v === "inf" || v === "-inf" ? v : num(v, p));

export function checkedBlindReport(value: unknown): BlindReport {
  const o = closed(value, "report", REPORT_KEYS);
  if (o.schema !== "lpbf-user-blind-report-1") fail("report.schema differs");
  if (o.protocolId !== protocol.protocolId) fail("report.protocolId differs");
  checkedBlindHonesty(o.honesty, "report.honesty");
  hex64(o.freezeKey, "report.freezeKey"); hex64(o.freezeSha256, "report.freezeSha256"); hex64(o.targetsSha256, "report.targetsSha256"); hex64(o.wordingSha256, "report.wordingSha256");
  str(o.title, "report.title"); str(o.banner, "report.banner");
  const com = closed(o.commitment, "report.commitment", ["declared", "matched"]);
  bool(com.declared, "commitment.declared"); if (com.matched !== null) bool(com.matched, "commitment.matched");
  const at = closed(o.attempt, "report.attempt", ["n", "earlierTargetsSha256"]);
  int(at.n, "attempt.n"); arr(at.earlierTargetsSha256, "attempt.earlierTargetsSha256").forEach(s => hex64(s, "earlierTargetsSha256"));
  const bl = closed(o.blindness, "report.blindness", ["status", "sentence", "reasons", "revealEvents", "exposuresAfterCommitment"], ["overlap", "statuses"]);
  oneOf(bl.status, BLIND_BLINDNESS_WORDS, "report.blindness.status"); str(bl.sentence, "blindness.sentence"); strList(bl.reasons, "blindness.reasons");
  arr(bl.revealEvents, "blindness.revealEvents"); arr(bl.exposuresAfterCommitment, "blindness.exposuresAfterCommitment");
  obj(o.predictor, "report.predictor"); obj(o.scorer, "report.scorer");
  arr(o.divergences, "report.divergences").forEach((d, i) => {
    const x = closed(d, `report.divergences[${i}]`, ["id", "melt", "rule", "applied"]);
    str(x.id, "divergence.id"); str(x.melt, "divergence.melt"); str(x.rule, "divergence.rule"); bool(x.applied, "divergence.applied");
  });
  obj(o.thresholds, "report.thresholds"); grades(o.grades, "report.grades"); strList(o.blockIssues, "report.blockIssues");
  obj(o.resolution, "report.resolution"); obj(o.leverage, "report.leverage"); obj(o.commonSubset, "report.commonSubset");
  strList(o.labels, "report.labels"); obj(o.fragile, "report.fragile");
  const arms = obj(o.arms, "report.arms");
  for (const [id, a] of Object.entries(arms)) {
    oneOf(id, BLIND_ARM_IDS, "report.arms arm");
    const x = closed(a, `report.arms.${id}`, ["status", "sentence", "reason", "coverage", "stats", "unavailableConditions"], ["bootstrap95", "marginal", "servedBins", "bandCoverage", "consistencyCounts"]);
    oneOf(x.status, BLIND_STATUS_WORDS, `report.arms.${id}.status`); str(x.sentence, "arm.sentence"); strOrNull(x.reason, "arm.reason");
    const cov = closed(x.coverage, "arm.coverage", ["k", "n", "unavailable"]); int(cov.k, "k"); int(cov.n, "n"); int(cov.unavailable, "unavailable");
    if (x.stats !== null) {
      const s = closed(x.stats, `report.arms.${id}.stats`, ["n", "median", "p75", "p90", "meanSigned", "maxApe", "nFailed", "nNotFormed", "thresholdsMet", "allThresholdsMet"]);
      int(s.n, "stats.n"); for (const k of ["median", "p75", "p90", "meanSigned", "maxApe"]) numOrWord(s[k], `stats.${k}`);
      int(s.nFailed, "stats.nFailed"); int(s.nNotFormed, "stats.nNotFormed"); bool(s.allThresholdsMet, "stats.allThresholdsMet");
      for (const [k, v] of Object.entries(obj(s.thresholdsMet, "stats.thresholdsMet"))) bool(v, `thresholdsMet.${k}`);
    }
    strList(x.unavailableConditions, "arm.unavailableConditions");
  }
  if (!("served" in arms)) fail("report.arms lacks the served arm");
  arr(o.ledger, "report.ledger").forEach((r, i) => {
    const p = `report.ledger[${i}]`;
    const x = closed(r, p, ["condition", "P_W", "v_mm_s", "d_1e2_um", "indexBin", "nTracks", "trackDepths_um", "D_obs_um", "observed", "notFormed", "pred", "widthObs_um", "widthModel_um", "inputSensitivityRange_um"]);
    str(x.condition, `${p}.condition`); for (const k of ["P_W", "v_mm_s", "d_1e2_um"]) num(x[k], `${p}.${k}`);
    str(x.indexBin, `${p}.indexBin`); int(x.nTracks, `${p}.nTracks`);
    arr(x.trackDepths_um, `${p}.trackDepths_um`).forEach(d => num(d, "trackDepths_um"));
    if (x.D_obs_um !== null) num(x.D_obs_um, `${p}.D_obs_um`);
    bool(x.notFormed, `${p}.notFormed`);
    if (x.widthObs_um !== null) num(x.widthObs_um, `${p}.widthObs_um`);
    if (x.widthModel_um !== null) num(x.widthModel_um, `${p}.widthModel_um`);
    const ob = closed(x.observed, `${p}.observed`, ["sourceEvidenceKind", "tier", "sourceLocator"]);
    if (ob.sourceEvidenceKind !== USER_VALUE_LABEL) fail(`${p}.observed.sourceEvidenceKind must be "${USER_VALUE_LABEL}"`);
    if (ob.tier !== "Declared") fail(`${p}.observed.tier must be "Declared"`);
    obj(ob.sourceLocator, `${p}.observed.sourceLocator`);
    for (const [arm, pv] of Object.entries(obj(x.pred, `${p}.pred`))) {
      if (!PRED_ARMS.includes(arm)) fail(`${p}.pred has an unknown arm`);
      const e = closed(pv, `${p}.pred.${arm}`, ["value_um", "status", "reasonCode", "rel"], ["sourceEvidenceKind", "sourceReason", "sourceLocator"]);
      if (e.value_um !== null) num(e.value_um, "value_um");
      str(e.status, "pred.status"); strOrNull(e.reasonCode, "pred.reasonCode"); numOrWord(e.rel, "pred.rel");
      if ("sourceEvidenceKind" in e && e.sourceEvidenceKind !== SERVED_VALUE_LABEL) fail(`${p}.pred.${arm}.sourceEvidenceKind must be "${SERVED_VALUE_LABEL}"`);
    }
    if (x.inputSensitivityRange_um !== null) {
      const sr = closed(x.inputSensitivityRange_um, `${p}.inputSensitivityRange_um`, ["min_um", "max_um", "note"]);
      num(sr.min_um, "min_um"); num(sr.max_um, "max_um"); str(sr.note, "note");
    }
  });
  const ex = closed(o.excluded, "report.excluded", ["inputs", "targets"]);
  arr(ex.inputs, "excluded.inputs");
  arr(ex.targets, "excluded.targets").forEach((t, i) => {
    const x = closed(t, `excluded.targets[${i}]`, ["row", "condition", "track", "section", "status"]);
    int(x.row, "row"); str(x.condition, "condition"); strOrNull(x.track, "track"); strOrNull(x.section, "section"); oneOf(x.status, protocol.lossStatus, "excluded status");
  });
  const exc = closed(o.exclusions, "report.exclusions", ["sections", "tracks", "conditions"]);
  str(exc.sections, "sections"); str(exc.tracks, "tracks"); str(exc.conditions, "conditions");
  strList(o.lostConditions, "report.lostConditions");
  strList(closed(o.notFormed, "report.notFormed", ["conditions"]).conditions, "notFormed.conditions");
  const uv = closed(o.userValueLabel, "report.userValueLabel", ["sourceEvidenceKind", "tier"]);
  if (uv.sourceEvidenceKind !== USER_VALUE_LABEL || uv.tier !== "Declared") fail("report.userValueLabel differs");
  const sv = closed(o.servedValueLabel, "report.servedValueLabel", ["sourceEvidenceKind", "reason", "text"]);
  if (sv.sourceEvidenceKind !== SERVED_VALUE_LABEL) fail(`report.servedValueLabel.sourceEvidenceKind must be "${SERVED_VALUE_LABEL}"`);
  str(sv.reason, "servedValueLabel.reason"); str(sv.text, "servedValueLabel.text");
  return o as unknown as BlindReport;
}

// ------------------------------------------------------------------------------------------------ list and get
export interface BlindListEntry {
  freezeKey: string; state: string; blockLabel?: string; alloy?: string; createdAt?: string; counts?: BlindCounts;
  attempts?: number; latestStatus?: { served: string; blindness: string } | null;
}
export interface BlindList {
  schema: "lpbf-user-blind-list-1"; entries: BlindListEntry[]; total: number; page: number; readOnly: boolean; sharedHost: boolean;
  storeId: string | null; lockDomain: string | null; ledgerOk: boolean; incompleteStaging: number; honesty: BlindHonesty;
}
export function checkedBlindList(value: unknown): BlindList {
  const o = closed(value, "list", ["schema", "entries", "total", "page", "readOnly", "sharedHost", "storeId", "lockDomain", "ledgerOk", "incompleteStaging", "honesty"]);
  if (o.schema !== "lpbf-user-blind-list-1") fail("list.schema differs");
  checkedBlindHonesty(o.honesty, "list.honesty");
  assertNoPredictionKeys(o, "list");
  arr(o.entries, "list.entries").forEach((e, i) => {
    const p = `list.entries[${i}]`;
    const x = closed(e, p, ["freezeKey", "state"], ["blockLabel", "alloy", "createdAt", "counts", "attempts", "latestStatus"]);
    hex64(x.freezeKey, `${p}.freezeKey`); oneOf(x.state, STATE_WORDS, `${p}.state`);
    if (x.state !== "unreadable") {
      str(x.blockLabel, `${p}.blockLabel`); oneOf(x.alloy, protocol.enums.alloy, `${p}.alloy`); str(x.createdAt, `${p}.createdAt`);
      counts(x.counts, `${p}.counts`); int(x.attempts, `${p}.attempts`);
      if (x.latestStatus !== null) {
        const ls = closed(x.latestStatus, `${p}.latestStatus`, ["served", "blindness"]);
        oneOf(ls.served, BLIND_STATUS_WORDS, `${p}.latestStatus.served`); oneOf(ls.blindness, BLIND_BLINDNESS_WORDS, `${p}.latestStatus.blindness`);
      }
    }
  });
  int(o.total, "list.total"); int(o.page, "list.page"); bool(o.readOnly, "list.readOnly"); bool(o.sharedHost, "list.sharedHost");
  strOrNull(o.storeId, "list.storeId"); strOrNull(o.lockDomain, "list.lockDomain"); bool(o.ledgerOk, "list.ledgerOk"); int(o.incompleteStaging, "list.incompleteStaging");
  return o as unknown as BlindList;
}

export interface BlindGetDocument { name: string; attempt: number | null; jobId: string | null; jobRecordPresent: boolean; sha256?: string; size?: number }
export interface BlindGetAttempt { n: number; state?: string; targetsSha256?: string; blindness?: string; statuses?: Record<string, string>; reportSha256?: string }
export interface BlindGet {
  schema: "lpbf-user-blind-get-1"; freezeKey: string; receipt: BlindReceipt; revealEvents: { seq: number; at: string; jobId: string | null }[];
  attempts: BlindGetAttempt[]; documents: BlindGetDocument[]; readOnly: boolean; sharedHost: boolean; honesty: BlindHonesty;
}
export function checkedBlindGet(value: unknown): BlindGet {
  const o = closed(value, "get", ["schema", "freezeKey", "receipt", "revealEvents", "attempts", "documents", "readOnly", "sharedHost", "honesty"]);
  if (o.schema !== "lpbf-user-blind-get-1") fail("get.schema differs");
  checkedBlindHonesty(o.honesty, "get.honesty");
  assertNoPredictionKeys(o, "get");
  hex64(o.freezeKey, "get.freezeKey");
  const receipt = checkedBlindReceipt(o.receipt, "get.receipt");
  if (receipt.freezeKey !== o.freezeKey) fail("get.receipt names another freeze");
  arr(o.revealEvents, "get.revealEvents").forEach((e, i) => { const x = closed(e, `get.revealEvents[${i}]`, ["seq", "at", "jobId"]); int(x.seq, "seq"); str(x.at, "at"); strOrNull(x.jobId, "jobId"); });
  arr(o.attempts, "get.attempts").forEach((a, i) => {
    const p = `get.attempts[${i}]`;
    const x = closed(a, p, ["n"], ["state", "targetsSha256", "blindness", "statuses", "reportSha256"]);
    int(x.n, `${p}.n`);
    if (x.state !== undefined) { if (x.state !== "unreadable") fail(`${p}.state has an unknown word`); return; }
    hex64(x.targetsSha256, `${p}.targetsSha256`); hex64(x.reportSha256, `${p}.reportSha256`);
    oneOf(x.blindness, BLIND_BLINDNESS_WORDS, `${p}.blindness`); statusMap(x.statuses, `${p}.statuses`);
  });
  arr(o.documents, "get.documents").forEach((d, i) => {
    const p = `get.documents[${i}]`;
    const x = closed(d, p, ["name", "attempt", "jobId", "jobRecordPresent"], ["sha256", "size"]);
    oneOf(x.name, BLIND_ARTIFACT_NAMES, `${p}.name`);
    if (x.attempt !== null) int(x.attempt, `${p}.attempt`);
    strOrNull(x.jobId, `${p}.jobId`); bool(x.jobRecordPresent, `${p}.jobRecordPresent`);
    if (x.sha256 !== undefined) hex64(x.sha256, `${p}.sha256`);
    if (x.size !== undefined) int(x.size, `${p}.size`);
  });
  bool(o.readOnly, "get.readOnly"); bool(o.sharedHost, "get.sharedHost");
  return o as unknown as BlindGet;
}

// ------------------------------------------------------------------------------------------------ queued job results
export type BlindFreezeResult = BlindReceipt;
export function checkedBlindFreezeResult(value: unknown): BlindFreezeResult {
  const receipt = checkedBlindReceipt(value, "freeze result");
  if (!receipt.documents || !receipt.provenance) fail("freeze result lacks documents or provenance");
  return receipt;
}
export interface BlindRevealResult { freezeKey: string; revealN: number; ledgerSeq: number; documents: BlindDocumentRef[]; honesty: BlindHonesty; provenance: Obj }
export function checkedBlindRevealResult(value: unknown): BlindRevealResult {
  const o = closed(value, "reveal result", ["freezeKey", "revealN", "ledgerSeq", "documents", "honesty", "provenance"], ["runKind"]);
  checkedBlindHonesty(o.honesty, "reveal result.honesty"); assertNoPredictionKeys(o, "reveal result");
  hex64(o.freezeKey, "reveal result.freezeKey"); int(o.revealN, "revealN"); int(o.ledgerSeq, "ledgerSeq");
  documentRefs(o.documents, "reveal result.documents"); obj(o.provenance, "reveal result.provenance");
  return o as unknown as BlindRevealResult;
}
export interface BlindScoreResult { freezeKey: string; attempt: number; alreadyScored: boolean; reportSha256: string; statuses: Record<string, string>; documents: BlindDocumentRef[]; honesty: BlindHonesty; provenance: Obj }
export function checkedBlindScoreResult(value: unknown): BlindScoreResult {
  const o = closed(value, "score result", ["freezeKey", "attempt", "alreadyScored", "reportSha256", "statuses", "documents", "honesty", "provenance"], ["runKind"]);
  checkedBlindHonesty(o.honesty, "score result.honesty"); assertNoPredictionKeys(o, "score result");
  hex64(o.freezeKey, "score result.freezeKey"); int(o.attempt, "attempt"); bool(o.alreadyScored, "alreadyScored"); hex64(o.reportSha256, "reportSha256");
  statusMap(o.statuses, "score result.statuses"); documentRefs(o.documents, "score result.documents"); obj(o.provenance, "score result.provenance");
  return o as unknown as BlindScoreResult;
}
export interface BlindBundleResult { freezeKey: string; bundleN: number; sha256: string; size: number; documents: BlindDocumentRef[]; honesty: BlindHonesty; provenance: Obj }
export function checkedBlindBundleResult(value: unknown): BlindBundleResult {
  const o = closed(value, "bundle result", ["freezeKey", "bundleN", "sha256", "size", "documents", "honesty", "provenance"], ["runKind"]);
  checkedBlindHonesty(o.honesty, "bundle result.honesty"); assertNoPredictionKeys(o, "bundle result");
  hex64(o.freezeKey, "bundle result.freezeKey"); int(o.bundleN, "bundleN"); hex64(o.sha256, "sha256"); int(o.size, "size");
  documentRefs(o.documents, "bundle result.documents"); obj(o.provenance, "bundle result.provenance");
  return o as unknown as BlindBundleResult;
}
export interface BlindOpenResult { freezeKey: string; name: string; attempt: number | null; sha256: string; size: number; honesty: BlindHonesty; provenance: Obj }
export function checkedBlindOpenResult(value: unknown): BlindOpenResult {
  const o = closed(value, "open result", ["freezeKey", "name", "attempt", "sha256", "size", "honesty", "provenance"], ["runKind"]);
  checkedBlindHonesty(o.honesty, "open result.honesty"); assertNoPredictionKeys(o, "open result");
  hex64(o.freezeKey, "open result.freezeKey"); oneOf(o.name, BLIND_ARTIFACT_NAMES, "open result.name");
  if (o.attempt !== null) int(o.attempt, "attempt");
  hex64(o.sha256, "sha256"); int(o.size, "size"); obj(o.provenance, "open result.provenance");
  return o as unknown as BlindOpenResult;
}

export type BlindJobType = typeof protocol.requestTypes.jobs[number];
const JOB_RESULT_CHECKERS: Record<BlindJobType, (v: unknown) => unknown> = {
  "user-blind-freeze": checkedBlindFreezeResult,
  "user-blind-reveal": checkedBlindRevealResult,
  "user-blind-score": checkedBlindScoreResult,
  "user-blind-bundle": checkedBlindBundleResult,
  "user-blind-open": checkedBlindOpenResult,
};
export function checkedBlindJobResult(jobType: BlindJobType, value: unknown): unknown {
  const check = JOB_RESULT_CHECKERS[jobType];
  return check ? check(value) : fail("unknown job type");
}

// ------------------------------------------------------------------------------------------------ text cells and CSV
const FORMULA_LEAD = ["=", "+", "-", "@", "\t", "\r"];
/** A text cell starting with = + - @ tab or CR gets a leading apostrophe; numbers (negative ones too) are unchanged. */
export function blindCsvTextCell(value: string | number | boolean | null | undefined): string | number {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return value;
  return value.length > 0 && FORMULA_LEAD.includes(value[0]) ? `'${value}` : value;
}
export { csvCell, toCsv };

const EXAMPLE_VALUES: Record<string, string | number> = {
  condition_id: `C-${protocol.regex.syntheticMarker}`, track_id: `T-${protocol.regex.syntheticMarker}-1`, section_id: "S1",
  power_W: 200, speed_mm_s: 800, spot_um: 80, power_u_k1_W: "", depth_um: "", width_um: "", depth_u_um: "", depth_status: "not-measured",
};
/** Inputs template: the protocol record's header and one row whose ids carry the synthetic marker. */
export function blindInputsTemplateCsv(): string {
  const header = protocol.templates.inputs;
  return toCsv(header, [header.map(c => blindCsvTextCell(EXAMPLE_VALUES[c] ?? ""))]);
}
export function blindTargetsTemplateCsv(): string {
  const header = protocol.templates.targets;
  return toCsv(header, [header.map(c => blindCsvTextCell(EXAMPLE_VALUES[c] ?? ""))]);
}
export function blindMetadataTemplateJson(): string { return `${JSON.stringify(metadataTemplateFile, null, 1)}\n`; }

/** Inputs template written from a plan's tracks: track id, power, speed and spot only, never a score or a spread. */
export function blindInputsFromPlanCsv(plan: Pick<ExperimentPlanDocument, "points">): string {
  const header = ["track_id", "power_W", "speed_mm_s", "spot_um"];
  const rows = [...plan.points].sort((a, b) => a.layout.printOrder - b.layout.printOrder)
    .map(p => [blindCsvTextCell(p.trackId), p.power_W, p.speed_mm_s, p.beamDiameter_um]);
  return toCsv(header, rows);
}

// ------------------------------------------------------------------------------------------------ header-only checks
export type BlindCsvDialect = "comma-dot" | "semicolon-dot" | "semicolon-comma";
export interface BlindHeaderIssue { code: string; message: string }
export interface BlindHeaderMapping { header: string; canonical: string; unit: string | null; factor: number }
export interface BlindHeaderCheck {
  ok: boolean; issues: BlindHeaderIssue[]; warnings: string[]; header: string[]; mapped: Record<string, BlindHeaderMapping>;
  echoes: BlindHeaderMapping[]; labels: string[]; ignored: string[]; exampleRow: boolean; dataLines: number;
}
const TARGET_LIKE = new RegExp(protocol.regex.targetLike, "i");
const UNITS = protocol.units as Record<string, Record<string, number>>;
const UNITLESS = protocol.unitlessHeaders as Record<string, string>;
const CANONICAL_UNIT = protocol.canonicalUnit as Record<string, string>;
const SEPARATORS: Record<BlindCsvDialect, string> = { "comma-dot": ",", "semicolon-dot": ";", "semicolon-comma": ";" };
/** Python str.casefold on the one letter that matters here: the micro sign folds to the Greek mu. */
const fold = (s: string) => s.toLowerCase().replace(/µ/g, "μ");
const UNIT_TABLE_FOLDED: Record<string, Record<string, number>> = Object.fromEntries(
  Object.entries(UNITS).map(([c, t]) => [c, Object.fromEntries(Object.entries(t).map(([u, f]) => [fold(u), f]))]));
const UNIT_SUFFIX = /^(?<base>.*?)\s*(?:\((?<b1>[^()]*)\)|\[(?<b2>[^[\]]*)\])\s*$/;

function splitUnit(header: string): [string, string | null] {
  const m = UNIT_SUFFIX.exec(header);
  if (m?.groups && m.groups.base.trim()) return [m.groups.base.trim(), (m.groups.b1 ?? m.groups.b2).trim()];
  return [header, null];
}

/** One CSV line split on the separator, honouring double quotes. Returns null for an unterminated quote. */
export function splitCsvLine(line: string, separator: string): string[] | null {
  const cells: string[] = [];
  let cur = "", quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"') { if (line[i + 1] === '"') { cur += '"'; i += 1; } else quoted = false; } else cur += ch;
    } else if (ch === '"' && cur === "") quoted = true;
    else if (ch === separator) { cells.push(cur); cur = ""; } else cur += ch;
  }
  if (quoted) return null;
  cells.push(cur);
  return cells;
}

interface MapResult { mapped: Record<string, BlindHeaderMapping>; echoes: BlindHeaderMapping[]; labels: string[]; ignored: string[]; issues: BlindHeaderIssue[] }

/** Port of map_header in python/lpbf_user_blind_inputs.py. Stops at the first refusal, like Python. */
function mapHeader(header: string[], columns: readonly string[], aliases: Record<string, readonly string[]>, inputs: boolean): MapResult {
  const lookup = new Map<string, string>();
  for (const canon of columns) {
    lookup.set(fold(canon), canon);
    for (const a of aliases[canon] ?? []) lookup.set(fold(a), canon);
  }
  const res: MapResult = { mapped: {}, echoes: [], labels: [], ignored: [], issues: [] };
  for (const name of header) {
    const folded = fold(name);
    let canon: string | undefined = lookup.get(folded);
    let factor = 1;
    let unitRead: string | null = null;
    if (canon === undefined) {
      const [base, unit] = splitUnit(name);
      let baseCanon = lookup.get(fold(base)) ?? UNITLESS[fold(base)];
      if (baseCanon === undefined) baseCanon = columns.find(c => fold(base) === fold(c.split("_")[0]));
      if (unit !== null && baseCanon !== undefined && baseCanon in UNITS) {
        const table = UNIT_TABLE_FOLDED[baseCanon];
        if (!(fold(unit) in table)) {
          res.issues.push({ code: "HEADER_UNIT_UNKNOWN", message: `Column '${name}' states the unit '${unit}', which this form does not convert. Use ${Object.keys(UNITS[baseCanon]).join(", ")}.` });
          return res;
        }
        canon = baseCanon; factor = table[fold(unit)]; unitRead = unit;
      } else if (unit !== null && baseCanon !== undefined && !(baseCanon in UNITS) && !inputs) {
        canon = baseCanon; unitRead = unit;
      }
    }
    if (canon === undefined && inputs) {
      if (protocol.targetLikeExact.includes(folded) || name === "D" || name === "W") {
        res.issues.push({ code: "INPUTS_TARGET_COLUMN", message: `Column '${name}' may be a measurement (it contains '${name}'). The inputs file carries inputs only; put measurements in the targets file, or remove the column if it is not a measurement.` });
        return res;
      }
      const hit = TARGET_LIKE.exec(name);
      if (hit) {
        res.issues.push({ code: "INPUTS_TARGET_COLUMN", message: `Column '${name}' may be a measurement (it contains '${hit[0]}'). The inputs file carries inputs only; put measurements in the targets file, or remove the column if it is not a measurement.` });
        return res;
      }
      res.issues.push({ code: "INPUTS_UNKNOWN_COLUMN", message: `Column '${name}' is not an input column. Allowed: ${protocol.inputColumns.join(", ")}, or a listed alias.` });
      return res;
    }
    if (canon === undefined) { res.ignored.push(name); continue; }
    if (canon in res.mapped) {
      res.issues.push({ code: "AMBIGUOUS_ALIAS", message: `Columns '${res.mapped[canon].header}' and '${name}' both mean ${canon}. Keep one.` });
      return res;
    }
    if (unitRead === null && canon in UNITS && folded in UNITLESS) res.labels.push(`unit not stated, read as ${CANONICAL_UNIT[canon]}`);
    const entry = { header: name, canonical: canon, unit: unitRead, factor };
    res.mapped[canon] = entry;
    if (name !== canon) res.echoes.push(entry);
  }
  return res;
}

function sniffSeparator(firstLine: string, dialect: BlindCsvDialect): BlindHeaderIssue | null {
  const sep = SEPARATORS[dialect];
  if (sep === "," && firstLine.includes(";") && !firstLine.includes(",")) {
    return { code: "DIALECT_MISMATCH", message: "The header is separated by semicolons, but the declared format is comma separated. Choose a semicolon format." };
  }
  if (sep === ";" && firstLine.includes(",") && !firstLine.includes(";")) {
    return { code: "DIALECT_MISMATCH", message: "The header is separated by commas, but the declared format is semicolon separated. Choose the comma format." };
  }
  return null;
}

function lines(text: string): string[] { return text.split("\n").map(l => l.replace(/\r$/, "")); }
function countDataLines(all: string[]): number { return all.slice(1).filter(l => l.trim() !== "").length; }

function headerCheck(text: string, dialect: BlindCsvDialect, columns: readonly string[], aliases: Record<string, readonly string[]>, inputs: boolean): BlindHeaderCheck {
  const clean = text.startsWith("﻿") ? text.slice(1) : text;
  const out: BlindHeaderCheck = { ok: false, issues: [], warnings: [], header: [], mapped: {}, echoes: [], labels: [], ignored: [], exampleRow: false, dataLines: 0 };
  if (clean.startsWith("PK\u0003\u0004") || clean.includes("\u0000")) {
    out.issues.push({ code: "FILE_NOT_CSV_UTF8", message: "This file is not UTF-8 CSV text (it may be an Excel workbook). In Excel use Save As, CSV UTF-8." });
    return out;
  }
  const all = lines(clean);
  const first = all[0] ?? "";
  if (first.trim() === "") { out.issues.push({ code: "FILE_EMPTY", message: "The file has a header but no data rows." }); return out; }
  const sniff = sniffSeparator(first, dialect);
  if (sniff) { out.issues.push(sniff); return out; }
  const cells = splitCsvLine(first, SEPARATORS[dialect]);
  if (!cells) { out.issues.push({ code: "CSV_MALFORMED", message: "Row 1: the line could not be read as CSV (unterminated quote)." }); return out; }
  out.header = cells.map(c => c.trim());
  const mapped = mapHeader(out.header, columns, aliases, inputs);
  out.mapped = mapped.mapped; out.echoes = mapped.echoes; out.labels = mapped.labels; out.ignored = mapped.ignored; out.issues.push(...mapped.issues);
  if (mapped.issues.length) return out;
  const aliasList = (c: string) => (aliases[c] ?? []).join(", ") || "none";
  const needed = inputs ? ["power_W", "speed_mm_s"] : ["depth_um"];
  for (const need of needed) {
    if (!(need in out.mapped)) out.issues.push({ code: inputs ? "INPUTS_COLUMN_MISSING" : "TARGETS_COLUMN_MISSING", message: `Column ${need} is required (or one of its aliases: ${aliasList(need)}).` });
  }
  const hasKey = ["condition_id", "track_id"].some(c => c in out.mapped) || (!inputs && "section_id" in out.mapped);
  if (!hasKey) out.issues.push({ code: inputs ? "INPUTS_COLUMN_MISSING" : "TARGETS_COLUMN_MISSING", message: `Column condition_id or track_id is required (or one of their aliases: ${aliasList("condition_id")}, ${aliasList("track_id")}).` });
  if (inputs && "section_id" in out.mapped && !("track_id" in out.mapped)) out.issues.push({ code: "SECTION_WITHOUT_TRACK", message: "Row 2: section_id needs track_id." });
  if (inputs && !("spot_um" in out.mapped)) out.warnings.push("No spot column: the block beam diameter in the form must be set, otherwise the check refuses.");
  out.dataLines = countDataLines(all);
  if (out.dataLines === 0) out.issues.push({ code: "FILE_EMPTY", message: "The file has a header but no data rows." });
  const marker = protocol.regex.syntheticMarker.toLowerCase();
  const idIndexes = ["condition_id", "track_id", "section_id"].filter(c => c in out.mapped).map(c => out.header.indexOf(out.mapped[c].header));
  for (let i = 1; i < Math.min(all.length, 1 + 20); i += 1) {
    const row = splitCsvLine(all[i], SEPARATORS[dialect]);
    if (row && idIndexes.some(ix => (row[ix] ?? "").toLowerCase().includes(marker))) { out.exampleRow = true; break; }
  }
  if (out.exampleRow) out.issues.push({ code: "SYNTHETIC_EXAMPLE_ROW", message: "A row is the template's synthetic example. Delete it before uploading your own data." });
  out.ok = out.issues.length === 0;
  return out;
}

const REPEATABLE_INPUTS = ["power_W", "speed_mm_s", "spot_um", "power_u_k1_W"];
/** Header-only check of the inputs file (first 64 KiB is enough). Mirrors read_csv, map_header and parse_inputs. */
export function checkInputsHeader(text: string, dialect: BlindCsvDialect): BlindHeaderCheck {
  return headerCheck(text, dialect, protocol.inputColumns, protocol.inputAliases, true);
}
/** Header-only check of the targets file; the frozen key set is only known to the worker, which still checks it. */
export function checkTargetsHeader(text: string, dialect: BlindCsvDialect): BlindHeaderCheck {
  const columns = [...protocol.targetColumns, ...REPEATABLE_INPUTS];
  const aliases: Record<string, readonly string[]> = { ...protocol.targetAliases };
  for (const c of REPEATABLE_INPUTS) aliases[c] = (protocol.inputAliases as Record<string, readonly string[]>)[c] ?? [];
  return headerCheck(text, dialect, columns, aliases, false);
}

// ------------------------------------------------------------------------------------------------ metadata draft
/** The form works on strings so an empty field stays empty; `draftToMetadata` builds the closed request object. */
export interface BlindMetadataDraft {
  blockLabel: string; mode: string; alloy: string; quantity: string; depthBoundary: string; measurementMethod: string; depthDatum: string;
  reduction: string; crossSectionLocation: string; beamDiameter_um: string; beamQuantity: string; beamDefinition: string; beamBasis: string;
  beamProfile: string; beamUncertaintyReleased: boolean; beamUk1_um: string; powerBasis: string; powerMeterNamed: boolean;
  powerUncertaintyReleased: boolean; powerUk1Rel: string; wavelength_nm: string; substrateKind: string; layerThickness_um: string;
  amSubstrate: boolean; thickness_mm: string; surfacePreparation: string; alsi10mgState: string; preheat_C: string; preheatBasis: string;
  atmosphere: string; tracksPerCondition: string; sectionsPerTrack: string; rowsAreSeparateTracks: boolean; depthUncertaintyBasis: string;
  depthUncertaintyU: string; coverageFactor: string; chemistryBasis: string; sulfur_ppm: string; oxygen_ppm: string;
  predictionsViewedBeforeFreeze: string; dataPreviouslyPublished: string; publishedDoi: string; usedForMachineCalibration: string;
  targetCommitmentSha256: string; csvDialect: string;
}
/** Conservative defaults (python/lpbf_user_blind_inputs.py DEFAULTS). Required fields without a default start empty. */
export const BLIND_DRAFT_DEFAULTS: BlindMetadataDraft = {
  blockLabel: "", mode: "", alloy: "", quantity: "melt-pool-depth", depthBoundary: "other", measurementMethod: "other", depthDatum: "unresolved",
  reduction: "", crossSectionLocation: "unstated", beamDiameter_um: "", beamQuantity: "", beamDefinition: "unstated", beamBasis: "nominal",
  beamProfile: "unknown", beamUncertaintyReleased: false, beamUk1_um: "", powerBasis: "commanded", powerMeterNamed: false,
  powerUncertaintyReleased: false, powerUk1Rel: "", wavelength_nm: "", substrateKind: "", layerThickness_um: "", amSubstrate: false,
  thickness_mm: "", surfacePreparation: "unstated", alsi10mgState: "unstated", preheat_C: "", preheatBasis: "set-point", atmosphere: "unstated",
  tracksPerCondition: "", sectionsPerTrack: "", rowsAreSeparateTracks: false, depthUncertaintyBasis: "not-released", depthUncertaintyU: "",
  coverageFactor: "1", chemistryBasis: "unstated", sulfur_ppm: "", oxygen_ppm: "", predictionsViewedBeforeFreeze: "", dataPreviouslyPublished: "unknown",
  publishedDoi: "", usedForMachineCalibration: "", targetCommitmentSha256: "", csvDialect: "comma-dot",
};
export const BLIND_DRAFT_KEYS = Object.keys(BLIND_DRAFT_DEFAULTS) as (keyof BlindMetadataDraft)[];

const REQUIRED_DRAFT: [keyof BlindMetadataDraft, string][] = [
  ["blockLabel", "Block label"], ["mode", "Mode"], ["alloy", "Alloy"], ["reduction", "Reduction"], ["wavelength_nm", "Wavelength"],
  ["beamQuantity", "Beam quantity"], ["substrateKind", "Substrate"], ["preheat_C", "Plate temperature"],
  ["tracksPerCondition", "Tracks per condition"], ["sectionsPerTrack", "Sections per track"],
  ["predictionsViewedBeforeFreeze", "Predictions viewed before freeze"], ["usedForMachineCalibration", "Used for machine calibration"],
];
/** Labels of the required form fields that are still empty. */
export function draftMissing(draft: BlindMetadataDraft): string[] {
  const missing = REQUIRED_DRAFT.filter(([k]) => String(draft[k]).trim() === "").map(([, label]) => label);
  if (draft.substrateKind === "powder-layer" && draft.layerThickness_um.trim() === "") missing.push("Layer thickness");
  if (draft.depthUncertaintyBasis === "block" && draft.depthUncertaintyU.trim() === "") missing.push("Block depth uncertainty");
  return missing;
}
const numOrNull = (s: string): number | null => (s.trim() === "" ? null : Number(s));

/** Closed request metadata from the draft. Numbers that do not parse become NaN-free null so the worker names the field. */
export function draftToMetadata(draft: BlindMetadataDraft): Record<string, unknown> {
  const n = (s: string) => { const v = numOrNull(s); return v !== null && Number.isFinite(v) ? v : null; };
  const powder = draft.substrateKind === "powder-layer";
  const sha = draft.targetCommitmentSha256.trim().toLowerCase();
  return {
    schema: BLIND_METADATA_SCHEMA, blockLabel: draft.blockLabel, mode: draft.mode, alloy: draft.alloy, quantity: draft.quantity,
    depthBoundary: draft.depthBoundary, measurementMethod: draft.measurementMethod, depthDatum: draft.depthDatum, reduction: draft.reduction,
    crossSectionLocation: draft.crossSectionLocation, wavelength_nm: n(draft.wavelength_nm), preheat_C: n(draft.preheat_C),
    preheatBasis: draft.preheatBasis, atmosphere: draft.atmosphere, csvDialect: draft.csvDialect,
    targetCommitment: draft.mode === "post-measurement" && sha ? { sha256: sha } : null,
    beam: { diameter_um: n(draft.beamDiameter_um), quantity: draft.beamQuantity, definition: draft.beamDefinition, basis: draft.beamBasis, profile: draft.beamProfile, uncertaintyReleased: draft.beamUncertaintyReleased, u_k1_um: n(draft.beamUk1_um) },
    power: { basis: draft.powerBasis, meterNamed: draft.powerMeterNamed, uncertaintyReleased: draft.powerUncertaintyReleased, u_k1_rel: n(draft.powerUk1Rel) },
    substrate: { kind: draft.substrateKind, layerThickness_um: powder ? n(draft.layerThickness_um) : null, amSubstrate: draft.amSubstrate, thickness_mm: n(draft.thickness_mm), surfacePreparation: draft.surfacePreparation, alsi10mgState: draft.alloy === "AlSi10Mg" ? draft.alsi10mgState : null },
    replication: { tracksPerCondition: n(draft.tracksPerCondition), sectionsPerTrack: n(draft.sectionsPerTrack), rowsAreSeparateTracks: draft.rowsAreSeparateTracks },
    depthUncertainty: { basis: draft.depthUncertaintyBasis, u_um: n(draft.depthUncertaintyU), coverageFactor: Number(draft.coverageFactor) === 2 ? 2 : 1 },
    chemistry: { basis: draft.chemistryBasis, sulfur_ppm: n(draft.sulfur_ppm), oxygen_ppm: n(draft.oxygen_ppm) },
    independence: { predictionsViewedBeforeFreeze: draft.predictionsViewedBeforeFreeze, dataPreviouslyPublished: draft.dataPreviouslyPublished, publishedDoi: draft.publishedDoi.trim() === "" ? null : draft.publishedDoi.trim(), usedForMachineCalibration: draft.usedForMachineCalibration === "true" },
  };
}

// ------------------------------------------------------------------------------------------------ small display helpers
/** Formatting only: a fraction as a signed percent with one decimal. "inf" stays text. Not a statistic. */
export function formatSignedPercent(rel: BlindRel | undefined): string {
  if (rel === null || rel === undefined) return "n/a";
  if (rel === "inf") return "inf (track not formed)";
  if (rel === "-inf") return "-inf";
  const pct = rel * 100;
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(1)} %`;
}
export function fillWording(template: string, values: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (m, k: string) => (k in values ? values[k] : m));
}
