/**
 * Loads KaTeX (and its stylesheet) only when a "How this is calculated" panel is first opened, so the entry bundle does
 * not carry it. The promise is cached; a failed load is not cached, so a later open retries.
 */
export interface KatexRenderer {
  renderToString(latex: string, options?: { displayMode?: boolean; throwOnError?: boolean; output?: "html" | "mathml" | "htmlAndMathml" }): string;
}

let pending: Promise<KatexRenderer> | null = null;

export function loadKatex(): Promise<KatexRenderer> {
  if (!pending) {
    pending = (async () => {
      const [module] = await Promise.all([import("katex"), importKatexStyles()]);
      return (module.default ?? module) as unknown as KatexRenderer;
    })();
    pending.catch(() => { pending = null; });
  }
  return pending;
}

async function importKatexStyles(): Promise<void> {
  // Side-effect stylesheet import; resolved by Vite at build time, skipped where no DOM exists.
  if (typeof document === "undefined") return;
  await import("katex/dist/katex.min.css");
}
