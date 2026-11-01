import { WORKSPACES } from '../data/workspaces';
import React, { Suspense, lazy, useRef, useState } from 'react';
import { BookOpen, Download, Upload } from 'lucide-react';
import { MeltPoolMeasuredTrackPanel } from './MeltPoolMeasuredTrackPanel';
import { useResearchStore } from '../store/useResearchStore';
import { ResearchSourcesPanel } from './research/ResearchSourcesPanel';
import { ResearchExtractionPanel } from './research/ResearchExtractionPanel';
import { ResearchRegistryPanel } from './research/ResearchRegistryPanel';
import { ResearchSyncPanel } from './research/ResearchSyncPanel';
import { Field, Select, Notice, Empty, Badge, useDraft, buttonClass, primaryClass, panelClass } from './research/ResearchControls';

const BlindTestPanel = lazy(() => import('./research/BlindTestPanel'));

const tabs = [{ id: 'brief', label: '1. Research brief' }, { id: 'sources', label: '2. Literature & sources' }, { id: 'extract', label: '3. Data extraction' }, { id: 'registry', label: '4. Registry & feedback' }, { id: 'catalog', label: 'Measured track catalog' }, { id: 'blind-test', label: 'Your blind test' }] as const;
const briefDefaults = { question: '', alloy: '', process: 'LPBF', method: '', dataType: '' };

export const AdvancedResearchHub: React.FC = () => {
  const state = useResearchStore(), importRef = useRef<HTMLInputElement>(null);
  const [messages, setMessages] = useState<string[]>([]);
  const activeBrief = state.briefs.find(brief => brief.id === state.activeBriefId);
  function exportRegistry() {
    const blob = new Blob([JSON.stringify(state.exportSnapshot(), null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob), anchor = document.createElement('a'); anchor.href = url; anchor.download = `metalliksa-research-${new Date().toISOString().slice(0, 10)}.json`; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <div className="mx-auto max-w-[1500px] space-y-5 p-4 lg:p-7" data-testid="research-hub">
    <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 pb-5">
      <div><div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-widest text-sky-400"><BookOpen size={15} /> {WORKSPACES.find(workspace => workspace.id === 'evidence')!.label} <Badge>Research</Badge></div><h1 className="text-2xl font-semibold text-slate-100">Research Hub</h1><p className="mt-2 max-w-3xl text-sm text-slate-400">Turn literature into traceable engineering evidence. Extract reported values, review their conditions, and link them to material and validation work.</p></div>
      <div className="flex gap-2"><button className={buttonClass} onClick={exportRegistry}><Download size={14} /> Export registry</button><button className={buttonClass} onClick={() => importRef.current?.click()}><Upload size={14} /> Import registry</button><input ref={importRef} type="file" accept=".json,application/json" className="hidden" aria-label="Import research registry" onChange={async event => { const file = event.target.files?.[0]; if (!file) return; const input = event.currentTarget; try { if (file.size > 10 * 1024 * 1024) throw new Error('Registry exceeds the 10 MB import limit.'); const result = state.importSnapshot(JSON.parse(await file.text())); setMessages(result.errors.length ? result.errors : ['Registry imported. Existing records were preserved.']); } catch (error) { setMessages([error instanceof Error ? error.message : 'Unable to import registry.']); } input.value = ''; }} /></div>
    </header>
    <Notice messages={[...(state.storageError ? [state.storageError] : []), ...messages]} />
    {state.storageError && <button className={buttonClass} onClick={() => {
      const url = URL.createObjectURL(new Blob([JSON.stringify({ ...state.exportSnapshot(), browserDrafts: state.drafts }, null, 2)], { type: 'application/json' }));
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = `research-browser-recovery-${Date.now()}.json`; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    }}><Download size={14} /> Export browser recovery copy</button>}
    <ResearchSyncPanel />
    <div className="flex flex-wrap items-end justify-between gap-3">{state.activeTab !== 'blind-test' ? <div className="min-w-64 flex-1 max-w-xl"><Select label="Active research brief" value={state.activeBriefId} options={[{ value: '', label: 'Create a research brief to begin' }, ...state.briefs.map(brief => ({ value: brief.id, label: brief.question }))]} onChange={state.setActiveBrief} /></div> : <div className="flex-1" />}<p className="text-xs text-slate-500">{state.sources.length} saved sources · {state.findings.length} extractions · {state.integrations.length} evidence links</p></div>
    <nav aria-label="Research workflow" className="flex flex-wrap gap-2">{tabs.map(tab => <button key={tab.id} className={`${buttonClass} ${state.activeTab === tab.id ? 'border-sky-500 bg-sky-950 text-sky-200' : ''}`} aria-current={state.activeTab === tab.id ? 'step' : undefined} onClick={() => state.setActiveTab(tab.id)}>{tab.label}</button>)}</nav>
    {state.activeTab === 'brief' && <BriefPanel />}
    {state.activeTab === 'sources' && (activeBrief ? <ResearchSourcesPanel key={activeBrief.id} /> : <Empty>Create or select a research brief before collecting sources.</Empty>)}
    {state.activeTab === 'extract' && <ResearchExtractionPanel />}
    {state.activeTab === 'registry' && <ResearchRegistryPanel />}
    {state.activeTab === 'catalog' && <MeltPoolMeasuredTrackPanel />}
    {state.activeTab === 'blind-test' && <Suspense fallback={<p className="text-sm text-slate-400">Loading your blind test...</p>}><BlindTestPanel /></Suspense>}
    <p className="border-t border-slate-800 pt-3 text-xs text-slate-500">Browser records persist locally; server revisions are saved explicitly. Metadata discovery is not full-text review. Confidence and review are user assessments; they do not certify a material or validate a solver. Export JSON for portable traceability.</p>
  </div>;
};

function BriefPanel() {
  const { draft, patch, replace } = useDraft('brief', briefDefaults);
  const state = useResearchStore(); const [errors, setErrors] = useState<string[]>([]);
  return <section className={panelClass}><h2 className="mb-2 text-lg font-semibold text-slate-100">Define the engineering question</h2><p className="mb-5 text-sm text-slate-400">Specify the evidence you need and the conditions that make it relevant. Saved briefs remain reusable.</p><form className="space-y-4" onSubmit={event => { event.preventDefault(); const result = state.addBrief({ question: draft.question, alloy: draft.alloy, process: draft.process, method: draft.method, dataType: draft.dataType }); setErrors(result.errors); if (!result.errors.length) replace(briefDefaults); }}><Field label="Research question" value={draft.question} onChange={value => patch('question', value)} multiline required placeholder="Which measured melt-pool widths are reported for this alloy and process window?" /><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{(['alloy', 'process', 'method', 'dataType'] as const).map(key => <Field key={key} label={{ alloy: 'Material / alloy', process: 'Process', method: 'Measurement or simulation method', dataType: 'Required data type' }[key]} value={draft[key]} onChange={value => patch(key, value)} />)}</div><Notice messages={errors} /><button className={primaryClass} type="submit">Save brief and find sources</button></form></section>;
}
