import React from 'react';
import {useI18n} from '../../i18n';

// Supporting / contradictory / missing-discriminative evidence for the currently selected
// differential item (R8.3). Reads the arrays already present on NovaDifferentialItemOut.
function EvidenceList({items, extraClass}) {
  const {t} = useI18n();
  const arr = Array.isArray(items) ? items : [];
  if (!arr.length) return <div className="nova-empty">{t('nova.evidence.none')}</div>;
  return (
    <ul className={extraClass}>
      {arr.map((e, i) => <li key={i}>{typeof e === 'string' ? e : (e && (e.text || e.label || JSON.stringify(e)))}</li>)}
    </ul>
  );
}

export default function NovaEvidencePanel({item}) {
  const {t} = useI18n();
  return (
    <section className="nova-panel nova-evidence" aria-labelledby="nova-ev-h">
      <div className="nova-panel-head"><h3 id="nova-ev-h">{t('nova.evidence.title')}</h3></div>
      {!item
        ? <div className="nova-empty">{t('nova.evidence.selectHint')}</div>
        : <>
            <h4>{t('nova.evidence.supporting')}</h4>
            <EvidenceList items={item.supporting_evidence} />
            <h4>{t('nova.evidence.contradictory')}</h4>
            <EvidenceList items={item.contradictory_evidence} extraClass="contra" />
            <h4>{t('nova.evidence.missing')}</h4>
            <EvidenceList items={item.missing_discriminative_evidence} />
          </>}
    </section>
  );
}
