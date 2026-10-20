/**
 * Pure helpers for the guided tour. The demo case is read from the committed NIST AMB2022-03 transcription
 * (MELT_POOL_LITERATURE_CASES, which imports data/benchmark/nist-amb2022-03-optical/table4-aggregate-v2.json);
 * no measured or process value is written in code here.
 */
import { MELT_POOL_LITERATURE_CASES, relativeErrorPct, type MeltPoolLiteratureCase } from "../data/meltPoolLiteratureCases";
import type { LpbfCalibrationScorecardDocument } from "../data/lpbfCalibrationScorecard";
import type { LpbfProcessPatch } from "../store/useMaterialSpecimenStore";
import type { SimulationInput, SimulationJob } from "../services/lpbfSimulationService";
import type { ResearchHostState } from "../store/useLpbfResearchModelStore";
import { canonicalLpbfMaterialName } from "./lpbfMaterialIdentity";
import { meltPoolExtentInfo, type MeltPoolExtentFields } from "./meltPoolExtentStatus";

export const DEMO_CASE_ID = "nist-amb2022-03-0";
/** Absolute tolerance when matching a run's settings to the case (the values are copied, not recomputed). */
export const RUN_MATCH_TOLERANCE = 1e-6;

/** The literature case with every field the tour needs guaranteed present. */
export interface DemoCase extends MeltPoolLiteratureCase {
  laserPower_W: number;
  scanSpeed_mm_s: number;
  beamDiameter_um: number;
  preheatTemp_C: number;
  publishedWidth_um: number;
  publishedDepth_um: number;
  widthStdDev_um: number;
  depthStdDev_um: number;
  measurementCount: number;
}

/** Throws when the case is absent or incomplete: a tour built on a missing case must not run on invented numbers. */
export function demoCase(cases: readonly MeltPoolLiteratureCase[] = MELT_POOL_LITERATURE_CASES, id: string = DEMO_CASE_ID): DemoCase {
  const found = cases.find(c => c.id === id);
  if (!found) throw new Error(`Guided tour case ${id} is not in the literature cases.`);
  const numeric = [found.laserPower_W, found.scanSpeed_mm_s, found.beamDiameter_um, found.preheatTemp_C,
    found.publishedWidth_um, found.publishedDepth_um, found.widthStdDev_um, found.depthStdDev_um, found.measurementCount];
  if (found.kind !== "measured" || numeric.some(v => typeof v !== "number" || !Number.isFinite(v))) {
    throw new Error(`Guided tour case ${id} lacks a measured value, uncertainty or process field.`);
  }
  return found as DemoCase;
}

/** Process fields the case defines. Layer and hatch are null in the case (bare plate) and are deliberately not patched. */
export function demoProcessPatch(c: DemoCase): LpbfProcessPatch {
  return { laserPower_W: c.laserPower_W, scanSpeed_mms: c.scanSpeed_mm_s, beamDiameter_um: c.beamDiameter_um, preheatTemp_C: c.preheatTemp_C };
}

export type RunSettings = Pick<SimulationInput, "material" | "power_W" | "speed_mm_s" | "beamDiameter_um" | "preheat_C">;

/** True when a run's executed settings carry the case's material and process values (within 1e-6). */
export function runMatchesCase(settings: Partial<RunSettings> | null | undefined, c: DemoCase): boolean {
  if (!settings || typeof settings.material !== "string") return false;
  if (canonicalLpbfMaterialName(settings.material) !== canonicalLpbfMaterialName(c.material)) return false;
  const close = (a: unknown, b: number) => typeof a === "number" && Number.isFinite(a) && Math.abs(a - b) <= RUN_MATCH_TOLERANCE;
  return close(settings.power_W, c.laserPower_W) && close(settings.speed_mm_s, c.scanSpeed_mm_s)
    && close(settings.beamDiameter_um, c.beamDiameter_um) && close(settings.preheat_C, c.preheatTemp_C);
}

export interface ComparisonRow {
  quantity: "width" | "depth";
  predicted_um: number;
  measured_um: number;
  sd_um: number;
  /** predicted - measured */
  diff_um: number;
  diff_pct: number;
  withinOneSd: boolean;
}
export type MeasurementComparison =
  | { available: true; screeningOnly: boolean; n: number; rows: [ComparisonRow, ComparisonRow]; solverId: string; implementationHash: string | null; caseId: string; doi: string; surface: { mode: string | null; layer_um: number | null; hatch_um: number | null; bareTrack: boolean } }
  | { available: false; reason: string };

function extentFields(job: SimulationJob): MeltPoolExtentFields | undefined {
  const result = job.result as unknown as { meltPoolGeometry?: MeltPoolExtentFields; metrics?: MeltPoolExtentFields } | undefined;
  return result?.meltPoolGeometry ?? result?.metrics;
}

