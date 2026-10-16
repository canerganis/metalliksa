/**
 * Strict parsers for the quantity envelope v1 (python/quantity_envelope.py is the authority; the closed vocabularies
 * come from src/generated/quantityEnvelope.ts).
 *
 * Solidification integration contract Revision 1, section 4; the maintainer's label decisions 1 and 2 (per-value
 * sourceEvidenceKind under a screening-only module ceiling; Literature estimate / User input / Unresolved with named
 * inputs, Unresolved first; request process values never decide a label). `checkedValueProvenance` is the shared
 * value-provenance parser for P8's research records (P8 contract 6.3 and 13.5).
 *
 * Nothing here computes physics or upgrades a claim: each check mirrors python/quantity_envelope.py, and a payload
 * that breaks one is refused with the reason (no dual-read, no repair).
 */
import {
  QUANTITY_ENVELOPE,
  type Comparability,
  type FollowState,
  type FractionBasis,
  type InputKind,
  type InputPhase,
  type InputStatus,
  type LeafRole,
  type ModuleMaturityEcho,
  type NumericalState,
  type ObservationSourceEvidenceKind,
  type QuantityDefinitionId,
  type QuantitySourceEvidenceKind,
  type QuantityStatus,
  type QuantityUnit,
  type ReadLevel,
  type ReasonCode,
  type UncertaintyKind,
  type EstimateTier,
  type ValueWarningCode,
  type UnknownComponent,
  type EstimateQuantityDefinitionId,
} from "../generated/quantityEnvelope";
import type { ContractObservationDeclaration, ContractQuantityDeclaration } from "../generated/moduleRegistry";

export interface ValueProvenance {
  readonly kind: InputKind;
  readonly label: string;
  readonly sourceId: string;
  readonly sourceLocator: string | null;
  readonly declarationLocator: string | null;
  readonly source: string | null;
  readonly scope: string;
  readonly status: InputStatus;
  readonly sourceEvidenceKind: QuantitySourceEvidenceKind;
  readonly defaultValue: number | string | null;
  readonly defaultKind: InputKind | null;
  readonly followsInput: string | null;
  readonly followState: FollowState | null;
  readonly dependsOn: readonly string[];
  readonly phase: InputPhase | null;
  readonly referenceTemperature_K: number | null;
  readonly sourceRange_K: readonly [number, number] | null;
}

export interface QuantityReason {
  readonly code: ReasonCode;
  readonly params: Readonly<Record<string, number | string | boolean | null>>;
  readonly parent: { readonly input: string; readonly kind: InputKind } | null;
}

export interface SourceRef {
  readonly id: string;
  readonly locator: string;
  readonly readLevel: ReadLevel;
}

export type QuantityValue = number | string | Readonly<Record<string, number>>;

export interface Quantity {
  readonly status: QuantityStatus;
  readonly value: QuantityValue | null;
  readonly unit: QuantityUnit;
  readonly quantityDefinition: QuantityDefinitionId;
  readonly leafRole: LeafRole;
  readonly sourceEvidenceKind: QuantitySourceEvidenceKind | null;
  readonly dependsOn: readonly string[];
  readonly weakestInputs: readonly string[];
  readonly labelSources: readonly string[];
  readonly reasons: readonly QuantityReason[];
  readonly numericalStatus: {
    readonly state: NumericalState;
    readonly settings: Readonly<Record<string, unknown>>;
    readonly residuals: Readonly<Record<string, unknown>>;
  };
  readonly physicalValidation: { readonly status: "unvalidated"; readonly experimentalValidation: false; readonly productionReady: false };
  readonly sources: readonly SourceRef[];
  readonly assumptions: readonly string[];
  readonly validity: Readonly<Record<string, unknown>> | null;
  readonly uncertainty: { readonly kind: UncertaintyKind; readonly construction: string | null } | null;
  readonly fractionBasis: FractionBasis | null;
  readonly identity: { readonly input: string | null; readonly model: string | null; readonly parent: string | null };
}

export interface Observation {
  readonly recordKind: "source-observation";
  readonly observable: string;
  readonly value: number | Readonly<Record<string, number>>;
  readonly unit: QuantityUnit;
  readonly sourceEvidenceKind: ObservationSourceEvidenceKind;
  readonly sources: readonly SourceRef[];
  readonly materialScope: string;
  readonly processScope: string;
  readonly comparability: Comparability;
}

export interface QuantityContainer {
  readonly default?: boolean;
  readonly quantityEnvelopeSchema: typeof QUANTITY_ENVELOPE.schema;
  readonly moduleEvidenceCeiling: typeof QUANTITY_ENVELOPE.moduleEvidenceCeiling;
  readonly moduleMaturity: ModuleMaturityEcho;
  readonly quantities: Readonly<Record<string, Quantity>>;
  readonly observations?: Readonly<Record<string, Observation>>;
  readonly inputProvenance?: Readonly<Record<string, ValueProvenance>>;
}

export interface SourceLabelResult {
  readonly sourceEvidenceKind: QuantitySourceEvidenceKind;
  readonly weakestInputs: readonly string[];
  readonly labelSources: readonly string[];
  readonly determiningInputs: readonly string[];
}

type Label = QuantitySourceEvidenceKind;
type Json = Record<string, unknown>;

const V = QUANTITY_ENVELOPE;
const KEY = /^[A-Za-z][A-Za-z0-9_]*$/;
const RANK: Readonly<Record<Label, number>> = V.labelRank;

const has = (list: readonly unknown[], value: unknown): boolean => list.includes(value);
const isObject = (value: unknown): value is Json => typeof value === "object" && value !== null && !Array.isArray(value);
const isNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const isText = (value: unknown): value is string => typeof value === "string" && value.trim() !== "";
const isStrList = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === "string" && item !== "");
const isLabel = (value: unknown): value is Label => typeof value === "string" && Object.hasOwn(RANK, value);
const sameKeys = (value: Json, keys: readonly string[]): boolean =>
  Object.keys(value).length === keys.length && keys.every((key) => Object.hasOwn(value, key));
const equalLists = (a: readonly string[], b: readonly string[]): boolean =>
  a.length === b.length && a.every((item, index) => item === b[index]);
const weaker = (a: Label, b: Label): Label => (RANK[a] <= RANK[b] ? a : b);

function rejected(kind: string, problems: readonly string[]): never {
  throw new Error(`${kind} rejected: ${problems.join("; ")}`);
}

// --- Display (L1 to L3 drafts) ---------------------------------------------------------------------------------

/** English sentence of a reason code; template parameters must all be present. */
export function reasonText(code: ReasonCode, params: Readonly<Record<string, unknown>> = {}): string {
  const entry = V.reasonTemplates[code];
  const missing = entry.params.filter((name: string) => !Object.hasOwn(params, name));
  if (missing.length > 0) throw new Error(`reason ${code} needs params ${missing.join(", ")}`);
  return entry.template.replace(/\{([A-Za-z][A-Za-z0-9_]*)\}/g, (_match: string, name: string) => String(params[name]));
}

/** "Literature estimate", "User input: a, b" or "Unresolved: a" for a quantity's label and named inputs. */
export function sourceLabelText(kind: QuantitySourceEvidenceKind | "Measured", names: readonly string[] = []): string {
  return V.sourceLabelDisplay[kind].replace("{names}", names.join(", "));
}

// --- Shared value-provenance parser (P8 6.3) -----------------------------------------------------------------------

