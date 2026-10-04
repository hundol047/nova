"""Development-only full Round M experiment; no runtime files or blind sets changed.

Hypothesis: increasing each signal's candidate pool from 80 to 150 improves fixed
retrieval@150 without increasing tests/turns or reducing accuracy/critical recall.
The mutation is process-local and inherited by Linux fork workers. This does not
authorize promoting the result or represent a frozen runtime release.
"""
import json
import multiprocessing
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    multiprocessing.set_start_method("fork")
    import nova_agent.retrieval_pipeline as pipeline
    from scripts import evaluate_round_m_final as evaluation
    assert pipeline._PER_SIGNAL_QUERY_LIMIT == 80
    pipeline._PER_SIGNAL_QUERY_LIMIT = 150
    evaluation.OUT = ROOT / "artifacts/compliance_repair/retrieval_150/traces"
    evaluation.main()
    path = evaluation.OUT.parent / "final_summary.json"
    data = json.loads(path.read_text())
    data["experiment"] = {
        "status": "DEVELOPMENT EXPERIMENT ONLY; NOT CURRENT RUNTIME VERIFICATION",
        "override": {"nova_agent.retrieval_pipeline._PER_SIGNAL_QUERY_LIMIT": 150},
        "baseline_value": 80,
        "runtime_files_unchanged": True,
        "note": "runtime_sha256 identifies on-disk base, not the in-memory override above",
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
