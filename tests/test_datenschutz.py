from momo import datenschutz
from momo.konfig import Konfig

from test_sprechen import _bote
from test_vorgaenge import BRIEF, Chat, uhr


def test_hinweis_passt_zur_einstellung():
    t = datenschutz.hinweis("mistral", "rclone", "Christian", 30)
    assert "Frankreich" in t and "EU" in t and "von Christian" in t and "nach 30 Tagen" in t
    assert "Fotos schicke ich nicht" in t and "Lösch alles von mir" in t
    assert "Nichts geht nach draußen" in datenschutz.hinweis("ollama", "ordner", "", 14)
    assert "USA" in datenschutz.hinweis("claude-abo", "rclone", "", 30)
    assert "ohne KI" in datenschutz.hinweis("keine", "ordner", "", 30)


def test_konfig_aufheben():
    assert Konfig.aus_umgebung({"MOMO_AUFHEBEN_TAGE": "14"}).aufheben_tage == 14
    assert Konfig.aus_umgebung({}).aufheben_tage == 30


def test_alles_loeschen_nur_mit_zitat(tmp_path):
    b = _bote(tmp_path)
    b.vorgaenge.uhr = uhr("2026-11-15")
    b.vorgaenge.brief_eintragen("Briefe/Gesundheit/Praxis/2026-11-01 Rechnung", BRIEF)
    b.briefe.ablage.schreiben("Briefe/Gesundheit/Praxis/2026-11-01 Rechnung/original/seite-01.jpg", b"x")
    b.briefe.ablage.schreiben("Fristen.txt", b"x")
    b.entwuerfe.absender = ["Max", "Weg 1", "12345 Ort"]
    chat = Chat()

    assert "Ich weiß nicht" in b.antworten_auf("text", "Ja, löschen", False).text
    frage = b.antworten_auf("text", "Lösch bitte alles von mir", False)
    assert frage.text == datenschutz.LOESCH_FRAGE and frage.merken_als == "loesch_frage"
    nachricht = b._senden(chat, frage)
    assert "direkt auf meine Frage" in b.antworten_auf("text", "Ja, löschen", False).text  # ohne Zitat
    assert b.vorgaenge.daten["briefe"]  # noch nichts gelöscht
    fertig = b.antworten_auf("text", "Ja, löschen", False, zitiert=nachricht.id)
    assert fertig.text == datenschutz.LOESCH_FERTIG
    assert b.vorgaenge.daten["briefe"] == [] and b.briefe.ablage.liste("Briefe") == []
    assert not (tmp_path / "ablage" / "Fristen.txt").exists()
    assert not (tmp_path / "absender.json").exists() and b.gespraech.verlauf == []


def test_hinweis_einmal_und_auf_frage(tmp_path):
    b = _bote(tmp_path)
    chat = Chat()
    b._datenschutz_einmal(chat)
    b._datenschutz_einmal(chat)
    assert len(chat.gesendet) == 1 and chat.gesendet[0].startswith("Kurz zu deinen Daten")
    assert b.antworten_auf("text", "Was passiert mit meinen Daten?", False).text.startswith("Kurz zu deinen Daten")
