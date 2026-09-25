import React from 'react';
import {useI18n} from '../../i18n';

// SYSTEM STATUS (R8.3 / R10.4 / AK): FHIR, Database, LLM, Auth, NOVA. Reads /health/subsystems
// (subsystems map) + the decide response's llm_degraded. Never renders a secret. Status is shown
// by chip class + glyph + text, not color alone (accessibility).
function chipClass(state) {
  const s = String(state || '').toLowerCase();
  if (s === 'ok' || s === 'up' || s === 'healthy' || s === 'ready' || s === true) return 'ok';
  if (s === 'degraded') return 'degraded';
  if (s === 'down' || s === 'error' || s === 'unavailable' || s === false) return 'down';
  return '';
}
function stateLabel(t, state) {
  const c = chipClass(state);
  if (c === 'ok') return t('status.ok');
  if (c === 'degraded') return t('status.degraded');
  if (c === 'down') return t('status.down');
  return t('status.unknown');
}

export default function NovaSystemStatus({subsystems, llmDegraded, loading, error, onRetry}) {
  const {t} = useI18n();
  // Derive the AI headline from llmDegraded (from decide) and the llm subsystem state.
  const llmState = subsystems && (subsystems.llm || subsystems.LLM);
  const aiHeadline = llmDegraded
    ? t('status.aiDegraded')
    : chipClass(llmState) === 'down'
      ? t('status.llmUnavailable')
      : t('status.aiAvailable');

  const rows = [
    ['fhir', t('status.fhir'), subsystems && (subsystems.fhir || subsystems.FHIR)],
    ['database', t('status.database'), subsystems && (subsystems.database || subsystems.db || subsystems.postgres)],
    ['llm', t('status.llm'), llmDegraded ? 'degraded' : llmState],
    ['auth', t('status.auth'), subsystems && (subsystems.auth || subsystems.authentication)],
    ['nova', t('status.nova'), subsystems && (subsystems.nova || subsystems.nova_service)],
    ['kb', t('status.knowledgeBase'), subsystems && (subsystems.knowledge_base || subsystems.kb)],
  ];

  return (
    <section className="nova-panel" aria-labelledby="nova-status-h">
      <div className="nova-panel-head">
        <h3 id="nova-status-h">{t('status.title')}</h3>
        <span className={`nova-status-chip ${llmDegraded ? 'degraded' : ''}`}><span className="nova-dot" />{aiHeadline}</span>
      </div>
      {error
        ? <div className="nova-error">{t('errors.generic')}{onRetry ? <button className="nova-primary" onClick={onRetry}>{t('common.retry')}</button> : null}</div>
        : loading
          ? <div className="nova-loading">{t('common.loading')}</div>
          : <div className="nova-status-grid">
              {rows.map(([id, label, state]) => (
                <span key={id} className={`nova-status-chip ${chipClass(state)}`}>
                  <span className="nova-dot" />{label}: {stateLabel(t, state)}
                </span>
              ))}
            </div>}
    </section>
  );
}
