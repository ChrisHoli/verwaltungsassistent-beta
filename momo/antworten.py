"""Was Momo sagt. Kurz, freundlich, Leichte Sprache. Ohne Delta Chat testbar."""

from dataclasses import dataclass

BEGRUESSUNG = (
    "Hallo! Ich bin {name}.\n"
    "Ich helfe dir mit Briefen von Ämtern.\n"
    "Bald kannst du mir ein Foto von einem Brief schicken.\n"
    "Dann sage ich dir: Was ist das? Was musst du tun? Bis wann?\n"
    "Du kannst mir auch eine Sprachnachricht schicken."
)

NOCH_NICHT = {
    "bild": "Danke für das Bild. Briefe lesen lerne ich gerade noch. Bald kann ich das.",
    "datei": "Danke für die Datei. Briefe lesen lerne ich gerade noch. Bald kann ich das.",
    "sprache": "Danke für deine Sprachnachricht. Zuhören lerne ich gerade noch. Bald kann ich das.",
    "text": "Ich habe deine Nachricht bekommen. Ich lerne gerade noch. Bald kann ich dir mehr helfen.",
}

BRIEF_ERSTE_SEITE = (
    "Danke. Ich habe deinen Brief gespeichert. Hat er noch mehr Seiten? "
    "Dann schick mir die gleich hinterher. Lesen lerne ich gerade noch."
)
BRIEF_WEITERE_SEITE = "Seite {seite} ist auch gespeichert."
BRIEF_FEHLER = "Ich konnte deinen Brief gerade nicht speichern. Bitte schick ihn später noch einmal."
DATEI_UNBEKANNT = "Diese Datei kann ich nicht verwenden. Schick mir bitte ein Foto oder ein PDF von deinem Brief."

GRUSSWORTE = {"hallo", "hi", "hey", "moin", "servus", "guten tag", "hallo momo", "start", "/start", "hilfe", "/hilfe"}


@dataclass(frozen=True)
class Antwort:
    text: str
    vorlesen: bool = True


def ist_gruss(text: str) -> bool:
    return text.strip().lower().rstrip("!.? ") in GRUSSWORTE


def antworten(art: str, text: str, name: str, neu_gekoppelt: bool) -> Antwort:
    """art: text | bild | datei | sprache | sonst."""
    if neu_gekoppelt or (art == "text" and ist_gruss(text)):
        return Antwort(BEGRUESSUNG.format(name=name))
    return Antwort(NOCH_NICHT.get(art, NOCH_NICHT["text"]))
