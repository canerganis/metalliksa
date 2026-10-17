/**
 * Machine calibration (user data): typed, read-only view of what the Python side serves.
 *
 * Python is the authority (python/lpbf_machine_calibration.py, python/lpbf_machine_calibrated_meltpool.py). This module
 * validates the shape of the status and result documents and derives display text. It fits nothing, gates nothing and
 * never decides a label: the evidence badge is a pure function of the fields the backend returned, and anything that is
 * not an explicit served-and-complete cell falls back to "Screening only". Nothing here says "validated"; the fit is an
 * empirical machine offset on the user's own tracks, not an absorptivity and not a physical quantity.
 */

export const MACHINE_EVIDENCE_CALIBRATED = "calibrated-simulation";
export const MACHINE_EVIDENCE_SCREENING = "screening-only";
export const MACHINE_SCOPE_TEXT = "this machine, user data";
export const MACHINE_SECTION_TITLE = "Machine calibration (user data)";
export const MACHINE_BAND_SENTENCE = "80 % of your own held-out tracks fell inside a band like this in the simulation on published sources; it is not a tolerance.";
export const MACHINE_PRIVACY_SENTENCE = "Your measurements stay on this computer (.runtime/machine-calibration/), are not sent anywhere, do not change the published-track calibration or the scorecard, and do not become validation evidence.";
export const MACHINE_OFFSET_SENTENCE = "Empirical machine offset fitted to your own tracks. It is not an absorptivity and not a physical quantity; it absorbs model error.";
export const MACHINE_VERDICT_SENTENCE = "The Build Job verdict never uses this depth; it is reported next to the screening value.";
export const MACHINE_BADGE_CALIBRATED = "Calibrated simulation · this machine, user data";
export const MACHINE_BADGE_SCREENING = "Screening only";

export const METHOD_FIELD_LABELS: Readonly<Record<string, string>> = {
  depthDatum: "depth datum",
  beamDiameterDefinition: "beam diameter definition",
  measuredPowerW: "measured laser power",
  crossSectionLocation: "cross-section location",
  replicates: "replicates",
};

export type MachineCellStatus = "served" | "refused" | "not-eligible";

export interface MachineCellSummary {
  readonly kernel: string;
  readonly quantity: string;
  readonly status: MachineCellStatus;
  readonly evidenceKind: string;
  readonly evidenceScope: string | null;
  readonly evidenceLabel: string;
  readonly missingMethodFields: readonly string[];
  readonly reasonText: readonly string[];
}

export interface MachineArtefactSummary {
  readonly machineCalibrationId: string;
  readonly userSourceId: string;
  readonly contentSha256: string | null;
  readonly material: string;
  readonly generatedAt: string;
  readonly nTracks: number;
  readonly state: "ready";
  readonly cells: readonly MachineCellSummary[];
}

export interface MachineCalibrationStatus {
  readonly artefacts: readonly MachineArtefactSummary[];
  readonly skipped: number;
}

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const strArray = (v: unknown): string[] => Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];

const METHOD_FIELD_ORDER = ["depthDatum", "beamDiameterDefinition", "measuredPowerW", "crossSectionLocation", "replicates"];

/**
 * Backend shape: a list of {trackIds, fields} objects (plain strings are also accepted). Returns the de-duplicated union
 * of field names, declared fields first in their declared order, then any unknown names in first-seen order.
 */
export function parseMissingMethodFields(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  const seen = new Set<string>();
  for (const item of v) {
    if (typeof item === "string") seen.add(item);
    else if (isObj(item)) for (const f of strArray(item.fields)) seen.add(f);
  }
  const known = METHOD_FIELD_ORDER.filter(f => seen.has(f));
  return [...known, ...[...seen].filter(f => !METHOD_FIELD_ORDER.includes(f))];
}

function summarizeCell(raw: unknown): MachineCellSummary | null {
  if (!isObj(raw)) return null;
  if (typeof raw.kernel !== "string" || typeof raw.quantity !== "string") return null;
  if (raw.status !== "served" && raw.status !== "refused" && raw.status !== "not-eligible") return null;
  return {
    kernel: raw.kernel, quantity: raw.quantity, status: raw.status,
    evidenceKind: typeof raw.evidenceKind === "string" ? raw.evidenceKind : MACHINE_EVIDENCE_SCREENING,
    evidenceScope: typeof raw.evidenceScope === "string" ? raw.evidenceScope : null,
    evidenceLabel: typeof raw.evidenceLabel === "string" ? raw.evidenceLabel : "",
    missingMethodFields: parseMissingMethodFields(raw.missingMethodFields),
    reasonText: strArray(raw.reasonText),
  };
}

