"""Small adversarial evidence-interpretation probes, not diagnostic accuracy.

Authored before this revision's fixes. Positive and negative controls test whether
asserted observations are distinguished from tentative, negated or weaker ones.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from nova_agent.state import PatientState
from nova_agent.differential import _score_disease
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.evidence_interpreter import concept_present

# id, procedure (or concept), diagnosis/feature, text, support label, expected
PROBES = [
 ('csf_denied','lumbar_puncture','meningitis','no elevated white cell count','CSF pleocytosis',False),
 ('csf_possible','lumbar_puncture','meningitis','possible elevated white cell count','CSF pleocytosis',False),
 ('csf_pending','lumbar_puncture','meningitis','elevated white cell count pending confirmation','CSF pleocytosis',False),
 ('csf_positive','lumbar_puncture','meningitis','elevated white cell count','CSF pleocytosis',True),
 ('troponin_possible','troponin','acute_coronary_syndrome','possible elevated troponin; repeat pending','elevated troponin',False),
 ('troponin_hypothetical','troponin','acute_coronary_syndrome','if elevated troponin, reassess','elevated troponin',False),
 ('troponin_inconclusive','troponin','acute_coronary_syndrome','elevated troponin? inconclusive','elevated troponin',False),
 ('troponin_positive','troponin','acute_coronary_syndrome','elevated troponin','elevated troponin',True),
 ('troponin_contrast','troponin','acute_coronary_syndrome','no hemolysis; elevated troponin','elevated troponin',True),
 ('ketones_unspecified','ketones','diabetic_ketoacidosis','positive','large ketones',False),
 ('ketones_large','ketones','diabetic_ketoacidosis','large','large ketones',True),
 ('ketones_trace','ketones','diabetic_ketoacidosis','trace positive','large ketones',False),
 ('ketones_tentative','ketones','diabetic_ketoacidosis','possible large ketones','large ketones',False),
 ('hcg_possible','beta_hcg','ectopic_pregnancy','possibly positive','positive beta-hCG',False),
 ('hcg_positive','beta_hcg','ectopic_pregnancy','positive','positive beta-hCG',True),
 ('lipase_tentative','lipase','acute_pancreatitis','possible elevated lipase','elevated lipase',False),
 ('lipase_positive','lipase','acute_pancreatitis','elevated','elevated lipase',True),
 ('sounds_double_negative','concept','absent breath sounds','no absent breath sounds','',False),
 ('sounds_possible','concept','absent breath sounds','possible absent breath sounds','',False),
 ('sounds_positive','concept','absent breath sounds','absent breath sounds on the left','',True),
 ('sounds_normal','concept','absent breath sounds','clear breath sounds bilaterally','',False),
 ('sounds_no_sounds','concept','absent breath sounds','no breath sounds on the right','',True),
]


def run():
    rows=[]
    for key,procedure,diagnosis,text,label,expected in PROBES:
        if procedure=='concept':actual=concept_present(diagnosis,[text])
        else:
            state=PatientState()
            state.record_test(procedure,text)
            actual=label in _score_disease(disease_by_id(diagnosis),state)[2]
        rows.append(dict(id=key,text=text,expected=expected,actual=actual,correct=actual==expected))
    return {'metric':'evidence interpretation, NOT diagnostic accuracy','role':'same-author adversarial regression probes',
            'correct':sum(r['correct'] for r in rows),'total':len(rows),'cases':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--save-json',required=True)
    args=parser.parse_args()
    report=run()
    Path(args.save_json).write_text(json.dumps(report,indent=2)+'\n')
    print(f"Evidence probes: {report['correct']}/{report['total']}")

if __name__=='__main__': main()
