"""Gespräch mit der KI: feste Vorgabe, kurzer Verlauf, verständliche Fehler."""

import json
import logging
import re
from pathlib import Path

from .antworten import Antwort, antworten, ist_gruss
from .ki import KiAnbieter, KiFehler, Nachricht
from .woerter import frage_nach_wort, wort_erklaert

log = logging.getLogger(__name__)

VERLAUF_MAX = 12  # Nachrichten, nicht Runden

ANWEISUNG = """Du bist {name}. Du hilfst einem Menschen, dem Lesen und Schreiben schwerfällt, mit Post von Ämtern \
(Jobcenter, Agentur für Arbeit, Krankenkasse, Rentenversicherung, Wohngeldstelle, Finanzamt und andere).

So antwortest du:
- Leichte Sprache: kurze Sätze, einfache Wörter, ein Gedanke pro Satz. Du duzt.
- Höchstens fünf Sätze. Deine Antwort wird vorgelesen: keine Aufzählungszeichen, keine Sternchen, \
keine Überschriften, keine Links, keine Emojis.
- Schwere Wörter vom Amt erklärst du kurz mit einfachen Worten.
- Du erfindest nichts. Was du nicht weißt, sagst du ehrlich.
- Du machst keine Rechtsberatung. Bei Widerspruch, Fristen, Kürzungen oder Rückforderungen sagst du: \
Hol dir Hilfe bei einer Beratungsstelle, zum Beispiel Sozialberatung, Erwerbslosenberatung oder Verbraucherzentrale.
- Du verschickst nichts und bezahlst nichts.
- Hat der Mensch einen Brief, bittest du um ein Foto davon. Den liest du dann. Was du schon über einen Brief gesagt hast, steht im Gesprächsverlauf.
"""

FEHLER = {
    "anmeldung": "Ich komme gerade nicht an meinen Denkhelfer. Ich sage dem Betreiber Bescheid.",
    "limit": "Ich habe heute schon sehr viel nachgedacht. Bitte frag mich später noch einmal.",
    "voruebergehend": "Ich bin gerade langsam. Bitte schick mir deine Frage gleich noch einmal.",
    "keine": "Ich habe deine Nachricht bekommen. Antworten lerne ich gerade noch. Bald kann ich dir mehr helfen.",
    "sonstig": "Da ist bei mir etwas schiefgegangen. Bitte versuch es später noch einmal.",
}


def fuer_vorlesen(text: str) -> str:
    """Entfernt Markdown-Reste, die beim Vorlesen stören würden."""
    text = re.sub(r"[*_#`>]+", "", text)
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.MULTILINE)
    return text.strip()


class Gespraech:
    def __init__(self, ki: KiAnbieter, name: str, datei: Path):
        self.ki = ki
        self.name = name
        self.datei = Path(datei)
        self.verlauf: list[Nachricht] = self._laden()

    def _laden(self) -> list[Nachricht]:
        try:
            return [Nachricht(**n) for n in json.loads(self.datei.read_text())][-VERLAUF_MAX:]
        except (FileNotFoundError, ValueError, TypeError):
            return []

    def _sichern(self) -> None:
        self.datei.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.datei.with_suffix(".neu")
        tmp.write_text(json.dumps([n.__dict__ for n in self.verlauf], ensure_ascii=False))
        tmp.replace(self.datei)

    def merken(self, rolle: str, text: str) -> None:
        self._merken(rolle, text)

    def _merken(self, rolle: str, text: str) -> None:
        self.verlauf = (self.verlauf + [Nachricht(rolle, text)])[-VERLAUF_MAX:]
        self._sichern()

    def antworten(self, art: str, text: str, neu_gekoppelt: bool) -> Antwort:
        text = text.strip()
        if neu_gekoppelt or art != "text" or not text or ist_gruss(text):
            antwort = antworten(art, text, self.name, neu_gekoppelt)
            if text:
                self._merken("nutzer", text)
            self._merken("momo", antwort.text)
            return antwort
        self._merken("nutzer", text)
        wort = frage_nach_wort(text)
        if wort:
            antwort = Antwort(wort_erklaert(*wort))
            self._merken("momo", antwort.text)
            return antwort
        try:
            ki_text = fuer_vorlesen(self.ki.fragen(ANWEISUNG.format(name=self.name), self.verlauf))
            if not ki_text:
                raise KiFehler("sonstig", "leere Antwort")
        except KiFehler as e:
            log.error("KI %s: %s (%s)", self.ki.name, e.art, str(e)[:200])
            return Antwort(FEHLER.get(e.art, FEHLER["sonstig"]))
        self._merken("momo", ki_text)
        return Antwort(ki_text)
