"""Einrichtungsassistent: fragt Sprachmodell, Speicherort und Postfach ab, prüft jeden Zugang und schreibt die .env.

Läuft im Container (dort sind KI-Anschlüsse, rclone und Postfach-Prüfung vorhanden), gestartet von `./einrichten.sh`:
    python -m tools.einrichten [--ziel /daten/einrichtung.env]
Die bisherigen Werte kommen aus der Umgebung (docker compose lädt die alte .env). Enter übernimmt den Wert in Klammern.
Passwörter und Schlüssel werden nie angezeigt.
"""

import argparse
import getpass
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Welche KI? (Antwort auf die erste Frage des Assistenten)
KIS = [
    ("mistral", "Mistral", "Anbieter aus der EU (Frankreich), die Daten bleiben in der EU. Empfohlen.",
     "Schlüssel aus Mistral Studio: console.mistral.ai → API Keys"),
    ("anthropic", "Claude (Anthropic)", "schreibt sehr gute Briefe, Server in den USA.",
     "Schlüssel aus der Claude Console: console.anthropic.com → API Keys"),
    ("openai", "ChatGPT (OpenAI)", "Server in den USA.", "Schlüssel: platform.openai.com → API keys"),
    ("gemini", "Gemini (Google)", "Server in den USA.", "Schlüssel: aistudio.google.com → Get API key"),
    ("ollama", "Ollama, auf einem eigenen Rechner", "nichts verlässt das Haus; braucht einen starken Rechner "
     "und erklärt schwächer.", ""),
    ("openai-kompatibel", "Ein anderer Dienst", "z. B. IONOS, Scaleway, OpenRouter, LM Studio "
     "(alles mit /chat/completions).", ""),
    ("befehl", "Eigenes Programm", "Text rein über stdin, Antwort über stdout.", ""),
    ("claude-abo", "Claude-Abo", "nur zum Ausprobieren, nicht für den Dauerbetrieb.",
     "Token auf einem Rechner mit Claude Code erzeugen: claude setup-token"),
    ("keine", "Keine KI", "Momo legt ab und liest vor, erklärt aber keine Briefe.", ""),
]
# Wo der Schlüssel steht (wie in .env.example); alle anderen nutzen MOMO_KI_SCHLUESSEL
SCHLUESSEL_FELD = {"mistral": "MISTRAL_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
                   "gemini": "GEMINI_API_KEY", "claude-abo": "CLAUDE_CODE_OAUTH_TOKEN"}
STANDARD_MODELL = {"mistral": "mistral-medium-latest", "anthropic": "claude-opus-5-5", "claude-abo": "sonnet"}

# Bekannte Postfächer: Domain → (IMAP, SMTP, Hinweis zum App-Passwort)
POSTFAECHER = {
    "gmail.com": ("imap.gmail.com:993", "smtp.gmail.com:465",
                  "Google: 2-Schritt-Bestätigung an, dann myaccount.google.com/apppasswords"),
    "googlemail.com": ("imap.gmail.com:993", "smtp.gmail.com:465", ""),
    "gmx.de": ("imap.gmx.net:993", "mail.gmx.net:465", "GMX: in den Einstellungen „POP3/IMAP Abruf“ erlauben"),
    "gmx.net": ("imap.gmx.net:993", "mail.gmx.net:465", "GMX: in den Einstellungen „POP3/IMAP Abruf“ erlauben"),
    "web.de": ("imap.web.de:993", "smtp.web.de:587", "WEB.DE: in den Einstellungen „POP3/IMAP Abruf“ erlauben"),
    "posteo.de": ("posteo.de:993", "posteo.de:465", ""),
    "mailbox.org": ("imap.mailbox.org:993", "smtp.mailbox.org:465", ""),
    "t-online.de": ("secureimap.t-online.de:993", "securesmtp.t-online.de:465",
                    "Telekom: im Kundencenter ein eigenes E-Mail-Passwort anlegen"),
    "icloud.com": ("imap.mail.me.com:993", "smtp.mail.me.com:587", "Apple: appleid.apple.com → App-Passwörter"),
    "me.com": ("imap.mail.me.com:993", "smtp.mail.me.com:587", "Apple: appleid.apple.com → App-Passwörter"),
    "freenet.de": ("mx.freenet.de:993", "mx.freenet.de:465", ""),
    "ionos.de": ("imap.ionos.de:993", "smtp.ionos.de:465", ""),
    "outlook.de": ("outlook.office365.com:993", "smtp-mail.outlook.com:587",
                   "Microsoft lässt Programme oft nicht mehr mit Passwort hinein; dann ein anderes Postfach nehmen"),
    "outlook.com": ("outlook.office365.com:993", "smtp-mail.outlook.com:587",
                    "Microsoft lässt Programme oft nicht mehr mit Passwort hinein; dann ein anderes Postfach nehmen"),
    "hotmail.com": ("outlook.office365.com:993", "smtp-mail.outlook.com:587",
                    "Microsoft lässt Programme oft nicht mehr mit Passwort hinein; dann ein anderes Postfach nehmen"),
}

