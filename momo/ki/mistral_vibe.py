"""Mistral über Mistral Vibe (`vibe -p`), z. B. mit einem Le-Chat-Pro-Abo.

Vibe ist eigentlich ein Programmier-Werkzeug mit Shell, Dateien und Websuche. Für Momo laufen davon
keine Werkzeuge: Briefe sind nicht vertrauenswürdig (Grundregel 5). Deshalb: alle Werkzeuge aus
(Einstellung und Aufruf), keine Konnektoren, kein MCP, keine Unteragenten, kein Projektkontext,
eigene Anweisung statt Vibes Programmierer-Anweisung, ein leerer Arbeitsordner, eine Antwortrunde.
Schlüssel: in Mistral Studio unter Code → Vibe CLI (zählt aufs Abo). Bild mit MIT_VIBE=1 bauen.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path

from . import KiAnbieter, KiFehler, Nachricht, einordnen
from .claude_abo import verlauf_als_text

log = logging.getLogger(__name__)

# Alle eingebauten Werkzeuge von Vibe 3.1 (grep läuft über bash, Unteragenten sind mit enable_subagents aus);
# zusätzlich gilt disabled_tools = ["*"] für neue
WERKZEUGE = (
    "ask_user_question", "bash", "bash_log_file", "bash_output", "bash_sessions", "bash_stdin", "edit",
    "git_bash", "git_bash_log_file", "git_bash_output", "git_bash_sessions", "git_bash_stdin",
    "powershell", "powershell_log_file", "powershell_output", "powershell_sessions", "powershell_stdin",
    "read_file", "skill", "todo", "web_fetch", "web_search", "write_file",
)

EINSTELLUNG = """# Von Momo geschrieben – wird bei jedem Aufruf erneuert. Vibe antwortet hier nur mit Text.
disabled_tools = ["*"]
enable_connectors = false
enable_mcp = false
enable_subagents = false
enable_background_processes = false
include_project_context = false
outside_workdir = "deny"
default_approval_policy = "ask"
enable_auto_update = false
enable_update_checks = false
enable_telemetry = false
enable_otel = false
enable_notifications = false
show_greeting = false

[session_logging]
enabled = false
""" + "".join(f'\n[tools.{w}]\npermission = "never"\n' for w in WERKZEUGE)


class MistralVibe(KiAnbieter):
    name = "mistral-vibe"

    def __init__(self, schluessel: str, modell: str = "", befehl: str = "vibe", heim: str = "/daten/vibe",
                 zeitlimit: int = 180):
        self.schluessel = schluessel
        self.modell = modell
        self.befehl = befehl
        self.heim = Path(heim)
        self.zeitlimit = zeitlimit

    def _befehlszeile(self, anweisung_datei: Path) -> list[str]:
        zeile = [
            self.befehl, "-p", "--output", "text",
            "--system-prompt-file", str(anweisung_datei),
            "--max-turns", "1",
            "--time-limit", str(self.zeitlimit - 10),
            "--disabled-tools", "*",
            "--trust",
        ]
        if self.modell:
            zeile += ["--model", self.modell]
        return zeile

    def fragen(self, anweisung: str, verlauf: list[Nachricht]) -> str:
        if not self.schluessel:
            raise KiFehler("anmeldung", "Schlüssel für Mistral Vibe fehlt (MOMO_VIBE_SCHLUESSEL)")
        arbeitsordner = self.heim / "leer"
        for ordner in (self.heim, arbeitsordner):
            ordner.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self.heim / "config.toml").write_text(EINSTELLUNG)
        anweisung_datei = self.heim / "anweisung.txt"  # außerhalb des Arbeitsordners
        anweisung_datei.write_text(anweisung)
        # Schmale Umgebung: nur was Vibe braucht
        umgebung = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": str(self.heim),
            "VIBE_HOME": str(self.heim),
            "MISTRAL_API_KEY": self.schluessel,
            "LANG": "C.UTF-8",
            "NO_COLOR": "1",
        }
        try:
            ergebnis = subprocess.run(
                self._befehlszeile(anweisung_datei), input=verlauf_als_text(verlauf).encode(),
                capture_output=True, cwd=arbeitsordner, env=umgebung, timeout=self.zeitlimit,
            )
        except subprocess.TimeoutExpired:
            raise KiFehler("voruebergehend", f"Mistral Vibe hat nach {self.zeitlimit} s nicht geantwortet") from None
        except FileNotFoundError:
            raise KiFehler("sonstig", f"{self.befehl} nicht gefunden – Bild mit MIT_VIBE=1 bauen") from None
        finally:
            anweisung_datei.unlink(missing_ok=True)
            # Vibe führt Verlauf und Protokolle; nichts davon soll bleiben (Grundregel 9)
            (self.heim / "vibehistory").unlink(missing_ok=True)
            shutil.rmtree(self.heim / "logs", ignore_errors=True)
            shutil.rmtree(self.heim / "sessions", ignore_errors=True)
        text = ergebnis.stdout.decode(errors="replace").strip()
        fehler = ergebnis.stderr.decode(errors="replace").strip()
        if ergebnis.returncode != 0 or not text:
            meldung = (fehler or text or f"Exit-Code {ergebnis.returncode}")[-300:]
            raise KiFehler(einordnen(meldung), meldung)
        log.info("KI mistral-vibe: Modell=%s, %s Zeichen Antwort", self.modell or "Standard", len(text))
        return text
