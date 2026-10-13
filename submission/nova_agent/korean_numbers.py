"""Spoken Korean quantities to digits ("백오 센티미터" -> "105 cm", "십육 점 오 키로그람" -> "16.5 kg").

Organizer narratives and patient replies spell measurements out in words, as speech would be transcribed. Every
measurement parser in the engine (growth velocity, weights, vitals) reads digits. Only a numeral immediately
followed by a measurement unit is converted, so ordinary words that share a syllable with a numeral ("일" = work,
"이" = this) are left alone. Text without such a phrase is returned unchanged.
"""
import re

_DIGIT = {"영": 0, "공": 0, "일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "륙": 6, "칠": 7, "팔": 8, "구": 9}
_SCALE = {"십": 10, "백": 100, "천": 1000}
_NUMERAL = "[영공일이삼사오육륙칠팔구십백천만]+"
_UNITS = (
    ("센티미터", "cm"), ("센티", "cm"), ("밀리미터", "mm"), ("미터", "m"),
    ("킬로그램", "kg"), ("킬로그람", "kg"), ("키로그램", "kg"), ("키로그람", "kg"), ("킬로", "kg"), ("키로", "kg"),
    ("그램", "g"), ("밀리그램", "mg"), ("밀리그람", "mg"), ("퍼센트", "%"), ("수은주밀리미터", "mmHg"),
)
_UNIT_RE = "|".join(sorted((re.escape(k) for k, _ in _UNITS), key=len, reverse=True))
_UNIT = dict(_UNITS)
_PHRASE = re.compile(rf"(?<![가-힣])({_NUMERAL})(?:\s*점\s*([영공일이삼사오육칠팔구]+))?\s*({_UNIT_RE})")
_NATIVE={'한':1,'하나':1,'두':2,'둘':2,'세':3,'셋':3,'네':4,'넷':4,'다섯':5,'여섯':6,'일곱':7,'여덟':8,'아홉':9,'열':10}
_TABLETS=re.compile(r'(?<![가-힣])('+'|'.join(_NATIVE)+r')\s+(알|정)(?![가-힣]|\s*(?:이상|이하))')


def sino_number(word: str):
    """'백오' -> 105, '십육' -> 16, '오십' -> 50, '천이백' -> 1200, '이만' -> 20000; None if not a numeral."""
    total, section, digit = 0, 0, None
    for ch in word:
        if ch in _DIGIT:
            if digit is not None:
                return None  # two bare digits in a row are not a sino-Korean number
            digit = _DIGIT[ch]
        elif ch in _SCALE:
            section += (1 if digit is None else digit) * _SCALE[ch]
            digit = None
        elif ch == "만":
            total += (section + (digit or 0) or 1) * 10000
            section, digit = 0, None
        else:
            return None
    return total + section + (digit or 0)


def normalize_spoken_numbers(text: str) -> str:
    if not text:
        return text or ""
    # Exact single quantities only. Ranges such as 두세 알 are not guessed.
    text=_TABLETS.sub(lambda m:f'{_NATIVE[m[1]]} {m[2]}',text)

    def convert(m):
        whole = sino_number(m.group(1))
        if whole is None:
            return m.group(0)
        value = str(whole)
        if m.group(2):
            if any(ch not in _DIGIT for ch in m.group(2)):
                return m.group(0)
            value += "." + "".join(str(_DIGIT[ch]) for ch in m.group(2))
        return f"{value} {_UNIT[m.group(3)]}"

    return _PHRASE.sub(convert, text)
