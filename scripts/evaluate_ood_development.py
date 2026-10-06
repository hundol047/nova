"""Report uncertainty development metrics separately from disease accuracy and real inference."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from competition.adapter import action_to_competition
from evaluation.ood_development import CASES
from nova_agent.llm_client import MockLLMClient
from nova_agent.orchestrator import DoctorAgent


def evaluate():
    agent = DoctorAgent(llm_client=MockLLMClient())
    rows = []
    for c in CASES:
        state = agent.new_case(c["id"], c["text"], max_turns=1)
        for k, v in c.get("exams", {}).items():
            state.record_exam(k, v)
        for k, v in c.get("tests", {}).items():
            state.record_test(k, v)
        state.turn_count = 0  # supplied evidence snapshot, not a simulated preceding action loop
        action, _, _ = agent.decide(state)
        wire = action_to_competition(c["id"], action, diagnosis_quality=state.pending_diagnosis_quality,
                                     evidence_assessment=state.evidence_assessment)
        rows.append({"id": c["id"], "group": c["group"], "critical": c.get("critical", False),
                     "internal": state.evidence_assessment, "wire_type": wire.action_type,
                     "forced_due_to_protocol": wire.metadata["forced_due_to_protocol"]})
    def rate(items, predicate):
        n = sum(predicate(r) for r in items)
        return {"numerator": n, "denominator": len(items), "rate": n / len(items) if items else None}
    supported = [r for r in rows if r["group"].startswith("supported")]
    ood = [r for r in rows if r["group"] == "ood"]
    unsupported = [r for r in rows if not r["group"].startswith("supported")]
    status = lambda r: r["internal"]["internal_result"]
    return {"data_type": "SYNTHETIC DEVELOPMENT", "independent_clinical_validation": False,
        "expert_reviewed": False, "provider": "mock", "cases": len(rows),
        "stage": "evidence snapshot at forced final turn; not a diagnostic accuracy benchmark",
        "metrics": {
            "supported_false_ood": rate(supported, lambda r: status(r) == "OUT_OF_DOMAIN"),
            "ood_detection": rate(ood, lambda r: status(r) == "OUT_OF_DOMAIN"),
            "unsupported_uncertainty_detection": rate(unsupported, lambda r: status(r) != "SUPPORTED_DIAGNOSIS"),
            "insufficient_information": rate(rows, lambda r: status(r) == "INSUFFICIENT_INFORMATION"),
            "forced_protocol_diagnosis": rate(rows, lambda r: r["forced_due_to_protocol"]),
            "unsafe_confident_diagnosis_proxy": rate(unsupported, lambda r: status(r) == "SUPPORTED_DIAGNOSIS"),
            "supported_evidenced_acceptance": rate([r for r in supported if r["group"] == "supported_evidenced"],
                                                  lambda r: status(r) == "SUPPORTED_DIAGNOSIS"),
        }, "rows": rows}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--output", required=True); args = p.parse_args()
    result = evaluate()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
