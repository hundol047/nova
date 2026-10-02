#!/usr/bin/env python3
"""Import selected active, disorder-level Orphanet definitions under CC BY 4.0.

Use ORPHAnomenclature_en_2026.xml from the official July 2026 nomenclature pack.
No inference rules, severity thresholds, or clinical validation are derived here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, parse_qs
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.import_medline_candidates import PlainText

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'nova_agent/knowledge/orphanet_candidates'
SOURCE='https://www.orphacode.org/data/packs/Orphanet_Nomenclature_Pack_EN.zip'
LICENSE='https://creativecommons.org/licenses/by/4.0/'
ATTRIBUTION='Orphadata / Orphanet © INSERM. July 2026. CC BY 4.0. Selected English definitions; HTML removed and whitespace normalized.'
TYPES={'Disease','Clinical syndrome','Malformation syndrome'}


def read_conditions(path):
    raw=Path(path).read_bytes()
    if len(raw)>64*1024*1024 or b'<!ENTITY' in raw.upper():
        raise ValueError('Oversized XML or entity declaration rejected')
    root=ET.fromstring(raw)
    if root.tag!='JDBOR' or root.find('DisorderList') is None:
        raise ValueError('Expected Orphanet nomenclature XML')
    entries=[]
    for d in root.findall('DisorderList/Disorder'):
        if d.findtext('Totalstatus')!='Active' or d.findtext('ClassificationLevel/Name')!='Disorder' or d.findtext('DisorderType/Name') not in TYPES:
            continue
        name=d.findtext('Name','').strip();code=d.findtext('OrphaCode','')
        if not re.fullmatch(r'[1-9][0-9]*',code) or not name or d.find('Name').get('lang')!='en':
            raise ValueError('Invalid English disorder identity')
        original=d.findtext('ExpertLink','');url=urlsplit(original)
        if url.scheme not in {'http','https'} or url.netloc!='www.orpha.net' or url.path!='/consor/cgi-bin/OC_Exp.php' or parse_qs(url.query,keep_blank_values=True)!={'lng':['en'],'Expert':[code]} or url.fragment:
            raise ValueError('Unexpected official disorder URL')
        descriptions=[]
        for section in d.findall('SummaryInformationList/SummaryInformation/TextSectionList/TextSection'):
            if section.get('lang')=='en' and section.findtext('TextSectionType/Name')=='Definition':
                plain=PlainText();plain.feed(section.findtext('Contents',''));descriptions.append(plain.text())
        summary='\n'.join(p for p in descriptions if p)
        if not summary:continue
        entries.append({'id':'orphanet_'+code,'name':name,
            'aliases':list(dict.fromkeys(a.text.strip() for a in d.findall('SynonymList/Synonym') if a.get('lang')=='en' and a.text and a.text.strip())),
            'source_topic_id':code,'source_url':'https://www.orpha.net'+url.path+'?'+url.query,
            'source_original_url':original,'summary':summary,'groups':['Rare disorders'],
            'source_status':'Active','source_classification':'Disorder',
            'source_disorder_type':d.findtext('DisorderType/Name'),
            'attribution':ATTRIBUTION,'license_url':LICENSE,
            'validation_status':'reference_only','autonomous_diagnosis_enabled':False,
            'clinical_review_verified':False})
    return raw,root.get('ExtractionDate'),entries


def build(path,destination=DEST):
    raw,date,available=read_conditions(path)
    selected=(destination/'selection.txt').read_text().splitlines()
    if len(selected)!=2177 or len(set(selected))!=2177:raise ValueError('Expected 2177 unique selected disorders')
    by_name={e['name']:e for e in available};entries=[by_name[n] for n in selected]
    payload=(json.dumps(entries,ensure_ascii=False,indent=2)+'\n').encode()
    sha=lambda b:hashlib.sha256(b).hexdigest()
    manifest={'source_url':SOURCE,'source_release':'July 2026','source_generated_at':date,
        'source_sha256':sha(raw),'source_sha256_scope':'uncompressed_ORPHAnomenclature_en_2026.xml',
        'catalog_sha256':sha(payload),'selection_sha256':sha((destination/'selection.txt').read_bytes()),
        'n_reference_candidates':len(entries),'source_kind':'orphanet_disorder',
        'attribution':ATTRIBUTION,'license_url':LICENSE,'reuse_terms':'https://www.orphacode.org/pack-nomenclature/',
        'selection_method':'Frozen engineering selection in stable SHA256 name order, excluding normalized name/alias collisions; not clinical priority',
        'content_scope':'Active English disorder-level diseases/clinical syndromes/malformation syndromes with definitions only; no groups, subtypes, inactive/historical entities',
        'clinical_validation':False,'diagnostic_accuracy_measured':False}
    (destination/'catalog.json').write_bytes(payload)
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--xml',required=True)
    args=parser.parse_args();print(json.dumps(build(args.xml),indent=2))
