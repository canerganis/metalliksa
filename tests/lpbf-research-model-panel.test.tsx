import React from "react";
import test, { afterEach, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import { ResearchModelPanel } from "../src/components/3d-distortion-lab/ResearchModelPanel";
import { refusalText } from "../src/components/3d-distortion-lab/ResearchModuleSection";
import { useLpbfResearchModelStore } from "../src/store/useLpbfResearchModelStore";
import { APPROVED_WORDING, AUTHORED_WORDING, supportText } from "../src/utils/lpbfResearchWording";
import {
  inputSignature,
  renderServedDifference,
  sig4,
  type DifferenceContext,
} from "../src/utils/lpbfResearchPanelModel";
import { TI64_INPUT, completeResponse, describeResponse, nominalResponse } from "./support/researchPanelFixtures";

// R-UI render tests: the panel is collapsed by default, shows the approved header, scope line and evidence labels,
// keeps Run disabled until describe answers, prints the band caption once per module, never uses a banned word, and
// substitutes served numbers into a difference statement only when the served identity matches (4.6).

const store = () => useLpbfResearchModelStore.getState();
const text = (markup: string) => markup.replace(/<[^>]+>/g, " ").replace(/&#x27;/g, "'").replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&gt;/g, ">").replace(/&lt;/g, "<").replace(/\s+/g, " ");

// renderToStaticMarkup reads zustand's server snapshot, which is the initial state object; seed both so a render sees it.
const PRISTINE = { ...useLpbfResearchModelStore.getInitialState() };
type StoreState = ReturnType<typeof useLpbfResearchModelStore.getState>;
function seed(patch: Partial<StoreState> | ((s: StoreState) => Partial<StoreState>)) {
  const next = typeof patch === "function" ? patch(useLpbfResearchModelStore.getInitialState()) : patch;
  Object.assign(useLpbfResearchModelStore.getInitialState(), next);
  useLpbfResearchModelStore.setState(next);
}

const IDENTITY_OF = (input = TI64_INPUT) => JSON.stringify({ process: { ...input, laserWavelength: "IR_1064nm", absorptionModel: "flat-plate" }, propertyContext: input.propertyContext, options: { marangoni: {}, surfaceBalance: {}, ranges: { marangoni: {}, surfaceBalance: {} } } });

function seedHost(state: "describe-ready" | "complete" | "band-pending" | "checking" | "stale") {
  const identity = IDENTITY_OF();
  const describe = describeResponse("melt-pool:1");
  const complete = completeResponse("melt-pool:3");
  const nominal = nominalResponse("melt-pool:2");
  seed((s) => ({
    hosts: {
      ...s.hosts,
      "melt-pool": {
        input: TI64_INPUT, alloyKey: "ti6al4v", identity,
        describe: state === "checking"
          ? { status: "checking", alloyKey: "ti6al4v", key: identity, response: null, error: null }
          : { status: "ready", alloyKey: "ti6al4v", key: identity, response: describe, error: null },
        run: {
          status: state === "complete" ? "complete" : state === "band-pending" ? "band-pending" : state === "stale" ? "stale" : "idle",
          generation: 1,
          identity: state === "describe-ready" || state === "checking" ? null : identity,
          input: TI64_INPUT,
          requestKey: complete.requestKey,
          nominal: state === "describe-ready" || state === "checking" ? null : nominal,
          result: state === "complete" ? complete : null,
          progress: state === "band-pending" ? { armsDone: 20, armsTotal: 79 } : state === "complete" ? { armsDone: 79, armsTotal: 79 } : null,
          cache: complete.cache, channel: null, error: null,
        },
      },
    },
  }));
}

const panel = (props: Partial<React.ComponentProps<typeof ResearchModelPanel>> = {}) =>
  renderToStaticMarkup(<ResearchModelPanel host="melt-pool" input={TI64_INPUT} served={null} {...props} />);

const restore = () => { Object.assign(useLpbfResearchModelStore.getInitialState(), PRISTINE); store().reset(); };
beforeEach(restore);
afterEach(restore);

test("collapsed by default: the header and the evidence badges, nothing else", () => {
  seedHost("describe-ready");
  const html = panel();
  const t = text(html);
  assert.match(t, /^ ?Research model Research Screening only No experimental validation/);
  assert.match(html, /aria-expanded="false"/);
  assert.equal(t.includes(APPROVED_WORDING.scopeLine), false);
  assert.equal(t.includes(AUTHORED_WORDING.runButton), false);
});

test("opened: the approved scope line, a disabled Run before describe answers, an enabled Run after", () => {
  seedHost("checking");
  let html = panel({ defaultOpen: true });
  assert.ok(text(html).includes(APPROVED_WORDING.scopeLine));
  assert.match(html, /<button[^>]*disabled=""[^>]*>Run research models<\/button>/);
  assert.ok(text(html).includes("Checking inputs"));
  seedHost("describe-ready");
  html = panel({ defaultOpen: true });
  assert.doesNotMatch(html, /<button[^>]*disabled=""[^>]*>Run research models<\/button>/);
  assert.match(html, /<button[^>]*disabled=""[^>]*>Cancel<\/button>/, "Cancel is disabled while nothing runs");
  assert.match(html, /role="status"/);
  assert.match(html, /aria-live="polite"/);
});

test("with option problems Run stays disabled and the message is shown", () => {
  seedHost("describe-ready");
  const identity = IDENTITY_OF();
  const describe = describeResponse("melt-pool:1", {
    problems: [{ pointer: "/researchOptions/marangoni/length_m", rule: "below-min", limit: 1e-6, value: "0", message: "Research length m must be between 1e-6 and 0.01 m; got 0." }],
  });
  seed((s) => ({ hosts: { ...s.hosts, "melt-pool": { ...s.hosts["melt-pool"], describe: { status: "ready", alloyKey: "ti6al4v", key: identity, response: describe, error: null } } } }));
  const html = panel({ defaultOpen: true, defaultOpenModules: true });
  assert.match(html, /<button[^>]*disabled=""[^>]*>Run research models<\/button>/);
  assert.ok(text(html).includes("must be between 1e-6 and 0.01 m"));
});

test("the inputs come from describe: label, help bound by aria-describedby, provenance, reset", () => {
  seedHost("describe-ready");
  seed({ optionsByAlloy: { ti6al4v: { marangoni: { deltaTemperature_K: 700 }, surfaceBalance: {}, ranges: { marangoni: {}, surfaceBalance: {} } } } });
  const html = panel({ defaultOpen: true, defaultOpenModules: true });
  const control = describeResponse("x:1").controls.find((c) => c.key === "deltaTemperature_K")!;
  assert.ok(text(html).includes(control.label));
  assert.ok(text(html).includes(control.help));
  assert.ok(text(html).includes(control.provenance.label));
  assert.match(html, /aria-describedby="[^"]*-deltaTemperature_K-help/);
  assert.ok(text(html).includes(control.resetLabel!), "reset button for an edited control");
  const slope = describeResponse("x:1").controls.find((c) => c.key === "surfaceTensionSlope_N_mK")!;
  assert.ok(Object.keys(slope.displayUnits).every((u) => text(html).includes(u)), "slope shows its display unit");
});

test("a complete result: module headers carry Research, Screening only and No experimental validation", () => {
  seedHost("complete");
  const html = panel({ defaultOpen: true });
  const t = text(html);
  for (const id of ["keyholeCavity", "meltDepthLink", "marangoni", "surfaceBalance", "alSi10MgIndexDisclosure", "alSi10MgVapourMgAware", "unavailablePhysics"]) {
    assert.match(html, new RegExp(`data-testid="research-module-${id}"`));
  }
  for (const phrase of [APPROVED_WORDING.badgeResearch, APPROVED_WORDING.badgeScreeningOnly, APPROVED_WORDING.badgeNoValidation]) assert.ok(t.includes(phrase));
  assert.ok(t.includes("Not experimentally validated; research diagnostic/model only."));
  assert.ok(text(html).includes("Falsified flat non-receding HKL closure"), "the surface balance keeps its falsified status next to its numbers");
  assert.ok(t.includes("Request key"));
});

test("opened modules show the field table with source support, the caption and the scenario count", () => {
  seedHost("complete");
  const html = panel({ defaultOpen: true, defaultOpenModules: true });
  const t = text(html);
  assert.ok(t.includes(APPROVED_WORDING.supportLiterature));
  assert.ok(t.includes("User input: ") || t.includes("Unresolved: "), "weakest inputs are named");
  assert.ok(t.includes(APPROVED_WORDING.bandCaption));
  assert.match(t, /\d+ named scenarios\./);
  assert.match(t, /Lowest: .+\. Highest: /, "extremes name their scenarios, with the arm provenance in the label");
  assert.ok(t.includes(AUTHORED_WORDING.exactValues));
  assert.ok(t.includes(AUTHORED_WORDING.differencesHeading));
  assert.match(html, /data-testid="research-onset-support"/);
  assert.ok(t.includes(AUTHORED_WORDING.scenarioSupportHeading));
});

test("the field table gives 4 significant digits on screen and the exact double in Exact values", () => {
  seedHost("complete");
  const html = panel({ defaultOpen: true, defaultOpenModules: true });
  const depth = completeResponse("x:1").researchModels!.keyholeCavity!.fields.cavityDepth_um.value as number;
  assert.ok(text(html).includes(sig4(depth)));
  assert.ok(text(html).includes(String(depth)), "exact value in the expandable row");
  assert.equal(sig4(214.19283), "214.2");
  assert.equal(sig4(0.00008), "0.00008");
  assert.equal(sig4(1.23456789e-10), "1.235e-10");
  assert.equal(sig4(0), "0");
});

test("pending band: the nominal values show and the band reads as pending, with no min or max numbers", () => {
  seedHost("band-pending");
  const html = panel({ defaultOpen: true, defaultOpenModules: true });
  const t = text(html);
  assert.ok(t.includes("Computing scenario range: 20 of 79."));
  assert.ok(t.includes(AUTHORED_WORDING.modulePending));
  assert.equal(t.includes(APPROVED_WORDING.bandCaption), false, "no caption without a band");
  assert.match(html, /<button[^>]*disabled=""[^>]*>Run research models<\/button>/, "Run is disabled while running");
  assert.doesNotMatch(html, /<button[^>]*disabled=""[^>]*>Cancel<\/button>/, "Cancel is enabled while running");
});

test("stale: no research value is rendered and the status says why", () => {
  seedHost("stale");
  const html = panel({ defaultOpen: true, defaultOpenModules: true });
  assert.ok(text(html).includes(AUTHORED_WORDING.stale));
  assert.equal(html.includes("research-results"), false);
  assert.equal(html.includes("research-module-"), false);
});

test("R-UI-6: rendered research text has no banned wording outside the fixed captions", () => {
  seedHost("complete");
  let t = text(panel({ defaultOpen: true, defaultOpenModules: true }));
  for (const allowed of [APPROVED_WORDING.bandCaption, AUTHORED_WORDING.bandDegenerate]) t = t.split(allowed).join(" ");
  const onsetCaveat = completeResponse("x:1").researchModels!.keyholeCavity!.band!.onsetSupport?.caveat;
  if (onsetCaveat) t = t.split(onsetCaveat).join(" ");
  // Contract 13.4 permits only D1's served clause and the physical cavity-wall label.
  for (const allowedPeak of ["The served peak temperature is withheld", "Physical cavity-wall peak temperature"]) t = t.split(allowedPeak).join(" ");
  for (const banned of [/uncertainty band/i, /confidence/i, /error bar/i, /±/, /probability/i, /validated simulation/i, /\bpeak\b/i]) {
    assert.equal(banned.test(t), false, `banned wording ${banned} in the panel text`);
  }
  assert.equal(/[–—]/.test(t), false, "no em or en dash in the rendered text");
});

test("the approved top 25 strings the panel holds are exactly as approved", () => {
  assert.equal(APPROVED_WORDING.panelTitle, "Research model");
  assert.equal(APPROVED_WORDING.badgeResearch, "Research");
  assert.equal(APPROVED_WORDING.badgeScreeningOnly, "Screening only");
  assert.equal(APPROVED_WORDING.badgeNoValidation, "No experimental validation");
  assert.equal(APPROVED_WORDING.scopeLine, "Separate from the served result. Research values never change the served tiles, verdict or exports.");
  assert.equal(APPROVED_WORDING.researchArmLabel, "Literature estimate / Research / not validated");
  assert.equal(APPROVED_WORDING.supportLiterature, "Literature estimate");
  assert.equal(supportText("User input", ["length_m", "deltaTemperature_K"]), "User input: length_m, deltaTemperature_K");
  assert.equal(supportText("Unresolved", ["deltaTemperature_K"]), "Unresolved: deltaTemperature_K");
  assert.equal(supportText(null, []), null);
  assert.equal(APPROVED_WORDING.bandCaption, "Min / nominal / max is an envelope of named one-at-a-time scenarios. Interactions are not evaluated. It is not a confidence interval, an error bar, or a physical lower or upper bound.");
  assert.equal(APPROVED_WORDING.refusalKeyholeThermalFlow, "Not available: no source-bound closure or data exists for the keyhole thermal flow.");
  // the band caption of the real response is the approved one
  assert.equal(completeResponse("x:1").researchModels!.keyholeCavity!.band!.caption, APPROVED_WORDING.bandCaption);
  const d = describeResponse("x:1");
  assert.equal(d.sentences.bandCaption, APPROVED_WORDING.bandCaption);
  assert.equal(d.sentences["refusal.KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE"], APPROVED_WORDING.refusalKeyholeThermalFlow);
  assert.equal(refusalText("KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE", {}), null, "no client override when the server has no text");
  assert.equal(refusalText("KEYHOLE_THERMAL_FLOW_CLOSURE_UNAVAILABLE", d.sentences), APPROVED_WORDING.refusalKeyholeThermalFlow);
});

test("authored strings follow the style rules: no dash punctuation, no hype, no validation claim", () => {
  const all = [...Object.values(AUTHORED_WORDING), ...Object.values(APPROVED_WORDING)];
  for (const s of all) {
    assert.equal(/[–—]/.test(s), false, s);
    assert.equal(/ - /.test(s), false, s);
    assert.equal(/revolutionary|breakthrough|powerful|state-of-the-art|seamless|robust|leverage|unlock/i.test(s), false, s);
    assert.equal(/\b(validated|verified|accurate|reliable)\b/i.test(s.replace(/not validated|No experimental validation|not a known zero uncertainty/gi, "")), false, s);
  }
});

test("difference statements: served numbers only when the served identity matches, else the fallback text", () => {
  const block = completeResponse("x:1").researchModels!;
  const d4 = block.keyholeCavity!.servedDifferences.find((d) => d.id === "D4")!;
  const served = { meltPoolGeometry: { regime: "conduction", depth_um: 88.5 }, keyholeModel: { fabbroDepth_um: 131.25 }, processParameters: { heatSource: "goldak" } };
  const base: DifferenceContext = { host: "melt-pool", alloyId: "ti6al4v", served, servedMatches: true, block };
  const filled = renderServedDifference(d4, base);
  assert.ok(filled.includes("conduction"));
  assert.ok(filled.includes("131.3 um") || filled.includes("131.2 um"), filled);
  assert.equal(filled.includes("{served:"), false);
  assert.equal(filled.includes("{research:"), false);
  assert.equal(renderServedDifference(d4, { ...base, servedMatches: false }), d4.fallback);
  assert.equal(renderServedDifference(d4, { ...base, served: null }), d4.fallback);
  assert.equal(renderServedDifference(d4, { ...base, served: { meltPoolGeometry: {} } }), d4.fallback, "a missing served value falls back");
  // a variant for another host is not chosen
  const buildJob = renderServedDifference(d4, { ...base, host: "build-job" });
  assert.notEqual(buildJob, filled);
  // a null served value prints as unavailable
  const d1 = block.surfaceBalance!.servedDifferences.find((d) => d.id === "D1")!;
  const nullServed = { hydrodynamicsAndRecoil: { peakTemperature_C: null, peakUnavailableReason: "no source-bound surface balance" } };
  const d1Text = renderServedDifference(d1, { ...base, served: nullServed });
  assert.ok(d1Text.includes("no source-bound surface balance"));
  assert.equal(renderServedDifference(d1, { ...base, served: { hydrodynamicsAndRecoil: { peakTemperature_C: 2500 } } }), d1.fallback, "served-null does not hold for a number");
});

test("the Melt Pool host compares only with a served result of the same inputs", () => {
  seedHost("complete");
  const served = { meltPoolGeometry: { regime: "conduction", depth_um: 88.5 }, keyholeModel: { fabbroDepth_um: 131.25 }, processParameters: { heatSource: "goldak" } };
  const matching = text(panel({ defaultOpen: true, defaultOpenModules: true, served, servedSignature: inputSignature(TI64_INPUT) }));
  const other = text(panel({ defaultOpen: true, defaultOpenModules: true, served, servedSignature: inputSignature({ ...TI64_INPUT, laserPower_W: 300 }) }));
  assert.ok(matching.includes("The served regime label (conduction)"));
  assert.equal(other.includes("The served regime label (conduction)"), false);
  assert.ok(other.includes("The served result for these inputs is not loaded."));
});

test("no input: only the header renders, the host sends nothing", () => {
  const html = renderToStaticMarkup(<ResearchModelPanel host="build-job" input={null} served={null} defaultOpen />);
  assert.ok(text(html).includes(APPROVED_WORDING.panelTitle));
  assert.equal(html.includes("research-results"), false);
});

test("both hosts mount the panel and the Build Job host only with a job, without touching the served tiles", () => {
  const root = path.resolve(import.meta.dirname, "..");
  const melt = readFileSync(path.join(root, "src/components/3d-distortion-lab/MeltPool3DCrossSectionLab.tsx"), "utf8");
  const decision = readFileSync(path.join(root, "src/components/3d-distortion-lab/IndustrialLPBFDecisionLab.tsx"), "utf8");
  assert.match(melt, /<ResearchModelPanel host="melt-pool"/);
  assert.match(melt, /servedResearchSignatureRef\.current = researchProcessSignature\(/);
  assert.match(decision, /\{job && researchInput && <ResearchModelPanel host="build-job"/);
  // the melt pool panel sits between the calibrated panel and the solidification section
  assert.ok(melt.indexOf("<CalibratedMeltpoolPanel") < melt.indexOf("<ResearchModelPanel") && melt.indexOf("<ResearchModelPanel") < melt.indexOf("Solidification Kinetics &amp; Microstructure"));
});
