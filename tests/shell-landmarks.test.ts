import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { test } from "node:test";
import { rovingIndex } from "../src/utils/rovingFocus";

// D7 (Phase 2 record): skip link, one main landmark, one banner header, the module navigation as a
// single Tab stop, and the shell CSS that lets the sticky header and fixed dialogs work.
const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8").replace(/\r/g, "");
const app = read("src/App.tsx");
const css = read("src/index.css");

function listTsx(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    return statSync(full).isDirectory() ? listTsx(full) : name.endsWith(".tsx") ? [full] : [];
  });
}
const sources = listTsx(resolve(process.cwd(), "src")).map((full) => ({ rel: relative(process.cwd(), full).replace(/\\/g, "/"), text: readFileSync(full, "utf8") }));

test("the skip link is the first focusable element after the boot overlay and targets the one <main>", () => {
  const returned = app.slice(app.indexOf("  return <>"));
  // Only the boot overlay (a focus-trapping dialog that is removed once closed) precedes it; nothing focusable sits between.
  assert.match(returned, /^ {2}return <><SilentBoundary><Suspense fallback=\{<div className="mk-boot-cover" aria-hidden="true" \/>\}><BootSequence \/><\/Suspense><\/SilentBoundary><a href="#main-content" className="mk-skip-link" onClick=\{skipToMain\}>Skip to main content<\/a><div className="mk-shell /);
  assert.match(app, /<main id="main-content" tabIndex=\{-1\}/);
  // Hash routing owns location.hash: the handler must not follow the fragment, it focuses <main> itself.
  const handler = app.slice(app.indexOf("function skipToMain"), app.indexOf("function skipToMain") + 220);
  assert.match(handler, /event\.preventDefault\(\);/);
  assert.match(handler, /document\.getElementById\('main-content'\)\?\.focus\(\)/);
});

test("exactly one <main> landmark and one banner <header> in the source tree", () => {
  const mains = sources.flatMap(({ rel, text }) => [...text.matchAll(/<main\b/g)].map(() => rel));
  assert.deepEqual(mains, ["src/App.tsx"], `module views must not declare their own <main>: ${mains.join(", ")}`);
  for (const { rel, text } of sources) {
    assert.doesNotMatch(text, /role=["'](main|banner)["']/, `${rel} declares a main/banner role`);
  }
  // The app header is the only <header> outside <main>; module headers render inside <main>, where they are not banners.
  assert.equal((app.match(/<header\b/g) ?? []).length, 1);
  assert.ok(app.indexOf("<header") < app.indexOf("<main"), "the banner header sits before (outside) <main>");
  assert.match(app, /<header className="mk-header sticky top-0 z-40 /);
});

test("module navigation is its own component (focus moves do not re-render App), wired with arrow keys", () => {
  const nav = read("src/components/ModuleNav.tsx");
  // On the start page no module is the current page (review N1), so App passes home state.
  assert.match(app, /<ModuleNav home=\{home\} modules=\{filtered\} activeTab=\{activeTab\} activeWorkspace=\{activeWorkspace\.id\} onNavigate=\{navigate\} \/>/);
  assert.doesNotMatch(app, /navFocus|setNavFocus|onFocus=/, "App holds no roving focus state");
  assert.match(nav, /<nav aria-label="Engineering workspaces" onKeyDown=\{onKey\}>/);
  assert.match(nav, /<p id="module-nav-hint" className="mk-sr-only">Arrow keys move between modules\.<\/p>/);
  assert.match(nav, /tabIndex: key === stop \? 0 : -1/);
  assert.match(nav, /if \(event\.ctrlKey \|\| event\.altKey \|\| event\.metaKey\) return;/, "modifier shortcuts are left to the browser");
  assert.doesNotMatch(nav, /item\('ws:'/, "group headings are plain text, not roving entries");
  assert.match(nav, /role="group" aria-labelledby=/, "each group is labelled by its heading");
  assert.match(nav, /<button key=\{module\.id\} \{\.\.\.item\(module\.id, ' nav-desc-' \+ module\.id\)\} aria-current=\{!home && activeTab === module\.id \? 'page' : undefined\}/);
});

test("rovingIndex: Up/Down wrap, Home/End jump, other keys are ignored", () => {
  assert.equal(rovingIndex(5, 0, "ArrowDown"), 1);
  assert.equal(rovingIndex(5, 4, "ArrowDown"), 0);
  assert.equal(rovingIndex(5, -1, "ArrowDown"), 0);
  assert.equal(rovingIndex(5, 0, "ArrowUp"), 4);
  assert.equal(rovingIndex(5, 3, "ArrowUp"), 2);
  assert.equal(rovingIndex(5, -1, "ArrowUp"), 4);
  assert.equal(rovingIndex(5, 2, "Home"), 0);
  assert.equal(rovingIndex(5, 2, "End"), 4);
  assert.equal(rovingIndex(5, 2, "Tab"), null);
  assert.equal(rovingIndex(5, 2, "Enter"), null);
  assert.equal(rovingIndex(0, -1, "ArrowDown"), null);
});

test("shell rule is layered and sets no z-index, so sticky header and fixed dialogs keep their utilities", () => {
  const layered = /@layer components \{\s*\.mk-shell > \*:not\(\.mk-grid-overlay\):not\(\.mk-scanline\) \{\s*position: relative;\s*\}\s*\}/;
  assert.match(css, layered);
  // No unlayered copy of the rule that would beat Tailwind's `sticky`/`fixed` again.
  const unlayered = css.replace(layered, "");
  assert.doesNotMatch(unlayered, /\.mk-shell > \*:not\(\.mk-grid-overlay\)/);
  // The telemetry strip keeps its own z-index 0 (in-flow footer below module dialogs).
  assert.match(read("src/styles/boot.css"), /\.mk-shell > \.mk-telemetry:not\(\.mk-grid-overlay\):not\(\.mk-scanline\) \{ z-index: 0; \}/);
});

test("one header-height variable drives scroll padding, the lg header height and the sidebar offset", () => {
  assert.match(css, /:root \{ --mk-header-h: 5\.5rem; \}/);
  assert.match(css, /@media \(min-width: 64rem\) \{\s*:root \{ --mk-header-h: 4\.75rem; \}\s*\.mk-header \{ min-height: var\(--mk-header-h\); \}\s*\}/);
  assert.match(css, /html \{ scroll-padding-top: calc\(var\(--mk-header-h\) \+ 0\.5rem\); \}/, "focus is never scrolled under the sticky header (WCAG 2.4.11)");
  assert.match(app, /lg:sticky lg:top-\[var\(--mk-header-h\)\] lg:h-\[calc\(100vh_-_var\(--mk-header-h\)\)\]/);
  assert.doesNotMatch(app, /77px/, "no second, hard-coded header height");
});

test("scientific context panel is an early-started lazy chunk behind a silent boundary", () => {
  assert.doesNotMatch(app, /^import [^;]*\.\/components\/ScientificContextPanel['"]/m, "not in the index chunk");
  assert.match(app, /^const contextChunk = import\('\.\/components\/ScientificContextPanel'\);$/m, "request starts at module evaluation");
  assert.match(app, /contextChunk\.catch\(/, "no unhandled rejection before render");
  assert.match(app, /<SilentBoundary><Suspense fallback=\{null\}><ScientificContextPanel moduleId=\{activeTab\} specimen=\{specimen\} \/><\/Suspense><\/SilentBoundary>/);
});

test("skip link is visible on focus and uses contrast-tested tokens only", () => {
  const rule = css.match(/\.mk-skip-link \{([^}]*)\}/)?.[1] ?? "";
  assert.match(rule, /color: var\(--mk-ice\);/);
  assert.match(rule, /background: var\(--mk-surface-raised\);/);
  assert.match(rule, /border: 1px solid var\(--mk-focus-color\);/);
  assert.match(rule, /position: fixed;/);
  assert.doesNotMatch(rule, /#[0-9a-f]{3,6}\b|rgba?\(|transition/i, "token colors only, never animated");
  assert.match(css, /\.mk-skip-link:focus \{ transform: none; \}/);
});
