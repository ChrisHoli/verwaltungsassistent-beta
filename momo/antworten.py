"""Was Momo sagt. Kurz, freundlich, Leichte Sprache. Ohne Delta Chat testbar."""

from dataclasses import dataclass

BEGRUESSUNG = (
    "Hallo! Ich bin {name}.\n"
    "Ich helfe dir mit Briefen und Papieren aller Art.\n"
    "Schick mir ein Foto von einem Brief oder Dokument. Ich lese es und lege es ordentlich ab.\n"
    "Dann sage ich dir: Was ist das? Was musst du tun? Bis wann?\n"
    "Du kannst mit mir sprechen: Schick mir einfach eine Sprachnachricht.\n"
    "Zum Beispiel: Was heißt Anhörung? Oder: Lies mir den Brief noch mal vor."
)

NOCH_NICHT = {
    "sprache": "Danke für deine Sprachnachricht. Zuhören kann ich gerade nicht. Schreib mir bitte oder versuch es später.",
    "text": "Ich habe deine Nachricht bekommen. Ich lerne gerade noch. Bald kann ich dir mehr helfen.",
}

BRIEF_ERSTE_SEITE = (
    "Danke, ich habe deinen Brief. Hat er noch mehr Seiten? Dann schick sie jetzt. "
    "In einer Minute lese ich ihn dir vor."
)
BRIEF_WEITERE_SEITE = "Seite {seite} ist auch gespeichert."
BRIEF_FEHLER = "Ich konnte deinen Brief gerade nicht speichern. Bitte schick ihn später noch einmal."
NICHT_VERSTANDEN = ("Ich habe dich leider nicht verstanden. Sprich bitte noch einmal, "
                    "langsam und nah am Handy.")
SPRACHE_AN = "Gut. Ab jetzt antworte ich dir immer auch mit einer Sprachnachricht."
SPRACHE_AUS = ("Gut. Ab jetzt antworte ich dir nur noch mit Text. "
               "Wenn du wieder hören willst, sag: Antworte mit Sprache.")
KEIN_BRIEF = "Ich habe noch keinen Brief von dir. Schick mir ein Foto davon, dann lese ich ihn dir vor."
DATEI_UNBEKANNT = "Diese Datei kann ich nicht verwenden. Schick mir bitte ein Foto oder ein PDF von deinem Brief."

GRUSSWORTE = {"hallo", "hi", "hey", "moin", "servus", "guten tag", "hallo momo", "start", "/start", "hilfe", "/hilfe"}


@dataclass(frozen=True)
class Antwort:
    text: str
    vorlesen: bool = True
    sprechtext: str | None = None  # wenn das Vorlesen anders klingen soll als der Text
    immer_vorlesen: bool = False  # auch wenn „nur Text“ eingestellt ist (z. B. „Lies mir das vor“)
    datei: str | None = None  # z. B. der fertige Antwortbrief als PDF
    vorlage: bool = False  # Antwortbrief-Vorlage: ihre Nachrichten-ID wird für die Freigabe gemerkt
    merken_als: str | None = None  # Nachrichten-ID unter diesem Namen merken (z. B. die Löschfrage)

    @property
    def zum_vorlesen(self) -> str:
        return self.sprechtext or self.text


def ist_gruss(text: str) -> bool:
    return text.strip().lower().rstrip("!.? ") in GRUSSWORTE


def antworten(art: str, text: str, name: str, neu_gekoppelt: bool) -> Antwort:
    """art: text | bild | datei | sprache | sonst."""
    if neu_gekoppelt or (art == "text" and ist_gruss(text)):
        return Antwort(BEGRUESSUNG.format(name=name))
    return Antwort(NOCH_NICHT.get(art, NOCH_NICHT["text"]))
