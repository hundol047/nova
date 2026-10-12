"""Clinical +/- notation is assertion data, never a positive keyword alone.

Original encounter text remains untouched. This projection is for matching only.
Mixed bilateral signs remain uncertain rather than being reduced to all-positive.
"""
import re

_SIGNS = re.compile(r'([^,;\n:()]{1,100}?)\s*\(\s*([+\-−?](?:\s*/\s*[+\-−?])*)\s*\)')


def normalize_exam_notation(text):
    text = str(text or '')
    if '(' not in text or not re.search(r'\(\s*[+\-−?]',text):
        return text
    def project(match):
        finding, signs = match.groups()
        values = signs.replace('−', '-').replace(' ', '').split('/')
        status = 'present' if all(v == '+' for v in values) else 'absent' if all(v == '-' for v in values) else 'uncertain'
        return finding.strip() + ' is ' + status + ';'
    return _SIGNS.sub(project, text)
