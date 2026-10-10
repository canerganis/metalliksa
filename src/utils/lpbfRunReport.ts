import type { createLpbfQualificationReport } from "./lpbfQualificationReport";
import type { PythonLpbfBuildJobResult } from "../services/pythonComputationService";
import { canonicalLpbfMaterialName } from "./lpbfMaterialIdentity";
import { MACHINE_BAND_SENTENCE, MACHINE_OFFSET_SENTENCE, MACHINE_PRIVACY_SENTENCE, MACHINE_SECTION_TITLE, MACHINE_VERDICT_SENTENCE, machineReportLines, type MachineCalibrationReportInput } from "../data/lpbfMachineCalibration";
import { resolveDepthBiasWarning } from "./depthBiasWarning";
import type { SimulationResult } from "../services/lpbfSimulationService";

/** The research qualification dossier this export is built on. */
export type LpbfQualificationReport = ReturnType<typeof createLpbfQualificationReport>;

export interface LpbfRunReportExtras {
  /**
   * The same build job (or null) that was passed to createLpbfQualificationReport. The visible verdict and assumptions are
   * taken from report.buildScreening so they always match the hashed dossier; this job only supplies identity fields
   * (solver revision, build-job identity, material property revision) that the dossier summary does not carry.
   */
  buildJob: PythonLpbfBuildJobResult | null;
  /**
   * Optional machine calibration (user data) result shown next to the screening value. Display only: it is not part of the
   * hashed dossier, never changes the verdict, and the block is omitted when null or undefined.
   */
  machineCalibration?: MachineCalibrationReportInput | null;
}
export interface LpbfRunReportOptions {
  /** ISO timestamp supplied by the caller; the builder never reads the clock. */
  createdAt: string;
  /** SHA-256 hex of the exact embedded dossier bytes (see serializeLpbfRunReportDossier), or null when not computed. */
  dossierSha256: string | null;
  /** Static demo only: the banner sentence (demoBannerText) placed in the header. Omitted in normal reports. */
  staticDemoLine?: string | null;
}

const NOT_RECORDED = "Not recorded";

