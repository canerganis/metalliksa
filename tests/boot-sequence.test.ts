import assert from "node:assert/strict";
import { test } from "node:test";
import {
  BOOT_EXIT_DELAY_MS,
  BOOT_STEP_TIMEOUT_MS,
  bootAnnouncement,
  bootCountLive,
  bootSummary,
  createBootController,
  type BootOutcome,
  type BootSnapshot,
  type BootStep,
  type BootStepState,
} from "../src/utils/bootSequence";
import { buildBootSteps, describeEngine, type BootStepDeps } from "../src/services/bootSteps";
import { telemetryCells, type TelemetryInputs } from "../src/components/TelemetryStrip";
import { pythonComputationService } from "../src/services/pythonComputationService";

// setImmediate is not faked, so this drains pending promise callbacks between timer ticks.
const flush = async () => {
  for (let i = 0; i < 5; i += 1) await new Promise<void>((r) => setImmediate(r));
};

function step(id: string, run: () => Promise<BootOutcome>, log?: string[]): BootStep {
  return { id, label: id, run: () => (log?.push(id), run()) };
}
const ok = (detail = "fine"): (() => Promise<BootOutcome>) => async () => ({ state: "ok", detail });
const never = () => new Promise<BootOutcome>(() => undefined);

test("runs checks strictly in order, one at a time, and counts k/N", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const log: string[] = [];
  let releaseFirst!: () => void;
  const first = () => new Promise<BootOutcome>((r) => (releaseFirst = () => r({ state: "ok", detail: "a" })));
  const c = createBootController({ steps: [step("a", first, log), step("b", ok("b"), log), step("c", ok("c"), log)] });
  void c.start();
  await flush();
  assert.deepEqual(log, ["a"], "second check must not start before the first finishes");
  assert.equal(c.getSnapshot().rows[0].state, "running");
  assert.equal(c.getSnapshot().rows[1].state, "pending");
  assert.equal(c.getSnapshot().finished, 0);
  releaseFirst();
  await flush();
  assert.deepEqual(log, ["a", "b", "c"]);
  const snap = c.getSnapshot();
  assert.deepEqual(snap.rows.map((r) => [r.id, r.state, r.detail]), [["a", "ok", "a"], ["b", "ok", "b"], ["c", "ok", "c"]]);
  assert.equal(snap.finished, 3);
  assert.equal(snap.total, 3);
  assert.equal(snap.phase, "complete");
});

test("no minimum duration: exit is exactly 300 ms after the last check", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const c = createBootController({ steps: [step("a", ok()), step("b", ok())] });
  void c.start();
  await flush();
  assert.equal(c.getSnapshot().phase, "complete");
  t.mock.timers.tick(BOOT_EXIT_DELAY_MS - 1);
  assert.equal(c.getSnapshot().phase, "complete");
  t.mock.timers.tick(1);
  assert.equal(c.getSnapshot().phase, "done");
  assert.equal(BOOT_EXIT_DELAY_MS, 300);
});

test("a check that does not answer within 8 s is recorded as timed-out and the next check runs", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const log: string[] = [];
  const c = createBootController({ steps: [step("slow", never, log), step("next", ok("after"), log)] });
  void c.start();
  await flush();
  t.mock.timers.tick(BOOT_STEP_TIMEOUT_MS - 1);
  await flush();
  assert.equal(c.getSnapshot().rows[0].state, "running");
  assert.deepEqual(log, ["slow"]);
  t.mock.timers.tick(1);
  await flush();
  const snap = c.getSnapshot();
  assert.equal(snap.rows[0].state, "timed-out");
  assert.match(snap.rows[0].detail, /No answer within 8 s/);
  assert.equal(snap.rows[1].state, "ok");
  assert.deepEqual(log, ["slow", "next"]);
  assert.equal(snap.finished, 2);
  assert.equal(BOOT_STEP_TIMEOUT_MS, 8000);
});

test("a late answer after the 8 s timeout is ignored: the row stays timed-out", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let late!: (o: BootOutcome) => void;
  const c = createBootController({ steps: [step("slow", () => new Promise((r) => (late = r))), step("next", ok("after"))] });
  void c.start();
  await flush();
  t.mock.timers.tick(BOOT_STEP_TIMEOUT_MS);
  await flush();
  assert.equal(c.getSnapshot().rows[0].state, "timed-out");
  late({ state: "ok", detail: "too late" });
  await flush();
  const snap = c.getSnapshot();
  assert.deepEqual([snap.rows[0].state, snap.rows[0].detail.startsWith("No answer within 8 s")], ["timed-out", true]);
  assert.deepEqual([snap.rows[1].state, snap.rows[1].detail], ["ok", "after"]);
  assert.equal(snap.finished, 2);
});

