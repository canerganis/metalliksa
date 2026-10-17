import React from "react";
import { Activity } from "lucide-react";
import { EstimateWarnings } from "../SolidificationEstimates";
import { estimateLine } from "../../utils/solidificationEstimateDisplay";
import { checkedEstimateContainer } from "../../data/quantityEnvelope";
import { UNAVAILABLE_TEXT } from "../../utils/hardnessConversion";
import {
  type BuildJobKineticsLike,
  buildJobCctRow,
  buildJobKineticsAvailability,
  buildJobMartensiteText,
  coolingIntervalText,
  kineticsHardnessText,
} from "../../utils/kineticsHardnessDisplay";

// Phase-transformation kinetics of an LPBF build job (python/lpbf_build_job_solver.py build_job_kinetics). Python
// decides availability, the CCT row for the build cooling rate and whether a martensite fraction / verdict may be
// reported; this panel only displays those decisions. Anything withheld shows "Unavailable" with Python's reason.

const KineticsMetric: React.FC<{ label: string; value: string; hint?: string }> = ({ label, value, hint }) => (
  <div className="rounded-lg border px-2 py-1.5 border-[#162032] bg-[#060a12]" data-kinetics-metric={label}>
    <div className="text-[9px] text-slate-500 uppercase">{label}</div>
    <div className="text-[12px] text-white font-bold truncate">{value}</div>
    {hint && <div className="text-[9px] text-slate-500">{hint}</div>}
  </div>
);

/** Python reasons have no final period; add one for display. */
const sentence = (text: string): string => (/[.!?]$/.test(text) ? text : `${text}.`);

const ESTIMATE_ORDER = ["pathCoolingRate", "kmAlphaMFraction", "tiMartensiteDissolution", "phaseTransformation"];

/** Estimate quantities of the build-job kinetics block (python/lpbf_kinetics_estimates.py); Python owns every number and sentence. */
const KineticsEstimates: React.FC<{ kinetics: BuildJobKineticsLike }> = ({ kinetics }) => {
  const raw = kinetics.estimates;
  if (!raw) return null;
  let container;
  try {
    container = checkedEstimateContainer(raw);
  } catch (e) {
    return (
      <p role="status" className="text-[9px] text-slate-400" data-kinetics-line="estimates-rejected">
        Estimate payload rejected: {e instanceof Error ? e.message : String(e)}
      </p>
    );
  }
  const names = Object.keys(container.quantities);
  const ordered = [...ESTIMATE_ORDER.filter((n) => names.includes(n)), ...names.filter((n) => !ESTIMATE_ORDER.includes(n))];
  const interval = coolingIntervalText(raw.coolingInterval);
  return (
    <div className="space-y-2" data-kinetics-estimates>
      {interval && <p className="text-[10px] text-slate-300" data-kinetics-line="interval">{interval}</p>}
      <dl className="grid gap-2 text-[11px]">
        {ordered.map((name) => {
          const line = estimateLine(name, container.quantities[name]);
          return (
            <div key={name} data-quantity={name} className="border-b border-slate-700/50 pb-2">
              <dt className="flex flex-wrap items-center gap-2 text-slate-400">
                <span>{line.label}</span>
                <span data-estimate-tier={line.tier} className="rounded border border-slate-500/50 px-1.5 py-0.5 text-[9px] text-slate-200">
                  {line.tierLabel}
                </span>
              </dt>
              {line.value !== null && <dd className="break-words text-white font-bold">{line.value}</dd>}
              <EstimateWarnings warnings={line.warnings} />
              {line.text && <dd className="break-words text-slate-300">{line.text}</dd>}
            </div>
          );
        })}
      </dl>
    </div>
  );
};

export const BuildJobKineticsPanel: React.FC<{ kinetics: BuildJobKineticsLike | null | undefined }> = ({ kinetics }) => {
  if (!kinetics) return null;
  if (kinetics.estimates) {
    // Estimate-channel block: no CCT row and no steel martensite numbers. Unavailable status shows Python's reason.
    const reason = kinetics.status === "unavailable" ? buildJobKineticsAvailability(kinetics).reason : "";
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-rose-400" />
          <h3 className="text-xs font-bold text-white">Phase Transformation Kinetics</h3>
        </div>
        {reason && <p className="text-[9px] text-slate-400" data-kinetics-line="reason">{reason}</p>}
        <KineticsEstimates kinetics={kinetics} />
      </div>
    );
  }
  const availability = buildJobKineticsAvailability(kinetics);
  const cct = buildJobCctRow(kinetics);
  const hardness = kineticsHardnessText(cct.row);
  const martensite = buildJobMartensiteText(kinetics);
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Activity className="w-4 h-4 text-rose-400" />
        <h3 className="text-xs font-bold text-white">Phase Transformation Kinetics</h3>
      </div>
      {availability.available ? (
        <>
          <div className="grid grid-cols-2 gap-2">
            <KineticsMetric
              label="Primary Phase"
              value={cct.row?.primaryMicrostructure || UNAVAILABLE_TEXT}
              hint={
                !cct.row
                  ? "No CCT row selected"
                  : cct.row.primaryMicrostructure
                    ? "From the CCT row below"
                    : sentence(cct.row.unavailableReason || "No primary phase in the CCT row")
              }
            />
            <KineticsMetric label="Martensite" value={martensite.value} hint={martensite.hint} />
            <KineticsMetric
              label="Hardness (HRC)"
              value={hardness.hrcValue}
              hint={cct.row ? "Predicted at RT" : "No CCT row selected"}
            />
            <KineticsMetric
              label="Hardness (HV)"
              value={hardness.hvValue}
              hint={
                !cct.row
                  ? "No CCT row selected"
                  : hardness.hvValue === UNAVAILABLE_TEXT
                    ? "No verified HV conversion"
                    : "ASTM E140 from HRC"
              }
            />
          </div>
          <p className="text-[9px] text-slate-400 mt-1" data-kinetics-line="cct">{cct.label}</p>
          {martensite.verdict ? (
            <p className="text-[9px] text-slate-500 mt-1" data-kinetics-line="verdict">{martensite.verdict}</p>
          ) : (
            <p className="text-[9px] text-slate-400 mt-1" data-kinetics-line="martensite">
              Martensite and verdict: {martensite.reason}
            </p>
          )}
        </>
      ) : (
        <>
          <KineticsMetric label="Kinetics" value={UNAVAILABLE_TEXT} hint="Reason below" />
          <p className="text-[9px] text-slate-400 mt-1" data-kinetics-line="reason">{availability.reason}</p>
        </>
      )}
    </div>
  );
};
