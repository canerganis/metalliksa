// Display text for the kinetics solver's predicted hardness (python/kinetics_ttt_cct_solver.py, CCT map rows).
// predictedHardness_HV is an ASTM E140 Table 1 conversion of the predicted HRC for non-austenitic steels only; it is
// null for other alloy classes and outside HRC 20-68. A missing or null value is shown as "Unavailable", never as an
// invented number.
import { UNAVAILABLE_TEXT } from "./hardnessConversion";

export interface KineticsHardnessRow {
  predictedHardness_HRC?: number | null;
  predictedHardness_HV?: number | null;
  predictedHardness_HV_status?: string | null;
  predictedHardness_HRC_status?: string | null;
}

export const KINETICS_HV_STATUS_NOTES: Readonly<Record<string, string>> = {
  "converted-astm-e140-table1":
    "HV converted from the predicted HRC per ASTM E140 Table 1 (non-austenitic steels); approximate, not measured.",
  "unavailable-outside-e140-table1-hrc-20-68":
    "HV unavailable: the predicted HRC is outside the ASTM E140 Table 1 range (HRC 20-68).",
  "unavailable-no-verified-table-for-alloy-class":
    "HV unavailable: no verified HRC-HV conversion table for this alloy class.",
  "unavailable-no-predicted-hrc": "HV unavailable: no hardness is predicted (the Li model does not compute hardness).",
};

const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

// Status codes of the kinetics solver (python/kinetics_ttt_cct_solver.py, Li et al. 1998 model). The model is
// reported only for a steel inside the Li composition range; other alloys get null values with the reason
// ("kinetics model is steel-only" or "composition outside the Li (1998) model range: ...").
export const KINETICS_STATUS_NOTES: Readonly<Record<string, string>> = {
  "unavailable-kinetics-model-steel-only": "Unavailable: kinetics model is steel-only.",
  "unavailable-composition-outside-li-model-range":
    "Unavailable: the composition is outside the range stated for the Li (1998) model.",
  "unavailable-austenitizing-at-or-below-ae3":
    "Unavailable: the austenitizing temperature is at or below the Grange Ae3 (the model assumes a fully austenitic start).",
  "unavailable-fractions-not-computed":
    "Unavailable: phase fractions and hardness are not computed (the Li model needs equilibrium ferrite/pearlite amounts from a thermodynamic model that is not implemented).",
  "unavailable-not-modelled": "Unavailable: not modelled.",
  "generic-constants-illustrative":
    "Generic constants shared by every alloy (only the activation energy is per alloy); illustrative.",
  "registry-screening-value": "Registry screening value (unsourced); not a measured or computed temperature.",
  "unavailable-registry-placeholder": "Unavailable: the registry value is a non-physical placeholder.",
  "athermal-martensite-no-diffusional-start-above-ms": "No diffusional start above Ms; the martensite start is Ms.",
  "li1998-additivity-first-diffusional-start":
    "First 1 % diffusional start by the additivity rule on the Li (1998) start curves; unvalidated screening value.",
  "li1998-additivity-screening": "Li (1998) model with the additivity rule; unvalidated screening value.",
  "computed-grange-1961-screening": "Grange (1961) equation from the composition; screening value.",
  "computed-li-1998-screening": "Li et al. (1998) bainite-start equation from the composition; screening value.",
  "computed-andrews-kung-rayment-1982-screening":
    "Andrews linear Ms equation with the Kung-Rayment (1982) terms, from the composition; screening value.",
  "no-floor-li-1998-law": "The Li (1998) start-time law has no time floor.",
  "static-text-not-a-calphad-calculation": "Fixed steel text; no equilibrium (CALPHAD) calculation is performed.",
};

/** "855 °C" / "98%" for a finite number, else "Unavailable"; never "null", "NaN" or "undefined". */
export const kineticsValueText = (v: unknown, unit = ""): string => (finite(v) ? `${v}${unit}` : UNAVAILABLE_TEXT);

/** A solver string (label, text) or "Unavailable" when it is null or empty. */
export const kineticsLabelText = (v: unknown): string => (typeof v === "string" && v.trim() ? v : UNAVAILABLE_TEXT);

/** Human note for a solver status code; "" for unknown or missing codes. */
export const kineticsStatusNote = (status: unknown): string =>
  typeof status === "string" ? KINETICS_STATUS_NOTES[status] ?? "" : "";

