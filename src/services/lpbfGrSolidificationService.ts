import type { EstimateContainer, QuantityContainer } from "../data/quantityEnvelope";
import type { QuantityStatus } from "../generated/quantityEnvelope";
export type GrAlloyId = "in718" | "in625" | "ti6al4v" | "alsi10mg" | "ss316l";
export type GrCellStatus = QuantityStatus;
export type GrLocation = "bottom" | "median" | "tail";
export interface GrSolidificationRequest {
  mode: "point" | "map"; alloyId: GrAlloyId; beamDiameter_um: number; layer_um: number;
  hatch_um: number; preheatTemp_C: number; power_W?: number; speed_mm_s?: number; powers?: number[]; speeds?: number[];
}
export interface GrSourceChecks {
  equationRead: { status: "read" | "not-read"; locator: string | null };
  algebraReproduced: { status: "reproduced" | "not-reproduced" | "not-attempted"; test: string | null };
  printedLimitComparison: { status: "agrees" | "disagrees" | "not-available" | "not-attempted"; [key: string]: unknown };
}
export interface GrCetConstant { value: number | null; unit: string; source: string | null; locator: string | null; verified: boolean }
export interface GrCetSet {
  id: string; label: string; transferLabel: string; caveat: string; citation: string; doi?: string; osti?: string;
  sourceChecks: GrSourceChecks; equationLocator: string | null; phiSource: string; note: string;
  constants: Record<"a" | "n" | "N0", GrCetConstant>;
}
export interface GrCellBody {
  status: GrCellStatus; regime: string | null; normalizedEnthalpy: number | null; extentStatus: string | null;
  front: QuantityContainer;
  /** SOL-C CET projection (v2 estimate envelope): class, plus envelope fraction and chi when a front was formed. */
  cet: EstimateContainer & { status: GrCellStatus; projectionId: string; surrogate: string | null };
  laves: QuantityContainer & { status: GrCellStatus };
}
export interface GrCell extends GrCellBody { iP: number; iV: number; power_W: number; speed_mm_s: number }
export interface GrPoint extends GrCellBody { power_W: number; speed_mm_s: number }
export interface GrSolidificationResponse {
  success: true; engine: string; schema: string; mode: "point" | "map"; alloyId: GrAlloyId; materialName: string;
  request: { alloyId: GrAlloyId; beamDiameter_um: number; layer_um: number; hatch_um: number; preheatTemp_C: number };
  grid?: { powers_W: number[]; speeds_mm_s: number[]; nP: number; nV: number; nCells: number; rangeBasis: Record<string, unknown> };
  point?: GrPoint; cells?: GrCell[]; counts: Record<GrCellStatus, number>;
  cet: {
    modelId: string; equation: string; sourceChecks: GrSourceChecks;
    constantsStatus: { status: "available" | "unavailable"; reason: string | null; sets: GrCetSet[] };
  };
  laves: Record<string, unknown>;
  evidence: { kind: "screening-only"; experimentalValidation: false; statement: string };
  limits: string[];
  provenance: { heatSource: string; solidificationModelId: string; buildJobSolverRevision: string; implementationHash: string };
  computeMs?: number;
}

/** kind "validation": the engine refused the request (HTTP 422); "engine-unavailable": no usable answer. */
export class GrSolidificationRequestError extends Error {
  readonly kind: "validation" | "engine-unavailable";
  readonly status: number | null;
  constructor(kind: "validation" | "engine-unavailable", status: number | null, message: string) {
    super(message);
    this.name = "GrSolidificationRequestError";
    this.kind = kind;
    this.status = status;
  }
}

export async function runGrSolidification(req: GrSolidificationRequest, signal?: AbortSignal): Promise<unknown> {
  let res: Response;
  try {
    res = await fetch("/api/python/lpbf-gr-solidification", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new GrSolidificationRequestError("engine-unavailable", null, err instanceof Error ? err.message : "Network request failed.");
  }
  let body: any = null;
  try { body = await res.json(); } catch { /* body not JSON */ }
  if (!res.ok) {
    const detail = typeof body?.error === "string" ? body.error : `HTTP ${res.status}`;
    throw new GrSolidificationRequestError(body?.errorKind === "validation" ? "validation" : "engine-unavailable", res.status, detail);
  }
  if (body === null || typeof body !== "object") {
    throw new GrSolidificationRequestError("engine-unavailable", res.status, "The engine returned a non-JSON response.");
  }
  if (body.success !== true) {
    throw new GrSolidificationRequestError(body.errorKind === "validation" ? "validation" : "engine-unavailable", res.status,
      typeof body.error === "string" ? body.error : "The engine returned a failure without a reason.");
  }
  return body;
}
