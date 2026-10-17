import React from "react";
import { checkedEstimateContainer } from "../../data/quantityEnvelope";
import type { PythonLpbfMechanicsScenariosBlock } from "../../services/pythonComputationService";
import {
  CALIBRATION_IDENTITY_KEYS,
  type LpbfMechanicsBarInput,
  type LpbfMechanicsCantileverInput,
  type LpbfMechanicsEvidence,
  type LpbfMechanicsSessionInput,
  type LpbfProfileEvidence,
} from "../../store/useLpbfBuildJobStore";
import { estimateLine, type EstimateLine } from "../../utils/solidificationEstimateDisplay";
import { EstimateWarnings } from "../SolidificationEstimates";

const FIELD = "ml-1 bg-[#060a12] border border-[#162032] rounded px-1 py-0.5 text-[11px] text-slate-200";
const STATUSES = ["computed", "partial", "unavailable"];
const NAMES = ["barStress", "tipDeflection", "tipDeflectionOverThickness"];
export const SCOPE_NOTE = "These scenarios are not used by the Build Job verdict, the recoater gate, or the legacy residual-stress and distortion fields.";
export const SATURATION_BADGE = "Saturated at the supplied yield strength";

const EVIDENCE: readonly (readonly [LpbfMechanicsEvidence, string])[] =
  [["measured", "measured"], ["literature", "literature"], ["assumed-scenario", "assumed scenario"]];
const PROFILE_EVIDENCE: readonly (readonly [LpbfProfileEvidence, string])[] = [
  ["matched-build-calibration", "matched-build calibration"],
  ["assumed-effective-profile-scenario", "assumed effective-profile scenario"],
];
const IDENTITY_LABELS: Readonly<Record<string, string>> = {
  buildId: "Build ID", machine: "Machine", alloyState: "Alloy state", orientation: "Orientation",
  supportRestraint: "Support restraint", depositionHistory: "Deposition history",
  referenceGeometry: "Reference geometry", releaseSequence: "Release sequence",
};

function numberOrNull(raw: string): number | null {
  return raw.trim() === "" || !Number.isFinite(Number(raw)) ? null : Number(raw);
}

function Choice<T extends string>({ legend, name, value, options, onPick }: {
  legend: string; name: string; value: T | null; options: readonly (readonly [T, string])[]; onPick: (v: T) => void;
}) {
  return <fieldset className="flex flex-wrap items-center gap-2 text-[10px] text-slate-400 font-mono">
    <legend className="sr-only">{legend}</legend>
    <span>{legend}</span>
    {options.map(([v, text]) => <label key={v} className="flex items-center gap-1">
      <input type="radio" name={name} checked={value === v} onChange={() => onPick(v)} />{text}
    </label>)}
  </fieldset>;
}

