import assert from 'node:assert/strict';
import { test } from 'node:test';
import { pythonComputationService as service } from '../src/services/pythonComputationService';
import { simulationApi } from '../src/services/lpbfSimulationService';
import { PythonValidationError } from '../src/utils/pythonValidationError';

test('engine refusals reach the UI with actionable English and structured fields', async () => {
  const previous = globalThis.fetch;
  const message = 'Select a supported material and run again.';
  try {
    for (const nested of [false, true]) {
      globalThis.fetch = async () => new Response(JSON.stringify({
        success: false, errorKind: 'validation', code: 'UNSUPPORTED_MATERIAL', field: 'material',
        error: nested ? { code: 'UNSUPPORTED_MATERIAL', field: 'material', message, detail: {} } : message,
      }), { status: 422, headers: { 'Content-Type': 'application/json' } });
      for (const call of [
        () => service.runLpbfBayesianOptimization({ alloyId: 'in625' }),
        () => service.solveLPBFMachineCalibratedMeltpool({} as never),
        () => service.solveSTLSlicerBuildTime({} as never),
        () => service.solveLpbfBuildJob({} as never),
        () => simulationApi.estimate({} as never),
        () => simulationApi.submit({} as never),
      ]) {
        await assert.rejects(call(), (error: unknown) => {
          assert.ok(error instanceof PythonValidationError);
          assert.equal(error.message, message);
          assert.equal(error.code, 'UNSUPPORTED_MATERIAL');
          assert.equal(error.field, 'material');
          return true;
        });
      }
    }
  } finally { globalThis.fetch = previous; }
});