/** Parse GET /api/python/lpbf-machine-calibration/status. Only "ready" artefacts are kept; anything malformed is dropped. */
export function parseMachineCalibrationStatus(raw: unknown): MachineCalibrationStatus {
  if (!isObj(raw) || raw.success !== true || !Array.isArray(raw.artefacts)) return { artefacts: [], skipped: 0 };
  const artefacts: MachineArtefactSummary[] = [];
  let skipped = 0;
  for (const a of raw.artefacts) {
    if (!isObj(a) || a.state !== "ready" || typeof a.machineCalibrationId !== "string" || !/^mc-[0-9a-f]{12}$/.test(a.machineCalibrationId)
      || typeof a.userSourceId !== "string" || typeof a.material !== "string" || !Array.isArray(a.cells)) { skipped += 1; continue; }
    artefacts.push({
      machineCalibrationId: a.machineCalibrationId, userSourceId: a.userSourceId,
      contentSha256: typeof a.contentSha256 === "string" ? a.contentSha256 : null,
      material: a.material, generatedAt: typeof a.generatedAt === "string" ? a.generatedAt : "",
      nTracks: typeof a.nTracks === "number" ? a.nTracks : 0, state: "ready",
      cells: a.cells.map(summarizeCell).filter((c): c is MachineCellSummary => c !== null),
    });
  }
  return { artefacts, skipped };
}

/** The ready artefacts fitted for this alloy. The selector is hidden when this is empty. */
export function artefactsForMaterial(status: MachineCalibrationStatus | null, material: string): readonly MachineArtefactSummary[] {
  return status ? status.artefacts.filter(a => a.material === material) : [];
}

export function depthCellFor(artefact: MachineArtefactSummary | undefined, kernel: string): MachineCellSummary | undefined {
  return artefact?.cells.find(c => c.kernel === kernel && c.quantity === "depth");
}

/** The machineCalibrated block of POST /api/python/lpbf-machine-calibrated-meltpool (and of a Build Job result). */
export interface MachineCalibratedBlock {
  readonly available: boolean;
  readonly machineCalibrationId?: string;
  readonly kernel?: string;
  readonly material?: string;
  readonly status?: MachineCellStatus;
  readonly depth_um: number | null;
  readonly depthBand_um: readonly [number, number] | null;
  readonly factor?: number;
  readonly bandNotInformative?: boolean;
  readonly evidenceKind: string;
  readonly evidenceScope: string | null;
  readonly evidenceLabel?: string;
  readonly missingMethodFields: readonly string[];
  readonly reasonText: readonly string[];
  readonly userTrackRangeNotes?: readonly string[];
  readonly userResidualSummary?: { readonly nTracks: number | null; readonly meanLnResidualDefault: number | null };
  readonly usedForBuildJobVerdict?: boolean;
  readonly screeningDepth_um?: number | null;
  readonly experimentalValidation?: boolean;
  /** Width is not calibrated for the machine; this sentence comes from the endpoint. */
  readonly widthText?: string;
}

export interface MachineCalibratedResult {
  readonly screening?: { readonly meltPoolGeometry?: { readonly depth_um?: number } } | null;
  readonly machineCalibrated: MachineCalibratedBlock;
  readonly experimentalValidation: boolean;
}

export function parseMachineCalibratedResult(raw: unknown): MachineCalibratedResult | null {
  if (!isObj(raw) || !isObj(raw.machineCalibrated)) return null;
  const b = raw.machineCalibrated;
  const band = Array.isArray(b.depthBand_um) && b.depthBand_um.length === 2 && b.depthBand_um.every(x => typeof x === "number" && Number.isFinite(x))
    ? ([b.depthBand_um[0] as number, b.depthBand_um[1] as number] as const) : null;
  const block: MachineCalibratedBlock = {
    ...(b as unknown as MachineCalibratedBlock),
    available: b.available === true,
    depth_um: typeof b.depth_um === "number" && Number.isFinite(b.depth_um) ? b.depth_um : null,
    depthBand_um: band,
    evidenceKind: typeof b.evidenceKind === "string" ? b.evidenceKind : MACHINE_EVIDENCE_SCREENING,
    evidenceScope: typeof b.evidenceScope === "string" ? b.evidenceScope : null,
    missingMethodFields: parseMissingMethodFields(b.missingMethodFields),
    reasonText: strArray(b.reasonText),
  };
  return { screening: isObj(raw.screening) ? (raw.screening as MachineCalibratedResult["screening"]) : null, machineCalibrated: block, experimentalValidation: false };
}

