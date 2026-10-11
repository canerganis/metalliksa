// Depth-bias note for the served melt-pool depth. Reporting only: no regime threshold, depth number or verdict reads it.
// Mirror of python/lpbf_depth_bias.py (python/test_lpbf_depth_bias.py pins the table and templates equal, and the table
// equal to data/calibration/lpbf-meltpool-error-bands-v1.summary.json). Relative error there is pred / meas - 1.

export type DepthBiasDirection = "may-underestimate" | "may-overestimate" | null;

export interface DepthBiasWarning {
  direction: DepthBiasDirection;
  text: string | null;
  basis: string | null;
}

export const MIN_N_FOR_DIRECTION = 5;
export const MIN_ABS_MEDIAN_FOR_DIRECTION = 0.05;

/** Error-band class edges on the normalized enthalpy index dH/hs (summary config.thresholds): < lo conduction, < hi transition, else keyhole. */
export const DEPTH_BIAS_ENTHALPY_EDGES: readonly [number, number] = [15.0, 20.0];

export const DEPTH_BIAS_BANDS_ID = "lpbf-meltpool-error-bands-2026-10-11-38927d2295d6";

/** "alloy|kernel|regime" -> [median relative error, n tracks, n sources]. */
export const DEPTH_BIAS_CELLS: Record<string, readonly [number, number, number]> = {
  "316L Stainless Steel|eagar-tsai|conduction": [0.257, 167, 2],
  "316L Stainless Steel|eagar-tsai|keyhole": [-0.305, 442, 3],
  "316L Stainless Steel|eagar-tsai|transition": [-0.426, 122, 2],
  "Inconel 625|eagar-tsai|conduction": [0.208, 23, 2],
  "Inconel 625|eagar-tsai|keyhole": [-0.077, 1, 1],
  "Inconel 625|eagar-tsai|transition": [-0.518, 6, 1],
  "Inconel 718|eagar-tsai|keyhole": [-0.113, 7, 1],
  "Ti-6Al-4V|eagar-tsai|conduction": [0.556, 8, 1],
  "Ti-6Al-4V|eagar-tsai|keyhole": [-0.047, 80, 2],
  "Ti-6Al-4V|eagar-tsai|transition": [-0.41, 6, 1],
  "316L Stainless Steel|goldak|conduction": [0.371, 163, 2],
  "316L Stainless Steel|goldak|keyhole": [-0.305, 442, 3],
  "316L Stainless Steel|goldak|transition": [-0.385, 122, 2],
  "Inconel 625|goldak|conduction": [0.437, 17, 2],
  "Inconel 625|goldak|keyhole": [-0.013, 1, 1],
  "Inconel 625|goldak|transition": [-0.475, 6, 1],
  "Inconel 718|goldak|keyhole": [-0.113, 7, 1],
  "Ti-6Al-4V|goldak|conduction": [0.753, 8, 1],
  "Ti-6Al-4V|goldak|keyhole": [-0.047, 80, 2],
  "Ti-6Al-4V|goldak|transition": [-0.352, 6, 1],
  "316L Stainless Steel|rosenthal|conduction": [0.325, 164, 2],
  "316L Stainless Steel|rosenthal|keyhole": [-0.305, 442, 3],
  "316L Stainless Steel|rosenthal|transition": [-0.401, 122, 2],
  "Inconel 625|rosenthal|conduction": [0.413, 18, 2],
  "Inconel 625|rosenthal|keyhole": [-0.04, 1, 1],
  "Inconel 625|rosenthal|transition": [-0.492, 6, 1],
  "Inconel 718|rosenthal|keyhole": [-0.113, 7, 1],
  "Ti-6Al-4V|rosenthal|conduction": [0.68, 8, 1],
  "Ti-6Al-4V|rosenthal|keyhole": [-0.047, 80, 2],
  "Ti-6Al-4V|rosenthal|transition": [-0.372, 6, 1],
};

export const DEPTH_BIAS_DIRECTION_TEMPLATE =
  "Depth {verb} for this alloy and kernel in the {regime} band. On published single tracks the {kernel} " +
  "kernel on {alloy} {action} the depth by a median of {pct}% (n={n}, {sources} source{plural}). This is a screening " +
  "note, not a validated correction, and transfer to another machine is not established.";
export const DEPTH_BIAS_FEW_TEMPLATE =
  "Too few held-out tracks to give a direction: the {kernel} kernel on {alloy} in the {regime} band has n={n} " +
  "(median {action} the depth by {pct}%). This is a screening note, not a validated correction.";
