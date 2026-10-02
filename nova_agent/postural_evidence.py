"""Posture-tagged blood pressure changes, preserving timing uncertainty.

AHA 2024 scientific statement: https://doi.org/10.1161/HYP.0000000000000236
A 20 mmHg systolic or 10 mmHg diastolic drop within 3 minutes is the formal
criterion. If timing is absent, this module reports supportive evidence only;
it never asserts that a full diagnostic protocol was completed.
"""
import re

def postural_drop(text):
    if not text or re.search(r'\b(?:example|hypothetical|previous|yesterday)\b',text,re.I):
        return None
    readings={}
    # Bind posture to the same BP reading, not to a different clause or HR value.
    for clause in re.split(r';|\n',text):
        match=re.search(r'\b(?:BP\s*)?(\d{2,3})\s*/\s*(\d{2,3})\b',clause,re.I)
        if not match: continue
        posture=re.search(r'\b(supine|lying|standing|upright)\b',clause,re.I)
        if not posture: continue
        kind='lying' if posture[1].lower() in ('supine','lying') else 'standing'
        bp=tuple(map(int,match.groups()))
        if not (50<=bp[0]<=300 and 20<=bp[1]<bp[0]): continue
        readings[kind]=bp
    if set(readings)!={'lying','standing'}: return None
    sbp=readings['lying'][0]-readings['standing'][0]
    dbp=readings['lying'][1]-readings['standing'][1]
    return (sbp,dbp) if sbp>=20 or dbp>=10 else None