/** Escapes text for HTML element and attribute content. */
export function escapeHtml(value: unknown): string {
  return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

/**
 * The exact bytes embedded in the inert data block. Every "<" is written as the JSON escape <, so neither
 * "</script>" nor "<!--" can end or alter the block, and the text is still valid JSON. The digest printed in the
 * report is the SHA-256 of this string, as embedded.
 */
export function serializeLpbfRunReportDossier(report: LpbfQualificationReport, createdAt: string): string {
  return JSON.stringify({ ...report, createdAt }, null, 2).replace(/</g, "\\u003c");
}

/** SHA-256 hex over the UTF-8 bytes of text via crypto.subtle, or null when the platform cannot compute it. */
export async function sha256Hex(text: string): Promise<string | null> {
  try {
    const subtle = globalThis.crypto?.subtle;
    if (!subtle) return null;
    const digest = await subtle.digest("SHA-256", new TextEncoder().encode(text));
    return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
  } catch {
    return null;
  }
}

/** File name from the sanitized build id, else from the calendar date of `date`. */
export function runReportFileName(buildId: string, date: string | Date = new Date()): string {
  const slug = buildId.trim().replace(/[^A-Za-z0-9._-]+/g, "-").replace(/\.{2,}/g, ".").replace(/^[-.]+|[-.]+$/g, "").slice(0, 64).replace(/[-.]+$/g, "");
  const parsed = typeof date === "string" ? new Date(date) : date;
  const day = Number.isNaN(parsed.getTime()) ? "undated" : parsed.toISOString().slice(0, 10);
  return `metalliksa-lpbf-run-report-${slug || day}.html`;
}

const text = (value: unknown): string => {
  if (value === null || value === undefined) return NOT_RECORDED;
  const shown = typeof value === "string" ? value : String(value);
  return shown.trim() ? shown : NOT_RECORDED;
};
const unavailable = (value: unknown, reason: string): string => {
  if (value === null || value === undefined || (typeof value === "string" && !value.trim())) return `Not available - ${reason}`;
  return String(value);
};
const num = (value: number | null | undefined, reason = "not reported"): string => typeof value === "number" && Number.isFinite(value) ? String(value) : `Not available - ${reason}`;
const cell = (value: unknown) => `<td>${escapeHtml(value)}</td>`;
const row = (label: string, value: unknown, extraClass = "") => `<div class="row${extraClass ? ` ${extraClass}` : ""}"><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`;
const list = (items: readonly unknown[], ordered = false) => items.length ? `<${ordered ? "ol" : "ul"}>${items.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</${ordered ? "ol" : "ul"}>` : `<p class="muted">${NOT_RECORDED}</p>`;
const section = (id: string, title: string, body: string) => `<section id="${id}" aria-labelledby="${id}-h"><h2 id="${id}-h">${escapeHtml(title)}</h2>${body}</section>`;

const STYLE = `
:root{color-scheme:light dark;--bg:#fff;--fg:#14202b;--muted:#51606e;--line:#c4ccd4;--warn-bg:#fff4d6;--warn-fg:#5c3d00;--bad-bg:#fde4e1;--bad-fg:#7a1a10}
@media (prefers-color-scheme:dark){:root{--bg:#10171e;--fg:#e4eaf0;--muted:#a3b0bd;--line:#33414f;--warn-bg:#3b2f0a;--warn-fg:#ffe29a;--bad-bg:#4a1a14;--bad-fg:#ffc9c2}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:960px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:1.6rem;margin:.2rem 0 .6rem}
h2{font-size:1.15rem;margin:0 0 .6rem;padding-bottom:.3rem;border-bottom:1px solid var(--line)}
section{margin:1.6rem 0;break-inside:avoid-page}
.banner{border:1px solid var(--line);background:var(--warn-bg);color:var(--warn-fg);padding:.7rem .9rem;border-radius:6px}
.evidence-label{font-weight:700}
.badge{display:inline-block;padding:.05rem .5rem;border-radius:999px;font-size:.8rem;font-weight:700;background:var(--bad-bg);color:var(--bad-fg);border:1px solid var(--bad-fg)}
dl{margin:0}
.row{display:grid;grid-template-columns:minmax(10rem,14rem) 1fr;gap:.6rem;padding:.25rem 0;border-bottom:1px dotted var(--line)}
dt{color:var(--muted)}
dd{margin:0;overflow-wrap:anywhere;white-space:pre-wrap}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{border:1px solid var(--line);padding:.3rem .5rem;text-align:left;vertical-align:top;overflow-wrap:anywhere}
th{background:rgba(127,127,127,.12)}
.muted{color:var(--muted)}
.draft{border-left:4px solid var(--warn-fg);padding-left:.7rem}
pre{white-space:pre-wrap;overflow-wrap:anywhere;border:1px solid var(--line);padding:.5rem;border-radius:4px;font-size:.85rem}
code{overflow-wrap:anywhere}
@media (max-width:600px){.row{grid-template-columns:1fr;gap:0}}
@media print{
@page{margin:14mm}
:root{color-scheme:light;--bg:#fff;--fg:#000;--muted:#333;--line:#888;--warn-bg:#fff;--warn-fg:#000;--bad-bg:#fff;--bad-fg:#000}
body{font-size:11pt}
main{max-width:none;padding:0}
section,tr,.row{break-inside:avoid}
h2{break-after:avoid}
.banner{border:2px solid #000}
}`;

type Job = NonNullable<LpbfQualificationReport["job"]>;

/** Pure, deterministic HTML for one LPBF workflow run. Same report, extras and options give identical bytes. */
export function buildLpbfRunReportHtml(report: LpbfQualificationReport, extras: LpbfRunReportExtras, options: LpbfRunReportOptions): string {
  const job = report.job as Job | null;
  const result: SimulationResult | undefined = job?.result;
  const buildJob = extras.buildJob;
  const screening = report.buildScreening;
  const stale = report.resultMatchesCurrentInputs === false;
  const verdict = screening?.verdict;
  const executed = (report.executedInput ?? null) as unknown as Record<string, unknown> | null;
  const current = report.currentProcess as unknown as Record<string, unknown>;
  const noScreening = "no build-job screening for the current inputs";
  const noResult = "no completed thermal simulation is attached";

  const header = `<header><p class="muted">Metalliksa · ${escapeHtml(report.scope)} · schema version ${escapeHtml(report.schemaVersion)}</p><h1>LPBF run report</h1><p class="muted">${escapeHtml(report.reportType)} · created ${escapeHtml(options.createdAt)}</p>${options.staticDemoLine ? `<p class="banner" role="note">${escapeHtml(options.staticDemoLine)}</p>` : ""}`
    + `<p class="banner" role="note">Evidence label: <span class="evidence-label">${escapeHtml(report.resultType)}</span> · Qualification status: <span class="qualification-status">${escapeHtml(report.qualificationStatus)}</span> · not experimental validation, not a production release or standards certificate.</p>`
    + `<p>${escapeHtml(report.resultDescription)}${stale ? ` <span class="badge">Stale</span>` : ""}</p></header>`;

  const ctx = report.buildContext;
  const composition = Object.entries(report.specimen.composition ?? {}).map(([element, value]) => `${element} ${value}`).join(" · ");
  const context = section("context", "Context", `<dl>${[
    row("Build / experiment ID", text(ctx.buildId)), row("Machine model", text(ctx.machine)), row("Powder lot", text(ctx.powderLot)),
    row("Powder condition", text(ctx.powderCondition)), row("Heat treatment", text(ctx.heatTreatment)), row("Measurement method", text(ctx.measurementMethod)),
    row("Research objective and notes", text(ctx.notes)), row("Specimen", `${text(report.specimen.name)} (${text(report.specimen.id)})`),
    row("Composition", composition ? `${composition} ${report.specimen.compositionUnit === "wt_pct" ? "wt%" : report.specimen.compositionUnit === "at_pct" ? "at%" : text(report.specimen.compositionUnit)}` : NOT_RECORDED),
    row("Simulation job", job ? `${job.id} (${job.status})` : "No simulation job submitted"),
  ].join("")}</dl>`);

  const pairs: [string, string, string][] = [
    ["Laser power (W)", "laserPower_W", "power_W"], ["Scan speed (mm/s)", "scanSpeed_mms", "speed_mm_s"], ["Beam diameter (um)", "beamDiameter_um", "beamDiameter_um"],
    ["Preheat (degC)", "preheatTemp_C", "preheat_C"], ["Layer thickness (um)", "layer_um", "layer_um"], ["Hatch spacing (um)", "hatch_um", "hatch_um"],
  ];
  const shown = (value: unknown) => value === undefined || value === null ? NOT_RECORDED : String(value);
  const inputRows = pairs.map(([label, cur, exe]) => {
    const executedValue = executed ? executed[exe] : undefined;
    const differs = executed !== null && executedValue !== undefined && executedValue !== current[cur];
    return `<tr><th scope="row">${escapeHtml(label)}</th>${cell(shown(current[cur]))}${cell(shown(executedValue))}${cell(executed === null ? "No executed input" : differs ? "Differs" : "Same")}</tr>`;
  });
  inputRows.push(`<tr><th scope="row">Material</th>${cell(shown(canonicalLpbfMaterialName(report.specimen.name)))}${cell(shown(executed?.material))}${cell(executed === null ? "No executed input" : executed.material === canonicalLpbfMaterialName(report.specimen.name) ? "Same" : "Differs")}</tr>`);
  const known = new Set(["material", "properties", "measurements", ...pairs.map(pair => pair[2])]);
  const otherExecuted = executed ? Object.entries(executed).filter(([key, value]) => !known.has(key) && (typeof value === "string" || typeof value === "number" || typeof value === "boolean")) : [];
  const inputs = section("inputs", "Current and executed inputs", `${stale ? `<p><span class="badge">Stale</span> Current inputs or settings differ from the executed simulation. Current and executed values are shown side by side; staleness can also come from solver settings or scan strategy not listed here.</p>` : ""}`
    + `<table><thead><tr><th scope="col">Parameter</th><th scope="col">Current</th><th scope="col">Executed</th><th scope="col">Comparison</th></tr></thead><tbody>${inputRows.join("")}</tbody></table>`
    + `<p>Current scan strategy: ${escapeHtml(shown(report.currentProcess.scanStrategy))}</p>`
    + (otherExecuted.length ? `<h3>Other executed settings</h3><dl>${otherExecuted.map(([key, value]) => row(key, value)).join("")}</dl>` : ""));

  const prov = result?.provenance;
  const solverWhy = result ? "the result carries no provenance record" : noResult;
  const identity = section("identity", "Implementation fingerprint and identity", `<dl>${[
    row("Solver", result ? `${result.solver.id} (version ${result.solver.version})` : `Not available - ${noResult}`),
    row("Requested mode", result ? result.requestedMode : `Not available - ${noResult}`), row("Effective mode", result ? result.effectiveMode : `Not available - ${noResult}`),
    row("Fallback reason", result ? (result.fallbackReason ?? "None recorded") : `Not available - ${noResult}`),
    row("Implementation hash", unavailable(prov?.implementationHash, solverWhy)), row("Input hash", unavailable(prov?.inputHash, solverWhy)),
    row("Execution input hash", unavailable(prov?.executionInputHash, prov ? "not reported by the worker for this run" : solverWhy)),
    row("Implementation fingerprint schema", unavailable(prov?.implementationFingerprintSchema, prov ? "not reported by the worker for this run" : solverWhy)),
    row("Solver binary hash", unavailable(prov?.solverBinaryHash, prov ? "no solver binary was recorded for this backend" : solverWhy)),
    row("Build-job model", unavailable(screening?.modelId, noScreening)),
    row("Build-job solver revision", unavailable(buildJob?.solverRevision, buildJob ? "not reported" : "no build-job screening for the current inputs")),
    row("Build-job identity SHA-256", unavailable(buildJob?.buildJobIdentity?.sha256, buildJob ? "not reported" : "no build-job screening for the current inputs")),
    row("Material property revision", unavailable(buildJob?.materialPropertyRevision, buildJob ? "not reported" : "no build-job screening for the current inputs")),
    row("Material property SHA-256", unavailable(buildJob?.materialPropertySha256, buildJob ? "not reported" : "no build-job screening for the current inputs")),
  ].join("")}</dl>`);

  const energy = report.verification.conservation;
  const results = section("results", "Results", !result
    ? `<p>No completed thermal simulation is attached, so no melt pool dimensions are reported.</p>`
    : `${stale ? `<p><span class="badge">Stale</span> Executed job shown; current inputs differ.</p>` : ""}<table><thead><tr><th scope="col">Quantity</th><th scope="col">Value (um)</th></tr></thead><tbody>`
      + `<tr><th scope="row">Width (W)</th>${cell(num(result.metrics.width_um))}</tr><tr><th scope="row">Depth (D)</th>${cell(num(result.metrics.depth_um))}</tr><tr><th scope="row">Length (L)</th>${cell(num(result.metrics.length_um))}</tr></tbody></table>`
      + `<dl>${[
        row("Energy conservation check", energy ? `Present (relative error ${energy.relativeError})` : "Not available - not reported for this run"),
        row("Numerical convergence study", report.verification.numericalConvergence ? "Present" : "Not available - not reported for this run"),
        row("Experimental validation", report.verification.experimentalValidation),
      ].join("")}</dl>`);

  let verdictBody: string;
  if (!screening || !verdict) verdictBody = `<p>No build-job screening for the current inputs.</p>`;
  else {
    const gates = verdict.gates ?? [];
    const idList = (label: string, ids?: string[]) => row(label, ids && ids.length ? ids.join(", ") : "None");
    verdictBody = `${stale ? `<p><span class="badge">Stale</span> This screening describes the current inputs, not the executed run.</p>` : ""}<p class="muted">The extent status describes the build-job melt-pool geometry model, not the transient thermal W/D/L above.</p><p><strong>${escapeHtml(verdict.headline)}</strong></p><dl>${[
      row("Screening verdict", verdict.verdict), row("Verdict reason", text(verdict.verdictReason)),
      row("Build-job melt-pool extent status", unavailable(verdict.extentStatus, "not reported")), row("Build-job extent note", text(verdict.extentNote)),
      idList("Blocking gates", verdict.blockingGates), idList("Risk gates", verdict.riskGates), idList("Advisory gates", verdict.advisoryGates), idList("Unavailable gates", verdict.unavailableGates),
    ].join("")}</dl><h3>Reasons (in reported order)</h3>${list(verdict.reasons, true)}`
      + `<h3>Gates</h3>${gates.length ? `<table><thead><tr><th scope="col">Gate</th><th scope="col">Status</th><th scope="col">Measured</th><th scope="col">Required</th><th scope="col">Unit</th><th scope="col">Note</th></tr></thead><tbody>${gates.map(gate => `<tr>${cell(gate.id)}${cell(gate.status)}${cell(num(gate.measured, gate.reason || "gate unavailable"))}${cell(num(gate.required, "no threshold"))}${cell(text(gate.unit))}${cell(gate.reason ? `${gate.reason} ${gate.note}`.trim() : gate.note)}</tr>`).join("")}</tbody></table>` : `<p class="muted">${NOT_RECORDED}</p>`}`
      + `<h3>Advisories</h3>${list(verdict.advisories ?? [])}`
      + (verdict.ballingScreened === false ? `<p>The balling screen did not run; this verdict is not balling-cleared.</p>` : verdict.ballingScreened === true ? `<p>The balling screen ran (absorption model: ${escapeHtml(text(verdict.ballingAbsorptionModel))}).</p>` : "");
  }
  const verdictSection = section("build-job", "Build-job verdict", verdictBody);

  const draft = report.measurementDraft;
  const evidenceRows = result?.measurementEvidence ?? [];
  const measurements = section("measurements", "Measurements", `<div class="draft"><h3>User draft (unverified)</h3><p class="muted">${escapeHtml(draft.status)}</p><dl>${[
    row("Measured width (um)", text(draft.width_um)), row("Measured depth (um)", text(draft.depth_um)), row("Uncertainty (um)", text(draft.uncertainty_um)),
    row("Source", text(draft.source)), row("Specimen or DOI", text(draft.specimenOrDoi)), row("Independent holdout (user-declared)", text(draft.holdout)),
  ].join("")}</dl>${draft.replicates.trim() ? `<pre>${escapeHtml(draft.replicates)}</pre>` : `<p class="muted">Replicates: ${NOT_RECORDED}</p>`}</div>`
    + `<h3>Worker-reported evidence</h3>${evidenceRows.length ? `<table><thead><tr><th scope="col">Source</th><th scope="col">Same process vector</th><th scope="col">Uncertainty (um)</th><th scope="col">Independent holdout</th></tr></thead><tbody>${evidenceRows.map(item => `<tr>${cell(text(item.source))}${cell(text(item.sameProcessVector))}${cell(item.uncertainty_um === undefined || item.uncertainty_um === null ? NOT_RECORDED : typeof item.uncertainty_um === "object" ? JSON.stringify(item.uncertainty_um) : item.uncertainty_um)}${cell(item.independentHoldout === null ? "Unknown" : item.independentHoldout ? "Declared independent" : "Calibration data")}</tr>`).join("")}</tbody></table>` : `<p>No worker-reported measurement evidence is attached.</p>`}`);

  const research = report.researchEvidence;
  const sources = section("sources", "Sources", `<h3>Build-job assumptions (verbatim)</h3>${screening ? list(screening.assumptions) : `<p class="muted">Not available - no build-job screening for the current inputs.</p>`}`
    + `<h3>Thermal simulation assumptions (verbatim)</h3>${result ? list(result.assumptions) : `<p class="muted">Not available - ${noResult}.</p>`}`
    + `<h3>Material</h3><dl>${[
      row("Thermal material source", result ? `${result.material.name}: ${result.material.source} (quality: ${result.material.quality})` : `Not available - ${noResult}`),
      row("Material property revision", unavailable(buildJob?.materialPropertyRevision, buildJob ? "not reported" : "no build-job screening for the current inputs")),
      row("Material property SHA-256", unavailable(buildJob?.materialPropertySha256, buildJob ? "not reported" : "no build-job screening for the current inputs")),
    ].join("")}</dl><h3>Research evidence</h3>${research.length ? `<ul>${research.map(item => `<li><code>${escapeHtml(JSON.stringify(item))}</code></li>`).join("")}</ul>` : `<p>No linked research evidence records.</p>`}`);

  const thermalGeometry = buildJob?.thermal?.meltPoolGeometry;
  const depthBias = thermalGeometry ? resolveDepthBiasWarning(thermalGeometry, buildJob?.thermal?.material) : null;
  const depthBiasSection = !thermalGeometry || !depthBias ? "" : section("depth-bias", "Melt-pool depth bias note",
    `<p class="muted">Reporting text only: no label, verdict or gate reads it. Screening regime label: ${escapeHtml(thermalGeometry.regime)}.</p>`
    + (thermalGeometry.regimeMaterialNote ? `<p>Alloy note: ${escapeHtml(thermalGeometry.regimeMaterialNote)}.</p>` : "")
    + (depthBias.text ? `<p>${escapeHtml(depthBias.text)}</p><p class="muted">Basis: ${escapeHtml(depthBias.basis ?? "")}</p>` : `<p>No depth bias note applies to this regime and alloy.</p>`));

  const bands = report.publishedTrackBands;
  const bandsSection = !bands ? "" : section("error-bands", "Published-track error bands",
    `<p class="muted">${escapeHtml(bands.statement)} Reporting text only: no label, verdict or gate reads these bands. Kernel ${escapeHtml(bands.kernel)}, alloy ${escapeHtml(bands.material)}, screening regime class ${escapeHtml(bands.regime)} (default absorptivity).</p>`
    + bands.entries.map(entry => `<h3>${escapeHtml(entry.quantity === "depth" ? "Depth" : "Width")} (${escapeHtml(entry.state)})</h3><p>${escapeHtml(entry.sentence)}</p>`
      + `<dl>${row("Cell", entry.cell ?? "No published cell for this kernel, alloy and regime class")}</dl>`
      + (entry.sources.length ? `<table><thead><tr><th scope="col">Source</th><th scope="col">Source id</th><th scope="col">DOI</th><th scope="col">Rows</th></tr></thead><tbody>${entry.sources.map(src => `<tr>${cell(src.name)}${cell(src.id)}${cell(text(src.doi))}${cell(src.rows)}</tr>`).join("")}</tbody></table>` : `<p class="muted">No sources: ${NOT_RECORDED}</p>`)).join("")
    + `<dl>${[row("Band artefact id", bands.bandsId), row("Band artefact SHA-256", bands.contentSha256), row("Band implementation hash", bands.implementationHash)].join("")}</dl>`);

  const mc = extras.machineCalibration ?? null;
  const machineSection = !mc ? "" : section("machine-calibration", MACHINE_SECTION_TITLE,
    `<p class="muted">${escapeHtml(MACHINE_OFFSET_SENTENCE)} ${escapeHtml(MACHINE_VERDICT_SENTENCE)}</p>`
    + `<dl>${machineReportLines(mc).map(([label, value]) => row(label, value)).join("")}</dl>`
    + (mc.block.available ? `<p class="muted">${escapeHtml(MACHINE_BAND_SENTENCE)}</p>` : "")
    + `<p class="muted">${escapeHtml(MACHINE_PRIVACY_SENTENCE)}</p>`);

  const limitations = section("limitations", "Limitations", list(report.limitations));
  const reproduce = section("reproduce", "Reproduce", `<ol><li>Open the Metalliksa LPBF Engineering workspace and enter the context fields exactly as printed above.</li>`
    + `<li>Set the process vector to the executed values, not the current values, and select the requested mode and the solver backend recorded above.</li>`
    + `<li>Run the thermal simulation and compare its implementation hash, input hash and execution input hash with the fingerprint section.</li>`
    + `<li>Run the build-job screening on the same inputs and compare the build-job identity SHA-256.</li>`
    + `<li>Verify this file: compute the SHA-256 of the text inside the data block with id <code>dossier-data</code> and compare it with the digest below.</li></ol>`
    + `<dl>${row("Dossier JSON SHA-256", options.dossierSha256 ?? "not computed")}</dl>`);

  const data = `<script type="application/json" id="dossier-data">${serializeLpbfRunReportDossier(report, options.createdAt)}</script>`;
  return `<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">`
    + `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:"><meta name="referrer" content="no-referrer">`
    + `<title>${escapeHtml(`LPBF run report ${text(ctx.buildId)}`)}</title><style>${STYLE}</style></head><body><main>${header}${context}${inputs}${identity}${results}${verdictSection}${measurements}${depthBiasSection}${bandsSection}${machineSection}${sources}${limitations}${reproduce}${data}</main></body></html>\n`;
}
