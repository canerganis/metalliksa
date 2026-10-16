import { Router, Request, Response } from "express";
import { lpbfWorker, LpbfWorkerUnavailableError, LpbfWorkerValidationError } from "../server/lpbfWorkerBridge";
import { GpuCapabilityError } from '../src/utils/gpuCapability';

export function workerError(res: Response, error: unknown, fallback: string) {
  if (error instanceof GpuCapabilityError) return res.status(503).json({
    error: error.message, code: error.capability.code, capability: error.capability,
  });
  // Phase 6a: a worker-side input_validation error (e.g. fatigue UNKNOWN_ALLOY) is a
  // 422 with the validation envelope, like the migrated solvers on the dispatch routes.
  if (error instanceof LpbfWorkerValidationError) return res.status(422).json(error.envelope);
  if (error instanceof LpbfWorkerUnavailableError) {
    return res.status(503).set('Retry-After', '1').json({ error: error.message, code: error.code });
  }
  return res.status(400).json({ error: error instanceof Error ? error.message : fallback });
}

export const lpbfSimulationRouter = Router();
lpbfSimulationRouter.use("/api/lpbf", (req, res, next) => {
  const origin = req.get("origin");
  if (origin) {
    try { if (new URL(origin).host !== req.get("host")) return res.status(403).json({ error: "Same-origin requests required" }); }
    catch { return res.status(403).json({ error: "Invalid origin" }); }
  }
  next();
});
for (const [method, route, rpc] of [
  ["get", "/api/lpbf/capabilities", "capabilities"],
  ["post", "/api/lpbf/jobs", "submit"],
  ["post", "/api/lpbf/estimate", "estimate"],
  ["get", "/api/lpbf/jobs/:id", "get"],
  ["delete", "/api/lpbf/jobs/:id", "cancel"],
  ["post", "/api/python/lpbf-solidification-microstructure", "solidification-microstructure"],
  ["post", "/api/python/lpbf-solidification-estimates", "solidification-estimates"],
  ["post", "/api/python/lpbf-keyhole-raytracing", "keyhole-raytracing"],
] as const) {
  lpbfSimulationRouter[method](route, async (req, res) => {
    try {
      if (rpc === "submit" && Buffer.byteLength(JSON.stringify(req.body)) > 50000000) return res.status(413).json({ error: "Simulation input too large" });
      const passBody = ["submit", "estimate", "solidification-microstructure", "solidification-estimates", "keyhole-raytracing"].includes(rpc);
      const data = await lpbfWorker.request(rpc, passBody ? req.body : ("id" in req.params ? req.params.id : null));
      res.status(rpc === "submit" ? 202 : 200).json(data);
    } catch (e) { workerError(res, e, "Simulation request failed"); }
  });
}

// Explicit opt-in for a fresh execution record when the caller needs a distinct
// archive identity for unchanged physics inputs. The worker keeps the canonical
// physics cache key and input bytes; only this endpoint skips result reuse.
lpbfSimulationRouter.post("/api/lpbf/jobs/repeat", async (req, res) => {
  try {
    if (Buffer.byteLength(JSON.stringify(req.body)) > 50000000) return res.status(413).json({ error: "Simulation input too large" });
    const data = await lpbfWorker.request("submit-repeat", req.body);
    res.status(202).json(data);
  } catch (e) { workerError(res, e, "Simulation request failed"); }
});

lpbfSimulationRouter.get("/api/lpbf/jobs/:id/artifacts/:name", async (req: Request, res: Response) => {
  try {
    const data = await lpbfWorker.request("artifact", { id:req.params.id, name:req.params.name }) as {content:string;type:string};
    res.setHeader("Content-Type",data.type);
    res.setHeader("Content-Security-Policy","default-src 'none'; sandbox");
    res.setHeader("X-Content-Type-Options","nosniff");
    if (req.params.name.endsWith(".csv")) res.setHeader("Content-Disposition",'attachment; filename="thermal-history.csv"');
    res.send(Buffer.from(data.content,"base64"));
  } catch(e) { workerError(res, e, "Artifact unavailable"); }
});

