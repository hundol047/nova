#!/usr/bin/env python3
"""Import analytical summaries only; raw files must remain outside the repository."""
import argparse
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.official_result_tools import LABEL, redact, safe_files
from scripts.analyze_official_samples import analyze


def import_results(input_dir, output_dir, annotations=None):
    source=Path(input_dir).resolve();target=Path(output_dir).resolve()
    if source.is_relative_to(ROOT):raise ValueError('Raw human results must be outside the repository.')
    rows=[row for _,row in safe_files(source)]
    if not rows or any(row.get('mode')!='HUMAN_RUN' or row.get('label')!=LABEL for row in rows):
        raise ValueError('Only explicitly labeled HUMAN_RUN public sample results are accepted; fixtures refused.')
    report=redact(analyze(rows,annotations))
    payloads={}
    for name in ('official_sample_summary','doctor_quality','latency_tokens','exam_metrics','record_grounding','model_identity','rag_metrics'):
        value={'label':LABEL,'origin_attestation':report['origin_attestation'],'results':report[name]}
        text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
        if re.search(r'Bearer\s+\S+|sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|-----BEGIN.*PRIVATE KEY',text,re.I):
            raise ValueError('Secret scan rejected output before writing')
        payloads[name+'.json']=text
    # All analytical payloads pass before any artifact is written.
    target.mkdir(parents=True,exist_ok=True)
    for name,text in payloads.items():(target/name).write_text(text,encoding='utf-8')
    return sorted(payloads)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--output',default=str(ROOT/'artifacts/human_official_review'));p.add_argument('--annotations');a=p.parse_args()
    notes=json.loads(Path(a.annotations).read_text()) if a.annotations else None
    print(json.dumps(import_results(a.input,a.output,notes)))

if __name__=='__main__':main()
