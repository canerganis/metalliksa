import React from 'react';
import { BookOpen, FlaskConical, ShieldCheck, SlidersHorizontal } from 'lucide-react';
import type { ActiveSpecimenState } from '../store/useMaterialSpecimenStore';
import type { ModuleId } from '../data/workspaces';
import { buildScientificContext, hasScientificContext } from '../utils/scientificContext';

// Styles: .mk-dossier* and .mk-hud in src/index.css. The limitation line keeps its own warm cell and is
// never faded, blurred or animated. With `collapsed` the whole block sits behind a native disclosure whose
// summary is the kicker and the title (all text unchanged, one click or Enter/Space away).
export function ScientificContextPanel({ moduleId, specimen, collapsed = false }: { moduleId: ModuleId; specimen: ActiveSpecimenState; collapsed?: boolean }) {
  if (!hasScientificContext(moduleId)) return null;
  const context = buildScientificContext(moduleId, specimen);
  const kicker = <p className="mk-kicker">Scientific context · interpretation</p>;
  const observation = <p className="mt-2 max-w-4xl text-[13px] leading-relaxed text-slate-300">{context.observation}</p>;
  const grid = <div className="mk-dossier-grid">
    <div className="mk-dossier-cell"><h3><FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />Mechanism</h3><p>{context.mechanism}</p></div>
    <div className="mk-dossier-cell"><h3><SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />What drives the result</h3><ul className="space-y-1">{context.variables.map(variable => <li key={variable}>· {variable}</li>)}</ul></div>
    <div className="mk-dossier-cell is-limit"><h3><ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />How to read it</h3><p>{context.interpretation}</p><p className="mk-dossier-limit">Limitation: {context.limitation}</p></div>
  </div>;
  if (collapsed) {
    return <section aria-labelledby="scientific-context-title" className="mk-dossier mk-hud" data-collapsed="true">
      <details>
        <summary className="cursor-pointer">{kicker}<h2 id="scientific-context-title" className="mt-1.5 text-lg font-light text-slate-200">{context.title}</h2></summary>
        <div className="mt-2">{observation}</div>
        {grid}
      </details>
    </section>;
  }
  return <section aria-labelledby="scientific-context-title" className="mk-dossier mk-hud">
    <div className="flex items-start gap-4">
      <div className="hidden sm:grid h-10 w-10 shrink-0 place-items-center rounded-full border border-slate-700 bg-[var(--mk-paper)] text-slate-300"><BookOpen className="h-4 w-4" aria-hidden="true" /></div>
      <div className="min-w-0 flex-1">{kicker}<h2 id="scientific-context-title" className="mt-1.5 text-lg font-light text-slate-200">{context.title}</h2>{observation}</div>
    </div>
    {grid}
  </section>;
}
