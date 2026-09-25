import React, {useState, useRef, useEffect} from 'react';
import {useI18n} from '../../i18n';

// Generate a stable observation id. Reused across network retries (R8.6) so a retry never creates
// a double turn -- the backend gates on (case_id, observation_id) as an idempotency key.
function newObservationId() {
  try {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return `obs-${crypto.randomUUID()}`;
  } catch { /* ignore */ }
  return `obs-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

// Enter the ASK/EXAM/TEST result for the recommended action, then POST it. The action_type/key are
// prefilled from the recommended action but remain visible/editable so the clinician stays in
// control. DIAGNOSE is submitted via the review flow, not here.
export default function NovaObservationForm({recommendedAction, onSubmit, submitting, resultState}) {
  const {t} = useI18n();
  const [result, setResult] = useState('');
  // One observation_id per logical observation; regenerated only after a successful (non-replay)
  // submit, reused on any retry of the same observation.
  const obsIdRef = useRef(newObservationId());
  const type = recommendedAction ? recommendedAction.action_type : 'ASK';
  const key = recommendedAction ? recommendedAction.key : '';

  useEffect(() => {
    // A new recommended action => a new logical observation => fresh id + cleared field.
    obsIdRef.current = newObservationId();
    setResult('');
  }, [recommendedAction && recommendedAction.key, recommendedAction && recommendedAction.action_type]);

  if (!recommendedAction || type === 'DIAGNOSE') return null;

  function handleSubmit(e) {
    e.preventDefault();
    onSubmit({observation_id: obsIdRef.current, action_type: type, key, result});
  }

  return (
    <form className="nova-panel" onSubmit={handleSubmit} aria-labelledby="nova-obs-h">
      <div className="nova-panel-head"><h3 id="nova-obs-h">{t('nova.observation.title')}</h3></div>
      <div className="nova-field">
        <label>{t('nova.observation.actionType')}</label>
        <input value={t(`nova.nextAction.type.${type}`)} readOnly aria-readonly="true" />
      </div>
      <div className="nova-field">
        <label>{t('nova.observation.key')}</label>
        <input value={key} readOnly aria-readonly="true" />
      </div>
      <div className="nova-field">
        <label htmlFor="nova-obs-result">{t('nova.observation.result')}</label>
        <textarea
          id="nova-obs-result"
          value={result}
          onChange={(e) => setResult(e.target.value)}
          placeholder={t('nova.observation.resultPlaceholder')}
        />
      </div>
      <button type="submit" className="nova-primary" disabled={submitting}>
        {submitting ? t('nova.observation.submitting') : t('nova.observation.submit')}
      </button>
      {resultState === 'applied' ? <p className="nova-muted">{t('nova.observation.submitted')}</p> : null}
      {resultState === 'replayed' ? <p className="nova-muted">{t('nova.observation.replayed')}</p> : null}
    </form>
  );
}