function NumberField({ label, value, onChange, width = "w-20", step }: {
  label: string; value: number | null; onChange: (v: number | null) => void; width?: string; step?: string;
}) {
  return <label className="text-[10px] text-slate-400 font-mono">
    {label}
    <input type="number" step={step} value={value ?? ""} onChange={(e) => onChange(numberOrNull(e.target.value))}
      className={`${FIELD} ${width}`} />
  </label>;
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

/** Result of the mechanics scenarios block: payload sentences and numbers only, nothing computed or invented here. */
export function MechanicsScenariosResult({ block }: { block: unknown }) {
  let parsed: PythonLpbfMechanicsScenariosBlock;
  try {
    const container = checkedEstimateContainer(block);
    const body = container as unknown as Record<string, unknown>;
    if (body.usedForBuildJobVerdict !== false) throw new Error("Mechanics scenarios must not feed the verdict");
    if (!STATUSES.includes(String(body.status))) throw new Error("Unexpected mechanics status");
    parsed = container as unknown as PythonLpbfMechanicsScenariosBlock;
  } catch (e) {
    return <p role="status" className="text-xs text-slate-300">Mechanics payload rejected: {e instanceof Error ? e.message : String(e)}</p>;
  }
  const lines = NAMES.filter(n => n in parsed.quantities).map(n => estimateLine(n, parsed.quantities[n]));
  return <div data-mechanics-scenarios className="text-[10px]">
    {parsed.barScenario?.saturatedAtYield === true &&
      <p data-saturation-badge className="mb-1 w-fit rounded border border-amber-400/60 px-1.5 py-0.5 text-amber-200">{SATURATION_BADGE}</p>}
    <dl className="grid gap-1">{lines.map(line => <QuantityRow key={line.name} line={line} />)}</dl>
  </div>;
}

function BarInputs({ input, onChange }: { input: LpbfMechanicsBarInput; onChange: (p: Partial<LpbfMechanicsBarInput>) => void }) {
  return <div className="space-y-2" data-mechanics-bar-inputs>
    <h4 className="text-[11px] font-bold text-slate-200">Constrained bar (thermal cycle)</h4>
    <div className="flex flex-wrap gap-2 items-end">
      <NumberField label="Elastic modulus GPa" value={input.elasticModulus_GPa} onChange={(v) => onChange({ elasticModulus_GPa: v })} />
      <NumberField label="Thermal expansion 1/K" value={input.thermalExpansion_per_K} step="any" onChange={(v) => onChange({ thermalExpansion_per_K: v })} />
      <NumberField label="Yield at return temperature MPa" value={input.returnYield_MPa} onChange={(v) => onChange({ returnYield_MPa: v })} />
      <NumberField label="Return temperature °C" value={input.returnTemperature_C} onChange={(v) => onChange({ returnTemperature_C: v })} />
      <NumberField label="Peak temperature °C" value={input.peakTemperature_C} onChange={(v) => onChange({ peakTemperature_C: v })} />
    </div>
    <Choice legend="Elastic modulus is" name="mech-bar-e-evidence" value={input.elasticModulusEvidence} options={EVIDENCE}
      onPick={(v) => onChange({ elasticModulusEvidence: v })} />
    <Choice legend="Thermal expansion is" name="mech-bar-alpha-evidence" value={input.thermalExpansionEvidence} options={EVIDENCE}
      onPick={(v) => onChange({ thermalExpansionEvidence: v })} />
    <Choice legend="Yield strength is" name="mech-bar-yield-evidence" value={input.returnYieldEvidence} options={EVIDENCE}
      onPick={(v) => onChange({ returnYieldEvidence: v })} />
  </div>;
}

function CantileverInputs({ input, onChange }: {
  input: LpbfMechanicsCantileverInput; onChange: (p: Partial<LpbfMechanicsCantileverInput>) => void;
}) {
  const setRow = (i: number, patch: Partial<LpbfMechanicsCantileverInput["profile"][number]>) =>
    onChange({ profile: input.profile.map((r, j) => (j === i ? { ...r, ...patch } : r)) });
  return <div className="space-y-2" data-mechanics-cantilever-inputs>
    <h4 className="text-[11px] font-bold text-slate-200">Released cantilever (effective inherent-strain profile)</h4>
    <div className="flex flex-wrap gap-2 items-end">
      <NumberField label="Length mm" value={input.length_mm} onChange={(v) => onChange({ length_mm: v })} />
      <NumberField label="Thickness mm" value={input.thickness_mm} onChange={(v) => onChange({ thickness_mm: v })} />
      <NumberField label="Elastic modulus GPa" value={input.elasticModulus_GPa} onChange={(v) => onChange({ elasticModulus_GPa: v })} />
      <NumberField label="Yield strength MPa" value={input.releaseYield_MPa} onChange={(v) => onChange({ releaseYield_MPa: v })} />
      <NumberField label="Small-rotation limit rad" value={input.maxRotation_rad} step="any" onChange={(v) => onChange({ maxRotation_rad: v })} />
    </div>
    <Choice legend="Profile is" name="mech-profile-evidence" value={input.profileEvidence} options={PROFILE_EVIDENCE}
      onPick={(v) => onChange({ profileEvidence: v })} />
    {input.profileEvidence === "matched-build-calibration" && <div className="grid gap-1" data-mechanics-calibration-identity>
      {CALIBRATION_IDENTITY_KEYS.map(k => <label key={k} className="text-[10px] text-slate-400 font-mono">
        {IDENTITY_LABELS[k]}
        <input type="text" value={input.calibrationIdentity[k]} className={`${FIELD} w-48`}
          onChange={(e) => onChange({ calibrationIdentity: { ...input.calibrationIdentity, [k]: e.target.value } })} />
      </label>)}
    </div>}
    <div className="space-y-1" data-mechanics-profile>
      <p className="text-[10px] text-slate-500">
        Profile rows: fractions of the thickness measured from the bottom face (0 to 1), strain positive for expansion.
        Rows must cover the full thickness without gaps.
      </p>
      {input.profile.map((r, i) => <div key={i} className="flex flex-wrap items-end gap-2" data-profile-row>
        <NumberField label="From" value={r.from} step="any" width="w-16" onChange={(v) => setRow(i, { from: v })} />
        <NumberField label="To" value={r.to} step="any" width="w-16" onChange={(v) => setRow(i, { to: v })} />
        <NumberField label="Strain" value={r.strain} step="any" width="w-24" onChange={(v) => setRow(i, { strain: v })} />
        <button type="button" className="text-[10px] text-cyan-200 underline" aria-label={`Remove profile row ${i + 1}`}
          onClick={() => onChange({ profile: input.profile.filter((_, j) => j !== i) })}>Remove</button>
      </div>)}
      <button type="button" className="text-[10px] text-cyan-200 underline"
        onClick={() => onChange({ profile: [...input.profile, { from: null, to: null, strain: null }] })}>Add profile row</button>
    </div>
  </div>;
}

export function MechanicsScenariosPanel({ input, onBarChange, onCantileverChange, block }: {
  input: LpbfMechanicsSessionInput;
  onBarChange: (p: Partial<LpbfMechanicsBarInput>) => void;
  onCantileverChange: (p: Partial<LpbfMechanicsCantileverInput>) => void;
  block?: unknown;
}) {
  return <div className="space-y-2" data-mechanics-panel>
    <p className="text-[10px] text-slate-400" data-mechanics-scope>{SCOPE_NOTE}</p>
    <p className="text-[10px] text-slate-500">
      Nothing is prefilled. A section runs only when all of its fields and evidence kinds are set.
    </p>
    <BarInputs input={input.bar} onChange={onBarChange} />
    <CantileverInputs input={input.cantilever} onChange={onCantileverChange} />
    {block != null && <MechanicsScenariosResult block={block} />}
  </div>;
}
