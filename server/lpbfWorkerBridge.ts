import { spawn, ChildProcessWithoutNullStreams } from "node:child_process";
import path from "node:path";
import { createInterface } from "node:readline";
import { getHostPython, loadPythonEnvironment, lpbfWorkerCommand } from "./pythonRuntime.ts";
import { archiveJobRoot } from './lpbfArchivePaths';
import { gpuCapability, GpuCapabilityError } from '../src/utils/gpuCapability';

type WorkerCommand = { cmd: string; args: string[]; env?: Record<string, string | undefined> };
interface WorkerBridgeOptions {
  startupTimeoutMs?: number;
  requestTimeoutMs?: number;
  command?: (localFallback: boolean) => WorkerCommand;
  spawn?: (command: WorkerCommand) => ChildProcessWithoutNullStreams;
}

export class LpbfWorkerUnavailableError extends Error {
  constructor(message: string, public readonly code: 'LPBF_WORKER_STARTING' | 'LPBF_WORKER_UNAVAILABLE' = 'LPBF_WORKER_UNAVAILABLE') {
    super(message);
  }
}

/** Phase 6a validation envelope relayed by the worker RPC (rpc_error_response in
 * python/lpbf_worker.py); routes map it to HTTP 422 with the envelope as the body. */
export interface PythonValidationEnvelope {
  success: false;
  error: { code: string; field: string; message: string; detail: Record<string, unknown> };
  errorKind: "validation";
}

export class LpbfWorkerValidationError extends Error {
  constructor(public readonly envelope: PythonValidationEnvelope) {
    super(envelope.error.message);
  }
}

function validationEnvelope(reply: Record<string, unknown>): PythonValidationEnvelope | null {
  const env = reply.validation as Record<string, unknown> | undefined;
  if (reply.errorKind !== "validation" || !env || env.errorKind !== "validation") return null;
  const error = env.error as Record<string, unknown> | undefined;
  return error && typeof error.message === "string" ? env as unknown as PythonValidationEnvelope : null;
}

/** One worker owns the queue. Readiness outlives callers with shorter HTTP budgets. */
export class LpbfWorkerBridge {
  private process?: ChildProcessWithoutNullStreams;
  private starting?: Promise<void>;
  private readonly stopping = new Set<Promise<void>>();
  private readonly stoppingByChild = new WeakMap<ChildProcessWithoutNullStreams, Promise<void>>();
  private readonly transportFailures = new WeakMap<ChildProcessWithoutNullStreams, (error: Error) => void>();
  private pending = new Map<number, { child: ChildProcessWithoutNullStreams; resolve: (x: unknown) => void; reject: (e: Error) => void; timer: ReturnType<typeof setTimeout> }>();
  private sequence = 0;
  private localFallback = false;
  private generation = 0;
  private readonly startupTimeoutMs: number;
  private readonly requestTimeoutMs: number;

  constructor(private readonly options: WorkerBridgeOptions = {}) {
    this.startupTimeoutMs = options.startupTimeoutMs ?? 60000;
    this.requestTimeoutMs = options.requestTimeoutMs ?? 20000;
    for (const timeout of [this.startupTimeoutMs, this.requestTimeoutMs]) {
      if (!Number.isFinite(timeout) || timeout <= 0) throw new Error('Worker timeouts must be positive and finite');
    }
  }

