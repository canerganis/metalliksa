import {
  HeatTreatmentCondition,
  LPBFAlloyId,
  TraceableLPBFRecord,
} from "../types/lpbfDataFoundation";
import {
  MASTER_LPBF_REFERENCE_DATASETS,
  loadUserLPBFRecords,
} from "../data/lpbfReferenceDatasets";
import { authorityPvWindow, type AuthorityAlloyId } from "../data/lpbfMaterialAuthority";

export interface LiteraturePvWindow {
  powerMin_W: number;
  powerMax_W: number;
  speedMin_mm_s: number;
  speedMax_mm_s: number;
  notes: string;
  sources: string[];
}

/**
 * TS-local, not authority: the Python material authority has no IN625 P–v box
 * (python/four_alloy_materials.py LITERATURE_PV_WINDOWS covers the four locked alloys only).
 */
const IN625_PV_WINDOW_TS_LOCAL: LiteraturePvWindow = {
  powerMin_W: 150,
  powerMax_W: 350,
  speedMin_mm_s: 600,
  speedMax_mm_s: 1200,
  notes: "Typical AM-Bench IN625 parameter window; analogous to IN718 but slightly more power tolerance.",
  sources: ["NIST AMB2018-01"],
};

/** P–v numbers from the Python authority (src/generated/lpbfMaterialAuthority.json); notes and sources stay here. */
function authorityBox(alloyId: AuthorityAlloyId, notes: string, sources: string[]): LiteraturePvWindow {
  return { ...authorityPvWindow(alloyId), notes, sources };
}

/**
 * Published P–v DISPLAY RANGES (machine-class typical). P7a (2026-10-11, G1 audit V03): outside the range is an
 * advisory ("unsourced screening threshold"), never a verdict; no table or figure of any listed paper supplies an edge.
 * Sources are related literature only; each DOI below resolved by Crossref to the named paper on 2026-10-11. Removed
 * (G1 source sweep 1.4, the strings are listed in python/test_lpbf_p7a_rules_and_nulls.py): the Ti-6Al-4V "Acta Mater.
 * 2010" DOI (an epoxy nanocomposite paper) and the Kasperovich and Hausmann 2015 fatigue paper; the 316L "Cherry" DOI
 * (a 404; Cherry 2015 is 10.1007/s00170-014-6297-2) and the Liverani 2017 DOI (not Cherry); the AlSi10Mg Rapid
 * Prototyping J. DOI (a 404) and the "Acta Mater. 2016" DOI (a CoFeB/MgO magnetics paper).
 */
const RELATED_LITERATURE_NOTE = "related literature, no edge of this display range is taken from it";
export const LITERATURE_PV_WINDOWS: Record<LPBFAlloyId, LiteraturePvWindow> = {
  ti6al4v: authorityBox(
    "ti6al4v",
    `30 µm EOS-class display range; Gong 2014 (Addit. Manuf.) is ${RELATED_LITERATURE_NOTE}.`,
    ["10.1016/j.addma.2014.08.002"],
  ),
  ss316l: authorityBox(
    "ss316l",
    `Renishaw / Concept Laser 30 µm display range; Cherry 2015 (Int. J. Adv. Manuf. Technol.) and Kurzynowski 2018 (Mater. Sci. Eng. A) are ${RELATED_LITERATURE_NOTE}.`,
    ["10.1007/s00170-014-6297-2", "10.1016/j.msea.2018.01.103"],
  ),
  alsi10mg: authorityBox(
    "alsi10mg",
    `High-k Al display range; 150–200 °C preheat typical; Read 2015 (Mater. Des.) is ${RELATED_LITERATURE_NOTE}.`,
    ["10.1016/j.matdes.2014.09.044"],
  ),
  in718: authorityBox(
    "in718",
    `EOS-class display range (~285 W / 960 mm/s / 40 µm); Jia 2014 (J. Alloys Compd.), Chlebus 2015 (Mater. Sci. Eng. A) and Trosch 2016 (Mater. Lett.) are ${RELATED_LITERATURE_NOTE}.`,
    ["10.1016/j.jallcom.2013.09.171", "10.1016/j.msea.2015.05.035", "10.1016/j.matlet.2015.10.136"],
  ),
  in625: IN625_PV_WINDOW_TS_LOCAL,
};

