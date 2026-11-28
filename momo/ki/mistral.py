"""Mistral über die API (EU). Schlüssel aus Mistral Studio, Abrechnung nach Verbrauch.

Mistral spricht das OpenAI-kompatible Format; diese Klasse ist nur die Voreinstellung dafür."""

import httpx

from .offen import OpenAiKompatibel


class Mistral(OpenAiKompatibel):
    def __init__(self, schluessel: str, modell: str, adresse: str = "https://api.mistral.ai/v1",
                 zeitlimit: float = 120, transport: httpx.BaseTransport | None = None):
        super().__init__("mistral", adresse, schluessel, modell, temperatur=0.3, zeitlimit=zeitlimit,
                         transport=transport)
