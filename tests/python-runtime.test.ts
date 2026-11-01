import assert from "node:assert/strict";
import { test } from "node:test";
import dotenv from "dotenv";
import { createPythonRuntime, lpbfWorkerCommand, probePythonCommand, resolvePythonCommand,
  type PythonCommand, type PythonResolutionOptions } from "../server/pythonRuntime.ts";

function fixture(platform = "win32", env: Record<string, string | undefined> = {}) {
  const calls: PythonCommand[] = [];
  const files = new Set<string>();
  const working = new Set<string>();
  const options: PythonResolutionOptions = { platform, cwd: platform === "win32" ? "C:\\project space" : "/project space", env,
    exists: file => files.has(file), probe: command => { calls.push(command); return working.has(command.cmd); } };
  return { options, calls, files, working };
}

for (const [platform, executable] of [["win32", "C:\\GPU environment\\Scripts\\python.exe"], ["linux", "/gpu environment/bin/python"]]) {
  test(`${platform}: explicit executable with spaces remains one argument`, () => {
    const f = fixture(platform, { METALLIX_PYTHON: executable });
    f.working.add(executable);
    assert.deepEqual(resolvePythonCommand(f.options), { cmd: executable, prefix: [] });
    assert.equal(f.calls.length, 1);
  });
  test(`${platform}: invalid explicit selection never falls back`, () => {
    const f = fixture(platform, { METALLIX_PYTHON: executable });
    f.working.add("python3");
    assert.throws(() => resolvePythonCommand(f.options), /METALLIX_PYTHON.*no fallback/);
    assert.equal(f.calls.length, 1);
  });
}

for (const [platform, project, active] of [
  ["win32", "C:\\project space\\.venv\\Scripts\\python.exe", "C:\\active space\\Scripts\\python.exe"],
  ["linux", "/project space/.venv/bin/python", "/active space/bin/python"],
]) {
  test(`${platform}: project venv precedes active venv, then system`, () => {
    const f = fixture(platform, { VIRTUAL_ENV: platform === "win32" ? "C:\\active space" : "/active space" });
    f.files.add(project); f.files.add(active);
    f.working.add(project); f.working.add(active);
    assert.equal(resolvePythonCommand(f.options).cmd, project);
    f.working.delete(project);
    assert.equal(resolvePythonCommand(f.options).cmd, active);
    f.working.delete(active); f.working.add("python");
    assert.equal(resolvePythonCommand(f.options).cmd, "python");
  });
}

test("missing venvs are skipped; the Windows launcher prefers the supported 3.12", () => {
  const f = fixture(); f.working.add("py");
  assert.deepEqual(resolvePythonCommand(f.options), { cmd: "py", prefix: ["-3.12"] });
  assert.equal(f.calls.length, 1);
});

test("Windows launcher: 3.12, then 3.11, then any Python 3 (never the newest first)", () => {
  const installed = (...versions: string[]) => {
    const f = fixture();
    f.options.probe = command => { f.calls.push(command); return command.cmd === "py" && versions.includes(command.prefix[0]); };
    return f;
  };
  assert.deepEqual(resolvePythonCommand(installed("-3.12", "-3.11", "-3").options), { cmd: "py", prefix: ["-3.12"] });
  assert.deepEqual(resolvePythonCommand(installed("-3.11", "-3").options), { cmd: "py", prefix: ["-3.11"] });
  const only3 = installed("-3");
  assert.deepEqual(resolvePythonCommand(only3.options), { cmd: "py", prefix: ["-3"] });
  assert.deepEqual(only3.calls.map(c => c.prefix[0]), ["-3.12", "-3.11", "-3"]);
});

test("Unix system preference and complete failure", () => {
  const f = fixture("linux"); f.working.add("python3"); f.working.add("python");
  assert.equal(resolvePythonCommand(f.options).cmd, "python3");
  f.working.clear();
  assert.throws(() => resolvePythonCommand(f.options), /No working host Python/);
});

test("runtime is lazy, loads environment before selection and caches successful result", () => {
  const f = fixture(); f.working.add("configured after dotenv");
  let loads = 0;
  const runtime = createPythonRuntime(f.options, () => {
    loads++; f.options.env.METALLIX_PYTHON = "configured after dotenv";
  });
  assert.equal(loads, 0); assert.equal(f.calls.length, 0);
  assert.equal(runtime().cmd, "configured after dotenv");
  runtime().prefix.push("unwanted");
  assert.deepEqual(runtime().prefix, []);
  assert.equal(loads, 1); assert.equal(f.calls.length, 1);
});

