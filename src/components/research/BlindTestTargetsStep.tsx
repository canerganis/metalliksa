import React, { useId, useState } from 'react';
import {
  BLIND_PROTOCOL,
  BLIND_REVEAL_PHRASE,
  BLIND_WORDING,
  checkTargetsHeader,
  type BlindCsvDialect,
  type BlindHeaderCheck,
} from '../../data/lpbfUserBlind';
import { bytesToBase64 } from '../../services/lpbfUserBlindClient';
import { AccessibleModal } from '../AccessibleModal';
import { Select, buttonClass, inputClass, primaryClass } from './ResearchControls';
import { CheckBox } from './BlindTestMetadataForm';
import { FILE_NAME_INVALID_TEXT, SIZE_CAP_TEXT } from './BlindTestInputsStep';
import { blindOptionLabel } from './blindTestHelp';

const FILE_NAME = new RegExp(BLIND_PROTOCOL.regex.fileName);
export interface ScoreRequest {
  freezeKey: string; targetsCsvBase64: string; targetsFileName: string;
  declarations: { viewedPredictionsBeforeFinalisingTargets: 'no' | 'yes' | 'unsure' }; acceptCommitmentMismatch: boolean;
}

/** Confirmation with the exact phrase typed by the user. What the reveal does depends on a matched commitment. */
export function BlindRevealDialog({ onCancel, onConfirm, busy = false }: { onCancel: () => void; onConfirm: () => void; busy?: boolean }) {
  const titleId = useId(), inputId = useId();
  const [typed, setTyped] = useState('');
  return <AccessibleModal open onClose={onCancel} labelledBy={titleId} panelClassName="w-full max-w-lg space-y-3 rounded-xl border border-slate-700 bg-slate-950 p-5">
    <h3 id={titleId} className="text-base font-semibold text-slate-100">Reveal the frozen predictions</h3>
    <p className="text-sm text-slate-300">Revealing shows the frozen predictions and is recorded on this computer. This cannot be undone.</p>
    <ul className="list-disc space-y-1 pl-5 text-xs text-slate-300" data-testid="blind-reveal-effects">
      <li>Without a matched commitment: every later score of this test is marked not blind.</li>
      <li>With a commitment: if you committed the targets file by its SHA-256 before the freeze and later upload exactly that file, this test stays blind-committed, and the reveal is listed under exposures after the commitment. If the uploaded file differs, the test is marked not blind.</li>
      <li>In both cases, any later test on this computer with overlapping conditions, frozen after this reveal, is marked not blind.</li>
    </ul>
    <p className="text-xs text-slate-400">Type this phrase exactly: <code className="text-slate-100">{BLIND_REVEAL_PHRASE}</code></p>
    <div className="space-y-1.5"><label htmlFor={inputId} className="block text-xs text-slate-400">Confirmation phrase</label><input id={inputId} autoFocus className={inputClass} value={typed} onChange={e => setTyped(e.target.value)} autoComplete="off" /></div>
    <div className="flex gap-2"><button type="button" className={primaryClass} disabled={typed !== BLIND_REVEAL_PHRASE || busy} onClick={onConfirm}>{busy ? 'Revealing...' : 'Reveal predictions'}</button><button type="button" className={buttonClass} onClick={onCancel}>Cancel</button></div>
  </AccessibleModal>;
}

export interface BlindTestTargetsStepProps {
  freezeKey: string | null;
  defaultDialect: BlindCsvDialect;
  /** True once a reveal record or a score exists for this freeze. */
  revealedOrScored?: boolean;
  scoreBusy?: boolean;
  /** Last refusal of the score submit, if any. */
  scoreRefusal?: { code: string | null; message: string } | null;
  revealBusy?: boolean;
  revealMessage?: string | null;
  onScore: (request: ScoreRequest) => void;
  onReveal: () => void;
}

