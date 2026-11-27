"""Normale Sätze statt Befehle: erkennt die wenigen Wünsche, die Momo selbst erledigt (ohne KI).

Alles andere geht als Frage an das Gespräch.
"""

import re

NOCHMAL = "nochmal"
SPRACHE_AN = "sprache_an"
SPRACHE_AUS = "sprache_aus"

_AUS = [
    r"\b(nur|bloß|lieber)\s+(mit\s+|per\s+|als\s+)?(text|schrift|geschrieben|schreiben)",
    r"\b(keine|ohne|nicht mehr|kein)\b.{0,20}\b(sprach\w*|stimme|vorles\w*|audio)",
    r"\bnicht\s+(mehr\s+)?(vorlesen|sprechen|reden)\b",
    r"\b(hör|hoer)\s+auf\b.{0,20}\b(vorzulesen|zu sprechen|vorlesen)",
]
_AN = [
    r"\b(antwort\w*|sprich|sprech\w*|red\w*)\b.{0,25}\b(immer|wieder|auch|mit|per|als)\b.{0,15}"
    r"\b(sprach\w*|stimme|audio)",
    r"\b(lies|les|lese)\s+(mir\s+)?(immer|alles|wieder)\b.{0,15}\bvor\b",
    r"\b(immer|wieder)\b.{0,15}\b(vorlesen|sprachnachricht\w*)",
]
_NOCHMAL = [
    r"\b(lies|les|lese)\b.{0,40}\bvor\b",
    r"\b(noch\s*(ein)?mal|wiederhol\w*)\b.{0,30}\b(vorlesen|hören|sagen|brief)",
    r"\bwas\s+stand\s+(noch\s+mal\s+|nochmal\s+)?(in|im)\s+(dem|meinem|letzten)?\s*brief",
]


def erkennen(text: str) -> str | None:
    t = " ".join((text or "").lower().split())
    if len(t) > 160:  # lange Nachrichten sind Fragen, keine Wünsche
        return None
    for muster, wunsch in ((_AUS, SPRACHE_AUS), (_AN, SPRACHE_AN), (_NOCHMAL, NOCHMAL)):
        if any(re.search(m, t) for m in muster):
            return wunsch
    return None
