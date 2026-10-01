"""Conservative evidence-quality report, never a calibrated probability."""
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.config import get_config


def assess_decision(state, differential):
    reasons=[]
    if not differential:
        return {'band':'LOW','probability':None,'calibrated':False,'catalog_status':'unsupported','reasons':['no_candidate']}
    top=differential[0]
    entry=disease_by_id(top.diagnosis_id)
    from nova_agent.knowledge.reference_catalog import reference_by_name
    reference = None if entry else (reference_by_name(top.diagnosis_id) or reference_by_name(top.diagnosis))
    known=entry is not None
    if entry and entry.get("evidence_rules"):
        from nova_agent.expanded_evidence import evidence_complete
        if not evidence_complete(entry, state):reasons.append("required_evidence_missing")
    if not known:reasons.append('outside_local_catalog')
    if reference:reasons.append('unvalidated_reference_candidate')
    if not top.supporting_evidence:reasons.append('no_supporting_evidence')
    if top.contradictory_evidence:reasons.append('contradictory_evidence')
    if len(differential)>1 and abs(top.score-differential[1].score)<=0.25:reasons.append('close_alternative')
    if state.remaining_turns<=get_config().stop_policy.forced_diagnose_remaining_turns:reasons.append('turn_budget_exhausted')
    return {'band':'LOW' if reasons else top.confidence_band,'probability':None,'calibrated':False,
            'catalog_status':'known' if known else ('reference_only' if reference else 'outside_catalog'),'reasons':reasons}