export function BlindTestTargetsStep({ freezeKey, defaultDialect, revealedOrScored = false, scoreBusy = false, scoreRefusal = null, revealBusy = false, revealMessage = null, onScore, onReveal }: BlindTestTargetsStepProps) {
  const fileId = useId();
  const [dialect, setDialect] = useState<BlindCsvDialect>(defaultDialect);
  const [file, setFile] = useState<{ name: string; size: number } | null>(null);
  const [check, setCheck] = useState<BlindHeaderCheck | null>(null);
  const [base64, setBase64] = useState<string | null>(null);
  const [declaration, setDeclaration] = useState('');
  const [accept, setAccept] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [revealOpen, setRevealOpen] = useState(false);
  const mismatch = scoreRefusal?.code === 'COMMITMENT_MISMATCH';

  async function onPick(event: React.ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0];
    setCheck(null); setBase64(null); setLocalError(null);
    if (!picked) { setFile(null); return; }
    setFile({ name: picked.name, size: picked.size });
    if (!FILE_NAME.test(picked.name) || /^[=+\-@.]/.test(picked.name)) { setLocalError(FILE_NAME_INVALID_TEXT); return; }
    if (picked.size > BLIND_PROTOCOL.caps.fileBytes) { setLocalError(SIZE_CAP_TEXT); return; }
    const result = checkTargetsHeader(await picked.slice(0, 65536).text(), dialect);
    setCheck(result);
    if (result.ok) setBase64(bytesToBase64(new Uint8Array(await picked.arrayBuffer())));
  }

  function submit() {
    if (!freezeKey || !file || !base64 || !declaration) return;
    onScore({ freezeKey, targetsCsvBase64: base64, targetsFileName: file.name, declarations: { viewedPredictionsBeforeFinalisingTargets: declaration as 'no' | 'yes' | 'unsure' }, acceptCommitmentMismatch: mismatch && accept });
  }

  if (!freezeKey) return <p className="text-sm text-slate-400" data-testid="blind-targets-empty">Freeze predictions first, or load a test from the list, to score measurements against it.</p>;
  return <div className="space-y-5" data-testid="blind-targets-step">
    <p className="text-sm text-slate-300">Measure, then upload your targets file. The file must list exactly the frozen rows. A malformed file is refused without using up an attempt.</p>
    <p className="text-xs text-amber-200" role="status">{BLIND_WORDING.doNotResave}</p>
    <Select label="CSV format of the targets file" value={dialect} options={BLIND_PROTOCOL.enums.csvDialect.map(w => ({ value: w, label: blindOptionLabel(w) }))} onChange={v => setDialect(v as BlindCsvDialect)} />
    <div className="space-y-1.5">
      <label htmlFor={fileId} className="block text-xs text-slate-400">Targets file (CSV, at most 256 KiB)</label>
      <input id={fileId} type="file" accept=".csv,text/csv" className={inputClass} onChange={onPick} />
      {file && <p className="text-xs text-slate-500">{file.name}, {file.size} bytes</p>}
    </div>
    {check && !check.ok && <div role="alert" className="space-y-1 rounded border border-rose-700/60 bg-rose-950/20 p-3 text-xs text-rose-200" data-testid="blind-targets-issues">{check.issues.map(i => <p key={i.code}>{i.message} ({i.code})</p>)}</div>}
    {check?.ok && <p className="text-xs text-slate-400" data-testid="blind-targets-ok">Header looks right; {check.dataLines} data lines. The worker checks the rows and the key set.{check.ignored.length > 0 ? ` Ignored columns: ${check.ignored.join(', ')}.` : ''}</p>}
    {localError && <p role="alert" className="text-xs text-rose-200">{localError}</p>}
    <Select label="Did you view the frozen predictions before you finalised the targets?" value={declaration} options={[{ value: '', label: 'Choose...' }, { value: 'no', label: 'No' }, { value: 'yes', label: 'Yes' }, { value: 'unsure', label: 'Unsure' }]} onChange={setDeclaration} />
    <p className="text-[11px] text-slate-500">Yes or unsure marks the result as not blind.</p>
    {scoreRefusal && <p role="alert" className="text-xs text-rose-200" data-testid="blind-score-refusal">{scoreRefusal.message}{scoreRefusal.code ? ` (${scoreRefusal.code})` : ''}</p>}
    {mismatch && <CheckBox label="Continue anyway. The result will be marked as commitment not matched." checked={accept} onChange={setAccept} />}
    <button type="button" className={primaryClass} disabled={scoreBusy || !file || !base64 || !declaration || (mismatch && !accept)} onClick={submit}>{scoreBusy ? 'Scoring...' : 'Score against the frozen predictions'}</button>

    <section aria-labelledby="blind-reveal-h" className="space-y-2 border-t border-slate-800 pt-4">
      <h3 id="blind-reveal-h" className="text-sm font-semibold text-slate-100">Reveal the predictions</h3>
      <p className="text-xs text-slate-400">You can reveal the frozen predictions before you score. A reveal marks this test not blind unless your committed targets file is matched at scoring, and it marks later overlapping tests on this computer not blind.</p>
      {revealedOrScored && <p className="text-xs text-slate-400">The predictions are already available for this test.</p>}
      <button type="button" className={buttonClass} disabled={revealBusy} onClick={() => setRevealOpen(true)}>Reveal predictions</button>
      {revealMessage && <p role="status" className="text-xs text-slate-300">{revealMessage}</p>}
      {revealOpen && <BlindRevealDialog busy={revealBusy} onCancel={() => setRevealOpen(false)} onConfirm={() => { setRevealOpen(false); onReveal(); }} />}
    </section>
  </div>;
}
