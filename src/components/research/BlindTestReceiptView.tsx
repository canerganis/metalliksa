import React from 'react';
import type { BlindReceipt } from '../../data/lpbfUserBlind';
import { MODULE_CEILING_BADGE } from '../../data/lpbfUserBlind';
import { Badge, buttonClass } from './ResearchControls';

export function downloadBlindBytes(filename: string, data: BlobPart, type: string): void {
  const url = URL.createObjectURL(new Blob([data], { type }));
  const link = document.createElement('a');
  link.href = url; link.download = filename;
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** The receipt of a freeze: hashes, counts and availability counts. It never carries a predicted depth. */
export function BlindTestReceiptView({ receipt, onContinue }: { receipt: BlindReceipt; onContinue?: () => void }) {
  const withheldArms = receipt.armsFrozen;
  return <div className="space-y-4" data-testid="blind-receipt">
    <div className="flex flex-wrap items-center gap-2"><h3 className="text-base font-semibold text-slate-100">Receipt: {receipt.blockLabel}</h3><Badge>{MODULE_CEILING_BADGE}</Badge></div>
    <p className="text-sm text-slate-200" data-testid="blind-receipt-line">{receipt.receiptLine}</p>
    <p className="rounded border border-amber-700/60 bg-amber-950/20 p-3 text-sm text-amber-200" data-testid="blind-anchor-advice">{receipt.anchorAdvice}</p>
    {receipt.alreadyFrozen && <p role="status" className="text-xs text-slate-400">These inputs were already frozen. This is the existing record.</p>}
    <dl className="grid gap-x-6 gap-y-2 text-xs text-slate-300 sm:grid-cols-[max-content_1fr]">
      <dt className="text-slate-400">Freeze hash (freezeSha256)</dt><dd className="break-all font-mono">{receipt.freezeSha256}</dd>
      <dt className="text-slate-400">Freeze key</dt><dd className="break-all font-mono">{receipt.freezeKey}</dd>
      <dt className="text-slate-400">Predictions hash</dt><dd className="break-all font-mono">{receipt.predictionsSha256}</dd>
      <dt className="text-slate-400">Inputs hash</dt><dd className="break-all font-mono">{receipt.inputsSha256}</dd>
      <dt className="text-slate-400">Created (local clock, unverified)</dt><dd>{receipt.createdAt}</dd>
      <dt className="text-slate-400">Alloy</dt><dd>{receipt.alloy}</dd>
      <dt className="text-slate-400">Counts</dt><dd>{receipt.counts.conditions} conditions, {receipt.counts.tracks} tracks, {receipt.counts.sections} sections, {receipt.counts.rows} rows</dd>
      <dt className="text-slate-400">Target commitment</dt><dd className="break-all font-mono">{receipt.targetCommitmentSha256 ?? 'none'}</dd>
      <dt className="text-slate-400">Grades</dt><dd>power {receipt.grades.power}, beam {receipt.grades.beam}, block {receipt.grades.block}</dd>
    </dl>
    <section aria-labelledby="blind-arms-frozen-h" className="space-y-1">
      <h4 id="blind-arms-frozen-h" className="text-sm font-semibold text-slate-100">Arms frozen</h4>
      <ul className="text-xs text-slate-300">{withheldArms.map(a => <li key={a.id}>{a.id}: {a.available} of {a.of} conditions available{a.reasonCodes.length ? ` (${a.reasonCodes.join(', ')})` : ''}</li>)}</ul>
    </section>
    {receipt.labels.length > 0 && <ul className="list-disc pl-5 text-xs text-slate-300">{receipt.labels.map(l => <li key={l}>{l}</li>)}</ul>}
    <div className="flex flex-wrap gap-2">
      <button type="button" className={buttonClass} onClick={() => downloadBlindBytes(`blind-receipt-${receipt.freezeKey.slice(0, 12)}.json`, `${JSON.stringify(receipt, null, 1)}\n`, 'application/json')}>Download receipt JSON</button>
      {onContinue && <button type="button" className={buttonClass} onClick={onContinue}>Continue to measure and score</button>}
    </div>
  </div>;
}
