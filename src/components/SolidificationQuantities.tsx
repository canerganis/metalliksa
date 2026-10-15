import { checkedQuantityContainer } from "../data/quantityEnvelope";
import { QUANTITY_ENVELOPE } from "../generated/quantityEnvelope";
import React from "react";
import { pdasBandText } from "../utils/pdasBandText";
import { checkedFront, FRONT_LABELS, quantityText, SOLIDIFICATION_WORDING } from "../utils/solidificationDisplay";
export function SolidificationQuantities({ container, frontOnly = true }: { container: unknown; frontOnly?: boolean }) {
  try {
    const front = frontOnly ? checkedFront(container) : checkedQuantityContainer(container);
    return <div><p className="text-xs text-slate-400">{QUANTITY_ENVELOPE.containerHeaderText[front.moduleEvidenceCeiling]} · {front.moduleMaturity}</p><dl className="grid gap-2 text-xs" data-solidification-envelope>
      {Object.entries(front.quantities).map(([name, q]) => <div key={name} data-quantity={name} data-quantity-status={q.status} className="border-b border-slate-700/50 py-2">
        <dt className="text-slate-400">{FRONT_LABELS[name] ?? name} · {QUANTITY_ENVELOPE.statusLabels[q.status]}</dt>
        <dd className="break-words text-slate-200">{frontOnly && name === "pdas" ? pdasBandText(front) : quantityText(q)}</dd>
      </div>)}
    </dl></div>;
  } catch {
    return <p role="status">{SOLIDIFICATION_WORDING.legacy}</p>;
  }
}