export function methodFieldText(fields: readonly string[]): string {
  return fields.map(f => METHOD_FIELD_LABELS[f] ?? f).join(", ");
}

/**
 * The evidence badge. "Calibrated simulation · this machine, user data" only for a served block that carries that kind
 * AND that scope AND no missing method field AND is not marked as validation. Everything else, including every refused
 * cell, is "Screening only". Never "validated".
 */
export function machineEvidenceBadge(b: Pick<MachineCalibratedBlock, "available" | "evidenceKind" | "evidenceScope" | "missingMethodFields" | "experimentalValidation">): string {
  const calibrated = b.available && b.evidenceKind === MACHINE_EVIDENCE_CALIBRATED && b.evidenceScope === MACHINE_SCOPE_TEXT
    && b.missingMethodFields.length === 0 && b.experimentalValidation !== true;
  return calibrated ? MACHINE_BADGE_CALIBRATED : MACHINE_BADGE_SCREENING;
}

export const isMachineCalibratedBadge = (badge: string): boolean => badge === MACHINE_BADGE_CALIBRATED;

function um(v: number): string { return `${v.toFixed(1)} µm`; }

/** One line for the Build Job W×D tile: the calibrated depth next to, never instead of, the screening value. */
export function machineTileLine(b: MachineCalibratedBlock | null | undefined, screeningDepth: number | null | undefined): string | null {
  if (!b || !b.available || b.depth_um === null) return null;
  const screening = screeningDepth ?? b.screeningDepth_um;
  return `Machine depth ${um(b.depth_um)}${screening !== null && screening !== undefined ? ` (screening ${um(screening)})` : ""} · ${machineEvidenceBadge(b)}`;
}

/** What the run report prints. Display only: it is not part of the hashed dossier. */
export interface MachineCalibrationReportInput {
  readonly artefact: MachineArtefactSummary;
  readonly kernel: string;
  readonly block: MachineCalibratedBlock;
  readonly screeningDepth_um: number | null;
}

export function machineReportLines(input: MachineCalibrationReportInput): ReadonlyArray<readonly [string, string]> {
  const { artefact, block } = input;
  const rows: Array<[string, string]> = [
    ["Machine calibration id", artefact.machineCalibrationId],
    ["Artefact SHA-256", artefact.contentSha256 ?? "not reported"],
    ["User source", artefact.userSourceId],
    ["Tracks fitted (m)", String(artefact.nTracks)],
    ["Cell", `${input.kernel} depth for ${artefact.material}: ${block.status ?? "unknown"}`],
    ["Evidence", `${machineEvidenceBadge(block)} (experimental validation: false)`],
  ];
  if (block.available && block.depth_um !== null) {
    rows.push(["Machine depth", um(block.depth_um)]);
    if (block.factor !== undefined) rows.push(["Empirical machine offset (factor)", `x ${block.factor.toFixed(3)}`]);
    if (block.depthBand_um) rows.push(["80 % band (not a tolerance)", `${um(block.depthBand_um[0])} to ${um(block.depthBand_um[1])}${block.bandNotInformative ? " (not informative)" : ""}`]);
  }
  if (input.screeningDepth_um !== null) rows.push(["Screening depth (unchanged)", um(input.screeningDepth_um)]);
  const residual = block.userResidualSummary;
  if (residual && residual.meanLnResidualDefault !== null) rows.push(["Mean ln residual at default", residual.meanLnResidualDefault.toFixed(3)]);
  if (block.missingMethodFields.length) rows.push(["Missing method fields", methodFieldText(block.missingMethodFields)]);
  if (block.reasonText.length) rows.push(["Reasons", block.reasonText.join("; ")]);
  return rows;
}
