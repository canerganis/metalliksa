import {
  LPBFAlloyId,
  TraceableLPBFRecord,
  calculatePeakLaserIntensity,
} from "../types/lpbfDataFoundation";
import {
  MASTER_LPBF_REFERENCE_DATASETS,
  loadUserLPBFRecords,
} from "../data/lpbfReferenceDatasets";
import type { BaseMetalType } from "../store/useMaterialSpecimenStore";

/** "inconclusive": melt-pool geometry not resolved (extentStatus !== "computed"); no print / do-not-print claim. */
export type PrintVerdict = "printable" | "risky" | "do-not-print" | "inconclusive";

/** Label for every place the printable / risky / do-not-print verdict is shown; the verdict itself is unchanged. */
export const PRINT_VERDICT_SCREENING_LABEL = "Screening indication (not validated against build outcomes)";

export interface SolverMaterialMap {
  pythonThermal: string;
  pythonSlicer: string;
  alloyId: LPBFAlloyId;
}

type BuildJobSolverMaterialMap = SolverMaterialMap & {
  baseMetal: Extract<BaseMetalType, "Ti" | "Fe" | "Al" | "Ni">;
};

/** Strict material identity contract used only by the build-job solver. */
const TI64_BUILD_JOB_MATERIAL: BuildJobSolverMaterialMap = {
  pythonThermal: "Ti-6Al-4V", pythonSlicer: "Ti-6Al-4V ELI", alloyId: "ti6al4v", baseMetal: "Ti",
};
const SS316L_BUILD_JOB_MATERIAL: BuildJobSolverMaterialMap = {
  pythonThermal: "316L Stainless Steel", pythonSlicer: "SS 316L", alloyId: "ss316l", baseMetal: "Fe",
};
const ALSI10MG_BUILD_JOB_MATERIAL: BuildJobSolverMaterialMap = {
  pythonThermal: "AlSi10Mg", pythonSlicer: "AlSi10Mg", alloyId: "alsi10mg", baseMetal: "Al",
};
const IN718_BUILD_JOB_MATERIAL: BuildJobSolverMaterialMap = {
  pythonThermal: "Inconel 718", pythonSlicer: "Inconel 718", alloyId: "in718", baseMetal: "Ni",
};

const BUILD_JOB_MATERIALS: Record<string, BuildJobSolverMaterialMap> = {
  // Ti-6Al-4V canonical names, established shorthand, and product grade labels.
  ti6al4v: TI64_BUILD_JOB_MATERIAL,
  ti64: TI64_BUILD_JOB_MATERIAL,
  ti6al4vgrade5: TI64_BUILD_JOB_MATERIAL,
  ti6al4vgrade5titanium: TI64_BUILD_JOB_MATERIAL,
  ti6al4vgrade23eli: TI64_BUILD_JOB_MATERIAL,
  ti6al4vgrade23eliastmf3001: TI64_BUILD_JOB_MATERIAL,
  ti6al4vgrade23unsr56401: TI64_BUILD_JOB_MATERIAL,
  // 316L canonical names and grade/designation labels.
  "316l": SS316L_BUILD_JOB_MATERIAL,
  "316lstainlesssteel": SS316L_BUILD_JOB_MATERIAL,
  aisi316lstainlesssteel: SS316L_BUILD_JOB_MATERIAL,
  aisi316lstainlesssteelunss31603: SS316L_BUILD_JOB_MATERIAL,
  "316lstainlesssteelunss31603": SS316L_BUILD_JOB_MATERIAL,
  "ss316l": SS316L_BUILD_JOB_MATERIAL,
  // AlSi10Mg names used by the specimen preset and materials catalog.
  alsi10mg: ALSI10MG_BUILD_JOB_MATERIAL,
  alsi10mgadditivelightweight: ALSI10MG_BUILD_JOB_MATERIAL,
  alsi10mgadditivepowderalloylpbft6: ALSI10MG_BUILD_JOB_MATERIAL,
  // IN718 canonical shorthand and established specification labels.
  in718: IN718_BUILD_JOB_MATERIAL,
  inconel718: IN718_BUILD_JOB_MATERIAL,
  inconel718ams5662: IN718_BUILD_JOB_MATERIAL,
  inconel718ams5662unsn07718: IN718_BUILD_JOB_MATERIAL,
  inconel718nickelbasesuperalloyprecipitationhardened: IN718_BUILD_JOB_MATERIAL,
};

