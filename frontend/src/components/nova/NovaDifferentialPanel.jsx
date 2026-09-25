import React from 'react';
import {useI18n} from '../../i18n';

// Confidence is shown as a LOW/MEDIUM/HIGH band only -- never a raw % (R8.4: no percentage unless
// the backend marks it calibrated, which NovaDifferentialItemOut does not). The canonical
// diagnosis_id is always shown alongside the localized display name.
function confClass(band) {
  const up = String(band || '').toUpperCase();
  if (up.includes('HIGH')) return 'conf-HIGH';
  if (up.includes('MED')) return 'conf-MEDIUM';
  return 'conf-LOW';
}

export default function NovaDifferentialPanel({differential, selectedId, onSelect, loading}) {
  const {t} = useI18n();
  const items = Array.isArray(differential) ? differential : [];
  return (
    <section className="nova-panel" aria-labelledby="nova-diff-h">
      <div className="nova-panel-head"><h3 id="nova-diff-h">{t('nova.differential.title')}</h3></div>
      {loading
        ? <div className="nova-loading">{t('common.loading')}</div>
        : items.length
          ? <div className="nova-diff-list">
              {items.map((d) => {
                const id = d.diagnosis_id;
                const name = d.display_diagnosis || d.diagnosis;
                return (
                  <button
                    key={id || d.rank}
                    type="button"
                    className="nova-diff-item"
                    aria-pressed={selectedId === id}
                    onClick={() => onSelect && onSelect(id)}
                  >
                    <div className="nova-diff-top">
                      <span className="nova-diff-name">{d.rank}. {name}</span>
                      <span className={`nova-badge ${confClass(d.confidence_band)}`}>
                        {t('nova.differential.confidence')}: {d.confidence_band || t('common.unknown')}
                      </span>
                      {d.urgency ? <span className="nova-badge conf-MEDIUM">{t('nova.differential.urgency')}: {d.urgency}</span> : null}
                      {d.dangerous_if_missed ? <span className="nova-badge danger">{t('nova.differential.dangerous')}</span> : null}
                    </div>
                    <span className="nova-diff-id">{t('nova.differential.canonicalId')}: {id}</span>
                    {Array.isArray(d.candidate_sources) && d.candidate_sources.length
                      ? <span className="nova-muted">{t('nova.differential.sources')}: {d.candidate_sources.join(', ')}</span>
                      : null}
                  </button>
                );
              })}
            </div>
          : <div className="nova-empty">{t('nova.differential.none')}</div>}
    </section>
  );
}
