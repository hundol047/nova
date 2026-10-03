"""Conservative source checks for LLM-authored evidence, not medical validation.

Require quoted observations. Unsupported paraphrases remain missing evidence;
retrieved medical facts do not establish findings in this patient.
"""
import re
from nova_agent.assertion_status import is_uncertain
from nova_agent.matching import _strip_negated_spans
from nova_agent.state import PatientState


def _clean(text: str) -> str:
    return ' '.join(text.casefold().split()).strip(' .;')


def observed_clauses(state: PatientState, positive: bool) -> list[str]:
    texts = state.all_findings_text(include_context=False)
    if not positive:
        texts = [*texts, *state.pertinent_negatives]
    result = []
    for text in texts:
        for clause in re.split(r'[;\n]|(?<=\w)\.(?=\s|$)', text):
            if positive and (is_uncertain(clause) or re.search(
                    r'\b(?:history of|family history|previously|historical|baseline|last year)\b', clause, re.I)):
                continue
            value = _clean(_strip_negated_spans(clause) if positive else clause)
            if value:
                result.append(value)
    return list(dict.fromkeys(result))


def grounded_quotes(quotes: list[str], state: PatientState, *, positive: bool) -> list[str]:
    clauses = observed_clauses(state, positive)
    accepted = []
    for quote in quotes:
        normalized = _clean(quote)
        if normalized and any(re.search(r'(?<!\w)' + re.escape(normalized) + r'(?!\w)', c)
                              for c in clauses) and quote not in accepted:
            accepted.append(quote)
    return accepted


def distinct_support_count(quotes: list[str], state: PatientState) -> int:
    """Multiple fragments from the same assertion count once toward readiness."""
    clauses = observed_clauses(state, True)
    sources = set()
    for quote in grounded_quotes(quotes, state, positive=True):
        normalized = _clean(quote)
        sources.add(next(i for i, c in enumerate(clauses) if re.search(
            r'(?<!\w)' + re.escape(normalized) + r'(?!\w)', c)))
    return len(sources)
