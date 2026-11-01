import React from 'react';
import {
  BLIND_PROTOCOL,
  BLIND_WORDING,
  MODULE_CEILING_BADGE,
  SERVED_VALUE_LABEL,
  USER_TIER_LABEL,
  USER_VALUE_LABEL,
  formatSignedPercent,
  type BlindArm,
  type BlindLedgerRow,
  type BlindReport,
} from '../../data/lpbfUserBlind';
import { HASH_CHECK_SKIPPED_NOTE } from '../../services/lpbfUserBlindClient';
import { Badge, buttonClass } from './ResearchControls';

const SENSITIVITY_ARMS: { id: string; label: string }[] = [
  { id: 'served:P-5%', label: 'Power 5 % lower' }, { id: 'served:P+5%', label: 'Power 5 % higher' },
  { id: 'served:d-5%', label: 'Beam 5 % smaller' }, { id: 'served:d+5%', label: 'Beam 5 % larger' },
];
const RESEARCH_ARMS = ['research:melt-link', 'research:cavity'];
const STAT_ROWS: { label: string; stat: 'median' | 'p90' | 'meanSigned' | 'maxApe'; limit: 'median' | 'p90' | 'meanSigned' | 'maxApe' }[] = [
  { label: 'Median APE', stat: 'median', limit: 'median' }, { label: '90th percentile APE', stat: 'p90', limit: 'p90' },
  { label: 'Mean signed error', stat: 'meanSigned', limit: 'meanSigned' }, { label: 'Maximum APE', stat: 'maxApe', limit: 'maxApe' },
];
const BOOT_KEY = { median: 'median', p90: 'p90', meanSigned: 'mean_signed', maxApe: 'max_ape' } as const;

/** Formatting only: three decimals of the fraction the Python report holds. */
const frac = (v: number | string | null | undefined): string => (v === null || v === undefined ? 'n/a' : typeof v === 'number' ? v.toFixed(3) : v);
const um = (v: number | null | undefined): string => (v === null || v === undefined ? 'n/a' : String(v));

function StatsTable({ arm, thresholds, boot }: { arm: BlindArm; thresholds: Record<string, unknown>; boot?: Record<string, { lo?: number; hi?: number; marginal?: boolean }> }) {
  if (!arm.stats) return <p className="text-xs text-slate-400">No statistics for this arm.</p>;
  const s = arm.stats;
  return <div className="max-w-full overflow-auto" tabIndex={0} role="region" aria-label="Statistics of the served arm (scrollable)">
    <table className="w-full whitespace-nowrap text-xs text-slate-300 [&_td]:pr-3 [&_th]:pr-3 [&_th]:text-left" data-testid="blind-served-stats">
      <caption className="sr-only">Statistics of the served arm on {s.n} conditions</caption>
      <thead><tr><th scope="col">Statistic</th><th scope="col">Value (fraction)</th><th scope="col">Limit</th><th scope="col">Against the limit</th>{boot && <th scope="col">Bootstrap 95 % interval</th>}</tr></thead>
      <tbody>{STAT_ROWS.map(r => {
        const b = boot?.[BOOT_KEY[r.stat]];
        return <tr key={r.stat}><td>{r.label}</td><td>{frac(s[r.stat])}</td><td>{String(thresholds[r.limit] ?? 'n/a')}</td><td>{s.thresholdsMet[r.stat] ? 'limit met' : 'limit not met'}</td>{boot && <td>{b ? `${frac(b.lo)} to ${frac(b.hi)}${b.marginal ? ' (marginal)' : ''}` : 'n/a'}</td>}</tr>;
      })}</tbody>
    </table>
    <p className="mt-1 text-[11px] text-slate-500">{s.n} conditions scored, 75th percentile APE {frac(s.p75)}, {s.nFailed} failed, {s.nNotFormed} track not formed.</p>
  </div>;
}

