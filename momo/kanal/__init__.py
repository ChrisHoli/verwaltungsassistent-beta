"""Messenger-Anschluss. Jeder Messenger ist ein Kanal; Messenger-Code nur in diesem Paket.

Ein Kanal liefert eingehende Nachrichten als `Eingang` an den Boten und stellt Chat-Objekte bereit, über die der
Bote antwortet:
    chat.id
    chat.send_text(text) -> Nachricht mit .id
    chat.send_message(text=None, file=None, viewtype=None) -> Nachricht mit .id   (viewtype SPRACHE = Sprachnachricht)
    chat.accept()
Nachrichten-IDs sind Zahlen; eine Antwort per Zitat kommt als `zitiert` mit derselben Zahl zurück.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

SPRACHE = "Voice"

# Für Einrichtung, Datenschutz-Hinweis und Einladungsblatt
MESSENGER = {
    "deltachat": "Delta Chat",
    "telegram": "Telegram",
    "signal": "Signal",
}


@dataclass
class Eingang:
    kontakt: int | str           # bleibt für dieselbe Person immer gleich
    adresse: str                 # E-Mail-Adresse, Telefonnummer oder Benutzername (für MOMO_BESITZER_ADRESSEN)
    vertraut: bool               # darf koppeln: verschlüsselt (Delta Chat) bzw. mit Einladungscode (Telegram)
    chat: object
    art: str                     # text | bild | datei | sprache | sonst
    text: str = ""
    file: str | None = None      # Pfad der empfangenen Datei
    file_mime: str | None = None
    file_name: str | None = None
    zitiert: int | None = None   # ID der Nachricht, auf die geantwortet wurde


@dataclass
class Gesendet:
    id: int


class Kanal(ABC):
    name = "?"
    app_moeglich = False      # Mini-App im Chat (webxdc), nur Delta Chat
    loescht_selbst = False    # löscht den Chat nach der Aufbewahrungsfrist auf beiden Seiten

    @abstractmethod
    def starten(self, bote) -> None:
        """Verbinden, Einladung zeigen (falls nicht gekoppelt), bote.nebenher_starten(self) aufrufen,
        dann Nachrichten an bote.bei_eingang(eingang) liefern. Kehrt nicht zurück."""

    @abstractmethod
    def get_chat_by_id(self, chat_id):
        """Chat-Objekt für Erinnerungen (Chat-ID aus vorgaenge.json)."""

    def verlauf_loeschen(self, chat) -> bool:
        """Chatverlauf löschen, soweit der Messenger es erlaubt. True, wenn es auch beim Menschen weg ist."""
        return False


def einladung_ablegen(daten: Path, link: str, svg: str | None = None) -> None:
    (daten / "einladung.txt").write_text(link + "\n")
    if svg:
        (daten / "einladung.svg").write_text(svg)


def kanal_waehlen(name: str, konfig, umgebung: dict | None = None) -> Kanal:
    import os

    u = os.environ if umgebung is None else umgebung
    name = (name or "deltachat").strip().lower()
    if name == "deltachat":
        from .deltachat import DeltaChatKanal

        return DeltaChatKanal(konfig)
    if name == "telegram":
        from .telegram import TelegramKanal

        return TelegramKanal(konfig, u.get("MOMO_TELEGRAM_TOKEN", "").strip())
    if name == "signal":
        from .signal import SignalKanal

        return SignalKanal(konfig, u.get("MOMO_SIGNAL_NUMMER", "").strip(),
                           u.get("MOMO_SIGNAL_API", "http://signal:8080").strip())
    raise ValueError(f"Unbekannter Messenger {name!r} (möglich: {', '.join(MESSENGER)})")
