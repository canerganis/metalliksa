/**
 * Phase 6a validation envelope relayed by the server as HTTP 422:
 * { success: false, error: { code, field, message, detail }, errorKind: "validation" }.
 *
 * A validation failure means the request itself is invalid (for example an unknown
 * alloy or element). Callers must surface it instead of falling back to a client
 * formula that would silently compute something else.
 */
export class PythonValidationError extends Error {
  readonly code: string;
  readonly field: string;
  readonly detail: Record<string, unknown>;

  constructor(message: string, code: string, field: string, detail: Record<string, unknown> = {}) {
    super(message);
    this.name = "PythonValidationError";
    this.code = code;
    this.field = field;
    this.detail = detail;
  }
}

export function isPythonValidationError(err: unknown): err is PythonValidationError {
  return err instanceof PythonValidationError;
}

/** Read either the legacy string error or the typed worker envelope exactly once. */
export async function pythonRequestError(res: Pick<Response, 'status' | 'json'>, fallback: string): Promise<Error> {
  let body: any;
  try { body = await res.json(); } catch { return new Error(fallback); }
  const error = body?.error;
  const fields = error && typeof error === 'object' ? error : body;
  const message = typeof error === 'string' ? error : typeof error?.message === 'string' ? error.message : fallback;
  if (body?.errorKind === 'validation') {
    return new PythonValidationError(message, typeof fields?.code === 'string' ? fields.code : 'VALIDATION',
      typeof fields?.field === 'string' ? fields.field : '', fields?.detail ?? {});
  }
  return new Error(message);
}

/**
 * Returns a PythonValidationError when `res` is a 422 carrying the validation
 * envelope, otherwise null (the body is only read for 422 responses).
 */
export async function validationErrorFromResponse(
  res: Pick<Response, "status" | "json">,
  prefix: string,
): Promise<PythonValidationError | null> {
  if (res.status !== 422) return null;
  let body: any;
  try {
    body = await res.json();
  } catch {
    return null;
  }
  if (!body || body.errorKind !== "validation" || !body.error || typeof body.error !== "object") {
    return null;
  }
  const { code, field, message, detail } = body.error;
  const text = typeof message === "string" && message ? message : "Invalid input";
  return new PythonValidationError(
    `${prefix}: ${text}`,
    typeof code === "string" ? code : "VALIDATION",
    typeof field === "string" ? field : "",
    detail && typeof detail === "object" ? detail : {},
  );
}
