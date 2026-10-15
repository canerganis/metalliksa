import React, { useEffect, useId, useMemo, useState } from "react";
import { IS_STATIC_DEMO } from "../../demo/flag";
import {
  isResearchRunnable,
  useLpbfResearchModelStore,
  type ResearchHostState,
  type ResearchRunError,
} from "../../store/useLpbfResearchModelStore";
import {
  RESEARCH_MODULE_ORDER,
  type ResearchControl,
  type ResearchDescribeResponse,
  type ResearchHostId,
  type ResearchProblem,
} from "../../types/lpbfResearchModels";
import {
  inputSignature,
  researchAlloyKey,
  type AlloyOptions,
  type OptionModule,
  type ResearchHostInput,
} from "../../utils/lpbfResearchPanelModel";
import { APPROVED_WORDING, AUTHORED_WORDING, fill } from "../../utils/lpbfResearchWording";
import { MODULE_TITLES, ResearchModuleSection, refusalText } from "./ResearchModuleSection";

// Research model panel (P8 contract 4). Separate from every served tile, verdict and export: it reads its own store,
// holds the research options per alloy, and shows nothing it did not receive from the research route. Collapsed by
// default; the describe stage answers before Run is enabled; the band arrives in chunks and can be cancelled.

export interface ResearchModelPanelProps {
  host: ResearchHostId;
  /** The host's current request values, or null while the host has none (no aligned Build Job yet). */
  input: ResearchHostInput | null;
  /** The served thermal result the Differences compare with (Melt Pool: pyResult; Build Job: job.thermal). */
  served: unknown;
  /** Melt Pool lab: signature of the inputs that produced `served` (4.6). Omitted when the result is aligned by construction. */
  servedSignature?: string | null;
  /** Rendered open at first paint (tests and print). The product default is collapsed. */
  defaultOpen?: boolean;
  defaultOpenModules?: boolean;
}

// ---------------------------------------------------------------------------------------------------------------
// Inputs section

function parseNumber(text: string): number | null {
  const trimmed = text.trim();
  if (trimmed === "") return null;
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : null;
}

function toDisplay(value: number | null, factor: number): string {
  if (value === null) return "";
  return String(Number((value * factor).toPrecision(8)));
}

interface NumberFieldProps {
  id: string;
  value: number | null;
  factor: number;
  disabled: boolean;
  describedBy?: string;
  ariaLabel: string;
  onCommit: (si: number | undefined) => void;
}

/** A number input in a display unit. The committed value is SI; an empty box clears the option. */
function NumberField({ id, value, factor, disabled, describedBy, ariaLabel, onCommit }: NumberFieldProps) {
  const [text, setText] = useState(toDisplay(value, factor));
  useEffect(() => {
    const parsed = parseNumber(text);
    const same = value === null ? parsed === null : parsed !== null && Math.abs(parsed / factor - value) <= 1e-9 * Math.abs(value) + 1e-300;
    if (!same && !(value !== null && text.trim() === "")) setText(toDisplay(value, factor));
  }, [value, factor]);
  return (
    <input
      id={id}
      type="text"
      inputMode="decimal"
      aria-label={ariaLabel}
      aria-describedby={describedBy}
      disabled={disabled}
      value={text}
      className="w-28 rounded border border-slate-700 bg-[#050810] px-1.5 py-0.5 text-[11px] text-slate-100 disabled:opacity-50"
      onChange={(event) => {
        setText(event.target.value);
        const parsed = parseNumber(event.target.value);
        if (event.target.value.trim() === "") onCommit(undefined);
        else if (parsed !== null) onCommit(parsed / factor);
      }}
    />
  );
}

