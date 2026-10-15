/**
 * Python-compatible canonical JSON for LPBF build-job snapshot hashes.
 *
 * Python's json.dumps emits integral floats with `.0` and switches to
 * scientific notation at different magnitude thresholds than JSON.stringify.
 * In build-job snapshot schema v1 every material-property number is a Python
 * float; identity schema versions are integers. Keep these rules schema-bound
 * so parsed JSON's lost integer/float distinction cannot silently change the
 * bytes being authenticated.
 */
function pythonFloat(value: number): string {
  if (!Number.isFinite(value)) throw new Error("Build-job snapshots require finite numbers");
  if (Object.is(value, -0)) return "-0.0";
  if (value === 0) return "0.0";

  const raw = value.toString().toLowerCase();
  const exponentIndex = raw.indexOf("e");
  const magnitude = Math.abs(value);
  const useExponent = magnitude < 1e-4 || magnitude >= 1e16;

  if (useExponent) {
    let digits: string;
    let decimalIndex: number;
    if (exponentIndex >= 0) {
      const [mantissa, exponentText] = raw.split("e");
      const exponent = Number(exponentText);
      const point = mantissa.indexOf(".");
      const beforePoint = point < 0 ? mantissa.length : point;
      digits = mantissa.replace(".", "");
      decimalIndex = beforePoint + exponent;
    } else {
      const point = raw.indexOf(".");
      decimalIndex = point < 0 ? raw.length : point;
      digits = raw.replace(".", "");
    }
    const first = digits.search(/[1-9]/);
    const significant = digits.slice(first).replace(/0+$/, "") || "0";
    const scientificExponent = decimalIndex - first - 1;
    const mantissa = significant.length === 1
      ? significant
      : `${significant[0]}.${significant.slice(1)}`;
    const sign = scientificExponent >= 0 ? "+" : "";
    const paddedExponent = `${sign}${scientificExponent < 0 ? "-" : ""}${String(Math.abs(scientificExponent)).padStart(2, "0")}`;
    return `${value < 0 ? "-" : ""}${mantissa}e${paddedExponent}`;
  }

  if (exponentIndex < 0) return raw.includes(".") ? raw : `${raw}.0`;
  const [mantissa, exponentText] = raw.split("e");
  const exponent = Number(exponentText);
  const negative = mantissa.startsWith("-");
  const unsigned = negative ? mantissa.slice(1) : mantissa;
  const point = unsigned.indexOf(".");
  const beforePoint = point < 0 ? unsigned.length : point;
  const digits = unsigned.replace(".", "");
  const newPoint = beforePoint + exponent;
  let expanded: string;
  if (newPoint <= 0) expanded = `0.${"0".repeat(-newPoint)}${digits}`;
  else if (newPoint >= digits.length) expanded = `${digits}${"0".repeat(newPoint - digits.length)}.0`;
  else expanded = `${digits.slice(0, newPoint)}.${digits.slice(newPoint)}`;
  return `${negative ? "-" : ""}${expanded}`;
}

function canonical(value: unknown, snapshotNumbersAreFloats: boolean): string {
  if (value === null || typeof value === "string" || typeof value === "boolean") return JSON.stringify(value);
  if (typeof value === "number") return snapshotNumbersAreFloats ? pythonFloat(value) : JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(item => canonical(item, snapshotNumbersAreFloats)).join(",")}]`;
  if (value && typeof value === "object" && Object.getPrototypeOf(value) === Object.prototype) {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record).sort().map(key => `${JSON.stringify(key)}:${canonical(record[key], snapshotNumbersAreFloats && key !== "schemaVersion")}`).join(",")}}`;
  }
  throw new Error("Build-job identity must contain plain JSON values");
}

export function canonicalBuildJobMaterialSnapshot(snapshot: unknown): string {
  if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot)) throw new Error("Invalid build-job material snapshot");
  const value = snapshot as Record<string, unknown>;
  if (value.schemaVersion !== 1 || typeof value.alloyId !== "string"
    || !value.thermal || typeof value.thermal !== "object" || Array.isArray(value.thermal)
    || !value.slicer || typeof value.slicer !== "object" || Array.isArray(value.slicer)) {
    throw new Error("Unsupported build-job material snapshot schema");
  }
  // P7b freezes the numeric kernel ledger identity for ledger-backed alloys;
  // Python omits this field for other alloys. Keep both root shapes closed.
  const fields = Object.keys(value).sort().join(",");
  if (fields !== "alloyId,schemaVersion,slicer,thermal"
    && fields !== "alloyId,kernelLedgerSha256,schemaVersion,slicer,thermal") {
    throw new Error("Invalid build-job material snapshot fields");
  }
  if (Object.hasOwn(value, "kernelLedgerSha256")
    && (typeof value.kernelLedgerSha256 !== "string" || !/^[a-f0-9]{64}$/.test(value.kernelLedgerSha256))) {
    throw new Error("Invalid build-job material snapshot kernel ledger SHA-256");
  }
  return canonical(snapshot, true);
}

export function canonicalBuildJobIdentity(identity: unknown): string {
  if (!identity || typeof identity !== "object" || Array.isArray(identity)) throw new Error("Invalid build-job identity");
  const record = identity as Record<string, unknown>;
  if (Object.keys(record).sort().join(",") !== "alloyId,materialPropertyRevision,materialPropertySchemaVersion,materialPropertySha256,modelId,schemaVersion,sha256,solverRevision") {
    throw new Error("Invalid build-job identity fields");
  }
  const { sha256: _sha256, ...payload } = record;
  if (payload.schemaVersion !== 1 || !Number.isSafeInteger(payload.materialPropertySchemaVersion)) {
    throw new Error("Unsupported build-job identity schema");
  }
  return canonical(payload, false);
}

export async function sha256Utf8(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value);
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
}
