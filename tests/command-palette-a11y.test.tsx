import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { CommandPalette } from '../src/components/CommandPalette';
import { evidenceBadgeView } from '../src/components/sdk/EvidenceBadge';
import { MATURITY_BADGE_TITLE, MODULES, WORKSPACES } from '../src/data/workspaces';
import { contractById } from '../src/modules/registry';

// Phase 9 command palette a11y, same static pattern as the Phase 8 tests (tests/accessible-modal.test.tsx,
// tests/a11y-modal-migration.test.ts, tests/boot-telemetry-a11y.test.ts): server-rendered markup plus
// source checks. The repo has no jsdom/axe dependency, so live focus movement and an axe run are
// covered by the browser check, not here.
const read = (p: string) => readFileSync(resolve(process.cwd(), p), 'utf8').replace(/\r/g, '');
const html = renderToStaticMarkup(<CommandPalette activeTab={MODULES[0].id} onNavigate={() => undefined} onClose={() => undefined} />);
const attr = (tag: string, name: string) => new RegExp(`\\b${name}="([^"]*)"`).exec(tag)?.[1];
const openingTags = (role: string) => [...html.matchAll(new RegExp(`<[a-z]+\\b[^>]*\\brole="${role}"[^>]*>`, 'g'))].map(m => m[0]);
const hasId = (id: string) => html.includes(`id="${id}"`);

test('dialog: role=dialog, aria-modal, named by its visible heading', () => {
  const [dialog] = openingTags('dialog');
  assert.ok(dialog, 'renders a dialog');
  assert.equal(attr(dialog, 'aria-modal'), 'true');
  assert.equal(attr(dialog, 'aria-labelledby'), 'command-palette-title');
  assert.match(html, /<h2 id="command-palette-title"[^>]*>Go to module<\/h2>/);
});

test('combobox: labelled text field that controls the listbox and points at the active option', () => {
  const [combo] = openingTags('combobox');
  assert.ok(combo?.startsWith('<input'), 'the combobox is the text input');
  assert.equal(attr(combo, 'aria-expanded'), 'true', 'results are shown');
  assert.match(attr(combo, 'maxlength') ?? attr(combo, 'maxLength') ?? '', /^120$/, 'query length is capped');
  assert.equal(attr(combo, 'aria-autocomplete'), 'list');
  const listboxId = attr(combo, 'aria-controls')!;
  const [listbox] = openingTags('listbox');
  assert.equal(attr(listbox, 'id'), listboxId);
  assert.ok(attr(listbox, 'aria-label'), 'listbox is named');
  const inputId = attr(combo, 'id')!;
  assert.match(html, new RegExp(`<label for="${inputId}" class="sr-only">[^<]+</label>`), 'the field has a label (Tailwind sr-only from the eager index CSS)');
  assert.ok(hasId(attr(combo, 'aria-describedby')!), 'keyboard hint exists');
  const options = openingTags('option');
  assert.equal(attr(combo, 'aria-activedescendant'), attr(options[0], 'id'), 'first result is active');
});

test('options: one per registry module, exactly one selected, each named and described by existing ids', () => {
  const options = openingTags('option');
  assert.equal(options.length, MODULES.length);
  assert.equal(options.filter(tag => attr(tag, 'aria-selected') === 'true').length, 1);
  assert.equal(options.filter(tag => attr(tag, 'aria-selected') === 'false').length, MODULES.length - 1);
  for (const tag of options) {
    for (const name of ['id', 'aria-labelledby', 'aria-describedby']) assert.ok(attr(tag, name), `${name} on ${tag}`);
    assert.ok(hasId(attr(tag, 'aria-labelledby')!), tag);
    const described = attr(tag, 'aria-describedby')!.split(' ');
    assert.deepEqual(described.map(id => id.replace(/^command-palette-option-.*?-(workspace|meta)$/, '$1')), ['workspace', 'meta'], tag);
    for (const id of described) assert.ok(hasId(id), `${id} exists`);
    assert.doesNotMatch(tag, /tabindex/, 'options are not Tab stops (focus stays in the combobox)');
  }
  const ids = new Set(options.map(tag => attr(tag, 'id')));
  assert.equal(ids.size, options.length, 'unique option ids');
});

