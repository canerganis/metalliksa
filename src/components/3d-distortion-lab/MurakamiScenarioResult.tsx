import React from "react";
import { checkedEstimateContainer } from "../../data/quantityEnvelope";
import type { PythonLpbfMurakamiBlock } from "../../services/pythonComputationService";
import { estimateLine, formatSignificant, type EstimateLine } from "../../utils/solidificationEstimateDisplay";
import { EstimateWarnings } from "../SolidificationEstimates";

const STATUSES = ["screening_estimate", "data_not_supplied", "input_refused"];
const EVIDENCE_TEXT: Readonly<Record<string, string>> = { measured: "measured", "assumed-scenario": "assumed scenario" };

function evidenceText(kind: string | null): string {
  return kind ? (EVIDENCE_TEXT[kind] ?? kind) : "not stated";
}

function QuantityRow({ line }: { line: EstimateLine }) {
  return <div data-quantity={line.name} className="border-b border-slate-700/50 py-2">
    <dt className="flex flex-wrap items-center gap-2 text-slate-400">
      <span>{line.label}</span>
      <span data-estimate-tier={line.tier} className="rounded border border-slate-500/50 px-1.5 py-0.5 text-[10px] text-slate-200">{line.tierLabel}</span>
    </dt>
    {line.value !== null && <dd className="break-words text-slate-200" data-estimate-value>{line.value}</dd>}
    <EstimateWarnings warnings={line.warnings} />
    {line.text && <dd className="break-words text-slate-300">{line.text}</dd>}
    {line.sourceLabel && <dd className="break-words text-slate-400">{line.sourceLabel}</dd>}
  </div>;
}

/** Result of the Murakami screening block: payload sentences and numbers only, nothing computed or invented here. */
export function MurakamiScenarioResult({ block }: { block: unknown }) {
  let parsed: PythonLpbfMurakamiBlock;
  try {
    const container = checkedEstimateContainer(block);
    const body = container as unknown as Record<string, unknown>;
    if (body.schema !== "murakami-screening-2") throw new Error(`Unexpected fatigue schema ${String(body.schema)}`);
    if (!STATUSES.includes(String(body.status))) throw new Error("Unexpected fatigue status");
    parsed = container as unknown as PythonLpbfMurakamiBlock;
  } catch (e) {
    return <p role="status" className="text-xs text-slate-300">Fatigue payload rejected: {e instanceof Error ? e.message : String(e)}</p>;
  }
  const names = ["fatigueThreshold", "gumbelLargest"].filter(n => n in parsed.quantities);
  const lines = names.map(n => estimateLine(n, parsed.quantities[n]));
  const echo = parsed.scenarioEcho;
  const obs = parsed.observedMaximum;
  const ct = parsed.ctDetectionThreshold;
  return <div data-murakami-scenario className="text-[10px]">
    <dl className="grid gap-1">{lines.map(line => <QuantityRow key={line.name} line={line} />)}</dl>
    {echo.defectSqrtArea_um !== null && <p className="mt-1 break-words text-slate-300" data-scenario-echo>
      Scenario: defect √area {formatSignificant(echo.defectSqrtArea_um, 3)} µm
      ({evidenceText(echo.defectEvidence)}{echo.defectSqrtAreaBasis ? `, ${echo.defectSqrtAreaBasis}` : ""}),
      {" "}{echo.defectLocation ?? "location not stated"} defect,
      {" "}hardness {echo.hardness_HV !== null ? `${formatSignificant(echo.hardness_HV, 3)} HV` : "not stated"} ({evidenceText(echo.hardnessEvidence)}),
      {" "}R = {echo.loadRatio}{echo.specimenOrientation ? `, ${echo.specimenOrientation} specimen orientation` : ""}.
    </p>}
    {obs && <p className="mt-1 break-words text-slate-300" data-observed-maximum>
      Largest of {obs.n} supplied values: {formatSignificant(obs.value_um, 3)} µm, {obs.label}. {obs.note}
    </p>}
    {parsed.cycleTarget && <p className="mt-1 break-words text-slate-300" data-cycle-target>{parsed.cycleTarget.text}</p>}
    {(ct.label || ct.text) && <p className="mt-1 break-words text-slate-400" data-ct-threshold>
      {ct.value_um !== null && ct.label ? `${ct.label}: ${formatSignificant(ct.value_um, 3)} µm` : null}
      {ct.method ? ` (${ct.method})` : null}
      {ct.text ? ` ${ct.text}` : null}
    </p>}
    <p className="mt-1 break-words text-slate-500">{parsed.note}</p>
  </div>;
}
