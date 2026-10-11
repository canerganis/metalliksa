/**
 * MetalliX Python HPC Subsystem & Proxy Client Service
 * Dispatches heavy, CPU-intensive calculations (CALPHAD Gibbs minimization, elastic-constant homogenisation, PHACOMP,
 * XRD Peak Deconvolution, 3D Goldak LPBF Thermal)
 * to the backend Python 3.10 runtime with automatic fallback to client TypeScript engines.
 */

import type { MeltPoolExtentStatus } from "../utils/meltPoolExtentStatus";
import { parseMachineCalibratedResult, parseMachineCalibrationStatus, type MachineCalibratedBlock, type MachineCalibratedResult, type MachineCalibrationStatus } from "../data/lpbfMachineCalibration";
import {
  MultiComponentAlloyComposition,
  MultiComponentSolveResult,
  solveMultiComponentEquilibrium,
} from "../physics/calphadMultiComponentSolver";
import { parseTDBFile, PRELOADED_MULTI_COMPONENT_TDB } from "../physics/tdbParser";
import { createSeededRandom } from "../utils/seededRandom";
import { PythonValidationError, validationErrorFromResponse } from "../utils/pythonValidationError";
import {
  CLIENT_DATABASE_LABEL,
  CLIENT_MODEL_LABEL,
  parseCalphadUnavailable,
  type CalphadFieldStatus,
  type CalphadUnavailable,
} from "../utils/calphadDisplay";
import type {
  CalphadModelCacheInfo,
  CalphadPartitionRow,
  CalphadScheilBlock,
  CalphadScheilPoint,
  CalphadSystemCoverage,
} from "../utils/calphadResultDisplay";

export interface PersistentIPCDiagnostics {
  success: boolean;
  status: "online" | "restarting" | "initializing" | "fallback_mode";
  isPersistent: boolean;
  channels?: {
    unixSocket: { path: string; active: boolean };
    httpMicroservice: { url: string; active: boolean };
  };
  requestsProcessed?: number;
  avgLatencyMs?: number;
  uptimeSeconds?: number;
  warmModulesCount?: number;
  lastError?: string | null;
}

export interface PythonEngineStatus {
  online: boolean;
  status: string;
  pythonVersion?: string;
  platform?: string;
  durationMs?: number;
  warm?: boolean;
  channel?: string;
  ipcDaemon?: PersistentIPCDiagnostics;
  /** Server-side qualifier sent instead of a per-subsystem map (currently "unverified"). */
  subsystemStatus?: string;
  subsystems?: {
    calphad_solver?: { available: boolean; description?: string };
    cnls_fitting_solver?: { available: boolean; description?: string };
    xrd_peak_deconvolution?: { available: boolean; description?: string };
    lpbf_thermal_solver?: { available: boolean; description?: string };
    pourbaix_solver?: { available: boolean; description?: string };
    kinetics_ttt_cct_solver?: { available: boolean; description?: string };
  };
}

export interface PythonCalphadDatabaseEntry {
  id: string;
  fileName: string;
  name: string;
  description: string;
  elements: string[];
  primaryPhases: string[];
  source: string;
  suitability: string;
  /** "assessment" or "test-fixture"; a test fixture is refused by the solver. */
  status?: "assessment" | "test-fixture";
  usable?: boolean;
  statusReason?: string | null;
  /** Machine-readable scope: the base elements this database is assessed for. */
  assessedBaseElements?: string[];
  /** Scoped databases only (mc_ti): what the database may and may not be used for. */
  scopeFlag?: string;
  /** False when the database is only used if named by id (never picked by auto-detect). */
  autoSelect?: boolean;
}

export interface PythonCalphadSolveResult
  extends Omit<MultiComponentSolveResult, "solutePartitioning" | "multiElementScheil"> {
  /** pycalphad: k of the primary solid phase from the Scheil path (null with a reason); client: screening rows. */
  solutePartitioning: CalphadPartitionRow[];
  /** pycalphad: Scheil-Gulliver path points; client: the screening curve. */
  multiElementScheil: CalphadScheilPoint[];
  /** pycalphad only: the Scheil-Gulliver block (status, termination, validity, evidence label). */
  scheilSolidification?: CalphadScheilBlock;
  /** pycalphad only: compiled-model cache of the worker process ("cold" or "warm"). */
  modelCache?: CalphadModelCacheInfo;
  /** pycalphad only: measured stage times of this request (ms). */
  timingsMs?: Record<string, number>;
  /** pycalphad only: caveats for order/disorder model phase names (FCC_L12, BCC_B2): ordering not checked. */
  phaseNameNotes?: Record<string, string>;
  engine: string;
  /** null when the engine did not report a time (never an invented one). */
  computeTimeMs: number | null;
  proxyRoundtripMs?: number;
  isPythonEngine: boolean;
  iterations?: number;
  pycalphadVersion?: string;
  databaseUsed?: string;
  databasePath?: string;
  thermodynamicModel?: string;
  isEmpirical?: boolean;
  databaseId?: string;
  databaseStatus?: string;
  /** Per critical-temperature field: computed, heuristic or unavailable with a reason. */
  criticalTemperatureStatus?: Record<string, CalphadFieldStatus>;
  multiElementScheilStatus?: string;
  multiElementScheilNote?: string;
  /** Set when the Python CALPHAD engine answered "unavailable"; the numbers are then the client screening model's. */
  pythonUnavailable?: CalphadUnavailable;
  /** IN718 / IN625 only (any status): read-only literature solidification estimate (weld/DTA studies; not CALPHAD). */
  literatureSolidification?: unknown; knownDeviations?: { systemId?: string; notes?: string[]; criticalTemperatureNote?: string | null }[] /* pycalphad: stated database deviations */;
  activeComponents?: string[];
  unsupportedElements?: string[];
  databaseSuitability?: string;
  /** Scoped database only (mc_ti): valid and invalid uses, shown next to the numbers. */
  databaseScopeFlag?: string;
  /** Grid temperatures (degC) whose equilibrium did not converge; their profile entries are null. */
  nonConvergedPoints?: number[];
  boundaryRefinement?: { enabled: boolean; toleranceC: number; equilibriumCalls: number; note: string };
  phacompAnalysis?: {
    status: "screening-tabulated-values" | "unavailable";
    reason?: string;
    /** Bulk-composition Nv (Sims 1968 values); not compared with the residual-matrix 2.49 limit. */
    n_v_bar: number | null;
    /** Bulk-composition Md (Morinaga 1984 Table 1); the risk class compares it with the sourced critical Md. */
    m_d_bar: number | null;
    tcpEmbrittlementRisk: "Low" | "Moderate" | "High" | null;
    tcpSigmaRiskTemperatureC: number | null;
    thermodynamicStabilityIndex: number | null;
    compositionBasis?: string | null;
    /** C / B left out of both averages (no Md / Nv; carbides / borides), the rest renormalised. */
    excludedElements?: string[] | null;
    riskBasis?: string | null;
    criticalMd?: Array<{ temperatureK: number; criticalMd_eV: number }> | null;
    nvNote?: string | null;
    tcpSigmaRiskTemperatureReason?: string | null;
    thermodynamicStabilityIndexReason?: string | null;
    sources?: { Md: string; Nv: string } | null;
  };
  /** pycalphad only: reference state of each component's activity (pure element, SER phase, same T). */
  activityReferenceStates?: Record<string, {
    phase: string | null;
    temperature: string;
    pressurePa: number;
    status: "available" | "unavailable";
    reason: string | null;
    definition: string;
    /** Optional: SER reference basis of the pure element, present only when the engine reports it. */
    basis?: string;
    /** Optional: reference function used for the pure element (e.g. GHSERCC). */
    referenceFunction?: string;
    /** Optional: literature source of the reference data as carried by the database. */
    referenceSource?: string;
  }>;
  /** pycalphad only: the grid actually computed and every clamp that acted on the requested one. */
  effectiveTemperatureRangeC?: [number, number];
  effectiveTemperatureStepC?: number | null;
  gridAdjustments?: Array<{ field: string; requested: number; used: number | null; reason: string;
    requestedPoints?: number | null; usedPoints?: number }>;
}

