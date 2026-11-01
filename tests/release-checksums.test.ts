import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { verifyChecksums, writeChecksums } from "../scripts/release-checksums.mjs";

function tempRoot(): string {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "relsum-"));
  fs.mkdirSync(path.join(root, "dist", "assets"), { recursive: true });
  fs.mkdirSync(path.join(root, "sbom"));
  fs.writeFileSync(path.join(root, "dist", "server.cjs"), "server");
  fs.writeFileSync(path.join(root, "dist", "assets", "a.js"), "asset");
  fs.writeFileSync(path.join(root, "sbom", "node-cyclonedx.json"), "{}");
  fs.writeFileSync(path.join(root, "sbom", "notes.txt"), "ignored");
  return root;
}

test("writeChecksums lists dist and sbom json with sha256sum format", () => {
  const root = tempRoot();
  try {
    const files = writeChecksums(root) as string[];
    assert.deepEqual(files, ["dist/assets/a.js", "dist/server.cjs", "sbom/node-cyclonedx.json"]);
    const lines = fs.readFileSync(path.join(root, "SHA256SUMS"), "utf8").trimEnd().split("\n");
    assert.equal(lines.length, 3);
    const expected = crypto.createHash("sha256").update("server").digest("hex");
    assert.ok(lines.includes(`${expected}  dist/server.cjs`));
    assert.deepEqual(verifyChecksums(root), []);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test("verifyChecksums reports tampered and missing files", () => {
  const root = tempRoot();
  try {
    writeChecksums(root);
    fs.writeFileSync(path.join(root, "dist", "server.cjs"), "tampered");
    fs.rmSync(path.join(root, "dist", "assets", "a.js"));
    const failures = verifyChecksums(root) as string[];
    assert.deepEqual(failures.sort(), ["mismatch: dist/server.cjs", "missing: dist/assets/a.js"]);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test("writeChecksums refuses an empty tree", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "relsum-empty-"));
  try { assert.throws(() => writeChecksums(root), /No dist/); }
  finally { fs.rmSync(root, { recursive: true, force: true }); }
});
