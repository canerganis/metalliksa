import React, { useEffect, useId, useState } from 'react';
import {
  BLIND_PROTOCOL,
  BLIND_WORDING,
  checkInputsHeader,
  draftMissing,
  draftToMetadata,
  type BlindCsvDialect,
  type BlindHeaderCheck,
  type BlindMetadataDraft,
  type BlindPreview,
} from '../../data/lpbfUserBlind';
import { blindClient, bytesToBase64, describeBlindError } from '../../services/lpbfUserBlindClient';
import { Notice, buttonClass, inputClass, primaryClass } from './ResearchControls';
import { CheckBox } from './BlindTestMetadataForm';

const MAX_FILE_BYTES = BLIND_PROTOCOL.caps.fileBytes;
const FILE_NAME = new RegExp(BLIND_PROTOCOL.regex.fileName);

export const FILE_NAME_INVALID_TEXT = 'The file name may use letters, digits, spaces, dots, underscores, hyphens and brackets (1 to 120 characters), not starting with = + - @ or a dot. Rename the file and pick it again.';
export const SIZE_CAP_TEXT = 'The file exceeds 256 KiB. Split the campaign into blocks; each block needs at least 12 conditions to be scored.';

export interface FreezeRequest {
  metadata: Record<string, unknown>; inputsCsvBase64: string; inputsFileName: string;
  previewSha256: string; overlapSha256: string; acknowledgements: Record<string, true>;
}

export function acknowledgementLabel(code: string, preview: BlindPreview): string {
  const best = `${preview.bestReachable.status}${preview.bestReachable.reasons.length ? ` (${preview.bestReachable.reasons.join('; ')})` : ''}`;
  switch (code) {
    case 'predeterminedInconclusive': return `I understand this design can at best end ${best}.`;
    case 'powderLayerDescriptive': return 'I understand a powder layer test is shown for information and is not scored.';
    case 'exposedDescriptive': return `I understand this test is not blind and is shown for information: ${preview.bestReachable.reasons.join('; ') || 'exposure declared or found'}.`;
    case 'publishedConditionOverlap': return 'I understand some conditions match a published data set.';
    case 'calibrationOverlap': return 'I understand some conditions match calibration data on this computer.';
    default: return code;
  }
}