/** Predicted vs published width and depth, or the reason no comparison is possible. Never returns numbers when unavailable. */
export function compareToMeasurement(c: DemoCase, job: SimulationJob | undefined | null): MeasurementComparison {
  if (!job) return { available: false, reason: "No job has been run yet. Run Screening on the Thermal Simulation stage first." };
  if (job.status !== "completed" || !job.result) return { available: false, reason: `The current job is ${job.status}; only a completed job supplies a predicted melt pool.` };
  const result = job.result;
  if (!runMatchesCase(result.settings, c)) {
    return { available: false, reason: "The completed job was run with different material or process inputs than the NIST case, so it is not comparable. Run again after loading the case." };
  }
  const extent = meltPoolExtentInfo(extentFields(job));
  const { width_um, depth_um } = result.metrics;
  const screeningOnly = extent.status === "not-reported"
    && result.effectiveMode === "screening" && result.settings.mode === "screening"
    && Number.isFinite(width_um) && Number.isFinite(depth_um);
  if (!extent.computed && !screeningOnly) {
    const why = extent.status === "not-reported"
      ? "The solver does not report a melt-pool extent status for this run, so the tour cannot confirm that width and depth are a closed liquidus isotherm and does not compare them."
      : `The melt-pool extent is not computed (status: ${extent.status}; ${extent.description}). Width and depth from this run are not an isotherm and are excluded from the comparison.`;
    return { available: false, reason: why };
  }
  const settingsExtra = result.settings as unknown as { surfaceMode?: string; layer_um?: unknown; hatch_um?: unknown };
  const finiteOrNull = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);
  if (!Number.isFinite(width_um) || !Number.isFinite(depth_um)) return { available: false, reason: "The completed job reports no finite width and depth." };
  const row = (quantity: "width" | "depth", predicted: number, measured: number, sd: number): ComparisonRow => {
    const diff = predicted - measured;
    return { quantity, predicted_um: predicted, measured_um: measured, sd_um: sd, diff_um: diff, diff_pct: relativeErrorPct(predicted, measured), withinOneSd: Math.abs(diff) <= sd };
  };
  return {
    available: true, screeningOnly, n: c.measurementCount, caseId: c.id, doi: c.doi,
    rows: [row("width", width_um, c.publishedWidth_um, c.widthStdDev_um), row("depth", depth_um, c.publishedDepth_um, c.depthStdDev_um)],
    surface: { mode: settingsExtra.surfaceMode ?? null, layer_um: finiteOrNull(settingsExtra.layer_um), hatch_um: finiteOrNull(settingsExtra.hatch_um), bareTrack: settingsExtra.surfaceMode === "bare-plate" },
    solverId: result.solver.id, implementationHash: result.provenance?.implementationHash ?? null,
  };
}

/** Read a held P8 result only when both its current and executed identities still match. Never runs a model. */
export function researchDepthForCase(c: DemoCase, host: ResearchHostState) {
  const { run } = host;
  const input = run.input;
  if (run.status !== "complete" || !input || !run.identity || host.identity !== run.identity
    || !run.result?.progress.complete || !run.requestKey || run.requestKey !== run.result.requestKey
    || !runMatchesCase({ material: input.material, power_W: input.laserPower_W,
      speed_mm_s: input.scanSpeed_mm_s, beamDiameter_um: input.beamDiameter_um, preheat_C: input.preheatTemp_C }, c)) return null;
  const module = run.result.researchModels?.meltDepthLink;
  const depth = module?.fields.linkedMeltDepth_um;
  if (!module || module.status !== "available" || module.experimentalValidation !== false || !depth
    || depth.reasonCode || typeof depth.value !== "number" || !Number.isFinite(depth.value)) return null;
  return { module, depth };
}

/** What the committed calibration scorecard says about one material, stated only from its headline rows. */
export function scorecardStatementFor(material: string, record: LpbfCalibrationScorecardDocument | null): string {
  if (!record) return `No calibration scorecard record is committed in this build, so nothing is reported for ${material}.`;
  const rows = record.headline.filter(r => r.material === material);
  if (!rows.length) return `The committed calibration scorecard (generated ${record.generatedAt}) has no rows for ${material}.`;
  const counts = new Map<string, number>();
  for (const r of rows) counts.set(r.status, (counts.get(r.status) ?? 0) + 1);
  const where = `committed calibration scorecard, generated ${record.generatedAt}, implementation ${record.implementationHash}`;
  if (counts.size === 1 && counts.has("no-data")) {
    return `Every ${material} row (${rows.length} of ${rows.length}) in the ${where}, is no-data. No held-out error is available for this material, so the tour comparison has no calibration behind it.`;
  }
  const summary = [...counts.entries()].map(([status, n]) => `${n} ${status}`).join(", ");
  return `${material} rows in the ${where}: ${summary} (of ${rows.length}). These are calibration gate statuses, not experimental validation.`;
}
