"""API-key authentication + RBAC (spec: production API must require authentication, no anonymous
public endpoints; roles clinician/reviewer/admin/service; least-privilege credential separation).

Deliberately a static API-key map (production/config.py's NOVA_API_KEYS), not a full OAuth/JWT
identity provider -- this is the minimum real authentication a decision-support API needs to stop
being "anonymous public", and it is the piece that can be swapped for a real IdP later without
touching call sites (every endpoint depends on `Principal`, never on the key format itself).
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Iterable

from production.config import ProductionConfig, get_production_config
from production.errors import AuthenticationError, AuthorizationError

Role = str  # "clinician" | "reviewer" | "admin" | "service"

# Least-privilege role -> allowed-action map (spec: least-privilege credential separation).
# "service" is for machine-to-machine callers (e.g. an internal system posting observations),
# deliberately excluded from `decide` -- a service credential can feed data in, but the clinical
# decide step requires a human-attributable clinician/reviewer/admin credential.
_ROLE_PERMISSIONS: dict[Role, frozenset[str]] = {
    "clinician": frozenset({"create_case", "add_observation", "decide", "read_case"}),
    "reviewer": frozenset({"read_case"}),
    "admin": frozenset({"create_case", "add_observation", "decide", "read_case", "read_metrics"}),
    "service": frozenset({"create_case", "add_observation", "read_case", "read_metrics"}),
}


@dataclass(frozen=True)
class Principal:
    api_key_suffix: str  # last 4 chars only -- never echo/log a full credential
    role: Role

    def can(self, action: str) -> bool:
        return action in _ROLE_PERMISSIONS.get(self.role, frozenset())


def _constant_time_lookup(api_key: str, known_keys: dict[str, Role]) -> Role | None:
    """Avoids a timing side-channel on key comparison: compares against every configured key with
    hmac.compare_digest rather than short-circuiting a dict lookup on the first byte mismatch."""
    matched_role: Role | None = None
    for known_key, role in known_keys.items():
        if hmac.compare_digest(api_key, known_key):
            matched_role = role
    return matched_role


def authenticate(api_key: str | None, *, config: ProductionConfig | None = None) -> Principal:
    cfg = config or get_production_config()
    if not cfg.require_auth:
        # Auth explicitly disabled (dev/test only -- ProductionConfig.validate() refuses to start
        # this way in a real `production` environment). Every caller becomes an admin locally so
        # dev/test exercises the full permission surface without needing a configured key.
        return Principal(api_key_suffix="dev", role="admin")
    if not api_key:
        raise AuthenticationError("Missing API key (X-API-Key header).")
    role = _constant_time_lookup(api_key, cfg.api_keys)
    if role is None:
        raise AuthenticationError("Invalid API key.")
    return Principal(api_key_suffix=api_key[-4:], role=role)


def authorize(principal: Principal, action: str) -> None:
    if not principal.can(action):
        raise AuthorizationError(f"Role {principal.role!r} is not permitted to perform {action!r}.")


def require(principal: Principal, action: str) -> Principal:
    """Convenience combinator for endpoint handlers: `principal = require(principal, "decide")`."""
    authorize(principal, action)
    return principal


def known_roles() -> Iterable[Role]:
    return _ROLE_PERMISSIONS.keys()
