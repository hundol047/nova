"""Conservative evidence-quality report, never a calibrated probability."""
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.config import get_config


def assess_decision(state, differential):
    reasons=[]
    if not differential:
        return {'band':'LOW','probability':None,'calibrated':False,'catalog_status':'unsupported','reasons':['no_candidate']}
    top=differential[0]
    known=disease_by_id(top.diagnosis_id) is not None
    if not known:reasons.append('outside_local_catalog')
    if not top.supporting_evidence:reasons.append('no_supporting_evidence')
    if top.contradictory_evidence:reasons.append('contradictory_evidence')
    if len(differential)>1 and abs(top.score-differential[1].score)<=0.25:reasons.append('close_alternative')
    if state.remaining_turns<=get_config().stop_policy.forced_diagnose_remaining_turns:reasons.append('turn_budget_exhausted')
    return {'band':'LOW' if reasons else top.confidence_band,'probability':None,'calibrated':False,
            'catalog_status':'known' if known else 'outside_catalog','reasons':reasons}
