import React, { Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react';
import { IS_STATIC_DEMO } from '../../demo/flag.ts';
import { DemoUnavailable } from '../../demo/demoNotes';
import { useVisiblePolling } from '../../hooks/useVisiblePolling';
import {
  BLIND_REVEAL_PHRASE,
  BLIND_WORDING,
  MODULE_CEILING_BADGE,
  blindInputsTemplateCsv,
  blindMetadataTemplateJson,
  blindTargetsTemplateCsv,
  checkedBlindReport,
  draftMissing,
  type BlindCsvDialect,
  type BlindGet,
  type BlindList,
  type BlindReceipt,
  type BlindReport,
  type BlindJobType,
} from '../../data/lpbfUserBlind';
import { BlindClientError, HASH_CHECK_SKIPPED_NOTE, blindClient, describeBlindError, type BlindPollResult } from '../../services/lpbfUserBlindClient';
import { useUserBlindStore, type BlindPendingJob } from '../../store/useUserBlindStore';
import { Badge, Empty, Notice, buttonClass, panelClass } from './ResearchControls';
import { BlindTestMetadataForm } from './BlindTestMetadataForm';
import { BlindTestInputsStep, type FreezeRequest } from './BlindTestInputsStep';
import { BlindTestReceiptView, downloadBlindBytes } from './BlindTestReceiptView';
import { BlindTestTargetsStep, type ScoreRequest } from './BlindTestTargetsStep';
import { BlindTestList } from './BlindTestList';

const BlindTestReportView = lazy(() => import('./BlindTestReportView'));

export const SHARED_HOST_WARNING = 'Every signed-in user of this server can list and open every blind test on it, including your measurements and the frozen predictions.';
const LOCAL_HOSTNAMES = ['localhost', '127.0.0.1', '[::1]', '::1'];
export function isLocalHostname(hostname: string | undefined): boolean {
  return hostname === undefined || hostname === '' || LOCAL_HOSTNAMES.includes(hostname);
}

export function BlindSharedHostWarning({ sharedHost, hostname }: { sharedHost: boolean; hostname?: string }) {
  if (!sharedHost && isLocalHostname(hostname)) return null;
  return <p role="alert" data-testid="blind-shared-host" className="rounded-lg border border-amber-700/60 bg-amber-950/30 p-3 text-sm text-amber-200">{SHARED_HOST_WARNING}</p>;
}

export const BLIND_STEPS = ['Describe', 'Inputs and check', 'Freeze', 'Measure and score', 'Report'] as const;

export function BlindStepper({ step, onStep }: { step: number; onStep: (step: number) => void }) {
  return <nav aria-label="Blind test steps"><ol className="flex flex-wrap gap-2">{BLIND_STEPS.map((label, i) => <li key={label}>
    <button type="button" className={`${buttonClass} ${step === i + 1 ? 'border-sky-500 bg-sky-950 text-sky-200' : ''}`} aria-current={step === i + 1 ? 'step' : undefined} onClick={() => onStep(i + 1)}>{i + 1}. {label}</button>
  </li>)}</ol></nav>;
}

export interface BlindTestPanelProps {
  /** Test seam: force the static demo branch. Defaults to the compile-time flag. */
  demo?: boolean;
  /** Test seam: the page hostname. Defaults to location.hostname. */
  hostname?: string;
  initialStep?: number;
}

export default function BlindTestPanel({ demo, hostname, initialStep }: BlindTestPanelProps) {
  if (demo ?? IS_STATIC_DEMO) return <DemoUnavailable what="Your blind test" />;
  return <BlindTestPanelLive hostname={hostname} initialStep={initialStep} />;
}

type Delivered = { name: string; attempt: number | null; bytes: Uint8Array; hashCheck: 'matched' | 'skipped' | 'not-declared'; sha256: string | null; freezeKey: string };

function BlindTestPanelLive({ hostname, initialStep }: { hostname?: string; initialStep?: number }) {
  const draft = useUserBlindStore(s => s.draft), patchDraft = useUserBlindStore(s => s.patchDraft), resetDraft = useUserBlindStore(s => s.resetDraft);
  const pending = useUserBlindStore(s => s.pending);
  const [step, setStep] = useState(initialStep ?? 1);
  const [list, setList] = useState<BlindList | null>(null);
  const [listTick, setListTick] = useState(0);
  const [receipt, setReceipt] = useState<BlindReceipt | null>(null);
  const [get, setGet] = useState<BlindGet | null>(null);
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [notices, setNotices] = useState<string[]>([]);
  const [freezeError, setFreezeError] = useState<string | null>(null);
  const [scoreRefusal, setScoreRefusal] = useState<{ code: string | null; message: string } | null>(null);
  const [revealMessage, setRevealMessage] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState<{ report: BlindReport; sha256: string | null; hashCheck: 'matched' | 'skipped' | 'not-declared' } | null>(null);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const pageHost = hostname ?? (typeof location !== 'undefined' ? location.hostname : undefined);

  const freezeBusy = pending.some(p => p.jobType === 'user-blind-freeze');
  const scoreBusy = pending.some(p => p.jobType === 'user-blind-score');
  const revealBusy = pending.some(p => p.jobType === 'user-blind-reveal');
  const exportBusy = pending.some(p => p.jobType === 'user-blind-bundle' || p.jobType === 'user-blind-open');
  const addNotice = useCallback((message: string) => setNotices(n => [...n.slice(-3), message]), []);

  const loadGet = useCallback(async (key: string): Promise<BlindGet | null> => {
    try {
      const g = await blindClient.get(key);
      if (!mounted.current) return null;
      setGet(g); setReceipt(g.receipt); setActiveKey(key);
      return g;
    } catch (e) { addNotice(describeBlindError(e)); return null; }
  }, [addNotice]);

  const deliver = useCallback((d: Delivered) => {
    const short = d.freezeKey.slice(0, 12);
    const att = d.attempt === null ? '' : `-attempt${d.attempt}`;
    if (d.name === 'blind-report.json') {
      try {
        const report = checkedBlindReport(JSON.parse(new TextDecoder().decode(d.bytes)));
        setLoaded({ report, sha256: d.sha256, hashCheck: d.hashCheck }); setActiveKey(d.freezeKey); setStep(5);
      } catch { addNotice('The report did not match the expected document and was not shown.'); }
    } else if (d.name === 'blind-comparison.csv') downloadBlindBytes(`blind-comparison-${short}${att}.csv`, d.bytes as unknown as BlobPart, 'text/csv');
    else if (d.name === 'blind-bundle.tar') downloadBlindBytes(`blind-bundle-${short}${att}.tar`, d.bytes as unknown as BlobPart, 'application/x-tar');
    else downloadBlindBytes(`${d.name.replace(/\.json$/, '')}-${short}.json`, d.bytes as unknown as BlobPart, 'application/json');
    if (d.hashCheck === 'skipped') addNotice(HASH_CHECK_SKIPPED_NOTE);
  }, [addNotice]);

  const queue = useCallback(async (jobType: BlindJobType, payload: Record<string, unknown>, extra: Partial<BlindPendingJob> = {}): Promise<boolean> => {
    try {
      const id = await blindClient.submit(jobType, payload);
      useUserBlindStore.getState().addPending({ id, jobType, freezeKey: typeof payload.freezeKey === 'string' ? payload.freezeKey : null, name: null, attempt: null, ...extra });
      return true;
    } catch (e) {
      const message = describeBlindError(e);
      if (jobType === 'user-blind-freeze') setFreezeError(message);
      else if (jobType === 'user-blind-score') setScoreRefusal(e instanceof BlindClientError && e.kind === 'refusal' ? { code: e.code, message: e.message } : { code: null, message });
      else if (jobType === 'user-blind-reveal') setRevealMessage(message);
      else setExportError(message);
      return false;
    }
  }, []);

  const requestDocument = useCallback(async (g: BlindGet, name: string, attempt: number | null) => {
    setExportError(null);
    const doc = g.documents.find(d => d.name === name && d.attempt === attempt);
    if (!doc) { setExportError('That document is not available for this test yet.'); return; }
    const expected = doc.sha256 ?? (name === 'blind-freeze.json' ? g.receipt.freezeSha256 : null);
    if (doc.jobRecordPresent && doc.jobId) {
      try {
        const r = await blindClient.fetchDocument(doc.jobId, name, expected);
        deliver({ name, attempt, bytes: r.bytes, hashCheck: r.hashCheck, sha256: r.sha256, freezeKey: g.freezeKey });
      } catch (e) { setExportError(describeBlindError(e)); }
      return;
    }
    await queue('user-blind-open', { freezeKey: g.freezeKey, name, ...(attempt === null ? {} : { attempt }) }, { name, attempt });
  }, [deliver, queue]);

  const handleJob = useCallback(async (job: BlindPendingJob, r: Exclude<BlindPollResult, { state: 'pending' }>) => {
    if (r.state === 'failed') {
      const message = `${r.message}${r.code ? ` (${r.code})` : ''}`;
      if (job.jobType === 'user-blind-freeze') setFreezeError(message);
      else if (job.jobType === 'user-blind-score') setScoreRefusal({ code: r.code, message: r.message });
      else if (job.jobType === 'user-blind-reveal') setRevealMessage(message);
      else setExportError(message);
      return;
    }
    const result = r.result as Record<string, unknown>;
    const key = (job.freezeKey ?? (typeof result.freezeKey === 'string' ? result.freezeKey : null));
    if (job.jobType === 'user-blind-freeze') {
      const rec = r.result as BlindReceipt;
      useUserBlindStore.getState().rememberFreeze({ freezeKey: rec.freezeKey, freezeSha256: rec.freezeSha256, createdAt: rec.createdAt, blockLabel: rec.blockLabel, alloy: rec.alloy, conditions: rec.counts.conditions });
      setReceipt(rec); setActiveKey(rec.freezeKey); setGet(null); setLoaded(null); setFreezeError(null); setStep(3); setListTick(t => t + 1);
      void loadGet(rec.freezeKey);
    } else if (job.jobType === 'user-blind-reveal' && key) {
      setRevealMessage('The predictions were revealed. This test is no longer blind.');
      await loadGet(key);
    } else if (job.jobType === 'user-blind-score' && key) {
      setScoreRefusal(null); setListTick(t => t + 1);
      const g = await loadGet(key);
      const n = typeof result.attempt === 'number' ? result.attempt : null;
      if (g && n !== null) await requestDocument(g, 'blind-report.json', n);
    } else if ((job.jobType === 'user-blind-bundle' || job.jobType === 'user-blind-open') && key) {
      const name = job.jobType === 'user-blind-bundle' ? 'blind-bundle.tar' : job.name;
      const sha = typeof result.sha256 === 'string' ? result.sha256 : null;
      const attempt = job.jobType === 'user-blind-bundle' ? (typeof result.bundleN === 'number' ? result.bundleN : null) : (typeof result.attempt === 'number' ? result.attempt : job.attempt);
      if (!name) return;
      try {
        const doc = await blindClient.fetchDocument(job.id, name, sha);
        deliver({ name, attempt, bytes: doc.bytes, hashCheck: doc.hashCheck, sha256: doc.sha256, freezeKey: key });
      } catch (e) { setExportError(describeBlindError(e)); }
    }
  }, [deliver, loadGet, requestDocument]);

  // One poll step per tick for every queued job; hidden hubs pause, a reload resumes from the persisted ids.
  useVisiblePolling(async isLive => {
    for (const job of useUserBlindStore.getState().pending) {
      try {
        const r = await blindClient.pollJob(job.id, job.jobType);
        if (!isLive()) return null;
        if (r.state === 'pending') continue;
        useUserBlindStore.getState().removePending(job.id);
        await handleJob(job, r);
      } catch (e) {
        if (!isLive()) return null;
        useUserBlindStore.getState().removePending(job.id);
        addNotice(describeBlindError(e));
      }
    }
    return useUserBlindStore.getState().pending.length > 0 ? 1500 : null;
  }, pending.length > 0, pending.map(p => p.id).join(','));

  const onFreeze = (req: FreezeRequest) => { setFreezeError(null); void queue('user-blind-freeze', { ...req }); };
  const onScore = (req: ScoreRequest) => { setScoreRefusal(null); void queue('user-blind-score', { ...req }); };
  const onReveal = () => { if (activeKey) { setRevealMessage(null); void queue('user-blind-reveal', { freezeKey: activeKey, confirmation: BLIND_REVEAL_PHRASE }); } };
  const openTest = async (key: string) => {
    setLoaded(null); setScoreRefusal(null); setRevealMessage(null); setExportError(null);
    const g = await loadGet(key);
    if (g) setStep(g.attempts.length > 0 ? 5 : 3);
  };
  const onExportBundle = async () => {
    if (!get) return;
    const bundles = get.documents.filter(d => d.name === 'blind-bundle.tar');
    if (bundles.length > 0) await requestDocument(get, 'blind-bundle.tar', bundles[bundles.length - 1].attempt);
    else await queue('user-blind-bundle', { freezeKey: get.freezeKey });
  };
  const revealedOrScored = Boolean(get && (get.revealEvents.length > 0 || get.attempts.length > 0));
  const missing = draftMissing(draft);

  return <section className={`${panelClass} space-y-5`} aria-label="Your blind test" data-testid="blind-test-panel">
    <header className="space-y-2">
      <div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-semibold text-slate-100">{BLIND_WORDING.tab}</h2><Badge>{MODULE_CEILING_BADGE}</Badge></div>
      <p className="text-sm text-cyan-100" data-testid="blind-panel-banner">{BLIND_WORDING.banner}</p>
      <details className="text-xs text-slate-400"><summary className="cursor-pointer text-sky-300">What this test can and cannot show</summary>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>The order of events is recorded on the local clock of this computer. {BLIND_WORDING.anchorAdvice}</li>
          <li>The served predictor is public and deterministic, so viewing predictions elsewhere in this app is declared by you, not prevented.</li>
          <li>A person with disk access to the store can rewrite it. That is detectable only against a hash you anchored outside this computer.</li>
          <li>On a shared host every signed-in user can read every test.</li>
        </ul></details>
    </header>
    <BlindSharedHostWarning sharedHost={Boolean(list?.sharedHost)} hostname={pageHost} />
    {list?.readOnly && <p role="status" className="rounded-lg border border-slate-700 p-3 text-xs text-slate-300">This installation is read-only. You can list and open tests, but freezing, revealing and scoring are refused by the worker.</p>}
    <Notice messages={notices} />
    <BlindStepper step={step} onStep={setStep} />

    {step === 1 && <div className="space-y-4">
      <p className="text-sm text-slate-300">Inputs and measurements travel in separate files. The app does not receive your measurements until it has frozen its predictions.</p>
      <div className="flex flex-wrap gap-2">
        <button type="button" className={buttonClass} onClick={() => downloadBlindBytes('blind_inputs_v1.csv', blindInputsTemplateCsv(), 'text/csv')}>Download inputs template</button>
        <button type="button" className={buttonClass} onClick={() => downloadBlindBytes('blind_targets_v1.csv', blindTargetsTemplateCsv(), 'text/csv')}>Download targets template</button>
        <button type="button" className={buttonClass} onClick={() => downloadBlindBytes('blind_metadata_v1.json', blindMetadataTemplateJson(), 'application/json')}>Download metadata template</button>
        <button type="button" className={buttonClass} onClick={resetDraft}>Reset the description</button>
      </div>
      <p className="text-xs text-slate-400">The example row in each template is marked SYNTHETIC-EXAMPLE and is refused if you upload it.</p>
      <BlindTestMetadataForm draft={draft} onChange={patchDraft} />
      <button type="button" className={buttonClass} disabled={missing.length > 0} onClick={() => setStep(2)}>Continue to inputs</button>
    </div>}

    {step === 2 && <BlindTestInputsStep draft={draft} onFreeze={onFreeze} freezeBusy={freezeBusy} freezeError={freezeError} />}

    {step === 3 && (receipt ? <BlindTestReceiptView receipt={receipt} onContinue={() => setStep(4)} /> : <Empty>No freeze yet. Describe your test, check the inputs and freeze the predictions, or open a test from the list.</Empty>)}

    {step === 4 && <BlindTestTargetsStep freezeKey={activeKey} defaultDialect={draft.csvDialect as BlindCsvDialect} revealedOrScored={revealedOrScored}
      scoreBusy={scoreBusy} scoreRefusal={scoreRefusal} revealBusy={revealBusy} revealMessage={revealMessage} onScore={onScore} onReveal={onReveal} />}

    {step === 5 && <div className="space-y-4">
      {!activeKey && <Empty>No test is open. Score a test or open one from the list.</Empty>}
      {get && get.attempts.length > 0 && <div className="space-y-1" data-testid="blind-attempts"><h3 className="text-sm font-semibold text-slate-100">Score attempts</h3>
        <ul className="space-y-1 text-xs text-slate-300">{get.attempts.map(a => <li key={a.n}>Attempt {a.n}{a.blindness ? `: ${a.blindness}, served ${a.statuses?.served ?? 'n/a'}` : ': unreadable record'}{a.blindness && <button type="button" className={`${buttonClass} ml-2`} disabled={exportBusy} onClick={() => void requestDocument(get, 'blind-report.json', a.n)}>Open report of attempt {a.n}</button>}</li>)}</ul></div>}
      {exportBusy && <p role="status" className="text-xs text-slate-400">Fetching a document from the worker...</p>}
      {loaded && <Suspense fallback={<p className="text-xs text-slate-400">Loading the report view...</p>}>
        <BlindTestReportView report={loaded.report} reportSha256={loaded.sha256} hashCheck={loaded.hashCheck} exportBusy={exportBusy} exportError={exportError}
          onExportCsv={get ? () => void requestDocument(get, 'blind-comparison.csv', loaded.report.attempt.n) : undefined}
          onExportBundle={get ? () => void onExportBundle() : undefined} />
      </Suspense>}
      {!loaded && exportError && <p role="alert" className="text-xs text-rose-200">{exportError}</p>}
    </div>}

    <div className="border-t border-slate-800 pt-4"><BlindTestList onLoad={key => void openTest(key)} onListed={setList} refreshKey={listTick} activeKey={activeKey} /></div>
  </section>;
}
