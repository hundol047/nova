"""Disease-side encoder: turns a ClinicalConcept-like object into a retrieval embedding.

Uses the disease's own describable attributes — canonical name tokens, synonyms/aliases, category/
specialty, presentation tags, and external-code system tags — as the feature bag. No fabricated
clinical detail is introduced; the encoder only reflects what the concept already carries, so a
Tier-3 ontology concept (name + code + category only) simply produces a sparser embedding than a
Tier-1 deep profile — which is honest.

Dependency-free (feature hashing). A torch encoder may replace this later; the interface (a dim-
vector per disease) is unchanged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence

from learning.retrieval.embedding import EMBED_DIM, EMBEDDING_VERSION, hash_embed

_TOKEN_RE = re.compile(r"[a-z0-9\uac00-\ud7a3]+")  # latin/digits + Hangul syllables


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


@dataclass(frozen=True)
class DiseaseFeatures:
    """The describable attributes a disease concept exposes for encoding (mirrors ClinicalConcept)."""

    concept_id: str
    canonical_name: str
    aliases: Sequence[str] = ()
    category: str = ""
    tier: str = ""
    chief_complaint_tags: Sequence[str] = ()
    typical_features: Sequence[str] = ()
    code_systems: Sequence[str] = ()


def _feature_bag(d: DiseaseFeatures) -> List[str]:
    bag: List[str] = []
    # name + alias tokens (the strongest lexical signal)
    for term in [d.canonical_name, *d.aliases]:
        bag.extend(f"name:{t}" for t in _tokens(term))
    # specialty/category
    if d.category:
        bag.append(f"cat:{d.category.lower()}")
    # presentation tags + typical features (present only for curated tiers)
    for tag in d.chief_complaint_tags:
        bag.append(f"cc:{str(tag).lower()}")
    for feat in d.typical_features:
        bag.extend(f"feat:{t}" for t in _tokens(str(feat)))
    # code-system tags (which terminologies this concept is anchored in)
    for sysid in d.code_systems:
        bag.append(f"sys:{str(sysid).lower()}")
    return bag


class DiseaseEncoder:
    version = EMBEDDING_VERSION

    def __init__(self, dim: int = EMBED_DIM) -> None:
        self.dim = dim

    def encode(self, d: DiseaseFeatures) -> List[float]:
        # Name/alias tokens weighted higher than category/system tags (lexical match dominates recall).
        bag = _feature_bag(d)
        weights = {}
        for f in bag:
            if f.startswith("name:"):
                weights[f] = 2.0
            elif f.startswith("feat:") or f.startswith("cc:"):
                weights[f] = 1.2
            else:
                weights[f] = 0.8
        return hash_embed(bag, weights=weights, dim=self.dim)


def _concept_to_features(concept) -> DiseaseFeatures:
    """Adapt a nova_agent.ontology ClinicalConcept into DiseaseFeatures (duck-typed; no import to
    keep learning/ independent of nova_agent)."""
    code_systems = []
    for c in getattr(concept, "external_codes", ()) or ():
        sysid = getattr(c, "system", None)
        if sysid:
            code_systems.append(sysid)
    tier = getattr(concept, "tier", None)
    tier_val = getattr(tier, "value", tier) or ""
    return DiseaseFeatures(
        concept_id=getattr(concept, "concept_id", ""),
        canonical_name=getattr(concept, "canonical_name", ""),
        aliases=tuple(getattr(concept, "aliases", ()) or ()),
        category=getattr(concept, "category", "") or "",
        tier=tier_val,
        chief_complaint_tags=tuple(getattr(concept, "chief_complaint_tags", ()) or ()),
        typical_features=tuple(getattr(concept, "typical_features", ()) or ()),
        code_systems=tuple(code_systems),
    )


def encode_disease(concept, dim: int = EMBED_DIM) -> List[float]:
    """Convenience: encode a ClinicalConcept-like object directly."""
    return DiseaseEncoder(dim=dim).encode(_concept_to_features(concept))
