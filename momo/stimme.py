"""Vorlesen: Text → Sprachnachricht (Piper, lokal) als .m4a für Android und iPhone."""

import logging
import subprocess
import tempfile
import threading
import wave
from pathlib import Path

log = logging.getLogger(__name__)


class Stimme:
    def __init__(self, modell: Path | None, tempo: float = 1.15, prozent: int = 100):
        self.modell = modell
        self.tempo = tempo  # Piper length_scale: >1 = langsamer, Momos ruhiges Grundtempo
        # Sprechtempo in Prozent (MOMO_SPRECHTEMPO). Piper skaliert nicht gleichmäßig (150 % ergäbe nur etwa 125 %),
        # deshalb beschleunigt ffmpeg die fertige Aufnahme, ohne die Tonhöhe zu ändern.
        self.faktor = max(50, min(int(prozent or 100), 250)) / 100
        self._stimme = None
        self._sperre = threading.Lock()

    @property
    def verfuegbar(self) -> bool:
        return self.modell is not None and Path(self.modell).exists()

    def _laden(self):
        if self._stimme is None:
            from piper import PiperVoice

            self._stimme = PiperVoice.load(str(self.modell))
        return self._stimme

    def sprechen(self, text: str, ordner: Path) -> Path | None:
        """Legt eine .m4a-Datei in ordner an und gibt den Pfad zurück, bei Fehler None."""
        if not self.verfuegbar:
            return None
        try:
            from piper.config import SynthesisConfig

            ordner.mkdir(parents=True, exist_ok=True)
            with self._sperre:
                stimme = self._laden()
                with tempfile.NamedTemporaryFile(suffix=".wav", dir=ordner, delete=False) as roh:
                    wav = Path(roh.name)
                with wave.open(str(wav), "wb") as w:
                    stimme.synthesize_wav(text, w, syn_config=SynthesisConfig(length_scale=self.tempo))
            m4a = wav.with_suffix(".m4a")
            filter_ = ["-filter:a", f"atempo={self.faktor:g}"] if self.faktor != 1 else []
            subprocess.run(
                ["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), *filter_, "-c:a", "aac", "-b:a", "48k", str(m4a)],
                check=True,
                timeout=60,
            )
            wav.unlink(missing_ok=True)
            return m4a
        except Exception:
            log.exception("Vorlesen fehlgeschlagen")
            return None
