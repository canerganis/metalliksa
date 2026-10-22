import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { MODULES, WORKSPACES } from '../src/data/workspaces';
import { LISTED_CONTRACTS } from '../src/modules/registry';
import {
  FUZZY_SCORE_CAP, commitPaletteChoice, handlePaletteInputKey, isComposingKey, normalizeForSearch, paletteChoice, paletteKeyAction,
  rankPaletteEntries, scorePaletteEntry, subsequenceScore, type PaletteEffects, type PaletteEntry,
} from '../src/utils/commandPalette';
import {
  canOpenPalette, createShortcutListener, isApplePlatform, isPaletteShortcut, paletteShortcutDecision, paletteShortcutKeys,
  paletteShortcutLabel, visibleModalOpen, type PaletteGate,
} from '../src/hooks/useCommandPaletteShortcut';
import { isBootOverlayOpen, setBootOverlayOpen } from '../src/utils/bootOverlay';

// Phase 9 command palette: pure ranking over the registry-derived navigation list (MODULES).
const ENTRIES = MODULES.map(module => ({
  ...module,
  workspaceLabel: WORKSPACES.find(workspace => workspace.id === module.workspace)!.label,
}));
const ids = (query: string) => rankPaletteEntries(ENTRIES, query).map(entry => entry.id);
const entry = (label: string, extra: Partial<PaletteEntry> = {}): PaletteEntry =>
  ({ id: label.toLowerCase().replace(/\W+/g, '-'), label, description: '', scope: 'Research', workspaceLabel: 'W', ...extra });

test('the palette source list is the registry: every listed contract, in navigation order', () => {
  assert.deepEqual(ENTRIES.map(e => e.id), LISTED_CONTRACTS.map(contract => contract.id));
  assert.deepEqual(ids(''), MODULES.map(module => module.id), 'empty query = sidebar order, nothing dropped');
  assert.deepEqual(ids('   '), MODULES.map(module => module.id));
});

test('normalization folds case and diacritics', () => {
  assert.equal(normalizeForSearch('Alaşım İÇ Çelik'), 'alasim ic celik');
  assert.equal(normalizeForSearch('Résumé'), 'resume');
});

test('subsequence score: null when a character is missing, higher for consecutive and word-start runs', () => {
  assert.equal(subsequenceScore('keyhole ray tracing', 'kz'), null);
  assert.equal(subsequenceScore('abc', ''), 0);
  const tight = subsequenceScore('keyhole ray tracing', 'key')!;
  const loose = subsequenceScore('keyhole ray tracing', 'kye')!;
  assert.ok(tight > loose, `${tight} > ${loose}`);
  assert.ok(subsequenceScore('ray tracing', 'rt')! > subsequenceScore('rapid xt', 'rt')!, 'word starts outrank inner letters');
});

test('label prefix outranks word start, inner substring, id, workspace and description matches', () => {
  const list = [
    entry('Gamma description', { description: 'mentions keyhole here' }),
    entry('Alpha', { id: 'keyhole-id' }),
    entry('Inner xkeyhole'),
    entry('Ray keyhole'),
    entry('Keyhole first'),
    entry('Beta', { workspaceLabel: 'Keyhole workspace' }),
  ];
  assert.deepEqual(rankPaletteEntries(list, 'keyhole').map(e => e.label),
    ['Keyhole first', 'Ray keyhole', 'Inner xkeyhole', 'Alpha', 'Beta', 'Gamma description']);
});

test('every token must match (AND); scattered letters match the label only, ranked below exact matches', () => {
  assert.equal(ids('ray tracing')[0], 'keyhole-raytracing');
  assert.ok(ids('ray tracing').every(id => scorePaletteEntry(ENTRIES.find(e => e.id === id)!, 'tracing') !== null));
  assert.equal(ids('kyhl')[0], 'keyhole-raytracing', 'fuzzy subsequence on the label');
  assert.equal(scorePaletteEntry(entry('Keyhole'), 'kyhl')! < scorePaletteEntry(entry('Other', { description: 'kyhl' }), 'kyhl')!, true);
  assert.deepEqual(ids('zzqqxx'), []);
  assert.deepEqual(ids('keyhole zzqqxx'), [], 'one unmatched token removes the entry');
});

