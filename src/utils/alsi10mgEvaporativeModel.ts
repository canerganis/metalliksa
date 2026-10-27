import { canonicalLpbfMaterialName } from './lpbfMaterialIdentity';
import {
  ALSI10MG_EVAPORATIVE_JOB_TYPE, type AlSi10MgEvaporativeConfig, type AlSi10MgEvaporativeInput,
} from '../services/lpbfSimulationService';

export type AlSi10MgSurfaceMode = 'bare-plate' | 'powder-layer';
export const ALSI10MG_EVAPORATIVE_LABEL = 'AlSi10Mg evaporative surface, Al6061 proxy (research)';
export const ALSI10MG_PROXY_DISCLOSURE = 'Thermal and vapour constants are Al6061 values (Gan 2021 SI Tables 1-2, citing Valencia and Quested 2013) used as an Al-rich proxy for AlSi10Mg; Mg and Si selective evaporation and the real AlSi10Mg composition are not modelled.';

/**
 * UI default track. Measured 2026-10-27 on the reference CPU (300 W / 1300 mm/s / 100 um / 80 C, solver mesh defaults,
 * CLI): 600 um took 16 s, under the 120 s budget, so the solver's 600 um default is kept.
 */
export const ALSI10MG_EVAPORATIVE_TRACK_UM = 600;

/**
 * Declared scenario of the evaporation law. Thresholds 2800/3200 K and the return fraction 0.18 (retro-diffusion
 * coefficient) are Gan 2021 SI Table 2 values; surface tension 0.91 N/m is Gan SI Table 1 (Al6061). Ambient pressure
 * and the 5000 K ceiling are declared scenario choices. Not fitted to measurements.
 */
export const ALSI10MG_EVAPORATION_SCENARIO = {
  transitionLow_K: 2800, transitionHigh_K: 3200, ambientPressure_Pa: 101325, returnFraction: 0.18,
  maxTemperature_K: 5000, surfaceTension_N_m: 0.91,
} as const;

export type AlSi10MgAvailability = { available: true } | { available: false; code: 'wrong-alloy' | 'powder-layer'; reason: string };

export function alsi10mgEvaporativeAvailability(material: string, surfaceMode: AlSi10MgSurfaceMode): AlSi10MgAvailability {
  if (canonicalLpbfMaterialName(material) !== 'AlSi10Mg') {
    return { available: false, code: 'wrong-alloy', reason: `Unavailable: this model exists only for AlSi10Mg, and the selected material is ${material || 'not set'}.` };
  }
  if (surfaceMode !== 'bare-plate') {
    return { available: false, code: 'powder-layer', reason: 'Unavailable: the evaporative surface model supports a bare plate only. A powder layer is not modelled.' };
  }
  return { available: true };
}

export function buildAlSi10MgEvaporativeInput(process: { power_W: number; speed_mm_s: number; beamDiameter_um: number; preheat_C: number },
  trackLength_um: number = ALSI10MG_EVAPORATIVE_TRACK_UM): AlSi10MgEvaporativeInput {
  const config: AlSi10MgEvaporativeConfig = {
    power_W: process.power_W, speed_mm_s: process.speed_mm_s, beamDiameter_um: process.beamDiameter_um,
    preheat_C: process.preheat_C, trackLength_um, evaporation: { ...ALSI10MG_EVAPORATION_SCENARIO },
  };
  return { jobType: ALSI10MG_EVAPORATIVE_JOB_TYPE, config };
}
