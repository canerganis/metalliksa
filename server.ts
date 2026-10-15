// First import: checks the working directory before any module below starts the Python worker.
import "./server/startupGuard.ts";
import express, { Request, Response } from "express";
import path from "path";
import dotenv from "dotenv";
import { createServer, type Server } from "node:http";
import { attachDevelopmentMiddleware } from "./server/devMiddleware.ts";
import { LoginAuth, applySecurity, buildLoginBannerLines, buildTrustProxyWarning, errorHandler, isAuthenticated, resolveBindConfig, resolveTrustProxy } from "./server/security.ts";

import { physicsRouter } from "./routes/physics.ts";
import { lpbfSimulationRouter } from "./routes/lpbfSimulation.ts";
import { characterizationRouter } from "./routes/characterization.ts";
import { researchRouter } from "./routes/research.ts";
import { createResearchRegistryRouter } from "./routes/researchRegistry.ts";
import { createLpbfSourcesRouter } from "./routes/lpbfSources.ts";
import { createLpbfRunsRouter } from "./routes/lpbfRuns.ts";
import { processOrchestrationMiddleware } from "./server/processOrchestrator.ts";
import {
  AIRGAP_ALLOWED_LOCAL,
  AIRGAP_BLOCKED_SERVICES,
  isAirgappedFromEnv,
} from "./server/airgap.ts";

dotenv.config();
// The Python IPC secret is generated per daemon spawn (server/processOrchestrator.ts); a value from
// .env loaded just above must not linger in this process's environment or reach ad-hoc spawns.
delete process.env.METALLIX_IPC_TOKEN;

const AIRGAPPED = isAirgappedFromEnv(process.env);

// Process-level crash guards: isolate unhandled rejections and errors
// Ensures an unhandled error in an AI route cannot terminate the process or affect CALPHAD/EIS
process.on("unhandledRejection", (reason: any) => {
  console.error("[ProcessGuard] Unhandled Promise Rejection intercepted:", reason?.stack || reason);
});

// An uncaught exception leaves the process in an undefined state: log, stop accepting
// connections and exit non-zero (force-exit after 5s if close hangs).
let activeHttpServer: Server | null = null;
process.on("uncaughtException", (error: Error) => {
  console.error("[ProcessGuard] Uncaught Exception, shutting down:", error?.stack || error);
  const forceExit = setTimeout(() => process.exit(1), 5000);
  forceExit.unref();
  if (activeHttpServer) {
    activeHttpServer.close(() => process.exit(1));
  } else {
    process.exit(1);
  }
});

// Default bind is 127.0.0.1 (no login). A non-loopback METALLIKSA_HOST enables the login flow:
// METALLIKSA_TOKEN (if set) or a random access code printed at startup.
let bindConfig: ReturnType<typeof resolveBindConfig>;
try {
  bindConfig = resolveBindConfig(process.env);
} catch (error: any) {
  console.error(`[Metalliksa-Server] ${error?.message || error}`);
  process.exit(1);
}

const app = express();
// Off by default. Behind a TLS reverse proxy set METALLIKSA_TRUST_PROXY so req.secure, req.ip and the
// same-origin check use the X-Forwarded-* headers.
const trustProxy = resolveTrustProxy(process.env);
if (trustProxy !== false) app.set("trust proxy", trustProxy);
const configuredPort = Number(process.env.PORT ?? 3000);
const PORT = Number.isInteger(configuredPort) && configuredPort >= 1 && configuredPort <= 65535 ? configuredPort : 3000;

// Login mode: non-loopback bind, or an explicit token. Loopback without a token stays open.
const loginAuth = bindConfig.token || bindConfig.accessCode ? new LoginAuth({ token: bindConfig.token, accessCode: bindConfig.accessCode }) : null;

// Request id, access log, security headers, rate limit, /login and Bearer/session auth.
applySecurity(app, bindConfig.token, { auth: loginAuth });

// Registry payloads have a smaller limit and must run before the global parser.
app.use(createResearchRegistryRouter());
app.use(createLpbfSourcesRouter());
app.use(createLpbfRunsRouter());

// Body parsing with generous payload capacity for base64 micrograph scans & CAD models
app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ extended: true, limit: "50mb" }));

// Process orchestration & subprocess telemetry middleware
app.use(processOrchestrationMiddleware);

// Server & Infrastructure Health Endpoint
app.get("/api/health", (req: Request, res: Response) => {
  res.json({
    status: "ok",
    service: "Metalliksa-Unified-Server",
    hasApiKey: AIRGAPPED ? false : isAuthenticated(req, bindConfig.token, loginAuth) && !!process.env.OPENAI_API_KEY?.trim(),
    airgapped: AIRGAPPED,
    timestamp: new Date().toISOString(),
  });
});

app.get("/api/runtime-config", (_req: Request, res: Response) => {
  res.json({
    airgapped: AIRGAPPED,
    blockedServices: AIRGAPPED ? AIRGAP_BLOCKED_SERVICES : [],
    allowedLocal: [...AIRGAP_ALLOWED_LOCAL],
  });
});

// =========================================================================
// Modular Express Controllers
// =========================================================================
// 1. HPC Physics & Computational Metallurgy (CALPHAD, DFT, LPBF, Kinetics, ICME, UQ)
app.use(physicsRouter);
app.use(lpbfSimulationRouter);

// 2. Experimental Characterization & Spectroscopy (EIS, XRD, Battery Degradation, SEM Vision)
app.use(characterizationRouter);

// 3. Metallurgy Consultation, Alloy Formulation & Materials Project
app.use(researchRouter);

// Explicit JSON 404 for unmatched /api routes (prevents SPA index.html fallback for API calls)
app.all("/api/*", (req: Request, res: Response) => {
  res.status(404).json({
    error: `API endpoint ${req.method} ${req.originalUrl} not found`,
  });
});

// Global Process-Isolated Error Handling Middleware
// Prevents unhandled JSON parsing errors or route exceptions from terminating the Node server process
app.use(errorHandler());

// =========================================================================
// Vite Middleware & SPA Serving Pipeline
// =========================================================================
async function startServer() {
  const httpServer = createServer(app);
  activeHttpServer = httpServer;
  if (process.env.NODE_ENV !== "production") {
    await attachDevelopmentMiddleware(app, httpServer);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req: Request, res: Response) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  httpServer.listen(PORT, bindConfig.host, () => {
    console.log(`[Metalliksa-Server] Modular server running on http://${bindConfig.host}:${PORT}`);
    if (!bindConfig.loopback) {
      console.warn(`[Metalliksa-Server] Network exposure: host ${bindConfig.host} is not loopback. Prefer HTTPS (reverse proxy) for non-local use.`);
    }
    const proxyWarning = buildTrustProxyWarning(bindConfig, trustProxy);
    if (proxyWarning) console.warn(`[Metalliksa-Server] ${proxyWarning}`);
    for (const line of buildLoginBannerLines(bindConfig, PORT)) console.log(`[Metalliksa-Server] ${line}`);
    if (AIRGAPPED) {
      console.log("[Metalliksa-Server] AIRGAPPED=1 — Crossref literature search disabled; local LPBF and physics engines remain available.");
    }
  });
}

startServer();
