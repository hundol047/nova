"""Reproduce the review's reported defects on the current checkout. Read-only; prints observations."""
import os, json, sys
os.environ.setdefault("NOVA_LLM_PROVIDER", "mock"); os.environ.setdefault("NOVA_COMPETITION_RETRIEVAL", "1")
sec = set(sys.argv[1:]) or {"A","B","C","D","E","F"}
from nova_agent.state import PatientState
from nova_agent.differential import DifferentialEngine
def dx(s):
    return DifferentialEngine().update(s)
def item(s, did):
    return next((d for d in dx(s) if d.diagnosis_id == did), None)

if "A" in sec:
    from nova_agent.documented_diagnosis import documented_diagnosis_ids as ids
    rows = [
     ("The referral letter says atrial fibrillation was excluded", []),
     ("진단서에 atrial fibrillation 아니라고 적혀 있습니다", []),
     ("The referral letter says atrial fibrillation was ruled out", []),
     ("The letter says pulmonary embolism cannot be excluded", []),
     ("The letter confirms atrial fibrillation but excludes pulmonary embolism", ["cardiac_arrhythmia"]),
     ("The letter confirms atrial fibrillation; the patient has no fever", ["cardiac_arrhythmia"]),
     ("The letter says atrial fibrillation but pulmonary embolism was excluded", ["cardiac_arrhythmia"]),
     ("The letter says atrial fibrillation and I have no nausea", ["cardiac_arrhythmia"]),
     ("My mother was diagnosed with atrial fibrillation yesterday", []),
     ("The specialist letter states atrial fibrillation was present in 2016", []),
     ("진단서에 atrial fibrillation 의심된다고 적혀 있습니다", []),
     ("진단서에 atrial fibrillation 배제할 수 없다고 적혀 있습니다", []),
    ]
    ok = 0
    for t, exp in rows:
        got = ids([t]); hit = sorted(got) == sorted(exp); ok += hit
        print("A", "OK " if hit else "BAD", t, "->", got, "expected", exp)
    print("A total", ok, "/", len(rows))
    s = PatientState(case_id="a", chief_complaint="The referral letter says atrial fibrillation was excluded", demographics={"age": 60, "sex": "male"})
    d = item(s, "cardiac_arrhythmia"); print("A engine excluded-AF:", d and (d.score, d.supporting_evidence, d.candidate_sources))

if "B" in sec:
    from nova_agent.matching import feature_present
    print("B irregular->irregularly irregular:", feature_present('irregularly irregular rhythm', ['Pulse has an irregular rhythm with occasional pauses'], strict=True))
    print("B explicit:", feature_present('irregularly irregular rhythm', ['pulse is irregularly irregular'], strict=True))
    for v in ("BP 106/68, HR 37 regular, Temp 36.7", "BP 120/80, HR 172 regular, Temp 36.8", "BP 120/80, HR 68 regular, Temp 36.8"):
        s = PatientState(case_id="b", chief_complaint="I nearly fainted", demographics={"age": 70, "sex": "male"})
        s.preliminary_rules = True; s.record_initial_vitals(v)
        d = item(s, "cardiac_arrhythmia")
        print("B", v, "| vital findings", s.vital_sign_findings, "| arrhythmia", d and (round(d.score,2), d.supporting_evidence))
    s = PatientState(case_id="b2", chief_complaint="my heart feels irregular", demographics={"age": 70, "sex": "male"})
    s.record_exam("cardiac_auscultation", "Pulse has an irregular rhythm with occasional pauses")
    d = item(s, "cardiac_arrhythmia"); print("B engine general irregular:", d and (round(d.score,2), d.supporting_evidence))

if "C" in sec:
    for ans in ("Yes.", "No.", "I don't know.", "No palpitations.", "아니요, 없어요."):
        s = PatientState(case_id="c", chief_complaint="I feel dizzy", demographics={"age": 50, "sex": "male"})
        s.record_ask("associated_symptoms:palpitations", "Any palpitations?", ans)
        d = item(s, "cardiac_arrhythmia")
        print("C", repr(ans), "pos", s.pertinent_positives, "neg", s.pertinent_negatives, "| arr", d and (round(d.score,2), d.supporting_evidence, d.contradictory_evidence))
    s = PatientState(case_id="c2", chief_complaint="I feel dizzy", demographics={"age": 50, "sex": "male"})
    s.record_ask("medication", "What medicines?", "I cannot remember their names.")
    print("C meds", [(m.name, m.status) for m in s.medications])

if "D" in sec or "E" in sec:
    import importlib
    from evaluation.preliminary_driver import run_episode
    C = importlib.import_module("evaluation.validation_cases_round_p").VALIDATION_CASES_ROUND_P
    for cid in ("ValP_33", "ValP_34", "ValP_17", "ValP_11", "ValP_13", "ValP_16"):
        c = [x for x in C if x.case_id == cid][0]
        ep = run_episode(c); w = ep.wire[-1]; md = w.get("metadata") or {}
        says = [x.get("content") for x in ep.wire if x.get("action_type") == "SAY"][-2:]
        A = (w.get("soap") or {}).get("A", "")[:160].replace("\n", " | ")
        print("D", cid, "primary", w.get("primary_diagnosis"), "| key", md.get("key"), "| completion", md.get("completion_type"), md.get("internal_result"), "| closing", says, "| A:", A)
