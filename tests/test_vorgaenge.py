from datetime import datetime

from momo.antworten import Antwort
from momo.vorgaenge import ERLEDIGT, JA, NEIN, ZEITZONE, Vorgaenge, akte_von, erinnerung_text, ueberblick_text

from test_sprechen import _bote


def uhr(tag, stunde=10):
    return lambda: datetime.fromisoformat(f"{tag}T{stunde:02d}:00").replace(tzinfo=ZEITZONE).timestamp()


def obj(wert, ausschnitt="x"):
    return {"wert": wert, "seite": 1, "ausschnitt": ausschnitt}


BRIEF = {"absender": obj("Jobcenter Musterstadt"), "aktenzeichen": obj("987D 654321"),
         "handlungsbedarf": obj("Schick die Kontoauszüge"), "fristen": [obj("2026-11-20", "bis zum 20.11.2026")],
         "betraege": [], "verdacht_manipulation": False}


def test_ja_nein_streng():
    for ja in ("Ja", "ja bitte", "Ja, gerne!", "ok", "mach das", "Jaaa"):
        assert JA.match(ja), ja
    for kein in ("Bitte lies mir den Brief vor", "ja aber was heißt das?", "Ok und was jetzt?"):
        assert not JA.match(kein), kein
    assert NEIN.match("Nein danke") and not NEIN.match("Nein, was heißt Anhörung?")
    assert ERLEDIGT.search("Hab ich erledigt") and not ERLEDIGT.search("Ich habe dir ein Foto geschickt")
    assert akte_von("987D 654321") == akte_von("987d-654321")


def test_erinnerungen_nur_bestaetigt_und_ohne_nachholen(tmp_path):
    zeit = {"t": uhr("2026-11-10")()}
    v = Vorgaenge(tmp_path, uhr=lambda: zeit["t"])
    n = v.brief_eintragen("Briefe/a", BRIEF)
    v.frage_merken(n, 0, 501)
    assert v.faellig() == []  # noch nicht bestätigt
    frage = v.frage_zu(501)
    v.setzen(frage, "bestaetigt")
    zeit["t"] = uhr("2026-11-13", 8)()
    assert v.faellig() == []  # 7 Tage vorher, aber vor 9 Uhr
    zeit["t"] = uhr("2026-11-13")()
    (f, stufe), = v.faellig()
    assert stufe == 7
    v.erinnert(f, stufe, 777)
    assert v.faellig() == [] and v.frage_zu(777) == f  # Antwort auf die Erinnerung gehört zur Frist
    zeit["t"] = uhr("2026-11-20")()  # Ausfall: 2-Tage-Erinnerung verpasst → nur noch die von heute
    (f, stufe), = v.faellig()
    assert stufe == 0
    text = erinnerung_text(v.daten["briefe"][0], v.frist(f), 0, datetime(2026, 11, 20).date())
    assert text.startswith("Erinnerung: Heute, am 20. November 2026") and "Kontoauszüge" in text
    v.erinnert(f, 0, None)
    zeit["t"] = uhr("2026-11-21")()
    assert v.faellig() == []


def test_widerspruch_nur_wiedervorlage(tmp_path):
    v = Vorgaenge(tmp_path, uhr=uhr("2026-10-05"))
    v.brief_eintragen("Briefe/b", {"widerspruch": obj("ja", "Widerspruch erhoben werden"), "fristen": []})
    (f,) = v.daten["briefe"][0]["fristen"]
    assert f["art"] == "wiedervorlage" and f["datum"] == "2026-10-26"
    f["status"] = "bestaetigt"
    v.uhr = uhr("2026-10-24")
    assert v.faellig() == []  # Wiedervorlage nur am Tag selbst
    v.uhr = uhr("2026-10-26")
    assert len(v.faellig()) == 1


def test_manipulation_keine_fristen(tmp_path):
    v = Vorgaenge(tmp_path, uhr=uhr("2026-11-10"))
    v.brief_eintragen("Briefe/c", dict(BRIEF, verdacht_manipulation=True))
    assert v.daten["briefe"][0]["fristen"] == []


class Chat:
    def __init__(self):
        self.gesendet, self.id = [], 9

    def send_text(self, text):
        self.gesendet.append(text)
        return type("M", (), {"id": 100 + len(self.gesendet)})()


def test_bote_fragt_bestaetigt_und_zeigt_woche(tmp_path):
    b = _bote(tmp_path)
    b.vorgaenge.uhr = uhr("2026-11-15")
    chat = Chat()
    n = b.vorgaenge.brief_eintragen("Briefe/a", BRIEF)
    b._fristen_fragen(chat, n)
    assert "Soll ich dich an den 20. November 2026 erinnern?" in chat.gesendet[0]
    assert b.antworten_auf("text", "Bitte lies mir den Brief vor", False).text != "Gut. Ich erinnere dich an den 20. November 2026."
    assert b.antworten_auf("text", "Ja", False, zitiert=101).text == "Gut. Ich erinnere dich an den 20. November 2026."
    woche = b.antworten_auf("text", "Was ist diese Woche wichtig?", False).text
    assert "20. November 2026: Frist oder Termin vom Jobcenter Musterstadt. Schick die Kontoauszüge." in woche
    assert (tmp_path / "ablage" / "Fristen.txt").read_text().startswith("Das ist demnächst wichtig:")
    assert b.antworten_auf("text", "erledigt", False).text.startswith("Super")
    assert "keine Frist" in b.antworten_auf("text", "Welche Fristen habe ich?", False).text


def test_erinnern_schickt_in_den_chat(tmp_path):
    b = _bote(tmp_path)
    b.vorgaenge.uhr = uhr("2026-11-15")
    b.vorgaenge.chat_merken(9)
    n = b.vorgaenge.brief_eintragen("Briefe/a", BRIEF)
    b.vorgaenge.frage_merken(n, 0, 1)
    b.vorgaenge.setzen(b.vorgaenge.frage_zu(1), "bestaetigt")
    chat = Chat()
    konto = type("K", (), {"get_chat_by_id": lambda self, i: chat})()
    b._erinnern(konto)
    assert chat.gesendet and chat.gesendet[0].startswith("Erinnerung: In 5 Tagen")
    b._erinnern(konto)
    assert len(chat.gesendet) == 1
