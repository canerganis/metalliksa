import { checkedQuantityContainer, reasonText, sourceLabelText, type Quantity, type QuantityContainer } from "../data/quantityEnvelope";

// Wording table: pending maintainer approval (SOL-A, L6).
export const SOLIDIFICATION_WORDING = {
  transientHeading: "Transient diagnostics — unadmitted liquidus, single mesh",
  legacy: "Older solver result, recompute",
  alternatives: { hunt: "Hunt", kurzFisher: "Kurz-Fisher" } as Readonly<Record<string, string>>,
} as const;
export const FRONT_LABELS: Readonly<Record<string, string>> = {
  thermalGradient: "Thermal gradient", normalSpeed: "Solidification rate", coolingRate: "Cooling rate",
  gOverR: "G/R", pdas: "PDAS", sdas: "SDAS", morphology: "Morphology",
  solidStateTransformation: "Phase note",
};
export function quantityReason(q: Quantity): string {
  return q.reasons.map(r => reasonText(r.code, r.params)).join(" ");
}
export function quantityText(q: Quantity): string {
  if (q.value === null) return quantityReason(q);
  const value = typeof q.value === "number" ? q.value.toExponential(3) : typeof q.value === "string" ? q.value
    : Object.entries(q.value).map(([name, v]) => `${SOLIDIFICATION_WORDING.alternatives[name] ?? name}: ${(v * (q.unit === "m" ? 1e6 : 1)).toFixed(3)}`).join("; ");
  const unit = typeof q.value === "object" && q.unit === "m" ? "µm" : q.unit;
  const label = q.sourceEvidenceKind ? sourceLabelText(q.sourceEvidenceKind, q.weakestInputs) : "";
  return `${value} ${unit}${label ? ` · ${label}` : ""}`;
}
export function checkedFront(raw: unknown): QuantityContainer {
  const container = checkedQuantityContainer(raw);
  const legacyKeys = ["G_K_m", "R_m_s", "thermalGradient_G_K_m", "solidificationRate_R_m_s", "coolingRate_K_s", "pdasBand_um", "morphologyBands_G_over_R", "median", "bottom", "tail"];
  for (const key of legacyKeys) if (Object.hasOwn(container, key)) throw new Error(`Retired front key ${key}`);
  for (const name of Object.keys(FRONT_LABELS)) if (!container.quantities[name]) throw new Error(`Missing front quantity ${name}`);
  return container;
}

export const TRANSIENT_FRONT_METRICS = new Set(["thermalGradient_K_m", "solidificationRate_m_s", "coolingRate_K_s"]);