test("a failing check (throw or reject) is recorded with its reason and boot continues", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const c = createBootController({
    steps: [
      { id: "throws", label: "throws", run: () => { throw new Error("sync boom"); } },
      step("rejects", async () => { throw new Error("HTTP 503"); }),
      step("limited", async () => ({ state: "limited", detail: "degraded" })),
      step("last", ok()),
    ],
  });
  void c.start();
  await flush();
  const rows = c.getSnapshot().rows;
  assert.deepEqual(rows.map((r) => r.state), ["unavailable", "unavailable", "limited", "ok"]);
  assert.equal(rows[0].detail, "sync boom");
  assert.equal(rows[1].detail, "HTTP 503");
  assert.equal(c.getSnapshot().phase, "complete");
});

test("a blocked check (sign-in required) stops boot; later checks are not run and there is no auto-exit", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const log: string[] = [];
  const c = createBootController({
    steps: [step("config", ok(), log), step("access", async () => ({ state: "blocked", detail: "Sign-in required" }), log), step("engine", ok(), log)],
  });
  void c.start();
  await flush();
  t.mock.timers.tick(10_000);
  const snap = c.getSnapshot();
  assert.deepEqual(log, ["config", "access"]);
  assert.equal(snap.phase, "stopped");
  assert.equal(snap.rows[1].state, "blocked");
  assert.equal(snap.rows[2].state, "not-run");
  assert.equal(snap.finished, 2);
});

test("skip hides the presentation but never skips or cancels the checks", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const log: string[] = [];
  let release!: () => void;
  const c = createBootController({
    steps: [step("a", () => new Promise((r) => (release = () => r({ state: "ok", detail: "a" }))), log), step("b", ok(), log)],
  });
  void c.start();
  await flush();
  c.skip();
  assert.equal(c.getSnapshot().dismissed, true);
  assert.equal(c.getSnapshot().animate, false);
  release();
  await flush();
  assert.deepEqual(log, ["a", "b"]);
  assert.equal(c.getSnapshot().finished, 2);
  assert.equal(c.getSnapshot().phase, "complete");
});

test("reduced motion and a remembered skip disable animation; checks still run", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  for (const opts of [{ reducedMotion: true }, { skipAnimation: true }]) {
    const log: string[] = [];
    const c = createBootController({ steps: [step("a", ok(), log)], ...opts });
    assert.equal(c.getSnapshot().animate, false);
    assert.equal(c.getSnapshot().dismissed, false, "the static checklist is still shown");
    void c.start();
    await flush();
    assert.deepEqual(log, ["a"]);
  }
  assert.equal(createBootController({ steps: [] }).getSnapshot().animate, true);
});

test("start is idempotent (StrictMode double effects run each check once)", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const log: string[] = [];
  const c = createBootController({ steps: [step("a", ok(), log)] });
  const p1 = c.start();
  const p2 = c.start();
  assert.equal(p1, p2);
  await flush();
  assert.deepEqual(log, ["a"]);
});

// --- Real step wiring with injected sources --------------------------------------------------

function deps(over: Partial<BootStepDeps> & { probe?: BootStepDeps["probe"] } = {}): BootStepDeps {
  return {
    loadConfig: async () => ({ airgapped: false, blockedServices: [], allowedLocal: [] }),
    probe: () => ({ loaded: true, accessRequired: false, failure: null }),
    engineStatus: async () => ({ online: true, status: "online", pythonVersion: "3.12.10", subsystems: { calphad_solver: { available: true }, pourbaix_solver: { available: true } } }),
    moduleCount: () => 37,
    ...over,
  };
}

async function runAll(d: BootStepDeps) {
  const c = createBootController({ steps: buildBootSteps(d) });
  await c.start();
  return c.getSnapshot();
}

