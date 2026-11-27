import os
from pathlib import Path

import pytest

from momo import saetze
from momo.antworten import KEIN_BRIEF, SPRACHE_AN, SPRACHE_AUS, Antwort
from momo.bote import Bote
from momo.briefe import Briefablage
from momo.ablage import OrdnerAblage
from momo.einstellungen import Einstellungen
from momo.gespraech import Gespraech
from momo.ki import KeineKi
from momo.konfig import Konfig
from momo.stimme import Stimme


@pytest.mark.parametrize("satz, wunsch", [
    ("Lies mir den Brief noch mal vor", saetze.NOCHMAL),
    ("kannst du mir das nochmal vorlesen", saetze.NOCHMAL),
    ("Was stand noch mal in dem Brief?", saetze.NOCHMAL),
    ("Antworte immer mit Sprache", saetze.SPRACHE_AN),
    ("Sprich wieder mit mir per Sprachnachricht", saetze.SPRACHE_AN),
    ("Bitte nur mit Text antworten", saetze.SPRACHE_AUS),
    ("Keine Sprachnachrichten mehr bitte", saetze.SPRACHE_AUS),
    ("nicht mehr vorlesen", saetze.SPRACHE_AUS),
    ("Was wollte das Jobcenter von mir?", None),
    ("Was heißt Anhörung?", None),
    ("Muss ich da hingehen?", None),
])
def test_saetze(satz, wunsch):
    assert saetze.erkennen(satz) == wunsch


def _bote(tmp_path):
    k = Konfig.aus_umgebung({"MOMO_DATEN": str(tmp_path)})
    g = Gespraech(KeineKi(), "Momo", tmp_path / "verlauf.json")
    return Bote(k, Stimme(None), g, Briefablage(OrdnerAblage(str(tmp_path / "ablage"))))


def test_wuensche_ohne_ki(tmp_path):
    b = _bote(tmp_path)
    assert b.antworten_auf("text", "Lies mir den Brief vor", False).text == KEIN_BRIEF
    b.einstellungen.brief_merken(Antwort("Brief-Text", sprechtext="Brief zum Hören"))
    a = b.antworten_auf("text", "Lies mir den Brief noch mal vor", False)
    assert a.text == "Brief-Text" and a.zum_vorlesen == "Brief zum Hören" and a.immer_vorlesen
    assert b.antworten_auf("text", "Antworte nur mit Text", False).text == SPRACHE_AUS
    assert Einstellungen(tmp_path, "immer").vorlesen == "nie"  # überlebt Neustart
    assert b.antworten_auf("text", "Antworte wieder mit Sprache", False).text == SPRACHE_AN
    assert b.einstellungen.vorlesen == "immer"


class FalschesOhr:
    def __init__(self, text):
        self.text = text

    def umschreiben(self, datei):
        return self.text


def test_sprachnachricht_wird_zur_frage(tmp_path):
    b = _bote(tmp_path)
    b.ohr = FalschesOhr("Antworte nur mit Text")
    a = b._zuhoeren(tmp_path / "x.m4a")
    assert a.text.startswith("Ich habe verstanden: „Antworte nur mit Text“") and a.zum_vorlesen == SPRACHE_AUS
    b.ohr = FalschesOhr("")
    assert "nicht verstanden" in b._zuhoeren(tmp_path / "x.m4a").text


@pytest.mark.skipif(not os.environ.get("MOMO_WHISPER_TEST"), reason="echter Whisper-Test nur im Container")
def test_whisper_echt(tmp_path):
    from momo.zuhoeren import Ohr
    stimme = Stimme(Path(os.environ.get("MOMO_STIMME", "/app/stimmen/de_DE-thorsten-medium.onnx")))
    datei = stimme.sprechen("Was wollte das Jobcenter von mir?", tmp_path)
    text = Ohr(os.environ.get("MOMO_WHISPER", "small"), Path("/app/whisper")).umschreiben(datei)
    assert "jobcenter" in text.lower()
