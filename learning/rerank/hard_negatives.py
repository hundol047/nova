"""Generic hard-negative mimic pairs for reranker training (PHASE 1 PART G1).

These are well-known clinical MIMIC relationships — pairs that look similar but must be
distinguished. They are used as hard negatives during reranker training (a correct label paired
with a plausible confuser) so the model learns discriminating features, NOT to memorize any specific
evaluation/blind case. Deliberately GENERIC textbook pairs; NEVER keyed to a blind vignette.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# (condition, plausible mimic) — bidirectional in practice.
MIMIC_PAIRS: List[Tuple[str, str]] = [
    ("acute coronary syndrome", "myocarditis"),
    ("acute coronary syndrome", "pericarditis"),
    ("acute coronary syndrome", "musculoskeletal chest pain"),
    ("pulmonary embolism", "panic attack"),
    ("pulmonary embolism", "pneumonia"),
    ("aortic dissection", "acute coronary syndrome"),
    ("ischemic stroke", "migraine"),
    ("ischemic stroke", "hypoglycemia"),
    ("subarachnoid hemorrhage", "tension-type headache"),
    ("bacterial meningitis", "migraine"),
    ("diabetic ketoacidosis", "hyperosmolar hyperglycemic state"),
    ("appendicitis", "gastroenteritis"),
    ("appendicitis", "mesenteric adenitis"),
    ("pyelonephritis", "nephrolithiasis"),
    ("ectopic pregnancy", "ovarian torsion"),
    ("sepsis", "viral upper respiratory infection"),
    ("necrotizing fasciitis", "cellulitis"),
    ("cholecystitis", "biliary colic"),
    ("cholangitis", "cholecystitis"),
    ("testicular torsion", "epididymitis"),
    ("anaphylaxis", "vasovagal syncope"),
    ("giant cell arteritis", "tension-type headache"),
    ("guillain-barre syndrome", "peripheral neuropathy"),
    ("stevens-johnson syndrome", "erythema multiforme"),
    ("carbon monoxide poisoning", "viral illness"),
    ("thyroid storm", "sepsis"),
    ("adrenal crisis", "sepsis"),
    ("tension pneumothorax", "asthma exacerbation"),
]


def hard_negatives_for(condition: str) -> List[str]:
    """Return the generic mimics for a condition (case-insensitive substring match on either side)."""
    c = condition.strip().lower()
    out: List[str] = []
    for a, b in MIMIC_PAIRS:
        if c in a or a in c:
            out.append(b)
        elif c in b or b in c:
            out.append(a)
    # de-dup preserving order
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq
