import assert from "node:assert/strict";
import { test } from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { registerHooks } from "node:module";
import { readFileSync } from "node:fs";
import type { AtriumProps } from "../src/components/Atrium";
import { ModuleNav, navGroups, navTabStop } from "../src/components/ModuleNav";
import { CORE_FLOW, CORE_MODULE_IDS, LAB_MODULES, MODULES, NAV_GROUPS, isCoreModule } from "../src/data/workspaces";

// Atrium imports stylesheets, which plain Node cannot load: stub .css modules before importing it.
registerHooks({
  resolve: (specifier, context, next) => specifier.endsWith(".css") ? { url: "data:text/javascript,export default {}", shortCircuit: true } : next(specifier, context),
});

const nav = (activeTab: string, modules = [...MODULES]) => {
  const active = MODULES.find(m => m.id === activeTab)!;
  return renderToStaticMarkup(<ModuleNav modules={modules} activeTab={active.id} activeWorkspace={active.workspace} onNavigate={() => undefined} />);
};
const buttons = (html: string) => [...html.matchAll(/<button[^>]*>/g)].map(m => m[0]);
const moduleButtons = (html: string, ids: readonly string[]) => ids.filter(id => html.includes(`aria-describedby="module-nav-hint nav-desc-${id}"`));

test("core and labs partition the listed modules; core ids are listed and in flow order", () => {
  const listed = MODULES.map(m => m.id);
  for (const id of listed) assert.equal([isCoreModule(id), LAB_MODULES.some(m => m.id === id)].filter(Boolean).length, 1, `${id} is in exactly one of core/labs`);
  assert.equal(CORE_MODULE_IDS.length + LAB_MODULES.length, MODULES.length);
  assert.deepEqual([...CORE_MODULE_IDS, ...LAB_MODULES.map(m => m.id)].sort(), [...listed].sort());
  for (const id of CORE_MODULE_IDS) assert.ok(listed.includes(id), `${id} is a listed module`);
  assert.deepEqual(CORE_FLOW.map(step => step.id), [...CORE_MODULE_IDS]);
  assert.deepEqual(CORE_FLOW.map(step => step.verb), ["Set up and run", "Screen the process window", "Compare with published data", "Check the scorecard"]);
});

test("the sidebar lists every module at once, grouped Simulate / Compare with data / Materials and phases / Evidence and export", () => {
  assert.deepEqual(NAV_GROUPS.map(g => g.label), ["Simulate", "Compare with data", "Materials and phases", "Evidence and export"]);
  assert.deepEqual(NAV_GROUPS.flatMap(g => g.modules).sort(), MODULES.map(m => m.id).sort(), "every listed module is in exactly one group");
  for (const active of [CORE_MODULE_IDS[0], LAB_MODULES[0].id]) {
    const html = nav(active);
    assert.equal(moduleButtons(html, MODULES.map(m => m.id)).length, MODULES.length, "no collapsed Labs: every module has a button");
    assert.doesNotMatch(html, /Labs \(/);
    assert.doesNotMatch(html, /aria-controls="module-nav-labs"/);
  }
  const html = nav(CORE_MODULE_IDS[0]);
  let from = 0;
  for (const group of NAV_GROUPS) {
    const at = html.indexOf(`>${group.label}</p>`, from);
    assert.ok(at >= from, `${group.label} heading in order`);
    from = at;
  }
  for (const group of NAV_GROUPS) assert.match(html, new RegExp(`role="group" aria-labelledby="module-nav-group-${group.id}"`));
});

test("navGroups keeps a module that is in no group under More, and drops empty groups", () => {
  const groups = navGroups([{ id: "database" }, { id: "brand-new-module" }]);
  assert.deepEqual(groups.map(g => g.label), ["Materials and phases", "More"]);
  assert.deepEqual(groups[1].entries.map(e => e.id), ["brand-new-module"]);
  assert.deepEqual(navGroups([]), []);
});

test("exactly one Tab stop on the aria-current module, aria-current owned by it, for core and lab modules", () => {
  for (const id of [CORE_MODULE_IDS[0], LAB_MODULES[0].id]) {
    const all = buttons(nav(id));
    assert.equal(all.filter(b => /aria-current="page"/.test(b)).length, 1);
    const stops = all.filter(b => /tabindex="0"/.test(b));
    assert.equal(stops.length, 1);
    assert.match(stops[0], /aria-current="page"/);
    assert.ok(stops[0].includes(`nav-desc-${id}`));
    assert.ok(all.every(b => /tabindex="(0|-1)"/.test(b)));
  }
});

test("a filtered list shows only the matching groups; the Tab stop falls back to the first visible module", () => {
  const html = nav(CORE_MODULE_IDS[0], MODULES.filter(m => m.id === "database"));
  assert.match(html, />Materials and phases<\/p>/);
  assert.doesNotMatch(html, />Simulate<\/p>/);
  assert.equal(buttons(html).filter(b => /tabindex="0"/.test(b)).length, 1);
});

test("a throwing localStorage no longer matters: the navigation has no stored state", () => {
  const g = globalThis as unknown as { window?: unknown };
  const previous = g.window;
  g.window = { localStorage: { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); } } };
  try {
    assert.equal(moduleButtons(nav(CORE_MODULE_IDS[1]), MODULES.map(m => m.id)).length, MODULES.length);
  } finally {
    if (previous === undefined) delete g.window; else g.window = previous;
  }
});

