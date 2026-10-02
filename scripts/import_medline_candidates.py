#!/usr/bin/env python3
"""Import explicitly selected MedlinePlus HEALTH TOPIC summaries, not encyclopedia content.

Download the XML linked by https://medlineplus.gov/xml.html first, then run with
--xml PATH --source-url URL. No network calls or external XML entity processing here.
The public-domain summary reuse terms require the preserved NLM attribution.
Nothing imported is promoted to autonomous diagnostic eligibility.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'nova_agent/knowledge/reference_candidates'
ATTRIBUTION='Source: MedlinePlus, National Library of Medicine.'

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in {'p','li','h2','h3','br'}:self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in {'p','li','h2','h3'}:self.parts.append('\n')
    def handle_data(self,data):self.parts.append(data)
    def text(self):return '\n'.join(' '.join(line.split()) for line in ''.join(self.parts).splitlines() if line.strip())

def sha(data):return hashlib.sha256(data).hexdigest()

def build(xml_path, source_url, destination=DEST):
    url=urlsplit(source_url)
    if url.scheme!='https' or url.netloc!='medlineplus.gov' or not url.path.startswith('/xml/'):
        raise ValueError('Source must identify the official MedlinePlus XML download')
    raw=Path(xml_path).read_bytes()
    if len(raw)>64*1024*1024 or b'<!ENTITY' in raw.upper():
        raise ValueError('Oversized XML or entity declaration rejected')
    root=ET.fromstring(raw)
    if root.tag!='health-topics':raise ValueError('Expected health-topic XML, not third-party encyclopedia data')
    selected=(destination/'selection.txt').read_text().splitlines()
    if len(selected)!=204 or len(set(selected))!=204:raise ValueError('Expected 204 distinct selected titles')
    topics={t.get('title'):t for t in root.findall('health-topic') if t.get('language')=='English'}
    entries=[]
    for title in selected:
        topic=topics[title]
        source=topic.get('url','')
        parsed=urlsplit(source)
        if parsed.scheme!='https' or parsed.netloc!='medlineplus.gov' or not re.fullmatch(r'/[a-z0-9]+\.html',parsed.path) or parsed.query or parsed.fragment:
            raise ValueError('Only MedlinePlus health-topic URLs may be imported')
        html=topic.findtext('full-summary','')
        text=PlainText();text.feed(html);summary=text.text()
        if not summary:raise ValueError('Empty source summary: '+title)
        aliases=list(dict.fromkeys(a.text.strip() for a in topic.findall('also-called') if a.text and a.text.strip()))
        entries.append({'id':'medlineplus_'+topic.attrib['id'],'name':title,'aliases':aliases,
            'source_topic_id':topic.attrib['id'],'source_url':source,'summary':summary,
            'groups':[g.text for g in topic.findall('group') if g.text],
            'attribution':ATTRIBUTION,'validation_status':'reference_only',
            'autonomous_diagnosis_enabled':False,'clinical_review_verified':False})
    payload=(json.dumps(entries,ensure_ascii=False,indent=2)+'\n').encode()
    (destination/'catalog.json').write_bytes(payload)
    manifest={'source_url':source_url,'source_generated_at':root.get('date-generated'),
              'source_sha256':sha(raw),'source_sha256_scope':'uncompressed_xml_bytes','catalog_sha256':sha(payload),'selection_sha256':sha((destination/'selection.txt').read_bytes()),
              'n_reference_candidates':len(entries),'attribution':ATTRIBUTION,
              'reuse_terms':'https://medlineplus.gov/about/using/usingcontent/',
              'content_scope':'English health-topic public-domain full-summary and vocabulary only; no A.D.A.M. encyclopedia, images, or drug monographs',
              'clinical_validation':False,'diagnostic_accuracy_measured':False}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xml',required=True);parser.add_argument('--source-url',required=True)
    args=parser.parse_args();print(json.dumps(build(args.xml,args.source_url),indent=2))
