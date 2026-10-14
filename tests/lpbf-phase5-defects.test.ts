import assert from 'node:assert/strict';
import { test } from 'node:test';
import { execSync } from 'node:child_process';
import path from 'node:path';
import { writeFileSync, rmSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';

test('Phase 5: Defect Diagnostics & Porosity Aggregation', async t => {
  const directory = mkdtempSync(path.join(tmpdir(), 'metalliksa-phase5-'));
  t.after(() => {
    try { rmSync(directory, { recursive: true, force: true }); } catch (e) {}
  });

  const testScript = path.join(directory, 'test_defects.py');
  const pythonCode = `
import json
import sys
import math
sys.path.insert(0, 'python')

from lpbf_defect_diagnostics import balling_screen, defect_diagnostics
from lpbf_part_porosity_aggregator import aggregate_part_porosity
from lpbf_scanner_kinematics import calculate_scanner_kinematics

# 1. Scanner Kinematics
kinematics = calculate_scanner_kinematics(1000.0, 500.0, 200000.0)
assert kinematics['warning'] is not None, "Should warn about short track"
assert kinematics['effectiveMidTrackSpeed_mms'] < 1000.0, "Should not reach nominal speed"

# 2. Defect Diagnostics (balling): the band comes only from the Eagar-Tsai L/W screen (Moderate > 3.85; no High band since P7b)
assert defect_diagnostics(width_um=50, depth_um=30, length_um=200, hatch_um=40, layer_um=20)['balling']['risk'] is None
screen = balling_screen(300.0, 50.0, 30.0, 'computed')
diag_balling = defect_diagnostics(width_um=50, depth_um=30, length_um=200, hatch_um=40, layer_um=20, balling=screen)
assert diag_balling['balling']['risk'] == 'moderate', "Eagar-Tsai L/W 6 > 3.85 is Moderate (no High band since P7b, 2026-10-14)"
assert diag_balling['balling']['lengthToWidth'] == 4.0

# Keyhole (Wave B LA-3): D/W alone gives no risk verdict; King et al. 2014 sec. 5.2 mode indicator only
diag_keyhole = defect_diagnostics(width_um=50, depth_um=80, length_um=100, hatch_um=40, layer_um=20)
assert diag_keyhole['keyhole']['risk'] is None, "D/W alone must not assign a keyhole risk"
assert diag_keyhole['keyhole']['kingModeIndicator'] == 'keyhole-mode'
assert diag_keyhole['keyhole']['depthToWidth'] == 1.6

# 3. Aggregation
samples = [diag_balling, diag_keyhole]
agg = aggregate_part_porosity(samples, powder_gas_prior_percent=0.01)
assert agg['status'] == 'aggregated'
assert agg['mechanismCounts']['keyhole'] == 0, "a null keyhole risk adds no keyhole porosity"
assert agg['mechanismCounts']['balling'] == 1
assert agg['screeningIndex']['mean_percent'] < 100.0

print(json.dumps(agg))
`;

  writeFileSync(testScript, pythonCode);
  
  // Run python script
  const output = execSync(`python "${testScript}"`, { encoding: 'utf8' });
  const result = JSON.parse(output);
  
  assert.equal(result.status, 'aggregated');
  assert.equal(result.sampleCount, 2);
  assert.ok(result.screeningIndex.mean_percent > 0);
});
