"""Explicit synthetic-response mapping; never inspect a diagnosis label.

Alias matches preserve all supplied results. CBC/BMP responses may be partial;
unsupplied components are unknown, not normal. Non-equivalent imaging procedures
(e.g. generic chest CT versus pulmonary angiography) are never guessed.
"""
ALIASES = {
    'ASK': {'medication': ('medications',), 'allergy': ('allergies',)},
    'EXAM': {
        'general_appearance': ('general_exam',),
        'lung_auscultation': ('chest_exam', 'respiratory_exam'),
        'cardiac_auscultation': ('cardiac_exam', 'cardiovascular_exam'),
        'extremity_exam': ('leg_exam',),
    },
    'TEST': {
        'cxr': ('chest_xray',),
        'cbc': ('wbc', 'hemoglobin', 'platelets'),
        'bmp': ('sodium', 'potassium', 'bicarbonate', 'creatinine'),
    },
}
MISSING = 'Not provided in synthetic case.'


def resolve(case, action_type, key):
    mappings = {'ASK': case.answers, 'EXAM': case.exam_results, 'TEST': case.test_results}
    if action_type not in mappings:
        return ''
    mapping = mappings[action_type]
    keys = (key, *ALIASES.get(action_type, {}).get(key, ()))
    supplied = [(source, mapping[source]) for source in keys if source in mapping]
    if not supplied:
        return MISSING
    if len(supplied) == 1 and supplied[0][0] == key:
        return supplied[0][1]
    # Keep provenance and possible conflicting statements, not the first/most favorable result.
    return '; '.join(source + ': ' + text for source, text in supplied)
