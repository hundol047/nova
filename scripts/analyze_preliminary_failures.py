#!/usr/bin/env python3
"""Stage attribution of preliminary-benchmark misses (LOCAL DEVELOPMENT / PRELIMINARY SIMULATION, mock model).

Reads one or two outputs of scripts/evaluate_preliminary_benchmark.py and attributes every wrong SCORED case to the
earliest stage that lost the label. Heuristic engineering attribution, not clinical adjudication:

  normalization  - label is rank 1 of the final differential but the submitted primary name did not match it
  retrieval      - label never reached the final validated differential
  rerank         - label in the differential but below rank 5
  ranking:*      - label at ranks 2-5; sub-cause from the label's own evidence at diagnosis:
                     contradicted   -> a finding was read as AGAINST it (assertion/negation interpretation)
                     no_support     -> none of its features was elicited/recognised (collection or language)
                     outscored      -> it had support but another diagnosis scored higher
  premature      - (flag) diagnosed with < 8 interactions or with an unresolved critical alternative
Optionally compares a second run (e.g. a different retrieval mode or branch) case by case and lists every case that
got WORSE (correct -> wrong) and better.
"""
import argparse
import collections
import json
from pathlib import Path


def stage(r):
    if r["top1"]:
        return None
    rank = r.get("truth_rank")
    if rank == 1:
        return "normalization"
    if rank is None:
        return "retrieval"
    if rank > 5:
        return "rerank"
    if r.get("truth_contradictory"):
        return "ranking:contradicted"
    if not r.get("truth_supporting"):
        return "ranking:no_support"
    return "ranking:outscored"


def rows(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data, {r["case_id"]: r for suite in data["cases"].values() for r in suite}


def summarize(by_id):
    scored = [r for r in by_id.values() if r["scored"]]
    out = {"scored": len(scored), "wrong": sum(not r["top1"] for r in scored), "stages": collections.Counter(),
           "premature_flag": 0, "by_language": {}, "by_group": {}, "critical": {}}
    for r in scored:
        s = stage(r)
        if s:
            out["stages"][s] += 1
            out["premature_flag"] += bool(r["interactions"] < 8 or r["unresolved_critical_at_diagnosis"])
    for key, fn in (("by_language", lambda r: r.get("language", "?")),
                    ("by_group", lambda r: (r["category"].split(";")[1] if r["category"].startswith("ko_prelim;")
                                            else r["category"].split(";")[0]) or "uncategorised")):
        groups = collections.defaultdict(list)
        for r in scored:
            groups[fn(r)].append(r)
        out[key] = {g: {"n": len(v), "top1": round(sum(x["top1"] for x in v) / len(v), 3),
                        "critical_n": sum(x["critical"] for x in v),
                        "critical_top1": sum(x["top1"] for x in v if x["critical"])} for g, v in sorted(groups.items())}
    crit = [r for r in scored if r["critical"]]
    out["critical"] = {"n": len(crit), "top1": sum(r["top1"] for r in crit),
                       "misses": [(r["case_id"], r["truth"], r["primary"], stage(r)) for r in crit if not r["top1"]]}
    out["stages"] = dict(out["stages"])
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run")
    p.add_argument("--compare", help="a second benchmark output to diff against (case by case)")
    p.add_argument("--output")
    a = p.parse_args()
    data, cur = rows(a.run)
    report = {"label": data["label"], "retrieval_mode": data.get("retrieval_mode"), "summary": summarize(cur),
              "misses": [{"case_id": r["case_id"], "truth": r["truth"], "primary": r["primary"], "stage": stage(r),
                          "truth_rank": r.get("truth_rank"), "language": r.get("language"), "critical": r["critical"]}
                         for r in cur.values() if r["scored"] and not r["top1"]]}
    if a.compare:
        other_data, other = rows(a.compare)
        common = [c for c in cur if c in other and cur[c]["scored"]]
        report["comparison"] = {
            "against": a.compare, "against_mode": other_data.get("retrieval_mode"), "common_scored": len(common),
            "worse": [(c, cur[c]["truth"], other[c]["primary"], cur[c]["primary"], cur[c]["critical"]) for c in common
                      if other[c]["top1"] and not cur[c]["top1"]],
            "better": [(c, cur[c]["truth"], other[c]["primary"], cur[c]["primary"], cur[c]["critical"]) for c in common
                       if cur[c]["top1"] and not other[c]["top1"]]}
    text = json.dumps(report, ensure_ascii=False, indent=1)
    print(text)
    if a.output:
        Path(a.output).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
