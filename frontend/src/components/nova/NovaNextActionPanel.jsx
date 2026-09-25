import React from 'react';
import {useI18n} from '../../i18n';

// NEXT BEST ACTION (R8.5). Shows the action type (ASK/EXAM/TEST/DIAGNOSE) plus What / Why.
// "What it distinguishes" is only shown when the backend action carries it (see `distinguishes`
// below); it is never fabricated on the client -- if the field is absent, that row is omitted.
export default function NovaNextActionPanel({action, loading}) {
  const {t} = useI18n();
  if (loading) {
    return <section className="nova-panel nova-action"><div className="nova-loading">{t('common.loading')}</div></section>;
  }
  if (!action) {
    return <section className="nova-panel nova-action"><div className="nova-empty">{t('nova.nextAction.none')}</div></section>;
  }
  const type = action.action_type;
  const what = action.display_content || action.content;
  const why = action.rationale;
  // Optional: the backend may (in a future field) attach what the action distinguishes; render
  // only if present, never invented.
  const distinguishes = action.distinguishes || action.what_distinguishes || null;
  return (
    <section className="nova-panel nova-action" aria-labelledby="nova-action-h">
      <div className="nova-panel-head"><h3 id="nova-action-h">{t('nova.nextAction.title')}</h3></div>
      <span className="nova-action-type">{t(`nova.nextAction.type.${type}`)}</span>
      <dl>
        <dt>{t('nova.nextAction.what')}</dt><dd>{what}</dd>
        {why ? <><dt>{t('nova.nextAction.why')}</dt><dd>{why}</dd></> : null}
        {distinguishes ? <><dt>{t('nova.nextAction.distinguishes')}</dt><dd>{distinguishes}</dd></> : null}
      </dl>
    </section>
  );
}
