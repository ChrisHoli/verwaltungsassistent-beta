"""Was Momo sich dauerhaft merkt: Vorlese-Wunsch und die letzte Briefantwort (zum Nochmal-Vorlesen)."""

import json
from pathlib import Path

from .antworten import Antwort


class Einstellungen:
    def __init__(self, ordner: Path, vorlesen_standard: str):
        self.datei = Path(ordner) / "einstellungen.json"
        self.brief_datei = Path(ordner) / "letzter_brief.json"
        self.standard = vorlesen_standard

    def _lesen(self, datei: Path) -> dict:
        try:
            daten = json.loads(datei.read_text())
            return daten if isinstance(daten, dict) else {}
        except (FileNotFoundError, ValueError):
            return {}

    def _schreiben(self, datei: Path, daten: dict) -> None:
        datei.parent.mkdir(parents=True, exist_ok=True)
        tmp = datei.with_suffix(".neu")
        tmp.write_text(json.dumps(daten, ensure_ascii=False))
        tmp.replace(datei)

    @property
    def vorlesen(self) -> str:
        wert = self._lesen(self.datei).get("vorlesen")
        return wert if wert in ("immer", "nie") else self.standard

    @vorlesen.setter
    def vorlesen(self, wert: str) -> None:
        self._schreiben(self.datei, {**self._lesen(self.datei), "vorlesen": wert})

    def brief_merken(self, antwort: Antwort) -> None:
        self._schreiben(self.brief_datei, {"text": antwort.text, "sprechtext": antwort.sprechtext})

    def letzter_brief(self) -> Antwort | None:
        d = self._lesen(self.brief_datei)
        return Antwort(d["text"], sprechtext=d.get("sprechtext")) if d.get("text") else None