/** The review shown before anything is frozen: parsed inputs, status, issues, labels, overlap, budget, acknowledgements. */
export function BlindTestPreviewReview({ preview, acks, onAck, onFreeze, freezeBusy = false, freezeError = null }: {
  preview: BlindPreview; acks: Record<string, boolean>; onAck: (code: string, value: boolean) => void;
  onFreeze: () => void; freezeBusy?: boolean; freezeError?: string | null;
}) {
  const ready = preview.acknowledgementsRequired.every(code => acks[code]) && preview.predictorPinned && !freezeBusy;
  const overlapTotal = preview.overlap.earlierTests.length + preview.overlap.publishedSets.length + preview.overlap.calibrationStores.length + preview.overlap.buildJobHistory.length;
  const dc = preview.designChecks;
  const divergences = BLIND_PROTOCOL.divergences.filter(d => preview.divergences.includes(d.id));
  return <div className="space-y-5" data-testid="blind-preview-review">
    <section aria-labelledby="blind-parsed-h" className="space-y-2">
      <h3 id="blind-parsed-h" className="text-sm font-semibold text-slate-100">Parsed inputs</h3>
      <p className="text-xs text-slate-400">These are the values the app read from your file, in canonical units. They are inputs only, never a prediction. Check the units and the beam before you freeze anything.</p>
      <p className="text-xs text-slate-300">{preview.counts.conditions} conditions, {preview.counts.tracks} tracks, {preview.counts.sections} sections, {preview.counts.rows} rows. Format: {preview.dialect}.</p>
      {preview.aliases.length > 0 && <p className="text-xs text-slate-400">Header mapping: {preview.aliases.map(a => `${a.header} read as ${a.canonical}${a.unit ? ` in ${a.unit}` : ''}${a.factor !== 1 ? ` (factor ${a.factor})` : ''}`).join('; ')}.</p>}
      <div className="max-h-80 overflow-auto" tabIndex={0} role="region" aria-label="Units read from the header">
        <table className="w-full whitespace-nowrap text-xs text-slate-300 [&_td]:pr-3 [&_th]:pr-3 [&_th]:text-left">
          <caption className="sr-only">Header unit read and conversion applied</caption>
          <thead><tr><th scope="col">Column</th><th scope="col">Header in your file</th><th scope="col">Unit read</th><th scope="col">Conversion factor</th></tr></thead>
          <tbody>{Object.entries(preview.units).map(([col, u]) => <tr key={col}><td>{col}</td><td>{u.header}</td><td>{u.unitRead ?? `not stated, read as ${BLIND_PROTOCOL.canonicalUnit[col as keyof typeof BLIND_PROTOCOL.canonicalUnit] ?? 'canonical unit'}`}</td><td>{u.factor}</td></tr>)}</tbody>
        </table>
      </div>
      <div className="max-h-96 overflow-auto" tabIndex={0} role="region" aria-label="Parsed conditions (scrollable)">
        <table className="w-full whitespace-nowrap text-xs text-slate-300 [&_td]:pr-3 [&_th]:pr-3 [&_th]:text-left" data-testid="blind-parsed-table">
          <caption className="sr-only">Parsed conditions</caption>
          <thead><tr><th scope="col">Condition</th><th scope="col">Power (W)</th><th scope="col">Speed (mm/s)</th><th scope="col">Beam as given (um)</th><th scope="col">Beam quantity</th><th scope="col">Beam definition</th><th scope="col">Beam 1/e2 (um)</th><th scope="col">Tracks</th><th scope="col">Rows</th></tr></thead>
          <tbody>{preview.parsedInputs.map(p => <tr key={p.condition}><td>{p.condition}</td><td>{p.P_W}</td><td>{p.v_mm_s}</td><td>{p.beamDeclared_um}</td><td>{p.beamQuantity}</td><td>{p.beamDefinition}</td><td>{p.d_1e2_um}</td><td>{p.tracks}</td><td>{p.rows}</td></tr>)}</tbody>
        </table>
      </div>
    </section>

    <section aria-labelledby="blind-best-h" className="space-y-2">
      <h3 id="blind-best-h" className="text-sm font-semibold text-slate-100">Best reachable outcome</h3>
      <p className="text-sm text-slate-200" data-testid="blind-best-reachable">Best reachable outcome: {preview.bestReachable.status}{preview.bestReachable.reasons.length > 0 ? ` (${preview.bestReachable.reasons.join('; ')})` : ''}</p>
      <p className="text-xs text-slate-400">{preview.research.text}</p>
      <p className="text-xs text-slate-400">Grades: power {preview.grades.power}, beam {preview.grades.beam}, block {preview.grades.block}.</p>
      <p className="text-xs text-slate-400">Design: {dc.nConditions} conditions ({dc.nMinMet ? 'the minimum for scoring is met' : 'below the minimum for scoring'}). Leverage: {dc.leverage.nBelow ?? 'n/a'} below and {dc.leverage.nAtOrAbove20 ?? 'n/a'} at or above the index cuts. Resolution: {dc.resolution.evaluable ? 'can be evaluated' : dc.resolution.reason}.</p>
      {dc.uMNote && <p className="text-xs text-slate-400">{dc.uMNote}.</p>}
    </section>

    {preview.blockIssues.length > 0 && <section aria-labelledby="blind-issues-h" className="space-y-2">
      <h3 id="blind-issues-h" className="text-sm font-semibold text-slate-100">Block issues</h3>
      <ul className="space-y-1 text-xs text-slate-300" data-testid="blind-block-issues">{preview.blockIssues.map(i => <li key={i.code}><span className="font-semibold text-amber-200">{i.text}.</span> {i.fix}</li>)}</ul>
    </section>}

    <section aria-labelledby="blind-labels-h" className="space-y-2">
      <h3 id="blind-labels-h" className="text-sm font-semibold text-slate-100">Labels and declared divergences</h3>
      <ul className="list-disc pl-5 text-xs text-slate-300">{preview.labels.map(l => <li key={l}>{l}</li>)}</ul>
      <ul className="space-y-1 text-xs text-slate-400" data-testid="blind-applying-divergences">{divergences.map(d => <li key={d.id}><span className="font-semibold text-slate-200">{d.id}</span>: {d.rule}</li>)}</ul>
    </section>

    <section aria-labelledby="blind-overlap-h" className="space-y-1">
      <h3 id="blind-overlap-h" className="text-sm font-semibold text-slate-100">Overlap with data on this computer</h3>
      {overlapTotal === 0 ? <p className="text-xs text-slate-400">No overlap found with earlier tests, published sets, calibration stores or Build Job history.</p> : <ul className="list-disc pl-5 text-xs text-amber-200" data-testid="blind-overlap">
        {preview.overlap.earlierTests.map(e => <li key={e.freezeKey}>{e.nConditions} conditions match an earlier test that was {e.kind}.</li>)}
        {preview.overlap.publishedSets.map(e => <li key={e.datasetId}>{e.nConditions} conditions match the published set {e.datasetId}.</li>)}
        {preview.overlap.calibrationStores.map(e => <li key={e.storeId}>{e.nConditions} conditions match calibration store {e.storeId}.</li>)}
        {preview.overlap.buildJobHistory.map((e, i) => <li key={i}>{e.nConditions} conditions match Build Job history on this computer (partial check).</li>)}
      </ul>}
      {overlapTotal > 0 && <p className="text-xs text-slate-400">You may drop overlapping conditions from the file now and run the check again.</p>}
    </section>

    <section aria-labelledby="blind-budget-h" className="space-y-1">
      <h3 id="blind-budget-h" className="text-sm font-semibold text-slate-100">Budget</h3>
      <p className="text-xs text-slate-300" data-testid="blind-budget">{preview.budget.conditions} of at most {preview.budget.cap} conditions, {preview.budget.solverCalls} solver calls, about {preview.budget.estimate_s} s.</p>
    </section>

    {!preview.predictorPinned && <p role="alert" className="rounded border border-rose-700/60 bg-rose-950/20 p-3 text-xs text-rose-200">The running solver does not match the reviewed served model ({preview.predictorUnpinnedFiles.join(', ') || 'files not listed'}), so predictions cannot be frozen from it.</p>}

    <section aria-labelledby="blind-ack-h" className="space-y-2">
      <h3 id="blind-ack-h" className="text-sm font-semibold text-slate-100">Acknowledgements</h3>
      {preview.acknowledgementsRequired.length === 0 ? <p className="text-xs text-slate-400">No acknowledgement is required for this design.</p> : preview.acknowledgementsRequired.map(code => <CheckBox key={code} label={acknowledgementLabel(code, preview)} checked={Boolean(acks[code])} onChange={v => onAck(code, v)} />)}
    </section>

    <div className="space-y-2">
      <p className="text-xs text-slate-400" data-testid="blind-queue-note">{preview.budget.queueNote}</p>
      <button type="button" className={primaryClass} disabled={!ready} onClick={onFreeze}>{freezeBusy ? 'Freezing...' : 'Freeze predictions'}</button>
      {freezeError && <p role="alert" className="text-xs text-rose-200">{freezeError}</p>}
    </div>
  </div>;
}