test("real steps: order and honest wording when every source answers", async () => {
  const snap = await runAll(deps());
  assert.deepEqual(snap.rows.map((r) => r.id), ["runtime-config", "access", "airgap", "engine", "modules"]);
  assert.deepEqual(snap.rows.map((r) => r.state), ["ok", "ok", "ok", "ok", "ok"]);
  assert.equal(snap.rows[3].detail, "Python engine online · Python 3.12.10 · 2/2 subsystems available");
  for (const row of snap.rows) assert.doesNotMatch(row.detail, /validat|ready|certif/i, `${row.id} must not claim validation or readiness`);
});

test("real steps: config failure is amber with the reason, access and air-gap are not invented", async () => {
  const snap = await runAll(deps({ probe: () => ({ loaded: false, accessRequired: false, failure: "HTTP 500" }) }));
  assert.equal(snap.rows[0].state, "limited");
  assert.match(snap.rows[0].detail, /Config unavailable \(HTTP 500\)/);
  assert.equal(snap.rows[1].state, "unavailable");
  assert.equal(snap.rows[2].state, "unavailable", "air-gap must not report OFF from fallback defaults");
  assert.equal(snap.phase, "complete");
});

test("real steps: 401 stops boot at the access check", async () => {
  let engineCalled = false;
  const snap = await runAll(
    deps({
      probe: () => ({ loaded: false, accessRequired: true, failure: "HTTP 401" }),
      engineStatus: async () => ((engineCalled = true), { online: true, status: "online" }),
    }),
  );
  assert.equal(snap.phase, "stopped");
  assert.equal(snap.rows[1].state, "blocked");
  assert.equal(snap.rows[1].detail, "Sign-in required");
  assert.deepEqual(snap.rows.slice(2).map((r) => r.state), ["not-run", "not-run", "not-run"]);
  assert.equal(engineCalled, false);
});

test("real steps: air-gap ON counts only services the server listed", async () => {
  const on = await runAll(deps({ loadConfig: async () => ({ airgapped: true, blockedServices: ["a", "b", "c"], allowedLocal: [] }) }));
  assert.equal(on.rows[2].state, "limited");
  assert.equal(on.rows[2].detail, "Air-gap ON · 3 services cut");
  const unlisted = await runAll(deps({ loadConfig: async () => ({ airgapped: true, blockedServices: [], allowedLocal: [] }) }));
  assert.equal(unlisted.rows[2].detail, "Air-gap ON · cut services not listed");
});

test("engine wording: 'online' only when the status call says so", () => {
  const down = describeEngine({ online: false, status: "client_fallback" });
  assert.equal(down.state, "unavailable");
  assert.doesNotMatch(down.detail, /online/);
  assert.match(down.detail, /status request failed/);
  const partial = describeEngine({ online: true, status: "online", subsystems: { calphad_solver: { available: true }, pourbaix_solver: { available: false } } });
  assert.equal(partial.state, "limited");
  assert.match(partial.detail, /Python version not reported · 1\/2 subsystems available/);
  const bare = describeEngine({ online: true, status: "online", pythonVersion: "3.12.1" });
  assert.equal(bare.state, "ok", "online comes from the status call; missing subsystems are not a fault");
  assert.equal(bare.detail, "Python engine online · Python 3.12.1 · subsystems: not reported");
  // What the live server sends today: subsystemStatus "unverified" and no map. Never a count.
  const live = describeEngine({ online: true, status: "online", pythonVersion: "3.14.5", subsystemStatus: "unverified" });
  assert.equal(live.state, "ok");
  assert.equal(live.detail, "Python engine online · Python 3.14.5 · subsystems: unverified (server)");
  assert.doesNotMatch(live.detail, /\d+\/\d+/);
});

test("the status service passes the server's subsystemStatus through (and only a string)", async () => {
  const realFetch = globalThis.fetch;
  const reply = (body: unknown) => (async () => new Response(JSON.stringify(body), { status: 200 })) as typeof fetch;
  try {
    globalThis.fetch = reply({ status: "online", pythonVersion: "3.14.5", subsystemStatus: "unverified" });
    const s = await pythonComputationService.checkEngineStatus(true);
    assert.equal(s.online, true);
    assert.equal(s.subsystemStatus, "unverified");
    assert.equal(s.subsystems, undefined);
    globalThis.fetch = reply({ status: "online", subsystemStatus: { odd: true } });
    assert.equal((await pythonComputationService.checkEngineStatus(true)).subsystemStatus, undefined);
  } finally {
    globalThis.fetch = realFetch;
  }
});

