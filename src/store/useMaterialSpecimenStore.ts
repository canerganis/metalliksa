import { create } from "zustand";
import { persist } from "zustand/middleware";
import { materialProfileIdentity } from "../utils/materialProfileIdentity";
import { materialCategoryForBase } from "../utils/materialCategory";
import { setActivePipelineMaterial, PipelineMaterialPayload } from "../utils/materialDataPipeline";
import { estimateSpecimenHardnessHV } from "../utils/hardnessStrengthEstimate";
import { ELEMENTAL_DENSITY_GCM3, withoutCompositionHeuristicProperties } from "../utils/compositionPropertyAvailability";

export type BaseMetalType = "Ni" | "Fe" | "Ti" | "Al" | "Cu" | "Co" | "Mg" | "Refractory" | "Other";

export type LpbfScanStrategy = "island" | "meander-67" | "stripe";
export type LpbfBeamProfile = "gaussian" | "flat-top";

export interface LpbfSpecimenState {
  recommendedLaserPower_W: number;
  recommendedScanSpeed_mms: number;
  recommendedHatch_um: number;
  recommendedLayer_um: number;
  recommendedPreheatTemp_C: number;
  thermalConductivity_k_WmK: number;
  density_rho_kgm3: number;
  specificHeat_Cp_JkgK: number;
  laserAbsorptivity: number;
  thermalExpansion_CTE_10e6: number;
  criticalGradient_G_Km: number;
  hotTearingSusceptibility: "Low" | "Moderate" | "High";
  crackingMechanism: string;
  mitigationRecommendation: string;
  /** Active Build Job process vector — single source for all LPBF sub-labs */
  laserPower_W: number;
  scanSpeed_mms: number;
  hatch_um: number;
  layer_um: number;
  beamDiameter_um: number;
  preheatTemp_C: number;
  scanStrategy: LpbfScanStrategy;
  beamProfile: LpbfBeamProfile;
  cadAssetName: string;
  specimenDoi: string;
  /** Deterministic seed for Python screening extras (Marangoni pores, etc.). */
  processSeed: number;
  /** Surface incline from horizontal (deg); solidification R = v·cos(θ). */
  inclineAngle_deg: number;
  /** Overhang from vertical (deg); omit/0 = flat upskin. */
  downskinOverhang_deg: number;
  /**
   * Fields that were missing when this vector was built and were filled from LPBF_PROCESS_FALLBACKS. These values are
   * generic placeholders, not material-specific or measured; consumers should show them as defaults.
   */
  defaultsApplied?: LpbfDefaultedField[];
}

export type LpbfProcessPatch = Partial<
  Pick<
    LpbfSpecimenState,
    | "laserPower_W"
    | "scanSpeed_mms"
    | "hatch_um"
    | "layer_um"
    | "beamDiameter_um"
    | "preheatTemp_C"
    | "scanStrategy"
    | "beamProfile"
    | "cadAssetName"
    | "specimenDoi"
    | "processSeed"
    | "inclineAngle_deg"
    | "downskinOverhang_deg"
  >
>;

/**
 * Values substituted when a caller omits a field. Generic placeholders with no source: they are listed in
 * `LpbfSpecimenState.defaultsApplied` so the UI can disclose them. Numeric behaviour is unchanged.
 */
export const LPBF_PROCESS_FALLBACKS = {
  thermalConductivity_k_WmK: 11.5,
  density_rho_kgm3: 8200,
  specificHeat_Cp_JkgK: 435,
  // UI default, not a measurement: the served physics reads the Python authority (four_alloy_materials.py
  // ABSORPTIVITY_AUTHORITY since P7b, 2026-10-14); this form fallback never reaches a solver.
  laserAbsorptivity: 0.58,
  thermalExpansion_CTE_10e6: 13,
  criticalGradient_G_Km: 1.5e7,
  hotTearingSusceptibility: "Moderate",
  beamDiameter_um: 80,
  scanStrategy: "stripe",
  beamProfile: "gaussian",
} as const;
export type LpbfDefaultedField = keyof typeof LPBF_PROCESS_FALLBACKS;

/**
 * Class-level constants that deriveSpecimenProperties passes explicitly (per base metal or for every alloy). They are
 * unsourced heuristics, not measured or alloy-specific values, so they are flagged in defaultsApplied like the fallbacks.
 */
export const LPBF_DERIVED_HEURISTIC_FIELDS: readonly LpbfDefaultedField[] = [
  "thermalConductivity_k_WmK", "specificHeat_Cp_JkgK", "laserAbsorptivity", "thermalExpansion_CTE_10e6", "criticalGradient_G_Km",
];