test('every option shows its maturity and, when contracted, the unchanged evidence badge text', () => {
  for (const module of MODULES) {
    const start = html.indexOf(`id="command-palette-option-${module.id}"`);
    const end = html.indexOf('</li>', start);
    const option = html.slice(start, end);
    assert.match(option, new RegExp(`class="mk-scope-badge[^"]*">${module.scope}<`), module.id);
    const view = evidenceBadgeView(contractById(module.id));
    if (view) {
      assert.ok(option.includes(`>${view.text}<`), `${module.id} shows "${view.text}"`);
      assert.ok(option.includes(view.description.replace(/&/g, '&amp;')), `${module.id} keeps the badge description`);
      assert.match(option, new RegExp(`class="mk-count-badge[^"]*"[^>]*data-evidence-ceiling="${view.ceiling}"`));
    } else {
      assert.doesNotMatch(option, /Strongest claim allowed/, `${module.id}: legacy modules show no ceiling, as in the header`);
    }
  }
  assert.ok(MODULES.some(module => evidenceBadgeView(contractById(module.id))), 'at least one contracted module is covered');
});

test('result count is a status message and the close control is a named button', () => {
  assert.match(html, new RegExp(`<p role="status"[^>]*>${MODULES.length} of ${MODULES.length} modules</p>`));
  assert.match(html, /<button type="button"[^>]*>Close <kbd aria-hidden="true">Esc<\/kbd><\/button>/);
});

