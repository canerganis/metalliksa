import assert from "node:assert/strict";
import test from "node:test";
import {
  DISPLAY_CAP_LABEL,
  FALLBACK_VAPOR_CAP_C,
  colourScaleDisplayCap_C,
  colourScaleIsDisplayCap,
  colourScalePeak_C,
  peakTemperatureBasisLabel,
  servedTemperatureText,
} from "../src/utils/peakTemperatureDisplay";

// P6 containment (2026-10-11): the served peak is the loss-free Eagar-Tsai surface maximum, null above the sourced
// vapour temperature or where none exists; the colour scale uses a labelled display cap, never a clipped temperature.
const result = (peak: number | null, over: Record<string, unknown> = {}) => ({
  hydrodynamicsAndRecoil: {
    peakTemperature_C: peak, surfaceTemperature_C: peak, peakTemperatureBasis: "eagar-tsai-loss-free-surface-maximum",
    knudsenRecoilPressure_kPa: null, marangoniNumber: null, pecletThermalNumber: 1, powderDenudationWidth_um: null,
    ...over,
  },
});

test("display cap: sourced T_v (316L 3086 K) or the fallback, whichever max with 1.5 liquidus", () => {
  // 316L: sourced 2812.85 C above 1.5 * 1400 = 2100.
  assert.equal(colourScaleDisplayCap_C(result(null, { vaporTemperatureSourced_C: 2812.85 }), 1400), 2812.85);
  // IN718 (unsourced): the display fallback 3500 C above 1.5 * 1336.
  assert.equal(colourScaleDisplayCap_C(result(null), 1336), FALLBACK_VAPOR_CAP_C);
  // A very high liquidus: 1.5 * liquidus wins over the fallback.
  assert.equal(colourScaleDisplayCap_C(result(null), 2500), 3750);
});

test("a null peak (above T_v or unsourced) uses the display cap and says so", () => {
  const r = result(null, { vaporTemperatureSourced_C: 2812.85, peakUnavailableReason: "above the sourced vapour temperature" });
  assert.equal(colourScalePeak_C(r, 1400), 2812.85);
  assert.equal(colourScaleIsDisplayCap(r, 1400), true);
  assert.equal(DISPLAY_CAP_LABEL, "display cap, not a temperature claim");
});

test("a served peak below the cap is the scale top; a numeric legacy peak above it is capped", () => {
  const low = result(1363.2, { vaporTemperatureSourced_C: 2812.85 });
  assert.equal(colourScalePeak_C(low, 1400), 1363.2);
  assert.equal(colourScaleIsDisplayCap(low, 1400), false);
  // Legacy payload (pre-P6): numeric peak 35 097 C, surfaceTemperature_C = min(peak, T_vap) = 2850, no sourced value.
  const legacy = result(35097, { surfaceTemperature_C: 2850, peakTemperatureBasis: "regularised-singular-source-value" });
  assert.equal(colourScalePeak_C(legacy, 1336), 2850);
  assert.equal(colourScaleIsDisplayCap(legacy, 1336), true);
  // Legacy payload without surfaceTemperature_C still falls back to the display bound.
  assert.equal(colourScalePeak_C(result(35097, { surfaceTemperature_C: undefined }), 1336), 3500);
});

test("basis label text for the P6 basis and the older labels; null without a label", () => {
  assert.match(peakTemperatureBasisLabel(result(null)) ?? "", /loss-free Eagar-Tsai surface maximum/);
  assert.match(peakTemperatureBasisLabel(result(35097, { peakTemperatureBasis: "regularised-singular-source-value" })) ?? "", /not a wall temperature/);
  assert.match(peakTemperatureBasisLabel(result(19000, { peakTemperatureBasis: "distributed-source-conduction-centre-value" })) ?? "", /not a wall temperature/);
  assert.equal(peakTemperatureBasisLabel(result(2500, { peakTemperatureBasis: undefined })), null);
});

test("served temperature text: number with unit, else n/a with the reason", () => {
  assert.equal(servedTemperatureText(1363.2), "1363.2 °C");
  assert.equal(servedTemperatureText(null), "n/a");
  assert.equal(servedTemperatureText(undefined, "no sourced vapour temperature"), "n/a (no sourced vapour temperature)");
});
