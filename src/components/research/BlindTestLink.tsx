import React from 'react';
import { useResearchStore } from '../../store/useResearchStore';

/** Opens the Research Hub on the "Your blind test" tab (pattern of ResearchIntegrationPanel). */
export function openBlindTest(): void {
  useResearchStore.getState().setActiveTab('blind-test');
  window.dispatchEvent(new CustomEvent('metallix-navigate-tab', { detail: { tabId: 'research-hub' } }));
}

export const BLIND_TEST_CTA_LABEL = 'Test the model on your own tracks';

export function BlindTestCallToAction() {
  return <button type="button" onClick={openBlindTest} className="inline-flex items-center rounded-lg border border-sky-600 bg-sky-950/60 px-3 py-2 text-xs font-semibold text-sky-200 hover:border-sky-400">{BLIND_TEST_CTA_LABEL}</button>;
}

/** One line for the top of the Melt Pool vs Measurements lab. */
export function BlindTestPointer() {
  return <p className="text-xs text-slate-400" data-testid="blind-test-pointer">To score the model on your own measurements, open <button type="button" onClick={openBlindTest} className="text-sky-300 underline">Your blind test</button> in the Research Hub.</p>;
}
