"""The built submission package must actually contain the competition retrieval runtime
(nova_agent/retrieval_pipeline.py, nova_agent/open_world.py, nova_agent/ontology/, and the Tier-2
catalog data file) -- not merely exclude the wrong things. Mirrors the lenient
"skip if not built" pattern tests/test_submission_excludes_web.py already uses, since submission/
is a build artifact, not checked-in source."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_submission_contains_the_retrieval_pipeline_module():
    submission_nova_agent = _REPO_ROOT / "submission" / "nova_agent"
    if not submission_nova_agent.exists():
        return
    assert (submission_nova_agent / "retrieval_pipeline.py").is_file()
    assert (submission_nova_agent / "open_world.py").is_file()


def test_submission_contains_the_ontology_package_and_tier2_catalog():
    submission_nova_agent = _REPO_ROOT / "submission" / "nova_agent"
    if not submission_nova_agent.exists():
        return
    assert (submission_nova_agent / "ontology").is_dir()
    assert (submission_nova_agent / "ontology" / "registry.py").is_file()
    assert (submission_nova_agent / "knowledge" / "tier2_catalog.json").is_file()