export function valueProvenanceProblems(raw: unknown, where = "input"): string[] {
  if (!isObject(raw)) return [`${where}: input record must be an object`];
  const problems: string[] = [];
  const missing = V.inputRecordKeys.filter((key: string) => !Object.hasOwn(raw, key));
  const extra = Object.keys(raw).filter((key) => !has(V.inputRecordKeys, key)).sort();
  if (missing.length) problems.push(`${where}: missing keys ${missing.join(", ")}`);
  if (extra.length) problems.push(`${where}: unknown keys ${extra.join(", ")}`);
  if (missing.length) return problems;
  const kind = raw.kind;
  if (!has(V.inputKinds, kind)) return [...problems, `${where}: unknown kind ${String(kind)}`];
  const inputKind = kind as InputKind;
  if (!isText(raw.label)) problems.push(`${where}: label must be a non-empty string`);
  if (!isText(raw.sourceId)) problems.push(`${where}: sourceId must be a non-empty string`);
  for (const key of ["sourceLocator", "declarationLocator", "source"] as const) {
    if (raw[key] !== null && !isText(raw[key])) problems.push(`${where}: ${key} must be null or a non-empty string`);
  }
  if (typeof raw.scope !== "string") problems.push(`${where}: scope must be a string`);
  if (!has(V.inputStatuses, raw.status)) problems.push(`${where}: status must be one of ${V.inputStatuses.join(", ")}`);
  const evidence = raw.sourceEvidenceKind;
  if (evidence === "Measured") {
    problems.push(`${where}: an input used to compute a value never reads Measured (contract 4.3 item 4)`);
  } else if (!isLabel(evidence)) {
    problems.push(`${where}: sourceEvidenceKind must be one of ${V.quantitySourceEvidenceKinds.join(", ")}`);
  } else {
    const ceiling = V.inputKindEvidence[inputKind] as Label | null;
    if (ceiling !== null && RANK[evidence] > RANK[ceiling]) {
      problems.push(`${where}: kind ${inputKind} cannot read ${evidence} (at most ${ceiling})`);
    }
  }
  if (has(V.sourcedInputKinds, inputKind) && !isText(raw.sourceLocator)) {
    problems.push(`${where}: a ${inputKind} record needs a located source (sourceLocator)`);
  }
  if (inputKind === "declaredAssumption" && !isText(raw.declarationLocator)) {
    problems.push(`${where}: a declaredAssumption names where it is declared (declarationLocator)`);
  }
  if (inputKind === "alloyTransfer" && raw.status === "inRange") {
    problems.push(`${where}: a transfer keeps its scope extrapolated, never inRange`);
  }
  if (raw.defaultValue !== null && !isNumber(raw.defaultValue) && typeof raw.defaultValue !== "string") {
    problems.push(`${where}: defaultValue must be a finite number, a string or null`);
  }
  if (raw.defaultKind !== null && !has(V.inputKinds, raw.defaultKind)) {
    problems.push(`${where}: defaultKind must be an input kind or null`);
  }
  if (raw.defaultKind === "legacyEstimate") problems.push(`${where}: a legacy estimate is never a default`);
  if (raw.defaultKind === "sourcedAlternative") problems.push(`${where}: a sourcedAlternative is never a defaultKind`);
  const follows = raw.followsInput;
  const state = raw.followState;
  if (inputKind === "followsInput") {
    if (!isText(follows) || state !== "following") problems.push(`${where}: followsInput needs followsInput and followState 'following'`);
    if (raw.defaultKind === null) problems.push(`${where}: followsInput needs defaultKind, the kind of its rule`);
  } else if (inputKind === "userInput" && state !== null) {
    if (state !== "user-fixed" || !isText(follows)) problems.push(`${where}: a typed follower is userInput with followState 'user-fixed'`);
  } else if (follows !== null || state !== null) {
    problems.push(`${where}: only followsInput (or a user-fixed userInput) carries followsInput/followState`);
  }
  if (!isStrList(raw.dependsOn) || new Set(raw.dependsOn).size !== raw.dependsOn.length) {
    problems.push(`${where}: dependsOn must be a list of unique names`);
  }
  if (raw.phase !== null && !has(V.inputPhases, raw.phase)) problems.push(`${where}: phase must be one of ${V.inputPhases.join(", ")} or null`);
  if (raw.phase === V.processPhase && kind !== "userInput") problems.push(`${where}: only userInput may carry phase process`);
  if (raw.referenceTemperature_K !== null && !isNumber(raw.referenceTemperature_K)) {
    problems.push(`${where}: referenceTemperature_K must be a finite number or null`);
  }
  const range = raw.sourceRange_K;
  if (range !== null && !(Array.isArray(range) && range.length === 2 && isNumber(range[0]) && isNumber(range[1]) && range[0] <= range[1])) {
    problems.push(`${where}: sourceRange_K must be [low, high] finite numbers or null (never invented)`);
  }
  return problems;
}

/** The shared value-provenance parser: a P8-shaped input record, or an Error naming every problem. */
export function checkedValueProvenance(raw: unknown, where = "input"): ValueProvenance {
  const problems = valueProvenanceProblems(raw, where);
  if (problems.length) rejected("value provenance", problems);
  return raw as unknown as ValueProvenance;
}

// --- Label rule (decision 2; contract 4.3; P8 13.12) --------------------------------------------------------------

type Records = Readonly<Record<string, unknown>>;

function determining(dependsOn: readonly string[], inputs: Records, quantities: Records | undefined, seen: ReadonlySet<string> = new Set()): string[] {
  const names: string[] = [];
  for (const name of dependsOn) {
    if (quantities && Object.hasOwn(quantities, name) && !Object.hasOwn(inputs, name)) {
      if (seen.has(name)) {
        names.push(name);
        continue;
      }
      const sibling = quantities[name];
      const nested = isObject(sibling) && isStrList(sibling.dependsOn) ? sibling.dependsOn : [];
      for (const inner of determining(nested, inputs, quantities, new Set([...seen, name]))) {
        if (!names.includes(inner)) names.push(inner);
      }
    } else if (!names.includes(name)) {
      names.push(name);
    }
  }
  return names;
}

function inputLabel(name: string, inputs: Records, seen: ReadonlySet<string>): [Label | null, string[]] {
  if (has(V.requestProcessInputs, name)) return [null, []];
  const record = Object.hasOwn(inputs, name) ? inputs[name] : undefined;
  if (!isObject(record) || seen.has(name)) return ["Unresolved", []];
  const kind = record.kind;
  let label: Label;
  let locators: string[] = [];
  if (has(V.sourcedInputKinds, kind)) {
    if (isText(record.sourceLocator)) {
      label = "Literature estimate";
      locators = [record.sourceLocator];
    } else {
      label = "Unresolved";
    }
  } else if (has(V.unsourcedInputKinds, kind)) {
    label = "Unresolved";
  } else if (kind === "userInput") {
    label = "User input";
  } else if (kind === "followsInput") {
    const ruleKind = record.defaultKind;
    const rule = typeof ruleKind === "string" && has(V.inputKinds, ruleKind) ? (V.inputKindEvidence[ruleKind as InputKind] as Label | null) : null;
    label = rule ?? "Unresolved";
    if (label === "Literature estimate") {
      if (isText(record.sourceLocator)) locators = [record.sourceLocator];
      else label = "Unresolved";
    }
    const followed = [record.followsInput, ...(Array.isArray(record.dependsOn) ? record.dependsOn : [])];
    for (const other of followed) {
      if (typeof other !== "string") continue;
      const [otherLabel, otherLocators] = inputLabel(other, inputs, new Set([...seen, name]));
      if (otherLabel === null) continue;
      label = weaker(otherLabel, label);
      for (const locator of otherLocators) if (!locators.includes(locator)) locators.push(locator);
    }
  } else if (kind === "derived") {
    const deps = (Array.isArray(record.dependsOn) ? record.dependsOn : []).filter((dep): dep is string => typeof dep === "string");
    const labelled = deps
      .map((dep) => inputLabel(dep, inputs, new Set([...seen, name])))
      .filter((item): item is [Label, string[]] => item[0] !== null);
    if (labelled.length) {
      label = labelled.map((item) => item[0]).reduce(weaker);
      for (const [, itemLocators] of labelled) for (const locator of itemLocators) if (!locators.includes(locator)) locators.push(locator);
    } else if (isText(record.sourceLocator)) {
      label = "Literature estimate";
      locators = [record.sourceLocator];
    } else {
      label = "Unresolved";
    }
  } else {
    label = "Unresolved";
  }
  const own = record.sourceEvidenceKind;
  if (!isLabel(own)) label = "Unresolved";
  else label = weaker(own, label);
  return [label, label === "Literature estimate" ? locators : []];
}