function normalizeBuildJobMaterialAlias(name: string): string {
  return name.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

export function mapSpecimenToBuildJobMaterials(
  name: string,
  baseMetal?: BaseMetalType
): BuildJobSolverMaterialMap | null {
  const alias = normalizeBuildJobMaterialAlias(name);
  if (!Object.prototype.hasOwnProperty.call(BUILD_JOB_MATERIALS, alias)) return null;
  const materials = BUILD_JOB_MATERIALS[alias];
  return baseMetal === undefined || baseMetal === materials.baseMetal ? materials : null;
}

export function mapSpecimenToSolverMaterials(
  name: string,
  baseMetal: BaseMetalType
): SolverMaterialMap {
  const n = `${name} ${baseMetal}`.toLowerCase();
  if (n.includes("ti-6") || n.includes("ti64") || n.includes("titanium") || baseMetal === "Ti") {
    return { pythonThermal: "Ti-6Al-4V", pythonSlicer: "Ti-6Al-4V ELI", alloyId: "ti6al4v" };
  }
  if (n.includes("alsi") || n.includes("aluminum") || baseMetal === "Al") {
    return { pythonThermal: "AlSi10Mg", pythonSlicer: "AlSi10Mg", alloyId: "alsi10mg" };
  }
  if (n.includes("316") || n.includes("stainless") || baseMetal === "Fe") {
    return { pythonThermal: "316L Stainless Steel", pythonSlicer: "SS 316L", alloyId: "ss316l" };
  }
  if (n.includes("cocr") || baseMetal === "Co") {
    return { pythonThermal: "CoCrMo", pythonSlicer: "CoCrMo", alloyId: "ss316l" };
  }
  return { pythonThermal: "Inconel 718", pythonSlicer: "Inconel 718", alloyId: "in718" };
}

export function inferSlicerPreset(cadAssetName: string): "nozzle" | "turbine" | "bracket" | "gyroid" | "hip_implant" {
  const n = cadAssetName.toLowerCase();
  if (n.includes("turbine")) return "turbine";
  if (n.includes("bracket")) return "bracket";
  if (n.includes("gyroid")) return "gyroid";
  if (n.includes("hip")) return "hip_implant";
  return "nozzle";
}

export interface LiteratureMatch {
  record: TraceableLPBFRecord;
  distance: number;
}

/**
 * Live quantities used to rank literature records. Normalized enthalpy is deliberately absent:
 * the live ΔH/h_s is Python's (rho Cp (T_liq - T_preheat), the index convention absorptivity
 * absorptivity_index_IR since P7b, 2026-10-14; the field uses the measured authority) and records
 * carry no comparable Python value, so mixing the two in one distance is not done (B5 step 1).
 * Peak intensity has the same definition on both sides (8P/(pi d^2)).
 */
export interface LiteratureLiveDerived {
  peakIntensity_MW_cm2?: number;
  beamDiameter_um?: number;
}

export interface LiteratureOverlayPoint {
  power_W: number;
  speed_mm_s: number;
  doi: string;
  citation: string;
  sampleCode: string;
}

function alloyRecordPool(alloyId: LPBFAlloyId): TraceableLPBFRecord[] {
  return [
    ...(MASTER_LPBF_REFERENCE_DATASETS[alloyId] || []),
    ...loadUserLPBFRecords().filter((r) => r.build.alloyId === alloyId),
  ];
}

export function literatureOverlayPoints(alloyId: LPBFAlloyId): LiteratureOverlayPoint[] {
  return alloyRecordPool(alloyId).map((r) => ({
    power_W: r.params.laserPower_W,
    speed_mm_s: r.params.scanSpeed_mm_s,
    doi: r.source.doi || "",
    citation: r.source.citation,
    sampleCode: r.sample.sampleCode,
  }));
}

export function findNearestLiteratureRecord(
  alloyId: LPBFAlloyId,
  power_W: number,
  speed_mm_s: number,
  hatch_um: number,
  layer_um: number,
  live?: LiteratureLiveDerived
): LiteratureMatch | null {
  const pool = alloyRecordPool(alloyId);

  if (pool.length === 0) {
    const fallback = Object.values(MASTER_LPBF_REFERENCE_DATASETS).flat();
    if (fallback.length === 0) return null;
    return nearestInPool(fallback, power_W, speed_mm_s, hatch_um, layer_um, live);
  }

  return nearestInPool(pool, power_W, speed_mm_s, hatch_um, layer_um, live);
}

function livePeakIntensity(power_W: number, live?: LiteratureLiveDerived): number | undefined {
  if (live?.peakIntensity_MW_cm2 != null && Number.isFinite(live.peakIntensity_MW_cm2)) {
    return live.peakIntensity_MW_cm2;
  }
  if (live?.beamDiameter_um != null && live.beamDiameter_um > 0) {
    return calculatePeakLaserIntensity(power_W, live.beamDiameter_um);
  }
  return undefined;
}

function nearestInPool(
  pool: TraceableLPBFRecord[],
  power_W: number,
  speed_mm_s: number,
  hatch_um: number,
  layer_um: number,
  live?: LiteratureLiveDerived
): LiteratureMatch | null {
  const liveI0 = livePeakIntensity(power_W, live);
  let best: LiteratureMatch | null = null;
  for (const record of pool) {
    const p = record.params;
    let distance =
      Math.abs(p.laserPower_W - power_W) / Math.max(1, power_W) +
      Math.abs(p.scanSpeed_mm_s - speed_mm_s) / Math.max(1, speed_mm_s) +
      Math.abs(p.hatchSpacing_um - hatch_um) / Math.max(1, hatch_um) +
      Math.abs(p.layerThickness_um - layer_um) / Math.max(1, layer_um);

    const recI0 = p.derived?.peakLaserIntensity_MW_cm2;
    if (liveI0 != null && recI0 != null && recI0 > 0) {
      distance += Math.abs(recI0 - liveI0) / Math.max(1, liveI0);
    }

    if (!best || distance < best.distance) {
      best = { record, distance };
    }
  }
  return best;
}
