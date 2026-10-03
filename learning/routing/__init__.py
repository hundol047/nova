"""Multi-specialty routing (PHASE 1 PART E).

Routes a patient presentation to one or MORE clinical specialties simultaneously (a chest-pain +
fever + dyspnea patient may be cardiology HIGH, pulmonary MEDIUM, infectious MEDIUM at once). The
router is a RECALL AID, never a filter of last resort: its output can boost specialty-relevant
candidates, but a low-confidence route falls back to broad global retrieval, and a router miss can
NEVER remove a candidate — especially not a critical one (safety-recall runs independently).

Dependency-free (deterministic keyword/category scoring; torch-optional learned router later).
Never part of the competition submission.
"""

from learning.routing.router import (
    SpecialtyRouter,
    RouteBand,
    RouteResult,
    SpecialtyActivation,
)

__all__ = ["SpecialtyRouter", "RouteBand", "RouteResult", "SpecialtyActivation"]
