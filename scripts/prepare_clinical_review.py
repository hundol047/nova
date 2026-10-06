"""Offline field-level provenance triage and clinician review packet.

Lexical source occurrences are review leads, NOT medical validation or recovered
historical provenance. Never reads evaluation labels or writes diagnostic rules.
"""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/clinical_review_pass"
DOC = ROOT / "docs/clinical_review"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(value):
    return " ".join(re.findall(r"\w+", str(value).casefold().replace("_", " ")))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def leaves(value, pointer=""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, pointer + "/" + str(key).replace("~", "~0").replace("/", "~1"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from leaves(child, pointer + "/" + str(index))
    else:
        yield pointer, value


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    DOC.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((ROOT / "nova_agent/knowledge/licensed_references.json").read_text())
    references = catalog["records"]
    index = {}
    for ref in references:
        if ref["kind"] != "disease_reference":
            continue
        for word in {norm(s) for s in [ref["title"], *ref["aliases"]]}:
            index.setdefault(word, []).append(ref)
    facts, forms = [], []
    paths = sorted((ROOT / "nova_agent/knowledge/diseases").glob("*.json"))
    paths += [ROOT / "nova_agent/knowledge/tier2_catalog.json", ROOT / "nova_agent/knowledge/tier2_enrichment.json"]
    paths += sorted((ROOT / "nova_agent/knowledge/diagnostic_tests").glob("*.json"))
    paths += sorted((ROOT / "nova_agent/knowledge/guidelines").glob("*.json"))
    paths += sorted((ROOT / "nova_agent/knowledge/red_flags").glob("*.json"))
    for path in paths:
        data = json.loads(path.read_text())
        groups = enumerate(data) if isinstance(data, list) else [(None, data)]
        for idx, obj in groups:
            # For core profiles retain identity-based reference leads. For other structures
            # preserve every field, leaving linkage unreviewed rather than guessing ontology.
            matched = {}
            if isinstance(obj, dict) and path.parent.name == "diseases":
                for label in [obj.get("name", ""), *obj.get("aliases", [])]:
                    for ref in index.get(norm(label), []):
                        matched.setdefault(ref["reference_id"], dict(ref, match_label=label))
            lead_refs = list(matched.values())
            for ptr, value in leaves(obj, "" if idx is None else f"/{idx}"):
                occurrences = []
                # Exact whole normalized phrase only; even presence does not establish
                # indication, polarity, specificity, dose/threshold validity or causality.
                q = norm(value) if isinstance(value, str) else ""
                if len(q) >= 5:
                    for ref in lead_refs:
                        if " " + q + " " in " " + norm(ref["text"]) + " ":
                            occurrences.append(ref["reference_id"])
                facts.append(dict(path=str(path.relative_to(ROOT)), pointer=ptr, value=value,
                                  original_source_status="UNRESOLVED",
                                  reference_occurrences=occurrences,
                                  occurrence_status="TEXT_OCCURRENCE_ONLY_NOT_VALIDATED" if occurrences else "NO_LINK_ESTABLISHED",
                                  clinical_review="PENDING", rights_review="PENDING_ORIGINAL_OR_REPLACEMENT_EVIDENCE"))
            if isinstance(obj, dict) and path.parent.name == "diseases":
                forms.append(dict(disease_id=obj["id"], name=obj["name"], source_path=str(path.relative_to(ROOT)),
                                  source_sha256=sha(path), dangerous=obj.get("dangerous"), urgency=obj.get("urgency"),
                                  current_profile=obj, source_leads=[{
                                      "reference_id": r["reference_id"], "title": r["title"], "url": r["source_url"],
                                      "matched_existing_label": r["match_label"], "license": catalog["sources"][r["source"]]["license"],
                                      "version": catalog["sources"][r["source"]]["version"],
                                      "attribution": catalog["sources"][r["source"]]["attribution"],
                                      "relationship": "LEXICAL_REVIEW_LEAD_NOT_VERIFIED_CLINICAL_EQUIVALENCE",
                                  } for r in lead_refs],
                                  review={"reviewer_name": None, "qualification": None, "review_date": None,
                                          "feature_validity": "PENDING", "objective_finding_specificity": "PENDING",
                                          "dangerous_alternatives": "PENDING", "minimum_workup": "PENDING",
                                          "negative_evidence_sufficiency": "PENDING", "population_exceptions": "PENDING",
                                          "recommended_corrections": [], "supporting_sources": [], "approval": "PENDING"}))
    # Retain code-embedded constants separately. Their presence is not evidence of a
    # medically calibrated weight, threshold or verified multilingual equivalence.
    embedded = []
    for name in ("lay_language", "multilingual_concepts", "taxonomy", "matching", "objective_evidence",
                 "differential", "stop_policy", "resolution", "safety", "missing_info", "action_selector", "config"):
        path = ROOT / "nova_agent" / (name + ".py")
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                try:
                    value = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    continue
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                embedded.append(dict(path=str(path.relative_to(ROOT)), line=node.lineno,
                                     names=[ast.unparse(t) for t in targets], value=value,
                                     status="UNRESOLVED_OR_ENGINEERING_PARAMETER_REQUIRES_CLASSIFICATION"))
    # Python sets are encoded as sorted lists; snapshot is a review index, not executable code.
    embedded = json.loads(json.dumps(embedded, ensure_ascii=False, default=lambda x: sorted(x)))
    write(OUT / "field_provenance_inventory.json", dict(
        scope="Every JSON leaf in legacy diseases/catalog/enrichment/tests/guidelines/red-flags; selected module-level literal constants",
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in paths},
        clinical_validation=False, historical_provenance_recovered=False,
        rule="A source mention is a review lead, never retrospective provenance or clinical approval",
        fields=facts, embedded_literals=embedded))
    forms.sort(key=lambda f: (not f["dangerous"], f["name"]))
    write(DOC / "CLINICAL_REVIEW_FORM.json", forms)
    tier2 = json.loads((ROOT / "nova_agent/knowledge/tier2_catalog.json").read_text())["conditions"]
    enrichment = json.loads((ROOT / "nova_agent/knowledge/tier2_enrichment.json").read_text())["entries"]
    enriched = {e["id"]: e for e in enrichment}
    summary = dict(core_profiles=len(forms), field_count=len(facts),
                   literal_constant_count=len(embedded),
                   exact_text_occurrences=sum(bool(f["reference_occurrences"]) for f in facts),
                   clinically_verified_fields=0,
                   tier2_total=len(tier2), tier2_enrichment_entries=len(enrichment),
                   tier2_with_features=sum(bool(e.get("typical_features") or enriched.get(e["id"], {}).get("typical_features")) for e in tier2),
                   tier2_with_confirmatory=sum(bool(e.get("confirmatory_findings") or enriched.get(e["id"], {}).get("confirmatory_findings")) for e in tier2),
                   tier2_clinician_reviewed=0, source_linked_core_profiles=sum(bool(f["source_leads"]) for f in forms))
    summary["tier2_without_features"] = len(tier2) - summary["tier2_with_features"]
    write(OUT / "provenance_summary.json", summary)
    lines = ["# NOVA 임상 검토 요청 자료", "", "퓨처랩스 · 작성 기준: 2026-10-05", "",
             "이 문서는 교수님께 검토를 요청하기 위한 자료입니다. 검토 완료·자문 참여·추천·승인을 의미하지 않습니다.",
             "실제 환자 기록 제공은 필요하지 않습니다. 현재 규칙의 타당성, 빠진 위험 신호, 잘못된 확진 표현을 우선 검토해 주시면 됩니다.",
             "", "## 검토 순서", "",
             "1. 위험 질환의 누락 가능성, 음성 검사로 배제하는 조건, 필요한 최소 검사.",
             "2. 증상·검사 소견이 해당 질환에 얼마나 특이적인지와 수치·단위·시간 조건.",
             "3. 임신·소아·고령자·면역저하자 등 적용 범위와 예외.",
             "4. 한국어·일본어 표현이 같은 임상 개념을 뜻하는지.",
             "", "## 자료 해석 시 주의", "",
             "- 아래 문구와 수치는 현재 코드의 내용이며, 검증된 진료지침이라는 뜻이 아닙니다.",
             "- 연결된 공개 자료는 새로 찾은 검토용 근거 후보입니다. 기존 규칙의 원출처나 동등성을 입증하지 않습니다.",
             "- 출처의 이용 허용, 내용의 의학적 타당성, 교수님의 검토 여부는 각각 별도로 기록합니다.",
             "- 소프트웨어 시험과 합성 사례 정확도는 독립적인 임상 검증을 대신하지 않습니다.",
             "- 특정 문구가 출처에 등장해도 부정·시간·대상·검사 조건을 검토하기 전에는 근거 확인 완료로 표시하지 않습니다.",
             "", "## 작성 양식", "",
             "검토자 성명: ______ / 전문 분야: ______ / 검토일: ______",
             "수정 권고에는 근거 URL·문서명·버전·해당 절/쪽·적용 대상·예외를 함께 적어 주세요.",
             "기계 판독 양식은 CLINICAL_REVIEW_FORM.json의 review 항목입니다. 서명 없이 자동 승인되지 않습니다.", ""]
    for f in forms:
        p = f["current_profile"]
        lines += [f"## {f['name']} — {f['disease_id']}", "", f"파일: `{f['source_path']}`",
                  f"현재 코드 분류: urgency={f['urgency']}, dangerous={f['dangerous']} (미검토)", ""]
        for key, label in (("typical_features", "증상 특징"), ("confirmatory_findings", "현재 확진 관련 소견"),
                           ("risk_factors", "위험 인자"), ("minimum_workup", "최소 검사"),
                           ("red_flag_keywords", "위험 신호"), ("discriminating_tests", "구별용 검사")):
            lines.append(f"- {label}: " + json.dumps(p.get(key, []), ensure_ascii=False))
        lines += ["", "검토용 출처 후보:", ""]
        if not f["source_leads"]:
            lines.append("- 현재 묶음에서 정확한 이름 연결을 찾지 못했습니다. 별도 근거가 필요합니다.")
        for r in f["source_leads"]:
            lines.append(f"- [{r['title']}]({r['url']}) — {r['version']}; {r['license']}; 기존 이름 `{r['matched_existing_label']}`와 문자 일치. 임상적 동등성 미확인.")
        lines += ["", "판정: □ 적절 □ 수정 필요 □ 적용 제한 □ 근거 부족",
                  "수정안 및 근거: ____________________",
                  "음성 결과만으로 배제하면 안 되는 상황: ____________________",
                  "대상 환자·시간·수치·검사법 예외: ____________________", ""]
    (DOC / "PROFESSOR_REVIEW_KO.md").write_text("\n".join(lines))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
