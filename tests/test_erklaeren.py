from momo.aufnahme import einfacher_satz, pruefen_und_kuerzen
from momo.erklaeren import betrag_sprechbar, erklaerung, zeichenweise
from momo.gespraech import Gespraech
from momo.ki import KeineKi
from momo.woerter import frage_nach_wort, im_brief
from tools.testbriefe import BRIEFE

from test_aufnahme import GUT, SEITE, obj


def test_drei_fragen_und_sprechtext():
    roh = dict(GUT, was_ist_das="Das Jobcenter lädt dich zu einem Gespräch ein.",
               handlungsbedarf=obj("Geh zum Termin ins Jobcenter", "bitte kommen Sie am 03.12.2026"))
    a = erklaerung(pruefen_und_kuerzen(roh, [SEITE]), [SEITE])
    for teil in ("Was ist das?\nDas Jobcenter lädt dich", "Was musst du tun?\nGeh zum Termin ins Jobcenter.",
                 "Bis wann?\nWichtig ist der 3. Dezember 2026.", "Aktenzeichen: 12345BG0067890", "Beratungsstelle"):
        assert teil in a.text
    assert "eins, zwei, drei, vier, fünf, Be, Ge, null" in a.sprechtext
    assert "12345BG" not in a.sprechtext
    assert "„Leistungsminderung“ heißt" in a.text  # „gemindert“ steht im Brief


def test_satz_mit_zahlen_wird_verworfen():
    assert einfacher_satz("Du sollst 500 € zahlen.") is None
    assert einfacher_satz("Siehe www.beispiel.de") is None
    assert einfacher_satz("Das ist eine Mahnung") == "Das ist eine Mahnung."
    assert einfacher_satz({"wert": "Das ist eine Mahnung.", "seite": 1}) == "Das ist eine Mahnung."
    e = pruefen_und_kuerzen(dict(GUT, was_ist_das="Am 3.12. Termin"), [SEITE])
    assert e["was_ist_das"] is None
    assert "Ein Brief von Jobcenter Musterstadt. Es ist: Einladung." in erklaerung(e, [SEITE]).text


def test_manipulation_ohne_ki_saetze():
    seite = BRIEFE[3]["seiten"][0]
    roh = {"verdacht_manipulation": True, "was_ist_das": "Du musst sofort zahlen.",
           "handlungsbedarf": obj("Überweise das Geld", "überweisen muss")}
    a = erklaerung(pruefen_und_kuerzen(roh, [seite]), [seite])
    assert "sofort zahlen" not in a.text and "Überweise" not in a.text
    assert "Mach bitte nichts" in a.text and "Ungewöhnliches" in a.text


def test_widerspruch_ohne_datum():
    seiten = BRIEFE[2]["seiten"]
    roh = {"widerspruch": obj("ja", "innerhalb eines Monats nach Bekanntgabe", 2)}
    a = erklaerung(pruefen_und_kuerzen(roh, seiten), seiten)
    assert "meistens einen Monat" in a.text and "Beratungsstelle" in a.text


def test_sprechhilfen():
    assert zeichenweise("WG-2026 4711") == "We, Ge, Strich, zwei, null, zwei, sechs. vier, sieben, eins, eins"
    assert betrag_sprechbar("1.087,40 €") == "1087 Euro und 40 Cent"
    assert betrag_sprechbar("563,00 €") == "563 Euro"
    assert betrag_sprechbar("ungefähr 5") == "ungefähr 5"


def test_woerterliste():
    assert [w for w, _ in im_brief(BRIEFE[5]["seiten"][0])] == ["Anhörung", "Erstattung"]
    assert frage_nach_wort("Was heißt Mitwirkungspflicht?")[0] == "Mitwirkungspflicht"
    assert frage_nach_wort("was bedeutet eigentlich bescheid") [0] == "Bescheid"
    assert frage_nach_wort("Ich habe eine Anhörung bekommen") is None


def test_gespraech_beantwortet_wortfrage_ohne_ki(tmp_path):
    g = Gespraech(KeineKi(), "Momo", tmp_path / "v.json")
    a = g.antworten("text", "Was heißt Anhörung?", False)
    assert a.text.startswith("„Anhörung“ heißt:")


def test_momo_prueft_fristen_selbst():
    from momo.aufnahme import fristdaten_im_text, fristdauer_im_text
    from momo.lesen import brief_ist_schlecht
    wohngeld = BRIEFE[8]["seiten"]
    assert fristdaten_im_text(wohngeld) == {"2026-11-15", "2026-11-10"}
    assert fristdaten_im_text(BRIEFE[2]["seiten"]) == set()  # Zeitraum „vom … bis …“ ist keine Frist
    assert fristdaten_im_text(BRIEFE[9]["seiten"]) == {"2026-12-02"}  # „Zeitraum 01.07. bis 30.09.“ auch nicht
    e = pruefen_und_kuerzen({"datum": obj("2026-11-01", "Musterstadt, 01.11.2026")}, wohngeld)
    assert e["pruefen"] and "kein Tag" not in erklaerung(e, wohngeld).text
    kk = BRIEFE[4]["seiten"]
    assert fristdauer_im_text(kk) == "innerhalb von 14 Tagen nach Erhalt dieses Schreibens"
    assert "„innerhalb von 14 Tagen" in erklaerung(pruefen_und_kuerzen({}, kk), kk).text
    assert brief_ist_schlecht(BRIEFE[6]["seiten"])
    assert not any(brief_ist_schlecht(b["seiten"]) for i, b in enumerate(BRIEFE) if i != 6)
