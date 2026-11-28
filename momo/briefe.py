"""Briefe aufnehmen: Fotos und PDFs aus dem Chat als Vorgang in der Ablage speichern.

Neue Briefe landen in Briefe/Eingang/<JJJJ-MM-TT_HHMMSS>/original/seite-01.jpg …
Nach dem Lesen sortiert Momo sie ein: Briefe/<Bereich>/<Absender>/<JJJJ-MM-TT> <Worum es geht>/
mit original/, text/, json/ und später antwortbriefe/. Seiten, die kurz hintereinander kommen, gehören zusammen.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from .ablage import Ablage

ZUSAMMEN_SEKUNDEN = 5 * 60
ENDUNGEN = {
    "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/heic": "heic",
    "image/heif": "heic", "application/pdf": "pdf",
}
ZEITZONE = ZoneInfo("Europe/Berlin")


def endung_fuer(mime: str | None, dateiname: str | None) -> str | None:
    if mime and mime.lower() in ENDUNGEN:
        return ENDUNGEN[mime.lower()]
    if dateiname and "." in dateiname:
        e = dateiname.rsplit(".", 1)[1].lower()
        if e in {"jpg", "jpeg", "png", "webp", "heic", "pdf"}:
            return "jpg" if e == "jpeg" else e
    return None


@dataclass(frozen=True)
class Aufnahme:
    vorgang: str
    seite: int
    pfad: str


class Briefablage:
    def __init__(self, ablage: Ablage, uhr=time.time):
        self.ablage = ablage
        self.uhr = uhr
        self._vorgang: str | None = None
        self._seite = 0
        self._zuletzt = 0.0

    def aufnehmen(self, daten: bytes, endung: str) -> Aufnahme:
        jetzt = self.uhr()
        if self._vorgang is None or jetzt - self._zuletzt > ZUSAMMEN_SEKUNDEN:
            self._vorgang = "Briefe/Eingang/" + datetime.fromtimestamp(jetzt, ZEITZONE).strftime("%Y-%m-%d_%H%M%S")
            self._seite = 0
        seite = self._seite + 1
        pfad = f"{self._vorgang}/original/seite-{seite:02d}.{endung}"
        self.ablage.schreiben(pfad, daten)
        self._seite, self._zuletzt = seite, jetzt
        return Aufnahme(self._vorgang, seite, pfad)

    def einsortieren(self, vorgang: str, bereich: str, absender: str | None, datum: str | None,
                     betreff: str | None) -> str:
        """Verschiebt den Vorgang aus dem Eingang an seinen Platz und gibt den neuen Pfad zurück."""
        from .aufnahme import ordnername

        tag = datum or vorgang.rsplit("/", 1)[-1][:10]
        ordner = ordnername(absender) or "Unbekannt"
        name = f"{tag} {ordnername(betreff) or 'Brief'}"
        basis = f"Briefe/{ordnername(bereich) or 'Sonstiges'}/{ordner}/{name}"
        ziel, n = basis, 2
        while self.ablage.liste(ziel):
            ziel, n = f"{basis} ({n})", n + 1
        self.ablage.verschieben(vorgang, ziel)
        if self._vorgang == vorgang:  # weitere Seiten kämen sonst in den alten Ordner
            self._vorgang = None
        return ziel

    def originale(self, vorgang: str) -> list[tuple[bytes, str]]:
        """(Daten, Endung) aller Seiten eines Vorgangs, in Reihenfolge."""
        pfade = [p for p in self.ablage.liste(f"{vorgang}/original") if "/original/seite-" in p]
        return [(self.ablage.lesen(p), p.rsplit(".", 1)[-1]) for p in sorted(pfade)]

    def ergebnis_ablegen(self, vorgang: str, seiten: list[str], aufnahme: dict | None) -> None:
        import json

        for i, text in enumerate(seiten, start=1):
            self.ablage.schreiben(f"{vorgang}/text/seite-{i:02d}.txt", text.encode())
        if aufnahme is not None:
            self.ablage.schreiben(f"{vorgang}/json/aufnahme.json",
                                  json.dumps(aufnahme, ensure_ascii=False, indent=2).encode())