export function alloyRecords(alloyId: LPBFAlloyId): TraceableLPBFRecord[] {
  const extra = typeof window === "undefined" ? [] : loadUserLPBFRecords().filter((r) => r.build.alloyId === alloyId);
  return [...(MASTER_LPBF_REFERENCE_DATASETS[alloyId] || []), ...extra];
}

export function denseConductionHull(alloyId: LPBFAlloyId): {
  powerMin_W: number;
  powerMax_W: number;
  speedMin_mm_s: number;
  speedMax_mm_s: number;
  n: number;
} | null {
  const pts = alloyRecords(alloyId).filter(
    (r) =>
      r.properties.relativeDensity_pct >= 99.5 &&
      r.params.derived.predictedRegime === "Stable Conduction"
  );
  if (pts.length === 0) return null;
  return {
    powerMin_W: Math.min(...pts.map((r) => r.params.laserPower_W)),
    powerMax_W: Math.max(...pts.map((r) => r.params.laserPower_W)),
    speedMin_mm_s: Math.min(...pts.map((r) => r.params.scanSpeed_mm_s)),
    speedMax_mm_s: Math.max(...pts.map((r) => r.params.scanSpeed_mm_s)),
    n: pts.length,
  };
}

export function evaluateLiteraturePvWindow(
  alloyId: LPBFAlloyId,
  power_W: number,
  speed_mm_s: number
): { inside: boolean; box: (typeof LITERATURE_PV_WINDOWS)[LPBFAlloyId]; hull: ReturnType<typeof denseConductionHull> } {
  const box = LITERATURE_PV_WINDOWS[alloyId];
  const hull = denseConductionHull(alloyId);
  const insideBox =
    power_W >= box.powerMin_W &&
    power_W <= box.powerMax_W &&
    speed_mm_s >= box.speedMin_mm_s &&
    speed_mm_s <= box.speedMax_mm_s;
  const insideHull = hull
    ? power_W >= hull.powerMin_W &&
      power_W <= hull.powerMax_W &&
      speed_mm_s >= hull.speedMin_mm_s &&
      speed_mm_s <= hull.speedMax_mm_s
    : insideBox;
  return { inside: insideBox || insideHull, box, hull };
}

export interface HeatTreatmentCohort {
  condition: HeatTreatmentCondition;
  label: string;
  n: number;
  meanYS: number | null;
  meanUTS: number | null;
  meanEl: number | null;
  meanElong: number | null;
  meanDensity: number;
  meanFatigue: number | null;
}