/** Human labels for the disclosure UI. */
export const LPBF_DEFAULT_FIELD_LABELS: Record<LpbfDefaultedField, { label: string; unit: string }> = {
  thermalConductivity_k_WmK: { label: "Thermal conductivity", unit: "W/m·K" },
  density_rho_kgm3: { label: "Density", unit: "kg/m³" },
  specificHeat_Cp_JkgK: { label: "Specific heat", unit: "J/kg·K" },
  laserAbsorptivity: { label: "Laser absorptivity", unit: "" },
  thermalExpansion_CTE_10e6: { label: "Thermal expansion (CTE)", unit: "10⁻⁶/K" },
  criticalGradient_G_Km: { label: "Critical gradient G", unit: "K/m" },
  hotTearingSusceptibility: { label: "Hot-tearing susceptibility", unit: "" },
  beamDiameter_um: { label: "Beam diameter", unit: "µm" },
  scanStrategy: { label: "Scan strategy", unit: "" },
  beamProfile: { label: "Beam profile", unit: "" },
};

/** "Beam diameter 80 µm" style text for one flagged field. */
export function describeLpbfDefault(key: LpbfDefaultedField, lpbf: Pick<LpbfSpecimenState, LpbfDefaultedField>): string {
  const { label, unit } = LPBF_DEFAULT_FIELD_LABELS[key];
  return `${label} ${lpbf[key]}${unit ? ` ${unit}` : ""}`;
}

/** An explicit user edit of a field removes it from the flagged list; nothing else does. */
export function withoutEditedDefaults(flags: readonly LpbfDefaultedField[] | undefined, patch: object): LpbfDefaultedField[] {
  return (flags ?? []).filter(key => (patch as Record<string, unknown>)[key] === undefined);
}

export function withLpbfProcessDefaults(lpbf: Partial<LpbfSpecimenState> & Pick<LpbfSpecimenState, "recommendedLaserPower_W" | "recommendedScanSpeed_mms" | "recommendedHatch_um" | "recommendedLayer_um" | "recommendedPreheatTemp_C">): LpbfSpecimenState {
  // Flagged = filled from a fallback now, or already flagged by the caller (derived heuristics, earlier fills). Only an
  // explicit edit through the store actions (withoutEditedDefaults) un-flags a field.
  const flagged = new Set<LpbfDefaultedField>(lpbf.defaultsApplied ?? []);
  for (const key of Object.keys(LPBF_PROCESS_FALLBACKS) as LpbfDefaultedField[]) if (lpbf[key] === undefined) flagged.add(key);
  const defaultsApplied = (Object.keys(LPBF_PROCESS_FALLBACKS) as LpbfDefaultedField[]).filter(key => flagged.has(key));
  return {
    recommendedLaserPower_W: lpbf.recommendedLaserPower_W,
    recommendedScanSpeed_mms: lpbf.recommendedScanSpeed_mms,
    recommendedHatch_um: lpbf.recommendedHatch_um,
    recommendedLayer_um: lpbf.recommendedLayer_um,
    recommendedPreheatTemp_C: lpbf.recommendedPreheatTemp_C,
    thermalConductivity_k_WmK: lpbf.thermalConductivity_k_WmK ?? LPBF_PROCESS_FALLBACKS.thermalConductivity_k_WmK,
    density_rho_kgm3: lpbf.density_rho_kgm3 ?? LPBF_PROCESS_FALLBACKS.density_rho_kgm3,
    specificHeat_Cp_JkgK: lpbf.specificHeat_Cp_JkgK ?? LPBF_PROCESS_FALLBACKS.specificHeat_Cp_JkgK,
    laserAbsorptivity: lpbf.laserAbsorptivity ?? LPBF_PROCESS_FALLBACKS.laserAbsorptivity,
    thermalExpansion_CTE_10e6: lpbf.thermalExpansion_CTE_10e6 ?? LPBF_PROCESS_FALLBACKS.thermalExpansion_CTE_10e6,
    criticalGradient_G_Km: lpbf.criticalGradient_G_Km ?? LPBF_PROCESS_FALLBACKS.criticalGradient_G_Km,
    hotTearingSusceptibility: lpbf.hotTearingSusceptibility ?? LPBF_PROCESS_FALLBACKS.hotTearingSusceptibility,
    crackingMechanism: lpbf.crackingMechanism ?? "",
    mitigationRecommendation: lpbf.mitigationRecommendation ?? "",
    laserPower_W: lpbf.laserPower_W ?? lpbf.recommendedLaserPower_W,
    scanSpeed_mms: lpbf.scanSpeed_mms ?? lpbf.recommendedScanSpeed_mms,
    hatch_um: lpbf.hatch_um ?? lpbf.recommendedHatch_um,
    layer_um: lpbf.layer_um ?? lpbf.recommendedLayer_um,
    beamDiameter_um: lpbf.beamDiameter_um ?? LPBF_PROCESS_FALLBACKS.beamDiameter_um,
    preheatTemp_C: lpbf.preheatTemp_C ?? lpbf.recommendedPreheatTemp_C,
    scanStrategy: lpbf.scanStrategy ?? LPBF_PROCESS_FALLBACKS.scanStrategy,
    beamProfile: lpbf.beamProfile ?? LPBF_PROCESS_FALLBACKS.beamProfile,
    cadAssetName: lpbf.cadAssetName ?? "",
    specimenDoi: lpbf.specimenDoi ?? "",
    processSeed: lpbf.processSeed ?? 42,
    inclineAngle_deg: lpbf.inclineAngle_deg ?? 0,
    downskinOverhang_deg: lpbf.downskinOverhang_deg ?? 0,
    ...(defaultsApplied.length ? { defaultsApplied } : {}),
  };
}

