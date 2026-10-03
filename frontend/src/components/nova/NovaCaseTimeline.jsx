import React from 'react';
import {useI18n} from '../../i18n';

// Per-turn timeline (R8.4/AY): ASK/EXAM/TEST/DIAGNOSE + result + timestamp. The timeline is
// accumulated client-side from each applied observation (the backend does not return a transcript
// on decide), which is sufficient for the workspace view; the durable record lives in the audit.
export default function NovaCaseTimeline({turns}) {
  const {t} = useI18n();
  const items = Array.isArray(turns) ? turns : [];
  return (
    <section className="nova-panel nova-timeline" aria-labelledby="nova-tl-h">
      <div className="nova-panel-head"><h3 id="nova-tl-h">{t('nova.timeline.title')}</h3></div>
      {items.length
        ? <ol>
            {items.map((tr, i) => (
              <li key={i}>
                <span className="nova-tl-turn">#{tr.turn}</span>
                <span className="nova-tl-action">{t(`nova.nextAction.type.${tr.action_type}`)} · {tr.key}</span>
                <span className="nova-tl-result">{tr.result || '—'}</span>
                <span className="nova-tl-time">{tr.time || ''}</span>
              </li>
            ))}
          </ol>
        : <div className="nova-empty">{t('nova.timeline.none')}</div>}
    </section>
  );
}