function weakestRoots(name: string, inputs: Records, label: Label, seen: ReadonlySet<string> = new Set()): string[] {
  const record = inputs[name];
  if (!isObject(record) || seen.has(name)) return [name];
  if (record.kind !== "followsInput" && record.kind !== "derived") return [name];
  if (record.kind === "followsInput" && has(V.unsourcedInputKinds, record.defaultKind)) return [name];
  const deps = isStrList(record.dependsOn) ? record.dependsOn : [];
  const followed = record.kind === "followsInput" && typeof record.followsInput === "string" ? [record.followsInput, ...deps] : deps;
  const roots: string[] = [];
  const next = new Set([...seen, name]);
  for (const dep of followed) {
    if (inputLabel(dep, inputs, next)[0] === label) {
      for (const root of weakestRoots(dep, inputs, label, next)) if (!roots.includes(root)) roots.push(root);
    }
  }
  return roots.length ? roots : [name];
}

/** The decided label rule over a value's determining inputs (mirrors quantity_envelope.source_label). */
export function sourceLabel(inputs: Records, dependsOn: readonly string[], quantities?: Records): SourceLabelResult {
  const labelled: [string, Label, string[]][] = [];
  for (const name of determining(dependsOn, inputs, quantities)) {
    const [label, locators] = inputLabel(name, inputs, new Set());
    if (label !== null) labelled.push([name, label, locators]);
  }
  if (!labelled.length) return { sourceEvidenceKind: "Unresolved", weakestInputs: [], labelSources: [], determiningInputs: [] };
  const weakest = labelled.map((item) => item[1]).reduce(weaker);
  const sources: string[] = [];
  if (weakest === "Literature estimate") {
    for (const [, , locators] of labelled) for (const locator of locators) if (!sources.includes(locator)) sources.push(locator);
  }
  return {
    sourceEvidenceKind: weakest,
    weakestInputs: weakest === "Literature estimate" ? [] : [...new Set(labelled.filter((item) => item[1] === weakest)
      .flatMap((item) => weakestRoots(item[0], inputs, weakest)))],
    labelSources: sources,
    determiningInputs: labelled.map((item) => item[0]),
  };
}

/** Python's binary64 float.hex, including signed zero and subnormals. */
function floatHex(value: number): string {
  if (!Number.isFinite(value)) return String(value).toLowerCase();
  const bits = new DataView(new ArrayBuffer(8));
  bits.setFloat64(0, value);
  const high = bits.getUint32(0), low = bits.getUint32(4);
  const negative = (high >>> 31) ? "-" : "";
  const exponent = (high >>> 20) & 0x7ff;
  const fraction = (high & 0xfffff).toString(16).padStart(5, "0") + low.toString(16).padStart(8, "0");
  if (exponent === 0 && (high & 0xfffff) === 0 && low === 0) return `${negative}0x0.0p+0`;
  const power = exponent === 0 ? -1022 : exponent - 1023;
  return `${negative}0x${exponent === 0 ? "0" : "1"}.${fraction}p${power >= 0 ? "+" : ""}${power}`;
}

function contentKey(value: unknown): string {
  const encode = (item: unknown): unknown => {
    if (item === null || typeof item === "boolean" || typeof item === "string") return item;
    if (typeof item === "number") return ["number", floatHex(item)];
    if (Array.isArray(item)) return ["list", item.map(encode)];
    if (isObject(item)) return ["object", Object.keys(item).sort().map(key => [key, encode(item[key])])];
    return ["invalid", typeof item];
  };
  return JSON.stringify(encode(value));
}

/** Exact content digest of complete inputs and transitive sibling identities/values; no lossy hash. */
export function parentKey(inputs: Records, dependsOn: readonly string[], quantities?: Records): string {
  const parts: Json = {};
  const visit = (names: readonly string[], seen: ReadonlySet<string>): void => {
    for (const name of names) {
      if (seen.has(name)) continue;
      const next = new Set([...seen, name]);
      if (Object.hasOwn(inputs, name)) {
        const record = inputs[name];
        parts[name] = { input: record };
        if (isObject(record)) {
          const deps = isStrList(record.dependsOn) ? record.dependsOn : [];
          visit(typeof record.followsInput === "string" ? [...deps, record.followsInput] : deps, next);
        }
      } else if (quantities && isObject(quantities[name])) {
        const sibling = quantities[name];
        parts[name] = { identity: sibling.identity ?? null, value: sibling.value ?? null };
        visit(isStrList(sibling.dependsOn) ? sibling.dependsOn : [], next);
      } else parts[name] = null;
    }
  };
  visit(dependsOn, new Set());
  return `parents-v2:${contentKey(parts)}`;
}

// --- Quantity, observation and container --------------------------------------------------------------------------

interface DefinitionShape {
  readonly unit: string; readonly valueKind: string; readonly valueRange: string | null; readonly fraction: boolean;
  readonly members: readonly string[]; readonly memberUnits: Readonly<Record<string, string>>;
  readonly categories: readonly string[];
}
const V2 = V.estimates;
const V2_DEFINITIONS = V2.quantityDefinitions as unknown as Readonly<Record<string, DefinitionShape>>;
const V1_DEFINITIONS = V.quantityDefinitions as unknown as Readonly<Record<string, DefinitionShape>>;