test("module ids, hashes and navigate events are untouched: each button calls onNavigate with its own id", () => {
  const html = nav(CORE_MODULE_IDS[0]);
  for (const m of MODULES) assert.ok(html.includes(`nav-desc-${m.id}`), m.id);
  const src = readFileSync(new URL("../src/components/ModuleNav.tsx", import.meta.url), "utf8");
  assert.match(src, /onClick=[{]\(\) => onNavigate\(module\.id\)[}]/);
});

test("Atrium: four flow steps in order with registry labels, the screening note and the Labs count", async () => {
  const { Atrium } = await import("../src/components/Atrium");
  const props: AtriumProps = { continueId: CORE_MODULE_IDS[0], engine: null, engineChecking: false, shortcutLabel: "Ctrl K", onNavigate: () => undefined, onSearch: () => undefined };
  const html = renderToStaticMarkup(<Atrium {...props} />);
  const flow = html.slice(html.indexOf('class="mk-at-flow"'), html.indexOf("</ol>", html.indexOf('class="mk-at-flow"')));
  assert.equal((flow.match(/<li/g) ?? []).length, 4);
  let from = 0;
  for (const step of CORE_FLOW) {
    const module = MODULES.find(m => m.id === step.id)!;
    const at = flow.indexOf(module.label.replace(/&/g, "&amp;"), from);
    assert.ok(at >= from, `${module.label} follows the previous step`);
    assert.ok(flow.includes(step.verb));
    from = at;
  }
  assert.ok(flow.includes("Module maturity; this is not a validation claim"), "maturity badge title");
  assert.ok(html.includes("Flagship - LPBF melt-pool and process screening"));
  assert.ok(html.includes("Start the LPBF flow"));
  assert.ok(html.includes("Screening only. No result in this flow is experimental validation."));
  const counts = [...html.matchAll(/class="mk-at-count">(?:<!-- -->)?(\d+)(?:<!-- -->)? labs/g)].map(m => Number(m[1]));
  assert.equal(counts.reduce((a, b) => a + b, 0), LAB_MODULES.length);
  assert.match(html, new RegExp(`class="mk-at-section-label"><span>(?:<!-- -->)?0?${LAB_MODULES.length}(?:<!-- -->)?</span>Labs`));
});

test("focus key of a hidden entry falls back to the active module", () => {
  const core = MODULES.filter(m => m.id === CORE_MODULE_IDS[0]);
  assert.equal(navTabStop(core, { key: "gone", tab: CORE_MODULE_IDS[0] }, CORE_MODULE_IDS[0]), CORE_MODULE_IDS[0]);
});
