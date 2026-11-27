"""Feste Erklärliste für Behördenwörter, in Leichter Sprache.

Fest statt KI: Die Erklärung ist jedes Mal gleich und kann von einer Beratungsstelle geprüft werden.
Entwurf vom 27.11.2026, noch nicht fachlich geprüft.
"""

import re

# (Wort, Suchstämme im Brief, Erklärung). Reihenfolge = Vorrang, wenn mehrere im Brief stehen.
WOERTER: list[tuple[str, tuple[str, ...], str]] = [
    ("Anhörung", ("anhörung",),
     "Das Amt will etwas gegen dich entscheiden. Vorher fragt es dich: Was sagst du dazu? "
     "Du darfst antworten, bevor es entscheidet."),
    ("Erstattung", ("erstattung", "zu unrecht erhalten", "rückforderung"),
     "Das Amt meint: Du hast zu viel Geld bekommen. Du sollst einen Teil zurückzahlen."),
    ("Leistungsminderung", ("leistungsminderung", "gemindert", "minderung", "sanktion"),
     "Dein Geld vom Amt wird für eine Zeit gekürzt. Früher hieß das Sanktion."),
    ("Mitwirkungspflicht", ("mitwirkung",),
     "Du musst dem Amt helfen, deinen Antrag zu bearbeiten. Zum Beispiel Unterlagen schicken "
     "oder Fragen beantworten."),
    ("Versagung", ("versagt", "versagung", "entzogen", "entziehung"),
     "Das Amt zahlt nicht oder nicht mehr, weil Unterlagen oder Antworten fehlen."),
    ("Weiterbewilligungsantrag", ("weiterbewilligung",),
     "Damit sagst du dem Jobcenter: Ich brauche das Geld weiter. Ohne diesen Antrag kann die "
     "Zahlung aufhören."),
    ("Kooperationsplan", ("kooperationsplan", "eingliederungsvereinbarung"),
     "Ein Plan zwischen dir und dem Jobcenter. Darin steht, was du tust, um Arbeit zu finden, "
     "und wobei das Jobcenter dir hilft."),
    ("Widerspruch", ("widerspruch",),
     "Bist du mit einer Entscheidung vom Amt nicht einverstanden, kannst du das dem Amt sagen. "
     "Das heißt Widerspruch. Dafür gibt es eine Frist."),
    ("Rechtsbehelfsbelehrung", ("rechtsbehelfsbelehrung",),
     "Ein Text am Ende vom Brief. Dort steht, wie und bis wann du Widerspruch machen kannst."),
    ("Bescheid", ("bescheid",),
     "Ein Brief mit einer Entscheidung vom Amt. Zum Beispiel, wie viel Geld du bekommst."),
    ("Bewilligungszeitraum", ("bewilligungszeitraum", "für die zeit vom"),
     "Die Zeit, für die du das Geld bekommst. Danach musst du es neu beantragen."),
    ("Bedarfsgemeinschaft", ("bedarfsgemeinschaft", "bg-nummer"),
     "Die Menschen, die mit dir zusammen wohnen und zusammen Geld vom Jobcenter bekommen. "
     "Zum Beispiel du und dein Kind."),
    ("Regelbedarf", ("regelbedarf", "regelsatz"),
     "Das Geld für jeden Monat zum Leben. Für Essen, Kleidung und andere Dinge im Alltag."),
    ("Kosten der Unterkunft", ("kosten der unterkunft", "unterkunft und heizung"),
     "Das Geld für deine Wohnung. Also Miete, Nebenkosten und Heizung."),
    ("Mehrbedarf", ("mehrbedarf",),
     "Extra Geld, wenn du besondere Kosten hast. Zum Beispiel, weil du allein ein Kind großziehst."),
    ("Bekanntgabe", ("bekanntgabe",),
     "Der Tag, an dem der Brief als bei dir angekommen gilt. Ab dann läuft die Frist."),
]

FRAGE = re.compile(r"\b(was\s+(heißt|heisst|bedeutet|ist|sind|meint)|erklär|versteh)", re.I)


def _stamm_im(text: str, staemme: tuple[str, ...]) -> int:
    """Erste Fundstelle eines Stamms oder -1."""
    stellen = [text.find(s) for s in staemme]
    stellen = [s for s in stellen if s >= 0]
    return min(stellen) if stellen else -1


def im_brief(text: str, hoechstens: int = 2) -> list[tuple[str, str]]:
    """Die wichtigsten Behördenwörter aus dem Brief, nach Vorrang."""
    klein = (text or "").lower()
    treffer = [(wort, erklaerung) for wort, staemme, erklaerung in WOERTER if _stamm_im(klein, staemme) >= 0]
    return treffer[:hoechstens]


def frage_nach_wort(text: str) -> tuple[str, str] | None:
    """„Was heißt Anhörung?“ → (Wort, Erklärung). Nur bei einer echten Frage nach einem Wort."""
    if not FRAGE.search(text or ""):
        return None
    klein = text.lower()
    beste = None
    for wort, staemme, erklaerung in WOERTER:
        stelle = _stamm_im(klein, staemme + (wort.lower(),))
        if stelle >= 0 and (beste is None or stelle < beste[0]):
            beste = (stelle, wort, erklaerung)
    return (beste[1], beste[2]) if beste else None


def wort_erklaert(wort: str, erklaerung: str) -> str:
    return f"„{wort}“ heißt: {erklaerung}"
