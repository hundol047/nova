# Round R implementation contract

Baseline remote: 02e56eb8e97ba0b6ce09061091d64222fee1c37a on
claude/determined-brahmagupta-wrfveb; v22 runtime 8257ba6. Worktree is isolated
from the user's existing checkout. Main is unchanged. No AGENTS.md was present.

## Changes

1. Documented diagnosis parsing preserves every named occurrence and original spans.
   Per-diagnosis assertion, experiencer, time and source are independent; coordinated
   diagnosis lists share only their own predicate. An explicit later correction can
   replace the same diagnosis. Uncertain/excluded/family/speculative diagnosis names
   are masked in diagnostic evidence before canonicalization, without deleting raw text.
2. Mixed answers preserve affirmed, negated and unknown clauses. Bare disjunctive Yes
   remains raw context and is excluded from individual finding scores. Family context
   is available through the public state API, while ranking and severity use an explicit
   patient-only view; family-scoped risk features still have their own input.
3. Korean muscle cramps do not create a seizure; near-fainting does not create actual
   loss of consciousness. Urinary pain aliases require the pain–urination relation.
4. Existing KB risks generate bounded, single-intent follow-ups only for supported
   contenders. Short English/Korean/Japanese/Chinese questions retain their intended key.
   No question implies a sodium/potassium result or promotes danger in ranking.
5. Unknown ASK, rejected/unknown EXAM and unavailable TEST are distinct. Auscultatory
   features can generate a supported EXAM. Completion is separate from disease exclusion;
   the wire includes workup coverage, and the SOAP preserves original observations.
6. Final naming blocks generic-only or risk-only danger, unobserved ventricular subtype,
   and uncomplicated faint with an unexplained marked pulse. A documented alternative
   can be selected; otherwise the existing undifferentiated output is used. There is no
   new protocol action, blanket test requirement or new official schema assumption.

## Evaluation integrity

Existing tests are retained. The release-version allowlist will be extended only for
v23; archive/hash/commit assertions remain mandatory. Original evaluation cases,
labels, matching, denominators and simulator replies are unchanged. Former acceptance
cases are DEVELOPMENT regressions. The 24 new synthetic cases were committed and
hashed before execution (7fa7d68); 12 working-diagnosis cases and 12 deliberately
ambiguous/behavior cases are counted separately. Author read implementation and
previous failures: this is not independent clinical validation. No tuning after new
validation results. No blind v18/v19 execution.

Top150 / Weighted RRF / Top25 retrieval architecture and disease count are unchanged.
Official interface and actual fixed-model performance remain NOT VERIFIED.
