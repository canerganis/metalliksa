import path from "path";
import { PythonReadiness } from "./pythonStatus.ts";
import net from "net";
import http from "http";
import crypto from "crypto";
import { spawn, spawnSync, ChildProcess } from "child_process";
import { getHostPython, loadPythonEnvironment } from "./pythonRuntime.ts";

// =========================================================================
// IPC security helpers (python/persistent_ipc_service.py enforces the other side)
// Protocol metallix-ipc-v2: the per-spawn token never travels on the wire. A request's MAC covers
// method, path, ts, nonce, body length and SHA-256(body) (the daemon verifies it before reading
// the body); each response carries HMAC(token, nonce, status, length, SHA-256(body)). A listener
// that is not our daemon learns nothing reusable and cannot forge a response we accept.
// =========================================================================

export const IPC_PROTOCOL = "metallix-ipc-v2";
const HEX64 = /^[0-9a-f]{64}$/;
/** Largest reply accepted from the daemon (solver stdout is JSON; the daemon caps requests at 64 MiB). */
export const MAX_IPC_RESPONSE_BYTES = 64 * 1024 * 1024;
const MAX_UNIX_HEAD_BYTES = 4096;
/** Extra time over the solver timeout for the daemon's own timeout reply to arrive. */
const IPC_REPLY_GRACE_MS = 5000;

/** Fresh per-spawn shared secret (64 hex chars); passed to the daemon via env, never argv. */
export function generateIpcToken(): string {
  return crypto.randomBytes(32).toString("hex");
}

export function sha256Hex(body: Buffer): string {
  return crypto.createHash("sha256").update(body).digest("hex");
}

export function ipcRequestMac(token: string, method: string, reqPath: string, ts: string, nonce: string, length: number, digest: string): string {
  return crypto.createHmac("sha256", token)
    .update(Buffer.from([IPC_PROTOCOL, "req", method, reqPath, ts, nonce, String(length), digest].join("\n"), "utf8"))
    .digest("hex");
}

export function ipcResponseMac(token: string, nonce: string, status: number, length: number, digest: string): string {
  return crypto.createHmac("sha256", token)
    .update(Buffer.from([IPC_PROTOCOL, "resp", nonce, String(status), String(length), digest].join("\n"), "utf8"))
    .digest("hex");
}

export function signIpcRequest(token: string, method: string, reqPath: string, body: Buffer, now: number = Date.now()) {
  const ts = String(now);
  const nonce = crypto.randomBytes(16).toString("hex");
  const digest = sha256Hex(body);
  return { ts, nonce, digest, mac: ipcRequestMac(token, method, reqPath, ts, nonce, body.length, digest) };
}

/** Constant-time check that a response really comes from the daemon holding our token. */
export function verifyIpcResponse(token: string, nonce: string, status: number, body: Buffer, digest: unknown, mac: unknown): boolean {
  if (typeof mac !== "string" || !HEX64.test(mac) || typeof digest !== "string" || !HEX64.test(digest)) return false;
  if (sha256Hex(body) !== digest) return false;
  const expected = ipcResponseMac(token, nonce, status, body.length, digest);
  return crypto.timingSafeEqual(Buffer.from(mac, "ascii"), Buffer.from(expected, "ascii"));
}

/**
 * A failed IPC attempt. `executed: false` means the daemon certainly did not run the request
 * (no connection, request not fully sent, or a complete reply that is unsigned or has status
 * >= 400: the daemon only answers >= 400 before running anything and signs every reply to an
 * authenticated request). Only then may the call be retried on another channel or spawned
 * ad hoc. Anything after the request was sent without such a reply (timeout, reset, truncated,
 * oversized or undecodable signed reply) is `executed: "unknown"` and is never retried.
 */
export class IpcChannelError extends Error {
  constructor(message: string, readonly executed: false | "unknown") {
    super(message);
    this.name = "IpcChannelError";
  }
}

/** One UNIX-socket request: head line + body, and the nonce its reply must be bound to. */
export function buildUnixFrame(token: string, request: unknown, now: number = Date.now()): { data: Buffer; nonce: string } {
  const body = Buffer.from(JSON.stringify(request), "utf8");
  const { ts, nonce, digest, mac } = signIpcRequest(token, "UNIX", "/", body, now);
  const head = JSON.stringify({ v: 2, ts, nonce, len: body.length, sha256: digest, mac });
  return { data: Buffer.concat([Buffer.from(head + "\n", "utf8"), body]), nonce };
}

