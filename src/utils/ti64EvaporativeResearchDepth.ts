/**
 * C2: the P8 conditional linked melt-depth scenario shown beside a refused evaporative depth.
 *
 * Research only. The request is bound to the completed evaporative result's own provenance inputs (never to the
 * editable store). The P8 properties, absorption and onset rules stay P8's own; nothing from the evaporative solver
 * is forwarded as a P8 boundary condition. Only meltDepthLink.fields.linkedMeltDepth_um is read as the depth; a
 * conditional depth, a cavity depth or a band endpoint never stands in for it.
 */
import { pythonComputationService } from '../services/pythonComputationService';
import {
  RESEARCH_ROUTE_SCHEMA_REQUEST, isResearchLeaf,
  type ResearchFieldBand, type ResearchLeaf, type ResearchOutcome, type ResearchRequest, type ResearchRunResponse,
} from '../types/lpbfResearchModels';
import type { Ti64EvaporativeResult } from '../services/lpbfSimulationService';

export const P8_ROW_TITLE = 'P8 conditional linked melt-depth scenario (research)';
export const W1_CRITERION_NOTE = 'This run crossed its declared recoil/capillary criterion. The fixed-surface depth remains unavailable. This criterion is not an observation of a keyhole.';
export const P8_HYPOTHESIS_NOTE = 'Independent quasi-steady cavity/conduction hypothesis for the same incident power, scan speed, Gaussian 1/e² diameter and preheat. This is not a continuation, correction or replacement of the evaporative result. P8 uses different thermal properties, absorption and onset assumptions and does not resolve surface motion or melt flow. Linked depth is a liquidus envelope below the original surface, not vapour-cavity depth. Neither model is experimentally validated.';
export const P8_BELOW_ONSET_NOTE = 'P8 is at or below its own modeled onset. Any available linked depth is its Gaussian conduction envelope, not a keyhole-depth result.';
export const P8_UNAVAILABLE_SUFFIX = 'No substitute depth is supplied.';
export const P8_NO_FORWARDING_NOTE = 'No evaporative-model losses, temperatures or onset latch are forwarded to P8. P8 uses an IR (1064 nm) flat-plate absorption scenario and its own property resolver.';

/** Only a crossed recoil/capillary onset with resolved geometry bookkeeping starts a pairing; other nulls have other causes. */
export function p8PairingApplies(result: Pick<Ti64EvaporativeResult, 'gate'> | undefined): boolean {
  return !!result && result.gate.onset === true && result.gate.unresolvedGeometry === false;
}

/** Stable identity of the evaporative run's inputs; input edits change it and hide the pairing. */
export function p8PairingKey(result: Pick<Ti64EvaporativeResult, 'provenance'>): string {
  const i = result.provenance.inputs;
  return JSON.stringify([i.material, i.power_W, i.speed_mm_s, i.beamDiameter_um, i.preheat_C]);
}

export function buildP8Request(result: Pick<Ti64EvaporativeResult, 'provenance'>, stage: 'nominal' | 'band', clientRequestId: string,
  supersedeKey: string, timeBudgetMs?: number): ResearchRequest {
  const i = result.provenance.inputs;
  const num = (v: unknown, name: string) => {
    if (typeof v !== 'number' || !Number.isFinite(v)) throw new Error(`Evaporative result input ${name} is not a finite number`);
    return v;
  };
  if (typeof i.material !== 'string') throw new Error('Evaporative result input material is missing');
  return {
    schemaVersion: RESEARCH_ROUTE_SCHEMA_REQUEST, supersedeKey, clientRequestId, stage,
    ...(stage === 'band' ? { timeBudgetMs: timeBudgetMs ?? 1500 } : {}),
    process: {
      material: i.material, laserPower_W: num(i.power_W, 'power_W'), scanSpeed_mm_s: num(i.speed_mm_s, 'speed_mm_s'),
      beamDiameter_um: num(i.beamDiameter_um, 'beamDiameter_um'), preheatTemp_C: num(i.preheat_C, 'preheat_C'),
      laserWavelength: 'IR_1064nm', absorptionModel: 'flat-plate',
    },
    propertyContext: { kind: 'nominal' },
    sender: 'batch-client',
  };
}

export interface P8DepthView {
  status: 'available' | 'unavailable';
  modelId: string | null;
  linked: ResearchLeaf | null;
  powerOverOnset: number | null;
  atOrBelowOnset: boolean;
  band: ResearchFieldBand | null;
  bandCaption: string | null;
  bandPending: boolean;
  consistencySentence: string | null;
  uiSentence: string | null;
  validationStatus: string | null;
  warnings: string[];
  reason: { code: string; text: string } | null;
}

