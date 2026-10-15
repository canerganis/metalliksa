/**
 * Research model transport types and response guards (P8 integration contract, sections 3.4, 3.5, 5, 6, 9.3, 13.9).
 *
 * Research only. Nothing here is imported by a served module, by useLpbfBuildJobStore or by an export path.
 * The block is read, never recomputed: no equation, default or limit lives in TypeScript (R10).
 */

export const RESEARCH_ROUTE_SCHEMA_REQUEST = "p8-research-request-v1" as const;
export const RESEARCH_ROUTE_SCHEMA_RESPONSE = "p8-research-response-v1" as const;
export const RESEARCH_SCHEMA_VERSION = "p8-research-v3" as const;

export type ResearchStage = "describe" | "nominal" | "band";
export type ResearchSender = "research-panel" | "blind-freeze" | "batch-client";
export type ResearchHostId = "melt-pool" | "build-job";

export type ResearchModuleId =
  | "keyholeCavity"
  | "meltDepthLink"
  | "marangoni"
  | "surfaceBalance"
  | "alSi10MgIndexDisclosure"
  | "alSi10MgVapourMgAware"
  | "unavailablePhysics";

/** Order of the sections in the panel (P8 spec section 2 table). */
export const RESEARCH_MODULE_ORDER: readonly ResearchModuleId[] = [
  "keyholeCavity",
  "meltDepthLink",
  "marangoni",
  "surfaceBalance",
  "alSi10MgIndexDisclosure",
  "alSi10MgVapourMgAware",
  "unavailablePhysics",
];

export interface ResearchProcess {
  material: string;
  laserPower_W: number;
  scanSpeed_mm_s: number;
  beamDiameter_um: number;
  preheatTemp_C: number;
  laserWavelength: "IR_1064nm" | "Green_515nm" | "Blue_450nm";
  absorptionModel: "flat-plate";
}

export type ResearchPropertyContext =
  | { kind: "nominal" }
  | { kind: "build-job-snapshot"; alloyId: string; materialPropertySha256: string };

export type ResearchOptionValue = number | string;
export interface ResearchRangeEndpoints { min: number; max: number }
export interface ResearchOptions {
  marangoni: Record<string, ResearchOptionValue>;
  surfaceBalance: Record<string, ResearchOptionValue>;
  ranges: {
    marangoni: Record<string, ResearchRangeEndpoints>;
    surfaceBalance: Record<string, ResearchRangeEndpoints>;
  };
}

export interface ResearchRequest {
  schemaVersion: typeof RESEARCH_ROUTE_SCHEMA_REQUEST;
  supersedeKey: string;
  clientRequestId: string;
  stage: ResearchStage;
  /** band stage only: integer 250 to 8000, or null (finish every arm). */
  timeBudgetMs?: number | null;
  process: ResearchProcess;
  propertyContext: ResearchPropertyContext;
  researchOptions?: ResearchOptions;
  sender?: ResearchSender;
  relay?: { kind: string; previewSha256: string; conditionOrdinal: number };
}

export type ResearchEvidenceKind = "Literature estimate" | "User input" | "Unresolved";

/** One scalar result with its evidence. Numeric `value` is never rounded by the transport. */
export interface ResearchLeaf {
  value: unknown;
  unit: string;
  leafRole: string;
  moduleMaturity: string;
  sourceEvidenceKind: ResearchEvidenceKind | null;
  experimentalValidation: boolean;
  validationStatus: string;
  validationStatusLocator: string;
  uiSentence: string;
  reasonCode: string | null;
  warnings: string[];
  weakestInputs: string[];
  dependsOn: string[];
  labelSources: string[];
}

export type ResearchBandCompleteness = "complete" | "partial" | "unavailable" | "pending";

export interface ResearchFieldBand {
  completeness: ResearchBandCompleteness;
  method: string;
  min: ResearchLeaf;
  nominal: ResearchLeaf;
  max: ResearchLeaf;
  minArmId: string | null;
  maxArmId: string | null;
  minArmLabel: string | null;
  maxArmLabel: string | null;
  minArmTies: number | null;
  maxArmTies: number | null;
  failedArms: Array<{ armId?: string; reasonCode?: string | null; [key: string]: unknown }>;
  successfulArms: ResearchLeaf;
  totalArms: ResearchLeaf;
  reasonCode: string | null;
  unit: string;
}

export type ResearchField = ResearchLeaf & { band?: ResearchFieldBand; consistencyNoteRef?: string };

