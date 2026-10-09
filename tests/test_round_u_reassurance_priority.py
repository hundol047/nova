"""Absence of alternatives is not positive evidence for a current cause."""
from nova_agent.differential import _apply_positive_observation_priority


def row(name, score, support, risks=(), contradictory=()):
    return (score, 0.5, {'id':name, 'risk_factors':list(risks)}, list(support), list(contradictory), [], 'LOW')


def test_reassurance_only_cannot_displace_actual_pattern():
    absent = row('unexplained', 4, ['no chest pain', 'no palpitations'])
    actual = row('observed', 2, ['brief loss of consciousness', 'rapid recovery'], contradictory=['nausea'])
    assert _apply_positive_observation_priority([absent, actual]) == [actual, absent]


def test_risk_alone_does_not_establish_current_illness():
    risk = row('at_risk', 5, ['chronic kidney disease'], risks=['chronic kidney disease'])
    actual = row('observed', 2, ['localized swelling'])
    assert _apply_positive_observation_priority([risk, actual]) == [actual, risk]


def test_positive_competitors_and_direct_contradiction_keep_order():
    a = row('a', 5, ['localized swelling'])
    b = row('b', 3, ['documented diagnosis'])
    refuted = row('refuted', -1, ['rash'], contradictory=['rash'])
    assert _apply_positive_observation_priority([a,b,refuted]) == [a,b,refuted]