test('real registry queries: label, id and workspace hits', () => {
  assert.equal(ids('keyhole')[0], 'keyhole-raytracing');
  assert.equal(ids('calphad')[0], 'phase-diagram');
  const evidence = ids('evidence & records');
  const inEvidence = MODULES.filter(module => module.workspace === 'evidence').map(module => module.id);
  for (const id of inEvidence) assert.ok(evidence.includes(id), `${id} found by its workspace name`);
  assert.ok(ids('preview').length >= MODULES.filter(module => module.scope === 'Preview').length, 'scope is searchable');
});

test('a single letter matches only word starts in labels (not id, workspace, maturity, description or inner letters)', () => {
  const list = [
    entry('Alpha', { description: 'q in description', id: 'q-id', workspaceLabel: 'Q workspace', scope: 'Q' }),
    entry('Quench'), entry('Big Quartz'), entry('Aqua'),
  ];
  assert.deepEqual(rankPaletteEntries(list, 'q').map(e => e.label), ['Quench', 'Big Quartz']);
  assert.equal(rankPaletteEntries([entry('Keyhole')], 'y').length, 0, 'an inner letter is not enough');
  assert.equal(rankPaletteEntries([entry('Kxxxxe')], 'ke').length, 1, 'two-letter subsequence counts');
});

test('real registry: one letter never lists every module; each hit has a label word starting with it', () => {
  for (const letter of 'abcdefghijklmnopqrstuvwxyz') {
    const hits = ids(letter);
    assert.ok(hits.length < MODULES.length, `"${letter}" lists ${hits.length} of ${MODULES.length}`);
    for (const id of hits) {
      const label = normalizeForSearch(ENTRIES.find(e => e.id === id)!.label);
      assert.ok(label.split(/[^a-z0-9]+/).some(word => word.startsWith(letter)), `"${letter}" -> ${id}`);
    }
  }
  // The review's measured cases: e, r and i used to match all 37 through workspace and maturity names.
  for (const letter of ['e', 'r', 'i', 'İ', 'ı']) assert.ok(ids(letter).length < MODULES.length, letter);
  assert.deepEqual(ids('k'), ['keyhole-raytracing'], 'Keyhole Laser Absorption (prefix)');
  assert.ok(ids('re').length > ids('r').length, 'two characters reach id, workspace, maturity and description');
});

test('a later word-start occurrence counts as a word start', () => {
  assert.equal(scorePaletteEntry(entry('Axkey key'), 'key'), 100);
  assert.equal(scorePaletteEntry(entry('Axkey'), 'key'), 80);
});

test('scattered matches are capped below every exact field match', () => {
  const long = entry('Abcdefghijklmnopqrstuvwxyz');
  const raw = subsequenceScore(normalizeForSearch(long.label), 'acdefghij')!;
  assert.ok(raw > FUZZY_SCORE_CAP, `uncapped ${raw}`);
  assert.equal(scorePaletteEntry(long, 'acdefghij'), FUZZY_SCORE_CAP);
  assert.ok(FUZZY_SCORE_CAP < 20, 'below a description match (20)');
});

test('punctuation and symbols separate tokens; a query of only symbols lists everything', () => {
  assert.deepEqual(ids('ebsd/ct'), ids('ebsd ct'));
  assert.equal(ids('ray-tracing')[0], 'keyhole-raytracing');
  assert.deepEqual(ids('&'), MODULES.map(module => module.id));
  assert.deepEqual(ids('кейхол'), [], 'letters outside the labels match nothing');
});

test('normalization uses visible escapes and folds the dotted and dotless i', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/utils/commandPalette.ts'), 'utf8');
  assert.match(source, /\/\[\\u0300-\\u036f\]\/g/);
  assert.match(source, /\/\\u0131\/g/);
  assert.doesNotMatch(source, /[\u0300-\u036f\u0131]/, 'no invisible combining or dotless characters in the source');
  assert.equal(normalizeForSearch('İı'), 'ii');
});

test('ties keep the input (registry) order', () => {
  const list = [entry('Lab one'), entry('Lab two'), entry('Lab three')];
  assert.deepEqual(rankPaletteEntries(list, 'lab').map(e => e.label), ['Lab one', 'Lab two', 'Lab three']);
});