# Diese Einstellungen gehören zu Momo und werden übernommen; alles andere aus der Umgebung nicht
EIGENE = re.compile(r"^(MOMO_|RCLONE_CONFIG_|MISTRAL_|OPENAI_API_KEY$|GEMINI_API_KEY$|ANTHROPIC_API_KEY$|"
                    r"OPENROUTER_API_KEY$|GROQ_API_KEY$|CLAUDE_CODE_OAUTH_TOKEN$|MIT_CLAUDE$)")
GEHEIM = re.compile(r"(PASSWORT|PASS|KEY|SCHLUESSEL|TOKEN)$")
NICHT_UEBERNEHMEN = {"MOMO_DATEN", "MOMO_STIMME"}  # aus dem Abbild, nicht aus der .env


class Abbruch(Exception):
    pass


def verstaendlich(e: Exception) -> str:
    """Fehler in einem Satz, den man versteht; die Technik in Klammern dahinter."""
    roh = str(e)[:200]
    klein = roh.lower()
    art = getattr(e, "art", "")
    if art == "anmeldung" or "invalid api key" in klein:
        satz = "Der Schlüssel wird nicht angenommen. Ist er vollständig kopiert?"
    elif art == "limit":
        satz = "Der Zugang ist gesperrt oder das Guthaben ist leer."
    elif art == "voruebergehend":
        satz = "Der Dienst ist gerade nicht erreichbar. Stimmt die Adresse?"
    elif "authenticationfailed" in klein or "535" in klein or "login failed" in klein:
        satz = "Adresse oder Passwort stimmt nicht. Oft braucht es ein App-Passwort."
    elif "gaierror" in klein or "name or service not known" in klein or "connectionrefused" in klein:
        satz = "Der Server ist nicht erreichbar. Stimmt der Servername?"
    elif "401" in klein or "403" in klein:
        satz = "Benutzername oder Passwort wird nicht angenommen."
    else:
        return roh
    return f"{satz} ({roh})"


# ---------------------------------------------------------------- .env lesen und schreiben

def bisherige_werte(umgebung: dict) -> dict:
    return {k: v for k, v in umgebung.items() if EIGENE.match(k) and k not in NICHT_UEBERNEHMEN}


def _wert(v: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:@,+=\-]*", v):
        return v
    if "'" not in v:
        return f"'{v}'"  # in einfachen Anführungszeichen ersetzt docker compose nichts
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace("$", "$$") + '"'


