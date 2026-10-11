/**
 * P7a (2026-10-11): the served PDAS scalar is null. For IN625/IN718 inside the Ghosh 2017 validity range Python serves
 * a band {hunt, kurzFisher} (um); otherwise null with a reason. This renders the band as "x to y um (Ni-Nb model alloy,
 * Ghosh 2017)" and null as "n/a (reason)". Nothing is computed here.
 */
export interface PdasBandLike {
  pdasBand_um?: { hunt: number; kurzFisher: number } | null;
  pdasUnavailableReason?: string | null;
  unavailableReason?: string | null;
}

export const PDAS_BAND_LABEL = "Ni-Nb model alloy, Ghosh 2017";

export function pdasBandText(kin: PdasBandLike | null | undefined, digits = 2): string {
  const band = kin?.pdasBand_um;
  if (band && Number.isFinite(band.hunt) && Number.isFinite(band.kurzFisher)) {
    const lo = Math.min(band.hunt, band.kurzFisher);
    const hi = Math.max(band.hunt, band.kurzFisher);
    return `${lo.toFixed(digits)} to ${hi.toFixed(digits)} \u00b5m (${PDAS_BAND_LABEL})`;
  }
  const reason = kin?.pdasUnavailableReason ?? kin?.unavailableReason;
  return reason ? `n/a (${reason})` : "n/a";
}
