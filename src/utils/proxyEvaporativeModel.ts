import { canonicalLpbfMaterialName } from './lpbfMaterialIdentity';
import {
  PROXY_EVAPORATIVE_JOB_TYPE, PROXY_EVAPORATIVE_MODELS, type ProxyEvaporativeAlloy, type ProxyEvaporativeInput,
} from '../services/lpbfSimulationService';

export type ProxySurfaceMode = 'bare-plate' | 'powder-layer';

/**
 * UI default track: the solver's 600 um default. Measured 2026-10-27 on the reference CPU with the solver CLI
 * (mesh defaults, 80 C): 316L 200 W / 800 mm/s / 80 um took 16 s; IN718 285 W / 960 mm/s / 67 um took 25 s.
 */
export const PROXY_EVAPORATIVE_TRACK_UM = 600;

/** Names of the scenario inputs that no source gives for SS316 or Ni; at their defaults the output is Unresolved. */
export const PROXY_UNSOURCED_INPUTS = ['transitionLow_K', 'transitionHigh_K'] as const;

export interface ProxyAlloyProfile {
  alloy: ProxyEvaporativeAlloy; shortName: string;
  /** Liquidus of the solver's proxy material (K); the lower bound for transitionLow_K, as the Python solver enforces. */
  liquidus_K: number; label: string; disclosure: string; runtime: string;
  /** Declared scenario. Thresholds are unsourced defaults; see each entry for the sourced inputs. Not fitted to measurements. */
  scenario: { transitionLow_K: number; transitionHigh_K: number; ambientPressure_Pa: number; returnFraction: number; maxTemperature_K: number; surfaceTension_N_m: number };
}

export const PROXY_ALLOY_PROFILES: Record<ProxyEvaporativeAlloy, ProxyAlloyProfile> = {
  '316L Stainless Steel': {
    alloy: '316L Stainless Steel', shortName: '316L', liquidus_K: 1723, runtime: 'about 16 s',
    label: '316L evaporative surface, Gan 2021 SS316 proxy (research)',
    disclosure: 'Thermal and vapour constants are SS316 values (Gan 2021 SI Table 1, citing Valencia and Quested 2013) transferred to 316L as one effective Fe-rich vapour species; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.',
    // Return fraction 0.18 is Gan SI Table 2 (retro-diffusion coefficient); surface tension 1.87 N/m is Gan SI Table 1 SS316.
    scenario: { transitionLow_K: 3022, transitionHigh_K: 3522, ambientPressure_Pa: 101325, returnFraction: 0.18, maxTemperature_K: 5000, surfaceTension_N_m: 1.87 },
  },
  'Inconel 718': {
    alloy: 'Inconel 718', shortName: 'IN718', liquidus_K: 1609, runtime: 'about 25 s',
    label: 'IN718 evaporative surface, Fang 2021 thermal profile with a pure-Ni vapour proxy (research)',
    disclosure: 'Thermal properties are IN718 model inputs of Fang 2021 (SI Tables 2, 4, 7; k and cp held constant above 1573 K); the vapour law is pure Ni (Knapp 2019 Table 3 Ni row, NIST Ni atomic weight) used as a single-species proxy for IN718; selective evaporation, activity and composition change, melt flow, surface motion, plume and keyhole geometry are not modelled; the recoil/capillary gate is a model criterion, not an observed keyhole.',
    // Return fraction 0.18 is transferred from Gan SI Table 2; surface tension 1.882 N/m is Mills 2002 IN718 Table 1 (1336 C).
    scenario: { transitionLow_K: 3083, transitionHigh_K: 3583, ambientPressure_Pa: 101325, returnFraction: 0.18, maxTemperature_K: 5000, surfaceTension_N_m: 1.882 },
  },
};

