import React from "react";
import { describeLpbfDefault, type LpbfSpecimenState } from "../store/useMaterialSpecimenStore";

/**
 * Discloses LPBF inputs that are unsourced defaults or class heuristics (see LpbfSpecimenState.defaultsApplied), each
 * with the value in use. Compact by default: a one-line notice with a "show which" disclosure holding the full,
 * unchanged line. Renders nothing when no field is flagged.
 */
export function LpbfDefaultsNote({ lpbf, className }: { lpbf: LpbfSpecimenState; className?: string }) {
  const flagged = lpbf.defaultsApplied ?? [];
  if (!flagged.length) return null;
  return (
    <span role="note" data-testid="lpbf-defaults-applied" className={className ?? "text-amber-300"}>
      Unsourced defaults in use ({flagged.length}){" "}
      <details className="inline">
        <summary className="inline cursor-pointer underline underline-offset-2">show which</summary>
        <span className="block">Unsourced defaults or class heuristics in use: {flagged.map(key => describeLpbfDefault(key, lpbf)).join("; ")}</span>
      </details>
    </span>
  );
}