ABSCHNITTE = [
    ("Momo", ["MOMO_NAME", "MOMO_BETREIBER", "MOMO_CHATMAIL_QR", "MOMO_BESITZER_ADRESSEN", "MOMO_VORLESEN",
              "MOMO_WHISPER", "MOMO_AUFHEBEN_TAGE", "MOMO_ABSENDER"]),
    ("KI (nur Text geht an die KI, nie Fotos)", ["MOMO_KI", "MOMO_KI_MODELL", "MOMO_KI_ADRESSE",
                                                 "MOMO_KI_SCHLUESSEL", "MOMO_KI_BEFEHL", "MOMO_KI_AUFWAND",
                                                 "MISTRAL_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                                                 "GEMINI_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "MIT_CLAUDE"]),
    ("Speicherort", ["MOMO_ABLAGE", "MOMO_ABLAGE_ZIEL"]),
    ("E-Mail (Entwürfe ins Postfach; Abschicken nur nach Bestätigung, wenn MOMO_MAIL_SENDEN=ja)",
     ["MOMO_MAIL_ADRESSE", "MOMO_MAIL_PASSWORT", "MOMO_MAIL_IMAP", "MOMO_MAIL_SMTP", "MOMO_MAIL_SENDEN"]),
]


def env_text(werte: dict) -> str:
    zeilen = [f"# Momo – geschrieben vom Einrichtungsassistenten am {time.strftime('%d.%m.%Y %H:%M')}.",
              "# Ändern: ./einrichten.sh noch einmal starten. Alle Möglichkeiten: .env.example", ""]
    erledigt = set()
    for titel, schluessel in ABSCHNITTE:
        teil = [f"{k}={_wert(werte[k])}" for k in schluessel if werte.get(k, "") != ""]
        erledigt.update(schluessel)
        if titel == "Speicherort":
            rclone = sorted(k for k in werte if k.startswith("RCLONE_CONFIG_") and werte[k] != "")
            teil += [f"{k}={_wert(werte[k])}" for k in rclone]
            erledigt.update(rclone)
        if teil:
            zeilen += [f"# {titel}", *teil, ""]
    rest = sorted(k for k in werte if k not in erledigt and werte[k] != "")
    if rest:
        zeilen += ["# Weitere Einstellungen", *(f"{k}={_wert(werte[k])}" for k in rest), ""]
    return "\n".join(zeilen)


def mail_server(adresse: str) -> tuple[str, str, str]:
    domain = adresse.rsplit("@", 1)[-1].lower()
    if domain in POSTFAECHER:
        return POSTFAECHER[domain]
    return f"imap.{domain}:993", f"smtp.{domain}:465", ""


def nextcloud_adresse(basis: str, benutzer: str) -> str:
    basis = basis.strip().rstrip("/")
    if not re.match(r"https?://", basis):
        basis = "https://" + basis
    basis = re.sub(r"/(index\.php.*|remote\.php.*|apps/.*)$", "", basis)
    return f"{basis}/remote.php/dav/files/{benutzer}"


# ---------------------------------------------------------------- Prüfungen (nichts wird verschickt)

def ki_pruefen(werte: dict) -> str:
    from momo.ki import Nachricht, anbieter_waehlen

    ki = anbieter_waehlen(werte.get("MOMO_KI", "keine"), {**os.environ, **werte})
    if ki.name == "keine":
        return "ohne KI"
    antwort = ki.fragen("Antworte nur mit dem Wort OK.", [Nachricht("nutzer", "Test")])
    if not (antwort or "").strip():
        raise RuntimeError("leere Antwort")
    return "die KI antwortet"


def ablage_pruefen(werte: dict) -> str:
    from momo.ablage import ablage_waehlen

    for k, v in werte.items():  # rclone liest seine Verbindung aus der Umgebung
        if k.startswith("RCLONE_CONFIG_"):
            os.environ[k] = v
    ablage = ablage_waehlen(werte.get("MOMO_ABLAGE", "ordner"), werte.get("MOMO_ABLAGE_ZIEL", "/daten/ablage"))
    ablage.pruefen()
    probe = f"Momo-Probe-{int(time.time())}.txt"
    ablage.schreiben(probe, b"Probe vom Einrichtungsassistenten")
    try:
        if ablage.lesen(probe) != b"Probe vom Einrichtungsassistenten":
            raise RuntimeError("Probedatei kam anders zurück")
    finally:
        ablage.loeschen(probe)
    return "Probedatei geschrieben, gelesen und wieder gelöscht"


