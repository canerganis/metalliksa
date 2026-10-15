/**
 * Pure helpers of the Research model panel: request identity, per-alloy option shaping, number display and the
 * served-difference statements (contract 4.5, 4.6, 4.7, 8, 9.3). No physics lives here: defaults, limits, labels and
 * checks come from the describe stage, and no research value is ever written to a served store.
 */
import type {
  ResearchBlock,
  ResearchHostId,
  ResearchLeaf,
  ResearchModuleContainer,
  ResearchOptions,
  ResearchProcess,
  ResearchPropertyContext,
  ResearchServedDifference,
} from "../types/lpbfResearchModels";

// ---------------------------------------------------------------------------------------------------------------
// Host input and identity

export interface ResearchHostInput {
  material: string;
  laserPower_W: number;
  scanSpeed_mm_s: number;
  beamDiameter_um: number;
  preheatTemp_C: number;
  /** Served enum; the Build Job host is fixed to IR. A non-IR value is reported per module by the research route. */
  laserWavelength?: ResearchProcess["laserWavelength"];
  propertyContext: ResearchPropertyContext;
}

export function toResearchProcess(input: ResearchHostInput): ResearchProcess {
  return {
    material: input.material,
    laserPower_W: input.laserPower_W,
    scanSpeed_mm_s: input.scanSpeed_mm_s,
    beamDiameter_um: input.beamDiameter_um,
    preheatTemp_C: input.preheatTemp_C,
    laserWavelength: input.laserWavelength ?? "IR_1064nm",
    absorptionModel: "flat-plate",
  };
}

const ALLOY_NAMES: ReadonlyArray<readonly [string, string]> = [
  ["ti6al4v", "ti6al4v"],
  ["ti64", "ti6al4v"],
  ["alsi10mg", "alsi10mg"],
  ["inconel718", "in718"],
  ["in718", "in718"],
  ["316lstainlesssteel", "ss316l"],
  ["ss316l", "ss316l"],
  ["316l", "ss316l"],
];

/** Alloy key of the option store: the served alloy id for the four Build Job alloys, else the normalised name. */
export function researchAlloyKey(material: string): string {
  const flat = material.toLowerCase().replace(/[^a-z0-9]/g, "");
  for (const [name, id] of ALLOY_NAMES) if (flat === name || flat.startsWith(name)) return id;
  return flat || "unknown";
}

/** The research subset of a served request: what must match before a served number is shown beside a research one. */
export function researchProcessSignature(p: {
  material: string; laserPower_W: number; scanSpeed_mm_s: number; beamDiameter_um: number; preheatTemp_C: number;
  laserWavelength: string;
}): string {
  return JSON.stringify([p.material, p.laserPower_W, p.scanSpeed_mm_s, p.beamDiameter_um, p.preheatTemp_C, p.laserWavelength]);
}

export function inputSignature(input: ResearchHostInput): string {
  return researchProcessSignature({ ...toResearchProcess(input) });
}

// ---------------------------------------------------------------------------------------------------------------
// Options kept per alloy

export type OptionValue = number | string;
export interface AlloyOptions {
  marangoni: Record<string, OptionValue>;
  surfaceBalance: Record<string, OptionValue>;
  ranges: {
    marangoni: Record<string, { min: number; max: number }>;
    surfaceBalance: Record<string, { min: number; max: number }>;
  };
}
export type OptionModule = "marangoni" | "surfaceBalance";

export const VAPOUR_OVERRIDE_KEYS = ["vapourTemperature_K", "vapourLatentHeat_J_kg", "vapourMolarMass_kg_mol"] as const;
export const DIRECT_SLOPE_KEY = "surfaceTensionSlope_N_mK";

export function emptyAlloyOptions(): AlloyOptions {
  return { marangoni: {}, surfaceBalance: {}, ranges: { marangoni: {}, surfaceBalance: {} } };
}

function sortedRecord<T>(source: Record<string, T>): Record<string, T> {
  const out: Record<string, T> = {};
  for (const key of Object.keys(source).sort()) out[key] = source[key];
  return out;
}

