import React from "react";
import { FileSearch, ShieldAlert } from "lucide-react";
import {
  statusCounts,
  type GateStatus,
  type LpbfCalibrationScorecardDocument,
  type ScorecardConfusion,
  type ScorecardHeadlineRow,
  type ScorecardN01,
} from "../data/lpbfCalibrationScorecard";
import { summarizeScorecard, SUMMARY_LEGEND, SUMMARY_METRIC_DEFINITION } from "../data/lpbfCalibrationScorecardSummary";
import { COMMITTED_CALIBRATION_SCORECARD } from "../data/lpbfCalibrationScorecardRecord";
import { LpbfLeaderboardPanel } from "./LpbfLeaderboardPanel";
import { LpbfKeyholeBenchmarkPanel } from "./LpbfKeyholeBenchmarkPanel";
import { IS_STATIC_DEMO } from "../demo/flag.ts";
import { DemoFingerprintGate } from "../demo/demoFingerprint.tsx";

// Read-only view of the Python-generated record docs/LPBF_CALIBRATION_SCORECARD_<date>.view.json.
// Every number below is read from that JSON: no physics and no statistics are computed here.
// Screening only, not validation. Held-out errors are for nuisance parameters fitted OUTSIDE the frozen kernels.

type SlotProps = { children: React.ReactNode; className?: string };
const Card = ({ children, className = "" }: SlotProps) => <section className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>{children}</section>;
const CardHeader = ({ children, className = "" }: SlotProps) => <header className={`border-b border-slate-100 bg-slate-50 p-4 ${className}`}>{children}</header>;
const CardContent = ({ children, className = "" }: SlotProps) => <div className={`p-4 ${className}`}>{children}</div>;
const CardTitle = ({ children, className = "" }: SlotProps) => <h3 className={`font-semibold text-slate-800 ${className}`}>{children}</h3>;

export const KERNEL_LABELS: Readonly<Record<string, string>> = {
  rosenthal: "Rosenthal",
  "eagar-tsai": "Eagar–Tsai v2",
  goldak: "Goldak v3",
};

// Dark text on light chips (>= 4.5:1); the status word is always printed, colour is never the only signal.
export const STATUS_CHIP: Readonly<Record<GateStatus, string>> = {
  enabled: "bg-emerald-100 text-emerald-900 border-emerald-300",
  "within-source-only": "bg-amber-100 text-amber-900 border-amber-300",
  rejected: "bg-rose-100 text-rose-900 border-rose-300",
  "no-data": "bg-slate-100 text-slate-700 border-slate-300",
};

export function fmt1(value: number | null | undefined): string {
  if (value === null || value === undefined) return "n/a";
  const text = value.toFixed(1);
  return text === "-0.0" ? "0.0" : text;
}

export function fmt2(value: number | null | undefined): string {
  if (value === null || value === undefined) return "n/a";
  const text = value.toFixed(2);
  return text === "-0.00" ? "0.00" : text;
}

function ci(interval: readonly [number, number] | null | undefined, digits = 2): string {
  return interval ? ` [${interval[0].toFixed(digits)}, ${interval[1].toFixed(digits)}]` : "";
}

export function doiHref(doi: string): string {
  return /^https?:\/\//.test(doi) ? doi : `https://doi.org/${doi}`;
}

export function StatusChip({ status }: { status: GateStatus }) {
  return <span data-status={status} className={`inline-block rounded border px-2 py-0.5 text-xs font-semibold ${STATUS_CHIP[status]}`}>{status}</span>;
}

export function NoScorecardRecord() {
  return (
    <div role="status" data-testid="no-scorecard-record" className="m-4 rounded-xl border border-slate-300 bg-white p-6 text-sm text-slate-700">
      <div className="mb-2 flex items-center gap-2 font-semibold text-slate-800"><FileSearch className="h-4 w-4" aria-hidden="true" />No calibration scorecard record committed yet</div>
      <p>Run <code>npm run lpbf:calibration</code> to generate <code>docs/LPBF_CALIBRATION_SCORECARD_&lt;date&gt;.view.json</code>. Until then this page has nothing to show and no calibrated mode is offered anywhere. Every melt-pool result stays screening only.</p>
    </div>
  );
}

