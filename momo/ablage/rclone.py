"""Ablage über rclone: Nextcloud/WebDAV, Google Drive, iCloud Drive, OneDrive, Dropbox …

Ziel ist ein rclone-Pfad wie `nextcloud:` oder `drive:Momo`. Die Verbindung steht entweder in
RCLONE_CONFIG_<NAME>_* (Umgebung) oder in /daten/rclone.conf (`rclone config`).
"""

import logging
import subprocess

from . import Ablage, AblageFehler, _sicherer_pfad

log = logging.getLogger(__name__)


class RcloneAblage(Ablage):
    def __init__(self, ziel: str, befehl: str = "rclone", zeitlimit: int = 120):
        if ":" not in ziel:
            raise ValueError(f"rclone-Ziel braucht die Form name:pfad, nicht {ziel!r}")
        self.ziel = ziel.rstrip("/")
        self.befehl = befehl
        self.zeitlimit = zeitlimit

    def _pfad(self, pfad: str) -> str:
        teil = str(_sicherer_pfad(pfad)) if pfad else ""
        if self.ziel.endswith(":"):
            return self.ziel + teil
        return f"{self.ziel}/{teil}" if teil else self.ziel

    def _rclone(self, *argumente: str, eingabe: bytes | None = None) -> bytes:
        try:
            ergebnis = subprocess.run([self.befehl, *argumente], input=eingabe, capture_output=True,
                                      timeout=self.zeitlimit)
        except subprocess.TimeoutExpired:
            raise AblageFehler(f"rclone {argumente[0]}: Zeitüberschreitung") from None
        except FileNotFoundError:
            raise AblageFehler("rclone nicht installiert") from None
        if ergebnis.returncode != 0:
            raise AblageFehler(f"rclone {argumente[0]}: {ergebnis.stderr.decode(errors='replace')[-300:]}")
        return ergebnis.stdout

    def schreiben(self, pfad: str, daten: bytes) -> None:
        self._rclone("rcat", self._pfad(pfad), eingabe=daten)

    def lesen(self, pfad: str) -> bytes:
        return self._rclone("cat", self._pfad(pfad))

    def liste(self, ordner: str = "") -> list[str]:
        try:
            roh = self._rclone("lsf", "-R", "--files-only", self._pfad(ordner))
        except AblageFehler as e:
            if "not found" in str(e).lower():
                return []
            raise
        praefix = f"{ordner.strip('/')}/" if ordner else ""
        return sorted(praefix + z for z in roh.decode().splitlines() if z)

    def verschieben(self, ordner: str, ziel: str) -> None:
        # Nextcloud/WebDAV verschiebt auf dem Server; der leere alte Ordner wird danach entfernt
        self._rclone("move", self._pfad(ordner), self._pfad(ziel), "--delete-empty-src-dirs")
        try:
            self._rclone("rmdir", self._pfad(ordner))
        except AblageFehler:
            pass

    def pruefen(self) -> None:
        self._rclone("lsf", "--max-depth", "1", self._pfad(""))