export interface ResearchInputProvenance {
  kind: string;
  label: string;
  source: string | null;
  sourceId: string | null;
  sourceLocator: string | null;
  declarationLocator: string | null;
  sourceEvidenceKind: ResearchEvidenceKind | null;
  phase: string | null;
  referenceTemperature_K: number | null;
  sourceRange_K: [number, number] | null;
  scope: string;
  status: string;
  followsInput: string | null;
  followState: string | null;
  dependsOn: string[];
  defaultKind: string | null;
  defaultValue: unknown;
}

export interface ResearchInputRecord {
  provenance: ResearchInputProvenance;
  derivation: Record<string, unknown> | null;
}

export interface ResearchManifestArm {
  armId: string;
  label: string;
  family: string;
  onsetEvent: string | null;
  armProvenance: ResearchInputProvenance;
  aliasArmIds: string[];
  changes: Array<{ input: string; provenance: ResearchInputProvenance; nominalAnchor?: ResearchLeaf; [key: string]: unknown }>;
}

export interface ResearchModuleBand {
  completeness: ResearchBandCompleteness;
  method: string;
  caption: string;
  reasonCode: string | null;
  manifest?: ResearchManifestArm[];
  successfulArmCount?: ResearchLeaf;
  failedArms: unknown[];
  fields?: Record<string, ResearchFieldBand>;
  onsetSupport?: { caveat?: string; supported?: ResearchLeaf; total?: ResearchLeaf; unresolved?: ResearchLeaf; [key: string]: unknown };
  statusSupport?: unknown[];
  categoricalSupport?: unknown[];
  [key: string]: unknown;
}

export interface ResearchReason {
  code: string;
  cause: string;
  fieldPaths: string[];
  missingInputs: string[];
  changeInputs: string[];
  quantity: string | null;
  value: unknown;
  limitMin: unknown;
  limitMax: unknown;
  allowedValues: string[] | null;
}

export interface ResearchArmNote {
  armId: string;
  note: {
    sentence: ResearchLeaf;
    sentenceId: string;
    status: string;
    reasons: ResearchReason[];
    assumptions: ResearchLeaf[];
    knownContradictions: unknown[];
    [key: string]: unknown;
  };
}

export interface ResearchConsistencyNote {
  armNotes: ResearchArmNote[];
  assumptions: ResearchLeaf[];
  knownContradictions: unknown[];
  reasons?: ResearchReason[];
  [key: string]: unknown;
}

export interface ResearchServedDifference {
  id: string;
  servedPaths: string[];
  researchPaths: string[];
  variants: Array<{ when: string[]; template: string }>;
  fallback: string;
}

export type ResearchModuleStatus = "available" | "unavailable" | "not-applicable" | "pending";

export interface ResearchModuleContainer {
  modelId: string;
  status: ResearchModuleStatus;
  reasonCode: string | null;
  moduleMaturity: string;
  moduleEvidenceCeiling: string;
  experimentalValidation: boolean;
  validationStatus: string;
  validationStatusLocator: string;
  uiSentence: string;
  warnings: string[];
  fields: Record<string, ResearchField>;
  band?: ResearchModuleBand;
  consistencyNote: ResearchConsistencyNote;
  inputProvenance: Record<string, ResearchInputRecord>;
  servedDifferences: ResearchServedDifference[];
  [key: string]: unknown;
}

export type ResearchBlock = { schemaVersion: string } & Partial<Record<ResearchModuleId, ResearchModuleContainer>>;

export interface ResearchIdentity {
  researchImplementationSha256: string;
  servedImplementationFingerprint: string;
  researchSchemaVersion: string;
  propertySetSha256: string;
  propertyContextKind: string;
}

export interface ResearchProgress { armsTotal: number; armsDone: number; complete: boolean }
export interface ResearchCacheInfo { cacheInstanceId: string; armsHit: number; armsComputed: number }

/** Nominal or band response (3.5). `researchModels` is null only for an incomplete band stage. */
export interface ResearchRunResponse {
  success: true;
  schemaVersion: typeof RESEARCH_ROUTE_SCHEMA_RESPONSE;
  clientRequestId: string;
  requestKey: string;
  stage: "nominal" | "band";
  progress: ResearchProgress;
  researchModels: ResearchBlock | null;
  labels: Record<string, string>;
  identity: ResearchIdentity;
  cache: ResearchCacheInfo;
  digests?: { researchModelsSha256: string; labelsSha256: string };
  relay?: { kind: string; subsetJson: string; subsetSha256: string };
  computeMs?: number;
  channel?: string | null;
}

