/**
 * User-visible strings of the Research model panel that TypeScript renders itself.
 *
 * Two groups, kept apart on purpose:
 *  - APPROVED_WORDING: the maintainer-approved top 25 (WORDING_TOP25_2026-10-15.md), used exactly as written.
 *  - AUTHORED_WORDING: strings written for the panel states and controls (contract 4.2, 4.3, 4.7, 13.8; W-1 drafts
 *    with no maintainer approval yet). Each one is listed for lead review; none may use a dash as punctuation, a hype
 *    word, or any claim of validation.
 * Every other string on screen comes from the describe text tables or from the response itself (labels, sentences,
 * band captions, served-difference templates), so Python stays the one author of research wording.
 */

export const APPROVED_WORDING = {
  /** 1  W1-4.2-2.1 */ panelTitle: "Research model",
  /** 2  W1-visible-1 */ badgeResearch: "Research",
  /** 3  W1-visible-2 */ badgeScreeningOnly: "Screening only",
  /** 4  W1-visible-3 */ badgeNoValidation: "No experimental validation",
  /** 5  W1-4.2-3.1 */ scopeLine: "Separate from the served result. Research values never change the served tiles, verdict or exports.",
  /** 6  Q1-2.2-25 */ researchArmLabel: "Literature estimate / Research / not validated",
  /** 7  W1-visible-5 */ supportLiterature: "Literature estimate",
  /** 8  W1-visible-6 */ supportUserInput: "User input: {weakestInputs}",
  /** 9  W1-visible-7 */ supportUnresolved: "Unresolved: {weakestInputs}",
  /** 10 SENTENCES.bandCaption (Python is the source; this copy pins it) */
  bandCaption:
    "Min / nominal / max is an envelope of named one-at-a-time scenarios. Interactions are not evaluated. It is not a confidence interval, an error bar, or a physical lower or upper bound.",
  /** 23 SENTENCES.refusal.KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE, as written in the approved list */
  refusalKeyholeThermalFlow: "Not available: no source-bound closure or data exists for the keyhole thermal flow.",
} as const;

export const AUTHORED_WORDING = {
  runButton: "Run research models",
  cancelButton: "Cancel",
  retryButton: "Retry",
  checkingInputs: "Checking inputs",
  inputsReady: "Inputs checked.",
  idleHint: "Press Run research models to compute the nominal values and the scenario range.",
  runningNominal: "Computing nominal values.",
  bandPending: "Computing scenario range: {armsDone} of {armsTotal}.",
  cancelled: "Scenario range not computed (cancelled). Run research models to compute it.",
  stale: "Inputs changed. Run research models to update.",
  complete: "Research models computed.",
  staticDemo: "Research models need the local engine; the static demo has no recorded research result.",
  describeFailed: "The inputs could not be checked: {reason}",
  errorPrefix: "The research request failed: {reason}",
  errorGeneric: "The research request failed ({code}). The served result is not affected.",
  errorNetwork: "The local engine could not be reached ({message}). The served result is not affected.",
  errorMalformed: "The research response did not match the expected schema and was not used.",
  inputsHeading: "Inputs",
  inputsHelp: "Each input shows its provenance. Reset returns it to the value the model follows or the sourced default.",
  presetClearedNote: "Vapour ranges and overrides were cleared because the preset changed.",
  rangeLabel: "Scenario range",
  rangeMin: "min",
  rangeMax: "max",
  valueLabel: "Value",
  unitLabel: "Unit",
  differencesHeading: "Differences from the served result",
  inputProvenanceHeading: "Inputs and provenance",
  scenarioSupportHeading: "Scenario support",
  fieldsHeading: "Fields",
  exactValues: "Exact values",
  colField: "Field",
  colNominal: "Nominal",
  colMin: "Min",
  colMax: "Max",
  colSupport: "Source support",
  colInput: "Input",
  colKind: "Provenance",
  colSource: "Source",
  colPhase: "Phase",
  colRefTemp: "Reference temperature",
  colRange: "Source range",
  sourceRangeNotEstablished: "source range not established",
  notComputed: "n/a",
  namedScenarios: "{n} named scenarios.",
  bandDegenerate: "Unchanged in every declared scenario; this is not a known zero uncertainty.",
  bandExtremes: "Lowest: {min}. Highest: {max}.",
  bandTieLowest: "{k} scenarios share the lowest value.",
  bandTieHighest: "{k} scenarios share the highest value.",
  bandPartial: "{f} of {n} scenarios did not compute and are not in this range:",
  bandUnavailable: "No scenario computed; no range is shown.",
  scopeFootnote: "Request key {requestKey}. Research implementation {impl}. Cache: {hit} hits, {computed} computed.",
  channelAdhoc: "The persistent engine was not used for this request, so no scenario cache was kept.",
  showDetails: "Show details",
  hideDetails: "Hide details",
  moduleNotApplicable: "Not applicable to this alloy.",
  modulePending: "Waiting for the scenario range.",
} as const;

export type AuthoredWordingKey = keyof typeof AUTHORED_WORDING;

export function fill(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => (key in values ? String(values[key]) : match));
}

export function supportText(kind: "Literature estimate" | "User input" | "Unresolved" | null, weakestInputs: readonly string[]): string | null {
  if (kind === "Literature estimate") return APPROVED_WORDING.supportLiterature;
  if ((kind === "User input" || kind === "Unresolved") && weakestInputs.length === 0) return kind;
  if (kind === "User input") return fill(APPROVED_WORDING.supportUserInput, { weakestInputs: weakestInputs.join(", ") });
  if (kind === "Unresolved") return fill(APPROVED_WORDING.supportUnresolved, { weakestInputs: weakestInputs.join(", ") });
  return null;
}