/** Classifies a complete reply (status, body, digest, mac) under the shared channel policy. */
export function acceptIpcReply(token: string, nonce: string, status: number, body: Buffer, digest: unknown, mac: unknown, channel: string): any {
  if (!verifyIpcResponse(token, nonce, status, body, digest, mac)) {
    throw new IpcChannelError(`${channel} reply is not signed by this server's daemon (status ${status})`, false);
  }
  if (status >= 400) {
    let code = "";
    try { code = String(JSON.parse(body.toString("utf8"))?.code ?? ""); } catch { /* non-JSON error body */ }
    throw new IpcChannelError(`${channel} refused the request before running it (status ${status}${code ? ` ${code}` : ""})`, false);
  }
  try {
    return JSON.parse(body.toString("utf8"));
  } catch (err: any) {
    throw new IpcChannelError(`${channel} signed reply is not JSON: ${err.message}`, "unknown");
  }
}

/** Incremental parser of a UNIX-socket reply (head line, then exactly `len` body bytes). */
export class UnixReplyParser {
  private chunks: Buffer[] = [];
  private size = 0;
  private head: { status: number; len: number; sha256: unknown; mac: unknown } | null = null;
  private headBytes = 0;

  /** Returns the complete reply, or null while more bytes are needed; throws on a bad frame. */
  push(chunk: Buffer): { status: number; body: Buffer; sha256: unknown; mac: unknown } | null {
    this.chunks.push(chunk);
    this.size += chunk.length;
    if (!this.head) {
      const all = Buffer.concat(this.chunks);
      const nl = all.indexOf(0x0a, Math.max(0, all.length - chunk.length));
      if (nl < 0) {
        if (all.length > MAX_UNIX_HEAD_BYTES) throw new IpcChannelError("UNIX socket reply head too large", "unknown");
        this.chunks = [all];
        return null;
      }
      let head: any;
      try { head = JSON.parse(all.subarray(0, nl).toString("utf8")); } catch { head = null; }
      if (!head || !Number.isInteger(head.status) || !Number.isInteger(head.len) || head.len < 0) {
        throw new IpcChannelError("UNIX socket reply head is malformed", "unknown");
      }
      if (head.len > MAX_IPC_RESPONSE_BYTES) throw new IpcChannelError("UNIX socket reply too large", "unknown");
      this.head = { status: head.status, len: head.len, sha256: head.sha256, mac: head.mac };
      this.headBytes = nl + 1;
      this.chunks = [all];
    }
    if (this.size - this.headBytes < this.head.len) return null;
    const all = Buffer.concat(this.chunks);
    return { status: this.head.status, body: all.subarray(this.headBytes, this.headBytes + this.head.len), sha256: this.head.sha256, mac: this.head.mac };
  }
}

export function isLoopbackHost(host: string): boolean {
  const h = host.trim().toLowerCase().replace(/^\[|\]$/g, "");
  if (h === "localhost" || h === "::1" || h === "0:0:0:0:0:0:0:1") return true;
  return net.isIPv4(h) && h.split(".")[0] === "127";
}

/**
 * The daemon only ever binds loopback (the supervisor in this process is its only client). A
 * non-loopback METALLIX_IPC_HOST is replaced by 127.0.0.1 with a loud warning.
 */
export function resolveIpcHost(
  env: Record<string, string | undefined>,
  warn: (message: string) => void = console.warn
): string {
  const requested = (env.METALLIX_IPC_HOST || "127.0.0.1").trim();
  if (isLoopbackHost(requested)) return requested.replace(/^\[|\]$/g, "");
  warn(`[Python-Supervisor] WARNING: ignoring non-loopback METALLIX_IPC_HOST=${requested}; the IPC daemon binds 127.0.0.1 (only loopback is supported).`);
  return "127.0.0.1";
}

/**
 * Spawn spec for the daemon: the token travels only in the child's environment. Port 0 (the
 * default) lets the daemon bind an ephemeral port; without a socket path the daemon creates a
 * private 0700 directory. Both actual addresses come back in its ready message. The daemon
 * watches its stdin (a pipe held by this process) and exits when this process is gone.
 */
