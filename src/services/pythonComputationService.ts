import type { QuantityContainer } from "../data/quantityEnvelope";
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
import { PythonValidationError, validationErrorFromResponse, pythonRequestError } from "../utils/pythonValidationError";
import type { ResearchOutcome, ResearchRequest } from "../types/lpbfResearchModels";
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
// SOL-A: Python owns each quantity's availability, reason codes and per-value provenance.
// The worker projects the thermal front container without a second numeric/scalar representation.
export interface SolidificationMicrostructureAvailable extends QuantityContainer {
  schema: "lpbf-solidification-microstructure-2";
  status: "computed" | "partial" | "unavailable";
  source: string;
  modelId?: string;
  heatSourceModel?: string | null;
  materialName?: string | null;
  regime?: string | null;
  normalizedEnthalpy?: number | null;
}
export type SolidificationMicrostructureResult = SolidificationMicrostructureAvailable;

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

/** Unavailable result for a request that ended without a Python answer (client deadline, dropped, failed). */
export function calphadUnreachableResult(
  alloy: MultiComponentAlloyComposition,
  tMin: number,
  tMax: number,
  tStep: number,
  reason: string,
): PythonCalphadSolveResult {
  return calphadUnavailableResult(alloy, tMin, tMax, tStep, engineUnreachable(reason));
}

/** Server budget of POST /api/python/calphad-minimize (routes/physics.ts). */
export const CALPHAD_SERVER_TIMEOUT_MS = 240000;
/** The client stops waiting this long after sending: the server budget plus reply slack. A request still open
 * then has no answer coming, and the studio says so instead of waiting forever. */