function valueProblems(value: unknown, id: string, where: string, table: Readonly<Record<string, DefinitionShape>> = V1_DEFINITIONS): string[] {
  const definition = table[id];
  const range: string | null = definition.valueRange;
  const numberProblem = (item: unknown): string | null => {
    if (!isNumber(item)) return "must be a finite number";
    if (range === "positive" && !(item > 0)) return "must be positive";
    if (range === "fraction" && !(item >= 0 && item <= 1)) return "must lie in [0, 1]";
    if (range === "nonnegative" && !(item >= 0)) return "must be nonnegative";
    return null;
  };
  const problems: string[] = [];
  const kind: string = definition.valueKind;
  if (kind === "number") {
    const problem = numberProblem(value);
    if (problem) problems.push(`${where}.value ${problem}`);
  } else if (kind === "alternatives" || kind === "record") {
    const members: readonly string[] = definition.members.length ? definition.members : Object.keys(definition.memberUnits);
    if (!isObject(value) || !sameKeys(value, members)) {
      problems.push(`${where}.value must be an object with exactly the members ${members.join(", ")}`);
    } else {
      for (const member of members) {
        const problem = numberProblem(value[member]);
        if (problem) problems.push(`${where}.value.${member} ${problem}`);
      }
    }
  } else if (kind === "map") {
    if (!isObject(value) || Object.keys(value).length === 0) {
      problems.push(`${where}.value must be a non-empty object keyed by names`);
    } else {
      for (const [key, item] of Object.entries(value)) {
        const problem = numberProblem(item);
        if (problem) problems.push(`${where}.value.${key} ${problem}`);
      }
    }
  } else if (kind === "inventory") {
    const members = definition.members;
    if (!isObject(value) || !sameKeys(value, members)) {
      problems.push(`${where}.value must be an object with exactly the members ${members.join(", ")}`);
    } else {
      for (const member of members) {
        const problem = numberProblem(value[member]);
        if (problem) problems.push(`${where}.value.${member} ${problem}`);
      }
      if (!problems.length && Math.abs(members.reduce((sum, member) => sum + (value[member] as number), 0) - 1) > 1e-12) {
        problems.push(`${where}.value members must sum to 1 (a closed inventory)`);
      }
    }
  } else if (kind === "category") {
    if (!has(definition.categories, value)) {
      problems.push(`${where}.value must be one of [${definition.categories.join(", ")}] (no admitted category means no non-null value)`);
    }
  }
  return problems;
}

function sourceListProblems(sources: unknown, where: string): string[] {
  if (!Array.isArray(sources)) return [`${where} must be a list`];
  const problems: string[] = [];
  sources.forEach((item, index) => {
    if (!isObject(item) || !sameKeys(item, ["id", "locator", "readLevel"])) problems.push(`${where}[${index}] must be {id, locator, readLevel}`);
    else if (!isText(item.id) || !isText(item.locator) || !has(V.readLevels, item.readLevel)) {
      problems.push(`${where}[${index}] needs id, locator and readLevel in ${V.readLevels.join(", ")}`);
    }
  });
  return problems;
}

function reasonProblems(reasons: unknown, where: string, inputs: Records, quantities: Records): string[] {
  if (!Array.isArray(reasons)) return [`${where}.reasons must be a list`];
  const problems: string[] = [];
  reasons.forEach((item, index) => {
    const at = `${where}.reasons[${index}]`;
    if (!isObject(item) || !sameKeys(item, ["code", "params", "parent"])) {
      problems.push(`${at} must be {code, params, parent} (no text from producers)`);
      return;
    }
    if (!has(V.reasonCodes, item.code)) {
      problems.push(`${at}: unknown reason code ${String(item.code)}`);
      return;
    }
    const params = item.params;
    if (!isObject(params) || !Object.keys(params).every((key) => KEY.test(key))) {
      problems.push(`${at}.params must be an object keyed by names`);
    } else {
      for (const [key, value] of Object.entries(params)) {
        if (value !== null && !isNumber(value) && typeof value !== "string" && typeof value !== "boolean") problems.push(`${at}.params.${key} must be a scalar`);
      }
      const needed: readonly string[] = V.reasonTemplates[item.code as ReasonCode].params;
      const missing = needed.filter((name) => !Object.hasOwn(params, name));
      if (missing.length) problems.push(`${at}: params ${missing.join(", ")} are required by the sentence template`);
    }
    const parent = item.parent;
    if (parent !== null) {
      if (!isObject(parent) || !sameKeys(parent, ["input", "kind"])) {
        problems.push(`${at}.parent must be null or {input, kind}`);
      } else if (typeof parent.input === "string" && Object.hasOwn(inputs, parent.input) && isObject(inputs[parent.input])) {
        const record = inputs[parent.input] as Json;
        if (parent.kind !== record.kind) problems.push(`${at}.parent kind ${String(parent.kind)} differs from the input record ${parent.input} (${String(record.kind)})`);
      } else if (typeof parent.input === "string" && Object.hasOwn(quantities, parent.input)) {
        if (parent.kind !== "derived") problems.push(`${at}.parent names sibling quantity ${parent.input}, whose kind is derived`);
      } else {
        problems.push(`${at}.parent ${String(parent.input)} is neither an input record nor a sibling quantity of this container`);
      }
    }
  });
  return problems;
}