export interface ActiveSpecimenState {
  id: string;
  name: string;
  chemicalFormula: string;
  category: string;
  baseMetal: BaseMetalType;
  composition: Record<string, number>; // element symbol -> wt%
  unit: "wt_pct" | "at_pct";
  
  // Thermodynamic and mechanical properties: null = unavailable. No validated composition-to-property model exists
  // here (see COMPOSITION_PROPERTY_UNAVAILABLE_NOTE); the old per-base linear formulas had no source.
  liquidus_C: number | null;
  solidus_C: number | null;
  freezingRange_C: number | null;
  solvus_C: number | null;
  stablePhases: string[];
  
  yieldStrength_25C_MPa: number | null;
  uts_25C_MPa: number | null;
  density_gcm3: number;
  youngsModulus_GPa: number | null;
  elongation_pct: number | null;
  
  // 3D LPBF Additive & Melt Pool Parameters (single Build Job source)
  lpbf: LpbfSpecimenState;
  
  // Crystallography & XRD (Propagated directly to XRD Lab)
  xrd: {
    crystalSystem: "FCC" | "BCC" | "HCP" | "Tetragonal" | "Other";
    spaceGroup: string;
    latticeA_A: number;
    latticeC_A?: number;
    targetPhases: string[];
    microstrain_pct: number;
    crystalliteSize_nm: number;
  };
  
  // Identity transfer never upgrades existing estimates to measured evidence.
  materialTransfer?: {sourceModule:string;sourceRecordId:string;compositionInterpretation:string;resultType:"Screening only";note:string};
  // Provenance & Digital Thread
  sourceTab: string;
  lastModified: number;
  isCustomModified: boolean;
}

export interface MaterialSpecimenStore {
  activeSpecimen: ActiveSpecimenState;
  
  // Actions
  updateComposition: (
    newComposition: Record<string, number>,
    customName?: string,
    forcedBaseMetal?: BaseMetalType,
    sourceTab?: string
  ) => void;
  setSpecimen: (specimen: Partial<ActiveSpecimenState>) => void;
  updateLpbfProcess: (patch: LpbfProcessPatch) => void;
  loadPreset: (presetId: string) => void;
  resetToDefault: () => void;
}

// ----------------------------------------------------------------------
// Physics Calculation Helpers
// ----------------------------------------------------------------------

export function detectBaseMetalFromComposition(comp: Record<string, number>): BaseMetalType {
  let highestElem = "Ni";
  let maxPct = -1;
  for (const [elem, pct] of Object.entries(comp)) {
    if (typeof pct === "number" && pct > maxPct) {
      maxPct = pct;
      highestElem = elem;
    }
  }

  if (highestElem === "Ni") return "Ni";
  if (highestElem === "Fe") return "Fe";
  if (highestElem === "Ti") return "Ti";
  if (highestElem === "Al") return "Al";
  if (highestElem === "Cu") return "Cu";
  if (highestElem === "Co") return "Co";
  if (highestElem === "Mg") return "Mg";
  if (["W", "Mo", "Ta", "Nb", "Re"].includes(highestElem)) return "Refractory";
  return "Other";
}

/** Tabulated elemental densities; single source in compositionPropertyAvailability. */
const ELEMENT_DENSITIES = ELEMENTAL_DENSITY_GCM3;

/**
 * Internal LPBF-input density only (feeds lpbf.density_rho_kgm3 and must stay stable): it uses 8.0 g/cm3 for an
 * element without a tabulated density and 8.2 g/cm3 for an empty composition. These fallbacks are NOT for display;
 * screens use ruleOfMixturesDensity(), which reports 'unavailable' instead.
 */
export function calculateAlloyDensity(comp: Record<string, number>): number {
  let totalMass = 0;
  let totalVolume = 0;

  for (const [elem, pct] of Object.entries(comp)) {
    if (typeof pct === "number" && pct > 0) {
      totalMass += pct;
      const rho = ELEMENT_DENSITIES[elem] || 8.0;
      totalVolume += pct / rho;
    }
  }

  if (totalVolume <= 0 || totalMass <= 0) return 8.2;
  return parseFloat((totalMass / totalVolume).toFixed(3));
}

// Generate chemical formula string from composition (e.g. Ni-16Cr-8.5Co-1.7Mo-2.6W-1.7Ta-3.4Al-3.4Ti)
export function generateChemicalFormula(comp: Record<string, number>, baseMetal: BaseMetalType): string {
  // Sort elements by percentage descending, with base metal first
  const entries = Object.entries(comp)
    .filter(([_, pct]) => typeof pct === "number" && pct > 0.05)
    .sort((a, b) => b[1] - a[1]);

  const baseEntry = entries.find(([el]) => el === baseMetal);
  const otherEntries = entries.filter(([el]) => el !== baseMetal);

  const parts: string[] = [];
  if (baseEntry) {
    parts.push(baseEntry[0]);
  }

  for (const [elem, pct] of otherEntries) {
    const formatted = Number.isInteger(pct) ? `${pct}` : pct.toFixed(1).replace(/\.0$/, "");
    parts.push(`${formatted}${elem}`);
  }

  return parts.join("-");
}