export interface BlindTestInputsStepProps {
  draft: BlindMetadataDraft;
  onFreeze: (request: FreezeRequest) => void;
  freezeBusy?: boolean;
  freezeError?: string | null;
}

export function BlindTestInputsStep({ draft, onFreeze, freezeBusy = false, freezeError = null }: BlindTestInputsStepProps) {
  const fileId = useId();
  const [file, setFile] = useState<{ name: string; size: number } | null>(null);
  const [check, setCheck] = useState<BlindHeaderCheck | null>(null);
  const [base64, setBase64] = useState<string | null>(null);
  const [preview, setPreview] = useState<BlindPreview | null>(null);
  const [acks, setAcks] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const metadataKey = JSON.stringify(draft);
  useEffect(() => { setPreview(null); setAcks({}); }, [metadataKey]);
  const missing = draftMissing(draft);

  async function onPick(event: React.ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0];
    setPreview(null); setAcks({}); setError(null); setBase64(null); setCheck(null);
    if (!picked) { setFile(null); return; }
    setFile({ name: picked.name, size: picked.size });
    if (!FILE_NAME.test(picked.name) || /^[=+\-@.]/.test(picked.name)) { setError(FILE_NAME_INVALID_TEXT); return; }
    if (picked.size > MAX_FILE_BYTES) { setError(SIZE_CAP_TEXT); return; }
    const result = checkInputsHeader(await picked.slice(0, 65536).text(), draft.csvDialect as BlindCsvDialect);
    setCheck(result);
    if (!result.ok) return;
    setBase64(bytesToBase64(new Uint8Array(await picked.arrayBuffer())));
  }

  async function runPreview() {
    if (!file || !base64) return;
    setBusy(true); setError(null);
    try { setPreview(await blindClient.preview(draftToMetadata(draft), base64, file.name)); } catch (e) { setPreview(null); setError(describeBlindError(e)); } finally { setBusy(false); }
  }

  function freeze() {
    if (!file || !base64 || !preview) return;
    const acknowledgements: Record<string, true> = {};
    for (const code of preview.acknowledgementsRequired) if (acks[code]) acknowledgements[code] = true;
    onFreeze({ metadata: draftToMetadata(draft), inputsCsvBase64: base64, inputsFileName: file.name, previewSha256: preview.previewSha256, overlapSha256: preview.overlapSha256, acknowledgements });
  }

  return <div className="space-y-5">
    <p className="text-sm text-slate-300">The inputs file carries power, speed and spot only. Your measurements go in a separate file later. The app does not receive them until it has frozen its predictions.</p>
    <div className="space-y-1.5">
      <label htmlFor={fileId} className="block text-xs text-slate-400">Inputs file (CSV, at most 256 KiB)</label>
      <input id={fileId} type="file" accept=".csv,text/csv" className={inputClass} onChange={onPick} />
      {file && <p className="text-xs text-slate-500">{file.name}, {file.size} bytes</p>}
    </div>
    {check && !check.ok && <div role="alert" className="space-y-1 rounded border border-rose-700/60 bg-rose-950/20 p-3 text-xs text-rose-200" data-testid="blind-header-issues">{check.issues.map(i => <p key={i.code}>{i.message} ({i.code})</p>)}</div>}
    {check && check.warnings.length > 0 && <Notice messages={check.warnings} />}
    {check?.ok && <div className="space-y-1 text-xs text-slate-400" data-testid="blind-header-ok">
      <p>Header looks right; {check.dataLines} data lines. This is a convenience check; the worker repeats every check.</p>
      {check.echoes.length > 0 && <p>Mapped: {check.echoes.map(e => `${e.header} as ${e.canonical}${e.unit ? ` (${e.unit}, factor ${e.factor})` : ''}`).join('; ')}.</p>}
      {check.labels.length > 0 && <p>{check.labels.join('; ')}.</p>}
      {check.ignored.length > 0 && <p>Ignored columns: {check.ignored.join(', ')}.</p>}
    </div>}
    {error && <p role="alert" className="text-xs text-rose-200">{error}</p>}
    {missing.length > 0 && <p role="status" className="text-xs text-amber-200">Fill in the description first: {missing.join(', ')}.</p>}
    <button type="button" className={buttonClass} disabled={busy || !base64 || missing.length > 0} onClick={runPreview}>{busy ? 'Checking...' : 'Check inputs with the app'}</button>
    {preview && <BlindTestPreviewReview preview={preview} acks={acks} onAck={(code, v) => setAcks(a => ({ ...a, [code]: v }))} onFreeze={freeze} freezeBusy={freezeBusy} freezeError={freezeError} />}
    <p className="text-[11px] text-slate-500">{BLIND_WORDING.anchorAdvice}</p>
  </div>;
}