/** Problems of one quantity in its container context (mirrors quantity_envelope.quantity_problems). */
export function quantityProblems(raw: unknown, where: string, inputs: Records, quantities: Records,
  schema: string = V.schema): string[] {
  if (!isObject(raw)) return [`${where} must be an object`];
  const problems: string[] = [];
  const v2 = schema === V2.schema;
  const table = v2 ? V2_DEFINITIONS : V1_DEFINITIONS;
  const extraKeys: readonly string[] = v2 && typeof raw.quantityDefinition === "string"
    ? ((V2.extraQuantityKeys as Readonly<Record<string, readonly string[]>>)[raw.quantityDefinition] ?? []) : [];
  const missing = V.quantityKeys.filter((key: string) => !Object.hasOwn(raw, key));
  const extra = Object.keys(raw).filter((key) => !has(V.quantityKeys, key) && !extraKeys.includes(key)).sort();
  if (missing.length) problems.push(`${where}: missing keys ${missing.join(", ")}`);
  if (extra.length) problems.push(`${where}: unknown keys ${extra.join(", ")}`);
  if (missing.length) return problems;
  const status = raw.status;
  const value = raw.value;
  if (!has(V.statuses, status)) return [...problems, `${where}.status must be one of ${V.statuses.join(", ")}`];
  if (typeof raw.quantityDefinition !== "string" || !Object.hasOwn(table, raw.quantityDefinition)) {
    return [...problems, `${where}.quantityDefinition ${String(raw.quantityDefinition)} is not a registered definition`];
  }
  const id = raw.quantityDefinition;
  const definition = table[id];
  if (raw.unit !== definition.unit) problems.push(`${where}.unit must be ${definition.unit} for ${id}`);
  const role = raw.leafRole;
  if (!has(V.leafRoles, role)) problems.push(`${where}.leafRole must be one of ${V.leafRoles.join(", ")}`);
  else if (!has(V.labelledRoles, role)) problems.push(`${where}: a registered quantity definition requires a labelled role`);
  const hasValue = value !== null;
  if (has(V.valueStatuses, status) && !hasValue) problems.push(`${where}: status ${String(status)} needs a value`);
  if (!has(V.valueStatuses, status) && hasValue) problems.push(`${where}: status ${String(status)} must carry value null`);
  if (hasValue) problems.push(...valueProblems(value, id, where, table));
  const evidence = raw.sourceEvidenceKind;
  if (evidence === "Measured") problems.push(`${where}: Measured never labels a quantity; transcribed measurements are observation records`);
  else if (evidence !== null && !isLabel(evidence)) problems.push(`${where}.sourceEvidenceKind must be one of ${V.quantitySourceEvidenceKinds.join(", ")} or null`);
  for (const key of ["dependsOn", "weakestInputs", "labelSources", "assumptions"] as const) {
    if (!isStrList(raw[key])) problems.push(`${where}.${key} must be a list of non-empty strings`);
  }
  const dependsOn = isStrList(raw.dependsOn) ? raw.dependsOn : null;
  const weakest = isStrList(raw.weakestInputs) ? raw.weakestInputs : [];
  const labelSources = isStrList(raw.labelSources) ? raw.labelSources : [];
  if (dependsOn) {
    const unknown = dependsOn.filter((name) => !Object.hasOwn(inputs, name) && !Object.hasOwn(quantities, name));
    if (unknown.length) problems.push(`${where}.dependsOn names ${unknown.join(", ")}, which are neither input records nor sibling quantities of this container`);
  }
  if (!hasValue && evidence !== null) problems.push(`${where}: a null value carries no source label`);
  if (!hasValue) {
    if (raw.uncertainty !== null) problems.push(`${where}: a null value carries no uncertainty`);
    if (isObject(raw.identity) && raw.identity.parent !== null) problems.push(`${where}: a null value carries no parent identity`);
    if (!dependsOn?.length) problems.push(`${where}: a null quantity must name its blocking input or sibling in dependsOn`);
  }
  if (evidence === null && (weakest.length || labelSources.length)) problems.push(`${where}: weakestInputs and labelSources stay empty without a source label`);
  if (has(V.unlabelledRoles, role) && evidence !== null) problems.push(`${where}: a ${String(role)} leaf carries no source label`);
  if (role === "requestInput" && evidence !== null && evidence !== "User input") problems.push(`${where}: a request echo reads User input or null`);
  if (hasValue && has(V.labelledRoles, role) && dependsOn) {
    const expected = sourceLabel(inputs, dependsOn, quantities);
    if (!expected.determiningInputs.length) problems.push(`${where}: no determining physical or coefficient input; request process values never decide a label`);
    if (evidence === null) problems.push(`${where}: a non-null ${String(role)} value needs its per-value source label`);
    else if (evidence !== expected.sourceEvidenceKind) problems.push(`${where}: source label ${String(evidence)} differs from the label rule (${expected.sourceEvidenceKind}); no upgrade or downgrade by hand`);
    if ((evidence === "User input" || evidence === "Unresolved") && !weakest.length) problems.push(`${where}: ${evidence} must name its inputs (weakestInputs)`);
    if (evidence === "Literature estimate" && !labelSources.length) problems.push(`${where}: Literature estimate needs its labelSources`);
    if (!equalLists(weakest, expected.weakestInputs) || !equalLists(labelSources, expected.labelSources)) {
      problems.push(`${where}: weakestInputs/labelSources differ from the label rule`);
    }
  }
  problems.push(...reasonProblems(raw.reasons, where, inputs, quantities));
  if (Array.isArray(raw.reasons)) {
    const codes = raw.reasons.filter(isObject).map((item) => item.code);
    if (status === "computed" && codes.length) problems.push(`${where}: a computed value carries no blocking reason`);
    if (status !== "computed" && !codes.length) problems.push(`${where}: status ${String(status)} needs at least one reason`);
    if (status === "not-requested" && !codes.includes("not-requested")) problems.push(`${where}: status not-requested carries the reason not-requested`);
  }
  const numerical = raw.numericalStatus;
  if (!(isObject(numerical) && sameKeys(numerical, ["state", "settings", "residuals"]) && has(V.numericalStates, numerical.state)
    && isObject(numerical.settings) && isObject(numerical.residuals))) {
    problems.push(`${where}.numericalStatus must be {state in ${V.numericalStates.join(", ")}, settings, residuals}`);
  }
  const physical = raw.physicalValidation;
  if (!(isObject(physical) && sameKeys(physical, Object.keys(V.physicalValidation)) && physical.status === "unvalidated"
    && physical.experimentalValidation === false && physical.productionReady === false)) {
    problems.push(`${where}.physicalValidation must be unvalidated with experimentalValidation and productionReady false`);
  }
  problems.push(...sourceListProblems(raw.sources, `${where}.sources`));
  const sources = Array.isArray(raw.sources) ? raw.sources : [];
  if (!hasValue && sources.length) problems.push(`${where}: a null value carries no source claim (no stale DOI on a null value)`);
  if (raw.validity !== null && !isObject(raw.validity)) problems.push(`${where}.validity must be an object or null`);
  const uncertainty = raw.uncertainty;
  if (uncertainty !== null) {
    if (!(isObject(uncertainty) && sameKeys(uncertainty, ["kind", "construction"]) && has(V.uncertaintyKinds, uncertainty.kind)
      && (uncertainty.construction === null || isText(uncertainty.construction)))) {
      problems.push(`${where}.uncertainty must be {kind in ${V.uncertaintyKinds.join(", ")}, construction}`);
    } else if (definition.valueKind === "alternatives" && uncertainty.kind !== "model-alternatives") {
      problems.push(`${where}: two source models are model alternatives, never an interval`);
    }
  }
  const basis = raw.fractionBasis;
  if (basis !== null && !has(V.fractionBases, basis)) problems.push(`${where}.fractionBasis must be one of ${V.fractionBases.join(", ")} or null`);
  if (basis !== null && !definition.fraction) problems.push(`${where}: fractionBasis applies only to fraction quantities`);
  let identity: Json | null = raw.identity as Json | null;
  if (!(isObject(identity) && sameKeys(identity, ["input", "model", "parent"])
    && Object.values(identity).every((item) => item === null || isText(item)))) {
    problems.push(`${where}.identity must be {input, model, parent} strings or null`);
    identity = null;
  }
  if (hasValue && has(V.labelledRoles, role)) {
    if (!dependsOn || !dependsOn.length) problems.push(`${where}: a non-null value names the inputs it depends on`);
    if (!sources.length) problems.push(`${where}: a non-null value names its source relation (sources)`);
    if (uncertainty === null) problems.push(`${where}: a non-null value states its uncertainty (at least not-quantified)`);
    if (definition.fraction && basis === null) problems.push(`${where}: a fraction needs its fractionBasis`);
    if (identity) {
      if (!identity.model) problems.push(`${where}: a non-null value names its engine/model identity`);
      const expectedParent = dependsOn ? parentKey(inputs, dependsOn, quantities) : null;
      if (!identity.parent) problems.push(`${where}: a non-null value names its parent identity`);
      else if (identity.parent !== expectedParent) problems.push(`${where}: parent identity is not the current parent ${String(expectedParent)}; a stale-parent value is not current`);
    }
  }
  if (v2) problems.push(...estimateProblems(raw, where, inputs, quantities));
  return problems;
}

// --- Envelope v2: SOL-C typed estimate fields (mirrors quantity_envelope.estimate_problems) -----------------------

