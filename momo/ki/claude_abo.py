"""Claude über ein Abo (Claude Code im Druckmodus, `claude -p`, setup-token).

Gedacht zum Testen durch den Betreiber. Claude Code läuft ohne Werkzeuge, ohne Einstellungen,
ohne MCP, in einem leeren Arbeitsordner. Bild nur mit MIT_CLAUDE=1 gebaut (siehe Dockerfile).
"""

import json
import logging
import os
import subprocess
from pathlib import Path

from . import KiAnbieter, KiFehler, Nachricht, einordnen

log = logging.getLogger(__name__)


def verlauf_als_text(verlauf: list[Nachricht]) -> str:
    if len(verlauf) == 1:
        return verlauf[0].text
    teile = ["Bisheriges Gespräch:"]
    for n in verlauf[:-1]:
        teile.append(f"{'Nutzer' if n.rolle == 'nutzer' else 'Momo'}: {n.text}")
    teile.append(f"\nNeue Nachricht vom Nutzer:\n{verlauf[-1].text}")
    return "\n".join(teile)


class ClaudeAbo(KiAnbieter):
    name = "claude-abo"

    def __init__(self, token: str, modell: str, befehl: str = "claude", heim: str = "/daten/claude",
                 zeitlimit: int = 120):
        self.token = token
        self.modell = modell
        self.befehl = befehl
        self.heim = Path(heim)
        self.zeitlimit = zeitlimit

    def _befehlszeile(self, anweisung: str) -> list[str]:
        return [
            self.befehl, "-p", "--output-format", "json",
            "--model", self.modell,
            "--tools", "",
            "--max-turns", "2",
            "--setting-sources", "",
            "--strict-mcp-config",
            "--disable-slash-commands",
            "--no-session-persistence",
            "--system-prompt", anweisung,
        ]

    def fragen(self, anweisung: str, verlauf: list[Nachricht]) -> str:
        if not self.token:
            raise KiFehler("anmeldung", "CLAUDE_CODE_OAUTH_TOKEN fehlt")
        arbeitsordner = self.heim / "leer"
        for ordner in (self.heim, arbeitsordner):
            ordner.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Schmale Umgebung: kein ANTHROPIC_API_KEY, der Vorrang vor dem Abo hätte
        umgebung = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": str(self.heim),
            "CLAUDE_CONFIG_DIR": str(self.heim / ".claude"),
            "CLAUDE_CODE_OAUTH_TOKEN": self.token,
            "LANG": "C.UTF-8",
            "DISABLE_AUTOUPDATER": "1",
            "DISABLE_TELEMETRY": "1",
        }
        try:
            ergebnis = subprocess.run(
                self._befehlszeile(anweisung), input=verlauf_als_text(verlauf).encode(),
                capture_output=True, cwd=arbeitsordner, env=umgebung, timeout=self.zeitlimit,
            )
        except subprocess.TimeoutExpired:
            raise KiFehler("voruebergehend", f"Claude hat nach {self.zeitlimit} s nicht geantwortet") from None
        except FileNotFoundError:
            raise KiFehler("sonstig", f"{self.befehl} nicht gefunden – Bild mit MIT_CLAUDE=1 bauen") from None
        roh = ergebnis.stdout.decode(errors="replace").strip()
        fehler = ergebnis.stderr.decode(errors="replace").strip()
        try:
            daten = json.loads(roh)
        except json.JSONDecodeError:
            meldung = (fehler or roh or f"Exit-Code {ergebnis.returncode}")[-300:]
            raise KiFehler(einordnen(meldung), meldung) from None
        text = (daten.get("result") or "").strip()
        if daten.get("is_error") or ergebnis.returncode != 0:
            meldung = (text or fehler or daten.get("subtype") or "unbekannt")[-300:]
            raise KiFehler(einordnen(meldung), meldung)
        nutzung = daten.get("usage") or {}
        log.info("KI claude-abo: Modell=%s, Eingabe=%s, Ausgabe=%s Tokens", self.modell,
                 nutzung.get("input_tokens"), nutzung.get("output_tokens"))
        return text
