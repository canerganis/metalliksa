/**
 * One display locale for formatted numbers, independent of the browser locale.
 * en-US: comma groups thousands, point marks decimals ("1,200 mm/s", "31.25 J/mm³"), matching the
 * en-US formatting already used for step counts and result values. Only the presentation changes:
 * the same rounding (maximumFractionDigits) is applied to the same value.
 */
export const DISPLAY_LOCALE = "en-US";

export function formatDisplayNumber(value: number, maximumFractionDigits = 1): string {
  return value.toLocaleString(DISPLAY_LOCALE, { maximumFractionDigits });
}

/**
 * en-US grouping with exactly the digits String(value) shows: no rounding, so a raw input value such as
 * 1200 or 0.0005 reads "1,200" / "0.0005". String() gives the shortest round-trip decimal; ICU rounding the
 * same double to that many fraction digits yields the same digits. Exponent forms, non-finite values, -0
 * and more than 20 fraction digits (the portable maximumFractionDigits limit) are returned as String() shows them.
 */
export function formatExactNumber(value: number): string {
  const text = String(value);
  const digits = text.split(".")[1]?.length ?? 0;
  if (!Number.isFinite(value) || value === 0 || digits > 20 || /e/i.test(text)) return text;
  return value.toLocaleString(DISPLAY_LOCALE, { maximumFractionDigits: digits });
}

/** Thin space (U+2009): the one separator between a number and its unit. */
export const THIN_SPACE = "\u2009";

const SUPERSCRIPT: Readonly<Record<string, string>> = { "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "-": "⁻" };

/** Unit as displayed: ASCII "um" and "µm" spellings become "µm" (micro sign), every other unit is unchanged. */
export function displayUnit(unit: string): string {
  return unit.replace(/(^|[^A-Za-z])um(?![A-Za-z])/g, "$1µm");
}

/**
 * Scientific notation as "1.7 × 10⁷" (not "1.7e+7"). `digits` is the number of significant digits and is kept exactly
 * (2.0 × 10⁷ stays two digits). Non-finite values return "—".
 */
export function formatScientific(value: number, digits = 3): string {
  if (!Number.isFinite(value)) return "—";
  const [mantissa, exponent] = value.toExponential(Math.max(0, Math.round(digits) - 1)).split("e");
  const power = String(Number(exponent)).split("").map(ch => SUPERSCRIPT[ch] ?? ch).join("");
  return `${mantissa} × 10${power}`;
}

/**
 * A number at `digits` significant digits (3 by default), en-US grouping, with the same value as the input rounded once.
 * Values below `sciBelow` or at/above `sciFrom` (in magnitude, nonzero) use scientific notation so a small value is never
 * rounded to zero. Non-finite values return "—". Show exact values in a tooltip or table where they are shown today.
 */
export function formatSignificant(value: number, digits = 3, sciBelow = 1e-3, sciFrom = 1e7): string {
  if (!Number.isFinite(value)) return "—";
  if (value === 0) return "0";
  const magnitude = Math.abs(value);
  if (magnitude < sciBelow || magnitude >= sciFrom) return formatScientific(value, digits);
  return value.toLocaleString(DISPLAY_LOCALE, { maximumSignificantDigits: digits });
}

/** A value with its unit: thin space between them, "um" shown as "µm", "%" attached without a space. */
export function formatWithUnit(value: number, unit: string, digits = 3): string {
  const text = formatSignificant(value, digits);
  if (!unit) return text;
  return unit === "%" ? `${text}%` : `${text}${THIN_SPACE}${displayUnit(unit)}`;
}