// Compute comprehensive physical, thermodynamic & additive parameters from composition
export function deriveSpecimenProperties(
  composition: Record<string, number>,
  customName?: string,
  forcedBase?: BaseMetalType
): Omit<ActiveSpecimenState, "id" | "sourceTab" | "lastModified" | "isCustomModified"> {
  const baseMetal = forcedBase || detectBaseMetalFromComposition(composition);
  const density_gcm3 = calculateAlloyDensity(composition);
  const density_rho_kgm3 = Math.round(density_gcm3 * 1000);
  const chemicalFormula = generateChemicalFormula(composition, baseMetal);

  // Normalize / compute key additions
  const cr = composition["Cr"] || 0;
  const mo = composition["Mo"] || 0;
  const w = composition["W"] || 0;
  const ta = composition["Ta"] || 0;
  const al = composition["Al"] || 0;
  const ti = composition["Ti"] || 0;
  const nb = composition["Nb"] || 0;
  const c = composition["C"] || 0;

  let crystalSystem: "FCC" | "BCC" | "HCP" | "Tetragonal" | "Other" = "FCC";
  let spaceGroup = "Fm-3m (225)";
  let latticeA_A = 3.595;
  let latticeC_A: number | undefined = undefined;
  let targetPhases: string[] = ["austenite-fcc", "gamma-prime-ni3al"];
  let thermalConductivity_k_WmK = 11.5;
  let specificHeat_Cp_JkgK = 435;
  let recommendedLaserPower_W = 285;
  let recommendedScanSpeed_mms = 960;
  let recommendedPreheatTemp_C = 120;
  let hotTearingSusceptibility: "Low" | "Moderate" | "High" = "Moderate";
  let crackingMechanism = "Interdendritic solute segregation during terminal solidification";
  let mitigationRecommendation = "Maintain bed preheat >=150°C and optimize volumetric energy density (VED).";

  if (baseMetal === "Ni") {
    // Nickel Superalloy Physics
    const gammaPrimeFormers = al + ti + ta + nb;
    const refractoryMoW = mo + w;

    // Internal screening index only: this unsourced liquidus-solidus spread still selects the hot-tearing class and the
    // recommended preheat below, which loadPreset copies into the live LPBF vector (kept unchanged on purpose). It is
    // never exposed as a liquidus, solidus or freezing range.
    const heuristicLiquidus_C = Math.round(1455 - (cr * 2.5 + mo * 4 + al * 8 + ti * 10 + c * 40));
    const heuristicSolidus_C = Math.round(heuristicLiquidus_C - (35 + gammaPrimeFormers * 4.5 + nb * 12 + c * 30));

    crystalSystem = "FCC";
    spaceGroup = "Fm-3m (225)";
    // Solute expansion on lattice parameter
    latticeA_A = parseFloat((3.524 + cr * 0.0018 + mo * 0.0035 + w * 0.0038 + ta * 0.0045 + al * 0.0022 + ti * 0.003).toFixed(3));

    if (nb > 2.5) {
      targetPhases = ["austenite-fcc", "gamma-double-prime", "laves-fe2nb"];
    } else if (gammaPrimeFormers > 3.0) {
      targetPhases = ["austenite-fcc", "gamma-prime-ni3al", "carbide-mc"];
    } else {
      targetPhases = ["austenite-fcc", "carbide-m23c6"];
    }

    thermalConductivity_k_WmK = parseFloat((11.0 + refractoryMoW * 0.3 - (cr + al) * 0.15).toFixed(1));
    specificHeat_Cp_JkgK = 435;
    recommendedLaserPower_W = 280;
    recommendedScanSpeed_mms = 940;
    
    const freezingRange = heuristicLiquidus_C - heuristicSolidus_C;
    if (freezingRange > 80 || (al + ti) > 4.5) {
      hotTearingSusceptibility = "High";
      recommendedPreheatTemp_C = 200;
      crackingMechanism = "Strain-age cracking and liquation cracking across high-angle grain boundaries (Al+Ti > 4.5%).";
      mitigationRecommendation = "Elevate build platform to 200–300°C; apply pulsed remelting or lower scan speed.";
    } else if (freezingRange > 45) {
      hotTearingSusceptibility = "Moderate";
      recommendedPreheatTemp_C = 100;
      crackingMechanism = "Interdendritic solute enrichment (Nb/Mo/Ti) forming low-melting terminal eutectics.";
      mitigationRecommendation = "Build plate preheat 100–150°C and meander scan rotation 67° to disperse thermal accumulation.";
    } else {
      hotTearingSusceptibility = "Low";
      recommendedPreheatTemp_C = 60;
      crackingMechanism = "Narrow solidification range limits liquid film rupture risk.";
      mitigationRecommendation = "Standard LPBF process window applicable.";
    }
  } else if (baseMetal === "Ti") {
    // Titanium Alloy Physics
    crystalSystem = "HCP";
    spaceGroup = "P6_3/mmc (194)";
    latticeA_A = 2.950;
    latticeC_A = 4.686;
    targetPhases = ["ti-alpha-hcp", "ti-beta-bcc"];

    thermalConductivity_k_WmK = 6.7;
    specificHeat_Cp_JkgK = 526;
    recommendedLaserPower_W = 240;
    recommendedScanSpeed_mms = 1200;
    recommendedPreheatTemp_C = 150;
    hotTearingSusceptibility = "Moderate";
    crackingMechanism = "Ultra-low thermal conductivity causes localized thermal shock and brittle martensitic alpha' transformation.";
    mitigationRecommendation = "Use 150–200°C baseplate preheat and high-purity argon (O2 < 100 ppm).";
  } else if (baseMetal === "Fe") {
    // Steel / Stainless Steel
    // Ni >= 8 (was > 8): nominal AISI 304 (Cr 18, Ni 8) was classed BCC.
    crystalSystem = cr > 12 && (composition["Ni"] || 0) >= 8 ? "FCC" : "BCC";
    spaceGroup = crystalSystem === "FCC" ? "Fm-3m (225)" : "Im-3m (229)";
    latticeA_A = crystalSystem === "FCC" ? 3.590 : 2.866;
    targetPhases = crystalSystem === "FCC" ? ["austenite-fcc", "delta-ferrite"] : ["ferrite-bcc", "cementite-fe3c"];

    thermalConductivity_k_WmK = crystalSystem === "FCC" ? 15.2 : 28.0;
    specificHeat_Cp_JkgK = 500;
    recommendedLaserPower_W = 200;
    recommendedScanSpeed_mms = 850;
    recommendedPreheatTemp_C = 80;
    hotTearingSusceptibility = "Low";
    crackingMechanism = "Primary ferritic-austenitic solidification mode buffers thermal contraction.";
    mitigationRecommendation = "Standard build parameters with adequate support volume.";
  } else if (baseMetal === "Al") {
    // Aluminum Alloy Physics
    crystalSystem = "FCC";
    spaceGroup = "Fm-3m (225)";
    latticeA_A = 4.049;
    targetPhases = ["al-matrix-fcc", "mg2si-beta"];
    thermalConductivity_k_WmK = 130.0;
    specificHeat_Cp_JkgK = 910;
    recommendedLaserPower_W = 350;
    recommendedScanSpeed_mms = 1300;
    recommendedPreheatTemp_C = 160;
    hotTearingSusceptibility = "Moderate";
    crackingMechanism = "Wide freezing range and high thermal conductivity create rapid solidification contraction.";
    mitigationRecommendation = "High power laser (350W+) with 150°C preheat to mitigate keyhole porosity and lack-of-fusion.";
  }

  // Auto-generate high-precision descriptive name if not provided
  const name = customName || `${baseMetal === "Ni" ? "Superalloy" : baseMetal} Specimen (${chemicalFormula})`;

  return {
    name,
    chemicalFormula,
    category: materialCategoryForBase(baseMetal),
    baseMetal,
    composition,
    unit: "wt_pct",
    liquidus_C: null,
    solidus_C: null,
    freezingRange_C: null,
    solvus_C: null,
    stablePhases: targetPhases,
    yieldStrength_25C_MPa: null,
    uts_25C_MPa: null,
    density_gcm3,
    youngsModulus_GPa: null,
    elongation_pct: null,
    lpbf: withLpbfProcessDefaults({
      recommendedLaserPower_W,
      recommendedScanSpeed_mms,
      recommendedHatch_um: 100,
      recommendedLayer_um: 40,
      recommendedPreheatTemp_C,
      thermalConductivity_k_WmK,
      density_rho_kgm3,
      specificHeat_Cp_JkgK,
      // UI default, not a measurement (0.68 / 0.35 / 0.58 are form placeholders; Python's authority drives the solver).
      laserAbsorptivity: baseMetal === "Ti" ? 0.68 : baseMetal === "Al" ? 0.35 : 0.58,
      thermalExpansion_CTE_10e6: baseMetal === "Ni" ? 13.0 : baseMetal === "Ti" ? 8.6 : 16.5,
      criticalGradient_G_Km: 1.5e7,
      hotTearingSusceptibility,
      crackingMechanism,
      mitigationRecommendation,
      defaultsApplied: [...LPBF_DERIVED_HEURISTIC_FIELDS],
    }),
    xrd: {
      crystalSystem,
      spaceGroup,
      latticeA_A,
      latticeC_A,
      targetPhases,
      microstrain_pct: 0.22,
      crystalliteSize_nm: 32,
    },
  };
}

