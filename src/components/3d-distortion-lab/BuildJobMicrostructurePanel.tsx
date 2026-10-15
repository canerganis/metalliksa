import React from "react";
import { Layers } from "lucide-react";
import { SolidificationQuantities } from "../SolidificationQuantities";
import { BuildJobSegregationPanel } from "./BuildJobSegregationPanel";
import type { QuantityContainer } from "../../data/quantityEnvelope";
export type BuildJobMicrostructureLike = QuantityContainer & { status?: string; modelId?: string };
export const BuildJobMicrostructurePanel: React.FC<{ micro: unknown; segregation?: unknown }> = ({ micro, segregation }) => !micro && segregation === undefined ? null : <div className="space-y-2">
  {!!micro && <><h3 className="flex items-center gap-2 text-xs font-bold text-white"><Layers className="h-4 w-4 text-teal-400" />Solidification Microstructure</h3>
  <SolidificationQuantities container={micro} /></>}
  {segregation !== undefined && <BuildJobSegregationPanel segregation={segregation} />}
</div>;
