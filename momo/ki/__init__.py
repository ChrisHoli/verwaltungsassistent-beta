"""KI-Anschluss. Jeder Anbieter ist ein Adapter hinter KiAnbieter; Anbieter-Code nur in diesem Paket.

Nur Text geht an die KI, so wenig wie nötig. Im Log nur Verbrauch, nie Inhalte.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class KiFehler(RuntimeError):
    """art: anmeldung | limit | voruebergehend | sonstig | keine"""

    def __init__(self, art: str, meldung: str):
        super().__init__(meldung)
        self.art = art


class KiNichtVerfuegbar(KiFehler):
    def __init__(self, meldung: str):
        super().__init__("keine", meldung)


@dataclass(frozen=True)
class Nachricht:
    rolle: str  # "nutzer" | "momo"
    text: str


_MUSTER = (
    ("anmeldung", ("not logged in", "/login", "invalid api key", "unauthorized", "401", "403",
                   "token has expired", "token expired", "revoked", "authentication")),
    ("limit", ("usage limit", "limit reached", "rate limit", "rate_limit", "429", "credit", "quota", "402",
               "billing", "subscription")),
    ("voruebergehend", ("overloaded", "529", "500", "502", "503", "504", "timeout", "timed out",
                        "network", "connect", "socket")),
)


def einordnen(text: str) -> str:
    klein = text.lower()
    for art, muster in _MUSTER:
        if any(m in klein for m in muster):
            return art
    return "sonstig"


class KiAnbieter(ABC):
    name = "?"

    @abstractmethod
    def fragen(self, anweisung: str, verlauf: list[Nachricht]) -> str:
        """anweisung: feste Systemvorgabe von Momo; verlauf: Gespräch, letzte Nachricht vom Nutzer."""


class KeineKi(KiAnbieter):
    name = "keine"

    def fragen(self, anweisung: str, verlauf: list[Nachricht]) -> str:
        raise KiNichtVerfuegbar("Keine KI eingerichtet (MOMO_KI=keine)")


# Voreinstellungen für KIs mit OpenAI-kompatibler Schnittstelle:
# name: (Adresse, übliche Umgebungsvariable für den Schlüssel, Standardmodell oder "", Schlüssel nötig)
OFFENE_KIS = {
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY", "mistral-medium-latest", True),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY", "", True),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", "", True),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "", True),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "", True),
    "ollama": ("http://localhost:11434/v1", "", "", False),
    "openai-kompatibel": ("", "", "", False),
}
ALLE_KIS = ("keine", *OFFENE_KIS, "anthropic", "claude-abo", "mistral-vibe", "befehl")


def anbieter_waehlen(name: str, umgebung: dict[str, str] | None = None) -> KiAnbieter:
    """MOMO_KI wählt die KI. Gemeinsame Einstellungen: MOMO_KI_MODELL, MOMO_KI_SCHLUESSEL, MOMO_KI_ADRESSE."""
    import os

    u = os.environ if umgebung is None else umgebung
    feld = lambda k: u.get(k, "").strip()  # noqa: E731
    modell, schluessel, adresse = feld("MOMO_KI_MODELL"), feld("MOMO_KI_SCHLUESSEL"), feld("MOMO_KI_ADRESSE")
    if name in ("", "keine"):
        return KeineKi()
    if name in OFFENE_KIS:
        from .offen import OpenAiKompatibel

        vorgabe_adresse, schluessel_var, vorgabe_modell, noetig = OFFENE_KIS[name]
        if name == "mistral":
            adresse = adresse or feld("MISTRAL_ADRESSE")
        adresse = adresse or vorgabe_adresse
        if not adresse:
            raise ValueError(f"MOMO_KI={name} braucht MOMO_KI_ADRESSE (z. B. http://mein-server:8000/v1)")
        temperatur = feld("MOMO_KI_TEMPERATUR")
        return OpenAiKompatibel(
            name=name, adresse=adresse, schluessel=schluessel or (feld(schluessel_var) if schluessel_var else ""),
            modell=modell or vorgabe_modell, schluessel_noetig=noetig and not feld("MOMO_KI_OHNE_SCHLUESSEL"),
            temperatur=float(temperatur) if temperatur else (0.3 if name == "mistral" else None),
            laengen_feld="max_completion_tokens" if name == "openai" else "max_tokens")
    if name == "anthropic":
        from .anthropic_api import AnthropicApi

        return AnthropicApi(schluessel=schluessel or feld("ANTHROPIC_API_KEY"),
                            modell=modell or "claude-opus-5-5", aufwand=feld("MOMO_KI_AUFWAND") or "medium")
    if name == "claude-abo":
        from .claude_abo import ClaudeAbo

        return ClaudeAbo(token=feld("CLAUDE_CODE_OAUTH_TOKEN"),
                         modell=modell or "sonnet",
                         befehl=feld("MOMO_CLAUDE_BEFEHL") or "claude",
                         heim=(u.get("MOMO_DATEN") or "/daten") + "/claude")
    if name == "mistral-vibe":
        from .mistral_vibe import MistralVibe

        return MistralVibe(schluessel=schluessel or feld("MOMO_VIBE_SCHLUESSEL"), modell=modell,
                           befehl=feld("MOMO_VIBE_BEFEHL") or "vibe",
                           heim=(u.get("MOMO_DATEN") or "/daten") + "/vibe")
    if name == "befehl":
        from .befehl import Befehl

        return Befehl(feld("MOMO_KI_BEFEHL"))
    raise ValueError(f"Unbekannte KI {name!r} (möglich: {', '.join(ALLE_KIS)})")
