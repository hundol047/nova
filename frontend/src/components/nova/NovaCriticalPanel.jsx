import React from 'react';
import {useI18n} from '../../i18n';

// MUST-NOT-MISS panel. Deliberately separated from the differential (R8.3). Fed from the decide
// response `red_flags` (list of strings) so it reflects the backend's active safety findings.
export default function NovaCriticalPanel({redFlags, loading}) {
  const {t} = useI18n();
  const flags = Array.isArray(redFlags) ? redFlags : [];
  return (
    <section className="nova-panel nova-critical" aria-labelledby="nova-critical-h">
      <div className="nova-panel-head">
        <h3 id="nova-critical-h">{t('nova.critical.title')}</h3>
      </div>
      <p className="nova-muted" style={{marginTop: 0}}>{t('nova.critical.subtitle')}</p>
      {loading
        ? <div className="nova-loading">{t('common.loading')}</div>
        : flags.length
          ? <ul>{flags.map((f, i) => <li key={i}>{f}</li>)}</ul>
          : <div className="nova-empty">{t('nova.critical.none')}</div>}
    </section>
  );
}