def mail_pruefen(werte: dict) -> str:
    from momo import post

    zugang = post.Zugang.aus_umgebung(werte)
    if not zugang:
        return "keine E-Mail"
    ordner = post.Postfach(zugang, zeitlimit=30).pruefen()
    return f"Anmeldung klappt, Entwürfe landen in „{ordner}“" + (", Abschicken möglich" if zugang.senden else "")


# ---------------------------------------------------------------- Fragen

class Frager:
    def __init__(self, eingabe=None, geheim=None, aus=print):
        self.eingabe = eingabe or (lambda text: input(text))
        self.geheim_eingabe = geheim or (getpass.getpass if sys.stdin.isatty() else self.eingabe)
        self.aus = aus

    def _lesen(self, f, text):
        try:
            return f(text)
        except EOFError:
            raise Abbruch() from None

    def frage(self, text: str, vorgabe: str = "", pflicht: bool = False) -> str:
        while True:
            antwort = self._lesen(self.eingabe, f"{text}{f' [{vorgabe}]' if vorgabe else ''}: ").strip()
            antwort = antwort or vorgabe
            if antwort or not pflicht:
                return antwort
            self.aus("  Bitte etwas eingeben.")

    def geheim(self, text: str, vorhanden: str = "") -> str:
        zusatz = " [gespeichert, Enter = behalten]" if vorhanden else ""
        while True:
            antwort = self._lesen(self.geheim_eingabe, f"{text}{zusatz}: ").strip()
            if antwort or vorhanden:
                return antwort or vorhanden
            self.aus("  Bitte eingeben (wird nicht angezeigt).")

    def wahl(self, text: str, optionen: list[tuple[str, str]], vorgabe: str | None = None) -> str:
        """optionen: (Wert, Beschriftung). Antwort per Nummer."""
        if text:
            self.aus(text)
        for i, (wert, beschriftung) in enumerate(optionen, 1):
            self.aus(f"  {i}  {beschriftung}")
        nummern = {str(i): w for i, (w, _) in enumerate(optionen, 1)}
        standard = next((str(i) for i, (w, _) in enumerate(optionen, 1) if w == vorgabe), "")
        while True:
            antwort = self.frage("Nummer", standard)
            if antwort in nummern:
                return nummern[antwort]
            self.aus(f"  Bitte eine Zahl von 1 bis {len(optionen)}.")

    def ja(self, text: str, vorgabe: bool = True) -> bool:
        while True:
            a = self.frage(f"{text} (j/n)", "j" if vorgabe else "n").lower()
            if a in ("j", "ja", "y", "yes"):
                return True
            if a in ("n", "nein", "no"):
                return False


def _pruefen_bis_ok(f: Frager, name: str, pruefung, werte: dict, nochmal) -> None:
    """Prüft; bei Fehler: neu eingeben, trotzdem übernehmen oder abbrechen."""
    while True:
        f.aus(f"  Ich prüfe {name} …")
        try:
            f.aus(f"  ✓ {pruefung(werte)}")
            return
        except Abbruch:
            raise
        except Exception as e:  # noqa: BLE001 – jede Störung soll verständlich gemeldet werden
            f.aus(f"  ✗ Das klappt noch nicht: {verstaendlich(e)}")
        wahl = f.wahl("Was nun?", [("neu", "Angaben neu eingeben"), ("behalten", "Trotzdem so übernehmen"),
                                   ("ende", "Abbrechen, nichts speichern")], "neu")
        if wahl == "ende":
            raise Abbruch()
        if wahl == "behalten":
            return
        nochmal()