export const CALPHAD_CLIENT_TIMEOUT_MS = CALPHAD_SERVER_TIMEOUT_MS + 30000;

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
      throw await pythonRequestError(res, `Optimizer request failed (HTTP ${res.status}).`);
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

  // SOL-C solidification estimate channel (quantity envelope v2). Returns the raw JSON; the component parses it
  // with checkedSolidificationEstimates so a rejected payload never shows numbers.
  async computeSolidificationEstimates(data: {
    params: Record<string, number | string>;
    options: { inputSensitivity: boolean; conductionSurrogate?: boolean };
  }): Promise<unknown> {
    const res = await fetch("/api/python/lpbf-solidification-estimates", {
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
    options: { signal?: AbortSignal; supersedeKey?: string; scheil?: boolean; timeoutMs?: number } = {}
  ): Promise<PythonCalphadSolveResult> {
    let pythonUnavailable: CalphadUnavailable | null = null;
    let literatureSolidification: unknown;
    if (usePython) {
      let validation: PythonValidationError | null = null;
      // The caller's signal aborts a superseded request; the deadline ends a request that gets no answer.
      const timeoutMs = options.timeoutMs ?? CALPHAD_CLIENT_TIMEOUT_MS;
      const request = new AbortController();
      let timedOut = false;
      const onCallerAbort = () => request.abort();
      if (options.signal?.aborted) request.abort();
      else options.signal?.addEventListener("abort", onCallerAbort);
      const deadline = setTimeout(() => {
        timedOut = true;
        request.abort();
      }, timeoutMs);
      try {
        const res = await fetch("/api/python/calphad-minimize", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: request.signal,
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
            // The server dropped it for a newer request of the same client. That is an abort only when the
            // caller did move on; otherwise the caller still waits for this answer and must be told.
            if (options.signal?.aborted) throw abortError("superseded by a newer CALPHAD request");
            return calphadUnreachableResult(alloy, tMin, tMax, tStep,
              "the Python CALPHAD service dropped this request as superseded; change the input or reload to send it again");
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
        if (timedOut && !options.signal?.aborted) {
          pythonUnavailable = engineUnreachable(
            `the Python CALPHAD service gave no answer within ${Math.round(timeoutMs / 1000)} s`);
        } else {
          if (isAbortError(err)) throw err; // superseded by newer input: the caller ignores it
          console.warn("Python CALPHAD proxy call failed:", err);
          pythonUnavailable = engineUnreachable("the Python CALPHAD service could not be reached");
        }
      } finally {
        clearTimeout(deadline);
        options.signal?.removeEventListener("abort", onCallerAbort);
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
      throw await pythonRequestError(res, `Slicer request failed (HTTP ${res.status}).`);
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
      throw await pythonRequestError(res, `Build Job request failed (HTTP ${res.status}).`);
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
   * P8 research models (python/lpbf_research_models.py; research only, not validation). Opt-in: only the Research model
   * panel and the batch client call this, and nothing here feeds a served result. The server answer is classified,
   * never thrown, so a refusal or a timeout cannot be mistaken for data. Only an aborted fetch rejects (AbortError),
   * and the body of a request is sent exactly as given: the caller owns the request identity.
   */
  async solveLpbfResearchModels(request: ResearchRequest, signal?: AbortSignal): Promise<ResearchOutcome> {
    let res: Response;
    try {
      res = await fetch("/api/python/lpbf-research-models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal,
      });
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") throw err;
      return { kind: "http-error", httpStatus: 0, message: err instanceof Error ? err.message : "Network request failed." };
    }
    let body: unknown;
    try { body = await res.json(); } catch { body = undefined; }
    // The guards load on the first research request, so every other chunk that imports this service stays as small as before.
    const { classifyResearchAnswer } = await import("../types/lpbfResearchModels");
    return classifyResearchAnswer(res.status, body);
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
    if (!res.ok) throw await pythonRequestError(res, `Machine calibration request failed (HTTP ${res.status}).`);
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
  /** P7a (2026-10-11): provenance of the gate edge; demoted gates carry "unsourced screening threshold". */
  basis?: string;
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
  /** "sourced-criteria-only" since P7a: do-not-print on the Tang unit criterion, risky in keyhole mode, else printable. */
  verdictBasis?: string;
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
  /** Advisories at the suggested point (P7a; empty when none or no patch). */
  suggestedPatchAdvisories?: string[];
  /** True when 0.80 < Tang index <= 1.0 (unsourced screening margin; advisory only since P7a). */
  lackOfFusionMarginAdvisory?: boolean;
  /** Number of advisories (P7a). */
  advisoryCount?: number;
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
    /** null since P7a: the former DOI resolved to an unrelated paper; the band edges are unsourced screening values. */
    doi?: string | null;
    basis?: string;
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
    /** P7b (2026-10-14): basis of the physical field absorptivity: the measured conduction-mode authority with its
     *  locator and band, or exactly "no measurement, unsourced estimate" (no-measurement alloys, every green run). */
    absorptivityBasis?: string;
    absorptivitySource?: string | null;
    /** P7b: the index convention absorptivity the dH/hs regime index reads (pre-P7 value, not a measurement). */
    indexAbsorptivity?: number;
    absorptivityIndexBasis?: string;
    effectiveConductivity_W_mK?: number;
    effectiveSpecificHeat_J_kgK?: number;
    /** P7b: the density every conduction-kernel read uses (AlSi10Mg 2696; the room temperature value elsewhere). */
    kernelDensity_kg_m3?: number;
    effectiveDiffusivity_m2_s?: number;
    /** P7b: "kernel-ledger-kirchhoff" (Ti-6Al-4V, AlSi10Mg: Kirchhoff mean of the sourced solid forms at the request
     *  preheat), "melting-point" (sourced k and cp at the melting point), "blend" (equal-weight solid/liquid, unsourced)
     *  or "kernel-override" (explicit kernel keys of a caller). */
    propertyConvention?: "kernel-ledger-kirchhoff" | "melting-point" | "blend" | "kernel-override";
    propertyConventionBasis?: string;
    kernelLedgerSha256?: string | null;
    solidConductivity_W_mK?: number;
    solidConductivityBasis?: string;
    liquidConductivity_W_mK?: number;
    densityBasis?: string;
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
    /** P7a: keyhole-mode onset statement with the per-alloy cut provenance (a mode onset, not a porosity boundary). */
    regimeKeyholeCutBasis?: string;
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
    /** "Pass" | "Fail" since P7a (one Tang unit rule); "Warning" only in older payloads. */
    lackOfFusionStatus: "Pass" | "Warning" | "Fail";
    /** P7a: 0.80 < Tang index <= 1.0 (unsourced screening margin, advisory only). */
    lackOfFusionMarginAdvisory?: boolean;
    lackOfFusionMarginBasis?: string;
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
    /** "unavailable: no sourced stress model (...)" since P7a (2026-10-11); older payloads: "Not evaluated from scan parameters (...)". */
    recoaterCrashRisk: string;
    /** null since P7a: the former 0.72·E·α·ΔT/(1−ν) heuristic used unsourced constants and is not served. */
    effectiveResidualStress_MPa: number | null;
    /** null since P7a: the former σ_eff·(layer/40 µm)/420 MPa index is not served. */
    distortionIndex: number | null;
    distortionIndexBasis?: string;
    stressUnavailableReason?: string | null;
  };
  /** SOL-A1 front container. Default quantities are unavailable until liquidus admission;
   * geometry, regime and defect diagnostics retain their separate authority. */
  solidificationKinetics: QuantityContainer & { modelId: string; alloyId: string | null };
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
    /** P7b (2026-10-14): "rosenthal-screening-v1" for every requested kernel (each cell is the served Rosenthal field
     *  extent at the authority field power). */
    gridKernel?: string;
    gridKernelNote?: string;
    /** P7b: the dH/hs threshold of keyholeIndexLackOfFusion, the per-alloy keyhole cut (13.6 IN625, 20 otherwise). */
    keyholeIndexLackOfFusionCut?: number;
    /** null when the solver was called with include_process_map=False (internal re-runs only). */
    grid: {
      power_W: number;
      speed_mm_s: number;
      normalizedEnthalpy: number;
      regime: string;
      color: string;
      /** P7b: null when the cell's field extent is not a computed isotherm (see extentStatus); older payloads: a number. */
      width_um: number | null;
      depth_um: number | null;
      /** P7b: the cell's liquidus extent status ("computed" or a fallback / floor / search-limit status). */
      extentStatus?: string;
      /** True when the Tang lack-of-fusion flag fired on a cell at or above keyholeIndexLackOfFusionCut (depth biased
       *  low, A(R) not modelled); never true on an unresolved cell. */
      keyholeIndexLackOfFusion?: boolean;
      /** Only present when keyholeIndexLackOfFusion is true. */
      lackOfFusionNote?: string;
    }[] | null;
    /** The grid marks no balling zone (no melt-pool length); balling is screened at the operating point. */
    ballingNote?: string;
  };
}

/** python/lpbf_defect_diagnostics.balling_screen: Eagar–Tsai liquidus L/W; Moderate > 3.85 (Yadroitsev 2010 Eq. 13 /
 *  Gusarov 2007 mechanism, advisory), null band = extent not computed. No High band since P7b (2026-10-14): the former
 *  in-sample 316L edge 5.5 was fitted on a geometry P7b changed; "high" appears only in older payloads. */
export interface PythonLpbfBallingScreen {
  modelId: string;
  kernel: string;
  extentStatus: string;
  lengthToWidth: number | null;
  depthToWidth: number | null;
  /** "high" only in payloads older than P7b (2026-10-14); the High band was removed for every alloy. */
  band: "high" | "moderate" | "stable" | null;
  moderateThreshold: number;
  /** null since P7b (no High band); older payloads carried 5.5. */
  highThreshold: number | null;
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