test("module registry row reports the bundled registry, not a probe", async () => {
  const snap = await runAll(deps());
  assert.equal(snap.rows[4].detail, "Bundled with the app · 37 modules (not probed)");
  const empty = await runAll(deps({ moduleCount: () => 0 }));
  assert.deepEqual([empty.rows[4].state, empty.rows[4].detail], ["unavailable", "Registry empty"]);
});

// --- Telemetry strip mapping ------------------------------------------------------------------

const baseInputs: TelemetryInputs = {
  config: { airgapped: false, blockedServices: [], allowedLocal: [] },
  accessRequired: false,
  engine: { online: true, status: "online", pythonVersion: "3.12.10", subsystems: { calphad_solver: { available: true }, pourbaix_solver: { available: false } } },
  engineChecking: false,
  moduleCount: 37,
  boot: { finished: 5, total: 5, stopped: false, rows: [] },
};
const bootRows = (...pairs: Array<[string, BootStepState]>) => pairs.map(([label, state]) => ({ label, state }));
const cellMap = (input: TelemetryInputs) => Object.fromEntries(telemetryCells(input).map((c) => [c.label, `${c.value}|${c.tone}`]));

test("telemetry cells show source values", () => {
  assert.deepEqual(cellMap(baseInputs), {
    "Air-gap": "OFF|ok",
    Access: "accepted|ok",
    Engine: "online · Python 3.12.10|ok",
    Subsystems: "1/2|warn",
    Modules: "37 registered|neutral",
    "Start-up checks": "5/5|neutral",
  });
});

test("a start-up engine failure is not repeated once the live status reports the engine online", () => {
  const rows = bootRows(["Runtime configuration", "ok"], ["Python engine", "unavailable"]);
  const online = cellMap({ ...baseInputs, boot: { finished: 5, total: 5, stopped: false, rows } });
  assert.equal(online["Start-up checks"], "5/5|neutral");
  const offline = cellMap({ ...baseInputs, engine: { online: false, status: "client_fallback" }, boot: { finished: 5, total: 5, stopped: false, rows } });
  assert.equal(offline["Start-up checks"], "5/5 · unavailable: Python engine|fail");
});

test("telemetry cells read 'unavailable' with no data and never show placeholder numbers", () => {
  const cells = cellMap({
    ...baseInputs,
    config: null,
    engine: { online: false, status: "client_fallback" },
    moduleCount: 0,
    boot: { finished: 5, total: 5, stopped: false, rows: bootRows(["Runtime configuration", "ok"], ["Python engine", "timed-out"]) },
  });
  assert.equal(cells["Air-gap"], "unavailable|fail");
  assert.equal(cells.Access, "unavailable|fail");
  assert.equal(cells.Engine, "unavailable|fail");
  assert.equal(cells.Subsystems, "unavailable|fail");
  assert.equal(cells.Modules, "unavailable|fail");
  assert.equal(cells["Start-up checks"], "5/5 · timed out: Python engine|fail");
  const pending = cellMap({ ...baseInputs, config: undefined, engine: null, engineChecking: true });
  assert.equal(pending["Air-gap"], "checking|neutral");
  assert.equal(pending.Engine, "checking|neutral");
  assert.equal(pending.Subsystems, "checking|neutral");
  assert.equal(cellMap({ ...baseInputs, accessRequired: true }).Access, "sign-in required|fail");
  // The live server sends subsystemStatus "unverified" and no subsystems map: never invent a count,
  // and do not show an amber that can never clear.
  assert.equal(cellMap({ ...baseInputs, engine: { online: true, status: "online", pythonVersion: "3.12.10" } }).Subsystems, "not reported|neutral");
  assert.equal(
    cellMap({ ...baseInputs, engine: { online: true, status: "online", pythonVersion: "3.14.5", subsystemStatus: "unverified" } }).Subsystems,
    "unverified (server)|neutral",
  );
  assert.equal(cellMap({ ...baseInputs, config: { airgapped: true, blockedServices: ["x", "y"], allowedLocal: [] } })["Air-gap"], "ON · 2 cut|warn");
});

