"""Validated offline catalog extensions; source declarations are not clinical review."""
import json
from pathlib import Path
from nova_agent.taxonomy import EXAM_CATALOG, QUESTION_CATALOG, TEST_CATALOG


def load_extension(path, existing_ids):
    entries=json.loads(Path(path).read_text())
    if not isinstance(entries,list):raise ValueError('Knowledge extension must be a JSON list')
    seen=set(existing_ids)
    for entry in entries:
        if not isinstance(entry,dict) or not all(isinstance(entry.get(k),str) and entry[k].strip() for k in ['id','name','evidence_level']):
            raise ValueError('Extension requires nonempty id, name and evidence_level')
        if entry['id'] in seen:raise ValueError('Duplicate diagnosis ID; overriding built-in knowledge is forbidden')
        seen.add(entry['id'])
        if not isinstance(entry.get('sources'),list) or not entry['sources'] or not all(isinstance(s,str) and s.startswith('https://') for s in entry['sources']):
            raise ValueError('Source URLs are required (declared provenance, not verified authority)')
        if not isinstance(entry.get('dangerous'),bool) or entry.get('urgency') not in {'LOW','MEDIUM','HIGH','CRITICAL'}:
            raise ValueError('Explicit dangerous and urgency metadata required')
        for field in ['aliases','chief_complaint_tags','typical_features','risk_factors','confirmatory_findings',
                      'discriminating_questions','discriminating_exams','discriminating_tests','minimum_workup','red_flag_keywords']:
            value=entry.get(field,[])
            if not isinstance(value,list) or not all(isinstance(x,str) for x in value):raise ValueError('Invalid '+field)
        for field,catalog in [('discriminating_questions',QUESTION_CATALOG),('discriminating_exams',EXAM_CATALOG),('discriminating_tests',TEST_CATALOG)]:
            if set(entry.get(field,[]))-set(catalog):raise ValueError('Unsupported action in '+field)
        if set(entry.get('minimum_workup',[]))-(set(TEST_CATALOG)|set(EXAM_CATALOG)):
            raise ValueError('Unsupported minimum workup')
        if not entry.get('typical_features') and not entry.get('confirmatory_findings'):
            raise ValueError('Diagnostic evidence features required')
    return entries