def ki_fragen(f: Frager, w: dict) -> None:
    f.aus("\n── 1. Welche KI? ──────────────────────────────────────────")
    f.aus("Die KI erklärt Briefe und schreibt Antworten. Sie bekommt nur Text, nie Fotos.")
    vorher = w.get("MOMO_KI", "") or "mistral"
    if vorher in ("openrouter", "groq"):
        vorher = "openai-kompatibel"
    name = f.wahl("", [(n, f"{titel} – {text}") for n, titel, text, _ in KIS], vorher)
    hinweis = next(h for n, _, _, h in KIS if n == name)
    w["MOMO_KI"] = name
    w.pop("MOMO_KI_OHNE_SCHLUESSEL", None)
    if name == "keine":
        return
    if name in ("ollama", "openai-kompatibel"):
        vorgabe = w.get("MOMO_KI_ADRESSE") or ("http://host.docker.internal:11434/v1" if name == "ollama" else "")
        if name == "ollama":
            f.aus("  Läuft Ollama auf diesem Rechner, passt die Adresse in Klammern.")
        w["MOMO_KI_ADRESSE"] = f.frage("Adresse (endet meist auf /v1)", vorgabe, pflicht=True)
    else:
        w.pop("MOMO_KI_ADRESSE", None)
    if name == "befehl":
        w["MOMO_KI_BEFEHL"] = f.frage("Befehl, z. B. ollama run llama3.1", w.get("MOMO_KI_BEFEHL", ""), pflicht=True)
        return
    if name != "ollama":
        if hinweis:
            f.aus(f"  {hinweis}")
        feld = SCHLUESSEL_FELD.get(name, "MOMO_KI_SCHLUESSEL")
        text = "Token" if name == "claude-abo" else "Schlüssel" + (" (leer lassen, wenn keiner nötig)"
                                                                   if name == "openai-kompatibel" else "")
        if name == "openai-kompatibel":
            w[feld] = f.frage(text, "") if not w.get(feld) else f.geheim(text, w[feld])
        else:
            w[feld] = f.geheim(text, w.get(feld) or (w.get("MOMO_KI_SCHLUESSEL", "") if feld != "MOMO_KI_SCHLUESSEL"
                                                      else ""))
            if feld != "MOMO_KI_SCHLUESSEL" and w.get("MOMO_KI_SCHLUESSEL") == w[feld]:
                w.pop("MOMO_KI_SCHLUESSEL")  # nur an einer Stelle aufheben
    standard = STANDARD_MODELL.get(name, "")
    modell = f.frage("Modell" + (" (Enter = Standard)" if standard else " (Name aus der Übersicht des Anbieters)"),
                     w.get("MOMO_KI_MODELL") or standard, pflicht=not standard)
    w["MOMO_KI_MODELL"] = "" if modell == standard else modell
    if name == "claude-abo":
        w["MIT_CLAUDE"] = "1"


