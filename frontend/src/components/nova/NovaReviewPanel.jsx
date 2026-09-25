import React, {useState} from 'react';
import {useI18n} from '../../i18n';

// Clinician review (R8.7): Accept / Modify / Reject + required reason. Posts to /close. Never
// triggers an automatic order (steering: nova-safety). A reason is mandatory before submitting.
export default function NovaReviewPanel({onSubmit, submitting, closed, disposition}) {
  const {t} = useI18n();
  const [choice, setChoice] = useState(null);
  const [reason, setReason] = useState('');
  const [touched, setTouched] = useState(false);

  const options = [
    ['accept', t('nova.review.accept')],
    ['modify', t('nova.review.modify')],
    ['reject', t('nova.review.reject')],
  ];

  function handleSubmit(e) {
    e.preventDefault();
    setTouched(true);
    if (!choice || !reason.trim()) return;
    onSubmit({disposition: choice, reason: reason.trim()});
  }

  if (closed) {
    return (
      <section className="nova-panel nova-review" aria-labelledby="nova-review-h">
        <div className="nova-panel-head"><h3 id="nova-review-h">{t('nova.review.title')}</h3></div>
        <p className="nova-muted">{t('nova.review.closed', {disposition})}</p>
        <p className="nova-muted">{t('nova.review.recorded')}</p>
      </section>
    );
  }

  return (
    <form className="nova-panel nova-review" onSubmit={handleSubmit} aria-labelledby="nova-review-h">
      <div className="nova-panel-head"><h3 id="nova-review-h">{t('nova.review.title')}</h3></div>
      <p className="nova-muted">{t('nova.review.noAutoOrder')}</p>
      <div className="nova-review-buttons" role="group" aria-label={t('nova.review.title')}>
        {options.map(([val, label]) => (
          <button key={val} type="button" aria-pressed={choice === val} onClick={() => setChoice(val)}>
            {label}
          </button>
        ))}
      </div>
      {choice === 'modify' ? (
        <p className="nova-muted" style={{marginTop: 8}}>{t('nova.review.modifyHint')}</p>
      ) : null}
      <label htmlFor="nova-review-reason" className="nova-muted" style={{display: 'block', marginTop: 8}}>
        {t('common.reason')}
      </label>
      <textarea
        id="nova-review-reason"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder={t('nova.review.reasonPlaceholder')}
        aria-invalid={touched && !reason.trim()}
      />
      {touched && (!choice || !reason.trim()) ? <p className="nova-muted" role="alert">{t('nova.review.needReason')}</p> : null}
      <button type="submit" className="nova-primary" disabled={submitting} style={{marginTop: 8}}>
        {submitting ? t('nova.observation.submitting') : t('common.submit')}
      </button>
    </form>
  );
}
