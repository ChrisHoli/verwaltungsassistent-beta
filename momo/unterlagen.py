"""Was die KI bei freien Fragen über die Briefe erfährt – und was Momo an ihrer Antwort nachprüft.

Freie Fragen („Wo soll ich das Geld hinschicken?“, „Muss ich da hingehen?“) beantwortet die KI. Damit sie nicht
raten muss, bekommt sie den Text des Briefs, um den es gerade geht, und eine kurze Liste der übrigen Briefe.
Kontonummern und Beträge in ihrer Antwort prüft Momo gegen den Brief (Grundregel 6).
"""

import re

from .erklaeren import zeichenweise

BRIEF_MAX = 12000  # Zeichen Brieftext an die KI
LISTE_MAX = 15

FRAGEWORT = re.compile(
    r"^\s*(wo|wohin|woher|was|wann|wie|wer|wem|wen|wessen|warum|wieso|weshalb|welche[rsmn]?|wofür|worum|wozu|"
    r"womit|worauf|wieviel|wie\s?viel|muss|soll|sollte|kann|darf|gibt|ist|sind|stimmt|bin|habe?|hast|hat|"
    r"brauche?|bekomme?|kriege?|weißt|weisst|erklär|sag\s+mir|kannst\s+du\s+mir\s+sagen)\b", re.I)


def ist_frage(text: str) -> bool:
    t = (text or "").strip()
    return t.endswith("?") or bool(FRAGEWORT.match(t))


def _zeile(nr: int, b: dict) -> str:
    teile = [f"Brief {nr + 1}", b.get("datum") or b.get("eingang") or "", b.get("absender") or "unbekannt",
             b.get("betreff") or b.get("dokumenttyp") or "", f"Bereich {b.get('kategorie') or 'Sonstiges'}"]
    offen = [f"{f['datum']} ({'Erinnerung an' if f['status'] == 'bestaetigt' else f['status']})"
             for f in b.get("fristen", []) if f.get("status") not in ("erledigt", "abgelehnt")]
    if offen:
        teile.append("Fristen: " + ", ".join(offen))
    if b.get("verdacht"):
        teile.append("VORSICHT: Verdacht auf Betrug")
    return " · ".join(t for t in teile if t)


def zusammenstellen(briefe: list[dict], aktuell: int | None, brieftext: str) -> str:
    """Text für die KI: der aktuelle Brief im Wortlaut, dazu eine Liste aller Briefe."""
    if not briefe:
        return ""
    teile = []
    if aktuell is not None:
        b = briefe[aktuell]
        kopf = _zeile(aktuell, b)
        if b.get("erklaerung", {}).get("text"):
            kopf += "\nDeine Erklärung dazu: " + b["erklaerung"]["text"][:1500]
        text = brieftext[:BRIEF_MAX] + ("\n[… gekürzt]" if len(brieftext) > BRIEF_MAX else "")
        teile.append(f"Der Brief, um den es gerade geht ({kopf}):\n{text}")
    start = max(0, len(briefe) - LISTE_MAX)
    teile.append("Alle Briefe, die du kennst (neueste zuletzt):\n" +
                 "\n".join(_zeile(i, briefe[i]) for i in range(start, len(briefe))))
    return "\n\n".join(teile)


IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){3,7}(?:[ ]?[A-Z0-9]{1,3})?\b")
BETRAG = re.compile(r"(\d{1,3}(?:\.\d{3})+|\d+),(\d{2})(?=\s*(?:€|EUR|Euro))|(?<=€)\s*(\d{1,3}(?:\.\d{3})+|\d+),(\d{2})")


def _norm(t: str) -> str:
    return re.sub(r"[\s.]", "", t or "").upper()


def ungedeckte_zahlen(antwort: str, quelle: str) -> list[str]:
    """Kontonummern und Beträge aus der Antwort, die so nicht in den Unterlagen stehen."""
    q = _norm(quelle)
    fehlt = [m.group(0) for m in IBAN.finditer(antwort or "") if _norm(m.group(0)) not in q]
    for m in BETRAG.finditer(antwort or ""):
        euro, cent = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        if _norm(f"{euro},{cent}") not in q:
            fehlt.append(f"{euro},{cent} €")
    return fehlt


def sprechbar(text: str) -> str:
    """Kontonummern Zeichen für Zeichen vorlesen."""
    return IBAN.sub(lambda m: zeichenweise(m.group(0)), text or "")