// ----------------------------------------------------------------------
// Standard High-Performance Presets
// ----------------------------------------------------------------------

export const SPECIMEN_PRESETS: Record<string, { name: string; composition: Record<string, number>; base: BaseMetalType; description: string }> = {
  // Custom user superalloy from the critique prompt
  "custom-ni-superalloy": {
    name: "AeroTurbine-850 (Ni-16Cr-8.5Co-1.7Mo-2.6W-1.7Ta-3.4Al-3.4Ti)",
    base: "Ni",
    description: "Advanced gamma-prime precipitation hardened nickel superalloy optimized for 850°C marine turbine blades.",
    composition: {
      Ni: 62.7,
      Cr: 16.0,
      Co: 8.5,
      Al: 3.4,
      Ti: 3.4,
      W: 2.6,
      Mo: 1.7,
      Ta: 1.7,
    },
  },
  "inconel-718": {
    name: "Inconel 718 (AMS 5662 / UNS N07718)",
    base: "Ni",
    description: "Niobium-modified gamma-double-prime (Ni3Nb) superalloy with high weldability and tensile strength.",
    composition: {
      Ni: 52.5,
      Cr: 19.0,
      Fe: 18.5,
      Nb: 5.15,
      Mo: 3.05,
      Ti: 0.95,
      Al: 0.55,
      C: 0.04,
      Co: 0.35,
    },
  },
  "ti-6al-4v": {
    name: "Ti-6Al-4V Grade 23 ELI (ASTM F3001)",
    base: "Ti",
    description: "Lightweight, damage-tolerant alpha-beta titanium alloy with low interstitial oxygen for additive parts.",
    composition: {
      Ti: 89.2,
      Al: 6.2,
      V: 4.1,
      Fe: 0.25,
      O: 0.13,
      C: 0.05,
    },
  },
  "ss-316l": {
    name: "AISI 316L Stainless Steel (UNS S31603)",
    base: "Fe",
    description: "Molybdenum-bearing austenitic stainless steel with excellent corrosion resistance and ductile fracture.",
    composition: {
      Fe: 65.5,
      Cr: 17.5,
      Ni: 12.0,
      Mo: 2.5,
      Mn: 1.8,
      Si: 0.6,
      C: 0.02,
    },
  },
  "alsi10mg": {
    name: "AlSi10Mg Additive Lightweight",
    base: "Al",
    description: "Near-eutectic aluminum-silicon casting alloy with high thermal conductivity and rapid hardening kinetics.",
    composition: {
      Al: 89.5,
      Si: 9.8,
      Mg: 0.45,
      Fe: 0.20,
      Mn: 0.05,
    },
  },
};