export interface KineticsHardnessText {
  /** "58" or "Unavailable" (bare value, e.g. for a metric tile labelled "Hardness (HRC)") */
  hrcValue: string;
  /** "653" or "Unavailable" */
  hvValue: string;
  /** "58 HRC" or "HRC: Unavailable" */
  hrc: string;
  /** "653 HV" or "HV: Unavailable" */
  hv: string;
  /** Why the HV is (un)available, from the solver status; "" when no row was given. */
  note: string;
}

export function kineticsHardnessText(row: KineticsHardnessRow | null | undefined): KineticsHardnessText {
  const hrc = row?.predictedHardness_HRC;
  const hv = row?.predictedHardness_HV;
  const status = row?.predictedHardness_HV_status ?? "";
  return {
    hrcValue: finite(hrc) ? String(hrc) : UNAVAILABLE_TEXT,
    hvValue: finite(hv) ? String(hv) : UNAVAILABLE_TEXT,
    hrc: finite(hrc) ? `${hrc} HRC` : `HRC: ${UNAVAILABLE_TEXT}`,
    hv: finite(hv) ? `${hv} HV` : `HV: ${UNAVAILABLE_TEXT}`,
    note: finite(hrc)
      ? KINETICS_HV_STATUS_NOTES[status] ?? (row && !finite(hv) ? "HV unavailable." : "")
      : kineticsStatusNote(row?.predictedHardness_HRC_status) ||
        (KINETICS_HV_STATUS_NOTES[status] ?? (row && !finite(hv) ? "HV unavailable." : "")),
  };
}

// ---------------------------------------------------------------------------------------------------------------
// Phase Kinetics Studio: CCT rows, phase fractions, model status (python/kinetics_ttt_cct_solver.py).

/**
 * The verdict sentence under the CALPHAD-vs-kinetics tab: only the mechanism the solver's verdict supports
 * (python/kinetics_ttt_cct_solver.py: "No diffusional start above Ms ..." or "<Phase> start at T C ...").
 */
export function kineticsVerdictSentence(
  verdict: unknown,
  coolingRate: number,
  modelAvailable: boolean,
  unavailableReason = "kinetics model is steel-only"
): string {
  if (!modelAvailable) return `Unavailable: ${sentence(unavailableReason || "kinetics model unavailable")}`;
  const rate = finite(coolingRate) ? `${coolingRate} °C/s` : "the selected cooling rate";
  if (typeof verdict !== "string") return "";
  if (verdict.startsWith("No diffusional start")) {
    return `At ${rate}, no ferrite, pearlite or bainite start is reached above Ms in the Li (1998) additivity model; the austenite transforms athermally (martensite).`;
  }
  const m = /^(Ferrite|Pearlite|Bainite) start at /.exec(verdict);
  if (m) {
    return `At ${rate}, the Li (1998) additivity model reaches a ${m[1].toLowerCase()} start above Ms; the phase fractions are not computed.`;
  }
  return "";
}

export interface TttPointLike {
  temperature_C?: number | null;
  phase?: string | null;
  tStart_s?: number | null;
}

/**
 * "Ferrite 607 °C (82 s) / Bainite 464 °C (4.6 s)": the solver point with the shortest 1 % start time per phase (the
 * nose of the listed C-curve, a selection of Python's points, not a new calculation); "" when there are no points.
 */
export function kineticsNoseText(points: TttPointLike[] | null | undefined): string {
  const best = new Map<string, { t: number; s: number }>();
  for (const p of points ?? []) {
    if (typeof p?.phase !== "string" || !finite(p.temperature_C) || !finite(p.tStart_s)) continue;
    const prev = best.get(p.phase);
    if (!prev || p.tStart_s < prev.s) best.set(p.phase, { t: p.temperature_C, s: p.tStart_s });
  }
  return [...best.entries()]
    .map(([phase, v]) => `${phase} ${Math.round(v.t)} °C (${Number(v.s.toPrecision(2))} s)`)
    .join(" / ");
}

export interface PhaseStartsLike {
  phaseStartTemps_C?: { Ferrite?: number | null; Pearlite?: number | null; Bainite?: number | null } | null;
}