export interface PythonXRDResult {
  success: boolean;
  engine: string;
  computeTimeMs: number;
  isPythonEngine: boolean;
  peaks: Array<{
    peak_id: number;
    two_theta_deg: number;
    hkl: string;
    fwhm_deg: number;
    eta_lorentz_fraction: number;
    d_spacing_angstrom: number;
    integral_breadth_deg: number;
    apparent_crystallite_size_nm: number;
    microstrain_pct: number;
  }>;
  williamsonHall: {
    linear_slope_4_epsilon: number;
    intercept_K_lambda_over_D: number;
    microstrain_epsilon: number | null;
    microstrain_percent: number | null;
    crystallite_size_nm: number | null;
    dislocation_density_m_minus_2: number | null;
    r_squared: number;
  };
}

export interface PythonBayesianOptimizationResult {
  success: boolean;
  error?: string;
  errorKind?: "validation" | "solver" | "optimizer";
  alloyId: string;
  beamDiameter_um?: number;
  preheatTemp_C?: number;
  nWarmup?: number;
  surrogateSteps?: number;
  objective?: string;
  bestVerdict?: string | null;
  noPositiveScore?: boolean;
  nInconclusive?: number;
  verdictCounts?: Record<string, number>;
  bestParams?: {
    laserPower_W: number;
    scanSpeed_mms: number;
    hatch_um: number;
    layer_um: number;
  };
  bestScore: number;
  iterations: Array<{
    iteration: number;
    params: {
      laserPower_W: number;
      scanSpeed_mms: number;
      hatch_um: number;
      layer_um: number;
    };
    score: number;
    verdict: string;
    /** Gates behind this candidate's verdict (python/lpbf_bayesian_optimizer.py _iteration_diagnostics). */
    diagnostics?: PythonBayesianIterationDiagnostics;
  }>;
  converged: boolean;
  elapsedMs: number;
  nIterations: number;
  gateSummary?: {
    blockingGateCounts: Record<string, number>;
    riskGateCounts: Record<string, number>;
    /** Advisory gates (no verdict / score effect), e.g. balling Moderate, recoater, distortion. */
    advisoryGateCounts?: Record<string, number>;
    inconclusiveExtentStatusCounts: Record<string, number>;
  };
  /** States that the keyhole gate is frozen solver physics (regime threshold 20 since the keyhole-regime bump; porosity screen stays a proxy). */
  keyholeGateNote?: string;
}

export interface PythonBayesianIterationDiagnostics {
  /** "fail" gates (do-not-print). */
  blockingGates: string[];
  /** "warn" gates (risky). */
  riskGates: string[];
  /** Advisory-only gates (never change the verdict). */
  advisoryGates: string[];
  reasons: string[];
  extentStatus: string | null;
  normalizedEnthalpy: number | null;
  aspectRatio_L_over_W: number | null;
  keyholeRisk: string | null;
  keyholeHigh: boolean | null;
  /** Balling screen band from the Eagar–Tsai L/W (null: extent not computed). */
  ballingBand?: "high" | "moderate" | "stable" | null;
  ballingLengthToWidthEagarTsai?: number | null;
}

// Phase 8: Solidification Microstructure Lab result type.
// Screening-field path (python/lpbf_solidification_microstructure.py compute_screening_field_microstructure):
// the numbers are thermal.solidificationKinetics from lpbf_thermal_solver (equal to the Build Job projection only
// for heatSource=rosenthal with the Build Job's inputs).
// status "available" = liquidus field-map G/R; "screening-fallback" = tail-length heuristic (reason says so);
// "degenerate-floor" = field map used but R/cooling are the solver's clamp floors (R <= 1e-4 m/s or cooling <=
// 1 K/s): the numbers are copied but are NOT a computed result and must not be shown as one;
// "unavailable" = no numbers (missing/unknown/impossible input), reason says why. Callers must check status first.
export interface SolidificationMicrostructureAvailable {
  status: 'available' | 'screening-fallback';
  reason?: string | null;
  source: string;
  modelId?: string | null;
  gradientSource?: string | null;
  usedFieldMap?: boolean | null;
  heatSourceModel?: string | null;
  materialName?: string | null;
  regime?: string | null;
  regimeNote?: string | null;
  normalizedEnthalpy?: number | null;
  absorptivity?: { effective: number | null; conduction: number | null };
  materialEvidence?: Record<string, unknown>;
  inputs?: Record<string, number>;
  morphologyBands_G_over_R?: { planar: number; cellular: number; columnar: number };
  scope?: string;
  G_K_m: number;
  R_m_s: number;
  coolingRate_K_s: number;
  g_over_r_ratio?: number | null;
  PDAS_um: number;
  SDAS_um: number;
  morphology: string;
  doi?: string | Record<string, string> | null;
  disclaimer: string;
  // Legacy CFD path only (a cfdResult was supplied); absent on the screening-field path.
  maxG_K_m?: number;
  maxR_m_s?: number;
  morphologyFractions?: { columnar: number; equiaxed: number; mixed: number };
  frontCellCount?: number;
}

export interface SolidificationMicrostructureUnavailable {
  status: 'unavailable';
  reason: string;
  source: string;
  heatSourceModel?: string | null;
  scope?: string;
  disclaimer?: string;
  doi?: string | Record<string, string> | null;
  G_K_m: null;
  R_m_s: null;
  coolingRate_K_s: null;
  PDAS_um: null;
  SDAS_um: null;
  morphology: null;
}

export type SolidificationMicrostructureDegenerate =
  Omit<SolidificationMicrostructureAvailable, 'status' | 'reason'> & {
    status: 'degenerate-floor';
    reason: string;
  };

export type SolidificationMicrostructureResult =
  | SolidificationMicrostructureAvailable
  | SolidificationMicrostructureDegenerate
  | SolidificationMicrostructureUnavailable;

function abortError(message: string): Error {
  const err = new Error(message);
  err.name = "AbortError";
  return err;
}

export function isAbortError(err: unknown): boolean {
  return typeof err === "object" && err !== null && (err as { name?: string }).name === "AbortError";
}

/** A CALPHAD result that carries only the reason: no profile, no temperatures, no client numbers. */
function calphadUnavailableResult(
  alloy: MultiComponentAlloyComposition,
  tMin: number,
  tMax: number,
  tStep: number,
  pythonUnavailable: CalphadUnavailable,
  literatureSolidification?: unknown,
): PythonCalphadSolveResult {
  return {
    alloyName: alloy.name,
    nominalComposition: { ...alloy.elements },
    temperatureRangeC: [tMin, tMax],
    temperatureStepC: tStep,
    equilibriumProfile: [],
    criticalTemperatures: { liquidusC: null, solidusC: null, freezingRangeC: null },
    solutePartitioning: [],
    multiElementScheil: [],
    thermodynamicStabilityIndex: null,
    tcpEmbrittlementRisk: null,
    engine: "none (pycalphad unavailable)",
    computeTimeMs: null,
    isPythonEngine: false,
    databaseUsed: pythonUnavailable.databaseUsed,
    pythonUnavailable,
    ...(literatureSolidification ? { literatureSolidification } : {}),
  };
}

