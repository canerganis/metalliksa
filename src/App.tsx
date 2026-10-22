import React, { useState, useEffect, useMemo, lazy, Suspense } from 'react';
import { ArrowRight, Search } from 'lucide-react';
import { CONTEXT_AFTER_MODULE, MATURITY_BADGE_TITLE, MODULES, MODULE_PURPOSE, WORKSPACES, ModuleId, isModuleId, legacyRedirectHash, moduleFromHash, moduleHash, resolveModuleId } from './data/workspaces';
import { WorkspaceVisibility } from './components/WorkspaceVisibility';
import { ModuleBoundary } from './components/ModuleBoundary';
import { useMaterialSpecimenStore } from './store/useMaterialSpecimenStore';
import { AirgapBanner } from './components/AirgapBanner';
import { pythonComputationService, PythonEngineStatus } from './services/pythonComputationService';
import { startMaterialContextBridge, useMaterialContextBridgeStore } from './services/materialContextBridge';
import { startEngineeringJobPersistence } from './store/useLpbfEngineeringStore';
import { ModuleEvidenceDisclosure } from './components/sdk/EvidenceBadge';
import { SilentBoundary } from './components/SilentBoundary';
import { ModuleNav } from './components/ModuleNav';
import { formatExactNumber } from './utils/numberFormat';
import { LpbfDefaultsNote } from './components/LpbfDefaultsNote';
import { canOpenPalette, isApplePlatform, paletteShortcutKeys, paletteShortcutLabel, useCommandPaletteShortcut, visibleModalOpen, type PaletteGate } from './hooks/useCommandPaletteShortcut';
import { isBootOverlayOpen, setBootOverlayOpen } from './utils/bootOverlay';
import { startEngineReadyPoll } from './utils/engineStatusPoll';
// Boot screen in its own chunk (keeps the index chunk in budget). The request starts as soon as this
// module evaluates, in parallel with React start-up; until it arrives an opaque cover hides the shell.
const bootChunk = import('./components/BootSequence');
// A failed chunk is handled by SilentBoundary at render (shell shows, with no boot screen to keep the palette closed).
bootChunk.catch(() => setBootOverlayOpen(false));
const BootSequence = lazy(() => bootChunk.then(m => ({ default: m.BootSequence })));
// Scientific context panel (mostly explanatory text) in its own chunk, requested at module evaluation like the
// boot chunk; it arrives while the boot overlay still covers the shell. Keeps the index chunk within budget.
const contextChunk = import('./components/ScientificContextPanel');
contextChunk.catch(() => undefined); // A failed chunk is handled by SilentBoundary at render.
const ScientificContextPanel = lazy(() => contextChunk.then(m => ({ default: m.ScientificContextPanel })));
// Own chunk: the strip sits at the end of the page, so it does not need to be in the index chunk.
const TelemetryStrip = lazy(() => import('./components/TelemetryStrip').then(m => ({ default: m.TelemetryStrip })));
// Own chunk: the engine availability dialog is opened on demand from the header status button. A factory,
// because React.lazy caches a rejected import: a retry after a failed chunk needs a new lazy component.
const loadEngineStatusDialog = () => lazy(() => import('./components/EngineStatusDialog').then(m => ({ default: m.EngineStatusDialog })));
// Own chunk: the command palette (Ctrl/Cmd+K or the header button) and its stylesheet load on first open. A factory
// for the same reason as the engine dialog: Retry after a failed chunk needs a fresh lazy component.
const loadCommandPalette = () => lazy(() => import('./components/CommandPaletteChunk').then(m => ({ default: m.CommandPalette })));
const APPLE = isApplePlatform(typeof navigator === 'undefined' ? '' : navigator.platform);
const SHORTCUT_LABEL = paletteShortcutLabel(APPLE);
const SHORTCUT_KEYS = paletteShortcutKeys(APPLE);
// Own chunk (with its stylesheet): the start page shown without a module link or from 'Overview'.
const Atrium = lazy(() => import('./components/Atrium').then(m => ({ default: m.Atrium })));
const EvidenceWorkspace = lazy(() => import('./components/EvidenceWorkspace').then(m => ({ default: m.EvidenceWorkspace })));
const ResearchIntegrationPanel = lazy(() => import('./components/ResearchIntegrationPanel').then(m => ({ default: m.ResearchIntegrationPanel })));
const MaterialsDatabaseView = lazy(() => import("./components/MaterialsDatabaseView").then(m => ({ default: m.MaterialsDatabaseView })));
const LpbfEngineeringWorkspace = lazy(() => import("./components/LpbfEngineeringWorkspace").then(m => ({ default: m.LpbfEngineeringWorkspace })));
const LpbfBayesianOptimizerLab = lazy(() => import("./components/LpbfBayesianOptimizerLab").then(m => ({ default: m.LpbfBayesianOptimizerLab })));
const SolidificationMicrostructureLab = lazy(() => import("./components/SolidificationMicrostructureLab").then(m => ({ default: m.SolidificationMicrostructureLab })));  // Phase 8
const ExperimentalValidationLab = lazy(() => import("./components/ExperimentalValidationLab").then(m => ({ default: m.ExperimentalValidationLab }))); // Phase 10
const KeyholeRaytracingLab = lazy(() => import("./components/KeyholeRaytracingLab").then(m => ({ default: m.KeyholeRaytracingLab }))); // Phase 26
const LpbfDatasetComparisonLab = lazy(() => import("./components/LpbfDatasetComparisonLab").then(m => ({ default: m.LpbfDatasetComparisonLab })));
const LpbfCalibrationScorecardLab = lazy(() => import("./components/LpbfCalibrationScorecardLab").then(m => ({ default: m.LpbfCalibrationScorecardLab })));

