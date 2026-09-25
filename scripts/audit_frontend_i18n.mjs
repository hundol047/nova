#!/usr/bin/env node
// Lightweight hardcoded-string audit for the frontend (independent-audit #17).
//
// Scans frontend/src for CJK (Korean/Japanese/Chinese) string/JSX-text literals that look like
// clinician-facing UI copy and are NOT going through the i18n t() layer. It is deliberately
// dependency-free (no eslint/babel) so it runs in any environment (node only), and heuristic --
// it flags candidates for review, it is not a compiler. Locale dictionaries (src/i18n/*.js) are
// EXEMPT (that is where translated copy lives by design).
//
// Whitelist: strings that are clinical codes / technical identifiers / non-translatable tokens
// (FHIR, LOINC, RxNorm, canonical diagnosis_id, drug ids, units) must NOT be translated and are
// ignored. This is a NAME-level whitelist, not a value dump.
//
// Usage:
//   node scripts/audit_frontend_i18n.mjs            # human report, exit 0
//   node scripts/audit_frontend_i18n.mjs --json     # JSON report
//   node scripts/audit_frontend_i18n.mjs --max N    # exit 1 if findings > N (gate mode)
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SRC = path.join(ROOT, 'frontend', 'src');

const CJK = /[\u3131-\uD79D\u3040-\u30FF\u4E00-\u9FFF]/; // Hangul + Kana + CJK ideographs

// Files/dirs exempt from the audit.
const EXEMPT_PATH = (p) =>
  p.includes(`${path.sep}i18n${path.sep}`) ||       // translations live here by design
  p.includes(`${path.sep}data${path.sep}`) ||       // static clinical data maps
  p.endsWith('.css') || p.endsWith('.json');

// Non-translatable technical tokens -- if a CJK-containing literal ALSO matches one of these it is
// still flagged (CJK copy should be translated), but purely-technical literals never contain CJK
// so this list mostly documents intent. Kept for future extension.
const TECHNICAL_WHITELIST = [/^FHIR$/i, /^LOINC$/i, /^RxNorm$/i, /_id$/i, /^[a-z0-9_]+$/];

function walk(dir) {
  const out = [];
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const st = fs.statSync(full);
    if (st.isDirectory()) { out.push(...walk(full)); continue; }
    if (!/\.(jsx?|tsx?)$/.test(name)) continue;
    if (EXEMPT_PATH(full)) continue;
    out.push(full);
  }
  return out;
}

function scanFile(full) {
  const rel = path.relative(ROOT, full);
  const lines = fs.readFileSync(full, 'utf8').split('\n');
  const findings = [];
  lines.forEach((line, i) => {
    if (!CJK.test(line)) return;
    // Skip lines that are clearly comments-only.
    const trimmed = line.trim();
    if (trimmed.startsWith('//') || trimmed.startsWith('*')) return;
    // A line already using t('...') for its copy is fine even if a comment on the same line has
    // CJK; heuristic: if the CJK appears only inside a // comment segment, skip.
    const codePart = line.split('//')[0];
    if (!CJK.test(codePart)) return;
    findings.push({line: i + 1, text: trimmed.slice(0, 160)});
  });
  return findings.length ? {file: rel, findings} : null;
}

const files = fs.existsSync(SRC) ? walk(SRC) : [];
const report = files.map(scanFile).filter(Boolean);
const total = report.reduce((n, r) => n + r.findings.length, 0);

const args = process.argv.slice(2);
if (args.includes('--json')) {
  console.log(JSON.stringify({total_findings: total, files: report}, null, 2));
} else {
  console.log(`Frontend hardcoded CJK-string audit (i18n) — ${total} candidate line(s) in ${report.length} file(s)`);
  console.log('(src/i18n/*, data/*, css, json are exempt; these are review candidates, not errors)');
  for (const r of report) {
    console.log(`\n  ${r.file}`);
    for (const f of r.findings) console.log(`    L${f.line}: ${f.text}`);
  }
  if (!report.length) console.log('  none');
}

const maxIdx = args.indexOf('--max');
if (maxIdx !== -1) {
  const max = Number(args[maxIdx + 1] || 0);
  if (total > max) {
    console.error(`\nGATE FAIL: ${total} hardcoded CJK string(s) > allowed ${max}`);
    process.exit(1);
  }
}
process.exit(0);
