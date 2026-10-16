import { checkedQuantityContainer } from "../data/quantityEnvelope";
import { QUANTITY_ENVELOPE } from "../generated/quantityEnvelope";
import React from "react";
import { pdasBandText } from "../utils/pdasBandText";
import { checkedFront, FRONT_LABELS, quantityText, quantityScopes, quantityContainerCsv, SOLIDIFICATION_WORDING } from "../utils/solidificationDisplay";
export function SolidificationQuantities({ container, frontOnly = true }: { container: unknown; frontOnly?: boolean }) {
  try {
    const front = frontOnly ? checkedFront(container) : checkedQuantityContainer(container);
    return <div><p className="text-xs text-slate-400">{QUANTITY_ENVELOPE.containerHeaderText[front.moduleEvidenceCeiling]} · {front.moduleMaturity}</p><a className="text-xs underline" download="solidification-quantities.csv" href={`data:text/csv;charset=utf-8,${encodeURIComponent(quantityContainerCsv(front))}`}>Download quantities CSV</a><dl className="grid gap-2 text-xs" data-solidification-envelope>
      {Object.entries(front.quantities).map(([name, q]) => <div key={name} data-quantity={name} data-quantity-status={q.status} className="border-b border-slate-700/50 py-2">
        <dt className="text-slate-400">{FRONT_LABELS[name] ?? name} · {QUANTITY_ENVELOPE.statusLabels[q.status]}</dt>
        <dd className="break-words text-slate-200">{frontOnly && name === "pdas" ? pdasBandText(front) : quantityText(q)}</dd>
        {quantityScopes(front, q).map(scope => <dd key={scope} className="break-words text-slate-400" data-input-scope>{scope}</dd>)}
      </div>)}
    </dl></div>;
  } catch {
    return <p role="status">{SOLIDIFICATION_WORDING.legacy}</p>;
  }
}
