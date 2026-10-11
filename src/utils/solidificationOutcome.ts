import type {
  SolidificationMicrostructureAvailable,
  SolidificationMicrostructureResult,
} from '../services/pythonComputationService';

export type SolidificationOutcome =
  | { error: string; degenerate?: true }
  | { result: SolidificationMicrostructureAvailable };

/**
 * Guard for the Microstructure Lab: only a Python result with status "available" or "screening-fallback" may
 * reach the numeric panels. "unavailable" yields Python's reason; "degenerate-floor" (R/cooling are solver
 * clamp floors) also yields Python's reason, flagged `degenerate`, and its copied numbers are never rendered
 * as results; a legacy block without a status (an old worker) is never rendered as available, and a numeric
 * block that lacks finite G/R/cooling is rejected. PDAS and SDAS are null since P7a (the sourced Ni-Nb band is
 * pdasBand_um); a non-null PDAS/SDAS must still be finite.
 */
export function solidificationOutcome(res: SolidificationMicrostructureResult | null | undefined): SolidificationOutcome {
  const status = (res as { status?: unknown } | null | undefined)?.status;
  if (status === 'unavailable') {
    return { error: (res as { reason?: string }).reason || 'no solidification data' };
  }
  if (status === 'degenerate-floor') {
    return { error: (res as { reason?: string }).reason || 'solidification front degenerate: floor-clamped R/cooling', degenerate: true };
  }
  if (status !== 'available' && status !== 'screening-fallback') {
    return { error: 'legacy result without status' };
  }
  const r = res as SolidificationMicrostructureAvailable;
  for (const value of [r.G_K_m, r.R_m_s, r.coolingRate_K_s]) {
    if (typeof value !== 'number' || !Number.isFinite(value)) return { error: 'result carries no finite G/R/cooling numbers' };
  }
  for (const value of [r.PDAS_um, r.SDAS_um]) {
    if (value !== null && value !== undefined && (typeof value !== 'number' || !Number.isFinite(value))) {
      return { error: 'result carries a non-finite PDAS/SDAS number' };
    }
  }
  return { result: r };
}