def ablage_fragen(f: Frager, w: dict) -> None:
    f.aus("\n── 2. Wo sollen die Briefe liegen? ───────────────────────")
    vorher = w.get("MOMO_ABLAGE", "ordner")
    ziel = w.get("MOMO_ABLAGE_ZIEL", "")
    vorgabe = "ordner" if vorher == "ordner" else ("nextcloud" if ziel.lower().startswith("nextcloud:") else "rclone")
    art = f.wahl("", [("ordner", "In einem Ordner auf diesem Rechner (daten/ablage)"),
                      ("nextcloud", "In einer Nextcloud"),
                      ("rclone", "In einer anderen Cloud: Google Drive, iCloud Drive, OneDrive, Dropbox …")], vorgabe)
    if art == "ordner":
        w["MOMO_ABLAGE"], w["MOMO_ABLAGE_ZIEL"] = "ordner", "/daten/ablage"
        return
    w["MOMO_ABLAGE"] = "rclone"
    if art == "nextcloud":
        f.aus("  Am besten einen eigenen Nextcloud-Benutzer für Momo anlegen und dort ein App-Passwort erzeugen")
        f.aus("  (Einstellungen → Sicherheit → Neues App-Passwort).")
        alt_url = w.get("RCLONE_CONFIG_NEXTCLOUD_URL", "")
        basis = f.frage("Adresse der Nextcloud, z. B. https://cloud.beispiel.de",
                        alt_url.split("/remote.php")[0] if alt_url else "", pflicht=True)
        benutzer = f.frage("Benutzername", w.get("RCLONE_CONFIG_NEXTCLOUD_USER", ""), pflicht=True)
        alt_pass = w.get("RCLONE_CONFIG_NEXTCLOUD_PASS", "")
        passwort = f.geheim("App-Passwort", alt_pass)
        if passwort != alt_pass:  # neu eingegeben: rclone will es verschleiert
            passwort = subprocess.run(["rclone", "obscure", "-"], input=passwort.encode(), capture_output=True,
                                      check=True).stdout.decode().strip()
        w.update({"RCLONE_CONFIG_NEXTCLOUD_TYPE": "webdav", "RCLONE_CONFIG_NEXTCLOUD_VENDOR": "nextcloud",
                  "RCLONE_CONFIG_NEXTCLOUD_URL": nextcloud_adresse(basis, benutzer),
                  "RCLONE_CONFIG_NEXTCLOUD_USER": benutzer, "RCLONE_CONFIG_NEXTCLOUD_PASS": passwort})
        ordner = f.frage("Ordner in der Nextcloud (leer = oberste Ebene)",
                         ziel.split(":", 1)[1] if ziel.lower().startswith("nextcloud:") else "Momo")
        w["MOMO_ABLAGE_ZIEL"] = f"nextcloud:{ordner}"
        return
    f.aus("  Gleich öffnet sich rclone. Dort: n (neue Verbindung), einen kurzen Namen wie „drive“ eingeben,")
    f.aus("  den Dienst aus der Liste wählen und den Fragen folgen. Bei „Use web browser“ zeigt rclone,")
    f.aus("  wie die Anmeldung auf einem anderen Rechner geht. Am Ende q zum Beenden.")
    if not f.ja("Ist die Verbindung schon eingerichtet?",
                vorgabe=":" in ziel and not ziel.lower().startswith("nextcloud:")):
        subprocess.run(["rclone", "config"])
    f.aus("  Ziel in der Form name:Ordner, z. B. drive:Momo")
    w["MOMO_ABLAGE_ZIEL"] = f.frage("Ziel", ziel if ":" in ziel else "", pflicht=True)


def mail_fragen(f: Frager, w: dict) -> None:
    f.aus("\n── 3. E-Mail (freiwillig) ────────────────────────────────")
    f.aus("Momo kann fertige Antwortbriefe als E-Mail mit PDF bei den Entwürfen ins Postfach legen.")
    if not f.ja("Postfach einrichten?", vorgabe=bool(w.get("MOMO_MAIL_ADRESSE"))):
        for k in ("MOMO_MAIL_ADRESSE", "MOMO_MAIL_PASSWORT", "MOMO_MAIL_IMAP", "MOMO_MAIL_SMTP", "MOMO_MAIL_SENDEN"):
            w.pop(k, None)
        return
    adresse = f.frage("E-Mail-Adresse", w.get("MOMO_MAIL_ADRESSE", ""), pflicht=True)
    imap, smtp, hinweis = mail_server(adresse)
    if adresse != w.get("MOMO_MAIL_ADRESSE"):
        w.pop("MOMO_MAIL_IMAP", None), w.pop("MOMO_MAIL_SMTP", None)
    f.aus("  Am besten ein App-Passwort, nicht das normale Passwort." + (f" {hinweis}" if hinweis else ""))
    w["MOMO_MAIL_ADRESSE"] = adresse
    w["MOMO_MAIL_PASSWORT"] = f.geheim("Passwort", w.get("MOMO_MAIL_PASSWORT", ""))
    w["MOMO_MAIL_IMAP"] = f.frage("IMAP-Server", w.get("MOMO_MAIL_IMAP") or imap, pflicht=True)
    f.aus("  Abschicken: Momo liest Empfänger und Betreff vor und schickt nur, wenn die Person")
    f.aus("  direkt auf genau diese E-Mail mit „Ja, abschicken“ antwortet.")
    senden = f.ja("Darf Momo nach dieser Bestätigung selbst abschicken?",
                  vorgabe=w.get("MOMO_MAIL_SENDEN", "").lower() in ("ja", "1", "true"))
    w["MOMO_MAIL_SENDEN"] = "ja" if senden else "nein"
    if senden:
        w["MOMO_MAIL_SMTP"] = f.frage("SMTP-Server", w.get("MOMO_MAIL_SMTP") or smtp, pflicht=True)


