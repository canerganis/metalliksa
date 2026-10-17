import React from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid } from "recharts";
import type { AcceptedPrefix, SimulationRefusal } from "../../services/lpbfSimulationService";
import { EstimateWarnings } from "../SolidificationEstimates";

/** Significant-figure formatting for the prefix values (displaySignificantDigits comes from the payload). */
export function sig(value: number, digits: number): string {
  const rounded = Number(value.toPrecision(digits));
  return rounded !== 0 && (Math.abs(rounded) < 1e-3 || Math.abs(rounded) >= 1e6) ? rounded.toExponential(digits - 1) : String(rounded);
}

/** Partial transient temperature history shown when the run is refused at the material boiling limit. */
export function AcceptedPrefixView({ refusal }: { refusal: SimulationRefusal }) {
  const prefix: AcceptedPrefix | undefined = refusal.detail.acceptedPrefix;
  if (!prefix) return null;
  const digits = prefix.displaySignificantDigits ?? 2;
  const hasValue = prefix.points.length > 0 && prefix.noValueText === null;
  return <section aria-label="Computed interval before the refusal" data-accepted-prefix className="mt-3 space-y-3 rounded-lg border border-slate-600/50 p-4 text-sm text-slate-200">
    <p data-prefix-refusal className="text-amber-200">{refusal.message}</p>
    {hasValue ? <>
      <p><span data-estimate-tier={prefix.estimateTier} className="rounded border border-slate-500/50 px-1.5 py-0.5 text-[11px]">{prefix.tierLabel}</span></p>
      {prefix.explanation && <p data-prefix-explanation className="text-xs leading-6 text-slate-300">{prefix.explanation}</p>}
      <p className="text-xs text-slate-400">Accepted steps: {prefix.acceptedSteps}. First rejected step: {prefix.firstRejectedStep.index} ({prefix.firstRejectedStep.reasonCode}).</p>
      <div className="overflow-x-auto"><table data-prefix-points className="w-full text-left text-xs">
        <caption className="pb-1 text-left text-slate-400">{prefix.pointRule}</caption>
        <thead><tr className="text-slate-400"><th className="pr-3">Point</th><th className="pr-3">Position x, y, z (µm)</th><th className="pr-3">Temperature, {prefix.maximumLabel} (K)</th><th>Time of that value (s)</th></tr></thead>
        <tbody>{prefix.points.map(pt => <tr key={pt.id} data-prefix-point={pt.id} className="border-t border-slate-700/50">
          <td className="pr-3">{pt.id}</td>
          <td className="pr-3 tabular-nums">{pt.coordinate_m.map(c => sig(c * 1e6, digits)).join(", ")}</td>
          <td className="pr-3 tabular-nums">{sig(pt.maximumOverComputedInterval_K, digits)}</td>
          <td className="tabular-nums">{sig(pt.timeOfMaximum_s, digits)}</td></tr>)}</tbody>
      </table></div>
      <div className="flex flex-wrap gap-3" aria-label="Temperature history at each point">{prefix.points.map(pt => <figure key={pt.id} className="m-0 text-[10px] text-slate-400">
        <LineChart width={150} height={70} data={pt.history} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#334155" strokeDasharray="2 3" /><XAxis dataKey="time_s" hide /><YAxis hide domain={["auto", "auto"]} />
          <Line type="monotone" dataKey="temperature_K" stroke="#38bdf8" dot={false} strokeWidth={1.5} isAnimationActive={false} />
        </LineChart><figcaption>{pt.id}</figcaption></figure>)}</div>
      <dl><EstimateWarnings warnings={prefix.domainWarnings} /></dl>
      <p data-prefix-complete className="text-xs leading-6 text-slate-300">{prefix.completeHistoryText}</p>
    </> : <p data-prefix-no-value className="text-xs leading-6 text-slate-300">{prefix.noValueText ?? prefix.completeHistoryText}</p>}
  </section>;
}
