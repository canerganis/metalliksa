import { availableProperty } from "./compositionPropertyAvailability";

/** Screening ratio the decision lab compares the stress proxy against: 0.7 x Rp0.2. Not an acceptance criterion. */
export const STRESS_PROXY_YIELD_FRACTION = 0.7;

export type StressProxyYieldCheck =
  | { status: "unavailable"; ok: null; limit_MPa: null; hint: string }
  | { status: "below" | "at-or-above"; ok: boolean; limit_MPa: number; hint: string };

/**
 * Compares the Python stress proxy with 0.7 x Rp0.2 only when a real yield strength is supplied. The shared specimen
 * carries none (the composition heuristic was removed), so with its value this reports "unavailable": no pass/fail.
 */
export function stressProxyYieldCheck(stressProxy_MPa: number, yieldStrength_MPa: number | null | undefined): StressProxyYieldCheck {
  const yieldMpa = availableProperty(yieldStrength_MPa);
  if (yieldMpa === null || !Number.isFinite(stressProxy_MPa)) {
    return {
      status: "unavailable",
      ok: null,
      limit_MPa: null,
      hint: "No pass/fail: Rp0.2 unavailable (not computed from composition)",
    };
  }
  const limit_MPa = Math.round(yieldMpa * STRESS_PROXY_YIELD_FRACTION);
  const ok = stressProxy_MPa < yieldMpa * STRESS_PROXY_YIELD_FRACTION;
  return { status: ok ? "below" : "at-or-above", ok, limit_MPa, hint: `< 0.7 Rp0.2 (${limit_MPa})` };
}

export const STRESS_PROXY_LABEL = "Thermal-strain proxy (heuristic, elastic; not a stress)";
export const STRESS_PROXY_UNIT_NOTE = "MPa-equivalent of an elastic thermal-strain estimate, not a resolved stress";
export const STRESS_PROXY_EXCEEDS_YIELD_NOTE = "Exceeds yield; elastic estimate not physical as a stress";

/**
 * Plain presentation of the stress proxy. The value is an elastic thermal-strain estimate (no plastic relaxation), so
 * it is shown as an MPa-equivalent index. When a real yield strength is supplied and the proxy is above it, the text
 * says that the elastic estimate is not physical as a stress. Reporting only; no gate reads it.
 */
export function stressProxyPresentation(stressProxy_MPa: number, yieldStrength_MPa: number | null | undefined) {
  const check = stressProxyYieldCheck(stressProxy_MPa, yieldStrength_MPa);
  const yieldMpa = availableProperty(yieldStrength_MPa);
  const exceedsYield = yieldMpa !== null && Number.isFinite(stressProxy_MPa) && stressProxy_MPa > yieldMpa;
  const hint = exceedsYield
    ? `${STRESS_PROXY_EXCEEDS_YIELD_NOTE} (proxy ${(stressProxy_MPa / yieldMpa).toFixed(1)} x Rp0.2 of ${Math.round(yieldMpa)} MPa)`
    : check.hint;
  return { check, exceedsYield, label: STRESS_PROXY_LABEL, unitNote: STRESS_PROXY_UNIT_NOTE, hint };
}