export function buildIpcSpawnSpec(
  python: { cmd: string; prefix: string[] },
  scriptPath: string,
  baseEnv: NodeJS.ProcessEnv,
  ipc: { socketPath?: string; port: number; host: string; token: string }
): { cmd: string; args: string[]; env: NodeJS.ProcessEnv } {
  const env: NodeJS.ProcessEnv = {
    ...baseEnv,
    METALLIX_IPC_PORT: String(ipc.port),
    METALLIX_IPC_HOST: ipc.host,
    METALLIX_IPC_TOKEN: ipc.token,
    METALLIX_IPC_STDIN_WATCH: "1",
  };
  if (ipc.socketPath) env.METALLIX_IPC_SOCK = ipc.socketPath;
  else delete env.METALLIX_IPC_SOCK;
  delete env.METALLIX_IPC_ALLOW_REMOTE;
  return { cmd: python.cmd, args: [...python.prefix, scriptPath], env };
}

/**
 * Scripts that may be dispatched, mirroring ALLOWED_SCRIPT_NAMES in python/persistent_ipc_service.py
 * (tests/persistent-ipc-auth.test.ts keeps the two lists equal). The ad-hoc fallback is held to
 * the same list as the daemon.
 */
export const DISPATCHABLE_SCRIPTS: ReadonlySet<string> = new Set([
  "calphad_solver",
  "lpbf_bayesian_optimizer",
  "lpbf_calibrated_meltpool",
  "lpbf_process_window",
  "lpbf_gr_solidification",
  "lpbf_machine_calibrated_meltpool",
  "lpbf_research_models",
  "lpbf_thermal_solver",
  "stl_slicer_build_time_solver",
  "xrd_peak_deconvolution",
]);
const SCRIPT_REF = /^python\/([A-Za-z_][A-Za-z0-9_]*)\.py$/;
export function assertDispatchableScript(scriptRelativePath: string): void {
  const m = typeof scriptRelativePath === "string" ? SCRIPT_REF.exec(scriptRelativePath) : null;
  if (!m || !DISPATCHABLE_SCRIPTS.has(m[1])) {
    throw new Error(`Refusing to dispatch Python script path ${JSON.stringify(scriptRelativePath)}; expected python/<module>.py for an allowlisted module`);
  }
}

function parsePort(value: string | undefined): number {
  const port = Number.parseInt(value ?? "0", 10);
  return Number.isInteger(port) && port >= 0 && port <= 65535 ? port : 0;
}

// Python Execution Result Interface
export interface PythonExecResult {
  stdout: string;
  stderr: string;
  exitCode: number | null;
  durationMs: number;
  warm?: boolean;
  channel?: "unix_socket" | "http_microservice" | "ad_hoc_fallback";
}

export interface IPCDaemonStatus {
  status: "online" | "restarting" | "initializing" | "fallback_mode";
  isPersistent: boolean;
  channels: {
    unixSocket: {
      path: string;
      active: boolean;
    };
    httpMicroservice: {
      url: string;
      active: boolean;
    };
  };
  requestsProcessed: number;
  avgLatencyMs: number;
  uptimeSeconds: number;
  warmModulesCount: number;
  warmModules: string[];
  pythonVersion: string | null;
  lastError: string | null;
}

function toExecResult(parsed: any, startTime: number, channel: "unix_socket" | "http_microservice"): PythonExecResult {
  return {
    stdout: parsed?.stdout ?? "",
    stderr: parsed?.stderr ?? "",
    exitCode: parsed?.exitCode ?? 0,
    durationMs: Date.now() - startTime,
    warm: true,
    channel,
  };
}

