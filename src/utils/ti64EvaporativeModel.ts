import { canonicalLpbfMaterialName } from './lpbfMaterialIdentity';
import { TI64_EVAPORATIVE_JOB_TYPE, type Ti64EvaporativeConfig, type Ti64EvaporativeInput } from '../services/lpbfSimulationService';

export type Ti64SurfaceMode = 'bare-plate' | 'powder-layer';
export const TI64_EVAPORATIVE_LABEL = 'Ti-6Al-4V evaporative surface (research)';

/**
 * UI default track. Measured on the reference CPU (A2, 2026-10-20, 150 W / 1000 mm/s / 80 um / 80 C, solver mesh
 * defaults): 600 um took 20.8 s, well under the 120 s budget, so the solver's own 600 um default is kept.
 */
export const TI64_EVAPORATIVE_TRACK_UM = 600;

/** Declared scenario inputs of the evaporation law (RESULTS_ti64_evaporative_cpu_2026-10-20). Not fitted to measurements. */
export const TI64_EVAPORATION_SCENARIO = {
  transitionLow_K: 3560, transitionHigh_K: 4000, ambientPressure_Pa: 101325, returnFraction: 0.2,
  maxTemperature_K: 5000, surfaceTension_N_m: 1.65,
} as const;

export type Ti64Availability = { available: true } | { available: false; code: 'wrong-alloy' | 'powder-layer'; reason: string };

export function ti64EvaporativeAvailability(material: string, surfaceMode: Ti64SurfaceMode): Ti64Availability {
  if (canonicalLpbfMaterialName(material) !== 'Ti-6Al-4V') {
    return { available: false, code: 'wrong-alloy', reason: `Unavailable: this model exists only for Ti-6Al-4V, and the selected material is ${material || 'not set'}.` };
  }
  if (surfaceMode !== 'bare-plate') {
    return { available: false, code: 'powder-layer', reason: 'Unavailable: the evaporative surface model supports a bare plate only. A powder layer is not modelled.' };
  }
  return { available: true };
}

export function buildTi64EvaporativeInput(process: { power_W: number; speed_mm_s: number; beamDiameter_um: number; preheat_C: number },
  trackLength_um: number = TI64_EVAPORATIVE_TRACK_UM): Ti64EvaporativeInput {
  const config: Ti64EvaporativeConfig = {
    power_W: process.power_W, speed_mm_s: process.speed_mm_s, beamDiameter_um: process.beamDiameter_um,
    preheat_C: process.preheat_C, trackLength_um, evaporation: { ...TI64_EVAPORATION_SCENARIO },
  };
  return { jobType: TI64_EVAPORATIVE_JOB_TYPE, config };
}
