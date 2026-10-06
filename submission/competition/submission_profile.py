"""The preliminary-round submission profile: the briefing's rules are ALWAYS on.

``NovaCompetitionAgent()`` follows ``NovaConfig.preliminary_rules`` (ON only for the ``competition``
provider) so every development benchmark keeps its behaviour. A submission must not depend on an
environment variable, so the entrypoint that the organizer contract will eventually plug into builds
its agent here: the rules are forced ON per agent and per case (``preliminary=True``), whatever
``NOVA_PRELIMINARY_RULES`` or ``NOVA_LLM_PROVIDER`` say. This does not open the fail-closed gate in
``competition.provider_lock``: no organizer transport is integrated, so ``submission/run.py`` still exits.
"""
from __future__ import annotations

from typing import Optional

from competition.adapter import NovaCompetitionAgent
from nova_agent.orchestrator import DoctorAgent


def build_submission_agent(agent: Optional[DoctorAgent] = None) -> NovaCompetitionAgent:
    """An adapter whose cases always run under the preliminary-round rules."""
    return NovaCompetitionAgent(agent=agent, preliminary=True)
