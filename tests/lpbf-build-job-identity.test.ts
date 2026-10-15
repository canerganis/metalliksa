import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { test } from 'node:test';
import { getHostPython } from '../server/pythonRuntime';
import { canonicalBuildJobMaterialSnapshot } from '../src/utils/lpbfBuildJobIdentity';

// Read the actual producer, including its independent Python JSON digest. These
// are material inputs, not measured data or a physical-validation fixture.
function pythonSnapshots(): [Record<string, unknown>, string][] {
  const python = getHostPython();
  const generated = spawnSync(python.cmd, [...python.prefix, '-B', '-c', [
    'import json, sys',
    'sys.path.insert(0, "python")',
    'from four_alloy_materials import THERMAL_NAME, SLICER_NAME',
    'from lpbf_build_job_material_snapshot import build_material_property_snapshot',
    'print(json.dumps([build_material_property_snapshot(a, THERMAL_NAME[a], SLICER_NAME[a]) for a in ("ti6al4v", "alsi10mg")]))',
  ].join('\n')], { encoding: 'utf8', windowsHide: true, timeout: 30_000 });
  assert.equal(generated.status, 0, generated.error?.message ?? generated.stderr);
  return JSON.parse(generated.stdout);
}

for (const [snapshot, pythonSha256] of pythonSnapshots()) {
  test(`${snapshot.alloyId}: real P7b snapshot hashes identically to Python`, () => {
    assert.match(snapshot.kernelLedgerSha256 as string, /^[a-f0-9]{64}$/);
    const canonical = canonicalBuildJobMaterialSnapshot(snapshot);
    assert.equal(createHash('sha256').update(canonical).digest('hex'), pythonSha256);
    const changedLedger = { ...snapshot, kernelLedgerSha256: '0'.repeat(64) };
    assert.notEqual(createHash('sha256').update(canonicalBuildJobMaterialSnapshot(changedLedger)).digest('hex'), pythonSha256);
  });

  test(`${snapshot.alloyId}: P7b snapshot still refuses an unknown root key`, () => {
    assert.throws(() => canonicalBuildJobMaterialSnapshot({ ...snapshot, unknownKernelKey: 1 }),
      /Invalid build-job material snapshot fields/);
  });
}

test('legacy snapshots still refuse unknown root keys', () => {
  assert.throws(() => canonicalBuildJobMaterialSnapshot({
    schemaVersion: 1, alloyId: 'in718', thermal: {}, slicer: {}, unknownKernelKey: 1,
  }), /Invalid build-job material snapshot fields/);
});

test('the optional kernel ledger must be a lowercase SHA-256 digest', () => {
  for (const kernelLedgerSha256 of [null, 42, '', 'a'.repeat(63), 'G'.repeat(64), 'A'.repeat(64)]) {
    assert.throws(() => canonicalBuildJobMaterialSnapshot({
      schemaVersion: 1, alloyId: 'ti6al4v', thermal: {}, slicer: {}, kernelLedgerSha256,
    }), /Invalid build-job material snapshot/);
  }
});
