"""Приведение текста к ASCII: весь вывод программы должен быть ASCII."""

import unicodedata

# Латиница для букв а..я (U+0430..U+044F) по порядку:
# а б в г д е ж з и й к л м н о п р с т у ф х ц ч ш щ ъ ы ь э ю я
_LATIN = [
    "a", "b", "v", "g", "d", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p",
    "r", "s", "t", "u", "f", "kh", "ts", "ch", "sh", "shch", "", "y", "", "e", "yu", "ya",
]
CYRILLIC = {chr(0x0430 + i): latin for i, latin in enumerate(_LATIN)}
# ё і ї є ґ
CYRILLIC |= {"\u0451": "e", "\u0456": "i", "\u0457": "yi", "\u0454": "ye", "\u0491": "g"}

# Типографские знаки из названий треков: дефисы и тире, кавычки, многоточие
PUNCTUATION = {
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u00ab": '"', "\u00bb": '"', "\u2026": "...", "\u00a0": " ",
}


def to_ascii(text: str) -> str:
    """Кириллицу транслитерировать, у латиницы снять диакритику (Ÿ -> Y),
    всё остальное (иероглифы и т.п.) записать как \\uXXXX."""
    out: list[str] = []
    for ch in text:
        if ch.isascii():
            out.append(ch)
        elif ch in PUNCTUATION:
            out.append(PUNCTUATION[ch])
        elif ch.lower() in CYRILLIC:
            latin = CYRILLIC[ch.lower()]
            out.append(latin if ch.islower() else latin.capitalize())
        else:
            # NFKD раскладывает "Ÿ" на "Y" + диакритический знак
            base = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode()
            out.append(base or ch.encode("ascii", "backslashreplace").decode())
    return "".join(out)