/** One estimateBand or inputSensitivity record (A7 range object inside validity). */
export function rangeProblems(band: unknown, value: unknown, unit: string, where: string): string[] {
  if (!isObject(band) || !sameKeys(band, V2.rangeKeys)) return [`${where} must be exactly the keys ${V2.rangeKeys.join(", ")}`];
  const problems: string[] = [];
  if (band.unit !== unit) problems.push(`${where}.unit must be the quantity unit ${unit}`);
  if (!has(V2.rangeConstructions, band.construction)) problems.push(`${where}.construction must be one of ${V2.rangeConstructions.join(", ")}`);
  const low = band.lower, high = band.upper;
  if (isObject(value)) {
    if (!(isObject(low) && isObject(high) && sameKeys(low, Object.keys(value)) && sameKeys(high, Object.keys(value)))) {
      problems.push(`${where}: lower/upper must be maps with the value's members`);
    } else {
      for (const [name, nominal] of Object.entries(value)) {
        if (!(isNumber(low[name]) && isNumber(high[name]) && isNumber(nominal) && (low[name] as number) <= nominal && nominal <= (high[name] as number))) {
          problems.push(`${where}: member ${name} range must be ordered and contain the value`);
        }
      }
    }
  } else if (!(isNumber(value) && isNumber(low) && isNumber(high) && low <= value && value <= high)) {
    problems.push(`${where}: lower <= value <= upper with finite numbers (no categorical interval)`);
  }
  const rows = band.inputRanges;
  if (!Array.isArray(rows) || rows.length === 0) problems.push(`${where}.inputRanges must be a non-empty list`);
  else {
    const names: string[] = [];
    rows.forEach((row, index) => {
      const at = `${where}.inputRanges[${index}]`;
      if (!isObject(row) || !sameKeys(row, V2.inputRangeKeys)) { problems.push(`${at} must be exactly the keys ${V2.inputRangeKeys.join(", ")}`); return; }
      names.push(String(row.name));
      if (!isText(row.name) || !isText(row.unit)) problems.push(`${at}: name and unit must be non-empty`);
      if (!(isNumber(row.lower) && isNumber(row.nominal) && isNumber(row.upper) && row.lower <= row.nominal && row.nominal <= row.upper)) {
        problems.push(`${at}: finite ordered bounds containing the nominal`);
      }
    });
    if (new Set(names).size !== names.length) problems.push(`${where}.inputRanges names must be unique`);
  }
  const arms = band.armIds;
  if (!(isStrList(arms) && arms.length > 0 && new Set(arms).size === arms.length)) problems.push(`${where}.armIds must be unique executed arm identities`);
  const unknown = band.unknownComponents;
  if (!(isStrList(unknown) && unknown.every((item) => has(V2.unknownComponents, item)) && unknown.includes("model-error"))) {
    problems.push(`${where}.unknownComponents must name model-error and only ${V2.unknownComponents.join(", ")}`);
  } else if (band.construction === "ofat" && !unknown.includes("input-interactions")) {
    problems.push(`${where}: a one-factor-at-a-time range names input-interactions as unknown`);
  }
  return problems;
}

/** Warning codes and null-parent state over a quantity's dependency closure (A7 emit contract). */
export function inheritedWarningCodes(name: string, inputs: Records, quantities: Records, stack: readonly string[] = []): { codes: Set<string>; nullParent: boolean } {
  if (stack.includes(name)) return { codes: new Set(), nullParent: true };
  const isInput = Object.hasOwn(inputs, name);
  const record = isInput ? inputs[name] : quantities[name];
  if (!isObject(record)) return { codes: new Set(), nullParent: true };
  const codes = new Set<string>();
  if (isInput) {
    if (record.kind === "alloyTransfer") codes.add("alloy-family-transfer");
    if (record.status === "extrapolated" || record.status === "outOfRange") codes.add("domain-extrapolation");
  } else if (stack.length) {
    const validity = isObject(record.validity) ? record.validity : {};
    for (const item of Array.isArray(validity.domainWarnings) ? validity.domainWarnings : []) {
      if (isObject(item) && typeof item.code === "string") codes.add(item.code);
    }
  }
  let nullParent = stack.length > 0 && !isInput && record.value === null;
  for (const dep of isStrList(record.dependsOn) ? record.dependsOn : []) {
    const inner = inheritedWarningCodes(dep, inputs, quantities, [...stack, name]);
    inner.codes.forEach((code) => codes.add(code));
    nullParent = nullParent || inner.nullParent;
  }
  return { codes, nullParent };
}

function estimateProblems(q: Json, where: string, inputs: Records, quantities: Records): string[] {
  const problems: string[] = [];
  const id = String(q.quantityDefinition);
  const definition = V2_DEFINITIONS[id];
  if (!definition) return problems;
  const value = q.value;
  const hasValue = value !== null;
  const validity = q.validity;
  if (!isObject(validity)) return [`${where}.validity must carry the typed estimate fields`];
  const missing = V2.validityRequiredKeys.filter((key: string) => !Object.hasOwn(validity, key));
  if (missing.length) problems.push(`${where}.validity misses ${missing.join(", ")}`);
  const tier = validity.estimateTier;
  if (!has(V2.tiers, tier)) problems.push(`${where}.validity.estimateTier must be one of ${V2.tiers.join(", ")}`);
  else if (hasValue === (tier === "no-value")) problems.push(`${where}: estimateTier is no-value exactly when the value is null`);
  const digitsTable = V2.displaySignificantDigits as Readonly<Record<string, number>>;
  const expectedDigits = hasValue ? digitsTable[id] ?? null : null;
  if (hasValue && expectedDigits === null) problems.push(`${where}: ${id} has no admitted display precision`);
  else if (validity.displaySignificantDigits !== expectedDigits) problems.push(`${where}.validity.displaySignificantDigits must be ${String(expectedDigits)}`);
  const codes = new Set<string>();
  const warnings = Array.isArray(validity.domainWarnings) ? validity.domainWarnings : null;
  if (!warnings) problems.push(`${where}.validity.domainWarnings must be a list`);
  (warnings ?? []).forEach((item, index) => {
    if (!(isObject(item) && sameKeys(item, ["code", "detail"]) && has(V2.warningCodes, item.code) && isText(item.detail))) {
      problems.push(`${where}.validity.domainWarnings[${index}] must be {code, detail} with a closed value-warning code`);
    } else codes.add(item.code as string);
  });
  const reasons = Array.isArray(q.reasons) ? q.reasons : [];
  for (const item of reasons) if (isObject(item) && has(V2.warningCodes, item.code)) problems.push(`${where}: value warning ${String(item.code)} is not a blocking reason`);
  if ((reasons.length > 0) === hasValue) problems.push(`${where}: blocking reasons are present exactly when the value is null`);
  const name = Object.keys(quantities).find((key) => quantities[key] === q);
  const inherited = name === undefined ? { codes: new Set<string>(), nullParent: false } : inheritedWarningCodes(name, inputs, quantities);
  if (hasValue) {
    if (inherited.nullParent) problems.push(`${where}: a value cannot depend on a null parent`);
    const lost = [...inherited.codes].filter((code) => !codes.has(code)).sort();
    if (lost.length) problems.push(`${where}: inherited warnings ${lost.join(", ")} are missing from domainWarnings`);
  }
  const all = new Set([...inherited.codes, ...codes]);
  if (tier === "Estimated") {
    if (V2.tierCappingWarningCodes.some((code: string) => all.has(code))) problems.push(`${where}: a transfer or out-of-domain dependency caps the value at Physics estimate`);
    if (definition.valueKind === "alternatives" || definition.valueKind === "category") problems.push(`${where}: ${definition.valueKind} values are never Estimated`);
    problems.push(...rangeProblems(validity.estimateBand, value, definition.unit, `${where}.validity.estimateBand`));
  } else if (validity.estimateBand !== null && validity.estimateBand !== undefined) problems.push(`${where}: an estimateBand exists only at tier Estimated`);
  if (validity.inputSensitivity !== null && validity.inputSensitivity !== undefined) {
    if (tier !== "Physics estimate") problems.push(`${where}: inputSensitivity is auxiliary to a Physics estimate only`);
    problems.push(...rangeProblems(validity.inputSensitivity, value, definition.unit, `${where}.validity.inputSensitivity`));
  }
  const statement = tier === "Physics estimate" ? V2.uncertaintyStatementTier2 : null;
  if (validity.uncertaintyStatement !== statement) problems.push(`${where}.validity.uncertaintyStatement must be ${String(statement)}`);
  const uncertainty = q.uncertainty;
  if (hasValue && isObject(uncertainty)) {
    const expected = definition.valueKind === "alternatives" ? "model-alternatives" : tier === "Estimated" ? "parameter-sensitivity" : "not-quantified";
    if (uncertainty.kind !== expected) problems.push(`${where}.uncertainty.kind must be ${expected} at tier ${String(tier)}`);
    if (!isText(uncertainty.construction)) problems.push(`${where}.uncertainty.construction must explain the construction`);
  }
  const basis = (V2.fractionBasis as Readonly<Record<string, string>>)[id];
  if (hasValue && basis !== undefined && q.fractionBasis !== basis) problems.push(`${where}.fractionBasis must be ${basis}`);
  if (hasValue && (id === "equiaxed-envelope-fraction" || id === "cet-class") && validity.nucleationScenarioNote !== V2.nucleationScenarioNote) {
    problems.push(`${where}.validity.nucleationScenarioNote must be the exact nucleation scenario note`);
  }
  if (hasValue && id === "km-alpha-m-fraction") problems.push(...kmProblems(q, where));
  return problems;
}