/** "F 721.3 / P 691.9 / B 531.6 °C" with "-" for a phase not reached above Ms; "Unavailable" without data. */
export function kineticsPhaseStartsText(row: PhaseStartsLike | null | undefined): string {
  const starts = row?.phaseStartTemps_C;
  if (!starts) return UNAVAILABLE_TEXT;
  const cell = (v: unknown) => (finite(v) ? String(v) : "-");
  return `F ${cell(starts.Ferrite)} / P ${cell(starts.Pearlite)} / B ${cell(starts.Bainite)} °C`;
}

export interface LswRowLike {
  meanRadius_nm?: number | null;
  precipitationHardening_MPa?: number | null;
  strengtheningMechanism?: string | null;
  status?: string | null;
  /** Machine-readable reasons of an unavailable row; the sentence for each code is not written here. */
  reasonCodes?: readonly string[] | null;
}

export interface LswBlockLike {
  status?: string | null;
  reason?: string | null;
  reasonCodes?: readonly string[] | null;
}

/**
 * Whether any LSW row has a radius; otherwise the solver's reason. The solver returns no radius, strength or
 * mechanism for any alloy (python/kinetics_ttt_cct_solver.py, SOL-K): the reason is its sentence when it gives one
 * (aging at or above the registry solvus), else the note of its status.
 */
export function kineticsLswAvailability(
  rows: LswRowLike[] | null | undefined,
  block: LswBlockLike | null | undefined
): { available: boolean; reason: string } {
  if ((rows ?? []).some((r) => finite(r?.meanRadius_nm))) return { available: true, reason: "" };
  return {
    available: false,
    reason: sentence(block?.reason || kineticsStatusNote(block?.status) || "No LSW coarsening profile was computed"),
  };
}

export interface KineticsCctRowLike extends KineticsHardnessRow {
  transformedStartTemp_C?: number | null;
  transformedStartTime_s?: number | null;
  primaryMicrostructure?: string | null;
  phaseFractions?: {
    Martensite_pct?: number | null;
    Bainite_pct?: number | null;
    Pearlite_Ferrite_pct?: number | null;
    RetainedAustenite_pct?: number | null;
  } | null;
  transformedStart_status?: string | null;
  phaseFractions_status?: string | null;
  unavailableReason?: string | null;
}

export interface KineticsCctRowText {
  startTemp: string;
  startTime: string;
  microstructure: string;
  martensite: string;
  /** Why the start columns are unavailable ("" when they are shown). */
  startNote: string;
  /** Why the phase fractions are unavailable, or the lookup caveat for steels. */
  fractionsNote: string;
}

export function kineticsCctRowText(row: KineticsCctRowLike | null | undefined): KineticsCctRowText {
  const startAvailable = finite(row?.transformedStartTemp_C);
  const martensite = row?.phaseFractions?.Martensite_pct;
  return {
    startTemp: kineticsValueText(row?.transformedStartTemp_C, " °C"),
    startTime: kineticsValueText(row?.transformedStartTime_s, " s"),
    microstructure: kineticsLabelText(row?.primaryMicrostructure),
    martensite: kineticsValueText(martensite, "%"),
    startNote: startAvailable ? "" : kineticsStatusNote(row?.transformedStart_status) || "Unavailable.",
    fractionsNote: finite(martensite)
      ? kineticsStatusNote(row?.phaseFractions_status)
      : kineticsStatusNote(row?.phaseFractions_status) || "Unavailable.",
  };
}

export interface KineticsPhaseSlice {
  name: string;
  value: number;
  key: "Martensite" | "Bainite" | "Pearlite_Ferrite" | "RetainedAustenite";
}

/** Pie slices for a CCT row: only finite fractions above zero; `reason` is set when none are available. */
export function kineticsPhaseSlices(row: KineticsCctRowLike | null | undefined): { slices: KineticsPhaseSlice[]; reason: string } {
  const pf = row?.phaseFractions;
  const all: Array<[KineticsPhaseSlice["key"], string, unknown]> = [
    ["Martensite", "Martensite", pf?.Martensite_pct],
    ["Bainite", "Bainite", pf?.Bainite_pct],
    ["Pearlite_Ferrite", "Pearlite / Ferrite", pf?.Pearlite_Ferrite_pct],
    ["RetainedAustenite", "Retained Austenite", pf?.RetainedAustenite_pct],
  ];
  if (!all.some(([, , v]) => finite(v))) {
    return { slices: [], reason: kineticsStatusNote(row?.phaseFractions_status) || "Phase fractions unavailable." };
  }
  return {
    slices: all.flatMap(([key, name, v]) => (finite(v) && v > 0 ? [{ key, name, value: v }] : [])),
    reason: "",
  };
}

