import type { SolidificationMicrostructureAvailable, SolidificationMicrostructureResult } from "../services/pythonComputationService";
import { checkedFront, SOLIDIFICATION_WORDING } from "./solidificationDisplay";
export type SolidificationOutcome = { error: string; degenerate?: true } | { result: SolidificationMicrostructureAvailable };
export function solidificationOutcome(res: SolidificationMicrostructureResult | null | undefined): SolidificationOutcome {
  try {
    if (res?.schema !== "lpbf-solidification-microstructure-2") return { error: SOLIDIFICATION_WORDING.legacy };
    if (!["computed", "partial", "unavailable"].includes(res.status)) return { error: SOLIDIFICATION_WORDING.legacy };
    checkedFront(res);
    return { result: res };
  } catch (error) { return { error: error instanceof Error ? error.message : SOLIDIFICATION_WORDING.legacy }; }
}
