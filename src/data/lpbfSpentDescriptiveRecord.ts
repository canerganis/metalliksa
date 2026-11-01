/// <reference types="vite/client" />
/**
 * The committed spent-set descriptive record, loaded lazily. The glob is non-eager, so Vite emits the record as its own
 * chunk and the comparison chunk is untouched. The newest file by name wins. When no file exists (or outside Vite, for
 * example under tsx) the loader resolves to null and the panel shows its empty state. A malformed committed record
 * throws from checkedSpentDescriptive.
 */
import { checkedSpentDescriptive, type LpbfSpentDescriptiveDocument } from "./lpbfSpentDescriptive";

let loaders: Record<string, () => Promise<unknown>> = {};
try {
  loaders = import.meta.glob("../../docs/LPBF_SPENT_DESCRIPTIVE_*.view.json", { import: "default" }) as Record<string, () => Promise<unknown>>;
} catch {
  loaders = {};
}

export async function loadCommittedSpentDescriptive(): Promise<LpbfSpentDescriptiveDocument | null> {
  const names = Object.keys(loaders).sort();
  const newest = names[names.length - 1];
  if (newest === undefined) return null;
  return checkedSpentDescriptive(await loaders[newest]());
}