function HeadlineTable({ rows }: { rows: readonly ScorecardHeadlineRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table data-testid="headline-table" className="w-full text-left text-xs">
        <caption className="mb-2 text-left text-slate-600">Equal-source-weight MAPE across held-out sources (both directions), default to served rung, and the gate status. A rung is chosen inside the training sources only; unresolved rows count against it.</caption>
        <thead><tr className="border-b border-slate-200 text-slate-600">
          <th scope="col" className="p-2">Kernel</th><th scope="col" className="p-2">Alloy</th><th scope="col" className="p-2">Quantity</th>
          <th scope="col" className="p-2">Gate status</th><th scope="col" className="p-2">MAPE default to served, %</th><th scope="col" className="p-2">Why</th>
        </tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.kernel}/${r.material}/${r.quantity}`} data-cell={`${r.kernel}/${r.material}/${r.quantity}`} className="border-b border-slate-100 align-top">
              <td className="p-2">{KERNEL_LABELS[r.kernel] ?? r.kernel}</td>
              <td className="p-2">{r.material}</td>
              <td className="p-2">{r.quantity}</td>
              <td className="p-2"><StatusChip status={r.status} /></td>
              <td className="p-2">{r.headline ? `${fmt1(r.headline.equalSourceWeight.mapeDefault)} to ${fmt1(r.headline.equalSourceWeight.mapeServed)}` : "n/a"}</td>
              <td className="p-2 text-slate-700">{r.reasons.length ? r.reasons.join("; ") : "all gate checks passed"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function P2Table({ rows }: { rows: readonly ScorecardHeadlineRow[] }) {
  const lines = rows.flatMap((r) => r.p2.map((p) => ({ r, p })));
  if (lines.length === 0) return <p className="text-sm text-slate-600">No leave-one-source-out result: every alloy with a second trainable source is listed above; single-source alloys are scored within the source only.</p>;
  return (
    <div className="overflow-x-auto">
      <table data-testid="loso-table" className="w-full text-left text-xs">
        <caption className="mb-2 text-left text-slate-600">Leave-one-source-out, both directions. Unresolved rows are shown, not dropped; skill is the paired cluster-bootstrap CI95 over test parameter sets.</caption>
        <thead><tr className="border-b border-slate-200 text-slate-600">
          <th scope="col" className="p-2">Cell</th><th scope="col" className="p-2">Held out</th><th scope="col" className="p-2">Rung</th>
          <th scope="col" className="p-2">Rows / sets</th><th scope="col" className="p-2">Unresolved default / rung</th>
          <th scope="col" className="p-2">MAPE default to served, %</th><th scope="col" className="p-2">Skill CI95</th><th scope="col" className="p-2">Interval 90 % coverage (Wilson 95 %)</th>
        </tr></thead>
        <tbody>
          {lines.map(({ r, p }) => (
            <tr key={`${r.kernel}/${r.material}/${r.quantity}/${p.heldOut}`} className="border-b border-slate-100 align-top">
              <td className="p-2">{KERNEL_LABELS[r.kernel] ?? r.kernel} · {r.material} · {r.quantity}</td>
              <td className="p-2">{p.heldOut}{p.role === "test-only" ? <span data-role="test-only" className="ml-1 text-slate-600">(test-only{p.reading && p.reading !== "stated" ? `, spot ${p.reading} µm` : ""})</span> : null}</td>
              <td className="p-2">{p.rung}</td>
              <td className="p-2">{p.nRows} / {p.nSets}</td>
              <td className="p-2">{p.unresolvedDefault} / {p.unresolvedServed}</td>
              <td className="p-2">{fmt1(p.mapeDefault)} to {fmt1(p.mapeServed)}</td>
              <td className="p-2">{fmt2(p.skill)}{ci(p.skillCi95)}{p.verdictVsDefault ? ` (${p.verdictVsDefault})` : ""}</td>
              <td className="p-2">{p.coverage90 ? `${fmt2(p.coverage90.coverage)}${ci(p.coverage90.wilson95)} n=${p.coverage90.n}` : "n/a"}{p.intervalNotInformative90 ? " (not informative: interval wider than x2.5)" : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ConfusionMatrix({ title, conf }: { title: string; conf: ScorecardConfusion }) {
  return (
    <div data-testid="confusion-matrix" className="mb-4">
      <h3 className="mb-1 text-sm font-semibold text-slate-800">{title}</h3>
      <p className="mb-1 text-xs text-slate-600">n = {conf.n}; accuracy {fmt2(conf.accuracy)}; keyhole precision {fmt2(conf.keyholeOnly.precision)}, recall {fmt2(conf.keyholeOnly.recall)}</p>
      <table className="text-left text-xs">
        <thead><tr className="border-b border-slate-200 text-slate-600">
          <th scope="col" className="p-2">published \ screening</th>
          {conf.labels.map((l) => <th key={l} scope="col" className="p-2">{l}</th>)}
        </tr></thead>
        <tbody>
          {conf.labels.map((p) => (
            <tr key={p} className="border-b border-slate-100">
              <th scope="row" className="p-2 font-medium">{p}</th>
              {conf.labels.map((c) => <td key={c} className="p-2 tabular-nums">{conf.matrix[p]?.[c] ?? 0}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function isConfusion(value: unknown): value is ScorecardConfusion {
  return typeof value === "object" && value !== null && Array.isArray((value as ScorecardConfusion).labels) && "matrix" in value;
}

interface GeometryKeyholeRung { readonly n: number; readonly tp: number; readonly fp: number; readonly fn: number; readonly tn: number; readonly precision: number | null; readonly recall: number | null }

function geometryRows(doc: LpbfCalibrationScorecardDocument): { key: string; alloy: string; kernel: string; rung: string; v: GeometryKeyholeRung }[] {
  const out: { key: string; alloy: string; kernel: string; rung: string; v: GeometryKeyholeRung }[] = [];
  for (const [alloy, blk] of Object.entries(doc.regimeConfusion.byAlloy)) {
    const per = (blk as { perKernelSensitivity?: Record<string, { geometryKeyholeDoverW?: { rung?: Record<string, GeometryKeyholeRung | null> } }> }).perKernelSensitivity ?? {};
    for (const [kernel, kk] of Object.entries(per)) {
      for (const [rung, v] of Object.entries(kk.geometryKeyholeDoverW?.rung ?? {})) {
        if (v) out.push({ key: `${alloy}/${kernel}/${rung}`, alloy, kernel, rung, v });
      }
    }
  }
  return out;
}

function GeometryKeyholeTable({ doc }: { doc: LpbfCalibrationScorecardDocument }) {
  const rows = geometryRows(doc);
  if (rows.length === 0) return null;
  return (
    <div className="overflow-x-auto">
      <table data-testid="geometry-keyhole-table" className="w-full text-left text-xs">
        <caption className="mb-2 text-left text-slate-600">Geometry-based keyhole call (predicted D/W &gt; 1 against measured D/W &gt; 1) on the KU Leuven rows held out of the fit. Each rung's own width and depth are used; measured depth is never combined with a calibrated width.</caption>
        <thead><tr className="border-b border-slate-200 text-slate-600">
          <th scope="col" className="p-2">Alloy</th><th scope="col" className="p-2">Kernel</th><th scope="col" className="p-2">Rung</th>
          <th scope="col" className="p-2">n</th><th scope="col" className="p-2">tp / fp / fn / tn</th><th scope="col" className="p-2">Precision</th><th scope="col" className="p-2">Recall</th>
        </tr></thead>
        <tbody>
          {rows.map(({ key, alloy, kernel, rung, v }) => (
            <tr key={key} className="border-b border-slate-100">
              <td className="p-2">{alloy}</td><td className="p-2">{KERNEL_LABELS[kernel] ?? kernel}</td><td className="p-2">{rung}</td>
              <td className="p-2">{v.n}</td><td className="p-2">{v.tp} / {v.fp} / {v.fn} / {v.tn}</td>
              <td className="p-2">{fmt2(v.precision)}</td><td className="p-2">{fmt2(v.recall)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ConfusionSection({ doc }: { doc: LpbfCalibrationScorecardDocument }) {
  const blocks: React.ReactNode[] = [];
  for (const [alloy, blk] of Object.entries(doc.regimeConfusion.byAlloy)) {
    for (const [key, value] of Object.entries(blk)) {
      if (!key.startsWith("beam")) continue;
      const at = (value as { atDefaultEta?: unknown }).atDefaultEta;
      if (isConfusion(at)) blocks.push(<ConfusionMatrix key={`${alloy}/${key}`} title={`${alloy}, KU beam reading ${key.slice(4)} µm: screening class at the default absorptivity (the served label)`} conf={at} />);
    }
  }
  return (
    <div>
      <p className="mb-2 text-xs text-slate-600">{doc.regimeConfusion.labelSource}. Calibration does not change the served regime label.</p>
      {blocks.length ? blocks : <p className="text-sm text-slate-600">No labelled rows in the record.</p>}
      <GeometryKeyholeTable doc={doc} />
    </div>
  );
}

export function N01Card({ n01, note }: { n01: readonly ScorecardN01[]; note: string }) {
  return (
    <section data-testid="n01-card" role="region" aria-label="Guo N01 sentinel" className="rounded-xl border-2 border-rose-700 bg-rose-50 p-4 text-rose-950">
      <h2 className="mb-1 flex items-center gap-2 font-semibold"><ShieldAlert className="h-4 w-4" aria-hidden="true" />Guo N01: known failure, not fitted</h2>
      <p className="mb-2 text-xs">{note}</p>
      {n01.length === 0 ? <p className="text-sm">This record carries no N01 rows (a smoke run or an incomplete record); the sentinel must be present in every full record.</p> : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead><tr className="border-b border-rose-300">
              <th scope="col" className="p-2">Kernel</th><th scope="col" className="p-2">Rung</th><th scope="col" className="p-2">W pred / meas, µm</th>
              <th scope="col" className="p-2">D pred / meas, µm</th><th scope="col" className="p-2">D factor</th><th scope="col" className="p-2">Inside x0.5 to x2</th>
            </tr></thead>
            <tbody>
              {n01.flatMap((n) => Object.entries(n.rungs).map(([rung, v]) => (
                <tr key={`${n.kernel}/${rung}`} className="border-b border-rose-200">
                  <td className="p-2">{KERNEL_LABELS[n.kernel] ?? n.kernel}</td>
                  <td className="p-2">{rung}</td>
                  <td className="p-2">{fmt1(v.width_um)} / {n.measured.width_um}</td>
                  <td className="p-2">{fmt1(v.depth_um)} / {n.measured.depth_um}</td>
                  <td className="p-2">{fmt2(v.depthFactor)}</td>
                  <td className="p-2 font-semibold">{v.insideFactor2 ? "yes" : "NO"}</td>
                </tr>
              )))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function ParamsTable({ rows }: { rows: readonly ScorecardHeadlineRow[] }) {
  const withParams = rows.filter((r) => r.params);
  return (
    <div className="overflow-x-auto">
      <table data-testid="params-table" className="w-full text-left text-xs">
        <caption className="mb-2 text-left text-slate-600">Effective absorptivity fitted on all trainable sources of the alloy, with bootstrap CI90. These are nuisance parameters that absorb model error, not measured absorptivities.</caption>
        <thead><tr className="border-b border-slate-200 text-slate-600">
          <th scope="col" className="p-2">Cell</th><th scope="col" className="p-2">η_W</th><th scope="col" className="p-2">η_D</th><th scope="col" className="p-2">η joint</th>
          <th scope="col" className="p-2">c_D by class</th><th scope="col" className="p-2">Gate relevant</th>
          <th scope="col" className="p-2">Physics-compensation diagnostics</th>
        </tr></thead>
        <tbody>
          {withParams.map((r) => (
            <tr key={`${r.kernel}/${r.material}/${r.quantity}`} className="border-b border-slate-100 align-top">
              <td className="p-2">{KERNEL_LABELS[r.kernel] ?? r.kernel} · {r.material} · {r.quantity}</td>
              <td className="p-2">{fmt2(r.params?.etaW)}{ci(r.params?.etaW_ci90)}</td>
              <td className="p-2">{fmt2(r.params?.etaD)}{ci(r.params?.etaD_ci90)}</td>
              <td className="p-2">{fmt2(r.params?.etaJoint)}{ci(r.params?.etaJoint_ci90)}</td>
              <td className="p-2">{r.params?.cD ? Object.entries(r.params.cD).map(([k, v]) => `${k} ${v >= 0 ? "+" : ""}${v.toFixed(2)}`).join(", ") : "n/a"}</td>
              <td className="p-2">{r.gateRelevant ? "yes" : "no (default rung served)"}</td>
              <td className="p-2">
                <div data-testid="physics-diagnostics">
                  bound-hit {fmt2(r.diagnostics?.boundHitBootstrapFraction)} · |ln(η_D/η_W)| {fmt2(r.diagnostics?.etaSplitLn)} · max |c_D| {fmt2(r.diagnostics?.maxAbsCd)}
                  {r.diagnostics?.absorptanceMismatch?.length ? ` · absorptance mismatch: ${r.diagnostics.absorptanceMismatch.map((m) => m.class).join(", ")}` : ""}
                </div>
                {r.flags.length ? r.flags.join(", ") : "no flags"}{r.flagNotes.length ? <div className="text-slate-600">{r.flagNotes.join(" ")}</div> : null}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// The app routes on the URL hash (an unknown hash opens LPBF), so the jump scrolls and focuses instead of navigating.
function VersionCard({ doc }: { doc: LpbfCalibrationScorecardDocument }) {
  if (!doc.calibrationVersion) return null;
  const rows = doc.v1Comparison ?? [];
  return (
    <Card>
      <CardHeader><CardTitle>Calibration {doc.calibrationVersion}: what changed against v1</CardTitle></CardHeader>
      <CardContent>
        <p data-testid="version-note" className="mb-2 text-xs text-slate-700">
          Pre-registered in <code>{doc.preRegistration?.doc}</code> before the run. Supersedes <code>{doc.supersedes?.record ?? "v1"}</code>, which stays committed and unchanged. {doc.supersedes?.note}
          {doc.reproducesV1TrainableOnly === true ? " Re-running the v1 protocol inside v2 reproduces every v1 status." : ""}
        </p>
        <div className="overflow-x-auto">
          <table data-testid="version-table" className="w-full text-left text-xs">
            <caption className="mb-2 text-left text-slate-600">Gate status per cell: v1 record, the v1 protocol re-run inside v2, and v2 with the test-only held-out sources.</caption>
            <thead><tr className="border-b border-slate-200 text-slate-600">
              <th scope="col" className="p-2">Cell</th><th scope="col" className="p-2">v1</th><th scope="col" className="p-2">v2 trainable-only</th><th scope="col" className="p-2">v2</th>
            </tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.kernel}/${r.material}/${r.quantity}`} className="border-b border-slate-100">
                  <td className="p-2">{KERNEL_LABELS[r.kernel] ?? r.kernel} · {r.material} · {r.quantity}</td>
                  <td className="p-2">{r.v1 ? <StatusChip status={r.v1} /> : "n/a"}</td>
                  <td className="p-2"><StatusChip status={r.v2TrainableOnly} /></td>
                  <td className="p-2"><StatusChip status={r.v2} />{r.changed ? " changed" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function jumpToDetails() {
  const target = document.getElementById("detailed-tables");
  if (!target) return;
  target.scrollIntoView({ block: "start" });
  target.focus();
}

function PlainLanguageCard({ doc }: { doc: LpbfCalibrationScorecardDocument }) {
  const summary = summarizeScorecard(doc);
  return (
    <section data-testid="plain-summary" aria-labelledby="plain-summary-title" className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-100 bg-slate-50 p-4">
        <h2 id="plain-summary-title" className="font-semibold text-slate-800">In plain language</h2>
        {doc.quick ? <p className="mt-1 text-xs font-semibold text-amber-900">SMOKE RUN: not a record.</p> : null}
      </header>
      <div className="p-4 text-sm text-slate-800">
        <ul className="list-disc space-y-1 pl-5">
          {summary.items.map((it) => (
            <li key={it.id} data-summary-item={it.id}>
              {it.parts.map((p, i) => (p.number ? <strong key={i} data-source={p.number.source} title={`record field: ${p.number.source}`}>{p.t}</strong> : <React.Fragment key={i}>{p.t}</React.Fragment>))}.
            </li>
          ))}
        </ul>
        <p data-testid="summary-legend" className="mt-3 text-xs text-slate-700">Error words: {SUMMARY_LEGEND}.</p>
        <p className="mt-1 text-xs text-slate-600">Metric: {SUMMARY_METRIC_DEFINITION} Screening only, not validation.</p>
        <details className="mt-2 text-xs text-slate-700">
          <summary className="cursor-pointer font-medium">What this does not show</summary>
          <ul className="mt-1 list-disc space-y-1 pl-5">{summary.notes.map((n, i) => <li key={`note-${i}`}>{n}</li>)}</ul>
        </details>
        <p className="mt-3 text-xs"><button type="button" className="underline text-sky-800" onClick={jumpToDetails}>Jump to details</button></p>
      </div>
    </section>
  );
}

function ScorecardView({ document: doc = COMMITTED_CALIBRATION_SCORECARD }: { document?: LpbfCalibrationScorecardDocument | null } = {}) {
  if (!doc) {
    return (
      <div className="space-y-4">
        <header className="p-4"><h1 className="text-lg font-semibold text-slate-100">Calibration Scorecard (LPBF melt pool)</h1></header>
        <NoScorecardRecord />
        <LpbfKeyholeBenchmarkPanel />
        <N01Card n01={[]} note="Guo N01 is a documented keyhole-depth failure of the frozen kernels; calibration does not and must not fix it." />
        <LpbfLeaderboardPanel />
      </div>
    );
  }
  const counts = statusCounts(doc);
  return (
    <div className="space-y-4" data-testid="scorecard">
      <header className="p-4">
        <h1 className="text-lg font-semibold text-slate-100">Calibration Scorecard (LPBF melt pool)</h1>
        <p className="mt-1 text-sm text-slate-300"><span data-testid="evidence-badge" className="mr-2 inline-block rounded border border-sky-300 bg-sky-100 px-2 py-0.5 text-xs font-semibold text-sky-900">Screening only</span>{doc.evidence.statement}</p>
        <p className="mt-1 text-xs text-slate-400">Label promotion proposed: <strong>{doc.evidence.labelPromotionProposed}</strong>. Generated {doc.generatedAt}; implementation fingerprint <code>{doc.implementationHash}</code>; config sha256 <code>{doc.configSha256}</code>.{doc.calibrationVersion ? ` Calibration ${doc.calibrationVersion} (supersedes ${doc.supersedes?.record ?? "v1"}).` : ""}{doc.quick ? " SMOKE RUN: not a record." : ""}</p>
      </header>

      <PlainLanguageCard doc={doc} />

      <VersionCard doc={doc} />

      <N01Card n01={doc.n01} note={doc.catalogSentinels.note} />

      <LpbfKeyholeBenchmarkPanel />

      <h2 id="detailed-tables" tabIndex={-1} className="px-4 pt-2 text-base font-semibold text-slate-100">Detailed tables</h2>

      <Card>
        <CardHeader><CardTitle>Gate outcome</CardTitle></CardHeader>
        <CardContent>
          <p className="mb-3 flex flex-wrap gap-2 text-xs" data-testid="gate-summary">
            {(["enabled", "within-source-only", "rejected", "no-data"] as GateStatus[]).map((s) => (
              <span key={s} className="inline-flex items-center gap-1"><StatusChip status={s} /><span className="tabular-nums">{counts[s]}</span></span>
            ))}
          </p>
          {counts.enabled === 0 ? <p data-testid="none-enabled" className="mb-3 text-sm text-slate-700">No cell passes the gate. Calibrated mode is therefore not offered in the Melt Pool lab, and every result stays the unchanged screening output.</p> : null}
          <HeadlineTable rows={doc.headline} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Errors on data the model was not fitted to (each source left out in turn)</CardTitle></CardHeader>
        <CardContent><P2Table rows={doc.headline} /></CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Regime confusion vs published labels</CardTitle></CardHeader>
        <CardContent><ConfusionSection doc={doc} /></CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Interval coverage (leak-free, source-aware)</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table data-testid="coverage-table" className="w-full text-left text-xs">
              <caption className="mb-2 text-left text-slate-600">Coverage of the source-aware interval on each held-out source; the between-source term never uses the held-out source. Wilson 95 % interval of the proportion.</caption>
              <thead><tr className="border-b border-slate-200 text-slate-600">
                <th scope="col" className="p-2">Cell</th><th scope="col" className="p-2">Held out</th><th scope="col" className="p-2">Nominal</th>
                <th scope="col" className="p-2">Coverage</th><th scope="col" className="p-2">n</th><th scope="col" className="p-2">Width ratio</th>
              </tr></thead>
              <tbody>
                {doc.coverage.map((c) => (
                  <tr key={`${c.kernel}/${c.material}/${c.quantity}/${c.heldOut}/${c.level}`} className="border-b border-slate-100">
                    <td className="p-2">{KERNEL_LABELS[c.kernel] ?? c.kernel} · {c.material} · {c.quantity}</td>
                    <td className="p-2">{c.heldOut}</td><td className="p-2">{c.level} %</td>
                    <td className="p-2">{fmt2(c.coverage)}{ci(c.wilson95)}</td><td className="p-2">{c.n}</td>
                    <td className="p-2">{fmt2(c.widthRatio)}{c.notInformative ? " (not informative)" : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Fitted parameters</CardTitle></CardHeader>
        <CardContent><ParamsTable rows={doc.headline} /></CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Unresolved-row accounting</CardTitle></CardHeader>
        <CardContent>
          <p className="mb-2 text-xs text-slate-600">{doc.unresolved.rule}</p>
          <div className="overflow-x-auto">
            <table data-testid="unresolved-table" className="w-full text-left text-xs">
              <thead><tr className="border-b border-slate-200 text-slate-600">
                <th scope="col" className="p-2">Kernel</th><th scope="col" className="p-2">Source</th><th scope="col" className="p-2">Role</th>
                <th scope="col" className="p-2">Rows</th><th scope="col" className="p-2">Resolved at default</th><th scope="col" className="p-2">Unresolved at default</th>
              </tr></thead>
              <tbody>
                {doc.unresolved.perKernelSource.map((u) => (
                  <tr key={`${u.kernel}/${u.source}`} className="border-b border-slate-100">
                    <td className="p-2">{KERNEL_LABELS[u.kernel] ?? u.kernel}</td><td className="p-2">{u.source}</td><td className="p-2">{u.role}</td>
                    <td className="p-2">{u.rowsUsed}</td><td className="p-2">{u.resolvedAtDefault}</td>
                    <td className="p-2">{u.unresolvedAtDefault}{u.unresolvedAtDefault ? ` (${Object.entries(u.statusAtDefault).filter(([k]) => k !== "computed").map(([k, v]) => `${k}: ${v}`).join(", ")})` : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className="mt-2 list-disc pl-5 text-xs text-slate-700">
            {doc.unresolved.loader.filter((l) => l.excludedByLoader.length > 0).map((l) => (
              <li key={l.source}>{l.source}: {l.excludedByLoader.map((x) => `${x.rowId} (${x.reason})`).join("; ")}</li>
            ))}
            {doc.unresolved.notGeometrySources.map((x) => <li key={x.source}>Not a geometry source: {x.source}: {x.reason}</li>)}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Provenance</CardTitle></CardHeader>
        <CardContent>
          <ul className="space-y-2 text-xs text-slate-700">
            {doc.sources.map((s) => (
              <li key={s.source} data-source={s.source}>
                <strong>{s.source}</strong> ({s.role}; {s.material}; {s.rowsUsed} rows, {s.parameterSets} parameter sets)
                {s.doi ? <> · DOI <a className="underline" href={doiHref(s.doi.split(" + ")[0])}>{s.doi}</a></> : null}
                {s.tableSha256 ? <> · table sha256 <code>{s.tableSha256}</code></> : null}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-slate-600">Tool <code>{doc.provenance.tool.path}</code> sha256 <code>{doc.provenance.tool.sha256}</code>. {doc.catalogSentinels.title}: Guo and NIST IN718 are test-only and never enter a fit or the gate.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>What this does not show</CardTitle></CardHeader>
        <CardContent><ul className="list-disc space-y-1 pl-5 text-xs text-slate-700">{doc.notes.map((n) => <li key={n}>{n}</li>)}</ul></CardContent>
      </Card>

      <LpbfLeaderboardPanel />
    </div>
  );
}

/** The scorecard module. In the static demo a snapshot/error-bands fingerprint mismatch hides the cards (docs/DEMO_STATIC_DESIGN.md section 4). */
export function LpbfCalibrationScorecardLab(props: { document?: LpbfCalibrationScorecardDocument | null } = {}) {
  const view = <ScorecardView {...props} />;
  return IS_STATIC_DEMO ? <DemoFingerprintGate>{view}</DemoFingerprintGate> : view;
}
