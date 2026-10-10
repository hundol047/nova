#!/usr/bin/env python3
"""Post-Round-W evaluation snapshot: preliminary suites (ALL / Round M / J / I / Korean / tuning), the EXAM-rejection
and unscripted-unknown variants, the "same-condition" set (every frozen synthetic fixture under evaluation/, run
with evaluate_round_s), and each closing set reported on its own. Mock LLM, competition retrieval, no TEST action.
Synthetic development data only -- NOT an official score.

    python scripts/post_round_w_baseline.py --output artifacts/post_round_w/baseline.json --work /tmp/pw
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ENV = dict(os.environ, NOVA_LLM_PROVIDER="mock", NOVA_COMPETITION_RETRIEVAL="1", PYTHONDONTWRITEBYTECODE="1")
METRICS = ("cases", "scored", "top1", "top3", "top5", "critical_cases", "critical_recall", "avg_interactions",
           "median_interactions", "say_count", "exam_count", "rejected_exam_count", "duplicate_action_rate",
           "premature_diagnosis_rate", "unresolved_critical_alternative_rate", "soap_information_retention",
           "soap_unsupported_info_rate", "rule_violations")
SUITE_NAMES = {"ALL": "ALL", "dev_round_m": "Round M", "dev_round_j": "Round J", "dev_round_i": "Round I",
               "ko_new": "Korean", "tuning": "tuning"}


def _summary(s: dict) -> dict:
    out = {k: s.get(k) for k in METRICS}
    if s.get("critical_cases") is not None and s.get("critical_recall") is not None:
        out["critical_miss_count"] = round(s["critical_cases"] * (1 - s["critical_recall"]))
    return out


def _prelim(work: Path, flag: str = "") -> dict:
    out = work / f"prelim{flag.replace('--', '_')}.json"
    if out.exists():
        return json.loads(out.read_text())
    cmd = [sys.executable, "scripts/evaluate_preliminary_benchmark.py", "--workers", "4", "--output", str(out)]
    if flag:
        cmd.append(flag)
    subprocess.run(cmd, cwd=ROOT, env=ENV, check=True, stdout=subprocess.DEVNULL)
    return json.loads(out.read_text())


def _fixtures():
    """Exactly the frozen fixtures of the same-condition runner (scripts/run_round_u_followup_suite.py FROZEN + the
    follow-up, Round V and Round W extras), each with its own evaluator."""
    from scripts.run_round_u_followup_suite import FROZEN
    for _name, fixture, manifest, evaluator in FROZEN:
        yield ROOT / "evaluation" / fixture, (ROOT / "evaluation" / manifest) if manifest else None, evaluator
    for stem in ("round_u_followup", "round_u_followup_closing", "round_v", "round_v_closing", "round_w", "round_w_closing"):
        path = ROOT / "evaluation" / f"frozen_validation_{stem}.json"
        if path.exists():
            yield path, path.with_name(path.stem + "_manifest.json"), "evaluate_round_s"


def _fixture(work: Path, path: Path, manifest, evaluator: str) -> dict:
    out = work / path.stem
    if not (out / "summary.json").exists():
        cmd = [sys.executable, f"scripts/{evaluator}.py", "--checkout", str(ROOT), "--cases", str(path), "--output", str(out)]
        if manifest:
            cmd += ["--freeze", str(manifest)]
        subprocess.run(cmd, cwd=ROOT, env=ENV, check=True, stdout=subprocess.DEVNULL)
    return json.loads((out / "summary.json").read_text())


def _pool(rows: list) -> dict:
    """Case-weighted pooled metrics over several fixtures (same definitions as the per-fixture summaries)."""
    scored = [r for r in rows if r.get("scored")]
    crit = [r for r in rows if r.get("critical")]
    n = len(rows) or 1
    return dict(cases=len(rows), scored=len(scored),
                top1=sum(bool(r.get("top1")) for r in scored) / (len(scored) or 1),
                top3=sum(bool(r.get("top3")) for r in scored) / (len(scored) or 1),
                top5=sum(bool(r.get("top5")) for r in scored) / (len(scored) or 1),
                critical_cases=len(crit), critical_recall=sum(bool(r.get("top1")) for r in crit) / (len(crit) or 1),
                critical_miss_count=sum(not r.get("top1") for r in crit),
                avg_interactions=sum(r.get("interactions", 0) for r in rows) / n)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--work", required=True)
    a = p.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    prelim = _prelim(work)
    rejection = _prelim(work, "--exam-rejection")
    unknown = _prelim(work, "--unscripted-unknown")
    suites = {SUITE_NAMES.get(k, k): _summary(v) for k, v in prelim["summaries"].items()}
    fixtures, same_rows, closing = {}, [], {}
    for path, manifest, evaluator in _fixtures():
        s = _fixture(work, path, manifest, evaluator)
        fixtures[path.stem] = dict(summary=_summary(s["summary"]), behavior=s.get("behavior"))
        if "closing" in path.stem:
            closing[path.stem] = fixtures[path.stem]
        same_rows += s["rows"]
    result = dict(
        label="LOCAL DEVELOPMENT / PRELIMINARY SIMULATION -- mock LLM, synthetic cases, NOT AN OFFICIAL SCORE",
        head=head, generated_utc=datetime.now(timezone.utc).isoformat(),
        preliminary=suites,
        preliminary_exam_rejection=_summary(rejection["summaries"]["ALL"]),
        preliminary_unscripted_unknown=_summary(unknown["summaries"]["ALL"]),
        same_condition=dict(definition="union of every frozen synthetic fixture under evaluation/ (Rounds R-W, "
                                       "follow-up, acceptance), run with scripts/evaluate_round_s.py",
                            pooled=_pool(same_rows), fixtures=fixtures),
        closing_sets=closing,
        round_w_closing=closing.get("frozen_validation_round_w_closing"),
    )
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: {m: v.get(m) for m in ("cases", "top1", "critical_recall", "avg_interactions")}
                      for k, v in suites.items()}, indent=1))
    print("same_condition", json.dumps(result["same_condition"]["pooled"]))


if __name__ == "__main__":
    main()