// =========================================================================
// Persistent Python IPC Supervisor & Worker Daemon Manager
// Keeps Python scientific modules (CALPHAD, EIS, DFT, XRD, LPBF, etc.) warm in RAM
// =========================================================================
export class PersistentPythonIPCSupervisor {
  private child: ChildProcess | null = null;
  private isReady: boolean = false;
  private isRestarting: boolean = false;
  private restartAttempts: number = 0;
  private maxRestartAttempts: number = 10;
  // Requested addresses; the channels actually used come from the child's ready message.
  private configuredSocketPath: string | undefined;
  private configuredPort: number;
  private httpHost: string;
  private startTime: number = Date.now();
  private requestsHandled: number = 0;
  private totalDurationMs: number = 0;
  private readiness = new PythonReadiness();
  private lastError: string | null = null;
  // Regenerated on every spawn; never logged, put on the command line or sent on the wire.
  private ipcToken: string = generateIpcToken();

  constructor() {
    loadPythonEnvironment();
    // The daemon's token is generated here; an inherited or .env value must not linger
    // (server.ts deletes it again after its own dotenv.config()).
    delete process.env.METALLIX_IPC_TOKEN;
    this.configuredSocketPath = process.env.METALLIX_IPC_SOCK || undefined;
    this.configuredPort = parsePort(process.env.METALLIX_IPC_PORT);
    this.httpHost = resolveIpcHost(process.env);

    this.startWorker();
    this.registerCleanupHooks();
  }

  private startWorker() {
    if (this.child && !this.child.killed) {
      return;
    }

    console.log("[Python-Supervisor] Launching persistent Python IPC microservice daemon...");
    const scriptPath = path.join(process.cwd(), "python", "persistent_ipc_service.py");

    this.ipcToken = generateIpcToken();
    this.readiness.reset();
    const spec = buildIpcSpawnSpec(getHostPython(), scriptPath, process.env, {
      socketPath: this.configuredSocketPath,
      port: this.configuredPort,
      host: this.httpHost,
      token: this.ipcToken,
    });
    const child = spawn(spec.cmd, spec.args, {
      windowsHide: true,
      env: spec.env,
      // stdin is a pipe we never write to: its EOF tells the daemon this process is gone.
      stdio: ["pipe", "pipe", "pipe"],
    });
    this.child = child;
    child.stdin?.on("error", () => { /* daemon gone; exit is handled below */ });

    // Readiness (and with it the channel addresses) is taken only from this spawn's own stdout.
    child.stdout?.on("data", (data) => {
      if (child !== this.child) return;
      if (this.readiness.consume(data.toString())) {
        this.isReady = this.readiness.ready;
        if (this.isReady) {
          this.isRestarting = false;
          this.restartAttempts = 0;
          this.lastError = null;
        }
        console.log(`[Python-Supervisor] Daemon ${this.isReady ? "ONLINE" : "UNAVAILABLE"}; ${this.readiness.warmModules.length} modules imported.`);
      }
    });

    child.stderr?.on("data", (data) => {
      const msg = data.toString().trim();
      if (msg.includes("[PersistentIPC]")) {
        console.log(msg);
      } else if (msg) {
        console.warn(`[Python-Worker stderr] ${msg}`);
      }
    });

    child.on("error", (err) => {
      console.error("[Python-Supervisor] Worker process error:", err);
      this.lastError = err.message;
      if (child === this.child) this.handleProcessExit();
    });

    child.on("exit", (code, signal) => {
      console.warn(`[Python-Supervisor] Persistent Python worker exited (code=${code}, signal=${signal})`);
      if (child === this.child) {
        this.lastError = `Python IPC daemon exited (code=${code}, signal=${signal})`;
        this.handleProcessExit();
      }
    });
  }

  private handleProcessExit() {
    this.isReady = false;
    this.readiness.reset();
    this.child = null;

    if (!this.isRestarting && this.restartAttempts < this.maxRestartAttempts) {
      this.isRestarting = true;
      this.restartAttempts++;
      const delay = Math.min(1000 * Math.pow(1.5, this.restartAttempts), 10000);
      console.log(`[Python-Supervisor] Scheduling worker restart #${this.restartAttempts} in ${delay}ms...`);
      setTimeout(() => {
        this.isRestarting = false;
        this.startWorker();
      }, delay);
    } else if (!this.isRestarting) {
      console.error(`[Python-Supervisor] Python IPC daemon unavailable after ${this.restartAttempts} restart attempts; using ad-hoc spawns.`);
    }
  }

  /** True once the restart budget is spent and no daemon is running: requests use ad-hoc spawns. */
  private get gaveUp(): boolean {
    return !this.child && !this.isRestarting && !this.isReady && this.restartAttempts >= this.maxRestartAttempts;
  }