/** The proxy alloy for a selected material, or undefined when the material has no proxy evaporative model. */
export function proxyAlloyFor(material: string): ProxyEvaporativeAlloy | undefined {
  const name = canonicalLpbfMaterialName(material);
  return Object.prototype.hasOwnProperty.call(PROXY_EVAPORATIVE_MODELS, name) ? name as ProxyEvaporativeAlloy : undefined;
}

export type ProxyAvailability = { available: true; alloy: ProxyEvaporativeAlloy } | { available: false; code: 'wrong-alloy' | 'powder-layer'; reason: string };

export function proxyEvaporativeAvailability(material: string, surfaceMode: ProxySurfaceMode): ProxyAvailability {
  const alloy = proxyAlloyFor(material);
  if (!alloy) {
    return { available: false, code: 'wrong-alloy', reason: `Unavailable: this model exists only for 316L and IN718, and the selected material is ${material || 'not set'}.` };
  }
  if (surfaceMode !== 'bare-plate') {
    return { available: false, code: 'powder-layer', reason: 'Unavailable: the evaporative surface model supports a bare plate only. A powder layer is not modelled.' };
  }
  return { available: true, alloy };
}

export interface ProxyThresholds { transitionLow_K: number; transitionHigh_K: number }

export type ProxyThresholdCheck = { ok: true; thresholds: ProxyThresholds } | { ok: false; reason: string };

/** The declared default thresholds of an alloy (unsourced). */
export const proxyDefaultThresholds = (alloy: ProxyEvaporativeAlloy): ProxyThresholds => ({
  transitionLow_K: PROXY_ALLOY_PROFILES[alloy].scenario.transitionLow_K, transitionHigh_K: PROXY_ALLOY_PROFILES[alloy].scenario.transitionHigh_K,
});

const parseKelvin = (text: string): number => {
  const trimmed = text.trim();
  return !/^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/i.test(trimmed) ? NaN : Number(trimmed);
};

/**
 * Same rule as the Python solver (lpbf_proxy_evaporation.validate_config):
 * liquidus <= low < high <= maxTemperature_K, and maxTemperature_K <= 6000 K. Returns the reason instead of a request.
 */
export function validateProxyThresholds(alloy: ProxyEvaporativeAlloy, lowText: string, highText: string): ProxyThresholdCheck {
  const { liquidus_K, shortName, scenario } = PROXY_ALLOY_PROFILES[alloy];
  const low = parseKelvin(lowText);
  const high = parseKelvin(highText);
  if (!Number.isFinite(low)) return { ok: false, reason: 'Lower transition threshold must be a number in K.' };
  if (!Number.isFinite(high)) return { ok: false, reason: 'Upper transition threshold must be a number in K.' };
  if (low < liquidus_K) return { ok: false, reason: `Lower transition threshold must be at least the ${shortName} liquidus, ${liquidus_K} K.` };
  if (!(low < high)) return { ok: false, reason: 'Lower transition threshold must be below the upper one.' };
  if (high > scenario.maxTemperature_K) return { ok: false, reason: `Upper transition threshold must not exceed the scenario ceiling, ${scenario.maxTemperature_K} K.` };
  return { ok: true, thresholds: { transitionLow_K: low, transitionHigh_K: high } };
}

export function buildProxyEvaporativeInput(alloy: ProxyEvaporativeAlloy,
  process: { power_W: number; speed_mm_s: number; beamDiameter_um: number; preheat_C: number },
  trackLength_um: number = PROXY_EVAPORATIVE_TRACK_UM, thresholds: ProxyThresholds = proxyDefaultThresholds(alloy)): ProxyEvaporativeInput {
  return {
    jobType: PROXY_EVAPORATIVE_JOB_TYPE,
    config: {
      material: alloy, power_W: process.power_W, speed_mm_s: process.speed_mm_s, beamDiameter_um: process.beamDiameter_um,
      preheat_C: process.preheat_C, trackLength_um, evaporation: { ...PROXY_ALLOY_PROFILES[alloy].scenario, ...thresholds },
    },
  };
}
