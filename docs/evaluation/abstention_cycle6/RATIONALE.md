# Final-label specificity guard — 2026-10-03

A remaining information-poor headache case was named bacterial meningitis despite no specific
meningeal or related objective evidence. A high rank among weak candidates is not confirmation.
The change adds a final-label context requirement using the existing declarative guard. It does
not remove meningitis from candidate generation, workup or the SafetyLayer. A case with concerning
features can still have urgent safety guidance while the diagnostic name remains unknown.

Context is checked against current symptoms/exam/test strings, not structured family/past history.
The existing scoped feature aliases are reused for this guard so multilingual and ordinary-language
signs do not fail solely because the wording differs. No benchmark case ID, target label, or example
text is used as a trigger. Existing case labels and scoring flags remain frozen.

This is a conservative software naming policy, NOT a clinical exclusion rule. Absence of a named
feature does not rule out meningitis and must not be used to defer medical evaluation. The current
matcher does not constitute comprehensive clinical temporal reasoning or expert adjudication.

Primary guidance checked 2026-10-03:
https://www.nice.org.uk/guidance/ng240/chapter/Recommendations
NICE combines clinical features, blood investigations and lumbar puncture results, rather than
using a single nonspecific blood test to diagnose or exclude the condition. The software policy is
an implementation decision informed by that principle, not a clinically validated diagnostic criterion.

Protocol: replay identical 400-case inputs from each of three previously recorded synthetic cohorts,
compare every final output and safety flag, and run the full non-API software regression suite.
All cohorts have previously exposed, correlated synthetic source families. Neither repeated runs nor
changed wording creates independent patient evidence. This cycle trains no model and changes no fixed
competition LLM weights. The real LLM call requirement and official adapter verification remain open.
