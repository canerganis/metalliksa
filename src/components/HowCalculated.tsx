import { displayUnit, formatWithUnit } from "../utils/numberFormat";
import React, { useCallback, useId, useState } from "react";
import {
  CALCULATION_EXPLAINERS, equationsForKernel, kernelOfModelId, readResultPath,
  type ExplainerEquation,
} from "../data/calculationExplainers";
import { loadKatex, type KatexRenderer } from "../utils/loadKatex";

type LoadState = "idle" | "loading" | "ready" | "failed";

function valueText(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : null;
  if (typeof value === "string") return value;
  if (typeof value === "boolean") return String(value);
  if (typeof value === "object" && !Array.isArray(value)) {
    // A record of plain numbers (for example the two Ni spacing models) is shown member by member.
    const members = Object.entries(value as Record<string, unknown>).map(([key, member]) => [key, valueText(member)] as const);
    return members.length > 0 && members.every(([, text]) => text !== null) ? members.map(([key, text]) => `${key} ${text}`).join(", ") : null;
  }
  return null;
}

function EquationView({ equation, katex }: { equation: ExplainerEquation; katex: KatexRenderer | null }) {
  let html: string | null = null;
  if (katex) {
    try {
      html = katex.renderToString(equation.latex, { displayMode: true, throwOnError: true, output: "html" });
    } catch {
      html = null;
    }
  }
  return (
    <li className="space-y-1.5 border-t border-slate-800 pt-2" data-equation-id={equation.id}>
      <h5 className="font-sans text-[11px] font-semibold text-slate-200">{equation.label}</h5>
      {html ? (
        <div role="img" aria-label={equation.plain} className="overflow-x-auto text-slate-100" dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        <code role="img" aria-label={equation.plain} className="block overflow-x-auto whitespace-pre-wrap rounded bg-[#050810] p-2 text-[11px] text-slate-100">
          {equation.plain}
        </code>
      )}
      <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-[10px] text-slate-400">
        {equation.symbols.map(([symbol, meaning]) => (
          <React.Fragment key={symbol}>
            <dt className="font-mono text-slate-300">{symbol}</dt>
            <dd>{meaning}</dd>
          </React.Fragment>
        ))}
      </dl>
      <p className="text-[10px] text-slate-400"><span className="text-slate-300">Code:</span> {equation.codeLocator}</p>
      <p className="text-[10px] text-slate-400"><span className="text-slate-300">Source:</span> {equation.sourceLocator}</p>
      {equation.asImplemented && (
        <p className="text-[10px] text-amber-200"><span className="font-semibold">As implemented:</span> {equation.asImplemented}</p>
      )}
    </li>
  );
}

/**
 * Collapsed disclosure "How this is calculated" shown next to a result: the equations the code actually uses, the
 * input values of this run (read from the result object, never recomputed) and the source of each equation. KaTeX is
 * loaded on first open only; without it the plain-text formula is shown.
 */
export function HowCalculated({ explainerId, result, className }: { explainerId: string; result: unknown; className?: string }) {
  const explainer = CALCULATION_EXPLAINERS[explainerId];
  const [state, setState] = useState<LoadState>("idle");
  const [katex, setKatex] = useState<KatexRenderer | null>(null);
  const bodyId = useId();

  const onToggle = useCallback((event: React.SyntheticEvent<HTMLDetailsElement>) => {
    if (!event.currentTarget.open || state === "loading" || state === "ready") return;
    setState("loading");
    loadKatex().then((renderer) => { setKatex(renderer); setState("ready"); }, () => setState("failed"));
  }, [state]);

  if (!explainer || result === null || result === undefined) return null;
  const kernel = kernelOfModelId(readResultPath(result, "modelId") ?? readResultPath(result, "heatSourceModel"));
  const alloyValue = readResultPath(result, "alloyId");
  const equations = equationsForKernel(explainer, kernel, typeof alloyValue === "string" ? alloyValue : null);

  return (
    <details className={`rounded-lg border border-slate-800 bg-[#050810]/60 p-2 text-[11px] text-slate-300 ${className ?? ""}`}
      onToggle={onToggle} data-how-calculated={explainer.id}>
      <summary className="cursor-pointer font-sans text-[11px] font-semibold text-sky-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/60"
        aria-controls={bodyId}>
        How this is calculated
      </summary>
      <div id={bodyId} className="mt-2 space-y-2">
        <p className="font-sans text-[11px] font-semibold text-slate-200">{explainer.title}</p>
        <p className="font-sans text-[10px] leading-4 text-slate-400">{explainer.summary}</p>
        {state === "failed" && <p role="status" className="text-[10px] text-amber-200">The equation renderer could not be loaded; formulas are shown as plain text.</p>}
        {state === "loading" && <p role="status" className="text-[10px] text-slate-400">Loading equation renderer.</p>}

        <div>
          <h5 className="font-sans text-[11px] font-semibold text-slate-200">Inputs of this run</h5>
          <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[10px]" data-run-inputs>
            {explainer.inputs.map((input) => {
              const raw = readResultPath(result, input.path);
              const text = valueText(raw);
              const unit = input.unit === "degC" ? "°C" : input.unit;
              // Shown rounded to 3 significant digits; the exact value of the result stays in the tooltip.
              const shown = typeof raw === "number" && Number.isFinite(raw) ? formatWithUnit(raw, unit) : text === null ? null : `${text}${unit ? ` ${displayUnit(unit)}` : ""}`;
              return (
                <React.Fragment key={input.symbol}>
                  <dt className="font-mono text-slate-300">{input.symbol}</dt>
                  <dd className="text-slate-400">
                    {input.label}: {text === null ? <span className="text-slate-500">symbol only, not in this result</span> : <span className="text-slate-100" title={`${text}${input.unit ? ` ${input.unit}` : ""}`}>{shown}</span>}
                  </dd>
                </React.Fragment>
              );
            })}
          </dl>
        </div>

        <ol className="space-y-2" data-equations>
          {equations.map((equation) => <EquationView key={equation.id} equation={equation} katex={katex} />)}
        </ol>

        {explainer.notes.map((note) => {
          const text = valueText(readResultPath(result, note.path));
          return text === null ? null : (
            <p key={note.path} className="text-[10px] leading-4 text-slate-400" data-result-note={note.path}>
              <span className="text-slate-300">{note.label}:</span> {text}
            </p>
          );
        })}
      </div>
    </details>
  );
}