function RangeFields({ control, alloyKey, idBase, range, factor }: {
  control: ResearchControl; alloyKey: string; idBase: string; range: { min: number; max: number } | undefined; factor: number;
}) {
  const setRange = useLpbfResearchModelStore((s) => s.setRange);
  const [minText, setMinText] = useState(range ? toDisplay(range.min, factor) : "");
  const [maxText, setMaxText] = useState(range ? toDisplay(range.max, factor) : "");
  useEffect(() => {
    if (!range) return;
    setMinText(toDisplay(range.min, factor));
    setMaxText(toDisplay(range.max, factor));
  }, [range?.min, range?.max, factor]);
  const commit = (a: string, b: string) => {
    const lo = parseNumber(a);
    const hi = parseNumber(b);
    if (a.trim() === "" && b.trim() === "") setRange(alloyKey, control.module, control.key, undefined);
    else if (lo !== null && hi !== null) setRange(alloyKey, control.module, control.key, { min: lo / factor, max: hi / factor });
  };
  return (
    <span className="inline-flex items-center gap-1" role="group" aria-label={`${control.label}: ${AUTHORED_WORDING.rangeLabel}`}>
      <input
        id={`${idBase}-min`} placeholder={AUTHORED_WORDING.rangeMin} type="text" inputMode="decimal" aria-label={`${control.label} ${AUTHORED_WORDING.rangeMin}`} value={minText}
        className="w-20 rounded border border-slate-700 bg-[#050810] px-1.5 py-0.5 text-[11px] text-slate-100"
        onChange={(e) => { setMinText(e.target.value); commit(e.target.value, maxText); }}
      />
      <input
        id={`${idBase}-max`} placeholder={AUTHORED_WORDING.rangeMax} type="text" inputMode="decimal" aria-label={`${control.label} ${AUTHORED_WORDING.rangeMax}`} value={maxText}
        className="w-20 rounded border border-slate-700 bg-[#050810] px-1.5 py-0.5 text-[11px] text-slate-100"
        onChange={(e) => { setMaxText(e.target.value); commit(minText, e.target.value); }}
      />
    </span>
  );
}

function problemsFor(problems: ResearchProblem[], module: OptionModule, key: string): ResearchProblem[] {
  return problems.filter((p) => p.pointer.endsWith(`/${module}/${key}`) || p.pointer.includes(`/${module}/${key}/`));
}

