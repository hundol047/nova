def test_skip_only_exact_already_supported_specific_question(monkeypatch):
    import nova_agent.config as config
    import nova_agent.missing_info as missing
    from nova_agent.differential import DifferentialItem
    from nova_agent.state import PatientState
    monkeypatch.setattr(config, "_config", config.NovaConfig(competition_retrieval_enabled=True))
    monkeypatch.setattr(missing, "_resolve_entry", lambda _: {
        "discriminating_questions": ["associated_symptoms:violet marker", "associated_symptoms:silver marker", "onset"],
    })
    item = DifferentialItem(diagnosis_id="fixture", diagnosis="Fixture", rank=1,
                            supporting_evidence=["violet marker"], score=1, score_ratio=1,
                            confidence_band="HIGH", urgency="LOW", dangerous_if_missed=False)
    state = PatientState(case_id="fixture", chief_complaint="a fixture symptom")
    keys = {c.key for c in missing.MissingInformationAnalyzer().analyze(state, [item], [])}
    assert "associated_symptoms:violet marker" not in keys
    assert "associated_symptoms:silver marker" in keys and "onset" in keys
    item.supporting_evidence = ["violet marker not present"]
    keys = {c.key for c in missing.MissingInformationAnalyzer().analyze(state, [item], [])}
    assert "associated_symptoms:violet marker" in keys


def test_ontology_coverage_requires_every_discriminator_and_never_substring(monkeypatch):
    import nova_agent.missing_info as missing
    import nova_agent.differential as differential
    from nova_agent.resolution import _ontology_workup_addressed
    from nova_agent.state import PatientState
    monkeypatch.setattr(missing, "_resolve_entry", lambda _: {
        "discriminating_questions": ["associated_symptoms:violet marker", "onset"],
    })
    evidence = ["violet marker"]
    monkeypatch.setattr(differential, "_score_disease", lambda *_: (0, 0, evidence, [], []))
    state = PatientState(case_id="independent", chief_complaint="fixture")
    assert not _ontology_workup_addressed("onto::fixture", state)
    state.asked_questions.append("ask:onset")
    assert _ontology_workup_addressed("onto::fixture", state)
    evidence[:] = ["violet marker not present"]
    assert not _ontology_workup_addressed("onto::fixture", state)
    evidence[:] = ["violet"]
    assert not _ontology_workup_addressed("onto::fixture", state)
    evidence.clear()
    assert not _ontology_workup_addressed("onto::fixture", state)
    state.asked_questions.append("ask:associated_symptoms:violet marker")
    assert _ontology_workup_addressed("onto::fixture", state)
    # No cross-patient remembered coverage.
    other = PatientState(case_id="other", chief_complaint="fixture")
    assert not _ontology_workup_addressed("onto::fixture", other)
