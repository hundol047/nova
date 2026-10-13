"""Shared exact Korean symptom questions; wording only, no diagnostic rules."""

# Exact, single-feature questions only. Open, compound, family and negated
# questions must never turn a bare acknowledgement into a patient finding.
SINGLE_FEATURE_QUESTIONS = {
    'tremor': ('손이 떨리나요?', '손 떨림이 있나요?'),
    'heat intolerance': ('더위를 견디기 어려우신가요?', '더위를 많이 타시나요?'),
    'sweating': ('땀이 평소보다 많아졌나요?', '땀이 많이 나나요?'),
    'palpitations': ('가슴이 두근거리나요?', '심장이 두근거리나요?'),
    'fever': ('열이 나나요?', '발열이 있나요?'),
    'cough': ('기침이 나나요?', '기침을 하시나요?'),
    'shortness of breath': ('숨이 차나요?', '호흡이 곤란한가요?'),
    'chest pain': ('가슴에 통증이 있나요?', '가슴이 아프신가요?'),
    'nausea': ('메스꺼운가요?', '속이 메스껍나요?'),
    'vomiting': ('구토를 했나요?', '토하셨나요?'),
    'diarrhea': ('설사를 하나요?', '설사가 있나요?'),
    'dysuria': ('소변볼 때 아픈가요?', '소변볼 때 따가운가요?'),
    'hematuria': ('소변에 피가 섞여 나오나요?', '혈뇨가 있나요?'),
    'syncope': ('이번 증상 때 의식을 잃었나요?', '이번 증상 때 실신했나요?'),
    'snoring': ('잘 때 코골이가 있나요?', '코골이가 있나요?'),
    'weight loss': ('체중이 줄었나요?', '살이 빠졌나요?'),
}

