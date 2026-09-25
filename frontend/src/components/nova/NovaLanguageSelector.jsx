import React from 'react';
import {useI18n, SUPPORTED_LOCALES, LOCALE_LABELS} from '../../i18n';

// Top-bar language selector (R8.8 / M): 한국어 | English | 日本語 | 中文. The selected value is
// persisted to localStorage by the i18n provider; priority is saved -> browser -> Korean.
export default function NovaLanguageSelector() {
  const {locale, setLocale, t} = useI18n();
  return (
    <div className="nova-lang-selector" role="group" aria-label={t('topbar.language')}>
      {SUPPORTED_LOCALES.map((loc) => (
        <button
          key={loc}
          type="button"
          className={locale === loc ? 'active' : ''}
          aria-pressed={locale === loc}
          onClick={() => setLocale(loc)}
          lang={loc === 'zh' ? 'zh-CN' : loc}
        >
          {LOCALE_LABELS[loc]}
        </button>
      ))}
    </div>
  );
}