  private registerCleanupHooks() {
    const shutdown = () => {
      const child = this.child;
      if (child && !child.killed) {
        console.log("[Python-Supervisor] Terminating persistent Python microservice worker...");
        if (process.platform === "win32" && child.pid) {
          // TerminateProcess would leave the daemon's pool workers running: kill the whole tree.
          spawnSync("taskkill", ["/T", "/F", "/PID", String(child.pid)], { windowsHide: true });
        } else {
          child.kill("SIGTERM");
        }
      }
    };

    process.on("SIGINT", shutdown);
    process.on("SIGTERM", shutdown);
    process.on("exit", shutdown);
  }

  /** The UNIX socket path, only when this server's own daemon announced an active socket. */
  private unixTarget(): string | null {
    return this.isReady && this.readiness.unixActive && this.readiness.unixSocketPath ? this.readiness.unixSocketPath : null;
  }

  /** The HTTP port, only when this server's own daemon announced an active HTTP listener. */
  private httpTarget(): number | null {
    return this.isReady && this.readiness.httpActive && this.readiness.httpPort ? this.readiness.httpPort : null;
  }

  /**
   * Dispatches script execution to the persistent Python daemon over its UNIX domain socket.
   * Rejects with IpcChannelError (see there for when the request may be retried).
   */
  private executeViaUnixSocket(
    socketPath: string,
    script: string,
    payload: any,
    args: string[],
    timeoutMs: number
  ): Promise<PythonExecResult> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      const token = this.ipcToken;
      const frame = buildUnixFrame(token, { action: "execute", script, payload, args, timeoutMs });
      const parser = new UnixReplyParser();
      let sent = false;
      let settled = false;
      const socket = net.createConnection(socketPath);
      const fail = (message: string) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        socket.destroy();
        reject(new IpcChannelError(message, sent ? "unknown" : false));
      };

      const timer = setTimeout(() => fail(`UNIX socket IPC got no reply within ${timeoutMs + IPC_REPLY_GRACE_MS}ms`),
        timeoutMs + IPC_REPLY_GRACE_MS);

      socket.on("connect", () => {
        socket.write(frame.data, (err) => { if (!err) sent = true; });
      });

      socket.on("data", (chunk: Buffer) => {
        if (settled) return;
        let reply;
        try {
          reply = parser.push(chunk);
        } catch (err: any) {
          return fail(err.message);
        }
        if (!reply) return;
        settled = true;
        clearTimeout(timer);
        socket.end();
        try {
          resolve(toExecResult(acceptIpcReply(token, frame.nonce, reply.status, reply.body, reply.sha256, reply.mac, "UNIX socket IPC"), startTime, "unix_socket"));
        } catch (err) {
          reject(err);
        }
      });

      socket.on("error", (err) => fail(`UNIX socket IPC error: ${err.message}`));
      socket.on("close", () => fail("UNIX socket IPC closed before a complete reply"));
    });
  }

  /**
   * HTTP loopback channel (port announced by this server's daemon). Same retry policy as the
   * UNIX socket (IpcChannelError).
   */
  private executeViaHttp(
    port: number,
    script: string,
    payload: any,
    args: string[],
    timeoutMs: number
  ): Promise<PythonExecResult> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      const token = this.ipcToken;
      const body = Buffer.from(JSON.stringify({ script, payload, args, timeoutMs }), "utf8");
      const auth = signIpcRequest(token, "POST", "/execute", body);
      let sent = false;
      let settled = false;
      const fail = (message: string) => {
        if (settled) return;
        settled = true;
        req.destroy();
        reject(new IpcChannelError(message, sent ? "unknown" : false));
      };

      const req = http.request(
        {
          hostname: this.httpHost,
          port,
          path: "/execute",
          method: "POST",
          agent: false,
          headers: {
            "Content-Type": "application/json",
            "Content-Length": body.length,
            "X-Metallix-Ts": auth.ts,
            "X-Metallix-Nonce": auth.nonce,
            "X-Metallix-Body-Sha256": auth.digest,
            "X-Metallix-Mac": auth.mac,
          },
          timeout: timeoutMs + IPC_REPLY_GRACE_MS,
        },
        (res) => {
          const declared = Number(res.headers["content-length"] ?? NaN);
          if (declared > MAX_IPC_RESPONSE_BYTES) return fail("HTTP microservice reply too large");
          const chunks: Buffer[] = [];
          let size = 0;
          res.on("data", (chunk: Buffer) => {
            size += chunk.length;
            if (size > MAX_IPC_RESPONSE_BYTES) return fail("HTTP microservice reply too large");
            chunks.push(chunk);
          });
          res.on("error", (err) => fail(`HTTP microservice reply error: ${err.message}`));
          res.on("end", () => {
            if (settled) return;
            if (!res.complete) return fail("HTTP microservice reply truncated");
            settled = true;
            try {
              resolve(toExecResult(acceptIpcReply(token, auth.nonce, res.statusCode ?? 0, Buffer.concat(chunks),
                res.headers["x-metallix-body-sha256"], res.headers["x-metallix-mac"], "HTTP microservice"), startTime, "http_microservice"));
            } catch (err) {
              reject(err);
            }
          });
        }
      );

      req.on("finish", () => { sent = true; });
      req.on("timeout", () => fail(`HTTP microservice got no reply within ${timeoutMs + IPC_REPLY_GRACE_MS}ms`));
      req.on("error", (err) => fail(`HTTP microservice error: ${err.message}`));
      req.end(body);
    });
  }

  /**
   * Fail-safe fallback: ad-hoc process spawn if persistent daemon is rebooting
   */
  private executeViaAdHocSpawn(
    scriptRelativePath: string,
    inputJson: any,
    args: string[],
    timeoutMs: number
  ): Promise<PythonExecResult> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      const scriptPath = path.join(process.cwd(), scriptRelativePath);

      const python = getHostPython();
      // UTF-8 mode: the JSON protocol is UTF-8 in both directions, but a Python started without it reads stdin
      // in the locale code page (cp1254/cp1252 on Windows) and garbles non-ASCII text.
      const pyProcess = spawn(python.cmd, [...python.prefix, scriptPath, ...args], {
        windowsHide: true,
        env: { ...process.env, PYTHONUTF8: "1" },
      });
      let stdout = "";
      let stderr = "";
      // Decode as a stream: a multi-byte character split across two chunks must not become U+FFFD.
      pyProcess.stdout.setEncoding("utf8");
      pyProcess.stderr.setEncoding("utf8");

      const timer = setTimeout(() => {
        pyProcess.kill("SIGKILL");
        reject(new Error(`Ad-hoc Python execution timed out after ${timeoutMs}ms`));
      }, timeoutMs);

      if (inputJson !== null && inputJson !== undefined) {
        const payload = typeof inputJson === "string" ? inputJson : JSON.stringify(inputJson);
        pyProcess.stdin.write(payload);
        pyProcess.stdin.end();
      }

      pyProcess.stdout.on("data", (data) => {
        stdout += data.toString();
      });

      pyProcess.stderr.on("data", (data) => {
        stderr += data.toString();
      });

      pyProcess.on("close", (code) => {
        clearTimeout(timer);
        const durationMs = Date.now() - startTime;
        resolve({
          stdout,
          stderr,
          exitCode: code,
          durationMs,
          warm: false,
          channel: "ad_hoc_fallback",
        });
      });

      pyProcess.on("error", (err) => {
        clearTimeout(timer);
        reject(err);
      });
    });
  }

  /**
   * Primary unified execution dispatcher. Only channels announced by this server's own daemon
   * are used. A request is tried on the next channel (or spawned ad hoc) only when the previous
   * attempt certainly did not run it (IpcChannelError.executed === false); once a request may
   * have run, the error is returned instead of running it a second time.
   */
  public async execute(
    scriptRelativePath: string,
    inputJson: any,
    args: string[] = [],
    timeoutMs: number = 15000
  ): Promise<PythonExecResult> {
    assertDispatchableScript(scriptRelativePath);
    const t0 = Date.now();
    const failures: string[] = [];

    const attempt = async (run: () => Promise<PythonExecResult>): Promise<PythonExecResult | null> => {
      try {
        const result = await run();
        this.recordSuccess(Date.now() - t0);
        return result;
      } catch (err: any) {
        if (err instanceof IpcChannelError && err.executed === false) {
          failures.push(err.message);
          return null;
        }
        throw new Error(`Python IPC request may already have run, so it was not retried: ${err?.message || err}`);
      }
    };

    const socketPath = this.unixTarget();
    if (socketPath) {
      const result = await attempt(() => this.executeViaUnixSocket(socketPath, scriptRelativePath, inputJson, args, timeoutMs));
      if (result) return result;
    } else {
      failures.push("no UNIX socket announced by this server's daemon");
    }

    const port = this.httpTarget();
    if (port) {
      const result = await attempt(() => this.executeViaHttp(port, scriptRelativePath, inputJson, args, timeoutMs));
      if (result) return result;
    } else {
      failures.push("no HTTP listener announced by this server's daemon");
    }

    console.warn(`[Python-Supervisor] IPC channels unavailable (${failures.join(" / ")}). Falling back to ad-hoc spawn...`);
    const spawnResult = await this.executeViaAdHocSpawn(scriptRelativePath, inputJson, args, timeoutMs);
    this.recordSuccess(Date.now() - t0);
    return spawnResult;
  }

  private recordSuccess(durationMs: number) {
    this.requestsHandled++;
    this.totalDurationMs += durationMs;
  }

  public getStatus(): IPCDaemonStatus {
    const avgDuration =
      this.requestsHandled > 0 ? (this.totalDurationMs / this.requestsHandled).toFixed(2) : "0.00";
    const httpPort = this.readiness.httpPort;
    const host = this.httpHost.includes(":") ? `[${this.httpHost}]` : this.httpHost;
    const gaveUp = this.gaveUp;
    return {
      status: this.isReady ? "online" : gaveUp ? "fallback_mode" : this.isRestarting ? "restarting" : "initializing",
      isPersistent: !gaveUp,
      channels: {
        unixSocket: {
          path: this.readiness.unixSocketPath ?? this.configuredSocketPath ?? "",
          active: this.unixTarget() !== null,
        },
        httpMicroservice: {
          url: httpPort ? `http://${host}:${httpPort}` : "",
          active: this.httpTarget() !== null,
        },
      },
      requestsProcessed: this.requestsHandled,
      avgLatencyMs: parseFloat(avgDuration),
      uptimeSeconds: Math.round((Date.now() - this.startTime) / 1000),
      warmModulesCount: this.readiness.warmModules.length,
      warmModules: [...this.readiness.warmModules],
      pythonVersion: this.readiness.pythonVersion,
      lastError: gaveUp
        ? `unavailable: Python IPC daemon failed ${this.restartAttempts} restarts (${this.lastError ?? "no detail"}); using ad-hoc spawns`
        : this.lastError,
    };
  }
}

