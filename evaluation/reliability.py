"""Descriptive confidence reliability, not a fitted probability calibrator."""
import math


def summarize_reliability(records):
    groups={}
    for record in records:
        if not record.get('scoring_expected',True):continue
        quality=record.get('decision_quality') or {}
        band=quality.get('band','UNREPORTED')
        group=groups.setdefault(band,{'n':0,'correct':0})
        group['n']+=1
        group['correct']+=bool(record.get('correct'))
    for group in groups.values():
        n=group['n'];p=group['correct']/n;z=1.96
        center=(p+z*z/(2*n))/(1+z*z/n)
        half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
        group.update(observed_accuracy=p,wilson_95=[max(0,center-half),min(1,center+half)])
    return {'calibrated_probabilities':False,'interpretation':'descriptive on supplied data; no generalization guarantee',
            'by_evidence_band':groups}
