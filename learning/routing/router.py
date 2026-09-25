"""Multi-specialty router (dependency-free, deterministic).

Scores each specialty from the patient's presentation using specialty keyword lexicons + the
categories of the retrieved candidates, then activates ALL specialties above a band threshold (not
just the top one). Output is a qualitative BAND (HIGH/MEDIUM/LOW) + a raw score — never a fabricated
probability (no calibration => no percent, per the whole system's honesty rule).

Governance:
  - Multiple specialties can be active simultaneously.
  - If the top specialty's confidence is LOW (nothing routes clearly), `global_fallback` is True and
    the caller must NOT restrict retrieval to any specialty — do broad global retrieval instead.
  - The router NEVER removes candidates. A method `boost()` only raises specialty-relevant scores;
    it never drops or zeroes anything. Critical candidates are protected by safety-recall regardless.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class RouteBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# Specialty keyword lexicons (presentation tokens that raise a specialty's activation). Deliberately
# broad/overlapping — the point is RECALL of relevant specialties, not exclusive routing.
SPECIALTY_KEYWORDS: Dict[str, List[str]] = {
    "cardiovascular": ["chest", "angina", "palpitation", "syncope", "edema", "dyspnea", "orthopnea",
                        "claudication", "hypertension", "murmur", "bradycardia", "tachycardia"],
    "pulmonary": ["cough", "dyspnea", "wheeze", "hemoptysis", "sputum", "hypoxia", "pleuritic",
                  "breathless", "stridor", "respiratory"],
    "neuro": ["headache", "weakness", "numbness", "seizure", "aphasia", "vertigo", "dizziness",
              "confusion", "ataxia", "tremor", "paralysis", "vision", "diplopia"],
    "abdominal_gi": ["abdominal", "abdomen", "nausea", "vomiting", "diarrhea", "constipation",
                     "melena", "hematemesis", "jaundice", "epigastric", "rlq", "ruq"],
    "infectious": ["fever", "chills", "rigors", "sepsis", "infection", "purulent", "abscess",
                   "cellulitis", "meningismus", "rash"],
    "genitourinary": ["dysuria", "hematuria", "urinary", "flank", "testicular", "vaginal",
                      "pelvic", "urine", "frequency", "retention"],
    "endocrine_metabolic": ["thirst", "polyuria", "glucose", "diabetic", "thyroid", "adrenal",
                            "hypoglycemia", "electrolyte", "weight"],
    "hematology": ["anemia", "bleeding", "bruising", "petechiae", "pallor", "thrombosis", "clot"],
    "oncology": ["mass", "lump", "weight loss", "night sweats", "lymphadenopathy", "cancer", "tumor"],
    "rheumatology": ["joint", "arthralgia", "arthritis", "rash", "stiffness", "myalgia", "swelling"],
    "dermatology": ["rash", "lesion", "blister", "pruritus", "ulcer", "skin", "purpura"],
    "psychiatric": ["depression", "anxiety", "suicidal", "hallucination", "psychosis", "mania",
                    "insomnia", "withdrawal"],
    "toxicology": ["overdose", "ingestion", "poisoning", "toxic", "envenomation"],
    "obstetric": ["pregnant", "pregnancy", "gestation", "postpartum", "contraction", "vaginal bleeding"],
    "gynecology": ["menstrual", "menorrhagia", "amenorrhea", "ovarian", "pelvic", "vaginal"],
    "pediatric": ["infant", "child", "neonate", "toddler", "pediatric"],
    "ent": ["ear", "throat", "hoarse", "sinus", "epistaxis", "hearing", "tonsil"],
    "ophthalmology": ["eye", "vision", "ocular", "diplopia", "photophobia", "red eye"],
    "orthopedics": ["fracture", "joint", "bone", "sprain", "dislocation", "back pain"],
    "vascular": ["claudication", "ischemia", "pulseless", "aneurysm", "varicose", "dvt"],
    "trauma": ["trauma", "injury", "fall", "collision", "blunt", "penetrating", "burn"],
    "environmental": ["heat", "cold", "hypothermia", "altitude", "drowning", "electrical"],
}

# Bands from raw activation score.
HIGH_THRESHOLD = 2.0
MEDIUM_THRESHOLD = 1.0
LOW_CONFIDENCE_MAX = 1.0  # if the TOP specialty is at/below this, trigger global fallback


@dataclass(frozen=True)
class SpecialtyActivation:
    specialty: str
    score: float
    band: RouteBand


@dataclass
class RouteResult:
    activations: List[SpecialtyActivation]
    global_fallback: bool
    notes: List[str] = field(default_factory=list)

    def active_specialties(self, min_band: RouteBand = RouteBand.MEDIUM) -> List[str]:
        order = {RouteBand.HIGH: 3, RouteBand.MEDIUM: 2, RouteBand.LOW: 1}
        return [a.specialty for a in self.activations if order[a.band] >= order[min_band]]

    def as_dict(self) -> dict:
        return {
            "global_fallback": self.global_fallback,
            "activations": [{"specialty": a.specialty, "score": round(a.score, 3), "band": a.band.value}
                            for a in self.activations],
            "notes": list(self.notes),
        }


class SpecialtyRouter:
    def __init__(self, keywords: Optional[Dict[str, List[str]]] = None) -> None:
        self._kw = keywords or SPECIALTY_KEYWORDS

    def _band(self, score: float) -> RouteBand:
        if score >= HIGH_THRESHOLD:
            return RouteBand.HIGH
        if score >= MEDIUM_THRESHOLD:
            return RouteBand.MEDIUM
        return RouteBand.LOW

    def route(self, text: str, candidate_categories: Optional[Sequence[str]] = None) -> RouteResult:
        """Score every specialty from the presentation text (keyword hits) + the categories of the
        retrieved candidates (a soft prior). Activate ALL specialties scoring MEDIUM+."""
        toks = set(_TOKEN_RE.findall((text or "").lower()))
        joined = " " + (text or "").lower() + " "
        scores: Dict[str, float] = {}
        for spec, kws in self._kw.items():
            s = 0.0
            for kw in kws:
                if " " in kw:
                    if kw in joined:
                        s += 1.0
                elif kw in toks:
                    s += 1.0
            scores[spec] = s
        # candidate-category prior (small): categories present in the retrieved pool nudge their
        # specialty up, so routing reflects what retrieval actually surfaced.
        for cat in (candidate_categories or []):
            if cat in scores:
                scores[cat] += 0.5

        activations = [SpecialtyActivation(spec, sc, self._band(sc))
                       for spec, sc in scores.items() if sc >= MEDIUM_THRESHOLD]
        activations.sort(key=lambda a: -a.score)

        top_score = activations[0].score if activations else 0.0
        global_fallback = top_score <= LOW_CONFIDENCE_MAX
        notes: List[str] = []
        if global_fallback:
            notes.append("Router confidence LOW; falling back to broad GLOBAL retrieval "
                         "(no specialty restriction).")
        if len(activations) > 1:
            notes.append(f"{len(activations)} specialties active simultaneously "
                         f"({', '.join(a.specialty for a in activations[:4])}).")
        return RouteResult(activations=activations, global_fallback=global_fallback, notes=notes)

    def boost(self, items: Sequence, route: RouteResult, weight: float = 0.15):
        """Raise the score of candidates whose category is an ACTIVE specialty. NEVER drops or
        zeroes any candidate — routing is additive-only. Mutates+returns the items list.

        `items` are objects with `.category` and `.score` (e.g. RetrievedItem). A router miss simply
        means no boost — the candidate keeps its original retrieval score and stays in the pool."""
        if route.global_fallback:
            return items  # no specialty restriction/boost under global fallback
        active = set(route.active_specialties(min_band=RouteBand.MEDIUM))
        band_by_spec = {a.specialty: a.band for a in route.activations}
        for it in items:
            cat = getattr(it, "category", "") or ""
            if cat in active:
                mult = 1.0 if band_by_spec.get(cat) == RouteBand.HIGH else 0.5
                it.score = float(getattr(it, "score", 0.0)) + weight * mult
        return items
