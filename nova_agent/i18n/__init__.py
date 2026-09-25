"""Locale display layer (spec: internal canonical clinical IDs -- diagnosis_id, concept tags,
lab.* keys -- must NEVER vary per locale; only rendered DISPLAY TEXT does).

`nova_agent/knowledge/diseases/*.json`'s `id` field is the one and only canonical diagnosis
identifier used throughout reasoning (candidate generation, scoring, StopPolicy, safety, audit).
This module is the ONE place that maps that stable id to a locale-appropriate display string --
never the reverse, and reasoning code never imports this module (it only ever handles ids).
"""

from nova_agent.i18n.diagnosis_display import translate_diagnosis

__all__ = ["translate_diagnosis"]