/**
 * The options a request carries (B8): in a Belton slope mode the request has no direct slope and no range for it; the
 * store keeps the saved direct value, so returning to `direct` restores it. Keys are ordered so equal options give one
 * identity key.
 */
export function buildResearchOptions(options: AlloyOptions): ResearchOptions {
  const marangoni = { ...options.marangoni };
  const marangoniRanges = { ...options.ranges.marangoni };
  const mode = marangoni.slopeMode;
  if (typeof mode === "string" && mode !== "direct") {
    delete marangoni[DIRECT_SLOPE_KEY];
    delete marangoniRanges[DIRECT_SLOPE_KEY];
  }
  const ranges = (r: Record<string, { min: number; max: number }>) => {
    const out: Record<string, { min: number; max: number }> = {};
    for (const key of Object.keys(r).sort()) out[key] = { min: r[key].min, max: r[key].max };
    return out;
  };
  return {
    marangoni: sortedRecord(marangoni),
    surfaceBalance: sortedRecord(options.surfaceBalance),
    ranges: { marangoni: ranges(marangoniRanges), surfaceBalance: ranges(options.ranges.surfaceBalance) },
  };
}

export function identityKey(input: ResearchHostInput, options: AlloyOptions): string {
  return JSON.stringify({ process: toResearchProcess(input), propertyContext: input.propertyContext, options: buildResearchOptions(options) });
}

export function supersedeKeyFor(host: ResearchHostId): string {
  return `p8-research:${host}`;
}

// ---------------------------------------------------------------------------------------------------------------
// Number display (4.7 display rules)

function trimZeros(text: string): string {
  return text.includes(".") ? text.replace(/\.?0+$/, "") : text;
}

/** 4 significant digits on screen; the exact double stays in the "Exact values" row. */
export function sig4(value: number): string {
  if (value === 0) return "0";
  const text = value.toPrecision(4);
  const e = text.indexOf("e");
  if (e >= 0) return `${trimZeros(text.slice(0, e))}${text.slice(e)}`;
  return trimZeros(text);
}

const unitSuffix = (unit: string): string => (unit && unit !== "1" ? ` ${unit}` : "");

export function formatScalar(value: unknown, unit: string): string | null {
  if (typeof value === "number") return Number.isFinite(value) ? `${sig4(value)}${unitSuffix(unit)}` : null;
  if (typeof value === "string") return value;
  if (typeof value === "boolean") return value ? "true" : "false";
  return null;
}

export function exactText(value: unknown): string | null {
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : null;
  if (value === null || value === undefined) return null;
  return typeof value === "string" ? value : JSON.stringify(value);
}

export function isScalar(value: unknown): value is number | string | boolean {
  return typeof value === "number" || typeof value === "string" || typeof value === "boolean";
}

/** Display unit for a served path, by the same suffix rule as the research units. */
const SERVED_UNIT_SUFFIXES: ReadonlyArray<readonly [string, string]> = [
  ["_um", "um"], ["_kPa", "kPa"], ["_MW_cm2", "MW/cm2"], ["_W_mK", "W/m/K"], ["_J_kgK", "J/kg/K"], ["_m2_s", "m2/s"],
  ["_N_mK", "N/m/K"], ["_m_s", "m/s"], ["_K_s", "K/s"], ["_ppm", "ppm"], ["_Pa", "Pa"], ["_C", "C"], ["_K", "K"], ["_W", "W"], ["_m", "m"],
];
function servedUnit(path: string): string {
  const leaf = path.split(".").pop() ?? "";
  for (const [suffix, unit] of SERVED_UNIT_SUFFIXES) if (leaf.endsWith(suffix)) return unit;
  return "";
}

// ---------------------------------------------------------------------------------------------------------------
// Served-difference statements (section 8, 4.6)

