from evaluation.safety_metrics import safety_metrics


def test_observed_flag_does_not_depend_on_diagnosis_correctness():
    rows = [dict(case_id=str(i), critical=c, final_safety_flag=f, correct=correct)
            for i, (c, f, correct) in enumerate([
                (True, True, False), (True, False, True),
                (False, True, True), (False, False, False)])]
    result = safety_metrics(rows)
    assert [result[k] for k in ('tp', 'fp', 'fn', 'tn')] == [1, 1, 1, 1]
    assert result['missed_case_ids'] == ['1']
    assert result['sensitivity'] == result['specificity'] == 0.5


def test_legacy_absent_telemetry_is_unknown_not_false():
    result = safety_metrics([dict(case_id='legacy', critical=True)])
    assert result['uninstrumented_cases'] == 1
    assert result['observed_cases'] == result['fn'] == 0
    assert result['sensitivity'] is None
