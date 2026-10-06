"""Submission-only fail-closed boundary. No organizer route is yet documented.

An environment variable is not approval. Integrate a reviewed organizer transport here
only after the participant guide arrives. Development clients remain outside this gate.
When it is integrated, build the agent with ``competition.submission_profile.build_submission_agent``
(preliminary-round rules forced on, independent of the environment).
"""
from nova_agent.config import get_config


def enforce_submission_provider():
    cfg = get_config()
    if cfg.ml_ranker_enabled or cfg.ml_model_path:
        raise RuntimeError("NOT READY: learned rankers/weights forbidden in preliminary submission")
    raise RuntimeError("NOT READY: EXTERNAL_OFFICIAL_INTERFACE_BLOCKED; no organizer-approved transport integrated")