// Keep the default within the LPBF material allowlist; experimental presets must be explicitly selected.
const INITIAL_SPECIMEN_PROPS = deriveSpecimenProperties(
  SPECIMEN_PRESETS["inconel-718"].composition,
  SPECIMEN_PRESETS["inconel-718"].name,
  SPECIMEN_PRESETS["inconel-718"].base
);

const INITIAL_SPECIMEN: ActiveSpecimenState = {
  id: "specimen-inconel-718",
  ...INITIAL_SPECIMEN_PROPS,
  sourceTab: "Alloy Formulator (Tab 1)",
  lastModified: Date.now(),
  isCustomModified: false,
};

export const MATERIAL_SPECIMEN_STORE_VERSION = 4;

/**
 * Version 3 nulls the composition-heuristic properties (liquidus ... elongation) of the persisted specimen. Everything
 * else, the live LPBF process vector included, is kept as persisted. Without a migrate function zustand would drop an
 * older blob entirely (and with it the user's process settings).
 */
export function migrateMaterialSpecimenStoreState(persisted: unknown, version: number): unknown {
  if (version >= MATERIAL_SPECIMEN_STORE_VERSION || !persisted || typeof persisted !== "object" || Array.isArray(persisted)) return persisted;
  const state = persisted as Record<string, unknown>;
  if (!state.activeSpecimen || typeof state.activeSpecimen !== "object") return state;
  const specimen = version < 3 ? withoutCompositionHeuristicProperties(state.activeSpecimen) : state.activeSpecimen;
  return { ...state, activeSpecimen: withLegacyDefaultsFlagged(specimen) };
}

/**
 * Version 4 adds LpbfSpecimenState.defaultsApplied. A record without it has unknown provenance, so each field that still
 * equals a fallback or the value this app derives for that composition is flagged (a user edit to another value is not).
 * Numeric values are untouched.
 */
function withLegacyDefaultsFlagged(specimenValue: unknown): unknown {
  const specimen = specimenValue as { lpbf?: Record<string, unknown>; composition?: Record<string, number>; name?: string; baseMetal?: BaseMetalType };
  const lpbf = specimen.lpbf;
  if (!lpbf || typeof lpbf !== "object" || Array.isArray(lpbf.defaultsApplied)) return specimenValue;
  let derivedLpbf: Record<string, unknown> = {};
  try {
    if (specimen.composition) derivedLpbf = deriveSpecimenProperties(specimen.composition, specimen.name, specimen.baseMetal).lpbf as unknown as Record<string, unknown>;
  } catch { /* unknown composition: compare against the fallbacks only */ }
  const defaultsApplied = (Object.keys(LPBF_PROCESS_FALLBACKS) as LpbfDefaultedField[])
    .filter(key => lpbf[key] === undefined || lpbf[key] === LPBF_PROCESS_FALLBACKS[key] || (LPBF_DERIVED_HEURISTIC_FIELDS.includes(key) && lpbf[key] === derivedLpbf[key]));
  return { ...specimen, lpbf: { ...lpbf, ...(defaultsApplied.length ? { defaultsApplied } : {}) } };
}

