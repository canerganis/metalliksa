import assert from "node:assert/strict";
import { test } from "node:test";
import {
  assertEnterpriseProfileConsistent,
  enterpriseProfileProblems,
  enterpriseStartupLine,
  isAirgappedFromEnv,
  isEnterpriseProfile,
} from "../server/airgap";

test("enterprise profile turns air-gap on without AIRGAPPED", () => {
  const env = { METALLIKSA_PROFILE: "Enterprise" };
  assert.equal(isEnterpriseProfile(env), true);
  assert.equal(isAirgappedFromEnv(env), true);
  assert.deepEqual(enterpriseProfileProblems(env), []);
  assert.match(enterpriseStartupLine(env) ?? "", /METALLIKSA_PROFILE=enterprise/);
});

test("default profile is unchanged", () => {
  assert.equal(isAirgappedFromEnv({}), false);
  assert.equal(isAirgappedFromEnv({ AIRGAPPED: "1" }), true);
  assert.equal(enterpriseStartupLine({}), null);
  assert.doesNotThrow(() => assertEnterpriseProfileConsistent({ OPENAI_API_KEY: "x" }));
});

test("enterprise profile refuses AIRGAPPED=0 and outbound credentials", () => {
  assert.throws(() => assertEnterpriseProfileConsistent({ METALLIKSA_PROFILE: "enterprise", AIRGAPPED: "0" }), /cannot be disabled/);
  assert.throws(() => assertEnterpriseProfileConsistent({ METALLIKSA_PROFILE: "enterprise", OPENAI_API_KEY: "sk-x" }), /OPENAI_API_KEY/);
  assert.doesNotThrow(() => assertEnterpriseProfileConsistent({ METALLIKSA_PROFILE: "enterprise", AIRGAPPED: "1" }));
});
