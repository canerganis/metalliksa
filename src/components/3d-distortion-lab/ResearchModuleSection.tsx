import React, { useState } from "react";
import type {
  ResearchBlock,
  ResearchField,
  ResearchFieldBand,
  ResearchInputProvenance,
  ResearchLeaf,
  ResearchModuleContainer,
  ResearchModuleId,
} from "../../types/lpbfResearchModels";
import {
  exactText,
  formatScalar,
  isScalar,
  primarySentence,
  renderServedDifference,
  type DifferenceContext,
} from "../../utils/lpbfResearchPanelModel";
import { APPROVED_WORDING, AUTHORED_WORDING, fill, supportText } from "../../utils/lpbfResearchWording";

// One research module: always-visible evidence header, a collapsed body that renders only when opened (the block is
// large, so nothing below the header is built while the section is closed). Research only, never validation: every
// value shows its source support, and no status uses an approval colour.

export const MODULE_TITLES: Record<ResearchModuleId, string> = {
  keyholeCavity: "Keyhole cavity",
  meltDepthLink: "Melt depth link",
  marangoni: "Marangoni surface flow",
  surfaceBalance: "Surface balance",
  alSi10MgIndexDisclosure: "AlSi10Mg absorption index",
  alSi10MgVapourMgAware: "AlSi10Mg vapour with Mg",
  unavailablePhysics: "Not available",
};

export interface ModuleSectionProps {
  moduleId: ResearchModuleId;
  container: ResearchModuleContainer;
  block: ResearchBlock;
  labels: Record<string, string>;
  sentences: Record<string, string>;
  differenceContext: DifferenceContext;
  /** Open at first render (tests and print); the panel leaves every module collapsed. */
  defaultOpen?: boolean;
}

export function refusalText(code: string | null, sentences: Record<string, string>): string | null {
  if (!code) return null;
  const key = `refusal.${code}`;
  return sentences[key] ?? null;
}

/** Label of a field; a `{name}` slot in a label is filled from the container's field of that name (for example the onset event). */
function fieldLabel(labels: Record<string, string>, moduleId: string, key: string, container?: ResearchModuleContainer): string {
  const label = labels[`${moduleId}.${key}`] ?? key;
  return label.replace(/\{(\w+)\}/g, (match, name: string) => {
    const value = container?.fields[name]?.value;
    return typeof value === "string" ? value : match;
  });
}

function displayValue(leaf: ResearchLeaf, labels: Record<string, string>, path: string): string | null {
  if (typeof leaf.value === "string") return labels[`${path}.${leaf.value}`] ?? leaf.value;
  return formatScalar(leaf.value, leaf.unit);
}

function Support({ leaf }: { leaf: ResearchLeaf }) {
  const text = supportText(leaf.sourceEvidenceKind, leaf.weakestInputs);
  if (!text) return <span className="text-slate-500">{AUTHORED_WORDING.notComputed}</span>;
  return <span title={leaf.labelSources.join("; ")}>{text}</span>;
}

function ValueCell({ leaf, labels, path, sentences }: { leaf: ResearchLeaf; labels: Record<string, string>; path: string; sentences: Record<string, string> }) {
  if (leaf.value === null || leaf.value === undefined) {
    const reason = refusalText(leaf.reasonCode, sentences);
    return (
      <span>
        {AUTHORED_WORDING.notComputed}
        {reason ? <span className="block text-[10px] leading-4 text-slate-400">{reason}</span> : leaf.reasonCode ? <span className="block text-[10px] text-slate-400">{leaf.reasonCode}</span> : null}
      </span>
    );
  }
  if (!isScalar(leaf.value)) return <span className="text-slate-400">{AUTHORED_WORDING.exactValues}</span>;
  return <span className="tabular-nums">{displayValue(leaf, labels, path)}</span>;
}