test("WSL remains first and never resolves host Python", () => {
  const command = lpbfWorkerCommand({ platform: "win32", file: "C:\\project space\\python\\lpbf_worker.py",
    localFallback: false, env: { METALLIKSA_WSL_DISTRO: "Research Linux" },
    hostPython: () => { throw new Error("must not probe host"); } });
  assert.deepEqual(command, { cmd: "wsl.exe", args: ["-d", "Research Linux", "--", "python3", "-u", "/mnt/c/project space/python/lpbf_worker.py"] });
});

test("a configured job root is forwarded to the WSL worker through WSLENV without mutating the input env", () => {
  const env = { METALLIKSA_JOB_ROOT: "D:/lpbf jobs/run", WSLENV: "USERPROFILE/p:METALLIKSA_JOB_ROOT/u:TERM", PATH: "C:\\bin" };
  const before = { ...env };
  const command = lpbfWorkerCommand({ platform: "win32", file: "C:\\project\\python\\lpbf_worker.py", localFallback: false, env,
    hostPython: () => { throw new Error("must not probe host"); } });
  assert.equal(command.cmd, "wsl.exe");
  assert.deepEqual(command.env, { ...env, METALLIKSA_JOB_ROOT: "D:\\lpbf jobs\\run",
    WSLENV: "USERPROFILE/p:TERM:METALLIKSA_JOB_ROOT/p" });
  assert.deepEqual(env, before, "the caller's environment (process.env in the bridge) is not mutated");

  const unset = lpbfWorkerCommand({ platform: "win32", file: "C:/w.py", localFallback: false, env: {},
    hostPython: () => { throw new Error("must not probe host"); } });
  assert.equal("env" in unset, false, "without a configured root the bridge keeps its own environment");
  const noPrior = lpbfWorkerCommand({ platform: "win32", file: "C:/w.py", localFallback: false,
    env: { METALLIKSA_JOB_ROOT: "C:\\jobs" }, hostPython: () => { throw new Error("must not probe host"); } });
  assert.equal(noPrior.env?.WSLENV, "METALLIKSA_JOB_ROOT/p");

  for (const root of ["\\\\server\\share\\jobs", "\\\\wsl$\\Ubuntu-22.04\\home\\jobs", "\\\\?\\UNC\\server\\share", "/home/user/jobs", "\\jobs"]) {
    assert.throws(() => lpbfWorkerCommand({ platform: "win32", file: "C:/w.py", localFallback: false,
      env: { METALLIKSA_JOB_ROOT: root }, hostPython: () => { throw new Error("must not probe host"); } }),
    /METALLIKSA_JOB_ROOT must be a drive-letter path/, root);
  }
  // Host interpreters read the variable directly; the host command keeps the bridge's environment.
  const host = lpbfWorkerCommand({ platform: "win32", file: "C:/w.py", localFallback: true,
    env: { METALLIKSA_JOB_ROOT: "\\\\server\\share\\jobs" }, hostPython: () => ({ cmd: "py", prefix: ["-3"] }) });
  assert.deepEqual(host, { cmd: "py", args: ["-3", "-u", "C:/w.py"] });
});

const noHost = () => { throw new Error("must not probe host"); };
function wslEnv(env: Record<string, string | undefined>) {
  return lpbfWorkerCommand({ platform: "win32", file: "C:/w.py", localFallback: false, env, hostPython: noHost }).env;
}

test("WSL forwards blind, read-only, host and calibration variables through WSLENV", () => {
  const env = {
    METALLIKSA_USER_BLIND_ROOT: "D:/blind data", METALLIKSA_READ_ONLY: "1", METALLIKSA_HOST: "0.0.0.0",
    METALLIKSA_USER_BLIND_SINGLE_USER: "1", LPBF_MACHINE_CALIBRATION_DIR: "E:\\calibration", METALLIKSA_JOB_ROOT: "C:\\jobs",
    WSLENV: "TERM:METALLIKSA_HOST/u:USERPROFILE/p",
  };
  const out = wslEnv(env);
  assert.ok(out);
  assert.equal(out.METALLIKSA_USER_BLIND_ROOT, "D:\\blind data", "path values are the drive-letter form");
  assert.equal(out.LPBF_MACHINE_CALIBRATION_DIR, "E:\\calibration");
  assert.equal(out.METALLIKSA_JOB_ROOT, "C:\\jobs");
  assert.equal(out.METALLIKSA_READ_ONLY, "1");
  assert.deepEqual(out.WSLENV?.split(":"), ["TERM", "USERPROFILE/p", "METALLIKSA_JOB_ROOT/p", "METALLIKSA_USER_BLIND_ROOT/p",
    "LPBF_MACHINE_CALIBRATION_DIR/p", "METALLIKSA_READ_ONLY", "METALLIKSA_HOST", "METALLIKSA_USER_BLIND_SINGLE_USER"]);
});

