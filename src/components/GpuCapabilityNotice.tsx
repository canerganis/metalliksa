import React from 'react';
import { gpuCapabilityMessage, type GpuCapability } from '../utils/gpuCapability';

/** Uses the engine availability dialog's neutral, accessible unavailable-state presentation. */
export function GpuCapabilityNotice({ capability }: { capability: GpuCapability }) {
  return <p role="status" className="rounded-lg border border-amber-500/30 p-3 text-sm text-amber-200">{gpuCapabilityMessage(capability)}</p>;
}
