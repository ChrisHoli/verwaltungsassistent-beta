"""Speicherort. Jede Ablage ist ein Adapter hinter Ablage: ordner (lokal) oder rclone (Nextcloud, Drive, iCloud …)."""

from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath


class AblageFehler(RuntimeError):
    pass


class Ablage(ABC):
    @abstractmethod
    def schreiben(self, pfad: str, daten: bytes) -> None: ...

    @abstractmethod
    def lesen(self, pfad: str) -> bytes: ...

    @abstractmethod
    def liste(self, ordner: str = "") -> list[str]: ...

    @abstractmethod
    def loeschen(self, pfad: str) -> None:
        """Ordner oder Datei samt Inhalt löschen. Fehlt er, ist das kein Fehler."""

    @abstractmethod
    def verschieben(self, ordner: str, ziel: str) -> None:
        """Ganzen Ordner umbenennen oder verschieben (zum Einsortieren)."""

    def pruefen(self) -> None:
        """Wirft AblageFehler, wenn der Speicherort nicht erreichbar ist."""


def _sicherer_pfad(pfad: str) -> PurePosixPath:
    p = PurePosixPath(pfad)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"Unzulässiger Pfad: {pfad!r}")
    return p


class OrdnerAblage(Ablage):
    def __init__(self, wurzel: str | Path):
        self.wurzel = Path(wurzel)

    def _ziel(self, pfad: str) -> Path:
        return self.wurzel / _sicherer_pfad(pfad)

    def pruefen(self) -> None:
        self.wurzel.mkdir(parents=True, exist_ok=True)

    def schreiben(self, pfad: str, daten: bytes) -> None:
        ziel = self._ziel(pfad)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        tmp = ziel.with_name(ziel.name + ".neu")
        tmp.write_bytes(daten)
        tmp.replace(ziel)

    def lesen(self, pfad: str) -> bytes:
        return self._ziel(pfad).read_bytes()

    def loeschen(self, pfad: str) -> None:
        import shutil

        ziel = self._ziel(pfad)
        if ziel.is_dir():
            shutil.rmtree(ziel)
        else:
            ziel.unlink(missing_ok=True)

    def verschieben(self, ordner: str, ziel: str) -> None:
        neu = self._ziel(ziel)
        if neu.exists():
            raise AblageFehler(f"Ziel gibt es schon: {ziel}")
        neu.parent.mkdir(parents=True, exist_ok=True)
        self._ziel(ordner).rename(neu)

    def liste(self, ordner: str = "") -> list[str]:
        basis = self._ziel(ordner) if ordner else self.wurzel
        if not basis.exists():
            return []
        return sorted(str(p.relative_to(self.wurzel)) for p in basis.rglob("*") if p.is_file())


def ablage_waehlen(art: str, ziel: str) -> Ablage:
    if art == "ordner":
        return OrdnerAblage(ziel)
    if art == "rclone":
        from .rclone import RcloneAblage

        return RcloneAblage(ziel)
    raise ValueError(f"Unbekannte Ablage {art!r} (möglich: ordner, rclone)")
