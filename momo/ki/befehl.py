"""Jede KI, die sich als Befehl aufrufen lässt (z. B. `ollama run …`, `llm -m …` oder ein eigenes Skript).

Die Anweisung und das Gespräch gehen als Text über die Standardeingabe hinein, die Antwort kommt über die
Standardausgabe zurück. Der Befehl läuft ohne Shell und mit schmaler Umgebung."""

import logging
import os
import shlex
import subprocess

from . import KiAnbieter, KiFehler, Nachricht, einordnen
from .claude_abo import verlauf_als_text

log = logging.getLogger(__name__)


class Befehl(KiAnbieter):
    name = "befehl"

    def __init__(self, befehl: str, zeitlimit: int = 300):
        self.teile = shlex.split(befehl)
        self.zeitlimit = zeitlimit

    def fragen(self, anweisung: str, verlauf: list[Nachricht]) -> str:
        if not self.teile:
            raise KiFehler("anmeldung", "MOMO_KI_BEFEHL fehlt")
        eingabe = f"{anweisung}\n\n{verlauf_als_text(verlauf)}"
        umgebung = {k: v for k, v in os.environ.items()
                    if k in ("PATH", "HOME", "LANG", "TZ") or k.startswith("MOMO_KI_BEFEHL_")}
        try:
            ergebnis = subprocess.run(self.teile, input=eingabe.encode(), capture_output=True,
                                      timeout=self.zeitlimit, env=umgebung)
        except FileNotFoundError:
            raise KiFehler("anmeldung", f"Befehl nicht gefunden: {self.teile[0]}") from None
        except subprocess.TimeoutExpired:
            raise KiFehler("voruebergehend", "Befehl: Zeitüberschreitung") from None
        if ergebnis.returncode != 0:
            meldung = ergebnis.stderr.decode(errors="replace")[-300:]
            raise KiFehler(einordnen(meldung), f"Befehl fehlgeschlagen: {meldung}")
        text = ergebnis.stdout.decode(errors="replace").strip()
        log.info("KI befehl: %s Zeichen Antwort", len(text))
        return text
