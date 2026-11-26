"""Speicherort. Jede Ablage ist ein Adapter hinter Ablage; rclone (Nextcloud, Drive, iCloud …) kommt in V4."""

from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath


class Ablage(ABC):
    @abstractmethod
    def schreiben(self, pfad: str, daten: bytes) -> None: ...

    @abstractmethod
    def lesen(self, pfad: str) -> bytes: ...

    @abstractmethod
    def liste(self, ordner: str = "") -> list[str]: ...


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

    def schreiben(self, pfad: str, daten: bytes) -> None:
        ziel = self._ziel(pfad)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        tmp = ziel.with_name(ziel.name + ".neu")
        tmp.write_bytes(daten)
        tmp.replace(ziel)

    def lesen(self, pfad: str) -> bytes:
        return self._ziel(pfad).read_bytes()

    def liste(self, ordner: str = "") -> list[str]:
        basis = self._ziel(ordner) if ordner else self.wurzel
        if not basis.exists():
            return []
        return sorted(str(p.relative_to(self.wurzel)) for p in basis.rglob("*") if p.is_file())


def ablage_waehlen(art: str, ziel: str) -> Ablage:
    if art == "ordner":
        return OrdnerAblage(ziel)
    raise ValueError(f"Unbekannte Ablage {art!r} – kommt in V4")