test('palette source: AccessibleModal for trap/Escape/restore, registry list, shared navigate, no hard-coded modules', () => {
  const source = read('src/components/CommandPalette.tsx');
  assert.match(source, /<AccessibleModal open onClose=\{onClose\} labelledBy="command-palette-title" closeOnBackdrop lockScroll/);
  assert.ok(!source.includes('fixed inset-0'), 'no hand-made overlay');
  assert.doesNotMatch(source, /addEventListener|['"]Escape['"]/, 'Escape and focus restore stay with AccessibleModal');
  assert.match(source, /import \{ MATURITY_BADGE_TITLE, MODULES, WORKSPACES, type ModuleId \} from '\.\.\/data\/workspaces';/);
  assert.match(source, /<EvidenceBadge moduleId=\{entry\.id\} \/>/);
  for (const module of MODULES) assert.ok(!source.includes(`'${module.id}'`) && !source.includes(`"${module.id}"`), `hard-coded ${module.id}`);
  // Wiring of the tested seam (behaviour: tests/command-palette.test.ts, Enter/click/IME with recorded effects).
  assert.match(source, /navigate: onNavigate,/);
  assert.match(source, /onClick=\{\(\) => commitPaletteChoice\(results, index, effects\)\}/);
  assert.match(source, /if \(isComposingKey\(key\)\) return;[^\n]*\n[\s\S]*?if \(handlePaletteInputKey\(key, results, current, effects\)\) event\.preventDefault\(\);/);
  assert.match(source, /isComposing: event\.nativeEvent\.isComposing, keyCode: event\.keyCode/);
  assert.doesNotMatch(source, /location\.hash|history\.|metallix-navigate-tab/, 'no second routing path');
  const claim = /\b(validated|ready|certified|qualified)\b/i;
  const code = source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:"'`])\/\/.*$/gm, '$1');
  assert.deepEqual(code.split('\n').filter(line => claim.test(line)), [], 'palette text makes no validation claim');
});

test('App: visible trigger, Ctrl/Cmd+K hook, lazy chunk with the same navigate() as the sidebar', () => {
  const app = read('src/App.tsx');
  assert.match(app, /<button type="button" aria-haspopup="dialog" aria-keyshortcuts=\{SHORTCUT_KEYS\} onClick=\{openPalette\}[^>]*>.*?<span className="sr-only sm:not-sr-only">Search modules<\/span><kbd aria-hidden="true"/, 'visible "Search modules" from sm up, the same accessible name on phones; the key hint is not part of the name');
  assert.match(app, /useCommandPaletteShortcut\(APPLE, paletteGate, \(\) => setPaletteOpen\(true\)\);/);
  // The gate is App state, not a DOM query: engine dialog requested (also while its chunk loads), boot overlay.
  assert.match(app, /const paletteGate = \(\): PaletteGate => \(\{ paletteOpen, engineDialogOpen: showStatus, bootOverlayOpen: isBootOverlayOpen\(\), moduleModalOpen: visibleModalOpen\(\) \}\);/);
  assert.match(app, /const openPalette = \(\) => \{ if \(canOpenPalette\(paletteGate\(\)\)\) setPaletteOpen\(true\); \};/);
  assert.match(app, /<button onClick=\{\(\) => \{ setPaletteOpen\(false\); setShowStatus\(true\); \}\} className="mk-status/, 'the engine dialog cancels a palette that is still loading');
  assert.match(app, /bootChunk\.catch\(\(\) => setBootOverlayOpen\(false\)\);/, 'a failed boot chunk does not block the palette');
  assert.match(read('src/components/BootSequence.tsx'), /const open = !gone && !snap\.dismissed;\n[^\n]*\n {2}useEffect\(\(\) => setBootOverlayOpen\(open\), \[open\]\);/);
  assert.match(app, /const loadCommandPalette = \(\) => lazy\(\(\) => import\('\.\/components\/CommandPaletteChunk'\)/);
  assert.match(app, /const CommandPalette = useMemo\(loadCommandPalette, \[paletteLoad\]\);/);
  assert.doesNotMatch(app, /^import [^;]*CommandPalette(Chunk)?['"]/m, 'never imported eagerly');
  assert.match(app, /<CommandPalette activeTab=\{activeTab\} onNavigate=\{navigate\} onClose=\{\(\) => setPaletteOpen\(false\)\} \/>/);
  assert.match(app, /<ModuleNav [^>]*onNavigate=\{navigate\} \/>/, 'the sidebar uses the same navigate');
  const fallback = app.match(/\{paletteOpen && <SilentBoundary key=\{paletteLoad\} fallback=\{(<div role="alert"[\s\S]*?<\/div>)\}>/)?.[1] ?? '';
  assert.match(fallback, /Module search could not be loaded\./);
  assert.match(fallback, />Retry<\/button>/);
  assert.match(fallback, /<button onClick=\{\(\) => \{ setPaletteOpen\(false\); retryPalette\(\); \}\}[^>]*>Close<\/button>/, 'Close also resets the lazy component so the next open retries');
  assert.match(fallback, /<button onClick=\{retryPalette\}[^>]*>Retry<\/button>/);
  assert.match(read('src/components/CommandPaletteChunk.ts'), /import '\.\.\/styles\/palette\.css';\s*export \{ CommandPalette \} from '\.\/CommandPalette';/);
  const hook = read('src/hooks/useCommandPaletteShortcut.ts');
  assert.match(hook, /const onKey = createShortcutListener\(apple, \(\) => latest\.current\);/);
  assert.doesNotMatch(hook, /Escape/, 'Escape stays with AccessibleModal');
  assert.doesNotMatch(hook.replace(/useLayoutEffect\(\(\) => \{\s*latest\.current = \{ gate, open \};\s*\}\);/, ''), /latest\.current =/, 'the ref is written in an effect, not during render');
  assert.match(hook, /^ {4}window\.addEventListener\('keydown', onKey\);\n {4}return \(\) => window\.removeEventListener\('keydown', onKey\);$/m, 'listener removed on unmount (not commented out)');
});

test('phone header keeps one row with the trigger: decorative brand mark from sm up, tighter right gap', () => {
  // Browser-measured at 375 px: without this the status button overflowed the viewport (right edge 422 px);
  // a wrapped header would exceed --mk-header-h (scroll padding, WCAG 2.4.11), so the row must not wrap.
  const app = read('src/App.tsx');
  // The mark is shown at every width (phones too, review N3), exposed as one labelled image.
  assert.match(app, /<div className="contents"><div className="mk-brand-mark" role="img" aria-label="Metalliksa logo">/);
  assert.match(app, /<div className="flex items-center gap-2 sm:gap-3"><button type="button" aria-haspopup="dialog"/);
  assert.match(app, /<h1 className="mk-brand-title[^"]*">METALLIKSA<\/h1>/, 'the brand name stays visible at every width');
});

test('options describe workspace and current state to assistive tech, not only visually', () => {
  const current = MODULES[0];
  const options = openingTags('option');
  assert.deepEqual(options.filter(tag => attr(tag, 'aria-current') === 'page').map(tag => attr(tag, 'id')), [`command-palette-option-${current.id}`]);
  for (const module of MODULES) {
    const id = `command-palette-option-${module.id}-workspace`;
    const text = html.match(new RegExp(`<span id="${id}"[^>]*>([^<]*)</span>`))?.[1] ?? '';
    const workspace = WORKSPACES.find(w => w.id === module.workspace)!.label.replace(/&/g, '&amp;');
    assert.equal(text, module.id === current.id ? `${workspace} · current` : workspace, module.id);
  }
});

test('details: aria-expanded follows the results, hover never moves the active option, one maturity title', () => {
  const source = read('src/components/CommandPalette.tsx');
  assert.match(source, /aria-expanded=\{results\.length > 0\}/);
  assert.doesNotMatch(source, /onMouseMove|onMouseEnter|onPointer(Move|Enter)/, 'aria-activedescendant follows the keyboard only');
  assert.match(source, /maxLength=\{PALETTE_QUERY_MAX_LENGTH\}/);
  assert.match(source, /onChange=\{event => \{ setQuery\(event\.target\.value\); setActive\(0\); if \(list\.current\) list\.current\.scrollTop = 0; \}\}/, 'a new query shows the first result');
  for (const file of ['src/App.tsx', 'src/components/CommandPalette.tsx']) {
    const text = read(file);
    assert.match(text, /<span title=\{MATURITY_BADGE_TITLE\} className=\{`mk-scope-badge/, file);
    assert.doesNotMatch(text, /not a validation claim/, `${file} uses the shared title`);
  }
  assert.equal(MATURITY_BADGE_TITLE, 'How finished this module is. It says nothing about whether a result is validated.');
  const css = read('src/styles/palette.css');
  assert.match(css, /max-height: min\(36rem, 76vh\);\s*max-height: min\(36rem, 76dvh\);/, 'dvh with a vh fallback');
  assert.match(css, /max-height: calc\(100vh - 2 \* var\(--mk-space-4\)\); max-height: calc\(100dvh - 2 \* var\(--mk-space-4\)\);/);
});
// Same token sets as tests/design-tokens-contrast.test.ts, which checks their contrast.
const TEXT_TOKEN = /^--mk-(text|muted|signal-|evidence-)|^--mk-(ice|plasma|amber)$/;
const SURFACES = ['--mk-bg', '--mk-surface', '--mk-surface-raised', '--mk-glass-bg', '--mk-fill-panel', '--mk-fill-deep'];
const LINES = ['--mk-border-strong', '--mk-focus-color', '--mk-line-subtle', '--mk-border'];

test('palette.css: token colors only, covered text/surface/boundary tokens, static focus ring, motion opt-in', () => {
  const css = read('src/styles/palette.css').replace(/\/\*[\s\S]*?\*\//g, '');
  assert.doesNotMatch(css, /#[0-9a-f]{3,8}\b/i, 'literal hex color');
  assert.doesNotMatch(css, /\b(rgba?|hsla?)\(/i, 'literal rgb/hsl color');
  assert.doesNotMatch(css, /url\(|@import|https?:\/\//i, 'external resource');
  const decls = [...css.matchAll(/([\w-]+)\s*:\s*([^;{}]+);/g)];
  const tokensOf = (prop: RegExp) => decls.filter(m => prop.test(m[1])).flatMap(m => [...m[2].matchAll(/var\((--mk-[\w-]+)\)/g)].map(v => v[1]));
  for (const token of tokensOf(/^color$/)) assert.match(token, TEXT_TOKEN, `${token} is not a contrast-checked text token`);
  for (const token of tokensOf(/^background(-color)?$/)) assert.ok(SURFACES.includes(token), `${token} is not a covered surface`);
  for (const token of tokensOf(/^(border(-\w+)?|outline(-color)?|box-shadow)$/).filter(t => !/-(width|offset|halo|elev-\d)$/.test(t))) {
    assert.ok(LINES.includes(token), `${token} is not a boundary/decorative line token`);
  }
  assert.doesNotMatch(css, /opacity|filter|visibility/, 'nothing fades or hides labels or badges');
  assert.doesNotMatch(css, /mk-(scope|count)-badge/, 'badges keep their shared style');
  assert.doesNotMatch(css, /transition/, 'no transitions (focus ring never animates)');
  const animations = [...css.matchAll(/animation\s*:/g)].length;
  const guarded = css.match(/@media \(prefers-reduced-motion: no-preference\) \{([\s\S]*?)\}\s*\}/)?.[1] ?? '';
  assert.equal((guarded.match(/animation\s*:/g) ?? []).length, animations, 'every animation sits under prefers-reduced-motion: no-preference');
  assert.match(css, /:focus-visible\s*\{[^}]*outline:\s*var\(--mk-focus-width\) solid var\(--mk-focus-color\)/);
});