test('keys: arrows wrap, Home/End jump, Enter chooses the active result, other keys stay with the field', () => {
  const plain = (key: string) => ({ key, altKey: false, ctrlKey: false, metaKey: false });
  assert.deepEqual(paletteKeyAction(plain('ArrowDown'), 3, 0), { type: 'move', index: 1 });
  assert.deepEqual(paletteKeyAction(plain('ArrowDown'), 3, 2), { type: 'move', index: 0 });
  assert.deepEqual(paletteKeyAction(plain('ArrowUp'), 3, 0), { type: 'move', index: 2 });
  assert.deepEqual(paletteKeyAction(plain('Home'), 3, 2), { type: 'move', index: 0 });
  assert.deepEqual(paletteKeyAction(plain('End'), 3, 0), { type: 'move', index: 2 });
  assert.deepEqual(paletteKeyAction(plain('Enter'), 3, 1), { type: 'choose', index: 1 });
  assert.equal(paletteKeyAction(plain('Enter'), 0, -1), null, 'Enter with no results does nothing');
  assert.equal(paletteKeyAction(plain('ArrowDown'), 0, -1), null);
  assert.equal(paletteKeyAction(plain('a'), 3, 0), null);
  assert.equal(paletteKeyAction(plain('Escape'), 3, 0), null, 'Escape belongs to AccessibleModal');
  assert.equal(paletteKeyAction({ ...plain('ArrowDown'), altKey: true }, 3, 0), null);
});

const shortcutKey = (k: string, mods: Partial<{ code: string; ctrlKey: boolean; metaKey: boolean; altKey: boolean; shiftKey: boolean; isComposing: boolean; keyCode: number }> = {}) =>
  ({ key: k, ctrlKey: false, metaKey: false, altKey: false, shiftKey: false, ...mods });

test('shortcut: Cmd+K on Apple platforms, Ctrl+K elsewhere; K by key or physical code; never during IME', () => {
  const MAC = true, PC = false;
  assert.ok(isPaletteShortcut(shortcutKey('k', { metaKey: true }), MAC));
  assert.ok(!isPaletteShortcut(shortcutKey('k', { ctrlKey: true }), MAC), 'macOS Ctrl+K stays "delete to end of line"');
  assert.ok(isPaletteShortcut(shortcutKey('k', { ctrlKey: true }), PC));
  assert.ok(!isPaletteShortcut(shortcutKey('k', { metaKey: true }), PC), 'Windows key + K is not the palette');
  assert.ok(!isPaletteShortcut(shortcutKey('k', { ctrlKey: true, metaKey: true }), PC));
  assert.ok(isPaletteShortcut(shortcutKey('K', { ctrlKey: true }), PC), 'Caps Lock');
  assert.ok(isPaletteShortcut(shortcutKey('л', { code: 'KeyK', ctrlKey: true }), PC), 'Russian layout: physical K');
  assert.ok(isPaletteShortcut(shortcutKey('κ', { code: 'KeyK', metaKey: true }), MAC), 'Greek layout on a Mac');
  assert.ok(!isPaletteShortcut(shortcutKey('k'), PC));
  assert.ok(!isPaletteShortcut(shortcutKey('k', { ctrlKey: true, shiftKey: true }), PC));
  assert.ok(!isPaletteShortcut(shortcutKey('k', { ctrlKey: true, altKey: true }), PC), 'AltGr');
  assert.ok(!isPaletteShortcut(shortcutKey('j', { ctrlKey: true, code: 'KeyJ' }), PC));
  assert.ok(!isPaletteShortcut(shortcutKey('k', { ctrlKey: true, isComposing: true }), PC));
  assert.ok(!isPaletteShortcut(shortcutKey('k', { ctrlKey: true, keyCode: 229 }), PC));
  for (const platform of ['MacIntel', 'iPhone', 'iPad']) assert.ok(isApplePlatform(platform), platform);
  for (const platform of ['Win32', 'Linux x86_64', '']) assert.ok(!isApplePlatform(platform), platform);
  assert.equal(paletteShortcutLabel(MAC), '⌘K');
  assert.equal(paletteShortcutLabel(PC), 'Ctrl K');
  assert.equal(paletteShortcutKeys(MAC), 'Meta+K');
  assert.equal(paletteShortcutKeys(PC), 'Control+K');
});

