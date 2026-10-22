import assert from "node:assert/strict";
import { test } from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ModuleNav, navTabStop, syncNavFocus } from "../src/components/ModuleNav";
import { LAB_MODULES, MODULES, MODULE_PURPOSE } from "../src/data/workspaces";

const mods = [
  { id: "a", workspace: "lpbf" },
  { id: "b", workspace: "lpbf" },
  { id: "c", workspace: "materials" },
];

test("navTabStop: remembered entry only under the module it was focused with; else active; else first", () => {
  assert.equal(navTabStop(mods, { key: "", tab: "a" }, "a"), "a");
  assert.equal(navTabStop(mods, { key: "c", tab: "a" }, "a"), "c", "arrowed to c, still on a");
  assert.equal(navTabStop(mods, { key: "ws:materials", tab: "a" }, "a"), "a", "an unknown key never becomes the Tab stop");
  // A navigation from outside (hash change, back button, Next link) moves the stop to the aria-current entry.
  assert.equal(navTabStop(mods, { key: "c", tab: "a" }, "b"), "b");
  // A filter that hides the remembered entry and the active module falls back to the first visible one.
  assert.equal(navTabStop(mods.slice(2), { key: "a", tab: "a" }, "a"), "c");
  assert.equal(navTabStop([], { key: "", tab: "a" }, "a"), undefined);
});

test("syncNavFocus: A -> B -> A (back button) does not revive the entry remembered under A", () => {
  let focus = { key: "c", tab: "a" }; // arrowed to c while a was active
  assert.equal(syncNavFocus(focus, "a"), focus, "unchanged while a stays active (same object: no re-render)");
  focus = syncNavFocus(focus, "b"); // hash change to b
  assert.deepEqual(focus, { key: "", tab: "b" });
  focus = syncNavFocus(focus, "a"); // back to a
  assert.equal(navTabStop(mods, focus, "a"), "a", "the stop is the aria-current entry, not c");
});

test("rendered navigation has exactly one Tab stop, on the aria-current module", () => {
  // Every module has a button at all times.
  const active = LAB_MODULES[0];
  const html = renderToStaticMarkup(<ModuleNav modules={[...MODULES]} activeTab={active.id} activeWorkspace={active.workspace} onNavigate={() => undefined} />);
  const buttons = [...html.matchAll(/<button[^>]*>/g)].map(m => m[0]);
  assert.equal(buttons.length, MODULES.length, "one button per module; group headings are not buttons");
  const stops = buttons.filter(b => /tabindex="0"/.test(b));
  assert.equal(stops.length, 1);
  assert.match(stops[0], /aria-current="page"/);
  assert.ok(buttons.every(b => /tabindex="(0|-1)"/.test(b)));
});

test("every module entry is described by the hint AND its own description", () => {
  const html = renderToStaticMarkup(<ModuleNav modules={[...MODULES]} activeTab={LAB_MODULES[0].id} activeWorkspace={LAB_MODULES[0].workspace} onNavigate={() => undefined} />);
  const escape = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
  for (const module of MODULES) {
    assert.match(html, new RegExp(`aria-describedby="module-nav-hint nav-desc-${module.id}"`), module.id);
    assert.ok(html.includes(`<span id="nav-desc-${module.id}">${escape(MODULE_PURPOSE[module.id])}</span>`), `${module.id} description element`);
  }
  assert.match(html, /<div hidden="">/, "descriptions are referenced, not displayed");
  assert.match(html, /<p id="module-nav-hint" class="mk-sr-only">Arrow keys move between modules\.<\/p>/);
});