test("WSL forwards every other variable when METALLIKSA_JOB_ROOT is unset, and only the set ones", () => {
  const out = wslEnv({ METALLIKSA_READ_ONLY: "1", METALLIKSA_USER_BLIND_ROOT: "C:\\blind", METALLIKSA_HOST: "" });
  assert.ok(out);
  assert.equal(out.WSLENV, "METALLIKSA_USER_BLIND_ROOT/p:METALLIKSA_READ_ONLY");
  assert.equal("METALLIKSA_JOB_ROOT" in out, false);
  assert.equal(wslEnv({ METALLIKSA_HOST: "", PATH: "C:\\bin" }), undefined, "nothing set means no env override");
});

test("WSL environment forwarding does not mutate the input env", () => {
  const env = { METALLIKSA_USER_BLIND_ROOT: "blind", METALLIKSA_READ_ONLY: "1", WSLENV: "METALLIKSA_READ_ONLY/u" };
  const before = { ...env };
  const out = wslEnv(env);
  assert.deepEqual(env, before);
  assert.notEqual(out, env);
  assert.equal(out?.WSLENV, "METALLIKSA_USER_BLIND_ROOT/p:METALLIKSA_READ_ONLY");
  assert.match(out?.METALLIKSA_USER_BLIND_ROOT ?? "", /^[A-Za-z]:\\/, "relative paths resolve to a drive-letter path");
});

test("WSL rejects non-drive-letter path variables and names the variable", () => {
  for (const name of ["METALLIKSA_USER_BLIND_ROOT", "LPBF_MACHINE_CALIBRATION_DIR", "METALLIKSA_JOB_ROOT"]) {
    for (const value of ["\\\\server\\share\\blind", "\\\\wsl$\\Ubuntu-22.04\\home\\x", "/home/user/blind"]) {
      assert.throws(() => wslEnv({ [name]: value }), new RegExp(`${name} must be a drive-letter path`), `${name} ${value}`);
    }
  }
});

test("explicit host Python also controls the first LPBF worker launch", () => {
  const python = { cmd: 'C:/scientific env/python.exe', prefix: [] };
  const command = lpbfWorkerCommand({ platform: 'win32', file: 'C:/project/python/lpbf_worker.py',
    localFallback: false, env: { METALLIX_PYTHON: python.cmd }, hostPython: () => python });
  assert.deepEqual(command, { cmd: python.cmd, args: ['-u', 'C:/project/python/lpbf_worker.py'] });
});

test("preexisting process override wins over dotenv values", () => {
  const f = fixture("win32", { METALLIX_PYTHON: "shell python" });
  f.working.add("shell python");
  const runtime = createPythonRuntime(f.options, () => {
    dotenv.populate(f.options.env as Record<string, string>, { METALLIX_PYTHON: "file python" }, { override: false });
  });
  assert.equal(runtime().cmd, "shell python");
});

test("LPBF Windows host fallback and Unix host use exact shared command", () => {
  for (const platform of ["win32", "linux"]) {
    for (const python of [{ cmd: "C:/GPU environment/python.exe", prefix: [] }, { cmd: "py", prefix: ["-3"] }]) {
      assert.deepEqual(lpbfWorkerCommand({ platform, file: "/project space/python/lpbf_worker.py",
        localFallback: true, env: {}, hostPython: () => python }),
      { cmd: python.cmd, args: [...python.prefix, "-u", "/project space/python/lpbf_worker.py"] });
    }
  }
});

test("LPBF propagates invalid host configuration", () => {
  assert.throws(() => lpbfWorkerCommand({ platform: "win32", file: "C:/worker.py", localFallback: true,
    env: {}, hostPython: () => { throw new Error("METALLIX_PYTHON invalid"); } }), /METALLIX_PYTHON invalid/);
});

test("version probe is bounded, hidden, shell-free, and requires Python 3", () => {
  const run = ((cmd, args, options) => {
    assert.equal(cmd, "C:/path with spaces/python.exe");
    assert.deepEqual(args, ["--version"]);
    assert.equal(options.timeout, 5000);
    assert.equal(options.windowsHide, true); assert.equal(options.shell, false);
    return { status: 0, stdout: "Python 3.12.10\n", stderr: "" };
  }) as Parameters<typeof probePythonCommand>[1];
  const command = { cmd: "C:/path with spaces/python.exe", prefix: [] };
  assert.equal(probePythonCommand(command, run), true);
  for (const result of [{ status: 0, stdout: "Python 2.7.18" }, { status: 0, stdout: "v24.0.0" },
    { status: null, error: new Error("ETIMEDOUT") }, { status: 1, stdout: "Python 3.12" }]) {
    assert.equal(probePythonCommand(command, (() => result) as Parameters<typeof probePythonCommand>[1]), false);
  }
});
