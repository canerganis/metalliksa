import type { QuantityContainer } from "../data/quantityEnvelope";
import { checkedFront, quantityText } from "./solidificationDisplay";
export type PdasBandLike = QuantityContainer;
export const PDAS_BAND_LABEL = "Ni-Nb model alloy, Ghosh 2017";
export function pdasBandText(container: QuantityContainer): string {
  return quantityText(checkedFront(container).quantities.pdas);
}
