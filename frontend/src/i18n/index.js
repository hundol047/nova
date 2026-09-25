// Dependency-free i18n for the SynexAgent + N.O.V.A. frontend.
//
// Design (see .kiro/specs/nova-hospital-grade/design.md 4.3):
//   - No new npm dependency: plain nested-key dictionaries + a t(key, vars) lookup.
//   - Locale selection priority: saved preference (localStorage) -> browser language -> Korean.
//   - Canonical clinical IDs are NEVER localized here; t() only ever returns display strings.
//     diagnosis_id / action key / concept id stay locale-independent (steering: nova-safety).
//   - Missing key -> returns the key itself (visible, non-crashing) rather than throwing, so a
//     partially-translated dictionary degrades gracefully instead of blanking the UI.
import React, {createContext, useContext, useState, useCallback, useMemo, useEffect} from 'react';
import ko from './ko';
import en from './en';
import ja from './ja';
import zh from './zh';

export const SUPPORTED_LOCALES = ['ko', 'en', 'ja', 'zh'];
export const LOCALE_LABELS = {ko: '한국어', en: 'English', ja: '日本語', zh: '中文'};
const DICTS = {ko, en, ja, zh};
const STORAGE_KEY = 'nova.locale';
const DEFAULT_LOCALE = 'ko';

// Map a full BCP-47 browser language (e.g. "zh-CN", "en-US", "ja") to one of our 4 supported
// locales, else null. zh-* (incl. zh-Hans / zh-CN / zh-TW) all fold to our single "zh".
function normalizeBrowserLanguage(lang) {
  if (!lang) return null;
  const low = String(lang).toLowerCase();
  if (low.startsWith('ko')) return 'ko';
  if (low.startsWith('ja')) return 'ja';
  if (low.startsWith('zh')) return 'zh';
  if (low.startsWith('en')) return 'en';
  return null;
}

export function detectInitialLocale() {
  // 1. saved preference
  try {
    const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    if (saved && SUPPORTED_LOCALES.includes(saved)) return saved;
  } catch { /* localStorage may be unavailable (private mode / SSR) -- fall through */ }
  // 2. browser language(s)
  try {
    const langs = (typeof navigator !== 'undefined' && (navigator.languages || [navigator.language])) || [];
    for (const l of langs) {
      const norm = normalizeBrowserLanguage(l);
      if (norm) return norm;
    }
  } catch { /* ignore */ }
  // 3. Korean
  return DEFAULT_LOCALE;
}

export function persistLocale(locale) {
  try {
    if (typeof localStorage !== 'undefined') localStorage.setItem(STORAGE_KEY, locale);
  } catch { /* ignore persistence failure -- in-memory locale still works this session */ }
}

// Resolve a dotted key ("nova.differential.title") against a dictionary, falling back to the
// English dictionary for any key a non-English dictionary hasn't translated yet, and finally to
// the raw key. Never throws.
function lookup(dict, key) {
  const parts = key.split('.');
  let node = dict;
  for (const p of parts) {
    if (node && typeof node === 'object' && p in node) node = node[p];
    else return undefined;
  }
  return typeof node === 'string' ? node : undefined;
}

export function translate(locale, key, vars) {
  const dict = DICTS[locale] || DICTS[DEFAULT_LOCALE];
  let str = lookup(dict, key);
  if (str === undefined && locale !== 'en') str = lookup(DICTS.en, key); // graceful EN fallback
  if (str === undefined) return key; // last-resort: show the key, don't crash
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      str = str.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
    }
  }
  return str;
}

const I18nContext = createContext(null);

export function I18nProvider({children, initialLocale}) {
  const [locale, setLocaleState] = useState(initialLocale || detectInitialLocale());

  const setLocale = useCallback((next) => {
    if (!SUPPORTED_LOCALES.includes(next)) return;
    setLocaleState(next);
    persistLocale(next);
  }, []);

  // Keep <html lang> in sync for accessibility / screen readers.
  useEffect(() => {
    try {
      if (typeof document !== 'undefined') document.documentElement.setAttribute('lang', locale);
    } catch { /* ignore */ }
  }, [locale]);

  const t = useCallback((key, vars) => translate(locale, key, vars), [locale]);

  const value = useMemo(() => ({locale, setLocale, t}), [locale, setLocale, t]);
  return React.createElement(I18nContext.Provider, {value}, children);
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (ctx) return ctx;
  // Safe fallback when used outside a provider (e.g. an isolated unit test rendering one panel):
  // default locale, no-op persistence.
  return {locale: DEFAULT_LOCALE, setLocale: () => {}, t: (key, vars) => translate(DEFAULT_LOCALE, key, vars)};
}
