"""Final decision audit shared by model prompts and offline diagnostics.

This adds no new patient evidence or diagnostic authority. It explicitly exposes
source-specific findings and contradictions for the model to reconsider before
committing to its final answer, in the existing single reasoning call.
"""
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.resolution import is_resolved


def review_differential(state, differential):
    notes = []
    if not differential:
        return ["No supported candidate: acquire discriminating evidence before diagnosing."]
    top = differential[0]
    if not top.supporting_evidence:
        notes.append("Leading candidate has no supporting evidence; do not confuse a tie-break with confirmation.")
    for item in differential[:3]:
        notes.append(f"Candidate {item.diagnosis}: support={item.supporting_evidence}; contrary={item.contradictory_evidence}")
        if item.dangerous_if_missed and not is_resolved(item.diagnosis_id, item.contradictory_evidence, state):
            notes.append(f"{item.diagnosis} remains unresolved; a completed procedure alone is not exclusion.")
    notes.append("Reconsider which candidate best explains the objective results, temporal course and medications. Do not discard a specific causal diagnosis merely because a broad syndrome has more generic matching words. Coexisting conditions may both remain plausible.")
    return notes
