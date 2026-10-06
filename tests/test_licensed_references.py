import hashlib
import json
from pathlib import Path
import socket

import pytest

from nova_agent.knowledge.licensed_reference_store import (
    CATALOG, MAX_REFERENCES, MAX_TEXT_CHARS, _index, retrieve_licensed_references,
)

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_reproduces_offline_from_retained_source(tmp_path, monkeypatch):
    from scripts import import_licensed_references as importer
    monkeypatch.setattr(importer.urllib.request, "urlopen", lambda *a, **k: pytest.fail("offline build called network"))
    target = tmp_path / "catalog.json"
    # build's diagnostic relative path is rooted in the output directory for this test.
    monkeypatch.setattr(importer, "ROOT", tmp_path)
    importer.build(target)
    assert target.read_bytes() == CATALOG.read_bytes()


def test_every_reference_has_source_rights_and_original_field_hash():
    catalog = json.loads(CATALOG.read_text())
    snapshot_path = ROOT / "research/licensed_references/source_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text())
    assert catalog["source_snapshot_sha256"] == hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    originals = {r["reference_id"]: r for r in snapshot["records"]}
    assert len(originals) == len(catalog["records"]) == 637
    for row in catalog["records"]:
        source = catalog["sources"][row["source"]]
        assert source["license"] and source["terms_url"] and source["attribution"] and source["version"]
        assert row["original_markup_sha256"] == hashlib.sha256(originals[row["reference_id"]]["original_markup"].encode()).hexdigest()
        assert row["text"] and row["source_url"]
        assert not {"typical_features", "confirmatory_findings", "urgency", "diagnosis_label"} & row.keys()
    assert len([r for r in catalog["records"] if r["source"] == "orphanet"]) == 260


def test_exact_matching_bounded_and_no_network(monkeypatch):
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("reference lookup used network"))
    refs = retrieve_licensed_references(["Sepsis", "Wilson disease"], ["troponin", "lipase"])
    assert len(refs) == MAX_REFERENCES
    assert all(len(r["text"]) <= MAX_TEXT_CHARS for r in refs)
    assert refs[0]["title"] == "Sepsis" and refs[1]["title"] == "Troponin Test"
    assert retrieve_licensed_references(["NOT a Sepsis diagnosis", "xyz-unknown"], []) == []


def test_return_values_do_not_mutate_shared_data_or_other_case():
    b = retrieve_licensed_references(["Wilson disease"], [])
    a = retrieve_licensed_references(["Sepsis"], ["ecg"])
    a[0]["text"] = "patient evidence must not persist"
    assert retrieve_licensed_references(["Wilson disease"], []) == b
    assert retrieve_licensed_references(["Sepsis"], ["ecg"])[0]["text"] != a[0]["text"]
    with pytest.raises(TypeError):
        _index()[0]["sepsis"] = ()


def test_ambiguous_publisher_alias_not_resolved():
    raw = json.loads(CATALOG.read_text())
    from nova_agent.knowledge.licensed_reference_store import _normalize
    expected = {}
    for row in raw["records"]:
        if row["kind"] != "disease_reference":
            continue
        for key in {_normalize(v) for v in [row["title"], *row["aliases"]]} - {""}:
            expected.setdefault((key, row["source"]), set()).add(row["reference_id"])
    for (key, source), ids in expected.items():
        if len(ids) > 1:
            assert not any(r.reference_id in ids for r in _index()[0].get(key, ()))


@pytest.mark.parametrize("enabled", [False, True])
def test_references_reach_actual_case_prompt_only_when_rag_enabled(monkeypatch, enabled):
    import nova_agent.config as config
    from nova_agent.orchestrator import DoctorAgent
    from nova_agent.llm_client import MockLLMClient, build_reasoning_prompt
    captured = []

    class Capture(MockLLMClient):
        def generate_turn_output(self, ctx):
            captured.append(ctx)
            return super().generate_turn_output(ctx)

    monkeypatch.setattr(config, "_config", config.NovaConfig(rag_enabled=enabled))
    agent = DoctorAgent(llm_client=Capture())
    state = agent.new_case("reference_case", "chest pain", {"age": 55, "sex": "male"})
    agent.decide(state)
    assert captured
    assert bool(captured[0].external_references) is enabled
    prompt = build_reasoning_prompt(captured[0])
    if enabled:
        assert "not observed patient evidence" in prompt
        assert all(r["source_url"] in prompt and r["attribution"] in prompt for r in captured[0].external_references)
    else:
        assert "Publisher background references" not in prompt


def test_markup_normalization_does_not_add_facts():
    from scripts.import_licensed_references import plain, read_xml
    assert plain("<p>A &amp; B</p><p>Not C.</p><script>bad()</script>") == "A & B\nNot C."
    with pytest.raises(ValueError):
        read_xml(b'<!DOCTYPE x [<!ENTITY x "unsafe">]><x/>')
