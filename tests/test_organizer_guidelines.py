"""Organizer guideline corpus retriever (NOVA_GUIDELINES_DIR). Synthetic corpus only; the organizer corpus is never
copied into the repository."""
import os
import time

from nova_agent.organizer_guidelines import build_index, retrieve, tokens

DOC_EN = """---
title: Hyperthyroidism overview
organization: StatPearls
year: 2024
language: en
source_url: https://example.org/hyper
license: CC BY-NC-ND 4.0
---
# Hyperthyroidism

Hyperthyroidism presents with weight loss, heat intolerance, palpitations and tremor.

Graves disease is the commonest cause; examine for goitre, bruit and eye signs.
"""
DOC_KO = """---
title: 불면증 진료지침
organization: 대한수면학회
year: 2023
language: ko
source_url: https://example.kr/insomnia
license: 공공누리 제4유형
---
# 불면증

수면제 장기 복용 시 내성과 금단 증상을 확인하고 용량 증량 여부를 묻는다.
"""


def _corpus(tmp_path, with_catalog=True):
    root = tmp_path / "guidelines"
    (root / "US_StatPearls").mkdir(parents=True)
    (root / "KR_Societies").mkdir()
    (root / "US_StatPearls" / "hyperthyroidism.md").write_text(DOC_EN, encoding="utf-8")
    (root / "KR_Societies" / "insomnia.md").write_text(DOC_KO, encoding="utf-8")
    (root / "KR_Societies" / "broken.md").write_bytes(b"\xff\xfe not yaml at all")
    outside = tmp_path / "outside.md"
    outside.write_text("---\ntitle: secret thyroid\n---\nthyroid secret", encoding="utf-8")
    os.symlink(outside, root / "US_StatPearls" / "link.md")
    if with_catalog:
        (root / "catalog.csv").write_text(
            "filename,title,organization,year,language,document type,format,license,source URL\n"
            "US_StatPearls/hyperthyroidism.md,Hyperthyroidism overview,StatPearls,2024,en,질환 개요(교과서),md,CC BY-NC-ND 4.0,https://example.org/hyper\n"
            "KR_Societies/insomnia.md,불면증 진료지침,대한수면학회,2023,ko,진료지침,md,공공누리 제4유형,https://example.kr/insomnia\n"
            "../outside.md,traversal,x,2020,en,기타,md,x,x\n", encoding="utf-8")
    return root


def test_missing_directory_degrades_to_empty(tmp_path, monkeypatch):
    monkeypatch.delenv("NOVA_GUIDELINES_DIR", raising=False)
    index = build_index()
    assert not index.available and retrieve(index, "thyroid") == []
    assert retrieve(build_index(str(tmp_path / "nope")), "thyroid") == []


def test_catalog_index_keeps_license_and_source(tmp_path):
    index = build_index(str(_corpus(tmp_path)))
    assert index.source == "catalog.csv" and len(index.docs) == 2 and index.skipped == 1  # traversal row skipped
    refs = retrieve(index, "weight loss palpitations hyperthyroidism", k=2)
    assert refs and refs[0]["title"] == "Hyperthyroidism overview"
    assert refs[0]["license"] == "CC BY-NC-ND 4.0" and refs[0]["source_url"] == "https://example.org/hyper"
    assert "goitre" in refs[0]["excerpt"] or "weight loss" in refs[0]["excerpt"]
    assert "title:" not in refs[0]["excerpt"]  # front matter is not excerpted


def test_korean_query_and_front_matter_fallback(tmp_path):
    index = build_index(str(_corpus(tmp_path, with_catalog=False)))
    assert index.source == "front_matter"
    assert all("link.md" not in d.path for d in index.docs)  # symlink not followed
    refs = retrieve(index, "불면증 수면제 금단", k=1)
    assert refs and refs[0]["organization"] == "대한수면학회" and "금단" in refs[0]["excerpt"]


def test_retrieval_is_fast_and_bounded(tmp_path):
    root = tmp_path / "big"
    root.mkdir()
    for i in range(500):
        (root / f"doc{i}.md").write_text(f"---\ntitle: topic {i} condition{i % 50}\n---\ntext condition{i % 50} " * 3,
                                        encoding="utf-8")
    started = time.monotonic()
    index = build_index(str(root))
    build = time.monotonic() - started
    started = time.monotonic()
    refs = retrieve(index, "condition7", k=3, max_chars=200)
    assert build < 10 and time.monotonic() - started < 1
    assert len(refs) == 3 and all(len(r["excerpt"]) <= 200 for r in refs)


def test_tokens_cover_korean_and_english():
    assert "hyperthyroidism" in tokens("Hyperthyroidism overview")
    assert "갑상" in tokens("갑상샘항진증") and "the" not in tokens("the patient")
