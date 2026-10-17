/**
 * Display rules for the SOL-C solidification estimate channel (quantity envelope v2).
 *
 * Python (python/lpbf_solidification_estimates.py) is the only authority for every number and sentence; this file
 * formats what the payload already states. Precision follows validity.displaySignificantDigits (two for thermal
 * kinematics and spacing, one for chi, fractions and CET); a small nonzero value is shown in scientific notation and
 * never rounded to zero. Tier labels are the maintainer's: "Estimated" with an input sensitivity range, and
 * "Uncalibrated estimate" with the unknown-uncertainty sentence. The range is never called an error bar.
 */
import { QUANTITY_ENVELOPE } from "../generated/quantityEnvelope";
import { checkedEstimateContainer, reasonText, sourceLabelText, type EstimateContainer, type EstimateQuantity, type EstimateRange } from "../data/quantityEnvelope";

const V2 = QUANTITY_ENVELOPE.estimates;

// Wording table: labels pending maintainer approval, except the tier labels (maintainer decision 2026-10-16).
export const ESTIMATE_LABELS: Readonly<Record<string, string>> = {
  thermalGradient: "Thermal gradient G", normalSpeed: "Solidification rate R", coolingRate: "Cooling rate",
  gOverR: "G/R", pdas: "Primary dendrite arm spacing", sdas: "Secondary dendrite arm scale",
  planarStabilityIndex: "Planar stability index", equiaxedEnvelopeFraction: "Equiaxed grain-envelope fraction",
  cetClass: "Grain model class (CET)", kmAlphaMFraction: "Alpha martensite or massive alpha",
  equilibriumPhaseInventory: "Terminal equilibrium phases", scheilMicroconstituents: "Scheil microconstituents",
  phaseInventory: "Phase inventory",
  pathCoolingRate: "Average cooling rate on the selected path",
  tiMartensiteDissolution: "Dissolved martensite in an isothermal hold",
  phaseTransformation: "Solid-state phase transformation",
  fatigueThreshold: "Murakami threshold stress amplitude (R = -1)",
  gumbelLargest: "Largest defect in target volume (Gumbel)",
  barStress: "Constrained-bar axial stress (scenario)",
  tipDeflection: "Released-cantilever tip deflection (scenario)",
  tipDeflectionOverThickness: "Tip deflection divided by thickness",
};
export const MEMBER_LABELS: Readonly<Record<string, string>> = {
  hunt: "Hunt", kurzFisher: "Kurz-Fisher", alphaAl: "alpha-Al", Si: "Si", Mg2Si: "Mg2Si",
  primaryAlphaAl: "primary alpha-Al", eutecticConstituent: "Al+Si eutectic",
};
export const RANGE_NAME = V2.inputSensitivityRangeName;

/** Display unit and scale: lengths in micrometres, stresses (Pa) in MPa, every other quantity in its SI unit. */
function displayUnit(q: EstimateQuantity): { unit: string; scale: number } {
  if (q.unit === "m" && q.quantityDefinition === "released-cantilever-tip-deflection") return { unit: "mm", scale: 1e3 };
  if (q.unit === "m") return { unit: "µm", scale: 1e6 };
  if (q.unit === "Pa") return { unit: "MPa", scale: 1e-6 };
  return { unit: q.unit === "1" ? "" : q.unit.replace("K*s/m^2", "K·s/m²"), scale: 1 };
}

/** A number at the stated significant digits; small nonzero values in scientific notation, never rounded to 0. */
export function formatSignificant(value: number, digits: number): string {
  if (!Number.isFinite(value)) throw new Error("nonfinite estimate value");
  if (value === 0) return "0";
  const magnitude = Math.abs(value);
  if (magnitude < 1e-2 || magnitude >= 1e5) return value.toExponential(Math.max(0, digits - 1));
  return Number(value.toPrecision(digits)).toString();
}

function formatScaled(value: number, q: EstimateQuantity): string {
  const digits = q.validity.displaySignificantDigits ?? 2;
  return formatSignificant(value * displayUnit(q).scale, digits);
}

