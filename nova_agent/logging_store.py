"""Case logging (spec section 19). Reuses SynexAgent's own AuditStore (backend/app/services/
audit.py) as-is -- same append-only SQLite event log the rest of the app already uses -- instead
of building a second logging mechanism. Only the small, evaluable fields spec section 19 lists are
recorded; no raw prompt text or chain-of-thought is ever persisted.
"""

from __future__ import annotations

from typing import List, Optional

from nova_agent._synex import AuditStore
from nova_agent.action_selector import AgentAction
from nova_agent.differential import DifferentialItem
from nova_agent.state import PatientState


class NovaCaseLogger:
    def __init__(self, store: Optional[AuditStore] = None) -> None:
        self.store = store or AuditStore()

    def log_turn(self, state: PatientState, action: AgentAction, differential: List[DifferentialItem],
                 safety_flags: List[str]) -> None:
        detail = {
            "turn": state.turn_count,
            "selected_action": {"type": action.action_type, "key": action.key, "content": action.content},
            "top_differential": [{"diagnosis": d.diagnosis, "confidence": d.confidence_band} for d in differential[:3]],
            "safety_flags": safety_flags,
            "remaining_turns": state.remaining_turns,
        }
        self.store.record(state.case_id, "nova_turn", detail)

    def log_final(self, state: PatientState, result: str) -> None:
        detail = {
            "final_diagnosis": state.final_diagnosis,
            "turn_count": state.turn_count,
            "result": result,
        }
        self.store.record(state.case_id, "nova_final", detail)

    def history(self, case_id: str) -> list:
        return self.store.list(case_id)
