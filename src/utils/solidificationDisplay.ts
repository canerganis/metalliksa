import { checkedQuantityContainer, reasonText, sourceLabelText, type Quantity, type QuantityContainer } from "../data/quantityEnvelope";

// Wording table: pending maintainer approval (SOL-A, L6).
export const SOLIDIFICATION_WORDING = {
  transientHeading: "Transient diagnostics · selected liquidus convention · single mesh",
  legacy: "Older solver result, recompute",
  alternatives: { hunt: "Hunt", kurzFisher: "Kurz-Fisher" } as Readonly<Record<string, string>>,
} as const;
export const FRONT_LABELS: Readonly<Record<string, string>> = {
  thermalGradient: "Thermal gradient", normalSpeed: "Solidification rate", coolingRate: "Cooling rate",
  gOverR: "G/R", pdas: "PDAS", sdas: "SDAS", morphology: "Morphology",
  solidStateTransformation: "Phase note",
};
// SOL-T head containers carry this gate while local front values are served on the SOL-C estimate channel only.
export const SOL_C_CHANNEL_GATE = "sol-c-local-samples-not-installed";
export const SOL_C_CHANNEL_TEXT = "Front estimates are computed on request on the solidification estimate channel (Solidification atlas).";
/** Reason sentences of one quantity, each sentence once (several null parents share one sentence). */
export function quantityReason(q: Quantity): string {
  const sentences = q.reasons.map(r => r.params?.gate === SOL_C_CHANNEL_GATE ? SOL_C_CHANNEL_TEXT : reasonText(r.code, r.params));
  return [...new Set(sentences)].join(" ");
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

export function quantityScopes(container: QuantityContainer, quantity: Quantity): string[] {
  return [...new Set(quantity.dependsOn.flatMap(name => {
    const input = container.inputProvenance?.[name];
    return input?.scope ? [input.scope] : [];
  }))];
}

export function quantityContainerCsv(container: QuantityContainer): string {
  const cell = (value: unknown) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const rows: unknown[][] = [["quantity", "status", "value", "unit", "sourceEvidenceKind", "labelSources", "scope", "parentIdentity"]];
  for (const [name, quantity] of Object.entries(container.quantities)) rows.push([
    name, quantity.status, typeof quantity.value === "object" && quantity.value !== null ? JSON.stringify(quantity.value) : quantity.value,
    quantity.unit, quantity.sourceEvidenceKind, quantity.labelSources.join("; "),
    quantityScopes(container, quantity).join("; "), quantity.identity.parent,
  ]);
  return rows.map(row => row.map(cell).join(",")).join("\r\n") + "\r\n";
}
