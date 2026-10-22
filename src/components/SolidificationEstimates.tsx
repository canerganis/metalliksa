import React, { useId, useState } from "react";
import { QUANTITY_ENVELOPE } from "../generated/quantityEnvelope";
import { checkedSolidificationEstimates, estimateLine, type SolidificationEstimates as EstimatePayload } from "../utils/solidificationEstimateDisplay";

const ORDER = ["thermalGradient", "normalSpeed", "coolingRate", "gOverR", "pdas", "sdas", "planarStabilityIndex",
  "equiaxedEnvelopeFraction", "cetClass", "kmAlphaMFraction", "equilibriumPhaseInventory", "scheilMicroconstituents", "phaseInventory"];
const SURROGATE_NOTE = "Conduction-field surrogate: the temperature field does not include the keyhole cavity.";
const DOMAIN_PREFIXES = ["Outside the model's stated domain", "Alloy or family transfer"];

function orderedNames(payload: EstimatePayload): string[] {
  const names = Object.keys(payload.quantities);
  return [...ORDER.filter(n => names.includes(n)), ...names.filter(n => !ORDER.includes(n))];
}

function warningLine(w: string) {
  return <>{DOMAIN_PREFIXES.some(p => w.startsWith(p)) ? <strong className="mr-1">Out of domain:</strong> : null}{w}</>;
}

/** Label of every "rest of the warnings" disclosure: the first warning stays visible, the rest are N more notes. */
export function moreNotesLabel(count: number): string { return `${count} more note${count === 1 ? "" : "s"}`; }

/** Plain list form of the same fold, for result lists rendered as bullets: first warning visible, the rest under a native disclosure. */
export function WarningNotes({ warnings, className }: { warnings: readonly string[]; className?: string }) {
  if (!warnings.length) return null;
  const rest = warnings.slice(1);
  return <div className={className} data-warning-notes>
    <p data-warning-note>{warnings[0]}</p>
    {rest.length > 0 && <details className="mt-1"><summary className="cursor-pointer text-cyan-200 underline">{moreNotesLabel(rest.length)}</summary><ul className="mt-1 list-disc space-y-1 pl-5">{rest.map(w => <li key={w} data-warning-note>{w}</li>)}</ul></details>}
  </div>;
}

/** First warning visible; the rest folded under an accessible "More" disclosure (native button, keyboard operable). */
export function EstimateWarnings({ warnings, initiallyOpen = false }: { warnings: readonly string[]; initiallyOpen?: boolean }) {
  const [open, setOpen] = useState(initiallyOpen);
  const id = useId();
  if (!warnings.length) return null;
  const rest = warnings.slice(1);
  return <dd className="break-words text-amber-200" data-estimate-warnings>
    <span className="block" data-estimate-warning>{warningLine(warnings[0])}</span>
    {rest.length > 0 && <>
      <button type="button" className="mt-1 text-[11px] text-cyan-200 underline focus:outline-none focus:ring-2 focus:ring-cyan-300/40"
        aria-expanded={open} aria-controls={id} onClick={() => setOpen(value => !value)} data-estimate-warnings-toggle>
        {open ? "Less" : moreNotesLabel(rest.length)}
      </button>
      <span id={id} hidden={!open} className="block" data-estimate-warnings-more>
        {rest.map(w => <span key={w} className="block" data-estimate-warning>{warningLine(w)}</span>)}
      </span>
    </>}
  </dd>;
}

export function SolidificationEstimates({ payload }: { payload: unknown }) {
  let parsed: EstimatePayload;
  try {
    parsed = checkedSolidificationEstimates(payload);
  } catch (e) {
    return <p role="status" className="text-xs text-slate-300">Estimate payload rejected: {e instanceof Error ? e.message : String(e)}</p>;
  }
  const lines = orderedNames(parsed).map(name => estimateLine(name, parsed.quantities[name]));
  return <div data-solidification-estimates>
    <p className="text-xs text-slate-400">{QUANTITY_ENVELOPE.containerHeaderText[parsed.moduleEvidenceCeiling]} · {parsed.moduleMaturity}</p>
    {parsed.surrogate && <p className="mt-1 text-xs text-amber-200" data-estimate-surrogate>{SURROGATE_NOTE}</p>}
    <dl className="mt-2 grid gap-2 text-xs">
      {lines.map(line => <div key={line.name} data-quantity={line.name} className="border-b border-slate-700/50 py-2">
        <dt className="flex flex-wrap items-center gap-2 text-slate-400">
          <span>{line.label}</span>
          <span data-estimate-tier={line.tier} className="rounded border border-slate-500/50 px-1.5 py-0.5 text-[10px] text-slate-200">{line.tierLabel}</span>
        </dt>
        {line.value !== null && <dd className="break-words text-slate-200">{line.value}</dd>}
        {line.rangeKind && line.range && <dd className="break-words text-slate-300" data-estimate-range={line.rangeKind}>
          {line.rangeKind === "auxiliary" && <span className="block text-slate-400">Auxiliary input sensitivity range (not an error bar)</span>}
          <span className="block">{line.range}</span>
          {line.rangeInputs && <span className="block text-slate-400">Varied inputs: {line.rangeInputs}</span>}
        </dd>}
        <EstimateWarnings warnings={line.warnings} />
        {line.text && <dd className="break-words text-slate-300">{line.text}</dd>}
        {line.sourceLabel && <dd className="break-words text-slate-400">{line.sourceLabel}</dd>}
      </div>)}
    </dl>
    {parsed.phaseContext && <section className="mt-3" aria-label="Literature context">
      <h3 className="text-xs font-semibold text-slate-300">Literature context</h3>
      <p className="break-words text-xs text-slate-300">{parsed.phaseContext.text}</p>
      <p className="break-words text-[11px] text-slate-500">{parsed.phaseContext.locator}</p>
    </section>}
  </div>;
}