export interface ResearchProblem {
  pointer: string;
  rule: string;
  limit: number | string | null;
  value: string;
  message: string;
}

export interface ResearchControl {
  key: string;
  module: "marangoni" | "surfaceBalance";
  label: string;
  help: string;
  unit: string;
  displayUnits: Record<string, number>;
  valueType: "number" | "enum";
  enumValues: string[] | null;
  min: number | null;
  max: number | null;
  enabled: boolean;
  value: number | string | null;
  provenance: ResearchInputProvenance;
  rangeAdmitted: boolean;
  resetLabel: string | null;
}

export interface ResearchDescribeResponse {
  success: true;
  schemaVersion: typeof RESEARCH_ROUTE_SCHEMA_RESPONSE;
  stage: "describe";
  clientRequestId: string;
  requestKey: string;
  controls: ResearchControl[];
  presets: {
    vapourPreset: Array<{ id: string; label: string; admitted: boolean; reasonCode: string | null }>;
    slopeMode: Array<{ id: string; label: string }>;
  };
  labels: Record<string, string>;
  problems: ResearchProblem[];
  moduleAvailability: Record<string, { status: "available" | "unavailable" | "not-applicable"; reasonCode: string | null }>;
  identity: ResearchIdentity;
  /** Closed text tables of the describe stage; `refusal.<CODE>` keys hold the English n/a text per reason code. */
  sentences: Record<string, string>;
  statusTexts: Record<string, string>;
  channel?: string | null;
}

export type ResearchTimeoutKind = "queue" | "run" | "reply" | "adhoc";

/**
 * What the transport reports. The service never throws for a server answer; only an aborted fetch rejects (with the
 * standard AbortError) so a cancelled request cannot be mistaken for a failure.
 */
export type ResearchOutcome =
  | { kind: "describe"; response: ResearchDescribeResponse }
  | { kind: "run"; response: ResearchRunResponse }
  | { kind: "refused"; reasonCode: string; problems: ResearchProblem[]; httpStatus: number; recycleWorker: boolean }
  | { kind: "failed"; reasonCode: string; httpStatus: number }
  | { kind: "timeout"; timeoutKind: ResearchTimeoutKind | null; channel: string | null }
  | { kind: "superseded" }
  | { kind: "http-error"; httpStatus: number; message: string }
  | { kind: "malformed"; message: string };

// ---------------------------------------------------------------------------------------------------------------
// Guards. They check the envelope and every shape the panel reads; deeper physics content is data.

type Rec = Record<string, unknown>;
const isRec = (v: unknown): v is Rec => typeof v === "object" && v !== null && !Array.isArray(v);
const isStr = (v: unknown): v is string => typeof v === "string";
const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const isStrList = (v: unknown): v is string[] => Array.isArray(v) && v.every(isStr);
const isStrMap = (v: unknown): v is Record<string, string> => isRec(v) && Object.values(v).every(isStr);
const SHA256 = /^[0-9a-f]{64}$/;

const EVIDENCE_KINDS = new Set<unknown>(["Literature estimate", "User input", "Unresolved", null]);
const BAND_STATES = new Set<unknown>(["complete", "partial", "unavailable", "pending"]);
const MODULE_STATES = new Set<unknown>(["available", "unavailable", "not-applicable", "pending"]);

export function isResearchLeaf(v: unknown): v is ResearchLeaf {
  return isRec(v)
    && "value" in v
    && isStr(v.unit)
    && isStr(v.leafRole)
    && EVIDENCE_KINDS.has(v.sourceEvidenceKind)
    && typeof v.experimentalValidation === "boolean"
    && isStr(v.validationStatus)
    && (v.reasonCode === null || isStr(v.reasonCode))
    && isStrList(v.warnings)
    && isStrList(v.weakestInputs)
    && isStrList(v.dependsOn)
    && isStrList(v.labelSources);
}

function isFieldBand(v: unknown): v is ResearchFieldBand {
  return isRec(v)
    && BAND_STATES.has(v.completeness)
    && isResearchLeaf(v.min) && isResearchLeaf(v.nominal) && isResearchLeaf(v.max)
    && isResearchLeaf(v.successfulArms) && isResearchLeaf(v.totalArms)
    && Array.isArray(v.failedArms);
}

