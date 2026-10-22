import React, { useId } from 'react';
import { contractById, type EvidenceType, type OracleState, type RegisteredContract } from '../../modules/registry';

// Phase 7 module SDK: shows a contracted module's maximum evidence claim (the contract ceiling) and
// oracle state from the committed core registry (src/generated/moduleRegistryCore.ts). It needs no
// server, takes no evidence input and never derives or upgrades a claim; legacy modules render nothing.

// Labels match the evidence legend in the App header.
const EVIDENCE_LABELS: Record<EvidenceType, string> = {
  measured: 'Measured',
  'validated-simulation': 'Validated simulation',
  'calibrated-simulation': 'Calibrated simulation',
  'literature-estimate': 'Literature estimate',
  'screening-only': 'Screening only',
  unresolved: 'Unresolved',
};

export interface EvidenceBadgeView {
  readonly ceiling: EvidenceType;
  readonly oracle: OracleState;
  readonly text: string;
  readonly description: string;
}

type BadgeContract = Pick<RegisteredContract, 'migrationState' | 'evidence' | 'tests'>;

/** Pure projection of the contract; the ceiling shown is always the contract's own. */
export function evidenceBadgeView(contract: BadgeContract | undefined): EvidenceBadgeView | null {
  if (!contract || contract.migrationState !== 'contracted') return null;
  const ceiling: EvidenceType = contract.evidence.ceiling;
  const { status, ciNote, scope } = contract.tests.oracle;
  const oracle = status === 'present' ? `An independent reference check exists. ${scope ?? ''}` : 'No independent reference check exists yet, so the claim level stays capped.';
  return {
    ceiling,
    oracle: status,
    text: `Strongest claim allowed: ${EVIDENCE_LABELS[ceiling]}. Reference check: ${status === 'present' ? 'available' : 'not yet available'}`,
    description: 'The strongest kind of evidence this module is allowed to report. '
      + `This is a limit, not a grade for any single result, and not a validation. ${oracle.trim()}${ciNote ? ` ${ciNote}` : ''}`,
  };
}

/** Renders a given contract (exported for tests); the app uses EvidenceBadge by module id. */
export function ContractEvidenceBadge({ contract }: { readonly contract: BadgeContract | undefined }) {
  const descriptionId = useId();
  const view = evidenceBadgeView(contract);
  if (!view) return null;
  return (
    <>
      <span className="mk-count-badge text-[11px]" title={view.description} aria-describedby={descriptionId}
        data-evidence-ceiling={view.ceiling} data-oracle={view.oracle}>
        {view.text}
      </span>
      <span id={descriptionId} className="mk-sr-only">{view.description}</span>
    </>
  );
}

export function EvidenceBadge({ moduleId }: { readonly moduleId: string }) {
  return <ContractEvidenceBadge contract={contractById(moduleId)} />;
}

/**
 * Module-header form of the same projection: the max-claim badge and its explanation sit behind a small
 * disclosure so the header leads with the title, the maturity badge and what the module is for. The text is
 * exactly the badge text and description above (one click away, keyboard operable). Legacy modules render nothing.
 */
export function ModuleEvidenceDisclosure({ moduleId, detail }: { readonly moduleId: string; readonly detail?: string }) {
  const view = evidenceBadgeView(contractById(moduleId));
  if (!view) return detail ? <details className="mk-about"><summary>About this module</summary><div className="mk-about-body"><p>{detail}</p></div></details> : null;
  return (
    <details className="mk-about" data-evidence-ceiling={view.ceiling} data-oracle={view.oracle}>
      <summary>What this result can claim</summary>
      <div className="mk-about-body">
        <p><span className="mk-count-badge text-[11px]">{view.text}</span></p>
        <p>{view.description}</p>
        {detail && <p>{detail}</p>}
      </div>
    </details>
  );
}
