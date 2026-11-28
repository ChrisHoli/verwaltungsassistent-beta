import json
import stat
from types import SimpleNamespace

import anthropic
import httpx
import pytest

from momo.ki import ALLE_KIS, KiFehler, Nachricht, anbieter_waehlen
from momo.ki.anthropic_api import AnthropicApi
from momo.ki.befehl import Befehl
from momo.ki.offen import OpenAiKompatibel

FRAGE = [Nachricht("nutzer", "Hallo")]


def test_jede_ki_waehlbar():
    u = {"MOMO_KI_SCHLUESSEL": "k", "MOMO_KI_MODELL": "m", "MOMO_KI_ADRESSE": "http://server:8000/v1",
         "MOMO_KI_BEFEHL": "cat"}
    for name in ALLE_KIS:
        assert anbieter_waehlen(name, u).name in (name, "keine")
    assert anbieter_waehlen("gemini", {"GEMINI_API_KEY": "g", "MOMO_KI_MODELL": "x"}).schluessel == "g"
    assert anbieter_waehlen("ollama", {"MOMO_KI_MODELL": "llama3"}).adresse == "http://localhost:11434/v1"
    assert anbieter_waehlen("anthropic", {"ANTHROPIC_API_KEY": "a"}).modell == "claude-opus-5-5"
    with pytest.raises(ValueError):
        anbieter_waehlen("openai-kompatibel", {})  # ohne Adresse geht es nicht


def _offen(name, status=200, json_antwort=None, **kw):
    gesehen = []

    def behandeln(anfrage):
        gesehen.append(anfrage)
        return httpx.Response(status, json=json_antwort or {"choices": [{"message": {"content": " Ja "}}]})

    return OpenAiKompatibel(name, kw.pop("adresse", "http://x/v1"), transport=httpx.MockTransport(behandeln), **kw), gesehen


def test_offen_ohne_schluessel_und_laengenfeld():
    ki, gesehen = _offen("ollama", schluessel="", modell="llama3", schluessel_noetig=False)
    assert ki.fragen("v", FRAGE) == "Ja"
    assert "authorization" not in gesehen[0].headers
    k = json.loads(gesehen[0].content)
    assert k["max_tokens"] == 1500 and "temperature" not in k and k["messages"][0]["role"] == "system"
    ki, gesehen = _offen("openai", schluessel="s", modell="m", laengen_feld="max_completion_tokens")
    ki.fragen("v", FRAGE)
    assert "max_completion_tokens" in json.loads(gesehen[0].content)


def test_offen_fehler():
    with pytest.raises(KiFehler) as f:
        _offen("openai", schluessel="", modell="m")[0].fragen("v", FRAGE)
    assert f.value.art == "anmeldung"
    with pytest.raises(KiFehler) as f:
        _offen("gemini", schluessel="s", modell="")[0].fragen("v", FRAGE)
    assert f.value.art == "anmeldung"
    with pytest.raises(KiFehler) as f:
        _offen("groq", status=429, json_antwort={"error": "rate limit"}, schluessel="s", modell="m")[0].fragen("v", FRAGE)
    assert f.value.art == "limit"
    with pytest.raises(KiFehler) as f:
        _offen("groq", json_antwort={"foo": 1}, schluessel="s", modell="m")[0].fragen("v", FRAGE)
    assert f.value.art == "sonstig"


class FalscherClient:
    def __init__(self, antwort=None, fehler=None):
        self.antwort, self.fehler, self.aufrufe = antwort, fehler, []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.aufrufe.append(kw)
        if self.fehler:
            raise self.fehler
        return self.antwort


def _antwort(stop="end_turn", text="Hallo"):
    return SimpleNamespace(stop_reason=stop, model="claude-opus-5-5",
                           usage=SimpleNamespace(input_tokens=3, output_tokens=1),
                           content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)])


def test_anthropic():
    c = FalscherClient(_antwort())
    assert AnthropicApi("k", "claude-opus-5-5", client=c).fragen("Vorgabe", FRAGE) == "Hallo"
    kw = c.aufrufe[0]
    assert kw["system"] == "Vorgabe" and kw["fallbacks"] == "default" and "temperature" not in kw
    with pytest.raises(KiFehler):
        AnthropicApi("k", "m", client=FalscherClient(_antwort(stop="refusal"))).fragen("v", FRAGE)
    anfrage = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    fehler = anthropic.RateLimitError("zu viel", response=httpx.Response(429, request=anfrage), body=None)
    with pytest.raises(KiFehler) as f:
        AnthropicApi("k", "m", client=FalscherClient(fehler=fehler)).fragen("v", FRAGE)
    assert f.value.art == "limit"
    with pytest.raises(KiFehler) as f:
        AnthropicApi("", "m").fragen("v", FRAGE)
    assert f.value.art == "anmeldung"


def test_befehl(tmp_path):
    skript = tmp_path / "ki.sh"
    skript.write_text("#!/bin/sh\nread erste\necho \"Antwort auf: $erste\"\n")
    skript.chmod(skript.stat().st_mode | stat.S_IEXEC)
    assert Befehl(str(skript)).fragen("Anweisung", FRAGE) == "Antwort auf: Anweisung"
    with pytest.raises(KiFehler):
        Befehl("gibt-es-nicht-123").fragen("v", FRAGE)
