import os
from pathlib import Path

import pytest

from momo.ablage import OrdnerAblage, ablage_waehlen
from momo.antworten import antworten, ist_gruss
from momo.besitzer import Besitzer
from momo.ki import KeineKi, KiNichtVerfuegbar, anbieter_waehlen
from momo.konfig import Konfig
from momo.stimme import Stimme


def test_besitzer_erster_verschluesselter_kontakt(tmp_path):
    b = Besitzer("", tmp_path / "besitzer.json")
    assert b.pruefen(5, "a@x", verschluesselt=False) == (False, False)
    assert b.pruefen(7, "a@x", verschluesselt=True) == (True, True)
    assert b.pruefen(7, "a@x", verschluesselt=True) == (True, False)
    assert b.pruefen(8, "b@x", verschluesselt=True) == (False, False)
    assert Besitzer("", tmp_path / "besitzer.json").kontakt_id == 7  # überlebt Neustart


def test_besitzer_nur_erlaubte_adressen(tmp_path):
    b = Besitzer("Freund@Beispiel.de, zweit@beispiel.de", tmp_path / "b.json")
    assert b.pruefen(3, "fremd@beispiel.de", verschluesselt=True) == (False, False)
    assert b.pruefen(4, "freund@beispiel.de", verschluesselt=True) == (True, True)


def test_konfig_standard_und_fehler(tmp_path):
    k = Konfig.aus_umgebung({"MOMO_DATEN": str(tmp_path)})
    assert k.name == "Momo" and k.vorlesen == "immer" and k.ki == "keine"
    assert k.ablage_ziel == str(tmp_path / "ablage")
    with pytest.raises(ValueError):
        Konfig.aus_umgebung({"MOMO_VORLESEN": "manchmal"})


def test_antworten():
    assert ist_gruss("Hallo!") and ist_gruss(" hallo momo ") and not ist_gruss("Hallo, was steht im Brief?")
    assert "Ich bin Momo" in antworten("text", "Hallo", "Momo", False).text
    assert "Ich bin Momo" in antworten("bild", "", "Momo", True).text  # erste Nachricht = Begrüßung
    assert "Nachricht" in antworten("sonst", "", "Momo", False).text
    assert "Sprachnachricht" in antworten("sprache", "", "Momo", False).text


def test_ki_geruest():
    assert isinstance(anbieter_waehlen("keine", {}), KeineKi)
    with pytest.raises(KiNichtVerfuegbar):
        KeineKi().fragen("a", [])
    with pytest.raises(ValueError):
        anbieter_waehlen("unbekannt", {})


def test_ordner_ablage(tmp_path):
    a = ablage_waehlen("ordner", str(tmp_path))
    a.schreiben("vorgang-1/brief.txt", b"Text")
    assert a.lesen("vorgang-1/brief.txt") == b"Text"
    assert a.liste() == ["vorgang-1/brief.txt"]
    for boese in ("../raus.txt", "/etc/passwd"):
        with pytest.raises(ValueError):
            a.schreiben(boese, b"x")


STIMME = os.environ.get("MOMO_STIMME")


@pytest.mark.skipif(not STIMME or not Path(STIMME).exists(), reason="MOMO_STIMME nicht gesetzt")
def test_stimme_erzeugt_m4a(tmp_path):
    datei = Stimme(Path(STIMME)).sprechen("Hallo, ich bin Momo.", tmp_path)
    assert datei and datei.suffix == ".m4a" and datei.stat().st_size > 1000
    assert list(tmp_path.glob("*.wav")) == []


def test_stimme_ohne_modell(tmp_path):
    assert Stimme(None).sprechen("x", tmp_path) is None


def test_sprechtempo_in_prozent():
    assert Stimme(None).faktor == 1 and Stimme(None).tempo == 1.15
    assert Stimme(None, prozent=150).faktor == 1.5
    assert Stimme(None, prozent=999).faktor == 2.5 and Stimme(None, prozent=10).faktor == 0.5  # gedeckelt