/** The value with its display precision and unit ("about" for maps), or null for a no-value quantity. */
export function estimateValueText(q: EstimateQuantity): string | null {
  if (q.value === null) return null;
  const { unit } = displayUnit(q);
  const suffix = unit ? ` ${unit}` : "";
  if (typeof q.value === "number") return `${formatScaled(q.value, q)}${suffix}`;
  if (typeof q.value === "string") return q.value;
  return Object.entries(q.value).map(([name, v]) => `${MEMBER_LABELS[name] ?? name} ${formatScaled(v, q)}${suffix}`).join("; ");
}

/** "input sensitivity range: a to b unit" for a range record (estimateBand or the auxiliary inputSensitivity). */
export function rangeText(range: EstimateRange, q: EstimateQuantity): string {
  const { unit } = displayUnit(q);
  const suffix = unit ? ` ${unit}` : "";
  if (typeof range.lower === "number" && typeof range.upper === "number") {
    return `${RANGE_NAME}: ${formatScaled(range.lower, q)} to ${formatScaled(range.upper, q)}${suffix}`;
  }
  const lower = range.lower as Readonly<Record<string, number>>, upper = range.upper as Readonly<Record<string, number>>;
  return `${RANGE_NAME}: ` + Object.keys(lower).map(name => `${MEMBER_LABELS[name] ?? name} ${formatScaled(lower[name], q)} to ${formatScaled(upper[name], q)}${suffix}`).join("; ");
}

/** The varied inputs of a range, with their actual dimensional endpoints. */
export function inputRangesText(range: EstimateRange): string {
  return range.inputRanges.map(row => `${row.name} ${formatSignificant(row.lower, 3)} to ${formatSignificant(row.upper, 3)} ${row.unit}`).join("; ");
}

export interface EstimateLine {
  readonly name: string;
  readonly label: string;
  readonly tier: string;
  readonly tierLabel: string;
  readonly value: string | null;
  readonly range: string | null;
  readonly rangeKind: "estimate" | "auxiliary" | null;
  readonly rangeInputs: string | null;
  readonly warnings: readonly string[];
  readonly text: string;
  readonly sourceLabel: string | null;
  readonly reasons: string;
}

/** Everything the panel shows for one quantity; each warning and reason sentence appears once. */
export function estimateLine(name: string, q: EstimateQuantity): EstimateLine {
  const v = q.validity;
  const band = v.estimateBand ?? v.inputSensitivity;
  const warnings = [...new Set(v.domainWarnings.map(w => `${V2.warningLabels[w.code]}: ${w.detail}`))];
  const reasons = [...new Set(q.reasons.map(r => reasonText(r.code, r.params)))].join(" ");
  return {
    name,
    label: ESTIMATE_LABELS[name] ?? name,
    tier: v.estimateTier,
    tierLabel: V2.tierLabels[v.estimateTier],
    value: estimateValueText(q),
    range: band ? rangeText(band, q) : null,
    rangeKind: v.estimateBand ? "estimate" : v.inputSensitivity ? "auxiliary" : null,
    rangeInputs: band ? inputRangesText(band) : null,
    warnings,
    text: q.value === null ? (v.noValueText ?? reasons) : (v.explanation ?? ""),
    sourceLabel: q.sourceEvidenceKind ? sourceLabelText(q.sourceEvidenceKind, q.weakestInputs) : null,
    reasons,
  };
}

export interface SolidificationEstimates extends EstimateContainer {
  readonly schema: "lpbf-solidification-estimates-1";
  readonly channelId: string;
  readonly status: "computed" | "partial" | "unavailable";
  readonly alloyId: string | null;
  readonly surrogate?: string | null;
  readonly phaseContext?: { readonly text: string; readonly locator: string };
  readonly refusal?: { readonly code: string; readonly detail: string };
}

/** Strict parse of one channel response: schema, channel identity and the v2 envelope rules. */
export function checkedSolidificationEstimates(raw: unknown): SolidificationEstimates {
  const container = checkedEstimateContainer(raw);
  const body = container as unknown as Record<string, unknown>;
  if (body.schema !== "lpbf-solidification-estimates-1") throw new Error(`Unexpected estimate schema ${String(body.schema)}`);
  if (body.channelId !== "sol-c-solidification-estimates") throw new Error("Unexpected estimate channel identity");
  if (!["computed", "partial", "unavailable"].includes(String(body.status))) throw new Error("Unexpected estimate status");
  return container as SolidificationEstimates;
}
