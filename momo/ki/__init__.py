"""KI-Anschluss. Jeder Anbieter ist ein Adapter hinter KiAnbieter; Anbieter-Code nur hier (V3).

Nur Text geht an die KI, so wenig wie nötig.
"""

from abc import ABC, abstractmethod


class KiNichtVerfuegbar(RuntimeError):
    pass


class KiAnbieter(ABC):
    name = "?"

    @abstractmethod
    def fragen(self, anweisung: str, text: str) -> str:
        """anweisung: feste Systemvorgabe von Momo; text: Inhalt (nicht vertrauenswürdig)."""


class KeineKi(KiAnbieter):
    name = "keine"

    def fragen(self, anweisung: str, text: str) -> str:
        raise KiNichtVerfuegbar("Keine KI eingerichtet (MOMO_KI=keine)")


def anbieter_waehlen(name: str) -> KiAnbieter:
    if name in ("", "keine"):
        return KeineKi()
    raise ValueError(f"Unbekannte KI {name!r} – kommt in V3")
