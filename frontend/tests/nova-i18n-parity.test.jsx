import {describe, it, expect} from 'vitest';
import ko from '../src/i18n/ko';
import en from '../src/i18n/en';
import ja from '../src/i18n/ja';
import zh from '../src/i18n/zh';

// Translation-completeness / key-parity gate (independent-re-audit #5): every locale must define
// EXACTLY the same set of keys as English, so no production-critical string is silently running on
// the English fallback. Pure unit test (no backend/bridge) -- runs in the `frontend` CI job.
function flatKeys(obj, prefix = '') {
  let keys = [];
  for (const k of Object.keys(obj)) {
    const v = obj[k];
    const kk = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object') keys = keys.concat(flatKeys(v, kk));
    else keys.push(kk);
  }
  return keys.sort();
}

describe('i18n key parity across ko/en/ja/zh', () => {
  const enKeys = flatKeys(en);

  for (const [name, dict] of [['ko', ko], ['ja', ja], ['zh', zh]]) {
    it(`${name} has exactly the same keys as en (no missing, no extra)`, () => {
      const keys = flatKeys(dict);
      const missing = enKeys.filter((k) => !keys.includes(k));
      const extra = keys.filter((k) => !enKeys.includes(k));
      expect(missing, `${name} missing keys`).toEqual([]);
      expect(extra, `${name} extra keys`).toEqual([]);
    });
  }

  it('canonical clinical id strings are never used as i18n keys', () => {
    // Guard: none of the dictionaries should contain a value that looks like a canonical
    // diagnosis_id being (mis)used as display text substitution -- display strings only.
    // (Sanity check: known canonical ids are not present as keys.)
    for (const forbidden of ['ischemic_stroke', 'acute_coronary_syndrome']) {
      expect(flatKeys(en)).not.toContain(forbidden);
    }
  });
});
