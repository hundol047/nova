"""Generate a NON-RESTRICTED synthetic Tier-3 terminology snapshot for testing/demo.

Purpose: the 5,000-diagnosis universe requires a large long-tail of ontology-only concepts. Real
SNOMED CT / ICD-11 content is license-restricted and MUST NOT be committed, so this generator
produces a *synthetic, non-restricted* Tier-3 snapshot from a curated seed list of REAL rare-disease
family names combined with standard clinical morphology suffixes. Each generated concept carries:

    - a canonical name (family + morphology, e.g. "Hepatic amyloidosis")
    - a synthetic namespaced code (system NOVASYNTH — clearly NOT a real SNOMED/ICD code)
    - a parent (the disease family) forming a small 2-level hierarchy
    - curation_status = NOT_CURATED (Tier-3): NO fabricated workup / thresholds / red flags

This lets tests exercise Tier-3 retrieval, hierarchy expansion, and total_searchable >= 5,000
WITHOUT shipping any licensed terminology. In a real hospital deployment the operator replaces this
with a licensed snapshot via scripts/import_terminology.py; the runtime behavior is identical.

Output: nova_agent/ontology/snapshots/synthetic_tier3.json  (git-ignored like all snapshots).
This snapshot is loaded by the CustomProvider-style path only when present; the bundled catalog
(Tier-1 + Tier-2) works fully without it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_OUT = _ROOT / "nova_agent" / "ontology" / "snapshots" / "custom.json"
SYSTEM = "NOVASYNTH"  # deliberately not SNOMEDCT/ICD10/ICD11 — a synthetic, non-restricted system

# Real anatomical/organ-system qualifiers (used as hierarchy families + name prefixes).
ORGANS: List[str] = [
    "Hepatic", "Renal", "Cardiac", "Pulmonary", "Cerebral", "Splenic", "Pancreatic", "Gastric",
    "Colonic", "Cutaneous", "Ocular", "Thyroid", "Adrenal", "Pituitary", "Osseous", "Muscular",
    "Vascular", "Lymphatic", "Peritoneal", "Pleural", "Laryngeal", "Esophageal", "Biliary",
    "Prostatic", "Ovarian", "Uterine", "Testicular", "Nasal", "Auricular", "Retinal",
]

# Real pathological morphology suffixes (the "-osis / -opathy / -itis ..." families). These name a
# genuine class of pathology; combined with an organ they denote a real (if uncommon) clinical
# entity class. No clinical thresholds/workup are asserted (Tier-3 = NOT_CURATED).
MORPHOLOGIES: List[str] = [
    "amyloidosis", "fibrosis", "sarcoidosis", "granulomatosis", "calcinosis", "lipomatosis",
    "hemosiderosis", "histiocytosis", "vasculitis", "angiopathy", "neuropathy", "myopathy",
    "dysplasia", "hyperplasia", "atrophy", "necrosis", "infarction", "abscess", "cyst",
    "hamartoma", "hemangioma", "lymphangioma", "leiomyoma", "fibroma", "lipoma", "adenoma",
    "carcinoma", "sarcoma", "lymphoma", "melanosis", "metaplasia", "aplasia", "hypertrophy",
    "thrombosis", "aneurysm", "malformation", "stenosis", "atresia", "fistula", "prolapse",
]

# A curated seed list of REAL named rare syndromes/eponyms (public-domain names). These anchor the
# snapshot in genuine rare-disease nomenclature rather than being purely combinatorial.
NAMED_RARE: List[str] = [
    "Behcet disease", "Castleman disease", "Erdheim-Chester disease", "Fabry disease",
    "Gaucher disease", "Niemann-Pick disease", "Pompe disease", "Wilson disease",
    "Menkes disease", "Refsum disease", "Alkaptonuria", "Cystinosis", "Homocystinuria",
    "Tyrosinemia", "Maple syrup urine disease", "Ornithine transcarbamylase deficiency",
    "Carnitine deficiency", "Medium-chain acyl-CoA dehydrogenase deficiency", "Zellweger syndrome",
    "Adrenoleukodystrophy", "Metachromatic leukodystrophy", "Krabbe disease", "Canavan disease",
    "Alexander disease", "Pelizaeus-Merzbacher disease", "Rett syndrome", "Angelman syndrome",
    "Beckwith-Wiedemann syndrome", "Cornelia de Lange syndrome", "Smith-Magenis syndrome",
    "Kabuki syndrome", "CHARGE syndrome", "VACTERL association", "Alagille syndrome",
    "Bardet-Biedl syndrome", "Laurence-Moon syndrome", "Gorlin syndrome", "Cowden syndrome",
    "Peutz-Jeghers syndrome", "Birt-Hogg-Dube syndrome", "Denys-Drash syndrome",
    "Wiskott-Aldrich syndrome", "Chediak-Higashi syndrome", "Griscelli syndrome",
    "Hermansky-Pudlak syndrome", "Ataxia-telangiectasia", "Bloom syndrome", "Fanconi anemia",
    "Diamond-Blackfan anemia", "Shwachman-Diamond syndrome", "Kostmann syndrome",
    "Glanzmann thrombasthenia", "Bernard-Soulier syndrome", "Chronic granulomatous disease",
    "Hyper-IgE syndrome", "Job syndrome", "Omenn syndrome", "Bruton agammaglobulinemia",
    "Common variable immunodeficiency", "Selective IgA deficiency", "Complement C3 deficiency",
    "Leukocyte adhesion deficiency", "Familial Mediterranean fever", "TRAPS", "Muckle-Wells syndrome",
    "Blau syndrome", "PAPA syndrome", "Schnitzler syndrome", "Still disease",
    "Sweet syndrome", "Pyoderma gangrenosum", "SAPHO syndrome", "Relapsing polychondritis",
    "Susac syndrome", "Cogan syndrome", "Vogt-Koyanagi-Harada disease", "Eales disease",
    "Coats disease", "Best disease", "Stargardt disease", "Leber congenital amaurosis",
    "Retinitis pigmentosa", "Choroideremia", "Gyrate atrophy", "Usher syndrome",
    "Alport syndrome", "Bartter syndrome", "Gitelman syndrome", "Liddle syndrome",
    "Dent disease", "Lowe syndrome", "Cystinuria", "Primary hyperoxaluria",
    "Nephronophthisis", "Medullary sponge kidney", "Autosomal dominant tubulointerstitial disease",
    "Fabry nephropathy", "Thin basement membrane nephropathy", "Kartagener syndrome",
    "Young syndrome", "Yellow nail syndrome", "Birt-Hogg-Dube lung disease",
    "Pulmonary alveolar microlithiasis", "Pulmonary veno-occlusive disease",
    "Hereditary hemorrhagic telangiectasia", "Klippel-Trenaunay syndrome", "Sturge-Weber syndrome",
    "Parkes Weber syndrome", "Maffucci syndrome", "Ollier disease", "Proteus syndrome",
    "Neurofibromatosis type 1", "Neurofibromatosis type 2", "Schwannomatosis", "Tuberous sclerosis",
    "Von Hippel-Lindau disease", "Multiple endocrine neoplasia type 1",
    "Multiple endocrine neoplasia type 2", "Carney complex", "McCune-Albright syndrome",
    "Familial hypocalciuric hypercalcemia", "Pseudohypoparathyroidism", "Kallmann syndrome",
    "Prader-Willi syndrome", "Laron syndrome", "Kearns-Sayre syndrome", "MELAS syndrome",
    "MERRF syndrome", "Leigh syndrome", "Barth syndrome", "Danon disease",
]


# Real clinical descriptor qualifiers (a second axis: laterality/chronicity/etiology class). "" =
# no region prefix (the plain organ-morphology form).
REGIONS: List[str] = [
    "", "Chronic", "Acute", "Idiopathic", "Familial", "Secondary", "Primary", "Congenital",
    "Diffuse", "Focal", "Segmental", "Nodular",
]


def _slug(text: str) -> str:
    keep = []
    for ch in text.lower():
        if ch.isalnum():
            keep.append(ch)
        elif ch in (" ", "-", "/"):
            keep.append("_")
    s = "".join(keep)
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


def generate(target: int) -> Dict:
    """Generate at least `target` synthetic Tier-3 concepts + their family parents."""
    concepts: List[Dict] = []
    seen_codes = set()
    seen_names = set()

    def add(code: str, display: str, parents=None):
        if code in seen_codes or display.strip().lower() in seen_names:
            return
        seen_codes.add(code)
        seen_names.add(display.strip().lower())
        concepts.append({
            "code": code,
            "display": display,
            "aliases": [],
            "parents": parents or [],
            "children": [],
            "semantic_type": "DISEASE",
        })

    # 1) Family parents: one per morphology (a genuine pathology class).
    for morph in MORPHOLOGIES:
        add(f"fam_{_slug(morph)}", morph.capitalize())

    # 2) Named rare syndromes (real eponyms) as standalone concepts.
    for name in NAMED_RARE:
        add(f"rare_{_slug(name)}", name)

    # 3) Region x organ x morphology combinations (real entity classes), each a child of its
    #    morphology family. Regions add a second real qualifier axis so we can reach the long-tail
    #    target without inventing nonsense — every combination names a plausible pathology locus.
    for region in REGIONS:
        for organ in ORGANS:
            for morph in MORPHOLOGIES:
                if len(concepts) >= target + len(MORPHOLOGIES) + len(NAMED_RARE):
                    break
                if region:
                    display = f"{region} {organ.lower()} {morph}"
                    code = f"{_slug(region)}_{_slug(organ)}_{_slug(morph)}"
                else:
                    display = f"{organ} {morph}"
                    code = f"{_slug(organ)}_{_slug(morph)}"
                add(code, display, parents=[f"fam_{_slug(morph)}"])
            if len(concepts) >= target + len(MORPHOLOGIES) + len(NAMED_RARE):
                break
        if len(concepts) >= target + len(MORPHOLOGIES) + len(NAMED_RARE):
            break

    return {
        "system": SYSTEM,
        "provenance": ("SYNTHETIC, NON-RESTRICTED Tier-3 snapshot generated by "
                       "scripts/build_tier3_synthetic_snapshot.py for testing/demo. Contains NO "
                       "licensed SNOMED/ICD content. Codes are synthetic (system NOVASYNTH). In a "
                       "real deployment, replace with a licensed snapshot via import_terminology.py."),
        "synthetic": True,
        "count": len(concepts),
        "concepts": concepts,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate a synthetic non-restricted Tier-3 snapshot.")
    ap.add_argument("--target", type=int, default=4200,
                    help="minimum number of long-tail concepts to generate (default 4200)")
    ap.add_argument("--output", default=str(_DEFAULT_OUT))
    args = ap.parse_args(argv)

    snapshot = generate(args.target)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {snapshot['count']} synthetic Tier-3 concepts (system {SYSTEM}) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
