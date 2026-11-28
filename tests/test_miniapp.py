import zipfile

from momo import miniapp, saetze

from test_sprechen import _bote
from test_vorgaenge import BRIEF, uhr


def test_xdc_enthaelt_app_und_schriften(tmp_path):
    datei = miniapp.xdc_bauen(tmp_path / "momo.xdc")
    namen = zipfile.ZipFile(datei).namelist()
    for n in ("index.html", "manifest.toml", "icon.png", "schriften/opendyslexic-400.woff2",
              "schriften/LIZENZ-lexend.txt"):
        assert n in namen
    html = zipfile.ZipFile(datei).read("index.html").decode()
    assert "http://" not in html and "https://" not in html  # lädt nichts aus dem Netz


def test_stand_und_bitten(tmp_path):
    b = _bote(tmp_path)
    b.vorgaenge.uhr = uhr("2026-11-15")
    n = b.vorgaenge.brief_eintragen("Briefe/Amt und Behörde/Jobcenter Musterstadt/2026-11-02 Unterlagen",
                                    dict(BRIEF, kategorie="Amt und Behörde"))
    st = miniapp.stand(b.vorgaenge)
    assert st["briefe"][n]["ordner"] == "Amt und Behörde › Jobcenter Musterstadt"
    assert st["fristen"] == [{"brief": 0, "frist": 0, "datum": "2026-11-20", "art": "frist", "status": "vorgeschlagen"}]
    assert "erklaerung" not in st["briefe"][0]
    roh = [{"payload": st, "serial": 1}, {"payload": {"typ": "bitte", "was": "erledigt", "brief": 0, "frist": 0}, "serial": 2},
           {"payload": {"typ": "bitte", "was": "loeschen", "brief": 0}, "serial": 3},
           {"payload": {"typ": "bitte", "was": "vorlesen", "brief": True}, "serial": 4}]
    assert miniapp.bitten(roh) == [{"was": "erledigt", "brief": 0, "frist": 0}]


def test_app_saetze():
    assert saetze.erkennen("Zeig mir meine Briefe") == saetze.APP
    assert saetze.erkennen("Schick mir die Übersicht") == saetze.APP
    assert saetze.erkennen("Was ist diese Woche wichtig?") == saetze.WOCHE


class Nachricht:
    def __init__(self, updates, chat):
        self.updates, self.chat, self.gesendet = updates, chat, []

    def get_webxdc_status_updates(self, serial):
        return [u for u in self.updates if u["serial"] > serial]

    def get_snapshot(self):
        return type("S", (), {"chat": self.chat})()

    def send_webxdc_status_update(self, update, beschreibung):
        self.gesendet.append(update)


def test_knoepfe_aus_der_app(tmp_path):
    from test_vorgaenge import Chat

    b = _bote(tmp_path)
    b.vorgaenge.uhr = uhr("2026-11-15")
    n = b.vorgaenge.brief_eintragen("Briefe/a", BRIEF)
    b.vorgaenge.erklaerung_merken(n, "Erklärung", "Zum Hören")
    chat = Chat()
    nachricht = Nachricht([
        {"serial": 1, "payload": {"typ": "stand"}},
        {"serial": 2, "payload": {"typ": "bitte", "was": "bestaetigen", "brief": 0, "frist": 0}},
        {"serial": 3, "payload": {"typ": "bitte", "was": "vorlesen", "brief": 0}},
        {"serial": 4, "payload": {"typ": "bitte", "was": "antworten", "brief": 0}},
    ], chat)
    b._konto = type("K", (), {"get_message_by_id": lambda self, i: nachricht})()
    b._app_schreiben({"nachricht": 77, "serial": 0})
    b._bei_app(type("E", (), {"msg_id": 77})())
    assert b.vorgaenge.daten["briefe"][0]["fristen"][0]["status"] == "bestaetigt"
    assert chat.gesendet[0] == "Erklärung"  # Vorlesen (ohne Stimme im Test nur Text)
    assert "Namen und deine Adresse" in chat.gesendet[1]  # Antworten startet beim Absender
    assert nachricht.gesendet and nachricht.gesendet[-1]["payload"]["fristen"][0]["status"] == "bestaetigt"
    b._bei_app(type("E", (), {"msg_id": 77})())  # nichts doppelt
    assert len(chat.gesendet) == 2
    b._bei_app(type("E", (), {"msg_id": 5})())  # fremde Nachricht
    assert len(chat.gesendet) == 2