// ----------------------------------------------------------------------
// Universal Zustand Reactive Store
// ----------------------------------------------------------------------

export const useMaterialSpecimenStore = create<MaterialSpecimenStore>()(
  persist(
    (set, get) => ({
      activeSpecimen: INITIAL_SPECIMEN,

      updateComposition: (newComposition, customName, forcedBaseMetal, sourceTab = "Alloy Formulator (Tab 1)") => {
        const previousProcess = get().activeSpecimen?.lpbf;
        const derived = deriveSpecimenProperties(newComposition, customName, forcedBaseMetal);
        const nextSpecimen: ActiveSpecimenState = {
          id: materialProfileIdentity(derived.name, derived.baseMetal, newComposition),
          ...derived,
          lpbf: withLpbfProcessDefaults({
            ...derived.lpbf,
            laserPower_W: previousProcess?.laserPower_W,
            scanSpeed_mms: previousProcess?.scanSpeed_mms,
            hatch_um: previousProcess?.hatch_um,
            layer_um: previousProcess?.layer_um,
            beamDiameter_um: previousProcess?.beamDiameter_um,
            preheatTemp_C: previousProcess?.preheatTemp_C,
            scanStrategy: previousProcess?.scanStrategy,
            beamProfile: previousProcess?.beamProfile,
            cadAssetName: previousProcess?.cadAssetName,
            specimenDoi: previousProcess?.specimenDoi,
            // Derived class heuristics are always flagged; the carried-over beam/scan/profile keep their previous flag.
            defaultsApplied: [
              ...LPBF_DERIVED_HEURISTIC_FIELDS,
              ...(previousProcess?.defaultsApplied ?? []).filter(key => key === "beamDiameter_um" || key === "scanStrategy" || key === "beamProfile"),
            ],
          }),
          sourceTab,
          lastModified: Date.now(),
          isCustomModified: true,
        };

        set({ activeSpecimen: nextSpecimen });

        // Bridge to pipeline for modules that also listen to data pipeline
        try {
          // HV is never measured here: steel-only estimate from the composition-based yield strength (Pavlina & Van
          // Tyne 2008) or unavailable. The old rule HV ~ YS/3.1 for every alloy had no source.
          const hardnessEstimate = estimateSpecimenHardnessHV({
            baseMetal: nextSpecimen.baseMetal,
            crystalSystem: nextSpecimen.xrd?.crystalSystem,
            composition: nextSpecimen.composition,
            unit: nextSpecimen.unit,
            yieldStrength_MPa: nextSpecimen.yieldStrength_25C_MPa,
          });
          const pipelinePayload: PipelineMaterialPayload = {
            id: nextSpecimen.id,
            name: nextSpecimen.name,
            category: nextSpecimen.category,
            // The shared specimen carries no standard designation; never a pseudo-standard label.
            standard: "",
            sourceModule: sourceTab,
            timestamp: Date.now(),
            composition: nextSpecimen.composition,
            compositionUnit: nextSpecimen.unit,
            compositionInterpretation: "nominal",
            baseMetal: nextSpecimen.baseMetal as any,
            yieldStrength: nextSpecimen.yieldStrength_25C_MPa,
            tensileStrength: nextSpecimen.uts_25C_MPa,
            youngsModulus: nextSpecimen.youngsModulus_GPa,
            density: nextSpecimen.density_gcm3,
            elongation: nextSpecimen.elongation_pct,
            hardness: hardnessEstimate.note,
            hardnessHV: hardnessEstimate.hv,
            hardnessHVSource: hardnessEstimate.hv === null ? "unavailable" : "estimate-from-yield",
            poissonsRatio: 0.31,
            thermalConductivity: nextSpecimen.lpbf.thermalConductivity_k_WmK,
            kineticProfile: {
              id: nextSpecimen.id,
              name: nextSpecimen.name,
              baseMetal: (["Ni", "Fe", "Ti", "Al"].includes(nextSpecimen.baseMetal) ? nextSpecimen.baseMetal : "Ni") as any,
              standardRef: "",
              initialGrainSize_um: 25,
              grainGrowthExponent_n: 2.1,
              activationEnergy_kJ_mol: 285,
              preExponential_k0: 1.2e-4,
              solvusTemp_C: nextSpecimen.solvus_C,
              criticalTemp_Ac3_C: null,
              solidusTemp_C: nextSpecimen.solidus_C,
              precipitateType: "Intermetallic / Carbides",
              initialPrecipVolFrac: 15,
              precipMeanRadius_nm: 25,
              // Unsourced constants (750 MPa·µm^0.5, 65 MPa·√m, L/LT/ST factors) removed: unavailable.
              hallPetch_ky_MPa_um05: null,
            } as any,
            hardnessProfile: {
              id: nextSpecimen.id,
              name: nextSpecimen.name,
              category: (["Nickel Superalloy", "Titanium Alloy", "Aluminum Alloys", "Steels & Irons", "Cobalt / Bio"].includes(nextSpecimen.category)
                ? nextSpecimen.category
                : "Nickel Superalloy") as any,
              crystalStructure: nextSpecimen.xrd.crystalSystem as any,
              // estimate or unavailable, see hardnessHVSource above
              defaultHardnessHV: hardnessEstimate.hv ?? undefined,
              hardnessHV: hardnessEstimate.hv,
              measuredYield_MPa: nextSpecimen.yieldStrength_25C_MPa,
              measuredUTS_MPa: nextSpecimen.uts_25C_MPa,
              strainHardeningExponent_n: 0.15,
              workHardeningExponent_n: 0.15,
              strengthCoefficient_K_MPa: null,
              cahoon_m: 0.33,
              tabor_c: 2.95,
              taborConstraintFactor_c: 2.95,
              hollomon_alpha: 0.002,
              elasticModulus_E_GPa: nextSpecimen.youngsModulus_GPa,
              youngsModulus_E_GPa: nextSpecimen.youngsModulus_GPa,
              poissonsRatio_nu: 0.31,
              poissonsRatio: 0.31,
              uniformElongation_pct: nextSpecimen.elongation_pct,
              fractureToughness_K1c_MPa_sqrt_m: null,
              estimatedK1c_MPam05: null,
              anisotropyFactors: null,
              description: `Shared specimen composition (${nextSpecimen.chemicalFormula})`,
              standardRef: "",
            } as any,
            xrdProfile: {
              crystalSystem: nextSpecimen.xrd.crystalSystem,
              spaceGroup: nextSpecimen.xrd.spaceGroup,
              latticeA_A: nextSpecimen.xrd.latticeA_A,
              latticeC_A: nextSpecimen.xrd.latticeC_A,
              primaryPhases: nextSpecimen.stablePhases,
              peaks: [],
            },
            icmeProfile: {
              liquidusTemp_C: nextSpecimen.liquidus_C,
              solidusTemp_C: nextSpecimen.solidus_C,
              solvusTemp_C: nextSpecimen.solvus_C,
              dominantPhases: nextSpecimen.stablePhases,
            },
          };
          setActivePipelineMaterial(pipelinePayload);
        } catch (e) {
          console.warn("[MaterialSpecimenStore] Pipeline sync skipped:", e);
        }
      },

      setSpecimen: (partial) => {
        set((state) => ({
          activeSpecimen: {
            ...state.activeSpecimen,
            ...partial,
            lpbf: partial.lpbf
              ? withLpbfProcessDefaults({ ...state.activeSpecimen.lpbf, ...partial.lpbf, defaultsApplied: partial.lpbf.defaultsApplied ?? withoutEditedDefaults(state.activeSpecimen.lpbf.defaultsApplied, partial.lpbf) })
              : state.activeSpecimen.lpbf,
            lastModified: Date.now(),
            isCustomModified: true,
          },
        }));
      },

      updateLpbfProcess: (patch) => {
        set((state) => ({
          activeSpecimen: {
            ...state.activeSpecimen,
            lpbf: withLpbfProcessDefaults({ ...state.activeSpecimen.lpbf, ...patch, defaultsApplied: withoutEditedDefaults(state.activeSpecimen.lpbf.defaultsApplied, patch) }),
            lastModified: Date.now(),
            isCustomModified: true,
          },
        }));
      },

      loadPreset: (presetId) => {
        const preset = SPECIMEN_PRESETS[presetId];
        if (!preset) return;
        get().updateComposition(preset.composition, preset.name, preset.base, `Preset (${preset.name})`);
        const rec = get().activeSpecimen.lpbf;
        get().updateLpbfProcess({
          laserPower_W: rec.recommendedLaserPower_W,
          scanSpeed_mms: rec.recommendedScanSpeed_mms,
          hatch_um: rec.recommendedHatch_um,
          layer_um: rec.recommendedLayer_um,
          preheatTemp_C: rec.recommendedPreheatTemp_C,
        });
      },

      resetToDefault: () => {
        set({ activeSpecimen: INITIAL_SPECIMEN });
      },
    }),
    {
      name: "metallix_active_material_specimen_v2",
      version: MATERIAL_SPECIMEN_STORE_VERSION,
      migrate: (persisted, version) => migrateMaterialSpecimenStoreState(persisted, version) as MaterialSpecimenStore,
      partialize: (state) => ({ activeSpecimen: state.activeSpecimen }),
      merge: (persisted, current) => {
        const persistedState = persisted as Partial<MaterialSpecimenStore> | undefined;
        const specimen = persistedState?.activeSpecimen;
        if (!specimen) return current;
        return {
          ...current,
          ...persistedState,
          activeSpecimen: {
            ...current.activeSpecimen,
            ...specimen,
            lpbf: withLpbfProcessDefaults({
              ...current.activeSpecimen.lpbf,
              ...specimen.lpbf,
              // The persisted record is authoritative about its own defaults (migrate flags legacy records); fields it lacks
              // entirely are taken from the fresh preset and flagged. Never inherit the fresh preset's own list.
              defaultsApplied: [
                ...(specimen.lpbf?.defaultsApplied ?? []),
                ...(Object.keys(LPBF_PROCESS_FALLBACKS) as LpbfDefaultedField[]).filter(key => specimen.lpbf?.[key] === undefined),
              ],
            }),
          },
        };
      },
    }
  )
);