/** Alloy id for the literature estimate: only IN718 / IN625 (by the studio's alloy name); anything else is undefined. */
export function literatureAlloyIdFromName(name: string | undefined): "in718" | "in625" | undefined {
  const n = String(name ?? "");
  if (/\b(?:inconel|in)[\s-]*718\b|N07718/i.test(n)) return "in718";
  if (/\b(?:inconel|in)[\s-]*625\b|N06625/i.test(n)) return "in625";
  return undefined;
}

/** Unavailable envelope for a CALPHAD request the Python service did not answer (no equilibrium is shown). */
function engineUnreachable(reason: string): CalphadUnavailable {
  return { unavailableKind: "engine-unreachable", reason, reasons: [reason] };
}

class PythonComputationService {
  private statusCache: PythonEngineStatus | null = null;
  private lastCheckTime = 0;
  private statusInflight: Promise<PythonEngineStatus> | null = null;
  private statusSeq = 0;
  private statusAppliedSeq = 0;

  async runLpbfBayesianOptimization(data: any): Promise<PythonBayesianOptimizationResult> {
    const res = await fetch("/api/python/lpbf-bayesian-optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      let detail = "";
      try { const b = await res.json(); detail = b?.error ? `: ${b.error}` : ""; } catch { /* body not JSON */ }
      throw new Error(`HTTP ${res.status}${detail}`);
    }
    return res.json();
  }