function mean(xs: number[]): number | null {
  if (xs.length === 0) return null;
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

export function heatTreatmentCohorts(alloyId: LPBFAlloyId): HeatTreatmentCohort[] {
  const groups = new Map<HeatTreatmentCondition, TraceableLPBFRecord[]>();
  for (const r of alloyRecords(alloyId)) {
    const k = r.sample.heatTreatment;
    const arr = groups.get(k) || [];
    arr.push(r);
    groups.set(k, arr);
  }
  return [...groups.entries()].map(([condition, recs]) => {
    const meanEl = mean(recs.map((r) => r.properties.elongationAtBreak_pct).filter((x): x is number => x != null));
    return {
      condition,
      label: condition,
      n: recs.length,
      meanYS: mean(recs.map((r) => r.properties.yieldStrength_MPa).filter((x): x is number => x != null)),
      meanUTS: mean(recs.map((r) => r.properties.ultimateTensileStrength_MPa).filter((x): x is number => x != null)),
      meanEl,
      meanElong: meanEl,
      meanDensity: mean(recs.map((r) => r.properties.relativeDensity_pct)) ?? 0,
      meanFatigue: mean(recs.map((r) => r.properties.fatigueLimit_MPa).filter((x): x is number => x != null)),
    };
  });
}

export interface OrientationCohort {
  deg: 0 | 45 | 90;
  label: string;
  n: number;
  meanYS: number | null;
  meanUTS: number | null;
  meanEl: number | null;
  meanFatigue: number | null;
  dois: string[];
}

export function orientationCohorts(
  alloyId: LPBFAlloyId,
  heatTreatment?: HeatTreatmentCondition
): OrientationCohort[] {
  const recs = alloyRecords(alloyId).filter((r) => {
    const htOk = heatTreatment ? r.sample.heatTreatment === heatTreatment : r.sample.heatTreatment === "As-Built";
    return htOk && r.properties.relativeDensity_pct >= 99.0;
  });
  return ([0, 45, 90] as const).map((deg) => {
    const slice = recs.filter((r) => r.sample.buildOrientationDeg === deg);
    return {
      deg,
      label: `${deg}°`,
      n: slice.length,
      meanYS: mean(slice.map((r) => r.properties.yieldStrength_MPa).filter((x): x is number => x != null)),
      meanUTS: mean(slice.map((r) => r.properties.ultimateTensileStrength_MPa).filter((x): x is number => x != null)),
      meanEl: mean(slice.map((r) => r.properties.elongationAtBreak_pct).filter((x): x is number => x != null)),
      meanFatigue: mean(slice.map((r) => r.properties.fatigueLimit_MPa).filter((x): x is number => x != null)),
      dois: [...new Set(slice.map((r) => r.source.doi))],
    };
  });
}

export function mapDisplayNameToAlloyId(name: string): LPBFAlloyId | null {
  const n = name.toLowerCase();
  if (n.includes("ti-6") || n.includes("ti64") || n.includes("grade 5")) return "ti6al4v";
  if (n.includes("316")) return "ss316l";
  if (n.includes("alsi")) return "alsi10mg";
  if (n.includes("718") || n.includes("inconel 718")) return "in718";
  if (n.includes("625") || n.includes("inconel 625")) return "in625";
  return null;
}

export function alloyIdToAnisotropyKey(id: LPBFAlloyId): string {
  if (id === "ti6al4v") return "Ti-6Al-4V Grade 5";
  if (id === "ss316l") return "316L Stainless Steel";
  if (id === "alsi10mg") return "AlSi10Mg";
  if (id === "in625") return "Inconel 625";
  return "Inconel 718";
}

export const alloyIdToFatigueDbKey = alloyIdToAnisotropyKey;

function pickNum(v: number | null, fallback: number): number {
  return v != null && Number.isFinite(v) ? v : fallback;
}

type AnisotropyPayload = {
  name: string;
  alloyFamily: string;
  asBuilt: {
    sigma_y_0deg_MPa: number;
    sigma_y_45deg_MPa: number;
    sigma_y_90deg_MPa: number;
    sigma_uts_0deg_MPa: number;
    sigma_uts_90deg_MPa: number;
    elongation_0deg_pct: number;
    elongation_90deg_pct: number;
    fatigueLimit_0deg_MPa: number;
    fatigueLimit_90deg_MPa: number;
    youngsModulus_0deg_GPa: number;
    youngsModulus_90deg_GPa: number;
    hallPetch_k_y: number;
    taylorFactor: number;
    dominantTexture: string;
  };
  heatTreated_HIP: {
    sigma_y_0deg_MPa: number;
    sigma_y_90deg_MPa: number;
    sigma_uts_0deg_MPa: number;
    sigma_uts_90deg_MPa: number;
    elongation_0deg_pct: number;
    elongation_90deg_pct: number;
    fatigueLimit_0deg_MPa: number;
    fatigueLimit_90deg_MPa: number;
    anisotropyIndex_pct: number;
  };
};

export function anisotropyOverlayFromGroundTruth(
  fallback: AnisotropyPayload,
  alloyId: LPBFAlloyId
): { data: AnisotropyPayload; grounded: boolean; sourced: boolean; dois: string[] } {
  const asBuilt = orientationCohorts(alloyId, "As-Built");
  const hip = orientationCohorts(alloyId, "Hot Isostatic Pressed (HIP)");
  const o0 = asBuilt.find((c) => c.deg === 0);
  const o45 = asBuilt.find((c) => c.deg === 45);
  const o90 = asBuilt.find((c) => c.deg === 90);
  const h0 = hip.find((c) => c.deg === 0);
  const h90 = hip.find((c) => c.deg === 90);
  const grounded = (o0?.n || 0) + (o90?.n || 0) > 0;
  const dois = [...new Set([...asBuilt, ...hip].flatMap((c) => c.dois))];

  const data: AnisotropyPayload = {
    ...fallback,
    asBuilt: {
      ...fallback.asBuilt,
      sigma_y_0deg_MPa: pickNum(o0?.meanYS ?? null, fallback.asBuilt.sigma_y_0deg_MPa),
      sigma_y_45deg_MPa: pickNum(o45?.meanYS ?? null, fallback.asBuilt.sigma_y_45deg_MPa),
      sigma_y_90deg_MPa: pickNum(o90?.meanYS ?? null, fallback.asBuilt.sigma_y_90deg_MPa),
      sigma_uts_0deg_MPa: pickNum(o0?.meanUTS ?? null, fallback.asBuilt.sigma_uts_0deg_MPa),
      sigma_uts_90deg_MPa: pickNum(o90?.meanUTS ?? null, fallback.asBuilt.sigma_uts_90deg_MPa),
      elongation_0deg_pct: pickNum(o0?.meanEl ?? null, fallback.asBuilt.elongation_0deg_pct),
      elongation_90deg_pct: pickNum(o90?.meanEl ?? null, fallback.asBuilt.elongation_90deg_pct),
      fatigueLimit_0deg_MPa: pickNum(o0?.meanFatigue ?? null, fallback.asBuilt.fatigueLimit_0deg_MPa),
      fatigueLimit_90deg_MPa: pickNum(o90?.meanFatigue ?? null, fallback.asBuilt.fatigueLimit_90deg_MPa),
    },
    heatTreated_HIP: {
      ...fallback.heatTreated_HIP,
      sigma_y_0deg_MPa: pickNum(h0?.meanYS ?? null, fallback.heatTreated_HIP.sigma_y_0deg_MPa),
      sigma_y_90deg_MPa: pickNum(h90?.meanYS ?? null, fallback.heatTreated_HIP.sigma_y_90deg_MPa),
      sigma_uts_0deg_MPa: pickNum(h0?.meanUTS ?? null, fallback.heatTreated_HIP.sigma_uts_0deg_MPa),
      sigma_uts_90deg_MPa: pickNum(h90?.meanUTS ?? null, fallback.heatTreated_HIP.sigma_uts_90deg_MPa),
      elongation_0deg_pct: pickNum(h0?.meanEl ?? null, fallback.heatTreated_HIP.elongation_0deg_pct),
      elongation_90deg_pct: pickNum(h90?.meanEl ?? null, fallback.heatTreated_HIP.elongation_90deg_pct),
      fatigueLimit_0deg_MPa: pickNum(h0?.meanFatigue ?? null, fallback.heatTreated_HIP.fatigueLimit_0deg_MPa),
      fatigueLimit_90deg_MPa: pickNum(h90?.meanFatigue ?? null, fallback.heatTreated_HIP.fatigueLimit_90deg_MPa),
    },
  };
  const sy0 = data.heatTreated_HIP.sigma_y_0deg_MPa;
  data.heatTreated_HIP.anisotropyIndex_pct = sy0 > 0
    ? Number((Math.abs(sy0 - data.heatTreated_HIP.sigma_y_90deg_MPa) / sy0 * 100).toFixed(1))
    : fallback.heatTreated_HIP.anisotropyIndex_pct;
  return { data, grounded, sourced: grounded, dois };
}

export function overlayAnisotropyFromGroundTruth(
  alloyId: LPBFAlloyId,
  fallback: AnisotropyPayload
) {
  return anisotropyOverlayFromGroundTruth(fallback, alloyId);
}




