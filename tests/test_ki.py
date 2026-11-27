import json
import stat

import httpx
import pytest

from momo.gespraech import FEHLER, Gespraech, fuer_vorlesen
from momo.ki import KiAnbieter, KiFehler, Nachricht, anbieter_waehlen, einordnen
from momo.ki.claude_abo import ClaudeAbo, verlauf_als_text
from momo.ki.mistral import Mistral


def test_anbieter_waehlen():
    assert anbieter_waehlen("mistral", {"MISTRAL_API_KEY": "x"}).modell == "mistral-medium-latest"
    assert anbieter_waehlen("claude-abo", {"MOMO_KI_MODELL": "opus"}).modell == "opus"
    with pytest.raises(ValueError):
        anbieter_waehlen("chatgpt", {})


def test_einordnen():
    assert einordnen("HTTP 401 Unauthorized") == "anmeldung"
    assert einordnen("429 rate limit") == "limit"
    assert einordnen("503 overloaded") == "voruebergehend"


def _mistral(antwort: httpx.Response, gesehen: list):
    def behandeln(anfrage: httpx.Request) -> httpx.Response:
        gesehen.append(anfrage)
        return antwort

    return Mistral("geheim", "mistral-small-latest", transport=httpx.MockTransport(behandeln))


def test_mistral_erfolg():
    gesehen = []
    ki = _mistral(httpx.Response(200, json={"choices": [{"message": {"content": " Hallo! "}}],
                                            "usage": {"prompt_tokens": 5, "completion_tokens": 2}}), gesehen)
    assert ki.fragen("Vorgabe", [Nachricht("nutzer", "Hi"), Nachricht("momo", "Hallo"),
                                Nachricht("nutzer", "Was ist ein Bescheid?")]) == "Hallo!"
    körper = json.loads(gesehen[0].content)
    assert gesehen[0].headers["authorization"] == "Bearer geheim"
    assert [m["role"] for m in körper["messages"]] == ["system", "user", "assistant", "user"]
    assert gesehen[0].url.host == "api.mistral.ai"


def test_mistral_fehler():
    with pytest.raises(KiFehler) as e:
        _mistral(httpx.Response(401, text="Unauthorized"), []).fragen("v", [Nachricht("nutzer", "x")])
    assert e.value.art == "anmeldung"
    with pytest.raises(KiFehler) as e:
        Mistral("", "m").fragen("v", [Nachricht("nutzer", "x")])
    assert e.value.art == "anmeldung"


def _falsches_claude(tmp_path, ausgabe: dict, code: int = 0):
    skript = tmp_path / "claude"
    skript.write_text(f"#!/bin/sh\ncat > {tmp_path}/eingabe.txt\nprintf '%s' '{json.dumps(ausgabe)}'\nexit {code}\n")
    skript.chmod(skript.stat().st_mode | stat.S_IEXEC)
    return ClaudeAbo("tok", "sonnet", befehl=str(skript), heim=str(tmp_path / "heim"))


def test_claude_abo_erfolg(tmp_path):
    ki = _falsches_claude(tmp_path, {"result": "Ein Bescheid ist ein Brief vom Amt.", "usage": {}})
    assert ki.fragen("v", [Nachricht("nutzer", "Was ist ein Bescheid?")]) == "Ein Bescheid ist ein Brief vom Amt."
    assert (tmp_path / "eingabe.txt").read_text() == "Was ist ein Bescheid?"
    assert "--tools" in ki._befehlszeile("v") and ki._befehlszeile("v")[ki._befehlszeile("v").index("--tools") + 1] == ""


def test_claude_abo_fehler(tmp_path):
    ki = _falsches_claude(tmp_path, {"result": "Usage limit reached", "is_error": True}, code=1)
    with pytest.raises(KiFehler) as e:
        ki.fragen("v", [Nachricht("nutzer", "x")])
    assert e.value.art == "limit"
    with pytest.raises(KiFehler):
        ClaudeAbo("", "sonnet").fragen("v", [Nachricht("nutzer", "x")])


def test_verlauf_als_text():
    t = verlauf_als_text([Nachricht("nutzer", "A"), Nachricht("momo", "B"), Nachricht("nutzer", "C")])
    assert "Nutzer: A" in t and "Momo: B" in t and t.endswith("C")


class Merker(KiAnbieter):
    name = "merker"

    def __init__(self, antwort="**Ein Bescheid** ist ein Brief.", fehler=None):
        self.antwort, self.fehler, self.aufrufe = antwort, fehler, []

    def fragen(self, anweisung, verlauf):
        self.aufrufe.append((anweisung, list(verlauf)))
        if self.fehler:
            raise KiFehler(self.fehler, "kaputt")
        return self.antwort


def test_gespraech_nutzt_ki_und_merkt_verlauf(tmp_path):
    ki = Merker()
    g = Gespraech(ki, "Momo", tmp_path / "verlauf.json")
    assert "Ich bin Momo" in g.antworten("text", "Hallo", True).text  # Begrüßung ohne KI
    assert ki.aufrufe == []
    a = g.antworten("text", "Muss ich da hingehen?", False)
    assert a.text == "Ein Bescheid ist ein Brief."
    anweisung, verlauf = ki.aufrufe[0]
    assert "Leichte Sprache" in anweisung and "Momo" in anweisung
    assert verlauf[-1] == Nachricht("nutzer", "Muss ich da hingehen?")
    assert len(Gespraech(ki, "Momo", tmp_path / "verlauf.json").verlauf) == 4  # überlebt Neustart


def test_gespraech_fehler_freundlich(tmp_path):
    g = Gespraech(Merker(fehler="limit"), "Momo", tmp_path / "v.json")
    assert g.antworten("text", "Frage", False).text == FEHLER["limit"]


def test_fuer_vorlesen():
    assert fuer_vorlesen("**Wichtig:** du musst\n- das tun\n# Titel") == "Wichtig: du musst\ndas tun\n Titel"
