"""Version identifiers surfaced on every production response/audit entry (spec: reproducibility --
a specific case result must be traceable back to the exact agent/prompt/KB/model combination that
produced it).

`kb_fingerprint()` is a content hash rather than a hand-maintained version string: a manually
bumped "KB version 3" is only honest if someone remembers to bump it on every edit, which this
repo's own history shows does not reliably happen. A hash can never be stale.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from nova_agent.config import get_config

AGENT_VERSION = "0.1.0"
SCHEMA_VERSION = "1"
# The LLM prompt template's own version, independent of the agent code version -- bump this
# whenever nova_agent/llm_client.py's build_reasoning_prompt() output shape changes.
PROMPT_VERSION = "1"

_KB_FINGERPRINT_CACHE: dict[str, str] = {}


def kb_fingerprint() -> str:
    """SHA-256 over every file under the configured knowledge directory, sorted by path for
    determinism. Cached per-process (the KB is loaded once at startup and never mutated at
    runtime, same assumption nova_agent/knowledge/retrieval.py's own caching already makes)."""
    knowledge_dir = Path(get_config().knowledge_dir)
    cache_key = str(knowledge_dir)
    cached = _KB_FINGERPRINT_CACHE.get(cache_key)
    if cached is not None:
        return cached
    digest = hashlib.sha256()
    if knowledge_dir.is_dir():
        for path in sorted(knowledge_dir.rglob("*")):
            if path.is_file():
                digest.update(str(path.relative_to(knowledge_dir)).encode("utf-8"))
                digest.update(path.read_bytes())
    fingerprint = digest.hexdigest()[:16]
    _KB_FINGERPRINT_CACHE[cache_key] = fingerprint
    return fingerprint


def model_version() -> str:
    """The configured LLM model identifier, or 'mock' under the offline deterministic provider --
    never a guessed/hardcoded model name (spec: reproducibility requires the REAL value)."""
    cfg = get_config()
    return cfg.llm_model if cfg.llm_provider != "mock" else "mock"