function kmProblems(q: Json, where: string): string[] {
  const problems: string[] = [];
  const ev = q.evaluation, residual = q.residual;
  if (!isObject(ev) || !sameKeys(ev, V2.kmEvaluationKeys)) return [`${where}.evaluation must be exactly ${V2.kmEvaluationKeys.join(", ")}`];
  if (ev.ruleId !== V2.kmEvaluationRule || ev.timeInterpolation !== "linear-in-temperature") problems.push(`${where}.evaluation rule must be ${V2.kmEvaluationRule}`);
  if (!(isNumber(ev.preheat_K) && isNumber(ev.offset_K) && isNumber(ev.temperature_K) && ev.preheat_K > 0 && ev.offset_K === 25
    && Math.abs(ev.temperature_K - ev.preheat_K - 25) <= 1e-9)) problems.push(`${where}.evaluation temperature must be preheat + 25 K`);
  if (!(isNumber(ev.time_s) && ev.time_s >= 0)) problems.push(`${where}.evaluation.time_s must be finite and nonnegative`);
  const ids = ev.historyBracketIds;
  if (!(isStrList(ids) && ids.length === 2 && ids[0] !== ids[1])) problems.push(`${where}.evaluation.historyBracketIds must be two distinct node IDs`);
  const ref = ev.refinement;
  if (!(isObject(ref) && sameKeys(ref, ["status", "timeTolerance_s", "temperatureTolerance_K"]) && ref.status === "refinement-passed"
    && isNumber(ref.timeTolerance_s) && ref.timeTolerance_s > 0 && isNumber(ref.temperatureTolerance_K) && ref.temperatureTolerance_K > 0)) {
    problems.push(`${where}.evaluation.refinement must have passed with positive tolerances`);
  }
  const value = q.value;
  if (!(isObject(residual) && sameKeys(residual, V2.kmResidualKeys) && Object.values(residual).every((x) => isNumber(x) && x >= 0 && x <= 1)
    && isNumber(value) && Math.abs(value + (residual.untransformedAsymptote as number) - (residual.beta0 as number)) <= 1e-12
    && Math.abs((residual.preExistingConstituent as number) - (1 - (residual.beta0 as number))) <= 1e-12)) {
    problems.push(`${where}.residual must conserve value + untransformedAsymptote = beta0 (no retained beta)`);
  }
  return problems;
}

/** One quantity checked in its container context, optionally against its contract declaration. */
export function checkedQuantity(raw: unknown, context: { inputs: Records; quantities: Records },
  declaration?: ContractQuantityDeclaration, where = "quantity"): Quantity {
  const problems = quantityProblems(raw, where, context.inputs, context.quantities);
  if (!problems.length && declaration) problems.push(...declarationProblems(raw as unknown as Quantity, declaration, where));
  if (problems.length) rejected("quantity", problems);
  return raw as unknown as Quantity;
}

function declarationProblems(q: Quantity, declaration: ContractQuantityDeclaration, where: string): string[] {
  const problems: string[] = [];
  if (q.quantityDefinition !== declaration.definition || q.unit !== declaration.unit) problems.push(`${where}: definition/unit differ from the declaration`);
  if (!declaration.statuses.includes(q.status)) problems.push(`${where}: status ${q.status} is not declared`);
  if (q.leafRole !== declaration.leafRole) problems.push(`${where}: leafRole ${q.leafRole} differs from the declaration`);
  if (q.sourceEvidenceKind !== null && !declaration.sourceEvidenceKinds.includes(q.sourceEvidenceKind)) problems.push(`${where}: source label ${q.sourceEvidenceKind} is not declared`);
  for (const item of q.reasons) if (!declaration.reasonCodes.includes(item.code)) problems.push(`${where}: reason code ${item.code} is not declared`);
  if (q.value !== null && q.fractionBasis !== declaration.fractionBasis) problems.push(`${where}: fractionBasis differs from the declaration`);
  return problems;
}

export function observationProblems(raw: unknown, where = "observation"): string[] {
  if (!isObject(raw)) return [`${where} must be an object`];
  if (!sameKeys(raw, V.observationKeys)) return [`${where}: keys must be exactly ${V.observationKeys.join(", ")}`];
  const problems: string[] = [];
  if (raw.recordKind !== V.observationRecordKind) problems.push(`${where}.recordKind must be ${V.observationRecordKind}`);
  if (!isText(raw.observable)) problems.push(`${where}.observable must name the transcribed observable`);
  const value = raw.value;
  if (!(isNumber(value) || (isObject(value) && Object.keys(value).length > 0 && Object.entries(value).every(([k, v]) => isText(k) && isNumber(v))))) {
    problems.push(`${where}.value must be a finite number or an object of finite numbers`);
  }
  if (!has(V.units, raw.unit)) problems.push(`${where}.unit must be one of ${V.units.join(", ")}`);
  if (!has(V.observationSourceEvidenceKinds, raw.sourceEvidenceKind)) problems.push(`${where}.sourceEvidenceKind must be one of ${V.observationSourceEvidenceKinds.join(", ")}`);
  problems.push(...sourceListProblems(raw.sources, `${where}.sources`));
  if (Array.isArray(raw.sources) && raw.sources.length === 0) problems.push(`${where}: an observation names its source`);
  for (const key of ["materialScope", "processScope"] as const) if (!isText(raw[key])) problems.push(`${where}.${key} must be a non-empty string`);
  if (!has(V.comparability, raw.comparability)) problems.push(`${where}.comparability must be one of ${V.comparability.join(", ")}`);
  return problems;
}

/** A transcribed source observation record (the only record that may read Measured). */
export function checkedObservation(raw: unknown, declaration?: ContractObservationDeclaration, where = "observation"): Observation {
  const problems = observationProblems(raw, where);
  if (!problems.length && declaration) {
    const o = raw as unknown as Observation;
    if (o.observable !== declaration.observable) problems.push(`${where}: observable differs from the declaration`);
    if (!declaration.sourceEvidenceKinds.includes(o.sourceEvidenceKind)) problems.push(`${where}: source label ${o.sourceEvidenceKind} is not declared`);
  }
  if (problems.length) rejected("observation", problems);
  return raw as unknown as Observation;
}

export interface ContainerOptions {
  /** Registry maturity label the container must echo. */
  readonly moduleMaturity?: string;
  /** Declarations keyed by quantity name; when given, the container holds exactly these quantities. */
  readonly quantityDeclarations?: Readonly<Record<string, ContractQuantityDeclaration>>;
  readonly observationDeclarations?: Readonly<Record<string, ContractObservationDeclaration>>;
  /** Envelope schema the container must carry (v1 by default; the SOL-C estimate channel uses v2). */
  readonly schema?: string;
}

