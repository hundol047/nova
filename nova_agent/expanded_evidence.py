"""Conservative, source-bound evidence rules for the expanded catalog.

Rules support ranking, not clinical confirmation or exclusion. Literal aliases are
intentionally bounded: no token-overlap inference, no positive from a test order.
"""
import re
from functools import lru_cache
from nova_agent.evidence_interpreter import asserted_clauses, patient_symptom_findings, positive_clauses
from nova_agent.language import normalize_clinical_text


@lru_cache(maxsize=1024)
def _phrase_pattern(phrase):
    return re.compile(r'(?<!\w)' + re.escape(phrase).replace(r'\ ', r'\s+') + r'(?!\w)', re.I)


def observed(phrase, texts):
    for text in patient_symptom_findings(texts):
        for clause in asserted_clauses(normalize_clinical_text(text)):
            if re.search(r'\b(?:history of|previously|resolved|ruled out|excluded)\b', clause, re.I):
                continue
            raw_match = _phrase_pattern(phrase).search(clause)
            if raw_match and re.match(r'\s*(?:is |was |are |were )?(?:absent|negative|not seen|not detected|not present)\b', clause[raw_match.end():], re.I):
                continue
            for positive in positive_clauses(clause):
                match = _phrase_pattern(phrase).search(positive)
                if match and not re.match(r'\s*(?:is |was |are |were )?(?:absent|negative|not seen|not detected|not present)\b', positive[match.end():], re.I):
                    return True
    return False


def rule_matches(entry, state):
    results = {**state.physical_examinations, **state.laboratory_tests, **state.imaging}
    return [any(observed(phrase, [results.get(rule['source'], '')]) for phrase in rule['any_of'])
            and not any(denied(phrase, results.get(rule['source'], '')) for phrase in rule['any_of'])
            for rule in entry.get('evidence_rules', [])]


def denied(phrase, text):
    for clause in asserted_clauses(normalize_clinical_text(text)):
        match = _phrase_pattern(phrase).search(clause)
        if not match:
            continue
        if (re.search(r'\b(?:no|without|denies|negative for|absence of)\s+(?:any\s+)?$', clause[:match.start()], re.I)
            or re.match(r'\s*(?:is |was |are |were )?(?:absent|negative|not seen|not detected|not present)\b', clause[match.end():], re.I)):
            return True
    return False


def evidence_complete(entry, state):
    matches = rule_matches(entry, state)
    return bool(matches) and all(matches)


def score_expanded(entry, state):
    findings = state.all_findings_text()
    support, missing, contradictions = [], [], []
    score = 0.0
    for phrase in entry['typical_features']:
        if observed(phrase, findings):
            support.append(phrase)
            score += 1.0
        else:
            missing.append(phrase)
    for rule, matched in zip(entry['evidence_rules'], rule_matches(entry, state)):
        label = rule['source'] + ': ' + ' / '.join(rule['any_of'])
        if matched:
            support.append(label)
            score += 2.5
        else:
            missing.append(label)
        result = {**state.physical_examinations, **state.laboratory_tests, **state.imaging}.get(rule['source'], '')
        if any(denied(phrase, result) for phrase in rule['any_of']):
            contradictions.append(label)
    maximum = len(entry['typical_features']) + 2.5 * len(entry['evidence_rules'])
    return score, max(maximum, 1.0), support, contradictions, missing
