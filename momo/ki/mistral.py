"""Mistral über die API (EU). Schlüssel aus Mistral Studio, Abrechnung nach Verbrauch."""

import logging

import httpx

from . import KiAnbieter, KiFehler, Nachricht, einordnen

log = logging.getLogger(__name__)


class Mistral(KiAnbieter):
    name = "mistral"

    def __init__(self, schluessel: str, modell: str, adresse: str = "https://api.mistral.ai/v1",
                 zeitlimit: float = 60, transport: httpx.BaseTransport | None = None):
        self.schluessel = schluessel
        self.modell = modell
        self.adresse = adresse.rstrip("/")
        self._client = httpx.Client(timeout=zeitlimit, transport=transport)

    def fragen(self, anweisung: str, verlauf: list[Nachricht]) -> str:
        if not self.schluessel:
            raise KiFehler("anmeldung", "MISTRAL_API_KEY fehlt")
        nachrichten = [{"role": "system", "content": anweisung}] + [
            {"role": "user" if n.rolle == "nutzer" else "assistant", "content": n.text} for n in verlauf
        ]
        try:
            antwort = self._client.post(
                f"{self.adresse}/chat/completions",
                headers={"Authorization": f"Bearer {self.schluessel}"},
                json={"model": self.modell, "messages": nachrichten, "temperature": 0.3, "max_tokens": 800},
            )
        except httpx.HTTPError as e:
            raise KiFehler("voruebergehend", f"Mistral nicht erreichbar: {type(e).__name__}") from None
        if antwort.status_code != 200:
            meldung = f"{antwort.status_code} {antwort.text[:300]}"
            raise KiFehler(einordnen(meldung), meldung)
        daten = antwort.json()
        nutzung = daten.get("usage") or {}
        log.info("KI mistral: Modell=%s, Eingabe=%s, Ausgabe=%s Tokens", self.modell,
                 nutzung.get("prompt_tokens"), nutzung.get("completion_tokens"))
        return (daten["choices"][0]["message"]["content"] or "").strip()
