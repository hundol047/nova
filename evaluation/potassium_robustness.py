"""Same-author parser probes, NOT diagnostic accuracy or independent clinical cases."""
import argparse
import json
from pathlib import Path
from nova_agent.electrolyte_evidence import extract_potassium_mmol_l

PROBES = []
for value in (4.2, 6.8):
    for unit in ('', 'mmol/L', 'mEq/L', 'mmol / L'):
        PROBES.append((f'potassium {value} {unit}'.strip(), value))
    for unit in ('mol/L', 'mEq/dL', 'mmol/dL', 'mmol/mL', 'µmol/L', 'unknown', 'mg/L'):
        PROBES.append((f'potassium {value} {unit}', None))
for text in (
    'K 6,8 mmol/L', 'K 6.8e-3 mol/L', 'K 6.8–7.1 mmol/L', 'K 6.8—7.1 mmol/L',
    'K 6.8 to 7.1 mmol/L', 'K 6.8-7.1 mmol/L', 'K >6.5 mmol/L',
    'possible potassium 6.8 mmol/L', 'potassium 6.8 mmol/L?',
    'potassium 6.8 mmol/L pending confirmation', 'potassium 6.8 mmol/L not confirmed',
    'potassium 6.8 mmol/L; potassium 4.2 mmol/L', 'K 4.2 mmol/L; K 6.8 mmol/L',
    'previous potassium 6.8 mmol/L', 'potassium 6.8 mmol/L hemolyzed',
    'no potassium 6.8 mmol/L', 'potassium 6.8 mmol/L; K 8 mol/L',
    'K 0 mmol/L', 'K 19 mmol/L',
): PROBES.append((text, None))
PROBES += [('K+ 6.8 mmol/L, creatinine 1.0 mg/dL', 6.8),
           ('potassium 4.2 mmol/L; K 4.2 mEq/L', 4.2)]


def run():
    rows = [{'text':t, 'expected':v, 'actual':extract_potassium_mmol_l(t)} for t,v in PROBES]
    for row in rows: row['correct'] = row['expected'] == row['actual']
    return {'metric':'potassium_text_parser_correctness_only', 'independent_validation':False,
            'clinical_accuracy_claim':False, 'role':'same-author synthetic parser probes',
            'correct':sum(r['correct'] for r in rows), 'total':len(rows), 'cases':rows}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--save-json',required=True)
    args=parser.parse_args();r=run();Path(args.save_json).write_text(json.dumps(r,indent=2)+'\n')
    print(r['correct'], '/', r['total'])