export const DEPTH_BIAS_FLAT_TEMPLATE =
  "No clear depth bias direction: the {kernel} kernel on {alloy} in the {regime} band has a median depth error of " +
  "{pct}% (n={n}, {sources} source{plural}). This is a screening note, not a validated correction.";
export const DEPTH_BIAS_NO_CHECK_TEMPLATE =
  "No held-out check for this alloy and kernel ({kernel} on {alloy}, {regime} band), so no direction of the depth " +
  "error is given.";
export const DEPTH_BIAS_DISAGREE_TEMPLATE =
  "No depth bias direction: the served regime label ({label}) and the error-band class from the enthalpy index " +
  "({regime}, dH/hs {index}) disagree here. For context only, the {kernel} kernel on {alloy} in the {regime} band has a " +
  "median depth error of {pct}% ({action}, n={n}, {sources} source{plural}). No direction is given. This is a screening " +
  "note, not a validated correction.";
export const DEPTH_BIAS_DISAGREE_NO_CELL_TEMPLATE =
  "No depth bias direction: the served regime label ({label}) and the error-band class from the enthalpy index " +
  "({regime}, dH/hs {index}) disagree here, and there is no held-out check for {kernel} on {alloy} in the {regime} band. " +
  "No direction is given.";
/** P1 planned bump (2026-10-11): appended to UNDER texts in the transition and keyhole bands and to Rosenthal OVER texts in the conduction band. */
export const DEPTH_BIAS_P1_UNDER_NOTE =
  " After 2026-10-11 no kernel represents the measured absorptance rise, so transition and keyhole " +
  "depth is biased low in all three kernels.";
export const DEPTH_BIAS_P1_OVER_NOTE =
  " The conduction field carries no latent-heat cut since 2026-10-11, so conduction-mode depth from " +
  "the Rosenthal kernel is higher than before.";
export const DEPTH_BIAS_BASIS_TEMPLATE =
  "Error-band summary {bands_id}, cell {alloy} / {kernel_id} / {regime}: relative error pred / meas - 1, equal source " +
  "weight, digitized figures included, screening only.";
export const DEPTH_BIAS_CLASS_BASIS =
  " Band class from the enthalpy index dH/hs: conduction below {lo}, transition {lo} to {hi}, " +
  "keyhole at {hi} or above.";
export const DEPTH_BIAS_BASIS_NO_CHECK = "Error-band summary {bands_id} has no depth cell for this alloy, kernel and regime band.";

const KERNEL_LABELS: Record<string, string> = { rosenthal: "Rosenthal", "eagar-tsai": "Eagar-Tsai", goldak: "Goldak" };

function fill(template: string, fields: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_m, k: string) => String(fields[k]));
}

function alloyOf(materialName: string | null | undefined): string | null {
  const m = String(materialName ?? "").toLowerCase();
  if (m.includes("316")) return "316L Stainless Steel";
  if (m.includes("625")) return "Inconel 625";
  if (m.includes("718")) return "Inconel 718";
  if (m.includes("ti-6al-4v") || m.includes("ti64") || m.includes("6al")) return "Ti-6Al-4V";
  return null;
}

function regimeClassOf(regime: string | null | undefined): string | null {
  const r = String(regime ?? "").toLowerCase();
  for (const name of ["conduction", "transition", "keyhole"]) if (r.startsWith(name)) return name;
  return null;
}

/** Error-band class of the normalized enthalpy index; null when the index is missing or not finite. */
export function enthalpyClassOf(enthalpy: number | null | undefined): string | null {
  if (enthalpy === null || enthalpy === undefined || !Number.isFinite(Number(enthalpy))) return null;
  const e = Number(enthalpy);
  const [lo, hi] = DEPTH_BIAS_ENTHALPY_EDGES;
  return e < lo ? "conduction" : e < hi ? "transition" : "keyhole";
}

/** Conduction vs keyhole is a contradiction; adjacent classes (the IN625 label has no transition band) keep their direction. */
function labelsContradict(labelClass: string | null, indexClass: string | null): boolean {
  return (labelClass === "conduction" && indexClass === "keyhole") || (labelClass === "keyhole" && indexClass === "conduction");
}

function kernelOf(heatSource: string | null | undefined): string | null {
  const k = String(heatSource ?? "").trim().toLowerCase().replace(/_/g, "-");
  for (const name of Object.keys(KERNEL_LABELS)) if (k.startsWith(name)) return name;
  return null;
}

/**
 * The note for the alloy, the heat-source kernel actually served (rosenthal, eagar-tsai or goldak) and the band class of
 * the normalized enthalpy index (the error bands' own edges). The served regime label is used only when the index is missing.
 */
export function computeDepthBiasWarning(
  regime: string | null | undefined,
  materialName: string | null | undefined,
  heatSource: string | null | undefined,
  enthalpy?: number | null,
): DepthBiasWarning {
  const byIndex = enthalpyClassOf(enthalpy);
  const rc = byIndex ?? regimeClassOf(regime);
  const alloy = alloyOf(materialName);
  const kernel = kernelOf(heatSource);
  if (!rc || !alloy || !kernel) return { direction: null, text: null, basis: null };
  const [lo, hi] = DEPTH_BIAS_ENTHALPY_EDGES;
  const classedBy = byIndex ? fill(DEPTH_BIAS_CLASS_BASIS, { lo, hi }) : "";
  const fields: Record<string, string | number> = { regime: rc, alloy, kernel: KERNEL_LABELS[kernel] };
  const cell = DEPTH_BIAS_CELLS[`${alloy}|${kernel}|${rc}`];
  const labelClass = regimeClassOf(regime);
  if (byIndex && labelsContradict(labelClass, byIndex)) {
    Object.assign(fields, { label: labelClass as string, index: String(Number(enthalpy)) });
    const dBasis =
      (cell ? fill(DEPTH_BIAS_BASIS_TEMPLATE, { bands_id: DEPTH_BIAS_BANDS_ID, alloy, kernel_id: kernel, regime: rc }) : fill(DEPTH_BIAS_BASIS_NO_CHECK, { bands_id: DEPTH_BIAS_BANDS_ID })) + classedBy;
    if (!cell) return { direction: null, text: fill(DEPTH_BIAS_DISAGREE_NO_CELL_TEMPLATE, fields), basis: dBasis };
    const [m, cn, cs] = cell;
    Object.assign(fields, { n: cn, pct: Math.round(Math.abs(m) * 100), sources: cs, plural: cs === 1 ? "" : "s", action: m > 0 ? "overpredicted" : "underpredicted" });
    return { direction: null, text: fill(DEPTH_BIAS_DISAGREE_TEMPLATE, fields), basis: dBasis };
  }
  if (!cell) {
    return {
      direction: null,
      text: fill(DEPTH_BIAS_NO_CHECK_TEMPLATE, fields),
      basis: fill(DEPTH_BIAS_BASIS_NO_CHECK, { bands_id: DEPTH_BIAS_BANDS_ID }) + classedBy,
    };
  }
  const [median, n, nSources] = cell;
  Object.assign(fields, {
    n,
    pct: Math.round(Math.abs(median) * 100),
    sources: nSources,
    plural: nSources === 1 ? "" : "s",
    action: median > 0 ? "overpredicted" : "underpredicted",
  });
  const basis = fill(DEPTH_BIAS_BASIS_TEMPLATE, { bands_id: DEPTH_BIAS_BANDS_ID, alloy, kernel_id: kernel, regime: rc }) + classedBy;
  if (n < MIN_N_FOR_DIRECTION) return { direction: null, text: fill(DEPTH_BIAS_FEW_TEMPLATE, fields), basis };
  if (Math.abs(median) < MIN_ABS_MEDIAN_FOR_DIRECTION) return { direction: null, text: fill(DEPTH_BIAS_FLAT_TEMPLATE, fields), basis };
  const over = median > 0;
  let text = fill(DEPTH_BIAS_DIRECTION_TEMPLATE, { ...fields, verb: over ? "may be overestimated" : "may be underestimated" });
  if (!over && (rc === "transition" || rc === "keyhole")) text += DEPTH_BIAS_P1_UNDER_NOTE;
  else if (over && rc === "conduction" && kernel === "rosenthal") text += DEPTH_BIAS_P1_OVER_NOTE;
  return {
    direction: over ? "may-overestimate" : "may-underestimate",
    text,
    basis,
  };
}

/** Uses a served depthBiasWarning when the payload carries one, else derives it from the enthalpy index (regime label only when the index is missing), alloy name and served kernel. */
export function resolveDepthBiasWarning(
  geometry: { regime?: string; depthBiasWarning?: DepthBiasWarning } | null | undefined,
  material: string | { name?: string } | null | undefined,
  heatSource?: string | null,
  enthalpy?: number | null,
): DepthBiasWarning {
  if (geometry?.depthBiasWarning) return geometry.depthBiasWarning;
  const name = typeof material === "string" ? material : material?.name;
  return computeDepthBiasWarning(geometry?.regime, name, heatSource, enthalpy);
}
