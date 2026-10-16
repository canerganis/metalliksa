export type GpuCapabilityCode = 'gpu-runtime-missing' | 'gpu-device-missing';
export interface GpuCapability { available: false; code: GpuCapabilityCode }

export function gpuCapability(value: unknown): GpuCapability | null {
  if (typeof value !== 'object' || value === null) return null;
  const state = value as Record<string, unknown>;
  return state.available === false && (state.code === 'gpu-runtime-missing' || state.code === 'gpu-device-missing')
    ? { available: false, code: state.code } : null;
}

export function gpuCapabilityMessage(state: GpuCapability): string {
  const reason = state.code === 'gpu-runtime-missing'
    ? 'no GPU runtime (NVIDIA Warp)' : 'no available CUDA device for this request';
  return `The GPU thermal solver uses NVIDIA Warp to compute heat flow on an NVIDIA GPU. This install has ${reason}. CPU solvers still work. Enable the Docker GPU option on a machine with NVIDIA GPU support to use this solver.`;
}

export function warpCapabilityFromInventory(caps: unknown): GpuCapability | null {
  if (typeof caps !== 'object' || caps === null) return null;
  const inventory = (caps as { gpuDevices?: { warp?: { capability?: unknown } } }).gpuDevices;
  return gpuCapability(inventory?.warp?.capability);
}

export class GpuCapabilityError extends Error {
  constructor(public readonly capability: GpuCapability) { super(gpuCapabilityMessage(capability)); }
}