/** Lightweight scatter of observed against served depth. No 1:1 band and no percentage guide lines. */
export function ObservedServedSvg({ rows }: { rows: BlindLedgerRow[] }) {
  const pts = rows.filter(r => r.D_obs_um !== null && r.pred.served?.value_um !== null && r.pred.served?.value_um !== undefined);
  if (pts.length === 0) return <p className="text-xs text-slate-400">No condition has both an observed and a served depth.</p>;
  const top = Math.max(...pts.map(r => Math.max(r.D_obs_um as number, r.pred.served.value_um as number, r.inputSensitivityRange_um?.max_um ?? 0)));
  const step = [10, 20, 25, 50, 100, 200, 250, 500, 1000].find(s => top / s <= 6) ?? 1000;
  const max = Math.ceil(top / step) * step;
  const W = 420, H = 340, L = 56, R = 16, T = 12, B = 46;
  const x = (v: number) => L + (v / max) * (W - L - R);
  const y = (v: number) => H - B - (v / max) * (H - T - B);
  const ticks = Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step);
  return <svg viewBox={`0 0 ${W} ${H}`} role="img" data-testid="blind-scatter" className="w-full max-w-lg rounded border border-slate-700 bg-slate-950"
    aria-label={`Observed depth against served depth for ${pts.length} conditions, in micrometres`}>
    <line x1={L} y1={H - B} x2={W - R} y2={H - B} stroke="#64748b" /><line x1={L} y1={T} x2={L} y2={H - B} stroke="#64748b" />
    {ticks.map(t => <g key={t}><line x1={x(t)} y1={H - B} x2={x(t)} y2={H - B + 4} stroke="#64748b" /><text x={x(t)} y={H - B + 16} fontSize={10} textAnchor="middle" fill="#cbd5e1">{t}</text>
      <line x1={L - 4} y1={y(t)} x2={L} y2={y(t)} stroke="#64748b" /><text x={L - 7} y={y(t) + 3} fontSize={10} textAnchor="end" fill="#cbd5e1">{t}</text></g>)}
    <text x={(L + W - R) / 2} y={H - 8} fontSize={11} textAnchor="middle" fill="#e2e8f0">Observed depth (um), Measured (user-supplied)</text>
    <text x={12} y={(T + H - B) / 2} fontSize={11} textAnchor="middle" fill="#e2e8f0" transform={`rotate(-90 12 ${(T + H - B) / 2})`}>Served depth (um), Unresolved</text>
    {pts.map(r => <g key={r.condition}>
      {r.inputSensitivityRange_um && <line x1={x(r.D_obs_um as number)} x2={x(r.D_obs_um as number)} y1={y(r.inputSensitivityRange_um.min_um)} y2={y(r.inputSensitivityRange_um.max_um)} stroke="#475569" strokeWidth={2} />}
      <circle cx={x(r.D_obs_um as number)} cy={y(r.pred.served.value_um as number)} r={3.5} fill="#38bdf8"><title>{`${r.condition}: observed ${r.D_obs_um} um, served ${r.pred.served.value_um} um`}</title></circle>
    </g>)}
  </svg>;
}

export interface BlindTestReportViewProps {
  report: BlindReport;
  reportSha256?: string | null;
  hashCheck?: 'matched' | 'skipped' | 'not-declared' | null;
  onExportCsv?: () => void;
  onExportBundle?: () => void;
  exportBusy?: boolean;
  exportError?: string | null;
}

