import React, { useId, useState } from 'react';
import {
  BLIND_PROTOCOL,
  BLIND_WORDING,
  checkTargetsHeader,
  draftMissing,
  type BlindCsvDialect,
  type BlindHeaderCheck,
  type BlindMetadataDraft,
} from '../../data/lpbfUserBlind';
import { blindClient, HASHING_NEEDS_SECURE_NOTE } from '../../services/lpbfUserBlindClient';
import { Field, Select, inputClass } from './ResearchControls';
import { BLIND_FIELD_HELP, blindOptionLabel } from './blindTestHelp';

type Key = keyof BlindMetadataDraft;
const ENUM_KEY: Partial<Record<Key, string>> = {
  mode: 'mode', alloy: 'alloy', quantity: 'quantity', depthBoundary: 'depthBoundary', measurementMethod: 'measurementMethod', depthDatum: 'depthDatum',
  reduction: 'reduction', crossSectionLocation: 'crossSectionLocation', beamQuantity: 'beam.quantity', beamDefinition: 'beam.definition', beamBasis: 'beam.basis',
  beamProfile: 'beam.profile', powerBasis: 'power.basis', substrateKind: 'substrate.kind', surfacePreparation: 'substrate.surfacePreparation',
  alsi10mgState: 'substrate.alsi10mgState', preheatBasis: 'preheatBasis', atmosphere: 'atmosphere', depthUncertaintyBasis: 'depthUncertainty.basis',
  coverageFactor: 'depthUncertainty.coverageFactor', chemistryBasis: 'chemistry.basis', predictionsViewedBeforeFreeze: 'independence.predictionsViewedBeforeFreeze',
  dataPreviouslyPublished: 'independence.dataPreviouslyPublished', csvDialect: 'csvDialect',
};
/** Required fields without a default start with an empty choice so the user has to decide. */
const NEEDS_CHOICE = new Set<Key>(['mode', 'alloy', 'reduction', 'beamQuantity', 'substrateKind', 'predictionsViewedBeforeFreeze', 'usedForMachineCalibration']);

function Help({ field }: { field: Key }) {
  const h = BLIND_FIELD_HELP[field];
  return <details className="text-[11px] text-slate-400"><summary className="cursor-pointer text-sky-300">Help: {h.label}</summary><p className="mt-1 max-w-3xl">{h.help}</p></details>;
}

function options(field: Key): { value: string; label: string }[] {
  if (field === 'usedForMachineCalibration') return [{ value: '', label: 'Choose...' }, { value: 'false', label: 'No' }, { value: 'true', label: 'Yes' }];
  const words = ((BLIND_PROTOCOL.enums as Record<string, readonly (string | number)[]>)[ENUM_KEY[field] ?? ''] ?? []).map(String);
  const list = words.map(w => ({ value: w, label: blindOptionLabel(w) }));
  return NEEDS_CHOICE.has(field) ? [{ value: '', label: 'Choose...' }, ...list] : list;
}

export interface BlindTestMetadataFormProps {
  draft: BlindMetadataDraft;
  onChange: (patch: Partial<BlindMetadataDraft>) => void;
  /** Test seam: defaults to whether SubtleCrypto exists in this browser. */
  subtleAvailable?: boolean;
}

export function BlindTestMetadataForm({ draft, onChange, subtleAvailable }: BlindTestMetadataFormProps) {
  const subtle = subtleAvailable ?? blindClient.hasSubtleCrypto();
  const missing = draftMissing(draft);
  const text = (field: Key, type: 'text' | 'number' = 'text', placeholder = '') => (
    <div className="space-y-1" key={field}><Field label={BLIND_FIELD_HELP[field].label} value={String(draft[field])} type={type} placeholder={placeholder} onChange={value => onChange({ [field]: value } as Partial<BlindMetadataDraft>)} /><Help field={field} /></div>
  );
  const select = (field: Key) => (
    <div className="space-y-1" key={field}><Select label={BLIND_FIELD_HELP[field].label} value={String(draft[field])} options={options(field)} onChange={value => onChange({ [field]: value } as Partial<BlindMetadataDraft>)} /><Help field={field} /></div>
  );
  const check = (field: Key) => (
    <div className="space-y-1" key={field}><CheckBox label={BLIND_FIELD_HELP[field].label} checked={Boolean(draft[field])} onChange={value => onChange({ [field]: value } as Partial<BlindMetadataDraft>)} /><Help field={field} /></div>
  );
  const group = (title: string, children: React.ReactNode) => (
    <fieldset className="space-y-3 rounded-lg border border-slate-800 p-4"><legend className="px-2 text-xs font-semibold uppercase tracking-wide text-slate-300">{title}</legend><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{children}</div></fieldset>
  );
  return <form className="space-y-4" aria-label="Blind test description" onSubmit={e => e.preventDefault()}>
    {group('Block', <>{text('blockLabel')}{select('mode')}{select('alloy')}{select('quantity')}{select('csvDialect')}</>)}
    {group('Measurement', <>{select('depthBoundary')}{select('measurementMethod')}{select('depthDatum')}{select('reduction')}{select('crossSectionLocation')}{text('tracksPerCondition', 'number')}{text('sectionsPerTrack', 'number')}{check('rowsAreSeparateTracks')}{select('depthUncertaintyBasis')}{text('depthUncertaintyU', 'number')}{select('coverageFactor')}</>)}
    {group('Beam', <>{select('beamQuantity')}{text('beamDiameter_um', 'number')}{select('beamDefinition')}{select('beamBasis')}{select('beamProfile')}{check('beamUncertaintyReleased')}{text('beamUk1_um', 'number')}</>)}
    {group('Power', <>{select('powerBasis')}{check('powerMeterNamed')}{check('powerUncertaintyReleased')}{text('powerUk1Rel', 'number')}</>)}
    {group('Plate and process', <>{text('wavelength_nm', 'number')}{select('substrateKind')}{draft.substrateKind === 'powder-layer' && text('layerThickness_um', 'number')}{check('amSubstrate')}{text('thickness_mm', 'number')}{select('surfacePreparation')}{draft.alloy === 'AlSi10Mg' && select('alsi10mgState')}{text('preheat_C', 'number')}{select('preheatBasis')}{select('atmosphere')}</>)}
    {group('Chemistry', <>{select('chemistryBasis')}{text('sulfur_ppm', 'number')}{text('oxygen_ppm', 'number')}</>)}
    {group('Independence', <>{select('predictionsViewedBeforeFreeze')}{select('dataPreviouslyPublished')}{text('publishedDoi')}{select('usedForMachineCalibration')}</>)}
    {draft.mode === 'post-measurement' && <TargetCommitment draft={draft} onChange={onChange} subtle={subtle} />}
    {missing.length > 0 && <p role="status" className="text-xs text-amber-200">Still to fill in: {missing.join(', ')}.</p>}
  </form>;
}