const rec = (v: unknown): Record<string, unknown> | null => typeof v === 'object' && v !== null && !Array.isArray(v) ? v as Record<string, unknown> : null;
const unavailable = (code: string, text: string): P8DepthView => ({
  status: 'unavailable', modelId: null, linked: null, powerOverOnset: null, atOrBelowOnset: false, band: null, bandCaption: null,
  bandPending: false, consistencySentence: null, uiSentence: null, validationStatus: null, warnings: [], reason: { code, text },
});

export function p8ViewFromOutcome(outcome: ResearchOutcome): P8DepthView {
  switch (outcome.kind) {
    case 'refused': return unavailable(outcome.reasonCode, outcome.problems.map(p => p.message).join(' ') || 'The research route refused the request.');
    case 'failed': return unavailable(outcome.reasonCode, 'The research route failed.');
    case 'timeout': return unavailable('RESEARCH_TIMEOUT', 'The research route timed out.');
    case 'superseded': return unavailable('REQUEST_SUPERSEDED', 'A newer research request replaced this one.');
    case 'http-error': return unavailable('HTTP_ERROR', outcome.message);
    case 'malformed': return unavailable('RESPONSE_MALFORMED', outcome.message);
    case 'describe': return unavailable('RESPONSE_MALFORMED', 'Unexpected describe response.');
    case 'run': return p8ViewFromRun(outcome.response);
  }
}

export function p8ViewFromRun(response: ResearchRunResponse): P8DepthView {
  const block = response.researchModels;
  const link = block?.meltDepthLink;
  if (!link) return unavailable('P8_LINKED_DEPTH_MISSING', 'The response has no linked melt-depth container.');
  const cavity = block?.keyholeCavity;
  const leaf = link.fields.linkedMeltDepth_um;
  const reasons = link.consistencyNote.reasons ?? [];
  const sentence = link.consistencyNote.sentence;
  const consistencySentence = isResearchLeaf(sentence) && typeof sentence.value === 'string' ? sentence.value : null;
  const common = {
    modelId: link.modelId, uiSentence: link.uiSentence, validationStatus: link.validationStatus, consistencySentence,
  };
  const value = leaf && isResearchLeaf(leaf) ? leaf.value : null;
  if (link.status !== 'available' || !leaf || typeof value !== 'number' || !Number.isFinite(value)) {
    const code = link.reasonCode ?? leaf?.reasonCode ?? 'P8_LINKED_DEPTH_NULL';
    const text = reasons.find(r => r.code === code)?.cause ?? reasons[0]?.cause ?? link.uiSentence;
    return { ...unavailable(code, text), ...common, validationStatus: link.validationStatus };
  }
  const above = cavity?.fields.modeledAboveOnset?.value;
  const ratio = cavity?.fields.powerOverOnset?.value;
  const band = (leaf as { band?: ResearchFieldBand }).band ?? link.band?.fields?.linkedMeltDepth_um ?? null;
  const warnings = [...leaf.warnings];
  return {
    status: 'available', ...common, linked: leaf,
    powerOverOnset: typeof ratio === 'number' ? ratio : null,
    atOrBelowOnset: above === false || (typeof ratio === 'number' && ratio <= 1),
    band, bandCaption: link.band?.caption ?? null, bandPending: !band || band.completeness === 'pending',
    warnings, reason: null,
  };
}

export const hasRecord = rec;

/** Nominal first (shown at once), then band chunks until complete. `onUpdate` receives every improved view. */
export async function fetchP8Depth(result: Ti64EvaporativeResult, onUpdate: (view: P8DepthView) => void, signal?: AbortSignal,
  maxBandRequests = 24): Promise<void> {
  const suffix = Math.random().toString(36).slice(2, 10).padEnd(8, '0');
  const key = `p8-research:batch:ti64evap${suffix}`;
  let counter = 0;
  const id = () => `ti64-evaporative-pair:${suffix}:${(counter += 1)}`;
  const nominal = await pythonComputationService.solveLpbfResearchModels(buildP8Request(result, 'nominal', id(), key), signal);
  const first = p8ViewFromOutcome(nominal);
  onUpdate(first);
  if (first.status !== 'available') return;
  for (let n = 0; n < maxBandRequests; n += 1) {
    const outcome = await pythonComputationService.solveLpbfResearchModels(buildP8Request(result, 'band', id(), key, 1500), signal);
    if (outcome.kind !== 'run') return; // keep the nominal view; the band stays pending
    if (outcome.response.requestKey !== (nominal.kind === 'run' ? nominal.response.requestKey : '')) return;
    if (outcome.response.progress.complete && outcome.response.researchModels) {
      onUpdate(p8ViewFromRun(outcome.response));
      return;
    }
  }
}
