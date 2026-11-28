import json

from momo import antwortbrief as ab
from momo.ki import KiAnbieter
from tools.testbriefe import BRIEFE

from test_sprechen import _bote
from test_vorgaenge import BRIEF, Chat, uhr

SEITE = BRIEFE[1]["seiten"][0]  # Mitwirkung Unterlagen


class Schreiber(KiAnbieter):
    name = "schreiber"

    def __init__(self):
        self.aufrufe = []

    def fragen(self, anweisung, verlauf):
        self.aufrufe.append((anweisung, verlauf[-1].text))
        aenderung = "Bisheriger Brieftext" in verlauf[-1].text
        return json.dumps({
            "betreff": "Fehlende Unterlagen",
            "text": ("Sehr gern schicke ich Ihnen die Kontoauszüge." if aenderung else
                     "ich schicke Ihnen die Kontoauszüge bis zum 20.11.2026.\n\nDie Nebenkostenabrechnung folgt."),
            "anschrift": ["Jobcenter Musterstadt"],
            "rueckfrage": None,
            "kurz": "Du schreibst, dass du die Unterlagen schickst.",
        })


def test_absender_lesen():
    assert ab.absender_lesen("Max Beispiel, Lindenweg 7, 12345 Musterstadt") == \
        ["Max Beispiel", "Lindenweg 7", "12345 Musterstadt"]
    assert ab.absender_lesen("Ich heiße Max Beispiel Lindenweg 7 12345 Musterstadt") == \
        ["Max Beispiel", "Lindenweg 7", "12345 Musterstadt"]
    assert ab.absender_lesen("Max Beispiel") is None


def test_briefwunsch():
    assert ab.ist_briefwunsch("Ich will dem Jobcenter antworten")
    assert ab.ist_briefwunsch("Schreib dem Jobcenter, dass ich die Unterlagen nächste Woche schicke")
    assert ab.ist_briefwunsch("Ich möchte Widerspruch einlegen")
    assert not ab.ist_briefwunsch("Was wollte das Jobcenter von mir?")


def test_anschrift_nur_wenn_im_brief():
    e = ab._ergebnis({"text": "Hallo", "anschrift": ["Jobcenter Musterstadt", "Erfundene Straße 9"]}, SEITE,
                     [SEITE], ["Jobcenter Musterstadt"])
    assert not e["anschrift_sicher"] and e["anschrift"] == ["Jobcenter Musterstadt"]
    e = ab._ergebnis({"text": "Ich zahle 500 Euro."}, SEITE, ["ich zahle", SEITE], [])
    assert e["zahlen_pruefen"]


def test_ganzer_ablauf(tmp_path):
    b = _bote(tmp_path)
    b.gespraech.ki = Schreiber()
    b.vorgaenge.uhr = uhr("2026-11-15")
    n = b.vorgaenge.brief_eintragen("Briefe/a", BRIEF)
    b.briefe.ablage.schreiben("Briefe/a/text/seite-01.txt", SEITE.encode())
    chat = Chat()
    b._chat = chat

    a = b.antworten_auf("text", "Schreib dem Jobcenter, dass ich die Unterlagen nächste Woche schicke", False)
    assert a.text == ab.ABSENDER_FRAGE
    a = b.antworten_auf("text", "Max Beispiel, Lindenweg 7, 12345 Musterstadt", False)
    assert a.vorlage and "Hier ist dein Brief:" in a.text and "Aktenzeichen: 987D 654321" in a.text
    assert "Musterstadt, " in a.text and "Max Beispiel" in a.text and "passt" in a.zum_vorlesen
    assert "nächste Woche" in b.gespraech.ki.aufrufe[0][1]  # Wunsch kommt bei der KI an, als Daten markiert
    assert "<<<WUNSCH-" in b.gespraech.ki.aufrufe[0][1]
    vorlage = b._senden(chat, a)  # merkt die Nachrichten-ID
    assert b.entwuerfe.entwurf().vorlage_id == vorlage.id

    assert "Antworte bitte direkt auf den Brief" in b.antworten_auf("text", "passt", False).text
    a = b.antworten_auf("text", "Schreib bitte freundlicher", False, zitiert=vorlage.id)
    assert "Sehr gern" in a.text
    neue = b._senden(chat, a)
    assert "direkt auf den Brief" in b.antworten_auf("text", "passt", False, zitiert=vorlage.id).text  # alte Fassung
    fertig = b.antworten_auf("text", "Passt!", False, zitiert=neue.id)
    assert fertig.datei and fertig.datei.endswith(".pdf") and "verschicke nichts" in fertig.text
    pdfs = [p for p in b.briefe.ablage.liste("Briefe/a/antwortbriefe")]
    assert pdfs and b.briefe.ablage.lesen(pdfs[0])[:4] == b"%PDF"
    assert b.entwuerfe.zustand() == {}


def test_kein_brief_und_abbrechen(tmp_path):
    b = _bote(tmp_path)
    assert "zuerst ein Foto" in b.antworten_auf("text", "Ich will dem Jobcenter antworten", False).text
    b.vorgaenge.brief_eintragen("Briefe/a", BRIEF)
    b.entwuerfe.absender = ["Max", "Weg 1", "12345 Ort"]
    assert "was drinstehen soll" in b.antworten_auf("text", "Ich will dem Jobcenter antworten", False).text
    assert "keinen Brief" in b.antworten_auf("text", "abbrechen", False).text
