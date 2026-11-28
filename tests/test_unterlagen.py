from momo import unterlagen as ul
from momo.ki import KiAnbieter

from test_antwortbrief import Schreiber, SEITE
from test_sprechen import _bote
from test_vorgaenge import BRIEF, Chat, uhr

RECHNUNG = """Stadtwerke Musterstadt · Rechnung Nr. 4711
Bitte überweisen Sie 87,50 € bis zum 15.12.2026 auf folgendes Konto:
IBAN DE12 3456 7890 1234 5678 90 · Verwendungszweck: Kundennummer 0815"""


class Merker(KiAnbieter):
    name = "merker"

    def __init__(self, antwort):
        self.antwort = antwort
        self.anweisungen = []

    def fragen(self, anweisung, verlauf):
        self.anweisungen.append(anweisung)
        return self.antwort


def test_ist_frage():
    for t in ("Wo soll ich das Geld hinschicken", "wohin muss ich überweisen", "Muss ich da hin",
              "Was heißt das genau?", "Welche Unterlagen brauchen die", "Kann ich das in Raten zahlen"):
        assert ul.ist_frage(t), t
    for t in ("Schreib bitte freundlicher", "Mach den Brief kürzer", "Und füg hinzu, dass ich krank war"):
        assert not ul.ist_frage(t), t


def test_ungedeckte_zahlen():
    assert ul.ungedeckte_zahlen("Überweise 87,50 € auf DE12 3456 7890 1234 5678 90.", RECHNUNG) == []
    assert ul.ungedeckte_zahlen("Überweise 97,50 € auf DE99 3456 7890 1234 5678 90.", RECHNUNG) == [
        "DE99 3456 7890 1234 5678 90", "97,50 €"]


def test_sprechbar_liest_iban_zeichenweise():
    s = ul.sprechbar("Konto: DE12 3456 7890 1234 5678 90.")
    assert "De, E, eins, zwei" in s or "eins, zwei" in s
    assert "DE12" not in s


def test_zusammenstellen_mit_wortlaut_und_liste():
    briefe = [{"absender": "Jobcenter Musterstadt", "betreff": "Unterlagen", "fristen": []}, {"absender": "Stadtwerke", "betreff": "Rechnung", "fristen": [
        {"datum": "2026-12-15", "status": "bestaetigt"}], "kategorie": "Wohnen"}]
    t = ul.zusammenstellen(briefe, 1, RECHNUNG)
    assert "DE12 3456" in t and "Brief 2" in t and "2026-12-15 (Erinnerung an)" in t and "Brief 1" in t


def test_freie_frage_geht_mit_brief_an_die_ki(tmp_path):
    b = _bote(tmp_path)
    b.vorgaenge.uhr = uhr("2026-11-28")
    b.vorgaenge.brief_eintragen("Briefe/alt", BRIEF)
    b.briefe.ablage.schreiben("Briefe/alt/text/seite-01.txt", SEITE.encode())
    b.vorgaenge.brief_eintragen("Briefe/neu", dict(BRIEF, absender={"wert": "Stadtwerke Musterstadt"}))
    b.briefe.ablage.schreiben("Briefe/neu/text/seite-01.txt", RECHNUNG.encode())
    ki = Merker("Überweise 87,50 € auf das Konto DE12 3456 7890 1234 5678 90. Das steht unten auf Seite 1.")
    b.gespraech.ki = ki
    a = b.antworten_auf("text", "Wo soll ich das Geld hinschicken", False)
    assert "DE12 3456" in a.text and "Achtung" not in a.text
    assert "Verwendungszweck" in ki.anweisungen[0] and "<<<UNTERLAGEN-" in ki.anweisungen[0]
    assert "DE12" not in a.zum_vorlesen  # Kontonummer wird Zeichen für Zeichen vorgelesen


def test_erfundene_kontonummer_wird_angemerkt(tmp_path):
    b = _bote(tmp_path)
    b.vorgaenge.brief_eintragen("Briefe/neu", BRIEF)
    b.briefe.ablage.schreiben("Briefe/neu/text/seite-01.txt", RECHNUNG.encode())
    b.gespraech.ki = Merker("Schick es an DE00 1111 2222 3333 4444 55.")
    a = b.antworten_auf("text", "Wohin mit dem Geld?", False)
    assert "Achtung: DE00 1111 2222 3333 4444 55 habe ich so nicht im Brief gefunden" in a.text


def test_offener_entwurf_fängt_keine_fragen_ab(tmp_path):
    """Der Fehler vom 28.11.: Ein offener Antwortbrief zum alten Brief hat eine Frage als Änderung genommen."""
    b = _bote(tmp_path)
    b.gespraech.ki = Schreiber()
    b.vorgaenge.uhr = uhr("2026-11-15")
    b.vorgaenge.brief_eintragen("Briefe/a", BRIEF)
    b.briefe.ablage.schreiben("Briefe/a/text/seite-01.txt", SEITE.encode())
    b._chat = Chat()
    b.antworten_auf("text", "Schreib dem Jobcenter, dass ich die Unterlagen nächste Woche schicke", False)
    a = b.antworten_auf("text", "Max Beispiel, Lindenweg 7, 12345 Musterstadt", False)
    assert a.vorlage and b.entwuerfe.entwurf() is not None
    ki = Merker("Das steht auf Seite 1.")
    b.gespraech.ki = ki
    a = b.antworten_auf("text", "Wo soll ich das Geld hinschicken", False)
    assert a.text.startswith("Das steht auf Seite 1.") and not a.vorlage
    assert b.entwuerfe.entwurf() is not None  # der Entwurf bleibt, er wird nur nicht verändert
