import React from 'react';
import {useI18n} from '../../i18n';

// Shows patient / case id / encounter / turn / status. Purely presentational.
export default function NovaCaseHeader({caseState}) {
  const {t} = useI18n();
  if (!caseState) {
    return <div className="nova-panel nova-muted">{t('nova.caseHeader.noCase')}</div>;
  }
  const {case_id, patient_id, encounter_id, turn_count, max_turns, status} = caseState;
  return (
    <div className="nova-panel nova-case-header" aria-label={t('nova.caseHeader.case')}>
      <div className="nova-ch-item"><span>{t('nova.caseHeader.patient')}</span><b>{patient_id}</b></div>
      <div className="nova-ch-item"><span>{t('nova.caseHeader.case')}</span><b title={case_id}>{String(case_id).slice(0, 8)}</b></div>
      {encounter_id ? <div className="nova-ch-item"><span>{t('nova.caseHeader.encounter')}</span><b>{encounter_id}</b></div> : null}
      <div className="nova-ch-item"><span>{t('nova.caseHeader.turn')}</span><b>{turn_count} {t('nova.caseHeader.of')} {max_turns}</b></div>
      <div className="nova-ch-item"><span>{t('nova.caseHeader.status')}</span><b>{status}</b></div>
    </div>
  );
}