function BandCells({ band, labels, sentences, path }: { band: ResearchFieldBand; labels: Record<string, string>; sentences: Record<string, string>; path: string }) {
  if (band.completeness === "pending") {
    return <><td className="px-2 py-1 text-slate-500" colSpan={2}>{AUTHORED_WORDING.modulePending}</td></>;
  }
  if (band.completeness === "unavailable") {
    return <td className="px-2 py-1 text-slate-400" colSpan={2}>{AUTHORED_WORDING.bandUnavailable}</td>;
  }
  return (
    <>
      <td className="px-2 py-1 align-top">
        <ValueCell leaf={band.min} labels={labels} path={path} sentences={sentences} />
      </td>
      <td className="px-2 py-1 align-top">
        <ValueCell leaf={band.max} labels={labels} path={path} sentences={sentences} />
      </td>
    </>
  );
}

/** Lowest and highest scenario with their arm labels (which carry the arm provenance), and tie counts (4.7). */
function Extremes({ band }: { band: ResearchFieldBand }) {
  if ((band.completeness !== "complete" && band.completeness !== "partial") || !band.minArmLabel || !band.maxArmLabel) return null;
  if (band.min.value === band.nominal.value && band.max.value === band.nominal.value) return null;
  const ties = [
    band.minArmTies && band.minArmTies > 1 ? fill(AUTHORED_WORDING.bandTieLowest, { k: band.minArmTies }) : "",
    band.maxArmTies && band.maxArmTies > 1 ? fill(AUTHORED_WORDING.bandTieHighest, { k: band.maxArmTies }) : "",
  ].filter(Boolean).join(" ");
  return (
    <span className="block text-[10px] leading-4 text-slate-400">
      {fill(AUTHORED_WORDING.bandExtremes, { min: band.minArmLabel, max: band.maxArmLabel })}{ties ? ` ${ties}` : ""}
    </span>
  );
}

