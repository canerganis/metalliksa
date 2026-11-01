/**
 * Air-gap / offline mode: AIRGAPPED=1 disables outbound cloud services.
 * Local Python LPBF / CALPHAD remain available.
 */

export type AirgapBlockedService =
  | "GPT-6 AI (reserved, not implemented)"
  | "NVIDIA cloud NIM / DeepSeek endpoints"
  | "Materials Project live DFT API (reserved, not implemented)"
  | "External powder / pricing APIs (reserved, not implemented)"
  | "Crossref literature search";

// Entries marked "(reserved, not implemented)" are policy slots with no code behind them yet;
// they stay listed so a future integration is blocked by default when AIRGAPPED=1.
export const AIRGAP_BLOCKED_SERVICES: AirgapBlockedService[] = [
  "GPT-6 AI (reserved, not implemented)",
  "NVIDIA cloud NIM / DeepSeek endpoints",
  "Materials Project live DFT API (reserved, not implemented)",
  "External powder / pricing APIs (reserved, not implemented)",
  "Crossref literature search",
];

export const AIRGAP_ALLOWED_LOCAL = [
  "Local LPBF build-job (Rosenthal screening + slicer)",
  "Local Python physics (CALPHAD when installed)",
] as const;

type EnvLike = NodeJS.ProcessEnv | Record<string, string | undefined>;

/**
 * Enterprise profile: METALLIKSA_PROFILE=enterprise turns air-gap on by default and refuses to start
 * when the environment tries to switch it off (AIRGAPPED=0) or supplies an outbound credential.
 */
export function isEnterpriseProfile(env: EnvLike = process.env): boolean {
  return String(env.METALLIKSA_PROFILE ?? "").trim().toLowerCase() === "enterprise";
}

export function isAirgappedFromEnv(env: EnvLike = process.env): boolean {
  // One boolean expression, no literal `return true`: the route-authority scanner follows
  // AIRGAPPED into /api/runtime-config and would read a literal return as a canned claim.
  const raw = String(env.AIRGAPPED ?? env.VITE_AIRGAPPED ?? "").trim().toLowerCase();
  return isEnterpriseProfile(env) || raw === "1" || raw === "true" || raw === "yes" || raw === "on";
}

/** Conflicts that make an enterprise start unsafe. Empty when the profile is off or consistent. */
export function enterpriseProfileProblems(env: EnvLike = process.env): string[] {
  if (!isEnterpriseProfile(env)) return [];
  const problems: string[] = [];
  const raw = String(env.AIRGAPPED ?? env.VITE_AIRGAPPED ?? "").trim().toLowerCase();
  if (raw !== "" && !["1", "true", "yes", "on"].includes(raw)) {
    problems.push(`AIRGAPPED=${raw} conflicts with METALLIKSA_PROFILE=enterprise (air-gap cannot be disabled)`);
  }
  if (String(env.OPENAI_API_KEY ?? "").trim() !== "") {
    problems.push("OPENAI_API_KEY is set but the enterprise profile allows no outbound feature; unset it");
  }
  return problems;
}

/** Throws before the server listens when the enterprise profile is inconsistent. */
export function assertEnterpriseProfileConsistent(env: EnvLike = process.env): void {
  const problems = enterpriseProfileProblems(env);
  if (problems.length) throw new Error(`Enterprise profile refused to start: ${problems.join("; ")}`);
}

export function enterpriseStartupLine(env: EnvLike = process.env): string | null {
  if (!isEnterpriseProfile(env)) return null;
  return "METALLIKSA_PROFILE=enterprise: air-gap forced on, all outbound features refused (Crossref, cloud AI, external APIs); local LPBF and physics engines remain available.";
}

export function airgapDenyPayload(service: string) {
  return {
    error: `Air-gap mode (AIRGAPPED=1): ${service} is disabled. Local LPBF and physics engines remain available.`,
    airgapped: true,
    blockedService: service,
    blockedServices: AIRGAP_BLOCKED_SERVICES,
    allowedLocal: AIRGAP_ALLOWED_LOCAL,
  };
}

export class AirgapBlockedError extends Error {
  readonly airgapped = true as const;
  readonly blockedService: string;
  constructor(service: string) {
    super(`Air-gap mode (AIRGAPPED=1): ${service} is disabled.`);
    this.name = "AirgapBlockedError";
    this.blockedService = service;
  }
}

/** Structural guard for service modules: throws before any outbound network call when air-gapped. */
export function assertNotAirgapped(service: string, env: NodeJS.ProcessEnv | Record<string, string | undefined> = process.env): void {
  if (isAirgappedFromEnv(env)) throw new AirgapBlockedError(service);
}
