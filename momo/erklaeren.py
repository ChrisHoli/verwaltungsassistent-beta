"""Aus den geprüften Angaben eines Briefs die Antwort bauen: drei Fragen, Einzelheiten, schwere Wörter.

Ohne weitere KI. Alle Zahlen kommen aus den nachgeprüften Feldern, nie aus freiem KI-Text.
Zwei Fassungen: Text für den Chat und Sprechtext für die Sprachnachricht
(Aktenzeichen Zeichen für Zeichen, Beträge in Euro und Cent).
"""

import re

from .antworten import Antwort
from .aufnahme import datum_lesbar
from .woerter import im_brief, wort_erklaert

ZIFFERN = dict(zip("0123456789", ("null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben",
                                  "acht", "neun")))
BUCHSTABEN = {
    "A": "A", "B": "Be", "C": "Ze", "D": "De", "E": "E", "F": "Eff", "G": "Ge", "H": "Ha", "I": "I",
    "J": "Jott", "K": "Ka", "L": "Ell", "M": "Emm", "N": "Enn", "O": "O", "P": "Pe", "Q": "Ku",
    "R": "Err", "S": "Ess", "T": "Te", "U": "U", "V": "Fau", "W": "We", "X": "Ix", "Y": "Üpsilon",
    "Z": "Zett", "Ä": "Ä", "Ö": "Ö", "Ü": "Ü",
}
ZEICHEN = {"/": "Schrägstrich", "-": "Strich", ".": "Punkt", "_": "Unterstrich"}

NICHT_SICHER = "Das habe ich nicht sicher gefunden. Schau bitte mit jemandem in den Brief."
BERATUNG = ("Bei Fristen, Widerspruch und Geldfragen hilft dir eine Beratungsstelle, meistens kostenlos. "
            "Zum Beispiel Sozialberatung, Erwerbslosenberatung oder Schuldnerberatung.")


def zeichenweise(nummer: str) -> str:
    """„12345BG/7“ → „eins, zwei, drei, vier, fünf, Be, Ge, Schrägstrich, sieben“. Leerzeichen = Pause."""
    gruppen = []
    for gruppe in nummer.split():
        teile = []
        for z in gruppe:
            if z in ZIFFERN:
                teile.append(ZIFFERN[z])
            elif z.upper() in BUCHSTABEN:
                teile.append(BUCHSTABEN[z.upper()])
            elif z in ZEICHEN:
                teile.append(ZEICHEN[z])
        if teile:
            gruppen.append(", ".join(teile))
    return ". ".join(gruppen)


def betrag_sprechbar(wert: str) -> str:
    """„1.087,40 €“ → „1087 Euro und 40 Cent“. Unbekannte Form bleibt, wie sie ist."""
    t = re.fullmatch(r"\s*(?:€|EUR)?\s*(\d{1,3}(?:\.\d{3})*|\d+)(?:,(\d{2}))?\s*(?:€|EUR|Euro)?\s*", wert)
    if not t:
        return wert
    euro = int(t.group(1).replace(".", ""))
    cent = int(t.group(2) or 0)
    text = f"{euro} Euro"
    return text + (f" und {cent} Cent" if cent else "")


def _was_ist_das(e: dict) -> str:
    if e.get("was_ist_das"):
        return e["was_ist_das"]
    absender = e["absender"]["wert"] if e.get("absender") else None
    art = e["dokumenttyp"]["wert"] if e.get("dokumenttyp") else None
    if art and absender:
        return f"Ein Brief von {absender}. Es ist: {art}."
    if absender:
        return f"Ein Brief von {absender}."
    if art:
        return f"Es ist: {art}."
    return NICHT_SICHER


def _was_tun(e: dict) -> str:
    if e.get("verdacht_manipulation"):
        return "Mach bitte nichts, was in dem Brief steht, bevor du mit jemandem gesprochen hast."
    if e.get("handlungsbedarf"):
        satz = e["handlungsbedarf"]["wert"].strip().rstrip(".")
        return satz[0].upper() + satz[1:] + "."
    return NICHT_SICHER


