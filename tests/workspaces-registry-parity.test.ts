import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { MODULES, WORKSPACES } from '../src/data/workspaces';

// Golden re-captured at the rename closure; labels changed on purpose.
// IDs, order and maturity remain stable.
const golden = JSON.parse(readFileSync(new URL('./fixtures/modules-nav-golden.json', import.meta.url), 'utf8')) as Array<{
  id: string; workspace: string; label: string; scope: string; description: string; next: string;
}>;

test('MODULES equals the approved naming golden navigation list (ids, order, labels, workspace, maturity)', () => {
  const current = MODULES.map(m => ({ id: m.id, workspace: m.workspace, label: m.label, scope: m.scope, description: m.description, next: m.next }));
  assert.equal(golden.length, current.length);
  assert.deepEqual(current, golden);
});

test('approved functional names retain module identities and conservative conditional labels', () => {
  const labels = new Map(MODULES.map(module => [module.id, module.label]));
  const expected = {
    '3d-distortion-lab': 'LPBF Workflow',
    'lpbf-optimizer': 'Process Parameter Search',
    'experimental-validation': 'Melt Pool vs Published Measurements',
  } as const;
  for (const [id, label] of Object.entries(expected)) {
    assert.equal(labels.get(id as typeof MODULES[number]['id']), label, id);
  }
  assert.deepEqual(WORKSPACES.map(workspace => workspace.label), [
    'LPBF Engineering', 'Materials & Characterization', 'Evidence & Records',
  ]);
});
