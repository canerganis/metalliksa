import { HowCalculated } from "../HowCalculated";
import React from "react";
import type { SimulationResult } from "../../services/lpbfSimulationService";
import { SIMULATION_MODES, simulationModeLimitations } from "../../data/simulationModes";
import { staleValueClass } from "./LpbfResultPresentation";
import { THIN_SPACE, formatWithUnit } from "../../utils/numberFormat";

/** Plain summary at the top of the Melt Pool Analysis stage. Every value, label and sentence comes from the result object and the existing mode scope text. */
export function MeltPoolSummaryCard({ result, stale = false }: { result: SimulationResult; stale?: boolean }) {
  const mode = SIMULATION_MODES.find(m => m.id === result.effectiveMode);
  const rows = [["Length", result.metrics.length_um], ["Width", result.metrics.width_um], ["Depth", result.metrics.depth_um]] as const;
  const regime = typeof result.regime === "string" && result.regime.trim() ? result.regime : null;
  return <section aria-label="Melt pool result summary" data-testid="melt-pool-summary" className="rounded-xl border border-slate-600/60 bg-slate-900/50 p-4">
    <h3 className="text-sm font-medium text-slate-100">Melt pool result</h3>
    <dl className="mt-3 grid gap-4 sm:grid-cols-3">{rows.map(([label, value]) => <div key={label}>
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd className={`mt-1 text-2xl tabular-nums ${staleValueClass(stale)}`} title={typeof value === "number" && Number.isFinite(value) ? `Exact value: ${value} µm` : undefined}>
        {typeof value === "number" && Number.isFinite(value) ? formatWithUnit(value, "µm") : `—${THIN_SPACE}µm`}
      </dd>
      <dd className="mt-1 text-xs text-amber-200" data-evidence-label>{result.label}</dd>
    </div>)}</dl>
    <p className="mt-3 text-sm text-slate-200" data-testid="melt-pool-summary-model">
      Produced by {result.solver.id}{mode ? ` in ${mode.name} mode` : ""}{mode ? `, scope: ${mode.scope}` : ""}. {simulationModeLimitations(result.effectiveMode)}
    </p>
    {regime && <p className="mt-2 text-sm text-slate-200" data-testid="melt-pool-summary-regime">Regime verdict: {regime}{result.riskScope ? ` · ${result.riskScope}` : ""}</p>}
    {/* Only Quick Screening: its geometry is the Goldak field read on a fixed grid (lpbf_simulation.screening). */}
    {result.effectiveMode === "screening" && <HowCalculated explainerId="screening-job-geometry" result={result} className="mt-3" />}
  </section>;
}