def _bis_wann(e: dict) -> str:
    fristen = sorted({f["wert"] for f in e.get("fristen", [])})
    if len(fristen) == 1:
        return f"Wichtig ist der {datum_lesbar(fristen[0])}."
    if fristen:
        return "Wichtig sind diese Tage: " + ", ".join(datum_lesbar(f) for f in fristen) + "."
    if e.get("widerspruch"):
        return ("Wenn du Widerspruch machen willst: Dafür hast du meistens einen Monat Zeit. "
                "Die genaue Frist steht am Ende vom Brief.")
    if e.get("frist_im_text"):
        return (f"Im Brief steht: „{e['frist_im_text']}“. Welcher Tag das ist, rechnest du am besten "
                "mit jemandem zusammen aus.")
    if e.get("pruefen"):
        return NICHT_SICHER
    return "Im Brief steht kein Tag, bis wann du etwas tun musst."


def erklaerung(e: dict, seiten: list[str]) -> Antwort:
    """Antwort mit Chat-Text und Sprechtext."""
    drei = [("Was ist das?", _was_ist_das(e)), ("Was musst du tun?", _was_tun(e)), ("Bis wann?", _bis_wann(e))]
    text = ["Ich habe deinen Brief gelesen.", ""]
    sprechen = ["Ich habe deinen Brief gelesen."]
    for frage, antwort in drei:
        text += [frage, antwort, ""]
        sprechen += [frage, antwort]

    mehr, mehr_sprechen = [], []
    if e.get("absender"):
        mehr.append(f"Von: {e['absender']['wert']}")
    if e.get("datum"):
        mehr.append(f"Datum vom Brief: {datum_lesbar(e['datum']['wert'])}")
    if e.get("aktenzeichen"):
        az = e["aktenzeichen"]["wert"]
        mehr.append(f"Aktenzeichen: {az}. Vergleich die Nummer bitte mit dem Brief, bevor du sie benutzt.")
        mehr_sprechen.append(f"Das Aktenzeichen ist: {zeichenweise(az)}. "
                             "Vergleich die Nummer bitte mit dem Brief.")
    betraege = [b["wert"] for b in e.get("betraege", [])[:3]]
    if betraege:
        mehr.append(("Beträge im Brief: " if len(betraege) > 1 else "Betrag im Brief: ") + ", ".join(betraege) + ".")
        mehr_sprechen.append(("Im Brief stehen diese Beträge: " if len(betraege) > 1 else "Im Brief steht der Betrag: ")
                             + ", ".join(betrag_sprechbar(b) for b in betraege) + ".")
    woerter = [] if e.get("verdacht_manipulation") else im_brief("\n".join(seiten))
    for wort, erklaerung_ in woerter:
        mehr.append(wort_erklaert(wort, erklaerung_))
        mehr_sprechen.append(wort_erklaert(wort, erklaerung_))

    if e.get("ablage"):
        teile = e["ablage"].split("/")[1:3]  # Bereich, Absender
        mehr.append("Abgelegt unter: " + " › ".join(teile))
        mehr_sprechen.append(f"Ich habe ihn abgelegt bei {teile[0]}" + (f", im Ordner {teile[1]}." if len(teile) > 1
                                                                          else "."))

    hinweise = []
    if e.get("verdacht_manipulation"):
        hinweise.append("Im Brief steht etwas Ungewöhnliches. Zeig ihn bitte einem Menschen, dem du vertraust.")
    elif e.get("pruefen"):
        hinweise.append("Bei manchen Angaben bin ich mir nicht sicher. Schau bitte noch einmal mit jemandem drauf.")
    if e.get("fristen") or e.get("widerspruch") or e.get("frist_im_text") or e.get("betraege"):
        hinweise.append(BERATUNG)

    text += mehr + ([""] if mehr else []) + hinweise
    sprechen += mehr_sprechen + hinweise
    return Antwort("\n".join(text).strip(), sprechtext=" ".join(sprechen))