  // Phase 8: Solidification Microstructure Lab
  // params: materialName + power_W, speed_mm_s, beamDiameter_um, preheat_C, layerThickness_um, hatch_um, heatSource.
  // Python looks the alloy up by materialName; no k/liquidus/absorptivity is sent.
  async computeSolidificationMicrostructure(data: {
    params: Record<string, number | string>;
    material?: Record<string, number | string>;
    cfdResult?: Record<string, unknown>;
  }): Promise<SolidificationMicrostructureResult> {
    const res = await fetch("/api/python/lpbf-solidification-microstructure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    return res.json();
  }

  /**
   * Check whether the configured Python runtime is reachable
   */
  async checkEngineStatus(forceRefresh = false): Promise<PythonEngineStatus> {
    const now = Date.now();
    if (!forceRefresh && this.statusCache && now - this.lastCheckTime < 15000) {
      return this.statusCache;
    }
    // Non-forced callers share one in-flight request (app shell and boot check start together).
    if (!forceRefresh && this.statusInflight) return this.statusInflight;
    const request = this.requestEngineStatus(now).finally(() => {
      if (this.statusInflight === request) this.statusInflight = null;
    });
    this.statusInflight = request;
    return request;
  }

  private async requestEngineStatus(now: number): Promise<PythonEngineStatus> {
    const seq = ++this.statusSeq;
    let result: PythonEngineStatus;
    try {
      const res = await fetch("/api/python/status", {
        method: "GET",
        headers: { "Accept": "application/json" },
      });

      if (!res.ok) {
        throw new Error(`Status check HTTP ${res.status}`);
      }

      const data = await res.json();
      result = {
        online: data.success === true || data.status === "online" || data.status === "ready",
        status: data.status || "online",
        pythonVersion: data.pythonVersion ?? undefined,
        platform: data.platform,
        durationMs: data.durationMs,
        warm: data.warm === true,
        channel: data.channel ?? undefined,
        ipcDaemon: data.ipcDaemon,
        subsystems: data.subsystems,
        subsystemStatus: typeof data.subsystemStatus === "string" ? data.subsystemStatus : undefined,
      };
    } catch (err: any) {
      result = {
        online: false,
        status: "client_fallback",
        durationMs: 0,
      };
    }
    // An older request that finishes after a newer (e.g. forced) one must not overwrite its answer.
    if (seq < this.statusAppliedSeq && this.statusCache) return this.statusCache;
    this.statusAppliedSeq = seq;
    this.statusCache = result;
    this.lastCheckTime = now;
    return result;
  }

  /**
   * Fetches real-time status of the persistent Python IPC microservice daemon
   */
  async getIPCStatus(): Promise<PersistentIPCDiagnostics> {
    try {
      const res = await fetch("/api/python/ipc-status", {
        headers: { "Accept": "application/json" },
      });
      if (!res.ok) throw new Error(`IPC status check HTTP ${res.status}`);
      return await res.json();
    } catch (err: any) {
      return {
        success: false,
        status: "fallback_mode",
        isPersistent: false,
        channels: {
          // Unknown while the status endpoint is unreachable (the daemon picks its own addresses).
          unixSocket: { path: "", active: false },
          httpMicroservice: { url: "", active: false },
        },
        requestsProcessed: 0,
        avgLatencyMs: 0,
        uptimeSeconds: 0,
        warmModulesCount: 0,
        lastError: err.message,
      };
    }
  }

  /**
   * Forces re-warming of in-memory Python calculation modules
   */
  async triggerIPCWarmup(): Promise<{ success: boolean; durationMs?: number; message?: string }> {
    try {
      const res = await fetch("/api/python/ipc-warmup", {
        method: "POST",
        headers: { "Accept": "application/json" },
      });
      return await res.json();
    } catch (err: any) {
      return { success: false, message: err.message };
    }
  }

  /**
   * Fetches available Open-Source Thermodynamic Databases (TDB) supported by the backend pycalphad engine
   */
  async getCalphadDatabases(): Promise<{
    success: boolean;
    engine: string;
    pycalphadAvailable: boolean;
    pycalphadVersion: string;
    databases: PythonCalphadDatabaseEntry[];
    /** Reference alloy systems: covered by an assessed database, or unavailable with the reason. */
    systemCoverage?: CalphadSystemCoverage[];
  }> {
    try {
      const res = await fetch("/api/python/calphad-databases", {
        headers: { "Accept": "application/json" },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err: any) {
      return {
        success: false,
        engine: "client-fallback",
        pycalphadAvailable: false,
        pycalphadVersion: "Unavailable",
        databases: [],
      };
    }
  }

  /**
   * Dispatch CALPHAD Gibbs free energy multi-component minimization to pycalphad backend
   */
  async solveCalphadEquilibrium(
    alloy: MultiComponentAlloyComposition,
    tMin = 400,
    tMax = 1450,
    tStep = 20,
    usePython = true,
    databaseId?: string,
    customTdbText?: string,
    adaptiveGrid = true,
    boundaryRefinement = false,
    minRefineStep = 0.5,
    /** signal: aborts a superseded request; supersedeKey: lets the server drop this client's queued,
     * not yet started request when a newer one arrives (slider drags); scheil: also compute the
     * Scheil-Gulliver path (about 1.5 to 2 minutes, so off unless asked for). */
    options: { signal?: AbortSignal; supersedeKey?: string; scheil?: boolean } = {}
  ): Promise<PythonCalphadSolveResult> {
    let pythonUnavailable: CalphadUnavailable | null = null;
    let literatureSolidification: unknown;
    if (usePython) {
      let validation: PythonValidationError | null = null;
      try {
        const res = await fetch("/api/python/calphad-minimize", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: options.signal,
          body: JSON.stringify({
            supersedeKey: options.supersedeKey,
            name: alloy.name,
            elements: alloy.elements,
            unit: alloy.unit || "wt_pct",
            tMin,
            tMax,
            tStep,
            databaseId,
            literatureAlloyId: literatureAlloyIdFromName(alloy.name),
            customTdbText,
            adaptiveGrid,
            boundaryRefinement,
            minRefineStep,
            scheil: options.scheil ?? false,
          }),
        });

        if (res.ok) {
          const data = await res.json();
          if (data.success && data.equilibriumProfile) {
            return {
              ...data,
              isPythonEngine: true,
              engine: data.engine || "pycalphad-open-tdb",
              computeTimeMs: typeof data.computeTimeMs === "number" ? data.computeTimeMs : null,
            };
          }
          if (data && data.status === "superseded") {
            // The server dropped it for a newer request of the same client: nothing to show.
            throw abortError("superseded by a newer CALPHAD request");
          }
          // The Python engine has no fallback model: it says "unavailable" and why.
          pythonUnavailable = parseCalphadUnavailable(data) ?? engineUnreachable("the Python CALPHAD service gave no result");
          literatureSolidification = data?.literatureSolidification;
        } else {
          validation = await validationErrorFromResponse(res, "CALPHAD");
          if (!validation) {
            pythonUnavailable = engineUnreachable(`the Python CALPHAD service answered HTTP ${res.status}`);
          }
        }
      } catch (err) {
        if (isAbortError(err)) throw err; // superseded by newer input: the caller ignores it
        console.warn("Python CALPHAD proxy call failed:", err);
        pythonUnavailable = engineUnreachable("the Python CALPHAD service could not be reached");
      }
      // Invalid input (e.g. an unknown element symbol): surface it (HTTP 422 envelope message).
      if (validation) throw validation;
      // Unavailable (no database, no pycalphad, failed equilibrium, 5xx, network): an explicit,
      // number-free result. The client screening model is NOT run in its place.
      return calphadUnavailableResult(alloy, tMin, tMax, tStep, pythonUnavailable, literatureSolidification);
    }

    // Client-side TypeScript Fallback
    const startTime = performance.now();
    const fallbackTdb = parseTDBFile(
      PRELOADED_MULTI_COMPONENT_TDB[0].rawTdbText,
      PRELOADED_MULTI_COMPONENT_TDB[0].name
    );
    const clientResult = solveMultiComponentEquilibrium(alloy, fallbackTdb, tMin, tMax, tStep);
    const elapsed = Math.round(performance.now() - startTime);

    // Client screening numbers: labelled as such, never as a pycalphad/CALPHAD result.
    return {
      ...clientResult,
      engine: "MetalliX-Client-TS-Solver",
      computeTimeMs: elapsed,
      isPythonEngine: false,
      isEmpirical: true,
      thermodynamicModel: CLIENT_MODEL_LABEL,
      databaseUsed: CLIENT_DATABASE_LABEL,
      iterations: (tMax - tMin) / tStep,
    };
  }

  /**
   * Dispatch XRD Peak Deconvolution & Williamson-Hall Microstrain Analysis to Python
   */
  async deconvolveXRD(payload: {
    twoTheta?: number[];
    intensity?: number[];
    radiationWavelength?: number;
    radiationKa1?: number;
    radiationKa2?: number;
    instrumentBroadeningDeg?: number;
    peaks?: Array<{ twoTheta: number; hkl: string; intensity?: number }>;
  }): Promise<PythonXRDResult> {
    // No client fallback: a failed or unsuccessful dispatch is an error, never a made-up fit.
    const res = await fetch("/api/python/xrd-deconvolve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => null);
    if (!res.ok || !data?.success) {
      const detail = typeof data?.error === "string" ? `: ${data.error}` : "";
      throw new Error(`XRD deconvolution failed (HTTP ${res.status})${detail}`);
    }
    return { ...data, isPythonEngine: true };
  }

  /**
   * High-Fidelity 3D LPBF Laser Melt Pool, Geometry & Multi-Defect Physics Solver
   */
  async solveLPBFThermalPhysics(payload: {
    material: string;
    laserPower_W: number;
    scanSpeed_mm_s: number;
    beamDiameter_um: number;
    preheatTemp_C?: number;
    layerThickness_um?: number;
    hatchSpacing_um?: number;
    laserWavelength?: "IR_1064nm" | "Green_515nm" | "Blue_450nm";
    heatSource?: "rosenthal" | "eagar-tsai" | "goldak";
    sulfur_ppm?: number;
  }, signal?: AbortSignal): Promise<PythonLPBFResult> {
    const res = await fetch("/api/python/lpbf-thermal-solver", {
      signal,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`LPBF Thermal & Melt Pool proxy error: HTTP ${res.status}`);
    }

    return await res.json();
  }

  /**
   * Opt-in calibrated melt-pool mode (screening only, not validation). Same inputs as solveLPBFThermalPhysics plus
   * the explicit calibrationMode flag; the response carries the UNCHANGED screening result and a calibrated block
   * for gate-enabled cells only. The default path (solveLPBFThermalPhysics) is never routed through here.
   */
  async solveLPBFCalibratedMeltpool(payload: {
    material: string;
    laserPower_W: number;
    scanSpeed_mm_s: number;
    beamDiameter_um: number;
    preheatTemp_C?: number;
    layerThickness_um?: number;
    hatchSpacing_um?: number;
    laserWavelength?: "IR_1064nm" | "Green_515nm" | "Blue_450nm";
    heatSource?: "rosenthal" | "eagar-tsai" | "goldak";
    sulfur_ppm?: number;
  }, signal?: AbortSignal): Promise<LPBFCalibratedMeltpoolResult> {
    const res = await fetch("/api/python/lpbf-calibrated-meltpool", {
      signal,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, calibrationMode: true }),
    });

    if (!res.ok) {
      throw new Error(`LPBF calibrated melt-pool proxy error: HTTP ${res.status}`);
    }

    return await res.json();
  }

  /**
   * CAD/STL hatch discretization and LPBF build-time estimate (galvo + recoater).
   */
  async solveSTLSlicerBuildTime(payload: {
    preset?: string;
    material: string;
    laserPower_W: number;
    scanSpeed_mms: number;
    layerThickness_um: number;
    hatchSpacing_um: number;
    recoatTimePerLayer_s?: number;
    hatchStrategy?: string;
    customTriangles?: number[][][] | null;
    cadAssetName?: string;
    triangleCountNative?: number;
  }): Promise<PythonSTLSlicerResult> {
    const res = await fetch("/api/python/stl-slicer-build-time", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        recoatTimePerLayer_s: 9,
        hatchStrategy: "meander",
        preset: payload.preset ?? "nozzle",
        ...payload,
      }),
    });
    if (!res.ok) {
      throw new Error(`STL slicer / build-time proxy error: HTTP ${res.status}`);
    }
    return await res.json();
  }

  /**
   * Single Build Job: Rosenthal screening + slicer + print verdict (Python owns the decision).
   */
  async solveLpbfBuildJob(payload: {
    alloyId: string;
    thermalMaterial?: string;
    slicerMaterial?: string;
    laserPower_W: number;
    scanSpeed_mm_s: number;
    beamDiameter_um: number;
    preheatTemp_C?: number;
    layerThickness_um: number;
    hatchSpacing_um: number;
    laserWavelength?: "IR_1064nm" | "Green_515nm" | "Blue_450nm";
    preset?: string;
    customTriangles?: number[][][] | null;
    cadAssetName?: string;
    triangleCountNative?: number;
    processSeed?: number;
    scanStrategy?: string;
    stripeWidth_mm?: number;
    scanRotation_deg?: number;
    hatchDwell_ms?: number;
    inclineAngle_deg?: number;
    downskinOverhang_deg?: number;
    maxTriangles?: number;
    enableUq?: boolean;
    uqSamples?: number;
    includeAmbench?: boolean;
    defectSqrtAreas_um?: number[] | null;
    defectSqrtAreasPaste?: string;
    hardness_HV?: number;
    ctDetectionThreshold_um?: number;
    bypassCache?: boolean;
    gitSha?: string;
  }): Promise<PythonLpbfBuildJobResult> {
    const res = await fetch("/api/lpbf/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jobType: "build-job", ...payload }),
    });
    if (!res.ok) {
      let detail = `LPBF build-job proxy error: HTTP ${res.status}`;
      try {
        const failed = await res.json();
        if (failed?.error) detail = String(failed.error);
      } catch { /* keep HTTP status text */ }
      throw new Error(detail);
    }
    const jobInfo = await res.json();
    const jobId = jobInfo.id;
    if (!jobId) throw new Error("No Job ID returned from /api/lpbf/jobs");

    while (true) {
      const poll = await fetch(`/api/lpbf/jobs/${jobId}`);
      if (!poll.ok) throw new Error(`Failed to poll job status: HTTP ${poll.status}`);
      const statusData = await poll.json();
      if (statusData.status === "completed") {
        return statusData.result;
      }
      if (["failed", "cancelled", "timed_out"].includes(statusData.status)) {
        throw new Error(statusData.error || `Python LPBF build-job ${statusData.status}`);
      }
      await new Promise(r => setTimeout(r, 500));
    }
  }

  /**
   * LPBF process-window map (python/lpbf_process_window.py; screening only, not validation). Returns the raw JSON
   * document: callers must pass it through checkedProcessWindow (src/data/lpbfProcessWindow.ts) before rendering.
   * Refusals (HTTP 422 / errorKind "validation") and unreachable-engine failures are thrown as typed errors so the
   * view can tell them apart; nothing is retried or substituted.
   */
  async runLpbfProcessWindow(data: LpbfProcessWindowRequest, signal?: AbortSignal): Promise<unknown> {
    let res: Response;
    try {
      res = await fetch("/api/python/lpbf-process-window", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
        signal,
      });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") throw err;
      throw new LpbfProcessWindowRequestError("engine-unavailable", null, err instanceof Error ? err.message : "Network request failed.");
    }
    let body: any = null;
    try { body = await res.json(); } catch { /* body not JSON */ }
    if (!res.ok) {
      const detail = typeof body?.error === "string" ? body.error : `HTTP ${res.status}`;
      throw new LpbfProcessWindowRequestError(body?.errorKind === "validation" ? "validation" : "engine-unavailable", res.status, detail);
    }
    if (body === null || typeof body !== "object") {
      throw new LpbfProcessWindowRequestError("engine-unavailable", res.status, "The engine returned a non-JSON response.");
    }
    if (body.success !== true) {
      throw new LpbfProcessWindowRequestError(body.errorKind === "validation" ? "validation" : "engine-unavailable", res.status,
        typeof body.error === "string" ? body.error : "The engine returned a failure without a reason.");
    }
    return body;
  }

  /**
   * Machine calibration (user data), screening only. GET status lists the ready artefacts found on this computer; the
   * solve call applies one artefact (selected by its id, never by a path) to the frozen Rosenthal depth. Both are
   * read-only on the server and are never used by the default solve paths.
   */
  async getLpbfMachineCalibrationStatus(signal?: AbortSignal): Promise<MachineCalibrationStatus> {
    const res = await fetch("/api/python/lpbf-machine-calibration/status", { signal, method: "GET", headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error(`Machine calibration status HTTP ${res.status}`);
    return parseMachineCalibrationStatus(await res.json());
  }

  async solveLPBFMachineCalibratedMeltpool(payload: {
    machineCalibration: string;
    material: string;
    laserPower_W: number;
    scanSpeed_mm_s: number;
    beamDiameter_um: number;
    preheatTemp_C?: number;
    layerThickness_um?: number;
    hatchSpacing_um?: number;
    laserWavelength?: "IR_1064nm" | "Green_515nm" | "Blue_450nm";
    heatSource?: "rosenthal" | "eagar-tsai" | "goldak";
    sulfur_ppm?: number;
  }, signal?: AbortSignal): Promise<MachineCalibratedResult> {
    const res = await fetch("/api/python/lpbf-machine-calibrated-meltpool", {
      signal,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Machine calibration proxy error: HTTP ${res.status}`);
    const parsed = parseMachineCalibratedResult(await res.json());
    if (!parsed) throw new Error("Machine calibration response had no machineCalibrated block.");
    return parsed;
  }
}

export interface PythonSTLSlicerResult {
  success?: boolean;
  pythonDurationMs?: number;
  geometrySource?: "uploaded-stl" | "demo-preset";
  preset?: string;
  cadAssetName?: string;
  meshMetrics?: {
    sizeX_mm: number;
    sizeY_mm: number;
    sizeZ_mm: number;
    estimatedSolidVolume_cm3: number;
    estimatedPartMass_g: number;
    triangleCount: number;
    triangleCountNative?: number;
  };
  buildTimeSummary?: {
    totalLayers: number;
    totalBuildTime_hr: number;
    totalBuildTime_min: number;
    totalLaserTime_hr: number;
    totalRecoatTime_hr: number;
    laserDutyRatio_pct: number;
    peakLayerArea_mm2: number;
    meanLayerArea_mm2: number;
  };
}

/** "advisory": reported but never changes the verdict (recoater / distortion: alloy/layer index, independent of P, v and hatch).
 *  "not-evaluated": the gate input was null (P6 containment, 2026-10-11); never counted as pass or fail. */
export type PythonLpbfGateStatus = "pass" | "warn" | "fail" | "unavailable" | "advisory" | "not-evaluated";

export interface PythonLpbfScreeningGate {
  id: string;
  status: PythonLpbfGateStatus;
  /** null when the gate is unavailable (melt-pool geometry not resolved). */
  measured: number | null;
  /** Set when status is "unavailable". */
  reason?: string;
  required: number | null;
  unit: string;
  note: string;
}

export interface PythonLpbfSuggestedPatch {
  laserPower_W: number;
  scanSpeed_mms: number;
  hatch_um: number;
  layer_um: number;
  beamDiameter_um: number;
}

export interface PythonLpbfBuildJobVerdict {
  verdict: "printable" | "risky" | "do-not-print" | "inconclusive";
  headline: string;
  reasons: string[];
  /** Each ratio is null when its melt-pool extent or Tang input is null (gate "not-evaluated"; never pass or fail). */
  lofGeometry: {
    widthOverHatch: number | null;
    depthOverLayer: number | null;
    tangIndex?: number | null;
    hOverW?: number | null;
    tOverD?: number | null;
  };
  literatureWindow: {
    inside: boolean;
    alloyId: string;
    box: { powerMin_W: number; powerMax_W: number; speedMin_mm_s: number; speedMax_mm_s: number };
  };
  gates?: PythonLpbfScreeningGate[];
  dominantGate?: string;
  suggestedPatch?: PythonLpbfSuggestedPatch | null;
  /** Why there is no suggestedPatch, or how the suggested point was verified by re-running the solver. */
  suggestedPatchNote?: string | null;
  /** false when meltPoolGeometry.extentStatus !== "computed": geometry gates are unavailable, verdict is inconclusive. */
  geometryResolved?: boolean;
  extentStatus?: string;
  extentNote?: string | null;
  verdictReason?: string | null;
  unavailableGates?: string[];
  /** Gate ids whose input was null (status "not-evaluated"); never counted as pass or fail (P6 containment). */
  notEvaluatedGates?: string[];
  /** false when the Eagar–Tsai balling screen did not run (gate unavailable); a verdict is then not balling-cleared. */
  ballingScreened?: boolean;
  /** Absorption model of the screened L/W; thresholds were calibrated on "flat-plate". */
  ballingAbsorptionModel?: string | null;
  geometryIndependentFailGates?: string[];
  /** Gate ids with status "fail" (drive do-not-print). */
  blockingGates?: string[];
  /** Gate ids with status "warn" (drive risky). */
  riskGates?: string[];
  /** Gate ids with status "advisory" (never change the verdict). */
  advisoryGates?: string[];
  /** Advisory lines; also appended (last) to reasons. */
  advisories?: string[];
  uq?: {
    P_printable: number;
    normalizedEnthalpy: { mean: number; std: number; unit: string };
    dominantUncertainty: string;
    nSamples: number;
  };
}

export interface PythonLpbfUqBlock {
  enabled: boolean;
  nSamples: number;
  seed: number;
  bands: Record<string, number>;
  calibration: string;
  P_printable: number;
  counts: { printable: number; risky: number; do_not_print: number; inconclusive?: number };
  normalizedEnthalpy: { mean: number; std: number; unit: string };
  sobolProxy: Record<string, number>;
  screeningSensitivity?: Record<string, number>;
  sensitivityMethod?: string;
  dominantUncertainty: string;
  note: string;
}

export interface PythonLpbfAmbenchBlock {
  source: {
    challenge: string;
    doi: string;
    url: string;
    alloy: string;
    citation: string;
  };
  model: string;
  disclaimer: string;
  cases: Array<{
    caseId: string;
    nist: { length_um: number; width_um: number; depth_um: number };
    predicted: { length_um: number; width_um: number; depth_um: number };
    /** null when status is "not-computed" (heuristic / floored / box-limited extent). */
    mape_pct: { length: number | null; width: number | null; depth: number | null; mean: number | null } | null;
    status?: "computed" | "not-computed";
    extentStatus?: string;
    extentNote?: string | null;
    predictedIsHeuristic?: boolean;
  }>;
  /** Mean over computed cases only; null when none. */
  overallMeanMape_pct: number | null;
  computedCases?: number;
  notComputedCases?: number;
  overallNote?: string;
  alloyCoverage?: { status: string; note: string };
  fourAlloyCoverage?: Record<string, { status: string; note: string }>;
}

export interface PythonLpbfMurakamiBlock {
  status: string;
  fatigueLimit_MPa?: number | null;
  fatigueLimit_internal_MPa?: number;
  fatigueLimit_surface_MPa?: number;
  hardness_HV?: number;
  hardnessSource?: string;
  nDefects?: number;
  gumbel?: Record<string, number | string> | null;
  note: string;
  pasteHint?: string;
  alloyHvDefaults?: Record<string, number>;
  ctDetectionThreshold_um?: number | null;
}

export interface PythonLpbfQualificationBlock {
  status: string;
  screeningOnly: boolean;
  alloyId: string;
  standards: string[];
  couponPlan: string[];
  traceability: { inputHash: string; gitSha?: string | null; note: string };
  note: string;
}

export interface PythonLpbfCacheMeta {
  hit: boolean;
  key: string;
  ageMs: number;
  stats?: { entries: number; hits: number; misses: number; hitRate: number };
}

export interface PythonLpbfBuildJobResult {
  success: boolean;
  error?: string;
  engine: string;
  modelId: string;
  solverRevision?: string;
  materialPropertySchemaVersion?: number;
  materialPropertyRevision?: string;
  materialPropertySha256?: string;
  materialPropertySnapshot?: {
    schemaVersion: number;
    alloyId: string;
    thermal: Record<string, unknown>;
    slicer: Record<string, unknown>;
  };
  /** Present only when the request named a machine calibration id; reported next to the screening depth, never used by the verdict. */
  machineCalibrated?: MachineCalibratedBlock;
  buildJobIdentity?: {
    schemaVersion: number;
    alloyId: string;
    modelId: string;
    solverRevision: string;
    materialPropertySchemaVersion: number;
    materialPropertyRevision: string;
    materialPropertySha256: string;
    sha256: string;
  };
  assumptions: string[];
  alloyId: string;
  processSeed?: number;
  scanStrategy?: {
    id: string;
    stripeWidth_mm: number;
    rotation_deg: number;
    hatchDwell_ms: number;
  };
  computeTimeMs: number;
  thermal: PythonLPBFResult;
  slicer: PythonSTLSlicerResult;
  verdict: PythonLpbfBuildJobVerdict;
  uq?: PythonLpbfUqBlock | null;
  ambench?: PythonLpbfAmbenchBlock | null;
  murakami?: PythonLpbfMurakamiBlock | null;
  qualification?: PythonLpbfQualificationBlock | null;
  cache?: PythonLpbfCacheMeta | null;
  porosity?: any;
  kinematics?: any;
  microstructure?: any;
  kinetics?: any;
}

/** Output of POST /api/python/lpbf-calibrated-meltpool (python/lpbf_calibration_layer.apply_calibration). */
export interface LPBFCalibratedMeltpoolResult {
  screening: PythonLPBFResult;
  evidenceKind: "screening-only";
  calibrated: {
    available: boolean;
    reason?: string | null;
    width_um: number | null;
    depth_um: number | null;
    width_pi80_um?: [number, number];
    width_pi90_um?: [number, number];
    /** PI 90 % wider than the configured ratio (x2.5): shown but labelled not informative. */
    width_pi90_notInformative?: boolean;
    depth_pi80_um?: [number, number];
    depth_pi90_um?: [number, number];
    depth_pi90_notInformative?: boolean;
    widthReason?: string;
    depthReason?: string;
    cells?: Record<string, { status: string; rung?: string }>;
    regimeLabel?: string | null;
    regimeAtEtaD_sensitivity?: string | null;
    depthOverWidth?: number | null;
    depthOverWidthReason?: string | null;
  };
  calibration: {
    calibrationId: string;
    contentSha256: string;
    fittedOn: string[];
    heldOutScore: Record<string, string>;
    evidenceKind: "screening-only";
    label: string;
  } | null;
  outsideTrainingEnvelope: boolean;
  envelopeNotes: string[];
}

export interface PythonLPBFResult {
  success: boolean;
  engine: string;
  modelId?: string;
  heatSourceModel?: string;
  keyholeModel?: {
    modelId?: string;
    fabbroDepth_um?: number;
    aspectRatio_e_over_d?: number;
    peclet?: number;
    /** Fabbro m=2.4, n=3 fit band 2 <= Pe <= 10 (Wave B LA-4). */
    pecletInFitRange?: boolean;
    basis?: string;
    absorptivity?: number;
    absorptivityBasis?: string;
    doi?: string;
  };
  marangoniModel?: {
    modelId?: string;
    flowDirection?: string;
    dGamma_dT_N_mK?: number;
    sulfur_ppm?: number;
    /** DebRoy & David 1995 Eq. 8 order-of-magnitude estimate (Wave B LA-1); null when the served peak is null (P6). */
    surfaceVelocity_m_s?: number | null;
    surfaceVelocityDoi?: string | null;
    pecletMarangoni?: number | null;
    /** Why the Marangoni number, velocity and Peclet are null (P6 containment); null when they are served. */
    marangoniUnavailableReason?: string | null;
    aspectNote?: string;
    doi?: string;
  };
  computeTimeMs: number;
  proxyRoundtripMs?: number;
  material: string;
  baseMetal: string;
  laserWavelength: string;
  processParameters: {
    laserPower_W: number;
    scanSpeed_mm_s: number;
    beamDiameter_um: number;
    preheatTemp_C: number;
    layerThickness_um: number;
    hatchSpacing_um: number;
    inclineAngle_deg?: number;
    processSeed?: number;
    effectiveAbsorptivity: number;
    effectiveConductivity_W_mK?: number;
    effectiveSpecificHeat_J_kgK?: number;
    solidConductivity_W_mK?: number;
    liquidConductivity_W_mK?: number;
    volumetricEnergyDensity_J_mm3: number;
    linearEnergyDensity_J_m: number;
    peakIntensity_MW_cm2?: number;
    normalizedEnthalpy: number;
    heatSource?: string;
    conductionAbsorptivity?: number;
    fabbroAbsorptivity?: number;
    /** "flat-plate" on every machine unless the GPU powder ray tracer was requested explicitly. */
    absorptionModel?: "flat-plate" | "powder-raytrace";
    thermalSliceBackend?: "cpu" | "warp";
    stefanNumber?: number;
    /** 1.0 for every source since 2026-10-11 (P1). */
    latentHeatPowerFactor?: number;
    /** Power that drove the screening field: P_absorbed * latentHeatPowerFactor. */
    fieldPower_W?: number;
  };
  meltPoolGeometry: {
    length_um: number;
    width_um: number;
    depth_um: number;
    aspectRatio_L_over_W: number;
    depthToWidthRatio_D_over_W: number;
    keyholeVaporCavityDepth_um: number;
    regime: string;
    /** Derivation of the regime thresholds (python REGIME_THRESHOLD_BASIS). */
    regimeBasis?: string;
    /** Keyhole-mode cut on ΔH/hs used for this alloy (python regime_keyhole_cut: 20, Inconel 625 13.6). */
    regimeKeyholeThreshold?: number;
    /** Per-alloy note shown with the regime (threshold derived / IN625 per-alloy cut / not validated). */
    regimeMaterialNote?: string;
    /** Reporting-only note on the direction the served depth is biased (src/utils/depthBiasWarning.ts). No depth or regime number depends on it. */
    depthBiasWarning?: { direction: "may-underestimate" | "may-overestimate" | null; text: string | null; basis: string | null };
    /** Only "computed" is a closed, unfloored liquidus isotherm (python/lpbf_thermal_solver.py). */
    extentStatus: MeltPoolExtentStatus;
    extentNote: string | null;
    /** x of the axial field maximum the liquidus extent search and the yz cross-sections are anchored at (negative = behind the beam). */
    peakOffset_um?: number;
    /** Axial (y = z = 0) maximum of the kernel's own field at peakOffset_um (Eagar-Tsai, Goldak), served only below the
     *  sourced vapour temperature; null with a reason otherwise and always null for Rosenthal (regularised value; P6).
     *  It can be a number while hydrodynamicsAndRecoil.peakTemperature_C is null; it is the loss-free field maximum on
     *  the axis, never a surface temperature (display it with AXIAL_FIELD_MAXIMUM_LABEL). */
    axialFieldMaximum_C?: number | null;
    axialFieldMaximumUnavailableReason?: string | null;
    goldakParameters: {
      semiAxis_af_front_um: number;
      semiAxis_ar_rear_um: number;
      semiAxis_b_halfwidth_um: number;
      semiAxis_c_depth_um: number;
    };
  };
  hydrodynamicsAndRecoil: {
    /** P6 containment (2026-10-11): the loss-free Eagar-Tsai surface maximum (same value for every kernel), served only
     *  below a SOURCED vapour temperature; null with peakUnavailableReason otherwise. Older payloads carried the
     *  beam-centre value T(0,0,0) of the kernel (see peakTemperatureBasis). */
    peakTemperature_C: number | null;
    /** "eagar-tsai-loss-free-surface-maximum" since P6; older: "regularised-singular-source-value" (Rosenthal) or
     *  "distributed-source-conduction-centre-value" (ET/Goldak). */
    peakTemperatureBasis?: string;
    peakTemperatureModelId?: string;
    peakTemperatureNote?: string;
    peakUnavailableReason?: string | null;
    /** x of the loss-free maximum behind the beam centre (negative), null when the peak is null. */
    peakLocation_x_um?: number | null;
    vaporTemperatureSourced_K?: number | null;
    vaporTemperatureSourced_C?: number | null;
    vaporTemperatureSource?: string | null;
    vaporTemperatureDoi?: string | null;
    vaporTemperatureUnavailableReason?: string | null;
    /** Loss-free maximum vs the sourced vapour temperature; null where no sourced value exists. */
    peakExceedsVaporization?: boolean | null;
    /** Equals the served peak (no clipping since P6); null when the peak is null. Older payloads: min(peak, T_vap). */
    surfaceTemperature_C?: number | null;
    surfaceTemperatureBasis?: string;
    /** Always null since P6 (no wall closure); older payloads carried the 0.54 p_sat value at the clipped T_vap. */
    knudsenRecoilPressure_kPa: number | null;
    recoilPressureUnavailableReason?: string | null;
    /** "below Fabbro 2020 App A onset" | "above onset, no wall closure" | null (T_v unsourced). */
    recoilOnsetStatus?: string | null;
    recoilOnsetUnavailableReason?: string | null;
    recoilOnsetBasis?: string;
    marangoniNumber: number | null;
    marangoniUnavailableReason?: string | null;
    marangoniGeometrySource?: string;
    molarMass_kg_mol?: number;
    pecletThermalNumber: number;
    /** Always null since P6 (uncited heuristic removed, G1 audit B05). */
    powderDenudationWidth_um: number | null;
    powderDenudationUnavailableReason?: string | null;
  };
  defectDiagnostics: {
    lackOfFusionStatus: "Pass" | "Warning" | "Fail";
    lackOfFusionRisk: string;
    lackOfFusionOverlapIndex: number;
    tangIndex_hW_tD?: number;
    hOverW?: number;
    tOverD?: number;
    keyholePorosityRisk: string;
    /** Basis text of the porosity proxy (independent of the regime threshold). */
    keyholePorosityBasis?: string;
    /** Always false: no published index cut resolves keyhole porosity (Zhao 2020). */
    keyholePorosityResolved?: boolean;
    /** Band text of the balling screen ("High…", "Moderate…", "Stable…", "Unavailable…"); see ballingScreen. */
    ballingInstabilityRisk: string;
    /** Eagar–Tsai L/W balling screen (python lpbf_defect_diagnostics.balling_screen). */
    ballingScreen?: PythonLpbfBallingScreen;
    /** "Not evaluated from scan parameters (...)" since the 2026-10-06 tier-2 bump: the index is alloy/layer/preheat-only. */
    recoaterCrashRisk: string;
    /** Heuristic 0.72·E·α·ΔT/(1−ν) with fixed uncited constants; not a stress solve. */
    effectiveResidualStress_MPa: number;
    /** Heuristic index σ_eff·(layer/40 µm)/420 MPa with fixed uncited constants. */
    distortionIndex: number;
    distortionIndexBasis?: string;
  };
  /** P6 containment (2026-10-11): G, R, cooling rate, PDAS, SDAS and morphology come from the rear liquidus of the
   *  loss-free conduction field ("conduction-field-interface") and are null with unavailableReason when the served
   *  depth comes from the Fabbro keyhole leg or fewer than 3 interface samples exist. No tail-length fallback, no
   *  floors, no incline multiplier (solidificationCosTheta is no longer served). */
  solidificationKinetics: {
    modelId?: string;
    gradientSource?: string | null;
    usedFieldMap?: boolean;
    interface?: string | null;
    unavailableReason?: string | null;
    thermalGradient_G_K_m: number | null;
    thermalGradient_G_K_um: number | null;
    thermalGradientTail_G_K_m?: number | null;
    solidificationRate_R_m_s: number | null;
    solidificationRate_R_mm_s: number | null;
    /** Older payloads only (removed by P6). */
    solidificationCosTheta?: number;
    coolingRate_K_s: number | null;
    coolingRate_log10: number | null;
    g_over_r_ratio: number | null;
    microstructureMorphology: string | null;
    primaryDendriteArmSpacing_PDAS_um: number | null;
    secondaryDendriteArmSpacing_SDAS_um: number | null;
    phaseTransformation?: {
      alloyClass?: string;
      expected?: string;
      criterion?: string;
      source?: string | null;
      doi?: string | null;
    } | null;
    frontPointCount?: number;
    tail?: { x_um: number; z_um: number; G_K_m: number; R_m_s: number };
    bottom?: { x_um: number; z_um: number; G_K_m: number; R_m_s: number };
    doi?: string;
    disclaimer?: string;
  };
  geometricContours: {
    topDownXY: { x_um: number; y_um: number }[];
    longitudinalXZ: { x_um: number; z_depth_um: number; isKeyhole: boolean }[];
    transverseYZ: { y_um: number; z_depth_um: number }[];
    multiTrackHatchOverlap: {
      trackId: string;
      y_center_um: number;
      contour: { y_um: number; z_depth_um: number }[];
    }[];
  };
  thermalSlices?: {
    liquidus_C: number;
    solidus_C: number;
    haz_C: number;
    xz: {
      nx: number;
      nz: number;
      xMin_um: number;
      xMax_um: number;
      zMin_um: number;
      zMax_um: number;
      T_C: number[];
    };
    yz: {
      ny: number;
      nz: number;
      yMin_um: number;
      yMax_um: number;
      zMin_um: number;
      zMax_um: number;
      T_C: number[];
    };
  };
  processWindowMap: {
    currentOperatingPoint: {
      power_W: number;
      speed_mm_s: number;
      regime: string;
      lofStatus: string;
    };
    grid: {
      power_W: number;
      speed_mm_s: number;
      normalizedEnthalpy: number;
      regime: string;
      color: string;
      width_um: number;
      depth_um: number;
      /** True when the Tang lack-of-fusion flag fired on a cell with dH/hs >= 20 (depth biased low, A(R) not modelled). */
      keyholeIndexLackOfFusion?: boolean;
      /** Only present when keyholeIndexLackOfFusion is true. */
      lackOfFusionNote?: string;
    }[];
    /** The quick grid marks no balling zone (no melt-pool length); balling is screened at the operating point. */
    ballingNote?: string;
  };
}

/** python/lpbf_defect_diagnostics.balling_screen: Eagar–Tsai liquidus L/W; High > 5.5 (empirical, Hofmann 316L,
 *  risky), Moderate > 3.85 (Yadroitsev 2010 Eq. 13 / Gusarov 2007 mechanism, advisory), null band = extent not computed. */
export interface PythonLpbfBallingScreen {
  modelId: string;
  kernel: string;
  extentStatus: string;
  lengthToWidth: number | null;
  depthToWidth: number | null;
  band: "high" | "moderate" | "stable" | null;
  moderateThreshold: number;
  highThreshold: number;
  relativeUncertainty: number;
  hofmannBalledFractionInBand: string | null;
  verdictEffect: "risky" | "advisory" | "none";
  basis: string;
  sources: string[];
  experimentalValidation: false;
  reason: string | null;
}

export interface StochasticPropertyStats {
  mean: number;
  stdDev: number;
  covPct: number;
  skewness: number;
  kurtosis: number;
  min: number;
  max: number;
  median_P50: number;
  P10: number;
  P90: number;
  ci95Lower_P2_5: number;
  ci95Upper_P97_5: number;
  P01: number;
  P99: number;
  mmpds_kA: number;
  mmpds_kB: number;
  aBasisAllowable: number;
  bBasisAllowable: number;
  aBasisConfidenceInterval95?: [number, number] | null;
  bBasisConfidenceInterval95?: [number, number] | null;
  allowableStandardError_A?: number | null;
  allowableStandardError_B?: number | null;
  allowableUncertaintyMethod?: string;
  cpk: number | null;
  conformancePct: number;
  histogram: {
    binCenter: number;
    binStart: number;
    binEnd: number;
    count: number;
    empiricalPdf: number;
    fittedNormalPdf: number;
    cumulativePct: number;
  }[];
}

export const pythonComputationService = new PythonComputationService();

// ---- LPBF process-window map (python/lpbf_process_window.py) -------------------------------------------------
export type LpbfProcessWindowVerdict = "printable" | "risky" | "do-not-print" | "inconclusive";
export type LpbfProcessWindowCellVerdict = LpbfProcessWindowVerdict | "error";

export interface LpbfProcessWindowRequest {
  alloyId: string;
  beamDiameter_um: number;
  layer_um: number;
  hatch_um: number;
  preheatTemp_C: number;
  powers?: number[];
  speeds?: number[];
  overlayBeamTolerance_pct?: number;
}

export interface LpbfProcessWindowCell {
  iP: number;
  iV: number;
  power_W: number;
  speed_mm_s: number;
  verdict: LpbfProcessWindowCellVerdict;
  headline: string;
  dominantGate: string | null;
  blockingGates: string[];
  riskGates: string[];
  advisoryGates: string[];
  unavailableGates: string[];
  reasons: string[];
  extentStatus: string | null;
  insideLiteratureBox: boolean | null;
  normalizedEnthalpy: number | null;
  ballingBand: string | null;
  width_um: number | null;
  depth_um: number | null;
  error: string | null;
}

export interface LpbfProcessWindowPointVerdict {
  verdict: LpbfProcessWindowCellVerdict;
  dominantGate: string | null;
  extentStatus: string | null;
  modelWidth_um: number | null;
  modelDepth_um: number | null;
  error: string | null;
}

export interface LpbfProcessWindowPoint {
  datasetId: string;
  rowId: string;
  power_W: number;
  speed_mm_s: number;
  beamDiameter_um: number | null;
  layer_um: number | null;
  preheat_C: number | null;
  measuredWidth_um: number | null;
  measuredDepth_um: number | null;
  modelVerdict: LpbfProcessWindowPointVerdict;
}

export interface LpbfProcessWindowDataset {
  id: string;
  label: string;
  status: "available" | "unavailable";
  reason: string | null;
  material?: string | null;
  doi?: string | null;
  url?: string | null;
  license?: string | null;
  citation?: string | null;
  caveats?: string[];
  nRows: number;
  nShown: number;
  hiddenByBeam: number;
  hiddenNoBeam: number;
  hiddenOutsideRange: number;
  points: LpbfProcessWindowPoint[];
}

export interface LpbfProcessWindowResponse {
  success: true;
  engine: string;
  alloyId: string;
  request: {
    alloyId: string;
    beamDiameter_um: number;
    layer_um: number;
    hatch_um: number;
    preheatTemp_C: number;
    overlayBeamTolerance_pct: number;
  };
  grid: {
    powers_W: number[];
    speeds_mm_s: number[];
    nP: number;
    nV: number;
    nCells: number;
    literatureBox: { powerMin_W: number; powerMax_W: number; speedMin_mm_s: number; speedMax_mm_s: number };
    rangeBasis: {
      power: { basis: "default" | "request"; min_W: number; max_W: number; n: number; rule: string };
      speed: { basis: "default" | "request"; min_mm_s: number; max_mm_s: number; n: number; rule: string };
    };
  };
  cells: LpbfProcessWindowCell[];
  counts: Record<LpbfProcessWindowCellVerdict, number>;
  gridAdvisories: { gate: string; note: string; cells: number }[];
  overlay: {
    beamTolerance_pct: number;
    beamWindow_um: [number, number];
    note: string | null;
    measurementKind: string;
    datasets: LpbfProcessWindowDataset[];
  };
  evidence: { kind: "screening-only"; experimentalValidation: false; statement: string };
  provenance: { modelId: string; solverRevision: string; implementationHash: string; absorptionModel: string | null };
  /** scope: the cache lives in one Python worker process, so identical requests handled by another worker are misses. */
  cache: { hit: boolean; key: string; stored?: boolean; scope?: string };
  computeMs: number;
  originalComputeMs?: number | null;
}

/** kind "validation": the engine refused the request (HTTP 422); "engine-unavailable": no usable answer. */
export class LpbfProcessWindowRequestError extends Error {
  readonly kind: "validation" | "engine-unavailable";
  readonly status: number | null;
  constructor(kind: "validation" | "engine-unavailable", status: number | null, message: string) {
    super(message);
    this.name = "LpbfProcessWindowRequestError";
    this.kind = kind;
    this.status = status;
  }
}
