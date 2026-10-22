/**
 * Holds back a value while a slider is being used. `touch()` marks a slider edit; while an edit is pending,
 * `value(v)` only remembers v and (re)starts a quiet timer; the remembered value is committed when the slider
 * is released (`release()`) or `delayMs` after the last value, whichever comes first. Without a pending edit
 * `value(v)` commits at once (presets, shared-material sync, database changes).
 */
export interface DeferredCommit<T> {
  touch(): void;
  value(next: T): void;
  release(): void;
  reset(): void;
  dispose(): void;
}

export function createDeferredCommit<T>(commit: (value: T) => void, delayMs: number): DeferredCommit<T> {
  let pending = false;
  let has = false;
  let latest: T | undefined;
  let timer: ReturnType<typeof setTimeout> | null = null;
  const stop = () => { if (timer !== null) clearTimeout(timer); timer = null; };
  const flush = () => {
    stop();
    pending = false;
    if (has) { has = false; commit(latest as T); }
  };
  return {
    touch() { pending = true; },
    value(next: T) {
      latest = next;
      if (!pending) { stop(); has = false; commit(next); return; }
      has = true;
      stop();
      timer = setTimeout(flush, delayMs);
    },
    release: flush,
    reset() { stop(); pending = false; has = false; },
    dispose() { stop(); },
  };
}
