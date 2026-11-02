// Writes (or verifies) a SHA256SUMS file for the release artefacts: dist/ and the SBOMs in sbom/.
// Usage:
//   node scripts/release-checksums.mjs [--root <dir>] [--out SHA256SUMS]   write
//   node scripts/release-checksums.mjs --verify [--root <dir>] [--out SHA256SUMS]
// Format matches `sha256sum`: "<hex>  <posix relative path>", sorted by path, LF line endings.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

function walk(dir, base, out) {
  if (!fs.existsSync(dir)) return;
  for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, base, out);
    else if (entry.isFile()) out.push(path.relative(base, full).split(path.sep).join('/'));
  }
}

export function collectArtefacts(root) {
  const files = [];
  walk(path.join(root, 'dist'), root, files);
  const sbomDir = path.join(root, 'sbom');
  if (fs.existsSync(sbomDir)) {
    for (const f of fs.readdirSync(sbomDir)) {
      if (f.endsWith('.json') && fs.statSync(path.join(sbomDir, f)).isFile()) files.push(`sbom/${f}`);
    }
  }
  return files.sort();
}

export function sha256File(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

export function writeChecksums(root, outName = 'SHA256SUMS') {
  const files = collectArtefacts(root);
  if (files.length === 0) throw new Error(`No dist/ or sbom/ artefacts under ${root}. Run "npm run build" and "npm run sbom" first.`);
  const lines = files.map((rel) => `${sha256File(path.join(root, rel))}  ${rel}`);
  fs.writeFileSync(path.join(root, outName), lines.join('\n') + '\n');
  return files;
}

export function verifyChecksums(root, outName = 'SHA256SUMS') {
  const failures = [];
  const text = fs.readFileSync(path.join(root, outName), 'utf8');
  for (const line of text.split('\n').filter(Boolean)) {
    const m = /^([0-9a-f]{64}) {2}(.+)$/.exec(line);
    if (!m) { failures.push(`malformed line: ${line}`); continue; }
    const file = path.resolve(root, m[2]);
    const rel = path.relative(path.resolve(root), file);
    if (rel.startsWith('..') || path.isAbsolute(rel)) failures.push(`outside root: ${m[2]}`);
    else if (!fs.existsSync(file)) failures.push(`missing: ${m[2]}`);
    else if (sha256File(file) !== m[1]) failures.push(`mismatch: ${m[2]}`);
  }
  return failures;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const val = (flag, dflt) => (args.includes(flag) ? args[args.indexOf(flag) + 1] : dflt);
  const root = path.resolve(val('--root', path.join(path.dirname(fileURLToPath(import.meta.url)), '..')));
  const out = val('--out', 'SHA256SUMS');
  try {
    if (args.includes('--verify')) {
      const failures = verifyChecksums(root, out);
      if (failures.length) { console.error(failures.join('\n')); process.exit(1); }
      console.log(`${out}: all files OK`);
    } else {
      const files = writeChecksums(root, out);
      console.log(`Wrote ${out} with ${files.length} entries`);
    }
  } catch (e) {
    console.error(e instanceof Error ? e.message : String(e));
    process.exit(1);
  }
}
