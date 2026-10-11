// Wave B D1/D10, P6 containment (2026-10-11): how the served melt-pool peak temperature is labelled and how far colour
// scales may use it.
import type { PythonLPBFResult } from "../services/pythonComputationService";

/**
 * Top of the melt-pool colour scale (Wave B D10, P6). Since the P6 containment bump the served peak is the loss-free
 * Eagar-Tsai surface maximum and is null wherever it is at or above the sourced vapour temperature or no sourced value
 * exists (Inconel 718, AlSi10Mg and every other alloy). The colour scale therefore needs a DISPLAY CAP that is not a
 * temperature claim: max(sourced vapour temperature when the result carries one, else FALLBACK_VAPOR_CAP_C, 1.5 * liquidus).
 * A served peak below that cap is used as the scale top; a null peak, or a peak above the cap, uses the cap. Older
 * payloads (a numeric peak with surfaceTemperature_C = min(peak, T_vap)) take the same path through their numeric peak.
 * FALLBACK_VAPOR_CAP_C is a display-only bound above the normal boiling point of every alloy base the app models
 * (Ti about 3287 C is the highest). Wherever the cap is printed it must be labelled as a display cap (DISPLAY_CAP_LABEL).
 */
export const FALLBACK_VAPOR_CAP_C = 3500;
export const DISPLAY_CAP_LABEL = "display cap, not a temperature claim";

type HydroLike = Pick<PythonLPBFResult, "hydrodynamicsAndRecoil">;

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/** The display cap alone (no served temperature enters it). */
export function colourScaleDisplayCap_C(result: HydroLike, liquidus_C: number): number {
  const h = result.hydrodynamicsAndRecoil;
  const sourcedTv = finite(h.vaporTemperatureSourced_C) ? h.vaporTemperatureSourced_C : null;
  const legacySurface = sourcedTv === null && finite(h.surfaceTemperature_C) ? h.surfaceTemperature_C : null;
  const vaporCap = sourcedTv ?? legacySurface ?? FALLBACK_VAPOR_CAP_C;
  return Math.max(vaporCap, 1.5 * liquidus_C);
}

/** Scale top: the served peak when it is a number below the display cap, else the display cap. */
export function colourScalePeak_C(result: HydroLike, liquidus_C: number): number {
  const cap = colourScaleDisplayCap_C(result, liquidus_C);
  const peak = result.hydrodynamicsAndRecoil.peakTemperature_C;
  return finite(peak) ? Math.min(peak, cap) : cap;
}

/** true when the scale top is the display cap rather than a served temperature. */
export function colourScaleIsDisplayCap(result: HydroLike, liquidus_C: number): boolean {
  const peak = result.hydrodynamicsAndRecoil.peakTemperature_C;
  return !finite(peak) || peak > colourScaleDisplayCap_C(result, liquidus_C);
}

/** Short text for the peak-temperature basis (Wave B D1, P6); null for older results without the label. */
export function peakTemperatureBasisLabel(result: HydroLike): string | null {
  switch (result.hydrodynamicsAndRecoil.peakTemperatureBasis) {
    case "eagar-tsai-loss-free-surface-maximum":
      return "loss-free Eagar-Tsai surface maximum, served only below the sourced vapour temperature";
    case "regularised-singular-source-value":
      return "regularised point-source centre value, not a wall temperature";
    case "distributed-source-conduction-centre-value":
      return "uncapped conduction-field centre value, not a wall temperature";
    default:
      return null;
  }
}

/** "1234.5 °C" for a served number, else "n/a" (with the served reason appended when given). */
export function servedTemperatureText(value: number | null | undefined, reason?: string | null): string {
  if (finite(value)) return `${value} °C`;
  return reason ? `n/a (${reason})` : "n/a";
}
