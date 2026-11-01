import path from "node:path";
import { existsSync } from "node:fs";
import { spawnSync, type SpawnSyncOptionsWithStringEncoding } from "node:child_process";
import dotenv from "dotenv";

export interface PythonCommand { cmd: string; prefix: string[] }
export interface PythonResolutionOptions {
  platform: string;
  cwd: string;
  env: Record<string, string | undefined>;
  exists: (file: string) => boolean;
  probe: (command: PythonCommand) => boolean;
}

/** Pure selection policy: all environment, filesystem and process operations are injected. */
export function resolvePythonCommand(options: PythonResolutionOptions): PythonCommand {
  const { platform, cwd, env, exists, probe } = options;
  const explicit = env.METALLIX_PYTHON;
  if (explicit) {
    const command = { cmd: explicit, prefix: [] };
    if (!probe(command)) {
      throw new Error("METALLIX_PYTHON failed its Python --version probe. Set it to one executable path without arguments; no fallback was attempted.");
    }
    return command;
  }
  const paths = platform === "win32" ? path.win32 : path.posix;
  const venvPython = (root: string) => paths.join(root, ...(platform === "win32" ? ["Scripts", "python.exe"] : ["bin", "python"]));
  const candidates: PythonCommand[] = [];
  for (const root of [paths.join(cwd, ".venv"), env.VIRTUAL_ENV]) {
    if (root) {
      const cmd = venvPython(root);
      if (exists(cmd)) candidates.push({ cmd, prefix: [] });
    }
  }
  candidates.push(...(platform === "win32"
    // The supported interpreters (3.12, then 3.11) come before "any Python 3": `py -3` selects the newest install,
    // which can be an unsupported 3.14 without numpy/scipy/warp while the supported one has them.
    ? [{ cmd: "py", prefix: ["-3.12"] }, { cmd: "py", prefix: ["-3.11"] }, { cmd: "py", prefix: ["-3"] },
      { cmd: "python", prefix: [] }, { cmd: "python3", prefix: [] }]
    : [{ cmd: "python3", prefix: [] }, { cmd: "python", prefix: [] }]));
  for (const command of candidates) if (probe(command)) return command;
  throw new Error("No working host Python found. Configure METALLIX_PYTHON or a project .venv / active VIRTUAL_ENV.");
}

type VersionProbeRunner = (cmd: string, args: string[], options: SpawnSyncOptionsWithStringEncoding) => {
  status: number | null; error?: Error; stdout?: string; stderr?: string;
};

export function probePythonCommand(command: PythonCommand, run: VersionProbeRunner = spawnSync): boolean {
  const result = run(command.cmd, [...command.prefix, "--version"], {
    encoding: "utf8", timeout: 5000, windowsHide: true, shell: false,
  });
  return !result.error && result.status === 0 && /^Python 3\./m.test(`${result.stdout || ""}\n${result.stderr || ""}`);
}

let environmentLoaded = false;
export function loadPythonEnvironment(): void {
  if (!environmentLoaded) {
    // Existing process variables take precedence. Do this before any interpreter selection.
    dotenv.config({ quiet: true, override: false });
    environmentLoaded = true;
  }
}

/** Lazy, cached resolution; importing this module never loads dotenv or probes Python. */
export function createPythonRuntime(options: PythonResolutionOptions, loadEnvironment: () => void): () => PythonCommand {
  let selected: PythonCommand | undefined;
  return () => {
    if (!selected) {
      loadEnvironment();
      selected = resolvePythonCommand(options);
    }
    return { cmd: selected.cmd, prefix: [...selected.prefix] };
  };
}

export const getHostPython = createPythonRuntime({
  platform: process.platform, cwd: process.cwd(), env: process.env,
  exists: existsSync, probe: probePythonCommand,
}, loadPythonEnvironment);

const WSL_PATH_VARIABLES = ["METALLIKSA_JOB_ROOT", "METALLIKSA_USER_BLIND_ROOT", "LPBF_MACHINE_CALIBRATION_DIR"] as const;
const WSL_PLAIN_VARIABLES = ["METALLIKSA_READ_ONLY", "METALLIKSA_HOST", "METALLIKSA_USER_BLIND_SINGLE_USER"] as const;

/** Environment for a WSL worker. Windows variables reach a wsl.exe child only when WSLENV lists them; without
 * this the WSL worker silently ignored the configured values. Each variable is handled on its own and is
 * forwarded only when it is set. Path variables (job root, user blind root, machine calibration directory) go
 * with the '/p' flag, which translates a drive path to /mnt/<drive>/...; WSL can do that only for a drive-letter
 * path, so UNC, \\wsl$ and Linux paths are rejected loudly, naming the variable. Plain variables (read-only
 * mode, host, blind single-user switch) are forwarded as they are. Existing WSLENV entries for the same names
 * are replaced and other entries keep their order. Returns a new object and never mutates env, or undefined
 * when none of these variables is set. */
function wslWorkerEnvironment(env: Record<string, string | undefined>): Record<string, string | undefined> | undefined {
  const overrides: Record<string, string> = {};
  const flagged: string[] = [];
  for (const name of WSL_PATH_VARIABLES) {
    const configured = env[name];
    if (!configured) continue;
    // A leading slash or backslash (UNC, \\wsl$, a Linux path, a root-relative path) would otherwise resolve
    // silently onto the current drive, so it is rejected before resolving; a relative path resolves against cwd.
    const resolved = /^[\\/]/.test(configured) ? configured : path.win32.resolve(configured);
    if (!/^[A-Za-z]:[\\/]/.test(resolved)) {
      throw new Error(`${name} must be a drive-letter path (for example C:\\lpbf-jobs) for the WSL LPBF worker; UNC, \\\\wsl$ and Linux paths cannot be forwarded: ${configured}`);
    }
    overrides[name] = resolved;
    flagged.push(`${name}/p`);
  }
  for (const name of WSL_PLAIN_VARIABLES) {
    const configured = env[name];
    if (!configured) continue;
    overrides[name] = configured;
    flagged.push(name);
  }
  if (flagged.length === 0) return undefined;
  const replaced = new Set<string>([...WSL_PATH_VARIABLES, ...WSL_PLAIN_VARIABLES].filter(name => name in overrides));
  const kept = (env.WSLENV ?? "").split(":").filter(entry => entry && !replaced.has(entry.split("/")[0]));
  return { ...env, ...overrides, WSLENV: [...kept, ...flagged].join(":") };
}

/** An explicit host executable takes precedence; otherwise keep WSL first on Windows. */
export function lpbfWorkerCommand(options: {
  platform: string; file: string; localFallback: boolean;
  env: Record<string, string | undefined>; hostPython: () => PythonCommand;
}): { cmd: string; args: string[]; env?: Record<string, string | undefined> } {
  if (options.platform === "win32" && !options.localFallback && !options.env.METALLIX_PYTHON) {
    const linuxPath = options.file.replace(/^([A-Za-z]):/, (_, drive: string) => `/mnt/${drive.toLowerCase()}`).replaceAll("\\", "/");
    const command = { cmd: "wsl.exe", args: ["-d", options.env.METALLIKSA_WSL_DISTRO || "Ubuntu-22.04", "--", "python3", "-u", linuxPath] };
    const env = wslWorkerEnvironment(options.env);
    return env ? { ...command, env } : command;
  }
  const python = options.hostPython();
  return { cmd: python.cmd, args: [...python.prefix, "-u", options.file] };
}
