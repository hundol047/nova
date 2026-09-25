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
//
// Correctness invariants enforced here (offline final-fixes pass):
//   - CASE ISOLATION (item 7): when `patientId` changes, ALL case state is reset so patient A's
//     case never bleeds into patient B's screen.
//   - RACE SAFETY (item 9): an `epochRef` is bumped on every patient change / new case; any async
//     response whose captured epoch no longer matches the current one is DISCARDED, so a slow
//     response for an old patient/case can never overwrite the current view.
//   - NO DUPLICATE / CONCURRENT REQUESTS (items 8, 10): an `inFlightRef` guard prevents a second
//     decide/observe/create/review while one is already running (covers double-click, repeated
//     Enter, and the locale-effect + observation both wanting to re-decide).
//   - NO ACTION AFTER DIAGNOSE/CLOSE (item 11): the observation form is hidden once the recommended
//     action is DIAGNOSE or the case is closed, the locale-switch effect no-ops when closed, and
//     the error-retry button is hidden once closed.
export default function NovaWorkspace({patientId, encounterId}) {
  const {t, locale} = useI18n();

  const [caseState, setCaseState] = useState(null);   // NovaCaseCreatedResponse-ish + running turn_count
  const [decision, setDecision] = useState(null);     // NovaDecideResponse
  const [selectedDxId, setSelectedDxId] = useState(null);
  const [timeline, setTimeline] = useState([]);       // per-turn record (server-restored + client-appended)
  const [subsystems, setSubsystems] = useState(null);
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [maxTurns, setMaxTurns] = useState(60);

  const [busy, setBusy] = useState('');               // '', 'create', 'decide', 'observe', 'review', 'locale'
  const [error, setError] = useState('');
  const [obsResultState, setObsResultState] = useState(null); // 'applied' | 'replayed' | null
  const [closed, setClosed] = useState(null);         // disposition string once closed

  const caseIdRef = useRef(null);
  const lastLocaleRef = useRef(locale);
  const epochRef = useRef(0);        // bumped on every patient change / new case -- guards stale responses
  const inFlightRef = useRef(false); // true while any create/decide/observe/review request is running

  const errText = useCallback((e) => (e && e.message) ? e.message : t('errors.generic'), [t]);

  // --- CASE ISOLATION (items 7, 9): hard reset whenever the selected patient changes. -----------
  // Bumping the epoch invalidates any in-flight response captured under the previous epoch.
  useEffect(() => {
    epochRef.current += 1;
    caseIdRef.current = null;
    inFlightRef.current = false;
    setCaseState(null);
    setDecision(null);
    setSelectedDxId(null);
    setTimeline([]);
    setClosed(null);
    setError('');
    setObsResultState(null);
    setBusy('');
    setChiefComplaint('');
    lastLocaleRef.current = locale;
    // Intentionally depends ONLY on patientId: a locale change must NOT reset the case.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  // Timeline is accumulated within the session as observations are applied. The durable per-turn
  // history is ALSO persisted server-side (PatientState.conversation_history) and now returned by
  // GET /v1/nova/cases/{id} as `conversation_history`, so a future "resume existing case" entry
  // point can restore it (mapping turn/action_type/content/result/timestamp). This workspace
  // currently always starts a fresh case, so no restore call is wired yet -- the server data is
  // available for that follow-up without another backend change.

  const runDecide = useCallback(async () => {
    const caseId = caseIdRef.current;
    if (!caseId || closed) return;
    if (inFlightRef.current) return;             // no concurrent/duplicate decide (items 8, 10)
    const myEpoch = epochRef.current;
    inFlightRef.current = true;
    setBusy('decide'); setError('');
    try {
      const d = await api(`/v1/nova/cases/${caseId}/decide`);
      if (epochRef.current !== myEpoch) return;  // patient/case changed while awaiting -- discard
      setDecision(d);
      setCaseState((prev) => prev ? {...prev, turn_count: d.turn_count} : prev);
      if (Array.isArray(d.differential) && d.differential.length) {
        setSelectedDxId((cur) => cur || d.differential[0].diagnosis_id);
      }
    } catch (e) {
      if (epochRef.current === myEpoch) setError(errText(e));
    } finally {
      inFlightRef.current = false;
      if (epochRef.current === myEpoch) setBusy('');
    }
  }, [errText, closed]);

  const refreshStatus = useCallback(async () => {
    try {
      const s = await api('/health/subsystems');
      setSubsystems(s && (s.subsystems || s));
    } catch { /* status is best-effort; leave as unknown (unknown != healthy) */ }
  }, []);

  useEffect(() => { refreshStatus(); }, [refreshStatus]);

  const createCase = useCallback(async () => {
    if (!patientId) { setError(t('nova.start.selectPatient')); return; }
    if (!chiefComplaint.trim()) { setError(t('nova.start.needComplaint')); return; }
    if (inFlightRef.current) return;
    // New case => new epoch: any prior in-flight response is invalidated.
    epochRef.current += 1;
    const myEpoch = epochRef.current;
    inFlightRef.current = true;
    setBusy('create'); setError(''); setClosed(null); setTimeline([]); setDecision(null); setSelectedDxId(null);
    try {
      const created = await api('/v1/nova/cases', {
        patient_id: patientId,
        encounter_id: encounterId || undefined,
        chief_complaint: chiefComplaint.trim(),
        max_turns: Number(maxTurns) || undefined,
        locale,
      });
      if (epochRef.current !== myEpoch) return;  // patient changed mid-create -- discard
      caseIdRef.current = created.case_id;
      setCaseState(created);
      inFlightRef.current = false;               // release before the follow-on decide
      await runDecide();
    } catch (e) {
      if (epochRef.current === myEpoch) setError(errText(e));
      inFlightRef.current = false;
    } finally {
      if (epochRef.current === myEpoch) setBusy('');
    }
  }, [patientId, encounterId, chiefComplaint, maxTurns, locale, runDecide, errText, t]);

  const submitObservation = useCallback(async (payload) => {
    const caseId = caseIdRef.current;
    if (!caseId || closed) return;
    if (inFlightRef.current) return;             // double-submit / concurrent guard (item 10)
    const myEpoch = epochRef.current;
    inFlightRef.current = true;
    setBusy('observe'); setError(''); setObsResultState(null);
    try {
      const resp = await api(`/v1/nova/cases/${caseId}/observations`, payload);
      if (epochRef.current !== myEpoch) return;
      setObsResultState(resp.applied ? 'applied' : 'replayed');
      if (resp.applied) {
        setTimeline((tl) => [...tl, {
          turn: resp.turn_count, action_type: payload.action_type, key: payload.key,
          result: payload.result, time: new Date().toLocaleTimeString(),
        }]);
        setCaseState((prev) => prev ? {...prev, turn_count: resp.turn_count} : prev);
        inFlightRef.current = false;             // release before the follow-on decide
        await runDecide();
        return;
      }
    } catch (e) {
      // On failure the SAME observation_id is retained by the form, so a retry is idempotent.
      if (epochRef.current === myEpoch) setError(errText(e));
    } finally {
      inFlightRef.current = false;
      if (epochRef.current === myEpoch) setBusy('');
    }
  }, [runDecide, errText, closed]);

  const submitReview = useCallback(async ({disposition, reason}) => {
    const caseId = caseIdRef.current;
    if (!caseId || closed) return;
    if (inFlightRef.current) return;
    const myEpoch = epochRef.current;
    inFlightRef.current = true;
    setBusy('review'); setError('');
    try {
      const resp = await api(`/v1/nova/cases/${caseId}/close`, {disposition, reason});
      if (epochRef.current !== myEpoch) return;
      setClosed(resp.disposition || disposition);
    } catch (e) {
      if (epochRef.current === myEpoch) setError(errText(e));
    } finally {
      inFlightRef.current = false;
      if (epochRef.current === myEpoch) setBusy('');
    }
  }, [errText, closed]);

  // Mid-case locale switch (R7.2 / P): PATCH the locale, then re-decide so display strings render
  // in the new locale. The case is NOT reset -- turn_count, timeline, and differential are kept.
  // No-ops when the case is closed (item 11) or when nothing is in flight would conflict (item 8).
  useEffect(() => {
    if (lastLocaleRef.current === locale) return;
    lastLocaleRef.current = locale;
    const caseId = caseIdRef.current;
    if (!caseId || closed) return;
    if (inFlightRef.current) return;
    const myEpoch = epochRef.current;
    inFlightRef.current = true;
    (async () => {
      setBusy('locale'); setError('');
      try {
        await api(`/v1/nova/cases/${caseId}/locale`, {locale}, undefined, 'PATCH');
        if (epochRef.current !== myEpoch) return;
        inFlightRef.current = false;
        await runDecide();
      } catch (e) {
        if (epochRef.current === myEpoch) setError(errText(e));
        inFlightRef.current = false;
      } finally {
        if (epochRef.current === myEpoch) setBusy('');
      }
    })();
  }, [locale, closed, runDecide, errText]);

  const selectedItem = decision && Array.isArray(decision.differential)
    ? decision.differential.find((d) => d.diagnosis_id === selectedDxId) || null
    : null;

  const safetyBanner = (decision && decision.safety_banner) || (caseState && caseState.safety_banner) || t('safety.banner');
  const recommended = decision ? decision.recommended_next_action : null;
  const isDiagnose = recommended && recommended.action_type === 'DIAGNOSE';

  return (
    <div className="nova-workspace">
      <div className="nova-safety-banner" role="note">
        <span aria-hidden="true">🛡️</span>
        <span>{safetyBanner}</span>
      </div>

      {decision && decision.llm_degraded ? (
        <div className="nova-degraded-banner" role="alert">
          <span aria-hidden="true">⚠️</span>
          <span>{t('status.degradedBanner')}</span>
        </div>
      ) : null}

      <NovaSystemStatus
        subsystems={subsystems}
        llmDegraded={decision ? decision.llm_degraded : false}
        loading={false}
        onRetry={refreshStatus}
      />

      {!patientId ? (
        // Custom/locally-entered patients are not resolvable by the backend EMR adapter, so a
        // N.O.V.A. case cannot be created for them (item 12). State the reason explicitly rather
        // than silently disabling the workspace.
        <section className="nova-panel" aria-labelledby="nova-unavail-h">
          <div className="nova-panel-head"><h3 id="nova-unavail-h">{t('nova.title')}</h3></div>
          <div className="nova-empty">{t('nova.unavailableForCustomPatient')}</div>
        </section>
      ) : !caseState ? (
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

          {error && !closed ? (
            <div className="nova-error" role="alert">
              <span>{error}</span>
              <button className="nova-primary" onClick={runDecide} disabled={busy !== ''}>{t('common.retry')}</button>
            </div>
          ) : null}

          <NovaCriticalPanel redFlags={decision ? decision.red_flags : []} loading={busy === 'decide'} />

          <NovaNextActionPanel action={recommended} loading={busy === 'decide'} />

          <NovaDifferentialPanel
            differential={decision ? decision.differential : []}
            selectedId={selectedDxId}
            onSelect={setSelectedDxId}
            loading={busy === 'decide'}
          />

          <NovaEvidencePanel item={selectedItem} />

          {!closed && recommended && !isDiagnose ? (
            <NovaObservationForm
              recommendedAction={recommended}
              onSubmit={submitObservation}
              submitting={busy === 'observe'}
              resultState={obsResultState}
            />
          ) : null}

          {isDiagnose ? (
            <section className="nova-panel">
              <div className="nova-panel-head"><h3>{t('nova.finalDiagnosis')}</h3></div>
              <p><b>{recommended.display_content || recommended.content}</b></p>
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
