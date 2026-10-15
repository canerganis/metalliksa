import { pythonStatusResponse } from "../server/pythonStatus.ts";
import { Router, Request, Response } from "express";
import { runPythonScript, pythonIPCSupervisor } from "../server/processOrchestrator.ts";
import { parsePythonStdout, pythonDispatchStatus } from "../server/pythonDispatchStatus.ts";

export const physicsRouter = Router();

// Overridable runner so route tests can exercise the status mapping without spawning Python.
export const physicsDeps = { runPythonScript };

async function handlePythonDispatch(scriptPath: string, payload: any, res: Response, timeoutMs: number = 25000) {
  try {
    const pyRes = await physicsDeps.runPythonScript(scriptPath, payload, [], timeoutMs);
    if (!pyRes.stdout && pyRes.stderr) {
      console.warn(`[Python stderr: ${scriptPath}]`, pyRes.stderr);
    }
    const stdout = (pyRes.stdout || "").trim();
    if (!stdout) {
      return res.status(500).json({
        error: pyRes.stderr?.trim() || `Python ${scriptPath} returned empty stdout (exit ${pyRes.exitCode}).`,
        script: scriptPath,
        stderr: pyRes.stderr,
      });
    }
    const parsed: any = parsePythonStdout(stdout) ?? { rawOutput: pyRes.stdout, stderr: pyRes.stderr, durationMs: pyRes.durationMs };
    return res.status(pythonDispatchStatus(parsed)).json(parsed);
  } catch (err: any) {
    console.error(`[Python error: ${scriptPath}]`, err);
    return res.status(500).json({
      error: err.message || "Failed to execute Python computation",
      script: scriptPath,
    });
  }
}

// System status & IPC health
physicsRouter.get("/api/python/status", (_req: Request, res: Response) => {
  const ipc = pythonIPCSupervisor.getStatus();
  res.json(pythonStatusResponse(ipc, process.platform));
});

physicsRouter.get("/api/python/ipc-status", (_req: Request, res: Response) => {
  res.json(pythonIPCSupervisor.getStatus());
});

physicsRouter.post("/api/python/ipc-warmup", async (_req: Request, res: Response) => {
  const ipc = pythonIPCSupervisor.getStatus();
  const ready = ipc.status === "online";
  res.status(ready ? 200 : 503).json({ success: ready, status: ipc.status, message: ready ? "Python IPC daemon ready" : "Python IPC daemon is not ready" });
});

// CALPHAD Gibbs Minimization & Databases
physicsRouter.post(["/api/python/calphad-minimize", "/api/calphad/minimize"], (req: Request, res: Response) => {
  return handlePythonDispatch("python/calphad_solver.py", req.body, res, 240000);
});

physicsRouter.get(["/api/python/calphad-databases", "/api/calphad/databases"], (req: Request, res: Response) => {
  return handlePythonDispatch("python/calphad_solver.py", { action: "list_databases" }, res, 15000);
});

// LPBF 3D Thermal Solver
physicsRouter.post("/api/python/lpbf-thermal-solver", (req: Request, res: Response) => {
  return handlePythonDispatch("python/lpbf_thermal_solver.py", req.body, res);
});

physicsRouter.post("/api/python/stl-slicer-build-time", (req: Request, res: Response) => {
  return handlePythonDispatch("python/stl_slicer_build_time_solver.py", req.body, res);
});



// Phase 6: Bayesian Process Window Optimization
physicsRouter.post("/api/python/lpbf-bayesian-optimize", (req: Request, res: Response) => {
  return handlePythonDispatch("python/lpbf_bayesian_optimizer.py", req.body, res, 120000);
});

// Opt-in calibrated melt-pool mode (screening only, not validation): the frozen solver run with a fitted
// effective absorptivity for gate-enabled cells only. A NEW route; /api/python/lpbf-thermal-solver is untouched.
physicsRouter.post("/api/python/lpbf-calibrated-meltpool", (req: Request, res: Response) => {
  return handlePythonDispatch("python/lpbf_calibrated_meltpool.py", req.body, res);
});

// LPBF process-window map (screening only, not validation): P x v grid of the frozen screening verdict plus a
// published-measurement overlay. 11 x 11 default grid at about 20 ms per cell, plus one model verdict per overlay
// point. A NEW route appended at the end of this file; no existing route or line reference moves.
physicsRouter.post("/api/python/lpbf-process-window", (req: Request, res: Response) => {
  return handlePythonDispatch("python/lpbf_process_window.py", req.body, res, 60000);
});

// LPBF melt-pool G/R coupled to solidification (screening only, not validation): Hunt G/R bands, a CET slot whose
// constants are unavailable for IN718/IN625, and a trapping-adjusted Laves bound. A NEW route appended at the end.
physicsRouter.post("/api/python/lpbf-gr-solidification", (req: Request, res: Response) => {
  return handlePythonDispatch("python/lpbf_gr_solidification.py", req.body, res, 60000);
});