/** Problems of one container (an object holding a quantities map), mirroring quantity_envelope.container_problems. */
export function containerProblems(raw: unknown, where = "container", options: ContainerOptions = {}): string[] {
  if (!isObject(raw)) return [`${where} must be an object`];
  const problems: string[] = [];
  for (const key of V.containerRequiredKeys) if (!Object.hasOwn(raw, key)) problems.push(`${where}: a container carries ${key}`);
  const schema = options.schema ?? V.schema;
  if (raw.quantityEnvelopeSchema !== schema) problems.push(`${where}.quantityEnvelopeSchema must be ${schema}`);
  if (raw.moduleEvidenceCeiling !== V.moduleEvidenceCeiling) problems.push(`${where}.moduleEvidenceCeiling must be ${V.moduleEvidenceCeiling} (decision 1)`);
  if (!has(V.moduleMaturities, raw.moduleMaturity)) problems.push(`${where}.moduleMaturity must be one of ${V.moduleMaturities.join(", ")}`);
  else if (options.moduleMaturity !== undefined && raw.moduleMaturity !== options.moduleMaturity) problems.push(`${where}.moduleMaturity must echo the registry label ${options.moduleMaturity}`);
  const quantities = raw.quantities;
  if (!isObject(quantities)) return [...problems, `${where}.quantities must be an object`];
  let inputs: Json = {};
  if (Object.hasOwn(raw, "inputProvenance")) {
    if (isObject(raw.inputProvenance)) inputs = raw.inputProvenance;
    else problems.push(`${where}.inputProvenance must be an object`);
  }
  for (const [name, record] of Object.entries(inputs)) {
    if (!KEY.test(name)) problems.push(`${where}.inputProvenance key ${name} must be a plain name`);
    problems.push(...valueProvenanceProblems(record, `${where}.inputProvenance.${name}`));
    if (isObject(record) && record.kind === "sourcedAlternative" && raw.default !== false) {
      problems.push(`${where}: sourcedAlternative requires container default: false`);
    }
  }
  if (Object.hasOwn(raw, "default") && typeof raw.default !== "boolean") problems.push(`${where}.default must be a boolean`);
  const overlap = Object.keys(inputs).filter((name) => Object.hasOwn(quantities, name)).sort();
  if (overlap.length) problems.push(`${where}: names ${overlap.join(", ")} are both an input and a quantity`);
  let observations: Json = {};
  if (Object.hasOwn(raw, "observations")) {
    if (isObject(raw.observations)) observations = raw.observations;
    else problems.push(`${where}.observations must be an object`);
  }
  for (const [name, record] of Object.entries(observations)) {
    const at = `${where}.observations.${name}`;
    const declaration = options.observationDeclarations?.[name];
    if (options.observationDeclarations && !declaration) problems.push(`${at}: not declared`);
    const recordProblems = observationProblems(record, at);
    problems.push(...recordProblems);
    if (!recordProblems.length && declaration) {
      try { checkedObservation(record, declaration, at); } catch (error) { problems.push((error as Error).message); }
    }
  }
  for (const [name, q] of Object.entries(quantities)) {
    const at = `${where}.quantities.${name}`;
    if (!KEY.test(name)) problems.push(`${where}.quantities key ${name} must be a plain name`);
    const quantityProblemList = quantityProblems(q, at, inputs, quantities, schema);
    problems.push(...quantityProblemList);
    const declaration = options.quantityDeclarations?.[name];
    if (options.quantityDeclarations && !declaration) problems.push(`${at}: not declared`);
    if (!quantityProblemList.length && declaration) problems.push(...declarationProblems(q as unknown as Quantity, declaration, at));
  }
  for (const name of Object.keys(options.quantityDeclarations ?? {})) {
    if (!Object.hasOwn(quantities, name)) problems.push(`${where}: declared quantity ${name} is missing from this container`);
  }
  for (const name of Object.keys(options.observationDeclarations ?? {})) {
    if (!Object.hasOwn(observations, name)) problems.push(`${where}: declared observation ${name} is missing from this container`);
  }
  // Parent propagation: a dependent of a null sibling is null and names that parent in a reason.
  for (const [name, q] of Object.entries(quantities)) {
    if (!isObject(q) || !isStrList(q.dependsOn)) continue;
    for (const dep of q.dependsOn) {
      const parent = !Object.hasOwn(inputs, dep) && Object.hasOwn(quantities, dep) ? quantities[dep] : undefined;
      if (!isObject(parent) || parent.value !== null) continue;
      if (q.value !== null) problems.push(`${where}.quantities.${name}: parent quantity ${dep} is null, so this value is null`);
      else if (!(Array.isArray(q.reasons) && q.reasons.some((item) => isObject(item) && isObject(item.parent) && item.parent.input === dep))) {
        problems.push(`${where}.quantities.${name}: a reason must name the null parent ${dep}`);
      }
    }
  }
  return problems;
}

/** A whole container, or an Error naming every problem (no repair, no dual-read). */
export function checkedQuantityContainer(raw: unknown, options: ContainerOptions = {}): QuantityContainer {
  const problems = containerProblems(raw, "container", options);
  if (problems.length) rejected("quantity container", problems);
  return raw as unknown as QuantityContainer;
}

export interface EstimateRange {
  readonly lower: number | Readonly<Record<string, number>>;
  readonly upper: number | Readonly<Record<string, number>>;
  readonly unit: string;
  readonly construction: "ofat" | "joint";
  readonly inputRanges: readonly { readonly name: string; readonly unit: string; readonly nominal: number; readonly lower: number; readonly upper: number }[];
  readonly armIds: readonly string[];
  readonly unknownComponents: readonly UnknownComponent[];
}

export interface EstimateValidity {
  readonly estimateTier: EstimateTier;
  readonly tierLabel?: string;
  readonly displaySignificantDigits: number | null;
  readonly domainWarnings: readonly { readonly code: ValueWarningCode; readonly detail: string }[];
  readonly estimateBand: EstimateRange | null;
  readonly inputSensitivity: EstimateRange | null;
  readonly uncertaintyStatement: string | null;
  readonly nucleationScenarioNote?: string;
  readonly explanation?: string | null;
  readonly noValueText?: string | null;
  readonly [key: string]: unknown;
}

export interface EstimateQuantity extends Omit<Quantity, "validity" | "quantityDefinition"> {
  readonly quantityDefinition: EstimateQuantityDefinitionId;
  readonly validity: EstimateValidity;
  readonly evaluation?: Readonly<Record<string, unknown>>;
  readonly residual?: Readonly<Record<string, number>>;
}

export interface EstimateContainer extends Omit<QuantityContainer, "quantityEnvelopeSchema" | "quantities"> {
  readonly quantityEnvelopeSchema: typeof QUANTITY_ENVELOPE.estimates.schema;
  readonly quantities: Readonly<Record<string, EstimateQuantity>>;
}

/** A quantity envelope v2 container (SOL-C estimate channel), or an Error naming every problem. */
export function checkedEstimateContainer(raw: unknown, options: Omit<ContainerOptions, "schema"> = {}): EstimateContainer {
  const problems = containerProblems(raw, "container", { ...options, schema: V2.schema });
  if (problems.length) rejected("estimate container", problems);
  return raw as unknown as EstimateContainer;
}
