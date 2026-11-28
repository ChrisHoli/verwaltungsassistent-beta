"""Jede KI mit OpenAI-kompatibler Schnittstelle (/chat/completions): Mistral, OpenAI, Gemini, Ollama, OpenRouter,
Groq, LM Studio, vLLM, IONOS, Scaleway und eigene Server. Nur die Adresse, der Schlüssel und das Modell ändern sich."""

import logging

import httpx

from . import KiAnbieter, KiFehler, Nachricht, einordnen

log = logging.getLogger(__name__)


class OpenAiKompatibel(KiAnbieter):
    def __init__(self, name: str, adresse: str, schluessel: str, modell: str, schluessel_noetig: bool = True,
                 temperatur: float | None = None, laengen_feld: str = "max_tokens", zeitlimit: float = 120,
                 transport: httpx.BaseTransport | None = None):
        self.name = name
        self.adresse = adresse.rstrip("/")
        self.schluessel = schluessel
        self.modell = modell
        self.schluessel_noetig = schluessel_noetig
        self.temperatur = temperatur
        self.laengen_feld = laengen_feld  # OpenAIs neuere Modelle wollen max_completion_tokens
        self._client = httpx.Client(timeout=zeitlimit, transport=transport)

    def fragen(self, anweisung: str, verlauf: list[Nachricht]) -> str:
        if self.schluessel_noetig and not self.schluessel:
            raise KiFehler("anmeldung", f"Schlüssel für {self.name} fehlt (MOMO_KI_SCHLUESSEL)")
        if not self.modell:
            raise KiFehler("anmeldung", f"Modell für {self.name} fehlt (MOMO_KI_MODELL)")
        nachrichten = [{"role": "system", "content": anweisung}] + [
            {"role": "user" if n.rolle == "nutzer" else "assistant", "content": n.text} for n in verlauf
        ]
        koerper = {"model": self.modell, "messages": nachrichten, self.laengen_feld: 1500}
        if self.temperatur is not None:
            koerper["temperature"] = self.temperatur
        kopf = {"Authorization": f"Bearer {self.schluessel}"} if self.schluessel else {}
        try:
            antwort = self._client.post(f"{self.adresse}/chat/completions", headers=kopf, json=koerper)
        except httpx.HTTPError as e:
            raise KiFehler("voruebergehend", f"{self.name} nicht erreichbar: {type(e).__name__}") from None
        if antwort.status_code != 200:
            meldung = f"{antwort.status_code} {antwort.text[:300]}"
            raise KiFehler(einordnen(meldung), meldung)
        try:
            daten = antwort.json()
            text = daten["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError):
            raise KiFehler("sonstig", f"{self.name}: unerwartete Antwort") from None
        nutzung = daten.get("usage") or {}
        log.info("KI %s: Modell=%s, Eingabe=%s, Ausgabe=%s Tokens", self.name, self.modell,
                 nutzung.get("prompt_tokens"), nutzung.get("completion_tokens"))
        return text.strip()