// Machine-calibrated melt-pool depth (screening only, not validation): the user's own fitted empirical machine offset
// applied to the frozen Rosenthal depth, served only for gate-passing cells. The artefact is selected by its
// machineCalibrationId from .runtime/machine-calibration/ (never by a request path). A NEW route appended at the end;
// the status route lists the artefacts and the eligible cells and runs no solver.
physicsRouter.post("/api/python/lpbf-machine-calibrated-meltpool", (req: Request, res: Response) => {
  return handlePythonDispatch("python/lpbf_machine_calibrated_meltpool.py", req.body, res);
});

physicsRouter.get("/api/python/lpbf-machine-calibration/status", (_req: Request, res: Response) => {
  return handlePythonDispatch("python/lpbf_machine_calibrated_meltpool.py", { action: "status" }, res, 15000);
});

// P8 research models (docs/research/SPEC_p8_integration_contract_2026-10-15.md, 3.1): research only, explicit opt-in.
// A NEW route and a research-only dispatch wrapper appended at the end; /api/python/lpbf-thermal-solver and
// handlePythonDispatch are untouched and no existing line moves.
export const RESEARCH_REQUEST_MAX_BYTES = 65536;
export const RESEARCH_ROUTE_TIMEOUT_MS = 30000;
/** Thrown-message markers of server/processOrchestrator.ts (reply and ad-hoc timeouts). A route test asserts both
 * literals still occur there, so a rename fails the test instead of turning a timeout into a generic 500. */
export const RESEARCH_REPLY_TIMEOUT_MARKER = "got no reply within";
export const RESEARCH_ADHOC_TIMEOUT_MARKER = "Ad-hoc Python execution timed out after";

type ResearchTimeoutKind = "queue" | "run" | "reply" | "adhoc";

function researchTimeout(res: Response, timeoutKind: ResearchTimeoutKind, channel: string | null) {
  return res.status(504).json({ success: false, errorKind: "research", reasonCode: "RESEARCH_TIMEOUT", timeoutKind, channel });
}

function replyTimeoutChannel(message: string): string | null {
  if (message.includes("UNIX socket IPC")) return "unix_socket";
  if (message.includes("HTTP microservice")) return "http_microservice";
  return null;
}

/**
 * Research-only wrapper beside handlePythonDispatch: every timeout becomes HTTP 504 with RESEARCH_TIMEOUT and its
 * timeoutKind (queue and run from the isolated lane's exit-124 envelope, reply and adhoc from the thrown message),
 * and every body carries `channel` from PythonExecResult. Every other outcome is mapped as handlePythonDispatch maps it.
 */
async function handleResearchDispatch(payload: any, res: Response, timeoutMs: number) {
  try {
    // Revision 5: only an explicit null budget admits the long ad-hoc fallback.
    if (payload?.timeBudgetMs === null) timeoutMs = 120000;
    const pyRes = await physicsDeps.runPythonScript("python/lpbf_research_models.py", payload, [], timeoutMs);
    const channel = pyRes.channel ?? null;
    if (!pyRes.stdout && pyRes.stderr) {
      console.warn("[Python stderr: python/lpbf_research_models.py]", pyRes.stderr);
    }
    const stdout = (pyRes.stdout || "").trim();
    const parsed: any = stdout ? parsePythonStdout(stdout) : null;
    if (pyRes.exitCode === 124 && parsed?.reasonCode === "RESEARCH_TIMEOUT"
        && (parsed.timeoutKind === "queue" || parsed.timeoutKind === "run")) {
      return researchTimeout(res, parsed.timeoutKind, channel);
    }
    if (!stdout) {
      return res.status(500).json({
        error: pyRes.stderr?.trim() || `Python python/lpbf_research_models.py returned empty stdout (exit ${pyRes.exitCode}).`,
        script: "python/lpbf_research_models.py",
        stderr: pyRes.stderr,
        channel,
      });
    }
    const body = parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)
      ? { ...parsed, channel }
      : { rawOutput: pyRes.stdout, stderr: pyRes.stderr, durationMs: pyRes.durationMs, channel };
    return res.status(pythonDispatchStatus(parsed ?? body)).json(body);
  } catch (err: any) {
    const message = String(err?.message ?? err);
    if (message.includes(RESEARCH_REPLY_TIMEOUT_MARKER)) return researchTimeout(res, "reply", replyTimeoutChannel(message));
    if (message.startsWith(RESEARCH_ADHOC_TIMEOUT_MARKER)) return researchTimeout(res, "adhoc", "ad_hoc_fallback");
    console.error("[Python error: python/lpbf_research_models.py]", err);
    return res.status(500).json({
      error: err?.message || "Failed to execute Python computation",
      script: "python/lpbf_research_models.py",
      channel: null,
    });
  }
}

physicsRouter.post("/api/python/lpbf-research-models", (req: Request, res: Response) => {
  if (Buffer.byteLength(JSON.stringify(req.body ?? null), "utf8") > RESEARCH_REQUEST_MAX_BYTES) {
    return res.status(413).json({ success: false, errorKind: "research-request",
      reasonCode: "RESEARCH_REQUEST_INVALID", problems: [{ pointer: "", rule: "too-large", limit: RESEARCH_REQUEST_MAX_BYTES }] });
  }
  return handleResearchDispatch(req.body, res, RESEARCH_ROUTE_TIMEOUT_MS);
});
