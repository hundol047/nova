#!/usr/bin/env python3
"""Report actual clinical content, not a catalog-size proxy for diagnostic capability."""
import argparse,json,sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nova_agent.ontology.registry import get_default_catalog
from nova_agent.candidate_generator import _concept_to_kb_entry


def audit():
    fields=('typical_features','specific_features','confirmatory_findings','risk_factors','reassuring_if_present','minimum_workup')
    rows=[]
    for c in get_default_catalog().all_concepts():
        if c.tier.value=='TIER1_DEEP':continue
        e=_concept_to_kb_entry(c)
        rows.append(dict(id=c.concept_id,name=c.canonical_name,source=c.source,curation_label=c.curation_status,
            counts={f:len(e.get(f,[])) for f in fields},
            diagnostic_depth='ABSENT' if not any(e.get(f) for f in fields) else 'PARTIAL'))
    return dict(catalog_entries=len(rows),depth_counts=dict(Counter(r['diagnostic_depth'] for r in rows)),
        fields_populated={f:sum(r['counts'][f]>0 for r in rows) for f in fields},
        interpretation='Terminology retrieval is not clinical reasoning depth. No missing clinical facts were invented.',
        enrichment_status='DEFERRED: these entries have no repo-backed clinical fields; clinical source review and adjudication required.',rows=rows)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();r=audit()
    Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='rows'}))