function isProvenance(v: unknown): v is ResearchInputProvenance {
  return isRec(v)
    && isStr(v.kind) && isStr(v.label)
    && EVIDENCE_KINDS.has(v.sourceEvidenceKind)
    && (v.phase === null || isStr(v.phase))
    && (v.referenceTemperature_K === null || isNum(v.referenceTemperature_K))
    && (v.sourceRange_K === null || (Array.isArray(v.sourceRange_K) && v.sourceRange_K.length === 2 && v.sourceRange_K.every(isNum)));
}

function isModuleContainer(v: unknown): v is ResearchModuleContainer {
  if (!isRec(v)) return false;
  if (!isStr(v.modelId) || !MODULE_STATES.has(v.status) || !isStr(v.uiSentence) || !isStr(v.moduleMaturity)) return false;
  if (typeof v.experimentalValidation !== "boolean" || !isStr(v.validationStatus) || !isStr(v.moduleEvidenceCeiling)) return false;
  if (!isRec(v.fields)) return false;
  for (const field of Object.values(v.fields)) {
    if (!isResearchLeaf(field)) return false;
    const band = (field as unknown as Rec).band;
    if (band !== undefined && !isFieldBand(band)) return false;
  }
  if (!isRec(v.consistencyNote) || !Array.isArray(v.consistencyNote.armNotes)) return false;
  for (const entry of v.consistencyNote.armNotes) {
    if (!isRec(entry) || !isStr(entry.armId) || !isRec(entry.note) || !isResearchLeaf(entry.note.sentence)) return false;
    if (!Array.isArray(entry.note.reasons)) return false;
  }
  if (!isRec(v.inputProvenance)) return false;
  for (const record of Object.values(v.inputProvenance)) {
    if (!isRec(record) || !isProvenance(record.provenance)) return false;
  }
  if (!Array.isArray(v.servedDifferences)) return false;
  for (const diff of v.servedDifferences) {
    if (!isRec(diff) || !isStr(diff.id) || !isStr(diff.fallback) || !Array.isArray(diff.variants) || !isStrList(diff.servedPaths) || !isStrList(diff.researchPaths)) return false;
    for (const variant of diff.variants) {
      if (!isRec(variant) || !isStr(variant.template) || !isStrList(variant.when)) return false;
    }
  }
  if (v.band !== undefined) {
    const band = v.band;
    if (!isRec(band) || !BAND_STATES.has(band.completeness) || !isStr(band.caption)) return false;
    if (band.fields !== undefined) {
      if (!isRec(band.fields)) return false;
      for (const fb of Object.values(band.fields)) if (!isFieldBand(fb)) return false;
    }
    if (band.manifest !== undefined) {
      if (!Array.isArray(band.manifest)) return false;
      for (const arm of band.manifest) {
        if (!isRec(arm) || !isStr(arm.armId) || !isStr(arm.label) || !isProvenance(arm.armProvenance)) return false;
      }
    }
  }
  return true;
}

export function isResearchBlock(v: unknown): v is ResearchBlock {
  if (!isRec(v) || !isStr(v.schemaVersion)) return false;
  for (const [key, container] of Object.entries(v)) {
    if (key === "schemaVersion") continue;
    if (!(RESEARCH_MODULE_ORDER as readonly string[]).includes(key)) return false;
    if (!isModuleContainer(container)) return false;
  }
  return true;
}

function isIdentity(v: unknown): v is ResearchIdentity {
  return isRec(v)
    && isStr(v.researchImplementationSha256) && SHA256.test(v.researchImplementationSha256)
    && isStr(v.servedImplementationFingerprint) && SHA256.test(v.servedImplementationFingerprint)
    && isStr(v.researchSchemaVersion) && isStr(v.propertySetSha256) && isStr(v.propertyContextKind);
}

function isProblem(v: unknown): v is ResearchProblem {
  return isRec(v) && isStr(v.pointer) && isStr(v.rule) && isStr(v.message);
}

function isControl(v: unknown): v is ResearchControl {
  return isRec(v)
    && isStr(v.key) && (v.module === "marangoni" || v.module === "surfaceBalance")
    && isStr(v.label) && isStr(v.help) && isStr(v.unit)
    && isRec(v.displayUnits) && Object.values(v.displayUnits).every(isNum)
    && (v.valueType === "number" || v.valueType === "enum")
    && (v.enumValues === null || isStrList(v.enumValues))
    && (v.min === null || isNum(v.min)) && (v.max === null || isNum(v.max))
    && typeof v.enabled === "boolean" && typeof v.rangeAdmitted === "boolean"
    && (v.value === null || isNum(v.value) || isStr(v.value))
    && (v.resetLabel === null || isStr(v.resetLabel))
    && isProvenance(v.provenance);
}

