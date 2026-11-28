import json

from momo import fakten as fk
from momo.ki import KiAnbieter

from test_sprechen import _bote


class Merker(KiAnbieter):
    name = "merker"

    def __init__(self, eintraege):
        self.eintraege = eintraege

    def fragen(self, anweisung, verlauf):
        return json.dumps({"eintraege": self.eintraege})


def test_nur_gesagte_werte():
    ki = Merker([{"bezeichnung": "Versichertennummer", "wert": "A123456789"},
                 {"bezeichnung": "IBAN", "wert": "DE00 1234"}])  # IBAN wurde nicht gesagt
    assert fk.aus_satz(ki, "Merk dir, meine Versichertennummer ist A 123 456 789") == [("Versichertennummer", "A123456789")]


def test_merken_fragen_vergessen(tmp_path):
    b = _bote(tmp_path)
    b.gespraech.ki = Merker([{"bezeichnung": "Versichertennummer", "wert": "A123456789"},
                             {"bezeichnung": "Geburtsdatum", "wert": "3. Mai 1980"}])
    a = b.antworten_auf("text", "Merk dir: meine Versichertennummer ist A123456789 und ich bin am 3. Mai 1980 geboren",
                        False)
    assert "Versichertennummer: A123456789" in a.text and "A, eins, zwei, drei" in a.sprechtext
    assert b.fakten.wert("geburtsdatum") == "3. Mai 1980"
    a = b.antworten_auf("text", "Was ist noch mal meine Versichertennummer?", False)
    assert a.text == "Versichertennummer: A123456789"
    assert "Geburtsdatum: 3. Mai 1980" in b.antworten_auf("text", "Was weißt du über mich?", False).text
    assert "vergessen" in b.antworten_auf("text", "Vergiss meine Versichertennummer", False).text
    assert b.fakten.wert("Versichertennummer") is None


def test_absender_kommt_aus_fakten(tmp_path):
    b = _bote(tmp_path)
    b.entwuerfe.absender = ["Max Beispiel", "Lindenweg 7", "12345 Musterstadt"]
    assert b.fakten.wert("Name") == "Max Beispiel" and b.fakten.wert("PLZ und Ort") == "12345 Musterstadt"
    assert b.entwuerfe.absender == ["Max Beispiel", "Lindenweg 7", "12345 Musterstadt"]
    assert "fakten.json" in __import__("momo.datenschutz", fromlist=["x"]).PERSONENDATEIEN
