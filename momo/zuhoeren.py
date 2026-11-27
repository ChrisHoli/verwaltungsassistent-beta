"""Zuhören: Sprachnachricht → Text (Whisper, lokal im Container). Nichts verlässt das Gerät.

Ins Log kommen nur Länge und Dauer, nie der erkannte Text.
"""

import logging
import subprocess
import threading
import time
from pathlib import Path

log = logging.getLogger(__name__)

# Wörter, die Whisper sonst verhört („Jobkenner“). Als Liste wirkt das besser als ein ganzer Satz (gemessen 27.11.2026).
AMTSWOERTER = ("Jobcenter, Kontoauszüge, Bescheid, Anhörung, Widerspruch, Frist, Aktenzeichen, "
               "Weiterbewilligungsantrag, Mitwirkung, Nebenkostenabrechnung, Bürgergeld")
HOECHSTENS_SEKUNDEN = 180  # längere Nachrichten werden nur bis hier umgeschrieben


class ZuhoerFehler(Exception):
    pass


def ton_laden(datei: Path):
    """Beliebige Tondatei → 16 kHz mono float32 (über ffmpeg, unabhängig von PyAV-Versionen)."""
    import numpy as np

    roh = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-nostdin", "-i", str(datei), "-t", str(HOECHSTENS_SEKUNDEN),
         "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True, check=True, timeout=120).stdout
    return np.frombuffer(roh, np.int16).astype(np.float32) / 32768.0


class Ohr:
    def __init__(self, modell: str, ordner: Path | None = None):
        self.modell = modell  # Name (tiny, base, small …) oder Pfad zu einem Modellordner
        self.ordner = ordner
        self._whisper = None
        self._sperre = threading.Lock()

    @property
    def verfuegbar(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return False
        return True

    def _laden(self):
        if self._whisper is None:
            from faster_whisper import WhisperModel

            quelle = str(self.ordner / self.modell) if self.ordner and (self.ordner / self.modell).exists() \
                else self.modell
            self._whisper = WhisperModel(quelle, device="cpu", compute_type="int8", cpu_threads=2)
        return self._whisper

    def umschreiben(self, datei: Path) -> str:
        """Erkannter Text (kann leer sein). Wirft ZuhoerFehler, wenn es gar nicht geht."""
        if not self.verfuegbar:
            raise ZuhoerFehler("faster-whisper fehlt")
        beginn = time.monotonic()
        try:
            with self._sperre:
                whisper = self._laden()
                stuecke, info = whisper.transcribe(
                    ton_laden(datei), language="de", beam_size=5, vad_filter=True,
                    condition_on_previous_text=False,
                    initial_prompt=AMTSWOERTER)
                teile = []
                for s in stuecke:
                    if s.start > HOECHSTENS_SEKUNDEN:
                        break
                    teile.append(s.text.strip())
        except Exception as e:
            raise ZuhoerFehler(f"{type(e).__name__}: {str(e)[:150]}") from e
        text = " ".join(t for t in teile if t).strip()
        log.info("Sprachnachricht umgeschrieben: %.0f s Ton, %s Zeichen, %.1f s Rechenzeit",
                 info.duration, len(text), time.monotonic() - beginn)
        return text