test("start-up checks cell names stopped, unavailable, timed-out and limited steps with a non-neutral tone", () => {
  const boot = (stopped: boolean, ...pairs: Array<[string, BootStepState]>) =>
    cellMap({ ...baseInputs, boot: { finished: pairs.length, total: 5, stopped, rows: bootRows(...pairs) } })["Start-up checks"];
  assert.equal(boot(true, ["Runtime configuration", "limited"], ["Access", "blocked"], ["Air-gap", "not-run"]), "stopped at Access|fail");
  // baseInputs reports the engine online now, so its start-up time-out is stale and not repeated.
  assert.equal(boot(false, ["Air-gap", "unavailable"], ["Python engine", "timed-out"]), "2/5 · unavailable: Air-gap|fail");
  assert.equal(boot(false, ["Runtime configuration", "limited"]), "1/5 · limited: Runtime configuration|warn");
  assert.equal(boot(false, ["Runtime configuration", "ok"]), "1/5|neutral");
});

test("engine cell on the first frame (no status yet, request about to start) reads checking, not unavailable", () => {
  // App passes engineChecking = checking || (status === null && statusError === null).
  assert.equal(cellMap({ ...baseInputs, engine: null, engineChecking: true }).Engine, "checking|neutral");
});

test("live summary: progress, problems by name, final result and the sign-in stop", () => {
  const rows = (...states: BootStepState[]) => states.map((state, i) => ({ id: `s${i}`, label: `Step ${i + 1}`, state, detail: state === "blocked" ? "Sign-in required" : "" }));
  const snap = (phase: BootSnapshot["phase"], ...states: BootStepState[]): BootSnapshot => ({
    rows: rows(...states),
    phase,
    finished: states.filter((s) => !["pending", "running", "not-run"].includes(s)).length,
    total: states.length,
    animate: false,
    dismissed: false,
  });
  assert.equal(bootSummary(snap("running", "ok", "running", "pending")), "1/3 checks finished");
  assert.equal(bootSummary(snap("running", "ok", "timed-out", "running")), "2/3 checks finished · needs attention: Step 2 timed out");
  assert.equal(bootSummary(snap("complete", "ok", "ok", "ok")), "Start-up checks finished 3/3 · no problems reported");
  assert.equal(bootSummary(snap("done", "limited", "ok", "unavailable")), "Start-up checks finished 3/3 · needs attention: Step 1 limited, Step 3 unavailable");
  assert.equal(bootSummary(snap("stopped", "ok", "blocked", "not-run")), "Start-up stopped at Step 2: Sign-in required");
});

test("rows start without a detail so the state word is not repeated ('Waiting Waiting')", () => {
  const c = createBootController({ steps: [step("a", ok())] });
  assert.equal(c.getSnapshot().rows[0].state, "pending");
  assert.equal(c.getSnapshot().rows[0].detail, "");
});

test("final result survives the overlay unmount (reduced motion / skip flag): spoken once, by the persistent announcer", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const c = createBootController({ steps: [step("a", ok()), step("b", async () => ({ state: "limited", detail: "x" }))], reducedMotion: true });
  assert.equal(bootCountLive(c.getSnapshot().phase), "polite", "progress is live in the overlay while running");
  assert.equal(bootAnnouncement(c.getSnapshot(), true), "");
  void c.start();
  await flush();
  const complete = c.getSnapshot();
  assert.equal(complete.phase, "complete");
  assert.equal(bootCountLive(complete.phase), "off", "the overlay does not try to speak the final result 300 ms before it unmounts");
  assert.equal(bootAnnouncement(complete, true), "", "nothing from the announcer while the overlay (aria-modal) is still open");
  t.mock.timers.tick(300);
  const done = c.getSnapshot();
  assert.equal(done.phase, "done");
  // With reduced motion or the skip flag, BootSequence unmounts the overlay at "done" (open = false).
  assert.equal(bootAnnouncement(done, false), "Start-up checks finished 2/2 · needs attention: b limited");
});

test("a sign-in stop is spoken by the overlay (it stays open), never repeated by the announcer", () => {
  const stopped: BootSnapshot = {
    rows: [{ id: "access", label: "Access", state: "blocked", detail: "Sign-in required" }],
    phase: "stopped",
    finished: 1,
    total: 1,
    animate: false,
    dismissed: false,
  };
  assert.equal(bootCountLive("stopped"), "polite");
  assert.equal(bootAnnouncement(stopped, false), "", "after Esc the shell's role=alert sign-in banner takes over");
});