function FieldTable({ moduleId, container, labels, sentences }: { moduleId: ResearchModuleId; container: ResearchModuleContainer; labels: Record<string, string>; sentences: Record<string, string> }) {
  const rows = Object.entries(container.fields) as Array<[string, ResearchField]>;
  const hasBands = rows.some(([, f]) => f.band !== undefined);
  return (
    <table className="w-full text-left text-[11px] text-slate-200" data-testid={`research-fields-${moduleId}`}>
      <caption className="sr-only">{`${MODULE_TITLES[moduleId]}: ${AUTHORED_WORDING.fieldsHeading}`}</caption>
      <thead>
        <tr className="text-[10px] uppercase tracking-wide text-slate-400">
          <th scope="col" className="px-2 py-1">{AUTHORED_WORDING.colField}</th>
          <th scope="col" className="px-2 py-1">{AUTHORED_WORDING.colNominal}</th>
          {hasBands && <th scope="col" className="px-2 py-1">{AUTHORED_WORDING.colMin}</th>}
          {hasBands && <th scope="col" className="px-2 py-1">{AUTHORED_WORDING.colMax}</th>}
          <th scope="col" className="px-2 py-1">{AUTHORED_WORDING.colSupport}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([key, field]) => {
          const path = `${moduleId}.${key}`;
          const echo = field.band && field.leafRole === "requestInput" && field.band.completeness === "complete"
            && field.band.min.value === field.band.nominal.value && field.band.max.value === field.band.nominal.value;
          return (
            <tr key={key} className="border-t border-slate-800 align-top">
              <th scope="row" className="px-2 py-1 font-normal text-slate-300">
                {fieldLabel(labels, moduleId, key, container)}
                {echo ? <span className="block text-[10px] leading-4 text-slate-400">{AUTHORED_WORDING.bandDegenerate}</span> : null}
                {field.band ? <Extremes band={field.band} /> : null}
              </th>
              <td className="px-2 py-1"><ValueCell leaf={field} labels={labels} path={path} sentences={sentences} /></td>
              {hasBands && (field.band ? <BandCells band={field.band} labels={labels} sentences={sentences} path={path} /> : <td className="px-2 py-1 text-slate-500" colSpan={2}>{AUTHORED_WORDING.notComputed}</td>)}
              <td className="px-2 py-1 text-slate-300"><Support leaf={field} /></td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function ExactValues({ moduleId, container }: { moduleId: ResearchModuleId; container: ResearchModuleContainer }) {
  const rows = Object.entries(container.fields) as Array<[string, ResearchField]>;
  return (
    <details className="text-[10px] text-slate-400" data-testid={`research-exact-${moduleId}`}>
      <summary className="cursor-pointer">{AUTHORED_WORDING.exactValues}</summary>
      <ul className="mt-1 space-y-0.5 font-mono">
        {rows.map(([key, field]) => (
          <li key={key}>
            {key}: {exactText(field.value) ?? "null"}
            {field.band && field.band.completeness !== "pending" ? ` (min ${exactText(field.band.min.value) ?? "null"}, max ${exactText(field.band.max.value) ?? "null"})` : ""}
          </li>
        ))}
      </ul>
    </details>
  );
}

function provenanceSource(p: ResearchInputProvenance): string {
  return p.sourceLocator ?? p.declarationLocator ?? p.source ?? "";
}

function InputProvenanceTable({ container }: { container: ResearchModuleContainer }) {
  const rows = Object.entries(container.inputProvenance);
  return (
    <table className="w-full text-left text-[10px] text-slate-300">
      <thead>
        <tr className="uppercase tracking-wide text-slate-400">
          <th scope="col" className="px-2 py-1">{AUTHORED_WORDING.colInput}</th>
          <th scope="col" className="px-2 py-1">{AUTHORED_WORDING.colKind}</th>
          <th scope="col" className="px-2 py-1">{AUTHORED_WORDING.colSource}</th>
          <th scope="col" className="px-2 py-1">{AUTHORED_WORDING.colPhase}</th>
          <th scope="col" className="px-2 py-1">{AUTHORED_WORDING.colRefTemp}</th>
          <th scope="col" className="px-2 py-1">{AUTHORED_WORDING.colRange}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([key, record]) => {
          const p = record.provenance;
          return (
            <tr key={key} className="border-t border-slate-800 align-top">
              <th scope="row" className="px-2 py-1 font-normal">{key}</th>
              <td className="px-2 py-1">{p.label}</td>
              <td className="px-2 py-1">{provenanceSource(p)}</td>
              <td className="px-2 py-1">{p.phase ?? AUTHORED_WORDING.notComputed}</td>
              <td className="px-2 py-1">{p.referenceTemperature_K === null ? AUTHORED_WORDING.notComputed : `${p.referenceTemperature_K} K`}</td>
              <td className="px-2 py-1">{p.sourceRange_K === null ? AUTHORED_WORDING.sourceRangeNotEstablished : `${p.sourceRange_K[0]} to ${p.sourceRange_K[1]} K`}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function BandBlock({ container, sentences }: { container: ResearchModuleContainer; sentences: Record<string, string> }) {
  const band = container.band;
  if (!band) return null;
  const failed = Array.isArray(band.failedArms) ? (band.failedArms as Array<{ armId?: string; reasonCode?: string | null }>) : [];
  const total = Array.isArray(band.manifest) ? band.manifest.length : null;
  const ok = typeof band.successfulArmCount?.value === "number" ? band.successfulArmCount.value : null;
  const support = band.onsetSupport;
  const listed = (band.manifest ?? []).filter((arm) => arm.armProvenance.kind !== "sourceDefault" && arm.armProvenance.kind !== "sourceModelAssumption" && arm.family !== "nominal");
  return (
    <div className="space-y-1 text-[11px] text-slate-300" data-testid="research-band-block">
      {band.completeness === "pending" ? null : (
        <p>
          {band.caption} {ok !== null ? fill(AUTHORED_WORDING.namedScenarios, { n: ok }) : ""}
        </p>
      )}
      {band.completeness === "partial" && failed.length > 0 && (
        <div>
          <p>{fill(AUTHORED_WORDING.bandPartial, { f: failed.length, n: total ?? failed.length })}</p>
          <ul className="ml-4 list-disc">
            {failed.map((f, i) => (
              <li key={`${f.armId ?? "arm"}-${i}`}>{f.armId ?? ""} {refusalText(f.reasonCode ?? null, sentences) ?? f.reasonCode ?? ""}</li>
            ))}
          </ul>
        </div>
      )}
      {band.completeness === "unavailable" && <p>{AUTHORED_WORDING.bandUnavailable}</p>}
      {support && (
        <div data-testid="research-onset-support">
          <h6 className="font-semibold text-slate-200">{AUTHORED_WORDING.scenarioSupportHeading}</h6>
          {support.caveat ? <p>{support.caveat}</p> : null}
          {listed.length > 0 && (
            <ul className="ml-4 list-disc">
              {listed.map((arm) => (
                <li key={arm.armId}>{arm.label}{arm.armProvenance.label ? ` (${arm.armProvenance.label})` : ""}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export function ResearchModuleSection(props: ModuleSectionProps) {
  const { moduleId, container, labels, sentences, differenceContext } = props;
  const [open, setOpen] = useState(props.defaultOpen === true);
  const primary = primarySentence(container);
  const notApplicable = container.status === "not-applicable";
  const notes = container.consistencyNote;
  const fieldShapeShown = moduleId === "meltDepthLink" && notes.fieldShapeStep != null && sentences.fieldShape;
  return (
    <section className="rounded-lg border border-slate-800 bg-[#050810] p-2.5" data-testid={`research-module-${moduleId}`} aria-labelledby={`research-module-${moduleId}-title`}>
      <header className="space-y-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <h5 id={`research-module-${moduleId}-title`} className="text-[11px] font-bold text-slate-100">{MODULE_TITLES[moduleId]}</h5>
          <span className="rounded border border-slate-600 px-1.5 py-0.5 text-[9px] text-slate-300">{APPROVED_WORDING.badgeResearch}</span>
          <span className="rounded border border-slate-600 px-1.5 py-0.5 text-[9px] text-slate-300">{APPROVED_WORDING.badgeScreeningOnly}</span>
          {container.experimentalValidation === false && (
            <span className="rounded border border-slate-600 px-1.5 py-0.5 text-[9px] text-slate-300">{APPROVED_WORDING.badgeNoValidation}</span>
          )}
        </div>
        <p className="text-[10px] leading-4 text-slate-400" title={container.validationStatusLocator}>{container.validationStatus}</p>
        {notApplicable ? <p className="text-[11px] text-slate-400">{AUTHORED_WORDING.moduleNotApplicable}</p> : null}
        <p className="text-[11px] leading-4 text-slate-300">{container.uiSentence}</p>
        {primary ? <p className="text-[11px] leading-4 text-slate-300" data-testid="research-primary-sentence">{primary}</p> : null}
        {fieldShapeShown ? <p className="text-[11px] leading-4 text-slate-300">{sentences.fieldShape}</p> : null}
        <button
          type="button"
          className="rounded border border-slate-700 px-2 py-0.5 text-[10px] text-slate-200 hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          aria-expanded={open}
          aria-controls={`research-module-${moduleId}-body`}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? AUTHORED_WORDING.hideDetails : AUTHORED_WORDING.showDetails}
        </button>
      </header>
      {open && (
        <div id={`research-module-${moduleId}-body`} className="mt-2 space-y-2">
          {Object.keys(container.fields).length > 0 && (
            <div className="overflow-x-auto">
              <FieldTable moduleId={moduleId} container={container} labels={labels} sentences={sentences} />
            </div>
          )}
          <BandBlock container={container} sentences={sentences} />
          {notes.assumptions.length > 0 && (
            <ul className="ml-4 list-disc text-[10px] leading-4 text-slate-400">
              {notes.assumptions.map((a, i) => (typeof a.value === "string" ? <li key={i}>{a.value}</li> : null))}
            </ul>
          )}
          {container.servedDifferences.length > 0 && (
            <div data-testid={`research-differences-${moduleId}`}>
              <h6 className="text-[10px] font-semibold uppercase tracking-wide text-slate-300">{AUTHORED_WORDING.differencesHeading}</h6>
              <ul className="ml-4 list-disc text-[11px] leading-4 text-slate-300">
                {container.servedDifferences.map((d) => (
                  <li key={d.id}>{renderServedDifference(d, differenceContext)}</li>
                ))}
              </ul>
            </div>
          )}
          <details className="text-[10px] text-slate-300">
            <summary className="cursor-pointer">{AUTHORED_WORDING.inputProvenanceHeading}</summary>
            <div className="mt-1 overflow-x-auto"><InputProvenanceTable container={container} /></div>
          </details>
          <ExactValues moduleId={moduleId} container={container} />
        </div>
      )}
    </section>
  );
}
