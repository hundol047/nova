"""Post-W: anatomical sex compatibility of a candidate diagnosis.

A diagnosis that needs an organ the patient's recorded sex does not have (an ectopic pregnancy or an ovarian torsion
in a male; a testicular torsion or prostatitis in a female) is not a possibility to rank, question or keep open as an
unresolved danger. This is an anatomical precondition, not a prevalence prior: no candidate gains score from age or
sex, and nothing is excluded when sex is not recorded. The table is explicit (no pattern on ids) and limited to
organ-bound conditions; breast conditions, which occur in both sexes, are not listed. Agent-authored, not
clinician-reviewed.
"""
from __future__ import annotations

from typing import Optional

# Conditions of the uterus, ovaries, cervix, vagina/vulva, or of pregnancy and the puerperium.
FEMALE_ONLY = frozenset({
    "ectopic_pregnancy", "ovarian_torsion", "ruptured_ovarian_cyst", "gu_ovarian_cyst", "gu_cervicitis",
    "bacterial_vaginosis", "cervical_dysplasia", "dysfunctional_uterine_bleeding", "endometrial_cancer", "endometriosis",
    "polycystic_ovary_syndrome", "tubo_ovarian_abscess", "uterine_fibroids", "uterine_prolapse",
    "vulvovaginal_candidiasis", "eclampsia", "preeclampsia", "placenta_previa", "placental_abruption",
    "postpartum_hemorrhage", "og2_acute_fatty_liver_pregnancy", "og2_ectopic_pregnancy_og2", "og2_endometritis_postpartum",
    "og2_molar_pregnancy", "og2_ovarian_hyperstimulation", "og2_premature_ovarian_insufficiency", "og2_retained_placenta",
    "og2_uterine_rupture", "cervical_cancer", "neo_cervical_intraepithelial", "neo_vaginal_ca", "ovarian_cancer",
    "psy_postpartum_depression", "pelvic_inflammatory_disease",
})
# Conditions of the testes, epididymis, prostate or penis.
MALE_ONLY = frozenset({
    "testicular_torsion", "epididymitis", "gu_epididymo_orchitis", "prostatitis", "prostate_cancer", "neo_penile_ca",
    "neo_testicular_ca",
})


def _bare_id(diagnosis_id: str) -> str:
    return diagnosis_id.rsplit(":", 1)[-1]


def _sex(value) -> Optional[str]:
    v = str(value or "").strip().lower()
    return {"male": "male", "m": "male", "man": "male", "female": "female", "f": "female", "woman": "female",
            "남": "male", "남성": "male", "여": "female", "여성": "female"}.get(v)


def incompatible(diagnosis_id: str, sex) -> bool:
    """True only when sex is recorded and the diagnosis needs an organ of the other sex."""
    s = _sex(sex)
    if s is None:
        return False
    bare = _bare_id(diagnosis_id)
    return (s == "male" and bare in FEMALE_ONLY) or (s == "female" and bare in MALE_ONLY)
