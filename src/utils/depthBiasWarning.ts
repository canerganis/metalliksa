// Depth-bias note for the served melt-pool depth. Reporting only: no regime threshold, depth number or verdict reads it.
// Mirror of python/lpbf_depth_bias.py (python/test_lpbf_depth_bias.py pins the texts equal).

export type DepthBiasDirection = "likely-underestimated" | "may-overestimate" | null;

export interface DepthBiasWarning {
  direction: DepthBiasDirection;
  text: string | null;
  basis: string | null;
}

export const DEPTH_BIAS_UNDER_TEXT =
  "Depth is likely underestimated. The served depth is a conduction isotherm depth plus an uncited keyhole increment. On IN625 single tracks in the " +
  "Transition band by this label (Lane et al. CBM tracks, 150 W at 400 mm/s and 195 W at 800 mm/s, beam about " +
  "100 um, enthalpy index 19.45 and 17.88) the observed depth to half-width ratio was 1.4 to 1.8 and the served " +
  "depth was about 0.7 to 0.85 times the observed depth. This is a screening note from a small held-out check, not a validated correction.";
export const DEPTH_BIAS_UNDER_BASIS =
  "Held-out IN625 check, Lane et al. CBM tracks (n=2); research notes RESULTS_lane_ab_latent_check_2026-10-10 " +
  "and RESULTS_ke_width_n3_2026-10-10. Alloys other than IN625 have no such check.";
export const DEPTH_BIAS_OVER_TEXT =
  "Depth may be overestimated. In our held-out checks, conduction depth estimates overpredicted conduction-mode " +
  "IN625 tracks (AMMT, beam 170 um, enthalpy index about 7.4 to 8.1) by about 1.25 to 1.3 times for the served depth. This is a screening note " +
  "from a small check, not a validated correction.";
export const DEPTH_BIAS_OVER_BASIS =
  "Held-out IN625 check, AMMT tracks; research notes RESULTS_ke_width_n3_2026-10-10 and " +
  "SOURCES_ke_scaling_2026-10-10.";

export function computeDepthBiasWarning(regime: string | null | undefined, materialName: string | null | undefined): DepthBiasWarning {
  const r = String(regime ?? "").toLowerCase();
  const isIn625 = String(materialName ?? "").toLowerCase().includes("625");
  if (r.startsWith("transition") || r.startsWith("keyhole")) {
    return { direction: "likely-underestimated", text: DEPTH_BIAS_UNDER_TEXT, basis: DEPTH_BIAS_UNDER_BASIS };
  }
  if (r.startsWith("conduction") && isIn625) {
    return { direction: "may-overestimate", text: DEPTH_BIAS_OVER_TEXT, basis: DEPTH_BIAS_OVER_BASIS };
  }
  return { direction: null, text: null, basis: null };
}

/** Uses a served depthBiasWarning when the payload carries one, else derives it from the regime label and alloy name. */
export function resolveDepthBiasWarning(
  geometry: { regime?: string; depthBiasWarning?: DepthBiasWarning } | null | undefined,
  material: string | { name?: string } | null | undefined,
): DepthBiasWarning {
  if (geometry?.depthBiasWarning) return geometry.depthBiasWarning;
  const name = typeof material === "string" ? material : material?.name;
  return computeDepthBiasWarning(geometry?.regime, name);
}