// Global Singleton IPC Supervisor
export const pythonIPCSupervisor = new PersistentPythonIPCSupervisor();

/**
 * Express middleware for subprocess lifecycle management & orchestration.
 * Injects IPC supervisor telemetry into response headers, isolates process errors,
 * and ensures sub-process resource tracing per request.
 */
export function processOrchestrationMiddleware(
  req: import("express").Request,
  res: import("express").Response,
  next: import("express").NextFunction
) {
  // Attach IPC supervisor telemetry headers
  const status = pythonIPCSupervisor.getStatus();
  res.setHeader("X-Python-IPC-Status", status.status);
  res.setHeader("X-Python-IPC-Warm-Modules", String(status.warmModulesCount));

  // Trace execution duration for process-heavy routes
  const startTime = Date.now();
  res.on("finish", () => {
    if (req.path.startsWith("/api/python/")) {
      const elapsed = Date.now() - startTime;
      if (elapsed > 8000) {
        console.warn(`[ProcessOrchestrator] Long-running process request ${req.method} ${req.path} took ${elapsed}ms`);
      }
    }
  });

  next();
}

/**
 * Drop-in helper for running python scripts using persistent warm IPC worker
 */
export function runPythonScript(
  scriptRelativePath: string,
  inputJson: any,
  args: string[] = [],
  timeoutMs: number = 15000
): Promise<PythonExecResult> {
  return pythonIPCSupervisor.execute(scriptRelativePath, inputJson, args, timeoutMs);
}