export function BlindTestReportView({ report, reportSha256 = null, hashCheck = null, onExportCsv, onExportBundle, exportBusy = false, exportError = null }: BlindTestReportViewProps) {
  const served = report.arms.served;
  const boot = served.bootstrap95 as Record<string, { lo?: number; hi?: number; marginal?: boolean }> | undefined;
  const fixes = BLIND_WORDING.blockIssueFix as Record<string, string>;
  const th = report.thresholds as Record<string, unknown>;
  const res = report.resolution as Record<string, unknown>;
  const lev = report.leverage as Record<string, unknown>;
  const fr = report.fragile as Record<string, unknown>;
  return <article className="space-y-6" data-testid="blind-report" aria-labelledby="blind-report-title">
    <div className="space-y-2 rounded-lg border border-cyan-800/50 bg-cyan-950/30 p-4"><p className="text-sm text-cyan-100" data-testid="blind-banner">{report.banner}</p><Badge>{MODULE_CEILING_BADGE}</Badge></div>
    <header className="space-y-2">
      <h2 id="blind-report-title" className="text-xl font-semibold text-slate-100">{report.title}</h2>
      <p className="text-sm text-slate-200" data-testid="blind-blindness">{report.blindness.sentence}</p>
      {report.blindness.reasons.length > 0 && <ul className="list-disc pl-5 text-xs text-slate-300" data-testid="blind-blindness-reasons">{report.blindness.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>}
      {report.blindness.exposuresAfterCommitment.length > 0 && <div className="text-xs text-slate-300" data-testid="blind-exposures-after-commitment"><p>Exposures after your commitment (they cannot have shaped the committed targets, so this test stays blind-committed):</p><ul className="list-disc pl-5">{report.blindness.exposuresAfterCommitment.map((e, i) => <li key={i}>{e.status}: {e.reason}</li>)}</ul></div>}
      <p className="text-xs text-slate-400">Blindness status: {report.blindness.status}. Attempt {report.attempt.n}{report.attempt.earlierTargetsSha256.length ? ` (${report.attempt.earlierTargetsSha256.length} earlier)` : ''}. Commitment: {report.commitment.declared ? (report.commitment.matched ? 'declared and matched' : 'declared, not matched') : 'none declared'}.</p>
      <p className="break-all text-[11px] text-slate-500">Freeze {report.freezeKey}. Targets {report.targetsSha256}.{reportSha256 ? ` Report ${reportSha256}.` : ''}</p>
      {hashCheck === 'skipped' && <p role="status" className="text-xs text-amber-200">{HASH_CHECK_SKIPPED_NOTE}</p>}
      {hashCheck === 'matched' && <p className="text-xs text-slate-400">Browser hash check: the downloaded report matches its declared SHA-256.</p>}
    </header>

    <section aria-labelledby="blind-served-h" className="space-y-2">
      <h3 id="blind-served-h" className="text-base font-semibold text-slate-100">Served arm</h3>
      <p className="text-sm text-slate-200" data-testid="blind-served-sentence">{served.sentence}</p>
      <p className="text-xs text-slate-400">Status: {served.status}. Coverage: {served.coverage.k} of {served.coverage.n} conditions.</p>
      <StatsTable arm={served} thresholds={th} boot={boot} />
    </section>

    <section aria-labelledby="blind-sens-h" className="space-y-2">
      <h3 id="blind-sens-h" className="text-base font-semibold text-slate-100">Input sensitivity summary</h3>
      <p className="text-xs text-slate-400">The served model was also run with power and beam size each changed by 5 %. This is an input sensitivity range, not an error bar.</p>
      <div className="max-w-full overflow-auto" tabIndex={0} role="region" aria-label="Input sensitivity arms (scrollable)">
        <table className="w-full whitespace-nowrap text-xs text-slate-300 [&_td]:pr-3 [&_th]:pr-3 [&_th]:text-left" data-testid="blind-sensitivity">
          <caption className="sr-only">Input sensitivity arms</caption>
          <thead><tr><th scope="col">Input changed</th><th scope="col">Status</th><th scope="col">Median APE</th><th scope="col">Maximum APE</th></tr></thead>
          <tbody>{SENSITIVITY_ARMS.map(a => { const arm = report.arms[a.id]; return <tr key={a.id}><td>{a.label}</td><td>{arm?.status ?? 'n/a'}</td><td>{frac(arm?.stats?.median)}</td><td>{frac(arm?.stats?.maxApe)}</td></tr>; })}</tbody>
        </table>
      </div>
    </section>

    <section aria-labelledby="blind-research-h" className="space-y-2">
      <h3 id="blind-research-h" className="text-base font-semibold text-slate-100">Research arms</h3>
      <ul className="space-y-1 text-xs text-slate-300" data-testid="blind-research-arms">{RESEARCH_ARMS.map(id => <li key={id}><span className="font-semibold text-slate-200">{id}</span>: {report.arms[id]?.sentence ?? 'Not in this report.'}</li>)}</ul>
    </section>

    <section aria-labelledby="blind-labels-h" className="space-y-2">
      <h3 id="blind-labels-h" className="text-base font-semibold text-slate-100">Labels</h3>
      <ul className="list-disc pl-5 text-xs text-slate-300" data-testid="blind-labels">{report.labels.map(l => <li key={l}>{l}</li>)}</ul>
      <p className="text-xs text-slate-400">Grades: power {report.grades.power}, beam {report.grades.beam}, block {report.grades.block}.</p>
      {report.blockIssues.length > 0 && <ul className="space-y-1 text-xs text-slate-300" data-testid="blind-report-issues">{report.blockIssues.map(code => <li key={code}><span className="font-semibold text-amber-200">{code}</span>: {fixes[code] ?? 'See the divergence list.'}</li>)}</ul>}
    </section>

    <section aria-labelledby="blind-qual-h" className="space-y-2">
      <h3 id="blind-qual-h" className="text-base font-semibold text-slate-100">Resolution and leverage</h3>
      <p className="text-xs text-slate-300" data-testid="blind-resolution">Resolution qualifier: {String(res.status)}{res.reason ? ` (${String(res.reason)})` : ''}.{res.u_m_assumed ? ` ${String(res.leadAssumption ?? '')}` : ''}</p>
      <p className="text-xs text-slate-300" data-testid="blind-leverage">Leverage: {String(lev.n_below ?? 'n/a')} conditions below and {String(lev.n_at_or_above_20 ?? 'n/a')} at or above the index cuts; {lev.ok === true ? 'requirement met' : 'requirement not met'}{lev.reason ? ` (${String(lev.reason)})` : ''}.</p>
      <p className="text-xs text-slate-400">Fragility to input changes: {String(fr.input)}. Fragility to property changes: {String(fr.property)}.</p>
      <p className="text-[11px] text-slate-500">{String(th.source ?? '')}</p>
    </section>

    <section aria-labelledby="blind-div-h" className="space-y-2">
      <h3 id="blind-div-h" className="text-base font-semibold text-slate-100">Declared divergences from the pre-registered method</h3>
      <ul className="space-y-1 text-xs text-slate-300" data-testid="blind-divergences">{report.divergences.map(d => <li key={d.id}><span className="font-semibold text-slate-100">{d.id}</span>{d.applied ? <span className="ml-2 rounded border border-amber-600 px-1.5 text-[10px] text-amber-200">applies to this test</span> : <span className="ml-2 text-[10px] text-slate-500">declared, does not apply here</span>}: {d.rule}</li>)}</ul>
    </section>

    <section aria-labelledby="blind-cond-h" className="space-y-2">
      <h3 id="blind-cond-h" className="text-base font-semibold text-slate-100">Per condition</h3>
      <p className="text-xs text-slate-400">{BLIND_WORDING.relNote}. Shown here as a percent with one decimal.</p>
      <div className="max-h-[32rem] max-w-full overflow-auto" tabIndex={0} role="region" aria-label="Per condition comparison (scrollable)">
        <table className="w-full whitespace-nowrap text-xs text-slate-300 [&_td]:pr-3 [&_td]:align-top [&_th]:pr-3 [&_th]:text-left" data-testid="blind-ledger">
          <caption className="sr-only">Observed and served depth per condition</caption>
          <thead><tr>
            <th scope="col">Condition</th><th scope="col">Power (W)</th><th scope="col">Speed (mm/s)</th><th scope="col">Beam (um)</th>
            <th scope="col">Observed depth (um)<span className="block font-normal text-slate-500">{USER_VALUE_LABEL}, {USER_TIER_LABEL}</span></th>
            <th scope="col">Served depth (um)<span className="block font-normal text-slate-500">{report.servedValueLabel.text}</span></th>
            <th scope="col">Signed relative difference</th><th scope="col">Input sensitivity range (um)</th><th scope="col">Tracks</th>
          </tr></thead>
          <tbody>{report.ledger.map(r => <tr key={r.condition}>
            <td>{r.condition}{r.notFormed ? ' (track not formed)' : ''}</td><td>{r.P_W}</td><td>{r.v_mm_s}</td><td>{r.d_1e2_um}</td>
            <td>{um(r.D_obs_um)}<span className="block text-[10px] text-slate-500">{USER_VALUE_LABEL}</span><span className="block text-[10px] text-slate-500">{USER_TIER_LABEL}</span></td>
            <td>{um(r.pred.served?.value_um)}<span className="block text-[10px] text-slate-500">{SERVED_VALUE_LABEL}</span></td>
            <td>{formatSignedPercent(r.pred.served?.rel)}</td>
            <td>{r.inputSensitivityRange_um ? `${r.inputSensitivityRange_um.min_um} to ${r.inputSensitivityRange_um.max_um}` : 'n/a'}</td><td>{r.nTracks}</td>
          </tr>)}</tbody>
        </table>
      </div>
      <p className="text-[11px] text-slate-500">{report.servedValueLabel.text} {report.ledger[0]?.inputSensitivityRange_um?.note ?? ''}</p>
      <div className="text-xs text-slate-400" data-testid="blind-exclusions">
        <p>Excluded: {report.exclusions.sections} sections, {report.exclusions.tracks} tracks, {report.exclusions.conditions} conditions.</p>
        {report.excluded.targets.length > 0 && <ul className="list-disc pl-5">{report.excluded.targets.map(t => <li key={`${t.row}`}>{t.condition}{t.track ? `, ${t.track}` : ''}{t.section ? `, ${t.section}` : ''}: {t.status}</li>)}</ul>}
        {report.notFormed.conditions.length > 0 && <p>Track not formed in: {report.notFormed.conditions.join(', ')}.</p>}
      </div>
    </section>

    <section aria-labelledby="blind-plot-h" className="space-y-2">
      <h3 id="blind-plot-h" className="text-base font-semibold text-slate-100">Observed against served depth</h3>
      <ObservedServedSvg rows={report.ledger} />
      <details className="text-xs text-slate-400"><summary className="cursor-pointer text-sky-300">Table of the plotted values</summary>
        <table className="mt-2 text-xs text-slate-300 [&_td]:pr-3 [&_th]:pr-3 [&_th]:text-left"><thead><tr><th scope="col">Condition</th><th scope="col">Observed (um)</th><th scope="col">Served (um)</th></tr></thead>
          <tbody>{report.ledger.map(r => <tr key={r.condition}><td>{r.condition}</td><td>{um(r.D_obs_um)}</td><td>{um(r.pred.served?.value_um)}</td></tr>)}</tbody></table>
      </details>
    </section>

    <section aria-labelledby="blind-export-h" className="space-y-2 print:hidden">
      <h3 id="blind-export-h" className="text-base font-semibold text-slate-100">Export</h3>
      <div className="flex flex-wrap gap-2">
        <button type="button" className={buttonClass} disabled={!onExportCsv || exportBusy} onClick={onExportCsv}>Download comparison CSV</button>
        <button type="button" className={buttonClass} disabled={!onExportBundle || exportBusy} onClick={onExportBundle}>Download bundle</button>
        <button type="button" className={buttonClass} onClick={() => window.print()}>Print this report</button>
      </div>
      {exportError && <p role="alert" className="text-xs text-rose-200">{exportError}</p>}
      <p className="text-[11px] text-slate-500">The CSV and the bundle are written by the worker and downloaded as they are. Protocol {BLIND_PROTOCOL.protocolId}.</p>
    </section>
  </article>;
}

export default BlindTestReportView;
