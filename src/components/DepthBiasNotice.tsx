import React from "react";
import { resolveDepthBiasWarning, type DepthBiasWarning } from "../utils/depthBiasWarning";

/**
 * Plain note next to the served melt-pool depth and regime label: the alloy note from the solver and the depth-bias
 * warning. Reporting only, screening, not validation. Renders nothing when neither applies.
 */
export const DepthBiasNotice: React.FC<{
  geometry: { regime?: string; regimeMaterialNote?: string; depthBiasWarning?: DepthBiasWarning } | null | undefined;
  material?: string | { name?: string } | null;
  /** Heat-source kernel actually served (rosenthal, eagar-tsai or goldak); the note depends on it. */
  heatSource?: string | null;
  /** Normalized enthalpy index dH/hs (processParameters.normalizedEnthalpy); the band class comes from it. */
  enthalpy?: number | null;
  className?: string;
}> = ({ geometry, material, heatSource, enthalpy, className }) => {
  const warning = resolveDepthBiasWarning(geometry, material, heatSource, enthalpy);
  const note = geometry?.regimeMaterialNote;
  if (!warning.text && !note) return null;
  return (
    <div
      className={`rounded border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[10px] text-amber-200 ${className ?? ""}`}
      data-depth-bias={warning.direction ?? "none"}
    >
      {note ? <span className="block" data-regime-material-note="true">Alloy note: {note}.</span> : null}
      {warning.text ? <span className="block">{warning.text}</span> : null}
      {warning.basis ? <span className="block opacity-80">Basis: {warning.basis}</span> : null}
    </div>
  );
};