export function isResearchDescribeResponse(v: unknown): v is ResearchDescribeResponse {
  if (!isRec(v) || v.success !== true || v.schemaVersion !== RESEARCH_ROUTE_SCHEMA_RESPONSE || v.stage !== "describe") return false;
  if (!isStr(v.clientRequestId) || !isStr(v.requestKey) || !SHA256.test(v.requestKey)) return false;
  if (!Array.isArray(v.controls) || !v.controls.every(isControl)) return false;
  if (!isRec(v.presets) || !Array.isArray(v.presets.vapourPreset) || !Array.isArray(v.presets.slopeMode)) return false;
  if (!v.presets.vapourPreset.every((p) => isRec(p) && isStr(p.id) && isStr(p.label) && typeof p.admitted === "boolean")) return false;
  if (!v.presets.slopeMode.every((p) => isRec(p) && isStr(p.id) && isStr(p.label))) return false;
  if (!isStrMap(v.labels) || !isStrMap(v.sentences) || !isStrMap(v.statusTexts)) return false;
  if (!Array.isArray(v.problems) || !v.problems.every(isProblem)) return false;
  if (!isRec(v.moduleAvailability)) return false;
  for (const entry of Object.values(v.moduleAvailability)) {
    if (!isRec(entry) || !MODULE_STATES.has(entry.status)) return false;
  }
  return isIdentity(v.identity);
}

export function isResearchRunResponse(v: unknown): v is ResearchRunResponse {
  if (!isRec(v) || v.success !== true || v.schemaVersion !== RESEARCH_ROUTE_SCHEMA_RESPONSE) return false;
  if (v.stage !== "nominal" && v.stage !== "band") return false;
  if (!isStr(v.clientRequestId) || !isStr(v.requestKey) || !SHA256.test(v.requestKey)) return false;
  if (!isRec(v.progress) || !isNum(v.progress.armsTotal) || !isNum(v.progress.armsDone) || typeof v.progress.complete !== "boolean") return false;
  if (!isStrMap(v.labels) || !isIdentity(v.identity)) return false;
  if (!isRec(v.cache) || !isStr(v.cache.cacheInstanceId) || !isNum(v.cache.armsHit) || !isNum(v.cache.armsComputed)) return false;
  if (v.researchModels === null) return v.stage === "band" && v.progress.complete === false;
  if (v.progress.complete && v.stage === "band" && v.researchModels === null) return false;
  return isResearchBlock(v.researchModels);
}

/** Parse a transport answer into an outcome. `status` is the HTTP status, `body` the parsed JSON (or undefined). */
export function classifyResearchAnswer(status: number, body: unknown): ResearchOutcome {
  if (isRec(body) && body.status === "superseded") return { kind: "superseded" };
  if (status === 504 && isRec(body) && body.reasonCode === "RESEARCH_TIMEOUT") {
    const kinds: readonly string[] = ["queue", "run", "reply", "adhoc"];
    const timeoutKind = isStr(body.timeoutKind) && kinds.includes(body.timeoutKind) ? (body.timeoutKind as ResearchTimeoutKind) : null;
    return { kind: "timeout", timeoutKind, channel: isStr(body.channel) ? body.channel : null };
  }
  if (isRec(body) && body.success === false && isStr(body.reasonCode)) {
    const problems = Array.isArray(body.problems) ? body.problems.filter(isProblem) : [];
    if (status === 422 || status === 413) {
      return { kind: "refused", reasonCode: body.reasonCode, problems, httpStatus: status, recycleWorker: body.recycleWorker === true };
    }
    return { kind: "failed", reasonCode: body.reasonCode, httpStatus: status };
  }
  if (status >= 200 && status < 300) {
    if (isResearchDescribeResponse(body)) return { kind: "describe", response: body };
    if (isResearchRunResponse(body)) return { kind: "run", response: body };
    return { kind: "malformed", message: "The research response did not match the expected schema." };
  }
  const message = isRec(body) && isStr(body.error) ? body.error : `HTTP ${status}`;
  return { kind: "http-error", httpStatus: status, message };
}