const CLOSED: PaletteGate = { paletteOpen: false, engineDialogOpen: false, bootOverlayOpen: false, moduleModalOpen: false };

test('gate: the palette opens only when no other modal is up or requested; when open, the shortcut is swallowed', () => {
  assert.equal(paletteShortcutDecision(CLOSED), 'open');
  assert.ok(canOpenPalette(CLOSED));
  assert.equal(paletteShortcutDecision({ ...CLOSED, paletteOpen: true }), 'swallow', 'focus on the field or the Close button');
  assert.equal(paletteShortcutDecision({ ...CLOSED, engineDialogOpen: true }), 'ignore', 'engine dialog open or its chunk still loading (no dialog in the DOM yet)');
  assert.equal(paletteShortcutDecision({ ...CLOSED, bootOverlayOpen: true }), 'ignore', 'boot overlay or its cover');
  assert.equal(paletteShortcutDecision({ ...CLOSED, moduleModalOpen: true }), 'ignore');
  for (const blocked of ['paletteOpen', 'engineDialogOpen', 'bootOverlayOpen', 'moduleModalOpen'] as const) {
    assert.ok(!canOpenPalette({ ...CLOSED, [blocked]: true }), `header button blocked by ${blocked}`);
  }
});

test('listener: opens or swallows with preventDefault, ignores otherwise; reads the latest shell state', () => {
  let gate: PaletteGate = CLOSED;
  let opened = 0;
  const listener = createShortcutListener(false, () => ({ gate: () => gate, open: () => { opened += 1; } }));
  const press = (mods: Parameters<typeof shortcutKey>[1], defaultPrevented = false) => {
    let prevented = false;
    listener({ ...shortcutKey('k', mods), defaultPrevented, preventDefault: () => { prevented = true; } });
    return prevented;
  };
  assert.equal(press({ ctrlKey: true }), true);
  assert.equal(opened, 1);
  gate = { ...CLOSED, paletteOpen: true };
  assert.equal(press({ ctrlKey: true }), true, 'swallowed inside the open palette');
  assert.equal(opened, 1, 'not opened twice');
  gate = { ...CLOSED, engineDialogOpen: true };
  assert.equal(press({ ctrlKey: true }), false, 'left to the browser');
  assert.equal(opened, 1);
  gate = CLOSED;
  assert.equal(press({ ctrlKey: true }, true), false, 'a module that handled the key keeps it');
  assert.equal(press({ metaKey: true }), false, 'not the shortcut on this platform');
  assert.equal(press({ ctrlKey: true, isComposing: true }), false);
  assert.equal(opened, 1);
});

test('visibleModalOpen: aria-modal dialogs inside a hidden module view do not count', () => {
  const dialog = (hiddenAncestor: boolean) => ({ closest: (selector: string) => (selector === '[hidden]' && hiddenAncestor ? {} : null) });
  const root = (...dialogs: ReturnType<typeof dialog>[]) => ({
    querySelectorAll: (selector: string) => {
      assert.equal(selector, '[role="dialog"][aria-modal="true"]');
      return dialogs as unknown as NodeListOf<Element>;
    },
  });
  assert.equal(visibleModalOpen(root()), false);
  assert.equal(visibleModalOpen(root(dialog(true))), false, 'left open in a visited, hidden module');
  assert.equal(visibleModalOpen(root(dialog(true), dialog(false))), true);
});

test('boot overlay flag starts set (cover shown from first paint) and follows reports', () => {
  assert.equal(isBootOverlayOpen(), true);
  setBootOverlayOpen(false);
  assert.equal(isBootOverlayOpen(), false);
  setBootOverlayOpen(true);
  assert.equal(isBootOverlayOpen(), true);
});
// The Enter/click seam: CommandPalette passes { navigate: onNavigate (App's navigate), close, setActive }
// to these functions, so a palette that stops navigating, opens the wrong result or opens on an empty
// list fails here.
type Call = readonly [string, ...unknown[]];
function recorder(onSetActive?: (index: number) => void) {
  const calls: Call[] = [];
  const effects: PaletteEffects = {
    navigate: id => { calls.push(['navigate', id]); },
    close: () => { calls.push(['close']); },
    setActive: index => { calls.push(['setActive', index]); onSetActive?.(index); },
  };
  return { calls, effects };
}
const key = (k: string, extra: Partial<{ altKey: boolean; ctrlKey: boolean; metaKey: boolean; isComposing: boolean; keyCode: number }> = {}) =>
  ({ key: k, altKey: false, ctrlKey: false, metaKey: false, ...extra });

