"""Evaluation-only identity from unchanged catalog terms, independent of runtime resolver.

This prevents a runtime normalization fix from changing the scoring rule between
BEFORE and AFTER. Exact canonical duplicates share identity; different canonical
names sharing an alias remain ambiguous. No expected-case label table is used.
"""
from functools import lru_cache
import re


def clean(text):
    return re.sub(r'[^\w\s]','',str(text).replace('_',' ').casefold()).strip()


@lru_cache(maxsize=1)
def vocabulary():
    from nova_agent.ontology.registry import get_default_catalog
    terms={}
    for c in get_default_catalog().all_concepts():
        identity=clean(c.canonical_name)
        for term in [c.concept_id,c.kb_id or '',c.canonical_name,*c.aliases]:
            if term:terms.setdefault(clean(term),set()).add(identity)
    return terms


def identities(text):
    # Prefer an exact full catalog term. Do not split the nested parentheses in
    # a canonical name such as "Musculoskeletal Chest Pain (Costochondritis)".
    table=vocabulary()
    exact=table.get(clean(text),set())
    if exact:
        return exact if len(exact)==1 else set()
    # Split only top-level display groups, retaining nested canonical names.
    # All identified parts still must agree: asthma (pneumonia) is not asthma.
    variants=[]; depth=0; start=0
    for i,char in enumerate(text):
        if char=='(':
            if depth==0:
                variants.append(text[start:i].strip());start=i+1
            depth+=1
        elif char==')':
            depth-=1
            if depth<0:return set()
            if depth==0:
                variants.append(text[start:i].strip());start=i+1
    if depth:return set()
    variants.append(text[start:].strip())
    known=set().union(*(table.get(clean(v),set()) for v in variants))
    return known if len(known)==1 else set()


def same_label(a,b):
    if clean(a)==clean(b) and clean(a):return True
    left,right=identities(a),identities(b)
    return bool(left and right and left==right)