def sonstiges_fragen(f: Frager, w: dict) -> None:
    f.aus("\n── 4. Momo selbst ────────────────────────────────────────")
    w["MOMO_NAME"] = f.frage("Name im Chat", w.get("MOMO_NAME") or "Momo")
    w["MOMO_BETREIBER"] = f.frage("Wer betreibt Momo? (steht im Datenschutz-Hinweis, z. B. dein Vorname)",
                                  w.get("MOMO_BETREIBER", ""), pflicht=True)
    vorlesen = f.ja("Jede Antwort auch als Sprachnachricht?", vorgabe=w.get("MOMO_VORLESEN", "immer") != "nie")
    w["MOMO_VORLESEN"] = "immer" if vorlesen else "nie"


def uebersicht(w: dict) -> list[str]:
    zeilen = []
    for k in sorted(w):
        if w[k] == "":
            continue
        zeilen.append(f"  {k} = {'••••••' if GEHEIM.search(k) else w[k]}")
    return zeilen


def ablauf(f: Frager, w: dict, pruefen=True) -> dict:
    f.aus("Momo einrichten. Enter übernimmt den Wert in [Klammern]. Strg+C bricht ab, dann bleibt alles, wie es war.")
    ki_fragen(f, w)
    if pruefen:
        _pruefen_bis_ok(f, "die KI", ki_pruefen, w, lambda: ki_fragen(f, w))
    ablage_fragen(f, w)
    if pruefen:
        _pruefen_bis_ok(f, "den Speicherort", ablage_pruefen, w, lambda: ablage_fragen(f, w))
    mail_fragen(f, w)
    if pruefen and w.get("MOMO_MAIL_ADRESSE"):
        _pruefen_bis_ok(f, "das Postfach", mail_pruefen, w, lambda: mail_fragen(f, w))
    sonstiges_fragen(f, w)
    w.setdefault("MOMO_CHATMAIL_QR", "dcaccount:nine.testrun.org")
    w.setdefault("MOMO_AUFHEBEN_TAGE", "30")
    f.aus("\n── Zusammenfassung ───────────────────────────────────────")
    for z in uebersicht(w):
        f.aus(z)
    if not f.ja("So speichern?"):
        raise Abbruch()
    return w


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ziel", default="/daten/einrichtung.env")
    p.add_argument("--ohne-pruefung", action="store_true", help="Zugänge nicht prüfen")
    a = p.parse_args(argv)
    f = Frager()
    try:
        werte = ablauf(f, bisherige_werte(dict(os.environ)), pruefen=not a.ohne_pruefung)
    except (Abbruch, KeyboardInterrupt):
        f.aus("\nAbgebrochen. Nichts wurde geändert.")
        return 1
    ziel = Path(a.ziel)
    alt = os.umask(0o077)
    try:
        ziel.write_text(env_text(werte))
    finally:
        os.umask(alt)
    f.aus("\nGespeichert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