test('paletteChoice: the result at the given index, null for an empty list or an index outside it', () => {
  const results = [{ id: 'a' }, { id: 'b' }, { id: 'c' }];
  assert.equal(paletteChoice(results, 2), 'c', 'the selected option, not the first');
  assert.equal(paletteChoice(results, 0), 'a');
  assert.equal(paletteChoice([], 0), null);
  assert.equal(paletteChoice(results, -1), null);
  assert.equal(paletteChoice(results, 3), null);
  assert.equal(paletteChoice(results, 1.5), null);
});

test('commitPaletteChoice navigates to the chosen module, then closes; an empty list is a no-op', () => {
  const results = rankPaletteEntries(ENTRIES, 'process');
  const { calls, effects } = recorder();
  assert.equal(commitPaletteChoice(results, 1, effects), results[1].id);
  assert.deepEqual(calls, [['navigate', results[1].id], ['close']], 'navigate exactly once with the chosen id, before closing');
  const empty = recorder();
  assert.equal(commitPaletteChoice([], 0, empty.effects), null);
  assert.deepEqual(empty.calls, [], 'nothing navigates and the palette stays open');
});

test('keyboard: Enter opens the active (moved-to) result, not the first one', () => {
  const results = ENTRIES;
  let current = 0;
  const { calls, effects } = recorder(index => { current = index; });
  for (const k of ['ArrowDown', 'ArrowDown']) assert.equal(handlePaletteInputKey(key(k), results, current, effects), true);
  assert.equal(current, 2);
  assert.equal(handlePaletteInputKey(key('Enter'), results, current, effects), true);
  assert.deepEqual(calls, [['setActive', 1], ['setActive', 2], ['navigate', results[2].id], ['close']]);
  const end = recorder(index => { current = index; });
  handlePaletteInputKey(key('End'), results, current, end.effects);
  handlePaletteInputKey(key('Enter'), results, current, end.effects);
  assert.deepEqual(end.calls.at(-2), ['navigate', results.at(-1)!.id]);
});

test('keyboard: Enter with no results, other keys and modified arrows do nothing', () => {
  const { calls, effects } = recorder();
  assert.equal(handlePaletteInputKey(key('Enter'), [], -1, effects), false);
  assert.equal(handlePaletteInputKey(key('a'), ENTRIES, 0, effects), false);
  assert.equal(handlePaletteInputKey(key('ArrowDown', { altKey: true }), ENTRIES, 0, effects), false);
  assert.equal(handlePaletteInputKey(key('Escape'), ENTRIES, 0, effects), false, 'Escape belongs to AccessibleModal');
  assert.deepEqual(calls, []);
});

test('IME: keys of a composition (isComposing or keyCode 229) neither navigate nor move nor prevent the default', () => {
  const { calls, effects } = recorder();
  for (const extra of [{ isComposing: true }, { keyCode: 229 }, { isComposing: true, keyCode: 229 }]) {
    assert.ok(isComposingKey(extra));
    for (const k of ['Enter', 'ArrowDown', 'ArrowUp', 'Home', 'End']) {
      assert.equal(paletteKeyAction(key(k, extra), 3, 1), null, `${k} ${JSON.stringify(extra)}`);
      assert.equal(handlePaletteInputKey(key(k, extra), ENTRIES, 1, effects), false, 'false = no preventDefault');
    }
  }
  assert.deepEqual(calls, []);
  assert.ok(!isComposingKey({ isComposing: false, keyCode: 13 }));
  assert.equal(handlePaletteInputKey(key('Enter', { isComposing: false, keyCode: 13 }), ENTRIES, 1, effects), true, 'after composition Enter chooses');
  assert.deepEqual(calls, [['navigate', ENTRIES[1].id], ['close']]);
});