  private async start(deadline: number, generation: number) {
    if (this.stopping.size) {
      const stopping = Promise.all([...this.stopping]).then(() => undefined);
      await new Promise<void>((resolve, reject) => {
        const timer = setTimeout(() => reject(new LpbfWorkerUnavailableError(
          'LPBF worker is restarting. Retry shortly.', 'LPBF_WORKER_STARTING')), Math.max(0, deadline - Date.now()));
        stopping.then(() => { clearTimeout(timer); resolve(); }, error => { clearTimeout(timer); reject(error); });
      });
    }
    if (generation !== this.generation) throw new LpbfWorkerUnavailableError('LPBF worker request was invalidated by close');
    // A spawned process may still be importing modules and initializing CUDA.
    if (!this.starting && this.process) return;
    let starting = this.starting;
    if (!starting) {
      starting = this.launch(generation, Date.now() + this.startupTimeoutMs)
        .catch(error => { throw error instanceof LpbfWorkerUnavailableError ? error
          : new LpbfWorkerUnavailableError(`LPBF worker startup failed: ${error instanceof Error ? error.message : String(error)}`); })
        .finally(() => { if (this.starting === starting) this.starting = undefined; });
      this.starting = starting;
      // Startup remains observed after all current HTTP callers have timed out.
      void starting.catch(() => {});
    }
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => reject(new LpbfWorkerUnavailableError(
        'LPBF worker is still starting. Retry shortly.', 'LPBF_WORKER_STARTING')), Math.max(0, deadline - Date.now()));
      starting!.then(() => { clearTimeout(timer); resolve(); }, error => { clearTimeout(timer); reject(error); });
    });
    if (generation !== this.generation) throw new LpbfWorkerUnavailableError('LPBF worker request was invalidated by close');
  }

  private rejectPending(child: ChildProcessWithoutNullStreams, error: Error) {
    for (const [id, pending] of this.pending) {
      if (pending.child !== child) continue;
      clearTimeout(pending.timer); this.pending.delete(id); pending.reject(error);
    }
  }

  private async stopChild(child: ChildProcessWithoutNullStreams) {
    if (child.exitCode !== null || child.signalCode !== null || !child.pid) return;
    await new Promise<void>(resolve => {
      const finish = () => { clearTimeout(timer); child.off('close', finish); child.off('exit', finish); resolve(); };
      const timer = setTimeout(() => { child.kill('SIGKILL'); }, 1000);
      child.once('close', finish);
      child.once('exit', finish);
      child.kill();
    });
  }

  private stopTracked(child: ChildProcessWithoutNullStreams) {
    // Track per child: a stop in flight for another child must not swallow this one.
    const existing = this.stoppingByChild.get(child);
    if (existing) return existing;
    const stopping = this.stopChild(child).finally(() => {
      this.stopping.delete(stopping);
      this.stoppingByChild.delete(child);
    });
    this.stopping.add(stopping);
    this.stoppingByChild.set(child, stopping);
    return stopping;
  }

  private async launch(generation: number, deadline: number): Promise<void> {
    loadPythonEnvironment();
    const file = path.resolve("python/lpbf_worker.py");
    const command = this.options.command?.(this.localFallback) ?? lpbfWorkerCommand({ platform: process.platform, file,
      localFallback: this.localFallback, env: process.env, hostPython: getHostPython });
    const attemptedWsl = path.win32.basename(command.cmd).toLowerCase() === 'wsl.exe';
    const child = this.options.spawn?.(command) ?? spawn(command.cmd, command.args, { windowsHide: true, stdio: "pipe", env: command.env ?? process.env });
    this.process = child;
    let stderr = "";
    // Bounded ring of non-JSON stdout lines, kept apart from stderr for error detail.
    const stdoutNoise: string[] = [];
    createInterface({ input: child.stdout }).on("line", line => {
      try {
        const reply = JSON.parse(line);
        const wait = this.pending.get(reply.id);
        if (!wait || wait.child !== child) return;
        clearTimeout(wait.timer); this.pending.delete(reply.id);
        if (reply.error) {
          const envelope = validationEnvelope(reply);
          const capability = reply.errorKind === 'capability' ? gpuCapability(reply.capability) : null;
          wait.reject(capability ? new GpuCapabilityError(capability)
            : envelope ? new LpbfWorkerValidationError(envelope) : new Error(reply.error));
        } else wait.resolve(reply.data);
      } catch { stdoutNoise.push(line.slice(0, 500)); if (stdoutNoise.length > 20) stdoutNoise.shift(); }
    });
    child.stderr.on("data", data => { stderr = (stderr + data.toString()).slice(-4000); });
    let failed = false;
    const fail = (error: Error) => {
      if (failed) return;
      failed = true;
      const unavailable = error instanceof LpbfWorkerUnavailableError ? error
        : new LpbfWorkerUnavailableError(`LPBF worker transport error: ${error.message}`);
      if (this.process === child) this.process = undefined;
      this.rejectPending(child, unavailable);
      void this.stopTracked(child);
    };
    this.transportFailures.set(child, fail);
    child.on("error", fail);
    child.stdin.on('error', fail);
    child.on("exit", code => fail(new LpbfWorkerUnavailableError(`LPBF worker exited (${code}): ${stderr}`
      + (stdoutNoise.length ? ` | non-JSON stdout: ${stdoutNoise.join(' / ')}` : ''))));
    try { await this.send("capabilities", null, deadline - Date.now()); }
    catch (error) {
      if (this.process === child) this.process = undefined;
      this.rejectPending(child, error instanceof Error ? error : new Error(String(error)));
      await this.stopTracked(child);
      if (generation === this.generation && attemptedWsl && !this.localFallback && Date.now() < deadline) {
        this.localFallback = true;
        return this.launch(generation, deadline);
      }
      throw error;
    }
  }

  private send(method: string, payload: unknown, timeoutMs: number): Promise<unknown> {
    const child = this.process;
    if (!child) return Promise.reject(new LpbfWorkerUnavailableError('LPBF worker is unavailable'));
    if (timeoutMs <= 0) return Promise.reject(new LpbfWorkerUnavailableError('LPBF worker request deadline exceeded'));
    const id = ++this.sequence;
    const message = JSON.stringify({ id, method, payload }) + "\n";
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.pending.delete(id); reject(new LpbfWorkerUnavailableError("LPBF worker RPC timeout")); }, timeoutMs);
      this.pending.set(id, { child, resolve, reject, timer });
      const written = (error?: Error | null) => {
        if (error) this.transportFailures.get(child)?.(error);
      };
      try { child.stdin.write(message, written); }
      catch (error) { written(error instanceof Error ? error : new Error(String(error))); }
    });
  }

  async request(method: string, payload: unknown = null) {
    const generation = this.generation;
    const deadline = Date.now() + this.requestTimeoutMs;
    await this.start(deadline, generation);
    if (generation !== this.generation) throw new LpbfWorkerUnavailableError('LPBF worker request was invalidated by close');
    return this.send(method, payload, deadline - Date.now());
  }

  async captureForArchive(jobId: string) {
    if (!/^[a-f0-9]{32}$/.test(jobId)) throw new Error('Invalid job id');
    const reply = await this.request('archive-capture', jobId) as { capture: unknown; root: string; platform: string };
    return { capture: reply.capture, root: path.join(archiveJobRoot(reply.root, reply.platform, process.platform), jobId) };
  }

  close() {
    this.generation++;
    const child = this.process;
    this.process = undefined;
    this.starting = undefined;
    if (!child) return;
    this.rejectPending(child, new LpbfWorkerUnavailableError('LPBF worker was closed'));
    void this.stopTracked(child);
  }
}

export const lpbfWorker = new LpbfWorkerBridge();
