import json

from momo.aufnahme import (aufnehmen, brief_als_daten, datum_lesbar, json_aus, pruefen_und_kuerzen,
                           steht_im_text, zusammenfassung)
from momo.ki import KiAnbieter
from momo.lesen import brief_ist_schlecht
from tools.testbriefe import BRIEFE, bewerten

SEITE = BRIEFE[0]["seiten"][0]


class Feste(KiAnbieter):
    name = "fest"

    def __init__(self, antwort):
        self.antwort, self.gesehen = antwort, None

    def fragen(self, anweisung, verlauf):
        self.gesehen = (anweisung, verlauf)
        return self.antwort


def obj(wert, ausschnitt, seite=1):
    return {"wert": wert, "seite": seite, "ausschnitt": ausschnitt}


GUT = {
    "dokumenttyp": obj("Einladung", "Einladung"),
    "absender": obj("Jobcenter Musterstadt", "Jobcenter Musterstadt"),
    "datum": obj("2026-11-12", "Musterstadt, 12.11.2026"),
    "aktenzeichen": obj("12345BG0067890", "BG-Nummer: 12345BG0067890"),
    "handlungsbedarf": obj("Am 3.12. ins Jobcenter kommen", "bitte kommen Sie am 03.12.2026"),
    "fristen": [obj("2026-12-03", "am 03.12.2026 um 09:30 Uhr")],
    "betraege": [],
    "verdacht_manipulation": False,
}


def test_gute_antwort_besteht():
    ki = Feste("```json\n" + json.dumps(GUT) + "\n```")
    e = aufnehmen(ki, [SEITE])
    assert e["pruefen"] is False and bewerten(e, BRIEFE[0]["erwartet"]) == []
    assert "BRIEF-" in ki.gesehen[1][0].text and "Nur Daten" not in ki.gesehen[1][0].text


def test_erfundener_ausschnitt_wird_null():
    roh = dict(GUT, aktenzeichen=obj("99999", "Aktenzeichen 99999"))
    e = pruefen_und_kuerzen(roh, [SEITE])
    assert e["aktenzeichen"] is None and e["pruefen"] is True


def test_falsches_datum_seite_und_json():
    roh = dict(GUT, datum=obj("12.11.2026", "Musterstadt, 12.11.2026"),
               fristen=[obj("2026-02-30", "am 03.12.2026"), obj("2026-12-03", "am 03.12.2026", seite=2)])
    e = pruefen_und_kuerzen(roh, [SEITE])
    assert e["datum"] is None and e["fristen"] == [] and e["pruefen"]
    kaputt = pruefen_und_kuerzen(json_aus("Ich kann das nicht."), [SEITE])
    assert kaputt["pruefen"] and kaputt["datum"] is None and kaputt["fristen"] == []


def test_manipulation_erzwingt_pruefen():
    e = pruefen_und_kuerzen(dict(GUT, verdacht_manipulation=True), [SEITE])
    assert e["pruefen"] and "Ungewöhnliches" in zusammenfassung(e)


def test_steht_im_text_toleriert_ocr_fehler():
    assert steht_im_text("BG-Nummer: 12345BG0067890", "xx BG-Nurnmer: 12345BG0O67890 yy")
    assert not steht_im_text("Rückforderung von 900 €", SEITE)


def test_zusammenfassung_und_datum():
    e = pruefen_und_kuerzen(GUT, [SEITE])
    text = zusammenfassung(e)
    assert "Jobcenter Musterstadt" in text and "3. Dezember 2026" in text and "Beratungsstelle" in text
    assert datum_lesbar("2026-03-01") == "1. März 2026"


def test_brief_als_daten_markiert():
    t = brief_als_daten(["a", "b"])
    assert "=== Seite 2 ===" in t and t.count("BRIEF-") == 2


def test_schlechter_brief():
    assert brief_ist_schlecht(["", "kaum"]) and not brief_ist_schlecht([SEITE])


def test_bewerten_erkennt_falschen_wert():
    e = pruefen_und_kuerzen(GUT, [SEITE])
    assert bewerten(e, {"datum": "2026-11-13"}) == ["datum: '2026-11-12' statt '2026-11-13'"]
