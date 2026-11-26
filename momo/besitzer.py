"""Wer darf mit Momo sprechen? Nur der gekoppelte Besitzer.

Der erste verschlüsselte Kontakt (nach dem Scannen des Einladungs-QR) wird Besitzer. Ist
MOMO_BESITZER_ADRESSEN gesetzt, nur einer dieser Adressen. Danach zählt nur die gespeicherte
Kontakt-ID. Zurücksetzen: besitzer.json im Datenordner löschen und den Bot neu starten.
"""

import json
from pathlib import Path


class Besitzer:
    def __init__(self, adressen: str, datei: Path):
        self.adressen = {a.strip().lower() for a in adressen.split(",") if a.strip()}
        self.datei = Path(datei)
        self.kontakt_id: int | None = self._laden()

    def _laden(self) -> int | None:
        try:
            return int(json.loads(self.datei.read_text())["kontakt_id"])
        except (FileNotFoundError, KeyError, ValueError, TypeError):
            return None

    def _speichern(self, kontakt_id: int) -> None:
        self.datei.parent.mkdir(parents=True, exist_ok=True)
        self.datei.write_text(json.dumps({"kontakt_id": kontakt_id}))

    @property
    def gekoppelt(self) -> bool:
        return self.kontakt_id is not None

    def pruefen(self, kontakt_id: int, adresse: str, verschluesselt: bool) -> tuple[bool, bool]:
        """Gibt (erlaubt, neu_gekoppelt) zurück."""
        if self.kontakt_id is not None:
            return kontakt_id == self.kontakt_id, False
        if not verschluesselt:
            return False, False
        if self.adressen and adresse.strip().lower() not in self.adressen:
            return False, False
        self.kontakt_id = kontakt_id
        self._speichern(kontakt_id)
        return True, True