export function CheckBox({ label, checked, onChange, disabled = false }: { label: string; checked: boolean; onChange: (value: boolean) => void; disabled?: boolean }) {
  const id = useId();
  return <div className="flex items-start gap-2 text-xs text-slate-300"><input id={id} type="checkbox" className="mt-0.5" checked={checked} disabled={disabled} onChange={e => onChange(e.target.checked)} /><label htmlFor={id}>{label}</label></div>;
}

/** Post-measurement mode: hash the finished targets file in the browser (header checked first) or take a pasted hash. */
function TargetCommitment({ draft, onChange, subtle }: { draft: BlindMetadataDraft; onChange: (patch: Partial<BlindMetadataDraft>) => void; subtle: boolean }) {
  const fileId = useId();
  const [check, setCheck] = useState<BlindHeaderCheck | null>(null);
  const [lines, setLines] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  async function onFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true); setCheck(null); setLines(null);
    try {
      const head = await file.slice(0, 65536).text();
      const result = checkTargetsHeader(head, draft.csvDialect as BlindCsvDialect);
      setCheck(result);
      if (!result.ok) { onChange({ targetCommitmentSha256: '' }); return; }
      const bytes = new Uint8Array(await file.arrayBuffer());
      setLines(checkTargetsHeader(new TextDecoder().decode(bytes), draft.csvDialect as BlindCsvDialect).dataLines);
      const hash = await blindClient.sha256Hex(bytes);
      onChange({ targetCommitmentSha256: hash ?? '' });
    } finally { setBusy(false); }
  }
  return <fieldset className="space-y-3 rounded-lg border border-slate-800 p-4">
    <legend className="px-2 text-xs font-semibold uppercase tracking-wide text-slate-300">Commitment to the targets file</legend>
    <p className="text-xs text-slate-400">{BLIND_FIELD_HELP.targetCommitmentSha256.help}</p>
    {subtle ? <div className="space-y-1.5"><label htmlFor={fileId} className="block text-xs text-slate-400">Finished targets file (hashed in this browser, never sent)</label><input id={fileId} type="file" accept=".csv,text/csv" className={inputClass} onChange={onFile} disabled={busy} /></div>
      : <p role="status" className="text-xs text-amber-200">{HASHING_NEEDS_SECURE_NOTE}</p>}
    {check && !check.ok && <ul role="alert" className="list-disc pl-5 text-xs text-rose-200">{check.issues.map(i => <li key={i.code}>{i.message} ({i.code})</li>)}</ul>}
    {check?.ok && lines !== null && <p className="text-xs text-slate-400">Header looks right; {lines} data lines.</p>}
    <Field label={BLIND_FIELD_HELP.targetCommitmentSha256.label} value={draft.targetCommitmentSha256} onChange={value => onChange({ targetCommitmentSha256: value.trim().toLowerCase() })} placeholder="64 hex characters" />
    {draft.targetCommitmentSha256 && !/^[0-9a-f]{64}$/.test(draft.targetCommitmentSha256) && <p role="alert" className="text-xs text-rose-200">A SHA-256 is 64 lower-case hex characters.</p>}
    <p role="status" className="rounded border border-amber-700/60 bg-amber-950/20 p-2 text-xs text-amber-200">{BLIND_WORDING.doNotResave}</p>
  </fieldset>;
}