export interface KineticsModelLike {
  status?: string | null;
  reason?: string | null;
  note?: string | null;
  validationStatus?: string | null;
  evidenceLevel?: string | null;
  validityDomain?: {
    status?: string | null;
    unchecked?: string[] | null;
    grainSize?: { astmG?: number | null; comparedRange_G?: number[] | null; insideComparedRange?: boolean | null } | null;
  } | null;
}
export interface TttIncubationFloorLike {
  status?: string | null;
  pointCount?: number | null;
  floorHitCount?: number | null;
  floorValue_s?: number | null;
}

export interface KineticsModelBanner {
  available: boolean;
  /** Headline when available: the model name with its evidence level and validation status. */
  headline: string;
  /** Headline: the reason when unavailable, else "" */
  reason: string;
  /** The solver's caution about the model (illustrative steel template, or why non-steels are refused). */
  caution: string;
  /** "32 of 40 TTT points are on the 1 ms incubation floor" or null. */
  floorLine: string | null;
  /** Applicability caveats of an available model: unchecked bounds, grain size outside the compared span. */
  validityLines: string[];
}

export function kineticsModelBanner(
  model: KineticsModelLike | null | undefined,
  floor: TttIncubationFloorLike | null | undefined
): KineticsModelBanner {
  const available = model?.status === "available";
  const hits = floor?.floorHitCount;
  const count = floor?.pointCount;
  const labels = [model?.evidenceLevel, model?.validationStatus].filter((v): v is string => typeof v === "string" && !!v);
  const domain = model?.validityDomain;
  const validityLines: string[] = [];
  if (available && domain) {
    if (domain.status === "inside-partially-checked") {
      for (const u of domain.unchecked ?? []) validityLines.push(`Validity range only partially checked: ${sentence(u)}`);
    }
    const g = domain.grainSize;
    if (g && g.insideComparedRange === false && finite(g.astmG) && Array.isArray(g.comparedRange_G)) {
      validityLines.push(
        `Grain size ASTM G ${g.astmG} is outside the span of the published comparisons (G ${g.comparedRange_G.join("-")}).`
      );
    }
  }
  return {
    available,
    headline: available ? `Li et al. (1998) TTT/CCT model${labels.length ? ` (${labels.join(", ")})` : ""}.` : "",
    reason: available ? "" : sentence(model?.reason || "Kinetics model unavailable"),
    caution: typeof model?.note === "string" ? model.note : "",
    validityLines,
    floorLine:
      finite(hits) && finite(count) && hits > 0
        ? `${hits} of ${count} TTT points are on the ${floor?.floorValue_s ?? 0.001} s incubation floor (floorHit): ` +
          "their start time is the floor, not a model value."
        : null,
  };
}

// ---------------------------------------------------------------------------------------------------------------
// LPBF build-job kinetics block (python/lpbf_build_job_solver.py build_job_kinetics). Python decides everything
// here; the UI only displays it. `status` is the field to trust ("available" / "unavailable"); `success: false` on
// an unavailable block is a legacy envelope shape, not a failed build job. Unavailable cases: alloys without a
// kinetics model of their own (316L, AlSi10Mg; never a substituted alloy), no finite build cooling rate, and the
// 1 K/s floor of a degenerate solidification front.

export interface BuildJobCctRow extends KineticsHardnessRow {
  coolingRate_C_s?: number | null;
  primaryMicrostructure?: string | null;
  /** Why the start/primary phase of a (steel) row is null, e.g. "incubation law has no Ae3 asymptote; ...". */
  unavailableReason?: string | null;
}

/** Python's choice of CCT row for the build cooling rate (lpbf_build_job_solver.build_cooling_rate_cct_row). */
export interface BuildCoolingRateCctRow {
  status?: string | null;
  reason?: string | null;
  rowIndex?: number | null;
  rowCoolingRate_C_s?: number | null;
  buildCoolingRate_C_s?: number | null;
  mapRange_C_s?: [number, number] | null;
}

