import React, {useState, useCallback, useEffect, useRef} from 'react';
import {api} from '../../lib/api';
import {useI18n} from '../../i18n';
import NovaCaseHeader from './NovaCaseHeader';
import NovaCriticalPanel from './NovaCriticalPanel';
import NovaDifferentialPanel from './NovaDifferentialPanel';
import NovaEvidencePanel from './NovaEvidencePanel';
import NovaNextActionPanel from './NovaNextActionPanel';
import NovaObservationForm from './NovaObservationForm';
import NovaCaseTimeline from './NovaCaseTimeline';
import NovaReviewPanel from './NovaReviewPanel';
import NovaSystemStatus from './NovaSystemStatus';
import './nova.css';

// Orchestrates the full N.O.V.A. case lifecycle against the REAL /v1/nova/* API (R8.2 -- no
// mock-only frontend). It owns case state + drives:
//   create case -> decide -> (enter result -> POST observation -> re-decide)* -> review -> close.
// Locale is driven by the shared i18n context; a locale change mid-case calls PATCH .../locale and
// re-decides WITHOUT resetting local case state (turns/observations/differential preserved).
export default function NovaWorkspace({patientId, encounterId}) {
  const {t, locale} = useI18n();

  const [caseState, setCaseState] = useState(null);   // NovaCaseCreatedResponse-ish + running turn_count
  const [decision, setDecision] = useState(null);     // NovaDecideResponse
  const [selectedDxId, setSelectedDxId] = useState(null);
  const [timeline, setTimeline] = useState([]);       // client-accumulated per-turn record
  const [subsystems, setSubsystems] = useState(null);
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [maxTurns, setMaxTurns] = useState(60);

  const [busy, setBusy] = useState('');               // '', 'create', 'decide', 'observe', 'review', 'locale'
  const [error, setError] = useState('');
  const [obsResultState, setObsResultState] = useState(null); // 'applied' | 'replayed' | null
  const [closed, setClosed] = useState(null);         // disposition string once closed

  const caseIdRef = useRef(null);
  const lastLocaleRef = useRef(locale);

  const errText = useCallback((e) => (e && e.message) ? e.message : t('errors.generic'), [t]);

  const runDecide = useCallback(async () => {
    const caseId = caseIdRef.current;
    if (!caseId) return;
    setBusy('decide'); setError('');
    try {
      const d = await api(`/v1/nova/cases/${caseId}/decide`);
      setDecision(d);
      setCaseState((prev) => prev ? {...prev, turn_count: d.turn_count} : prev);
      // Default-select the top differential item so the evidence panel is populated.
      if (Array.isArray(d.differential) && d.differential.length) {
        setSelectedDxId((cur) => cur || d.differential[0].diagnosis_id);
      }
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy('');
    }
  }, [errText]);

  const refreshStatus = useCallback(async () => {
    try {
      const s = await api('/health/subsystems');
      // Accept either {subsystems:{...}} or a flat map.
      setSubsystems(s && (s.subsystems || s));
    } catch { /* status is best-effort; leave as unknown */ }
  }, []);

  useEffect(() => { refreshStatus(); }, [refreshStatus]);

  const createCase = useCallback(async () => {
    if (!patientId) { setError(t('nova.start.selectPatient')); return; }
    if (!chiefComplaint.trim()) { setError(t('nova.start.needComplaint')); return; }
    setBusy('create'); setError(''); setClosed(null); setTimeline([]); setDecision(null); setSelectedDxId(null);
    try {
      const created = await api('/v1/nova/cases', {
        patient_id: patientId,
        encounter_id: encounterId || undefined,
        chief_complaint: chiefComplaint.trim(),
        max_turns: Number(maxTurns) || undefined,
        locale,
      });
      caseIdRef.current = created.case_id;
      setCaseState(created);
      await runDecide();
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy('');
    }
  }, [patientId, encounterId, chiefComplaint, maxTurns, locale, runDecide, errText, t]);

  const submitObservation = useCallback(async (payload) => {
    const caseId = caseIdRef.current;
    if (!caseId) return;
    setBusy('observe'); setError(''); setObsResultState(null);
    try {
      const resp = await api(`/v1/nova/cases/${caseId}/observations`, payload);
      setObsResultState(resp.applied ? 'applied' : 'replayed');
      if (resp.applied) {
        setTimeline((tl) => [...tl, {
          turn: resp.turn_count,
          action_type: payload.action_type,
          key: payload.key,
          result: payload.result,
          time: new Date().toLocaleTimeString(),
        }]);
        setCaseState((prev) => prev ? {...prev, turn_count: resp.turn_count} : prev);
        await runDecide();
      }
    } catch (e) {
      // On failure the SAME observation_id is retained by the form, so a retry is idempotent.
      setError(errText(e));
    } finally {
      setBusy('');
    }
  }, [runDecide, errText]);

  const submitReview = useCallback(async ({disposition, reason}) => {
    const caseId = caseIdRef.current;
    if (!caseId) return;
    setBusy('review'); setError('');
    try {
      const resp = await api(`/v1/nova/cases/${caseId}/close`, {disposition, reason});
      setClosed(resp.disposition || disposition);
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy('');
    }
  }, [errText]);

  // Mid-case locale switch (R7.2 / P): PATCH the locale, then re-decide so display strings render
  // in the new locale. The case is NOT reset -- turn_count, timeline, and differential are kept.
  useEffect(() => {
    if (lastLocaleRef.current === locale) return;
    lastLocaleRef.current = locale;
    const caseId = caseIdRef.current;
    if (!caseId || closed) return;
    (async () => {
      setBusy('locale'); setError('');
      try {
        await api(`/v1/nova/cases/${caseId}/locale`, {locale}, undefined, 'PATCH');
        await runDecide();
      } catch (e) {
        setError(errText(e));
      } finally {
        setBusy('');
      }
    })();
  }, [locale, closed, runDecide, errText]);

  const selectedItem = decision && Array.isArray(decision.differential)
    ? decision.differential.find((d) => d.diagnosis_id === selectedDxId) || null
    : null;

  const safetyBanner = (decision && decision.safety_banner) || (caseState && caseState.safety_banner) || t('safety.banner');

  return (
    <div className="nova-workspace">
      <div className="nova-safety-banner" role="note">
        <span aria-hidden="true">🛡️</span>
        <span>{safetyBanner}</span>
      </div>

      <NovaSystemStatus
        subsystems={subsystems}
        llmDegraded={decision ? decision.llm_degraded : false}
        loading={false}
        onRetry={refreshStatus}
      />

      {!caseState ? (
        <section className="nova-panel" aria-labelledby="nova-start-h">
          <div className="nova-panel-head"><h3 id="nova-start-h">{t('nova.start.title')}</h3></div>
          <div className="nova-field">
            <label htmlFor="nova-cc">{t('nova.start.chiefComplaint')}</label>
            <textarea id="nova-cc" value={chiefComplaint} onChange={(e) => setChiefComplaint(e.target.value)}
              placeholder={t('nova.start.chiefComplaintPlaceholder')} />
          </div>
          <div className="nova-field">
            <label htmlFor="nova-mt">{t('nova.start.maxTurns')}</label>
            <input id="nova-mt" type="number" min="1" max="200" value={maxTurns}
              onChange={(e) => setMaxTurns(e.target.value)} />
          </div>
          <button className="nova-primary" onClick={createCase} disabled={busy === 'create'}>
            {busy === 'create' ? t('common.loading') : t('nova.start.create')}
          </button>
          {error ? <p className="nova-error" role="alert">{error}</p> : null}
        </section>
      ) : (
        <>
          <NovaCaseHeader caseState={caseState} />

          {error ? (
            <div className="nova-error" role="alert">
              <span>{error}</span>
              <button className="nova-primary" onClick={runDecide}>{t('common.retry')}</button>
            </div>
          ) : null}

          <NovaCriticalPanel redFlags={decision ? decision.red_flags : []} loading={busy === 'decide'} />

          <NovaNextActionPanel action={decision ? decision.recommended_next_action : null} loading={busy === 'decide'} />

          <NovaDifferentialPanel
            differential={decision ? decision.differential : []}
            selectedId={selectedDxId}
            onSelect={setSelectedDxId}
            loading={busy === 'decide'}
          />

          <NovaEvidencePanel item={selectedItem} />

          {!closed && decision && decision.recommended_next_action
            && decision.recommended_next_action.action_type !== 'DIAGNOSE' ? (
              <NovaObservationForm
                recommendedAction={decision.recommended_next_action}
                onSubmit={submitObservation}
                submitting={busy === 'observe'}
                resultState={obsResultState}
              />
            ) : null}

          {decision && decision.recommended_next_action
            && decision.recommended_next_action.action_type === 'DIAGNOSE' ? (
              <section className="nova-panel">
                <div className="nova-panel-head"><h3>{t('nova.finalDiagnosis')}</h3></div>
                <p><b>{decision.recommended_next_action.display_content || decision.recommended_next_action.content}</b></p>
                <p className="nova-muted">{t('safety.reviewRequired')}</p>
              </section>
            ) : null}

          <NovaCaseTimeline turns={timeline} />

          <NovaReviewPanel onSubmit={submitReview} submitting={busy === 'review'} closed={!!closed} disposition={closed} />
        </>
      )}
    </div>
  );
}
