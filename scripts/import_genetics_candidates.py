#!/usr/bin/env python3
"""Import explicitly selected public-domain MedlinePlus Genetics condition descriptions.

Uses an offline copy of https://medlineplus.gov/download/ghr-summaries.xml.
Only health-condition-summary descriptions are imported, never gene/chromosome pages
or external database text. Selection is engineering coverage, not clinical prioritization.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'nova_agent/knowledge/genetics_candidates'
SOURCE = 'https://medlineplus.gov/download/ghr-summaries.xml'
ATTRIBUTION = 'Source: MedlinePlus, National Library of Medicine.'


def read_conditions(path):
    raw = Path(path).read_bytes()
    if len(raw) > 64 * 1024 * 1024 or b'<!ENTITY' in raw.upper():
        raise ValueError('Oversized XML or entity declaration rejected')
    root = ET.fromstring(raw)
    if root.tag.rsplit('}', 1)[-1] != 'summaries':
        raise ValueError('Expected MedlinePlus Genetics summaries')
    entries = []
    for topic in root.findall('{*}health-condition-summary'):
        name = topic.findtext('{*}name', '')
        url = topic.findtext('{*}ghr-page', '')
        match = re.fullmatch(r'https://medlineplus.gov/genetics/condition/([a-z0-9-]+)/?', url)
        if not match or not name.strip():
            raise ValueError('Invalid condition identity')
        paragraphs = []
        for section in topic.findall('{*}text-list/{*}text'):
            if section.findtext('{*}text-role') == 'description':
                for paragraph in section.findall('{*}html/{*}p'):
                    paragraphs.append(' '.join(''.join(paragraph.itertext()).split()))
        summary = '\n'.join(p for p in paragraphs if p)
        if not summary:
            continue
        slug = match.group(1)
        aliases = list(dict.fromkeys(s.text.strip() for s in topic.findall('{*}synonym-list/{*}synonym') if s.text and s.text.strip()))
        entries.append({'id': 'medlineplus_genetics_' + slug, 'name': name,
            'aliases': aliases, 'source_topic_id': slug, 'source_url': url, 'summary': summary,
            'groups': ['Genetic conditions'], 'source_reviewed_at': topic.findtext('{*}reviewed'),
            'attribution': ATTRIBUTION, 'validation_status': 'reference_only',
            'autonomous_diagnosis_enabled': False, 'clinical_review_verified': False})
    return raw, entries


def build(path, destination=DEST):
    raw, available = read_conditions(path)
    selected = (destination / 'selection.txt').read_text().splitlines()
    if len(selected) != 408 or len(set(selected)) != 408:
        raise ValueError('Expected 408 distinct selected conditions')
    by_name = {e['name']: e for e in available}
    entries = [by_name[name] for name in selected]
    payload = (json.dumps(entries, ensure_ascii=False, indent=2) + '\n').encode()
    sha = lambda b: hashlib.sha256(b).hexdigest()
    manifest = {'source_url': SOURCE, 'source_sha256': sha(raw),
        'source_sha256_scope': 'uncompressed_xml_bytes', 'catalog_sha256': sha(payload),
        'selection_sha256': sha((destination / 'selection.txt').read_bytes()),
        'n_reference_candidates': len(entries), 'source_kind': 'genetics_condition',
        'attribution': ATTRIBUTION, 'reuse_terms': 'https://medlineplus.gov/about/using/usingcontent/',
        'content_scope': 'Public-domain Genetics condition descriptions and synonyms only; no gene/chromosome pages or external database content',
        'selection_method': 'Frozen 408-name engineering selection; stable SHA256 name ordering after normalized name/alias overlap exclusion; not prevalence or clinical priority',
        'clinical_validation': False, 'diagnostic_accuracy_measured': False}
    (destination / 'catalog.json').write_bytes(payload)
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xml', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.xml), indent=2))
