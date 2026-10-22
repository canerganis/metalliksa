import React, { useState } from 'react';
import { MODULES, NAV_GROUPS, type ModuleId } from '../data/workspaces';
import { rovingIndex } from '../utils/rovingFocus';

/**
 * The single Tab stop: the entry focused last while `activeTab` was active, else the active module,
 * else the first visible module.
 */
export function navTabStop(modules: { id: string }[], focus: { key: string; tab: string }, activeTab: string): string | undefined {
  const shown = (key: string) => modules.some(m => m.id === key);
  return [focus.tab === activeTab ? focus.key : '', activeTab].find(shown) ?? modules[0]?.id;
}

/** Clears the remembered entry once the active module differs from the one it was focused under. */
export function syncNavFocus(focus: { key: string; tab: string }, activeTab: string): { key: string; tab: string } {
  return focus.tab === activeTab ? focus : { key: '', tab: activeTab };
}

/**
 * The sidebar groups (task order from NAV_GROUPS) holding the given modules. A module that is in no group
 * is shown under "More" so a new registry entry can never disappear from the navigation.
 */
export function navGroups<T extends { id: string }>(modules: readonly T[]): { id: string; label: string; entries: T[] }[] {
  const grouped = new Set<string>(NAV_GROUPS.flatMap(group => group.modules));
  const groups = NAV_GROUPS.map(group => ({ id: group.id, label: group.label, entries: group.modules.flatMap(id => modules.filter(m => m.id === id)) }));
  groups.push({ id: 'more', label: 'More', entries: modules.filter(m => !grouped.has(m.id)) });
  return groups.filter(group => group.entries.length > 0);
}

/**
 * Sidebar module navigation as one Tab stop (roving tabindex). Its own component so that moving focus
 * between entries re-renders only the navigation, not App and the mounted module views. Every module is
 * always listed, grouped by task.
 */
export function ModuleNav({ home = false, modules, activeTab, onNavigate }: {
  home?: boolean; modules: (typeof MODULES)[number][]; activeTab: ModuleId; activeWorkspace?: string; onNavigate: (id: string) => void;
}) {
  // The remembered entry is tied to the active module it was focused under: any navigation (hash change,
  // back button, Next link, navigate event) moves the Tab stop back to the aria-current entry.
  const [focus, setFocus] = useState<{ key: string; tab: string }>({ key: '', tab: activeTab });
  // Forget the remembered entry as soon as the active module changes, so going A -> B -> A (back button)
  // does not revive an entry remembered under A. Render-time adjustment: re-renders only this component.
  const synced = syncNavFocus(focus, activeTab);
  if (synced !== focus) setFocus(synced);
  const stop = navTabStop(modules, synced, activeTab);
  const item = (key: string, described = '') => ({ tabIndex: key === stop ? 0 : -1, onFocus: () => setFocus({ key, tab: activeTab }), 'aria-describedby': 'module-nav-hint' + described });
  function onKey(event: React.KeyboardEvent<HTMLElement>) {
    if (event.ctrlKey || event.altKey || event.metaKey) return;
    // Every button in the navigation is a module entry.
    const items = Array.from(event.currentTarget.querySelectorAll('button'));
    const next = rovingIndex(items.length, items.indexOf(document.activeElement as HTMLButtonElement), event.key);
    if (next === null) return;
    event.preventDefault();
    items[next].focus();
  }
  const entryButton = (module: (typeof MODULES)[number]) => (
    <button key={module.id} {...item(module.id, ' nav-desc-' + module.id)} aria-current={!home && activeTab === module.id ? 'page' : undefined} title={module.description} onClick={() => onNavigate(module.id)} className={`mk-nav-item${!home && activeTab === module.id ? ' is-active' : ''}`}>
      {module.label}
    </button>
  );
  return <nav aria-label="Engineering workspaces" onKeyDown={onKey}>
    <p id="module-nav-hint" className="mk-sr-only">Arrow keys move between modules.</p>
    {navGroups(modules).map(group => <div key={group.id} role="group" aria-labelledby={'module-nav-group-' + group.id} className="mb-6">
      <p id={'module-nav-group-' + group.id} className="mk-nav-ws">{group.label}</p>
      <div className="space-y-0.5">{group.entries.map(entryButton)}</div>
    </div>)}
    <div hidden>{modules.map(module => <span key={module.id} id={'nav-desc-' + module.id}>{module.description}</span>)}</div>
    {!modules.length && <p role="status" className="text-sm text-slate-400">No matching modules. Try a material, method or workflow name.</p>}
  </nav>;
}