export interface DifferenceContext {
  host: ResearchHostId;
  alloyId: string;
  /** The served thermal result (PythonLPBFResult in the Melt Pool lab, job.thermal in the Build Job lab), or null. */
  served: unknown;
  /** True only when the served result was produced by the inputs of this run (4.6). */
  servedMatches: boolean;
  block: ResearchBlock;
}

function getPath(root: unknown, path: string): unknown {
  let cursor: unknown = root;
  for (const part of path.split(".")) {
    if (typeof cursor !== "object" || cursor === null || !(part in cursor)) return undefined;
    cursor = (cursor as Record<string, unknown>)[part];
  }
  return cursor;
}

function researchField(block: ResearchBlock, path: string): ResearchLeaf | undefined {
  const dot = path.indexOf(".");
  if (dot < 0) return undefined;
  const container = (block as Record<string, unknown>)[path.slice(0, dot)] as ResearchModuleContainer | undefined;
  return container?.fields?.[path.slice(dot + 1)];
}

function conditionHolds(condition: string, diff: ResearchServedDifference, ctx: DifferenceContext): boolean {
  switch (condition) {
    case "always": return true;
    case "host-build-job": return ctx.host === "build-job";
    case "host-melt-pool": return ctx.host === "melt-pool";
    case "alloy-alsi10mg": return ctx.alloyId === "alsi10mg";
    case "served-null": return getPath(ctx.served, diff.servedPaths[0] ?? "") === null;
    case "served-number": {
      const v = getPath(ctx.served, diff.servedPaths[0] ?? "");
      return typeof v === "number" && Number.isFinite(v);
    }
    case "research-positive": {
      const leaf = researchField(ctx.block, diff.researchPaths[0] ?? "");
      return typeof leaf?.value === "number" && leaf.value > 0;
    }
    case "served-kernel-eagar-tsai-and-below-onset": {
      const ratio = researchField(ctx.block, "keyholeCavity.powerOverOnset")?.value;
      return getPath(ctx.served, "processParameters.heatSource") === "eagar-tsai" && typeof ratio === "number" && ratio <= 1;
    }
    default: return false; // a condition outside the closed list never selects a variant
  }
}

/** Substitute placeholders; returns null when any value is missing, so the caller falls back to the plain sentence. */
function substitute(template: string, ctx: DifferenceContext): string | null {
  let failed = false;
  const text = template.replace(/\{(served|research):([^}]+)\}|\{servedKernel\}/g, (match, source?: string, path?: string) => {
    if (match === "{servedKernel}") {
      const kernel = getPath(ctx.served, "processParameters.heatSource");
      if (typeof kernel === "string") return kernel;
      failed = true; return match;
    }
    if (source === "served") {
      const v = getPath(ctx.served, path ?? "");
      if (v === null) return "unavailable";
      const shown = formatScalar(v, servedUnit(path ?? ""));
      if (shown === null) { failed = true; return match; }
      return shown;
    }
    const leaf = researchField(ctx.block, path ?? "");
    if (!leaf) { failed = true; return match; }
    if (leaf.value === null) return "unavailable";
    const shown = formatScalar(leaf.value, leaf.unit);
    if (shown === null) { failed = true; return match; }
    return shown;
  });
  return failed ? null : text;
}

/** One statement: the first variant whose conditions hold with the served numbers filled in, else the fallback. */
export function renderServedDifference(diff: ResearchServedDifference, ctx: DifferenceContext): string {
  if (!ctx.servedMatches || ctx.served === null || ctx.served === undefined) return diff.fallback;
  for (const variant of diff.variants) {
    if (variant.when.every((c) => conditionHolds(c, diff, ctx))) {
      return substitute(variant.template, ctx) ?? diff.fallback;
    }
  }
  return diff.fallback;
}

// ---------------------------------------------------------------------------------------------------------------
// Texts read from the response

export function primarySentence(container: ResearchModuleContainer): string | null {
  const notes = container.consistencyNote?.armNotes ?? [];
  const nominal = notes.find((n) => n.armId === "nominal") ?? notes[0];
  const value = nominal?.note?.sentence?.value;
  return typeof value === "string" && value.length > 0 ? value : null;
}