function ControlRow({ control, alloyKey, options, describe, idBase }: {
  control: ResearchControl; alloyKey: string; options: AlloyOptions; describe: ResearchDescribeResponse; idBase: string;
}) {
  const setOption = useLpbfResearchModelStore((s) => s.setOption);
  const setVapourPreset = useLpbfResearchModelStore((s) => s.setVapourPreset);
  const resetControl = useLpbfResearchModelStore((s) => s.resetControl);
  const unitNames = Object.keys(control.displayUnits);
  const [unitName, setUnitName] = useState(unitNames[0] ?? control.unit);
  const factor = control.displayUnits[unitName] ?? 1;
  const helpId = `${idBase}-help`;
  const problemId = `${idBase}-problems`;
  const own = problemsFor(describe.problems, control.module, control.key);
  const set = options[control.module][control.key];
  const range = options.ranges[control.module][control.key];
  const describedBy = [helpId, own.length ? problemId : ""].filter(Boolean).join(" ");
  const showReset = control.resetLabel !== null && (set !== undefined || range !== undefined);
  const molarMass = control.key === "vapourLatentHeat_J_kg"
    ? describe.controls.find((c) => c.key === "vapourMolarMass_kg_mol")?.value
    : undefined;
  const perMole = typeof control.value === "number" && typeof molarMass === "number" ? control.value * molarMass : null;

  let field: React.ReactNode;
  if (control.valueType === "enum") {
    const choices = control.key === "slopeMode"
      ? describe.presets.slopeMode.map((p) => ({ id: p.id, label: p.label, disabled: false }))
      : control.key === "vapourPreset"
        ? describe.presets.vapourPreset.map((p) => ({ id: p.id, label: p.label, disabled: !p.admitted }))
        : (control.enumValues ?? []).map((v) => ({ id: v, label: v, disabled: false }));
    field = (
      <select
        id={idBase}
        aria-describedby={describedBy}
        disabled={!control.enabled}
        value={typeof control.value === "string" ? control.value : ""}
        className="rounded border border-slate-700 bg-[#050810] px-1.5 py-0.5 text-[11px] text-slate-100 disabled:opacity-50"
        onChange={(event) => {
          if (control.key === "vapourPreset") setVapourPreset(alloyKey, event.target.value);
          else setOption(alloyKey, control.module, control.key, event.target.value);
        }}
      >
        {choices.map((c) => <option key={c.id} value={c.id} disabled={c.disabled}>{c.label}</option>)}
      </select>
    );
  } else {
    field = (
      <>
        <NumberField
          id={idBase}
          ariaLabel={control.label}
          describedBy={describedBy}
          disabled={!control.enabled}
          value={typeof control.value === "number" ? control.value : null}
          factor={factor}
          onCommit={(si) => setOption(alloyKey, control.module, control.key, si)}
        />
        {unitNames.length > 1 ? (
          <select aria-label={`${control.label}: ${AUTHORED_WORDING.unitLabel}`} value={unitName} onChange={(e) => setUnitName(e.target.value)} className="rounded border border-slate-700 bg-[#050810] px-1 py-0.5 text-[11px] text-slate-100">
            {unitNames.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        ) : (
          <span className="text-[10px] text-slate-400">{unitNames[0] ?? (control.unit === "1" ? "" : control.unit)}</span>
        )}
        {control.rangeAdmitted && control.enabled ? <RangeFields control={control} alloyKey={alloyKey} idBase={idBase} range={range} factor={factor} /> : null}
      </>
    );
  }

  return (
    <li className="space-y-0.5 border-t border-slate-800 py-1.5" data-testid={`research-control-${control.key}`}>
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor={idBase} className="text-[11px] font-semibold text-slate-200">{control.label}</label>
        {field}
        <span className="rounded border border-slate-700 px-1.5 py-0.5 text-[9px] text-slate-300" title={control.provenance.scope}>{control.provenance.followsInput && !control.provenance.label.includes(control.provenance.followsInput) ? `${control.provenance.label} ${control.provenance.followsInput}` : control.provenance.label}</span>
        {showReset ? (
          <button type="button" className="rounded border border-slate-700 px-1.5 py-0.5 text-[10px] text-slate-200 hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400" onClick={() => resetControl(alloyKey, control.module, control.key)}>
            {control.resetLabel}
          </button>
        ) : null}
      </div>
      {perMole !== null ? <p className="text-[10px] text-slate-400">{`L x M = ${Number(perMole.toPrecision(5))} J/mol`}</p> : null}
      <p id={helpId} className="text-[10px] leading-4 text-slate-400">{control.help}</p>
      {own.length > 0 ? (
        <ul id={problemId} className="text-[10px] leading-4 text-amber-300">
          {own.map((p, i) => <li key={`${p.pointer}-${i}`}>{p.message}</li>)}
        </ul>
      ) : null}
    </li>
  );
}

function InputsSection({ alloyKey, describe, defaultOpen }: { alloyKey: string; describe: ResearchDescribeResponse; defaultOpen: boolean }) {
  const options = useLpbfResearchModelStore((s) => s.optionsByAlloy[alloyKey]);
  const cleared = useLpbfResearchModelStore((s) => s.presetCleared[alloyKey] === true);
  const resolved = useMemo<AlloyOptions>(() => options ?? { marangoni: {}, surfaceBalance: {}, ranges: { marangoni: {}, surfaceBalance: {} } }, [options]);
  const uid = useId();
  const modules: OptionModule[] = ["marangoni", "surfaceBalance"];
  const general = describe.problems.filter((p) => !modules.some((m) => p.pointer.includes(`/${m}/`)));
  return (
    <details className="rounded-lg border border-slate-800 bg-[#050810] p-2" open={defaultOpen || undefined} data-testid="research-inputs">
      <summary className="cursor-pointer text-[11px] font-bold text-slate-200">{AUTHORED_WORDING.inputsHeading}</summary>
      <p className="mt-1 text-[10px] leading-4 text-slate-400">{AUTHORED_WORDING.inputsHelp}</p>
      {cleared ? <p className="text-[10px] text-slate-300" role="status">{AUTHORED_WORDING.presetClearedNote}</p> : null}
      {general.length > 0 ? <ul className="text-[10px] text-amber-300">{general.map((p, i) => <li key={i}>{p.message}</li>)}</ul> : null}
      {modules.map((module) => {
        const controls = describe.controls.filter((c) => c.module === module);
        if (controls.length === 0) return null;
        return (
          <fieldset key={module} className="mt-1">
            <legend className="text-[10px] font-semibold uppercase tracking-wide text-slate-300">{MODULE_TITLES[module]}</legend>
            <ul>
              {controls.map((control) => (
                <ControlRow key={control.key} control={control} alloyKey={alloyKey} options={resolved} describe={describe} idBase={`${uid}-${control.key}`.replace(/:/g, "")} />
              ))}
            </ul>
          </fieldset>
        );
      })}
    </details>
  );
}

// ---------------------------------------------------------------------------------------------------------------
// Status

function errorText(error: ResearchRunError, sentences: Record<string, string>): string {
  const registry = refusalText(error.reasonCode, sentences);
  const problems = error.problems.map((p) => p.message).join(" ");
  if (registry) return [registry, problems].filter(Boolean).join(" ");
  if (problems) return problems;
  if (error.message) return error.reasonCode === "RESPONSE_MALFORMED" ? AUTHORED_WORDING.errorMalformed : fill(AUTHORED_WORDING.errorNetwork, { message: error.message });
  return fill(AUTHORED_WORDING.errorGeneric, { code: error.reasonCode ?? "unknown" });
}

function statusLine(host: ResearchHostState, sentences: Record<string, string>): string {
  const { run, describe } = host;
  const checking = describe.status === "checking" ? ` ${AUTHORED_WORDING.checkingInputs}.` : "";
  if (run.status === "running-nominal") return AUTHORED_WORDING.runningNominal;
  if (run.status === "band-pending") {
    return fill(AUTHORED_WORDING.bandPending, { armsDone: run.progress?.armsDone ?? 0, armsTotal: run.progress?.armsTotal ?? 0 });
  }
  if (run.status === "cancelled") return AUTHORED_WORDING.cancelled + checking;
  if (run.status === "stale") return AUTHORED_WORDING.stale + checking;
  if (run.status === "error" && run.error) return fill(AUTHORED_WORDING.errorPrefix, { reason: errorText(run.error, sentences) }) + checking;
  if (describe.status === "checking") return AUTHORED_WORDING.checkingInputs;
  if (describe.status === "error" && describe.error) return fill(AUTHORED_WORDING.describeFailed, { reason: errorText(describe.error, sentences) });
  if (run.status === "complete") return AUTHORED_WORDING.complete;
  return AUTHORED_WORDING.idleHint;
}

// ---------------------------------------------------------------------------------------------------------------
// Panel

export function ResearchModelPanel({ host, input, served, servedSignature, defaultOpen = false, defaultOpenModules = false }: ResearchModelPanelProps) {
  const [open, setOpen] = useState(defaultOpen);
  const hostState = useLpbfResearchModelStore((s) => s.hosts[host]);
  const syncHost = useLpbfResearchModelStore((s) => s.syncHost);
  const run = useLpbfResearchModelStore((s) => s.run);
  const cancel = useLpbfResearchModelStore((s) => s.cancel);
  const retry = useLpbfResearchModelStore((s) => s.retry);
  const unmountHost = useLpbfResearchModelStore((s) => s.unmountHost);

  // The host's current request values; a change (or an option edit, in the store) hides every research value.
  const inputKey = input ? JSON.stringify([inputSignature(input), input.propertyContext]) : "none";
  useEffect(() => {
    if (IS_STATIC_DEMO || input === null) return;
    syncHost(host, input);
  }, [host, inputKey, syncHost]);
  useEffect(() => () => unmountHost(host), [host, unmountHost]);

  const titleId = useId();
  const header = (
    <div className="flex flex-wrap items-center gap-2">
      <h4 id={titleId} className="text-xs font-bold text-white">{APPROVED_WORDING.panelTitle}</h4>
      <span className="rounded border border-slate-600 px-1.5 py-0.5 text-[10px] text-slate-300" title={APPROVED_WORDING.researchArmLabel}>{APPROVED_WORDING.badgeResearch}</span>
      <span className="rounded border border-slate-600 px-1.5 py-0.5 text-[10px] text-slate-300">{APPROVED_WORDING.badgeScreeningOnly}</span>
      <span className="rounded border border-slate-600 px-1.5 py-0.5 text-[10px] text-slate-300">{APPROVED_WORDING.badgeNoValidation}</span>
    </div>
  );

  if (IS_STATIC_DEMO) {
    return (
      <section data-testid="research-model-panel" aria-labelledby={titleId} className="rounded-xl border border-[#162032] bg-[#090e18] p-3.5 space-y-2">
        {header}
        <p className="text-[11px] text-slate-300">{AUTHORED_WORDING.staticDemo}</p>
      </section>
    );
  }

  const describe = hostState.describe;
  const response = describe.response;
  const sentences = response?.sentences ?? {};
  const runnable = isResearchRunnable(hostState) && input !== null;
  const running = hostState.run.status === "running-nominal" || hostState.run.status === "band-pending";
  const alloyKey = input ? researchAlloyKey(input.material) : null;

  // Which result is on screen: only one that belongs to the current inputs (4.3 item 4).
  const r = hostState.run;
  const belongs = input !== null && r.identity !== null && r.identity === hostState.identity;
  const shownResponse = belongs && (r.status === "complete" ? r.result : r.status === "band-pending" || r.status === "cancelled" || r.status === "error" ? r.nominal : null);
  const block = shownResponse?.researchModels ?? null;

  const servedMatches = served !== null && served !== undefined && r.input !== null
    && (servedSignature === undefined || servedSignature === inputSignature(r.input));

  return (
    <section data-testid="research-model-panel" aria-labelledby={titleId} className="rounded-xl border border-[#162032] bg-[#090e18] p-3.5 space-y-2.5">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-2 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
        aria-expanded={open}
        aria-controls={`${titleId}-body`}
        onClick={() => setOpen((v) => !v)}
      >
        {header}
        <span className="text-[10px] text-slate-400" aria-hidden="true">{open ? "-" : "+"}</span>
      </button>
      {open && (
        <div id={`${titleId}-body`} className="space-y-2.5">
          <p className="text-[11px] leading-4 text-slate-300" data-testid="research-scope-line">{APPROVED_WORDING.scopeLine}</p>

          {response && alloyKey ? <InputsSection alloyKey={alloyKey} describe={response} defaultOpen={defaultOpenModules} /> : null}
          {response && response.problems.length > 0 ? (
            <ul className="text-[10px] leading-4 text-amber-300" data-testid="research-problems">
              {response.problems.map((p, i) => <li key={`${p.pointer}-${i}`}>{p.message}</li>)}
            </ul>
          ) : null}

          <div className="flex flex-wrap items-center gap-2" data-testid="research-run-bar">
            <button
              type="button"
              disabled={!runnable || running}
              className="rounded border border-sky-500/50 bg-sky-500/10 px-2.5 py-1 text-[11px] font-semibold text-sky-100 disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              onClick={() => void run(host)}
            >
              {AUTHORED_WORDING.runButton}
            </button>
            <button
              type="button"
              disabled={!running}
              className="rounded border border-slate-600 px-2.5 py-1 text-[11px] text-slate-200 disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              onClick={() => cancel(host)}
            >
              {AUTHORED_WORDING.cancelButton}
            </button>
            {(r.status === "error" || describe.status === "error") && (
              <button type="button" className="rounded border border-slate-600 px-2.5 py-1 text-[11px] text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400" onClick={() => retry(host)}>
                {AUTHORED_WORDING.retryButton}
              </button>
            )}
            <span role="status" aria-live="polite" className="text-[11px] text-slate-300" data-testid="research-status">
              {input === null ? "" : statusLine(hostState, sentences)}
            </span>
          </div>

          {block && shownResponse ? (
            <div className="space-y-2" data-testid="research-results">
              {RESEARCH_MODULE_ORDER.map((moduleId) => {
                const container = block[moduleId];
                if (!container) return null;
                return (
                  <ResearchModuleSection
                    key={moduleId}
                    moduleId={moduleId}
                    container={container}
                    block={block}
                    labels={shownResponse.labels}
                    sentences={sentences}
                    defaultOpen={defaultOpenModules}
                    differenceContext={{ host, alloyId: alloyKey ?? "", served: servedMatches ? served : null, servedMatches, block }}
                  />
                );
              })}
              <p className="text-[10px] leading-4 text-slate-500" data-testid="research-footer">
                {fill(AUTHORED_WORDING.scopeFootnote, {
                  requestKey: shownResponse.requestKey.slice(0, 12),
                  impl: shownResponse.identity.researchImplementationSha256.slice(0, 12),
                  hit: r.cache?.armsHit ?? 0,
                  computed: r.cache?.armsComputed ?? 0,
                })}
                {r.channel === "ad_hoc_fallback" ? ` ${AUTHORED_WORDING.channelAdhoc}` : ""}
              </p>
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