const AdvancedResearchHub = lazy(() => import("./components/AdvancedResearchHub").then(m => ({ default: m.AdvancedResearchHub })));
const PhaseDiagramViewer = lazy(() => import("./components/PhaseDiagramViewer").then(m => ({ default: m.PhaseDiagramViewer })));

export type NavSubTab = ModuleId;
export type DisciplineHubId = typeof WORKSPACES[number]['id'];

// The start page: no hash, "#", "#/" or "#/home". Any other hash is a module link (unknown -> LPBF).
// Modules whose data are not about the shared specimen (the shared-material block and the context panel would describe the wrong material).
export const MODULES_WITHOUT_SHARED_SPECIMEN: ReadonlySet<string> = new Set(['lpbf-dataset-comparison', 'lpbf-calibration-scorecard']);
const isHome = (hash: string) => /^(#\/?(home)?)?$/.test(hash);
const startsHome = () => isHome(window.location.hash) && !/[?&]lpbf(Stage|SubTab)=/.test(window.location.search);

// A merged module's old link is rewritten in place to the module and tab that replaced it.
function rewriteLegacyHash(): void {
  const target = legacyRedirectHash(window.location.hash);
  if (!target) return;
  try { window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}${target}`); } catch { /* Navigation still resolves the module. */ }
}

function initialTab(): ModuleId {
  rewriteLegacyHash(); demoRedirectHidden();
  const linked = moduleFromHash(window.location.hash);
  if (linked) return linked;
  const parameters = new URLSearchParams(window.location.search);
  if (parameters.has('lpbfStage') || parameters.has('lpbfSubTab')) return '3d-distortion-lab';
  // Explicit unknown routes go to LPBF instead of silently restoring another workspace. The start page
  // (#/home) is not unknown: it keeps the remembered module as its Continue target.
  if (window.location.hash && !isHome(window.location.hash)) return '3d-distortion-lab';
  try { const saved = demoAllowedModule(resolveModuleId(localStorage.getItem('metallixa.workspace.module'))); if (saved) return saved; } catch { /* Optional storage. */ }
  return '3d-distortion-lab';
}

export default function App() {
  const [activeTab, setActiveTab] = useState<ModuleId>(initialTab);
  const [home, setHome] = useState(startsHome);
  const [visited, setVisited] = useState<ModuleId[]>(() => home ? [] : [initialTab()]);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [moduleSearch, setModuleSearch] = useState('');
  const [showStatus, setShowStatus] = useState(false);
  const [status, setStatus] = useState<PythonEngineStatus | null>(null);
  const [checking, setChecking] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [dialogLoad, setDialogLoad] = useState(0);
  const EngineStatusDialog = useMemo(loadEngineStatusDialog, [dialogLoad]);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteLoad, setPaletteLoad] = useState(0);
  const CommandPalette = useMemo(loadCommandPalette, [paletteLoad]);
  const retryPalette = () => setPaletteLoad(n => n + 1);
  // The palette opens only when no other modal is up or requested: the engine dialog (also while its chunk loads),
  // the boot overlay, or a module's own dialog on screen.
  const paletteGate = (): PaletteGate => ({ paletteOpen, engineDialogOpen: showStatus, bootOverlayOpen: isBootOverlayOpen(), moduleModalOpen: visibleModalOpen() });
  const openPalette = () => { if (canOpenPalette(paletteGate())) setPaletteOpen(true); };
  useCommandPaletteShortcut(APPLE, paletteGate, () => setPaletteOpen(true));
  // Chunk failure: Retry remounts the boundary with a fresh lazy import; Close also resets it so the next open retries.
  // Chrome keeps a failed module fetch for the page's lifetime (browser-checked: Retry did not refetch), so the
  // alert also offers a reload, as ModuleBoundary does.
  const retryDialog = () => setDialogLoad(n => n + 1);
  const closeDialog = () => { setShowStatus(false); retryDialog(); };
  const specimen = useMaterialSpecimenStore(s => s.activeSpecimen);
  const materialTransfer = useMaterialContextBridgeStore();
  const activeModule = MODULES.find(m => m.id === activeTab)!;
  const activeWorkspace = WORKSPACES.find(w => w.id === activeModule.workspace)!;
  const filtered = demoVisibleModules(MODULES).filter(m => `${m.label} ${m.description} ${m.workspace}`.toLowerCase().includes(moduleSearch.toLowerCase()));
  // Hash routing owns location.hash, so the skip link moves focus itself instead of following "#main-content".
  function skipToMain(event: React.MouseEvent) {
    event.preventDefault();
    document.getElementById('main-content')?.focus();
  }

  function activate(id: ModuleId) {
    setActiveTab(id); demoHiddenNoticePending = false;
    setHome(false);
    setVisited(current => current.includes(id) ? current : [...current, id]);
    setNavigationOpen(false);
  }
  function navigate(id: string) {
    if (!isModuleId(id) || !demoAllowedModule(id)) return;
    activate(id);
    if (window.location.hash !== moduleHash(id)) window.location.hash = moduleHash(id);
  }
  function showHome() { setHome(true); setNavigationOpen(false); }
  function goHome() {
    showHome();
    if (window.location.hash !== '#/home') window.location.hash = '#/home';
  }
  async function refreshStatus(force = true) {
    setChecking(true); setStatusError(null);
    try { setStatus(await pythonComputationService.checkEngineStatus(force)); }
    catch (error) { setStatus(null); setStatusError(error instanceof Error ? error.message : 'Engine status unavailable.'); }
    finally { setChecking(false); }
  }
  useEffect(() => {
    void refreshStatus(false);
    const onHash = () => {
      demoRedirectHidden(); if (isHome(window.location.hash)) { showHome(); return; }
      // Legacy id: rewrite the hash first, then re-announce it so a mounted module (its tab) follows; activate runs twice on purpose (idempotent).
      if (legacyRedirectHash(window.location.hash)) {
        rewriteLegacyHash();
        activate(moduleFromHash(window.location.hash) ?? '3d-distortion-lab');
        window.dispatchEvent(new HashChangeEvent('hashchange'));
        return;
      }
      activate(moduleFromHash(window.location.hash) ?? '3d-distortion-lab');
    };
    const onNavigate = (event: Event) => {
      const id = (event as CustomEvent<{ tabId?: string }>).detail?.tabId;
      if (id) navigate(id);
    };
    window.addEventListener('hashchange', onHash);
    window.addEventListener('metallix-navigate-tab', onNavigate);
    return () => { window.removeEventListener('hashchange', onHash); window.removeEventListener('metallix-navigate-tab', onNavigate); };
  }, []);
  // The daemon can finish starting after the first status check: keep asking (bounded, paused while the tab is hidden) until it is online.
  const engineOnline = status?.online === true;
  const firstCheckDone = status !== null || statusError !== null;
  useEffect(() => {
    if (engineOnline || checking || !firstCheckDone) return;
    return startEngineReadyPoll({
      check: () => pythonComputationService.checkEngineStatus(true),
      onStatus: (next) => { setStatus(next); setStatusError(null); },
      setTimer: (fn, ms) => window.setTimeout(fn, ms),
      clearTimer: (handle) => window.clearTimeout(handle as number),
      isHidden: () => document.hidden,
      onVisibilityChange: (cb) => { document.addEventListener('visibilitychange', cb); return () => document.removeEventListener('visibilitychange', cb); },
    });
  }, [engineOnline, checking, firstCheckDone]);
  useEffect(() => startMaterialContextBridge(), []);
  useEffect(() => startEngineeringJobPersistence(), []);
  useEffect(() => {
    try { localStorage.setItem('metallixa.workspace.module', activeTab); } catch { /* Navigation still works. */ }
  }, [activeTab]);

  function renderModule(id: ModuleId) {
    switch (id) {
      case '3d-distortion-lab': return <LpbfEngineeringWorkspace />;
      case 'lpbf-optimizer': return <LpbfBayesianOptimizerLab />;
      case 'solidification-microstructure': return <SolidificationMicrostructureLab />;  // Phase 8
      case 'experimental-validation': return <ExperimentalValidationLab />; // Phase 10
      case 'keyhole-raytracing': return <KeyholeRaytracingLab />; // Phase 26
      case 'lpbf-dataset-comparison': return <LpbfDatasetComparisonLab />;
      case 'lpbf-calibration-scorecard': return <LpbfCalibrationScorecardLab />;
      case 'research-hub': return <AdvancedResearchHub />;
      case 'experimental-data': return <EvidenceWorkspace mode="experimental" />;
      case 'traceability': return <EvidenceWorkspace mode="traceability" />;
      case 'database': return <MaterialsDatabaseView onNavigate={navigate} />;
      case 'phase-diagram': return <PhaseDiagramViewer />;
    }
  }

  // The skip link follows the boot overlay in the DOM: when the overlay closes, the browser's Tab starting point is
  // where the overlay was, so the next Tab lands on the skip link (it is the first focusable element left on the page).
  return <><SilentBoundary><Suspense fallback={<div className="mk-boot-cover" aria-hidden="true" />}><BootSequence /></Suspense></SilentBoundary><a href="#main-content" className="mk-skip-link" onClick={skipToMain}>Skip to main content</a><div className="mk-shell min-h-screen text-slate-100 selection:bg-sky-500/25">
    <div className="mk-grid-overlay" aria-hidden="true" />
    <div className="mk-scanline" aria-hidden="true" />
    <AirgapBanner />
    {IS_STATIC_DEMO && <DemoBanner />}
    <header className="mk-header sticky top-0 z-40 border-b px-4 lg:px-6 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3"><button aria-label="Toggle workspace navigation" aria-expanded={navigationOpen} onClick={() => setNavigationOpen(v => !v)} className="lg:hidden mk-status px-3 py-2 text-xs">Modules</button><div className="contents"><div className="mk-brand-mark" role="img" aria-label="Metalliksa logo"><span className="mk-brand-laser" aria-hidden="true" /></div></div><div><h1 className="mk-brand-title">METALLIKSA</h1><p className="mk-brand-tag hidden lg:block">Research engineering workstation</p></div></div>
        <div className="flex items-center gap-2 sm:gap-3"><button type="button" aria-haspopup="dialog" aria-keyshortcuts={SHORTCUT_KEYS} onClick={openPalette} className="mk-status inline-flex items-center gap-2 px-3 py-2 text-xs"><Search className="h-3.5 w-3.5" aria-hidden="true"/><span className="sr-only sm:not-sr-only">Search modules</span><kbd aria-hidden="true" className="hidden sm:inline font-mono text-[10px]">{SHORTCUT_LABEL}</kbd></button><button type="button" onClick={() => void useGuidedDemoStore.getState().start()} className="mk-status hidden px-3 py-2 text-xs lg:inline-block">Guided tour</button><span className="mk-hud-chip hidden xl:inline">Runs on this computer</span><button onClick={() => { setPaletteOpen(false); setShowStatus(true); }} className="mk-status px-3 py-2 text-xs"><span className={`mr-2 inline-block h-1.5 w-1.5 rounded-full ${checking ? 'bg-amber-500 animate-pulse' : status?.online ? 'bg-emerald-500' : 'bg-amber-500'}`}/>{IS_STATIC_DEMO ? 'Static snapshot, no engine' : checking ? 'Checking…' : status?.online ? 'Calculation engine ready' : 'Calculation engine unavailable'}</button></div>
      </div>
    </header>
    <div className="flex flex-col lg:flex-row">
      <aside className={`${navigationOpen ? 'block' : 'hidden'}${home ? ' is-home' : ''} mk-sidebar lg:block lg:w-60 xl:w-64 shrink-0 border-b lg:border-b-0 lg:border-r p-4 lg:sticky lg:top-[var(--mk-header-h)] lg:h-[calc(100vh_-_var(--mk-header-h))] overflow-y-auto`}>
        <div className="mb-5 flex items-center justify-between"><div><p className="mk-side-kicker">Navigation</p><p className="mt-1 text-sm text-slate-200">Engineering surfaces</p></div><span className="mk-count-badge font-mono text-[10px]">{String(demoVisibleModules(MODULES).length).padStart(2, '0')}</span></div><label htmlFor="module-search" className="mb-2 block text-xs text-slate-400">Find a module</label><div className="relative mb-6"><Search className="absolute left-3 top-3 w-4 h-4 text-slate-500"/><input id="module-search" type="search" value={moduleSearch} onChange={e => setModuleSearch(e.target.value)} placeholder="Materials, evidence…" className="aero-input w-full rounded-xl border pl-9 pr-2 py-2.5 text-sm"/></div>
        <button type="button" onClick={goHome} aria-current={home ? 'page' : undefined} className={`mk-nav-item mk-nav-home mb-5${home ? ' is-active' : ''}`}>Overview</button>
        <ModuleNav home={home} modules={filtered} activeTab={activeTab} activeWorkspace={activeWorkspace.id} onNavigate={navigate} />
      </aside>
      <main id="main-content" tabIndex={-1} className="flex-1 min-w-0 p-4 sm:p-6 xl:p-8">
        <SilentBoundary><Suspense fallback={null}><GuidedDemo home={home} engine={status} engineChecking={checking || (status === null && statusError === null)} /></Suspense></SilentBoundary>
        {home && <DemoHiddenNote />}
        {home ? <ModuleBoundary label="Overview"><Suspense fallback={<div role="status" className="mk-loading">Loading overview…</div>}><Atrium continueId={activeTab} engine={status} engineChecking={checking || (status === null && statusError === null)} shortcutLabel={SHORTCUT_LABEL} onNavigate={navigate} onSearch={openPalette} /></Suspense></ModuleBoundary> : <>
        {/* Laser wipe on entering a module (ornament, transform only, once per navigation). */}
        <div key={'wipe-' + activeTab} className="mk-wipe" aria-hidden="true" />
        <div key={activeTab} className="mk-content-header mb-6 border-b pb-6 pt-1"><p className="mk-kicker mb-3">{activeWorkspace.label}</p><h2>{activeModule.label}</h2><div className="mt-3 flex flex-wrap items-center gap-2"><span title={MATURITY_BADGE_TITLE} className={`mk-scope-badge ${activeModule.scope === 'Preview' ? 'is-preview' : ''}`}>{activeModule.scope}</span></div><p className="mt-4 max-w-3xl text-[15px] leading-7 text-slate-300">{MODULE_PURPOSE[activeModule.id]}</p><ModuleEvidenceDisclosure moduleId={activeModule.id} detail={activeModule.description} /></div>
        {!MODULES_WITHOUT_SHARED_SPECIMEN.has(activeTab) && <details className="mk-plate mb-5 px-4 py-3 text-xs">
          <summary className="cursor-pointer text-slate-300">Shared material · <span className="text-sky-200">{specimen.name}</span> · {formatExactNumber(specimen.lpbf.laserPower_W)} W / {formatExactNumber(specimen.lpbf.scanSpeed_mms)} mm/s <span className="ml-2 text-slate-500">Material and settings in use</span></summary>
          <div className="mt-3 grid gap-3 md:grid-cols-2 text-slate-400"><div>Hatch {specimen.lpbf.hatch_um} µm · Layer {specimen.lpbf.layer_um} µm · Beam {specimen.lpbf.beamDiameter_um} µm{specimen.lpbf.defaultsApplied?.includes('beamDiameter_um') ? ' (unsourced default)' : ''} · Preheat {specimen.lpbf.preheatTemp_C} °C. Material and process are shared across LPBF stages. <LpbfDefaultsNote lpbf={specimen.lpbf} className="block text-amber-300" /></div><p>Module status: Production, Research, Preview or Unresolved. Result evidence: Measured, Validated simulation, Calibrated simulation, Literature estimate, Screening only, Unresolved. Energy balance, mesh convergence and comparison with experiments are three separate checks.</p><p>Visited modules retain their local view during navigation. Specimen and registry persist in this browser. Meshes and most specialist views remain session-only.</p></div>
        </details>}
        {materialTransfer.message && <p role={materialTransfer.error ? 'alert' : 'status'} className={`mb-4 rounded-lg border px-4 py-3 text-xs ${materialTransfer.error ? 'border-amber-500/30 text-amber-200' : 'border-cyan-500/20 text-cyan-200'}`}>{materialTransfer.message}</p>}
        {!MODULES_WITHOUT_SHARED_SPECIMEN.has(activeTab) && !CONTEXT_AFTER_MODULE.has(activeTab) && <SilentBoundary><Suspense fallback={null}><ScientificContextPanel moduleId={activeTab} specimen={specimen} /></Suspense></SilentBoundary>}
        </>}
        {visited.map(id => <div key={id} hidden={home || id !== activeTab} data-module={id}><WorkspaceVisibility visible={!home && id === activeTab}>
          <ModuleBoundary label={MODULES.find(m => m.id === id)!.label}>
            <Suspense fallback={<div role="status" className="mk-loading">Loading engineering module…</div>}>
              {(id === 'database' || (id === '3d-distortion-lab' && !IS_STATIC_DEMO)) && <ResearchIntegrationPanel targetModule={id === 'database' ? 'materials-db' : 'lpbf-solver'} />}
              {renderModule(id)}
            </Suspense>
          </ModuleBoundary>
        </WorkspaceVisibility></div>)}
        {!home && CONTEXT_AFTER_MODULE.has(activeTab) && <div className="mt-8"><SilentBoundary><Suspense fallback={null}><ScientificContextPanel moduleId={activeTab} specimen={specimen} collapsed /></Suspense></SilentBoundary></div>}
        {!home && demoAllowedModule(activeModule.next) && <div className="mt-8 border-t border-slate-800 pt-4 flex flex-wrap justify-between items-center gap-3"><p className="text-xs text-slate-500">Review inputs, source applicability and evidence before making an engineering decision.</p><button onClick={() => navigate(activeModule.next)} className="inline-flex gap-2 items-center text-sm text-sky-300 hover:text-sky-100">Next: {MODULES.find(m => m.id === activeModule.next)?.label}<ArrowRight className="h-4 w-4"/></button></div>}
      </main>
    </div>
    <SilentBoundary><Suspense fallback={null}><TelemetryStrip engine={status} engineChecking={checking || (status === null && statusError === null)} moduleCount={demoVisibleModules(MODULES).length} /></Suspense></SilentBoundary>
    {showStatus && IS_STATIC_DEMO && <DemoEngineNote onClose={() => setShowStatus(false)} />}
    {showStatus && !IS_STATIC_DEMO && <SilentBoundary key={dialogLoad} fallback={<div role="alert" className="fixed bottom-4 left-4 right-4 z-50 mx-auto max-w-md rounded-lg border border-amber-500/30 bg-slate-950 p-4 text-sm text-amber-200">Engine availability details could not be loaded. <button onClick={retryDialog} className="ml-2 underline">Retry</button> <button onClick={() => window.location.reload()} className="ml-2 underline">Reload application</button> <button onClick={closeDialog} className="ml-2 underline">Close</button></div>}><Suspense fallback={null}><EngineStatusDialog status={status} statusError={statusError} checking={checking} onClose={() => setShowStatus(false)} onRefresh={() => void refreshStatus()} /></Suspense></SilentBoundary>}
    {paletteOpen && <SilentBoundary key={paletteLoad} fallback={<div role="alert" className="fixed bottom-4 left-4 right-4 z-50 mx-auto max-w-md rounded-lg border border-amber-500/30 bg-slate-950 p-4 text-sm text-amber-200">Module search could not be loaded. <button onClick={retryPalette} className="ml-2 underline">Retry</button> <button onClick={() => window.location.reload()} className="ml-2 underline">Reload application</button> <button onClick={() => { setPaletteOpen(false); retryPalette(); }} className="ml-2 underline">Close</button></div>}><Suspense fallback={null}><CommandPalette activeTab={activeTab} onNavigate={navigate} onClose={() => setPaletteOpen(false)} /></Suspense></SilentBoundary>}
  </div></>;
}



// Own chunk (below the module-contract refs in renderModule so their line numbers stay put): first-run card and tour panel.
const GuidedDemo = lazy(() => import('./components/GuidedDemo').then(m => ({ default: m.GuidedDemo })));
import { useGuidedDemoStore } from './store/useGuidedDemoStore';

// Static demo gates (docs/DEMO_STATIC_DESIGN.md section 5). Every call is guarded by the compile-time IS_STATIC_DEMO
// constant, so a normal build drops them. They sit below renderModule so the module-contract line anchors stay put.
import { IS_STATIC_DEMO } from './demo/flag.ts';
import { hiddenModuleRedirect, visibleModules as visibleDemoModules } from './demo/demoGate.ts';
import { DemoRedirectNote } from './demo/demoNotes.tsx';
import { DemoBanner } from './demo/demoBanner.tsx';
import { DemoEngineNote } from './demo/demoNotes.tsx';
import { isDemoModule } from './demo/demoModules.ts';

let demoHiddenNoticePending = false;
/** A link to a module outside the demo allowlist is rewritten to the start page, before unknown hashes map to LPBF. */
function demoRedirectHidden(): void {
  if (!IS_STATIC_DEMO) return;
  const target = hiddenModuleRedirect(window.location.hash, isModuleId);
  if (!target) return;
  demoHiddenNoticePending = true;
  try { window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}${target}`); } catch { /* The hash check below still resolves home. */ }
}
function demoAllowedModule<T extends string | null>(id: T): T | null {
  return IS_STATIC_DEMO && id !== null && !isDemoModule(id) ? null : id;
}
function demoVisibleModules<T extends { readonly id: string }>(modules: readonly T[]): readonly T[] {
  return IS_STATIC_DEMO ? visibleDemoModules(modules) : modules;
}
function DemoHiddenNote() {
  return IS_STATIC_DEMO && demoHiddenNoticePending ? <DemoRedirectNote /> : null;
}