/** Martensite fraction / verdict at the build rate (lpbf_build_job_solver.build_rate_martensite). */
export interface BuildRateMartensite {
  status?: string | null;
  reason?: string | null;
  predictedMartensite_pct?: number | null;
  verdict?: string | null;
  coolingRate_C_s?: number | null;
}

export interface BuildJobKineticsLike {
  status?: string | null;
  reason?: string | null;
  buildCoolingRate_C_s?: number | null;
  buildCoolingRateCctRow?: BuildCoolingRateCctRow | null;
  buildRateMartensite?: BuildRateMartensite | null;
  cctContinuousCoolingMap?: BuildJobCctRow[] | null;
}

/** Python reasons have no final period; add one for display. */
const sentence = (text: string): string => (/[.!?]$/.test(text) ? text : `${text}.`);

/** Whether the build-job kinetics block holds a computed result; otherwise the reason it is unavailable. */
export function buildJobKineticsAvailability(
  kinetics: BuildJobKineticsLike | null | undefined
): { available: boolean; reason: string } {
  if (!kinetics) return { available: false, reason: "No kinetics block in the build-job result." };
  if (kinetics.status !== "available") {
    return { available: false, reason: sentence(kinetics.reason || "Kinetics unavailable for this build") };
  }
  return { available: true, reason: "" };
}

/** "0.05", "2000", "30.1", "1.09e+6": at most 3-4 significant digits, never a long float. */
export function formatCoolingRate(rate: number): string {
  return Math.abs(rate) >= 1e4 ? rate.toExponential(2) : String(Number(rate.toPrecision(4)));
}

export interface BuildJobCctRowSelection {
  /** The CCT map row the solver selected for the build cooling rate, or null. */
  row: BuildJobCctRow | null;
  /** Which cooling rate the row corresponds to, or why no row is shown. */
  label: string;
}

/**
 * The CCT row the Python build job selected (nearest on a log scale to the build cooling rate, never extrapolated
 * beyond the tabulated rates). The UI does not re-select; a selection that does not match its map row is not
 * trusted. Without a selected row the tiles show "Unavailable".
 */
export function buildJobCctRow(kinetics: BuildJobKineticsLike | null | undefined): BuildJobCctRowSelection {
  const sel = kinetics?.buildCoolingRateCctRow;
  const map = kinetics?.cctContinuousCoolingMap;
  const index = sel?.rowIndex;
  if (sel?.status === "selected" && Number.isSafeInteger(index) && Array.isArray(map)) {
    const row = map[index as number];
    if (
      row &&
      finite(row.coolingRate_C_s) &&
      row.coolingRate_C_s === sel.rowCoolingRate_C_s &&
      finite(sel.buildCoolingRate_C_s)
    ) {
      return {
        row,
        label:
          `CCT row ${formatCoolingRate(row.coolingRate_C_s)} °C/s (nearest on a log scale to the build ` +
          `cooling rate ${formatCoolingRate(sel.buildCoolingRate_C_s)} °C/s).`,
      };
    }
  }
  return { row: null, label: `No CCT row: ${sentence(sel?.reason || "the solver selected no row for the build cooling rate")}` };
}

export interface BuildJobMartensiteText {
  /** "12.5%" or "Unavailable"; never "null%". */
  value: string;
  /** Martensite-based verdict, or null when withheld. */
  verdict: string | null;
  /** Why the fraction / verdict is withheld; "" when shown. */
  reason: string;
  /** "At build rate 30 °C/s" when shown. */
  hint: string;
}

/** Martensite tile text from Python's buildRateMartensite; the raw calphadVsKineticsGap is never read here. */
export function buildJobMartensiteText(kinetics: BuildJobKineticsLike | null | undefined): BuildJobMartensiteText {
  const m = kinetics?.buildRateMartensite;
  if (m?.status === "available" && finite(m.predictedMartensite_pct)) {
    return {
      value: `${m.predictedMartensite_pct}%`,
      verdict: m.verdict || null,
      reason: "",
      hint: finite(m.coolingRate_C_s) ? `At build rate ${formatCoolingRate(m.coolingRate_C_s)} °C/s` : "At build rate",
    };
  }
  return {
    value: UNAVAILABLE_TEXT,
    verdict: null,
    reason: sentence(m?.reason || "no martensite fraction for the build cooling rate"),
    hint: "Reason below",
  };
}
