/**
 * Residual stress and distortion in defectDiagnostics (python/lpbf_thermal_solver.py) are UNAVAILABLE since P7a
 * (2026-10-11, G1 audit B08/B09): the former heuristic sigma_eff = 0.72 E alpha dT / (1 - nu) and the index
 * sigma_eff (layer / 40 um) / 420 MPa used fixed unsourced constants and are not served (null with a reason).
 * Mercelis and Kruth 2006 (Rapid Prototyping J. 12, 254) Sec. 2 supports a cap at the yield strength only, and the
 * authority yield values are unsourced. These texts label the null; nothing is computed in TypeScript.
 */
export const STRESS_UNAVAILABLE_NOTE =
  "Unavailable: no sourced stress model (Mercelis and Kruth 2006 supports a yield cap only, and the yield values are " +
  "unsourced). The former 0.72 · E·α·ΔT / (1 − ν) proxy and the (layer / 40 µm) / 420 MPa distortion index used " +
  "unsourced constants and are no longer served (P7a, 2026-10-11).";

/** Kept under its former name for the labs that import it; it now states that the values are unavailable. */
export const DISTORTION_HEURISTIC_NOTE = STRESS_UNAVAILABLE_NOTE;

/** "n/a" with the solver's reason for a null stress or distortion value. */
export function stressValueText(value: number | null | undefined, reason?: string | null): string {
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return reason ? `n/a (${reason})` : "n/a (unavailable)";
}
