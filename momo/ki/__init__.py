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
    ("limit", ("usage limit", "limit reached", "rate limit", "rate_limit", "429", "credit", "quota")),
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


def anbieter_waehlen(name: str, umgebung: dict[str, str] | None = None) -> KiAnbieter:
    import os

    u = os.environ if umgebung is None else umgebung
    modell = u.get("MOMO_KI_MODELL", "").strip()
    if name in ("", "keine"):
        return KeineKi()
    if name == "mistral":
        from .mistral import Mistral

        return Mistral(schluessel=u.get("MISTRAL_API_KEY", "").strip(),
                       modell=modell or "mistral-medium-latest",
                       adresse=u.get("MISTRAL_ADRESSE", "https://api.mistral.ai/v1").strip())
    if name == "claude-abo":
        from .claude_abo import ClaudeAbo

        return ClaudeAbo(token=u.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip(),
                         modell=modell or "sonnet",
                         befehl=u.get("MOMO_CLAUDE_BEFEHL", "claude").strip(),
                         heim=u.get("MOMO_DATEN", "/daten") + "/claude")
    raise ValueError(f"Unbekannte KI {name!r} (möglich: keine, mistral, claude-abo)")
