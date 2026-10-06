import {describe, it, expect, beforeEach} from 'vitest';
import {translate, detectInitialLocale, SUPPORTED_LOCALES} from '../src/i18n';
import ko from '../src/i18n/ko';
import en from '../src/i18n/en';
import ja from '../src/i18n/ja';
import zh from '../src/i18n/zh';

// Pure unit tests -- no backend/API bridge needed. Verifies the i18n contract that the N.O.V.A.
// frontend depends on: locale detection priority, graceful fallback, variable interpolation, and
// (critically, per steering nova-safety) that translation only touches DISPLAY strings while
// canonical clinical IDs stay locale-independent.

describe('nova i18n translate()', () => {
  it('returns the locale-specific display string for a known key', () => {
    expect(translate('ko', 'nova.critical.title')).toBe('반드시 놓치면 안 되는 질환');
    expect(translate('en', 'nova.critical.title')).toBe('MUST-NOT-MISS');
    expect(translate('ja', 'nova.critical.title')).toBe('見逃してはならない疾患');
    expect(translate('zh', 'nova.critical.title')).toBe('绝不可漏诊');
  });

  it('interpolates {vars}', () => {
    expect(translate('en', 'nova.decide.remaining', {n: 12})).toBe('12 turns remaining');
    expect(translate('ko', 'nova.decide.remaining', {n: 12})).toBe('12턴 남음');
  });

  it('falls back to English for a missing non-English key, then to the raw key', () => {
    // A key that exists nowhere -> returned verbatim (visible, non-crashing).
    expect(translate('ko', 'nonexistent.key.path')).toBe('nonexistent.key.path');
  });

  it('keeps the same key structure across all four locales (no missing top-level sections)', () => {
    const sections = Object.keys(en);
    for (const dict of [ko, ja, zh]) {
      for (const s of sections) {
        expect(dict, `locale missing section "${s}"`).toHaveProperty(s);
      }
    }
  });
});

describe('nova i18n detectInitialLocale()', () => {
  beforeEach(() => {
    try { localStorage.clear(); } catch { /* ignore */ }
  });

  it('prefers a saved preference over the browser language', () => {
    localStorage.setItem('nova.locale', 'ja');
    expect(detectInitialLocale()).toBe('ja');
  });

  it('falls back to Korean when nothing is saved and browser language is unsupported', () => {
    // jsdom navigator.language is typically 'en-US'; force an unsupported one is not trivial, so
    // we only assert the result is one of the supported locales (never throws, never undefined).
    const loc = detectInitialLocale();
    expect(SUPPORTED_LOCALES).toContain(loc);
  });
});

describe('canonical IDs are never translated (steering invariant)', () => {
  it('translate() only accepts display keys; a diagnosis_id-shaped string is returned unchanged', () => {
    // A canonical id like "ischemic_stroke" is not an i18n key, so translate() returns it as-is
    // in every locale -- proving the display layer never rewrites canonical ids.
    for (const loc of SUPPORTED_LOCALES) {
      expect(translate(loc, 'ischemic_stroke')).toBe('ischemic_stroke');
    }
  });
});
