"""Telegram über die Bot-Schnittstelle (Bot bei @BotFather anlegen, Zugangsschlüssel in MOMO_TELEGRAM_TOKEN).

Achtung Datenschutz: Bot-Chats sind bei Telegram nicht Ende-zu-Ende-verschlüsselt; Telegram sieht Fotos und Texte.
Koppeln: Die Einladung ist ein Link t.me/<bot>?start=<Geheimcode>. Wer ihn zuerst öffnet und „Starten“ tippt, wird
Besitzer. Der Schlüssel steht in jeder Adresse – deshalb protokolliert httpx nichts (siehe __main__).
"""

import json
import logging
import secrets
import subprocess
import time
from pathlib import Path

import httpx

from . import SPRACHE, Eingang, Gesendet, Kanal, einladung_ablegen

log = logging.getLogger(__name__)

TEXT_MAX = 4000      # Telegram erlaubt 4096 Zeichen je Nachricht
UNTERTITEL_MAX = 1000  # 1024 für Bildunterschriften


class TelegramFehler(RuntimeError):
    pass


class Api:
    def __init__(self, token: str, client: httpx.Client | None = None, adresse: str = "https://api.telegram.org"):
        if not token:
            raise ValueError("MOMO_TELEGRAM_TOKEN fehlt (Bot bei @BotFather anlegen)")
        self.basis = f"{adresse}/bot{token}"
        self.dateien = f"{adresse}/file/bot{token}"
        self.client = client or httpx.Client(timeout=70)

    def __call__(self, methode: str, daten: dict | None = None, dateien: dict | None = None):
        try:
            r = self.client.post(f"{self.basis}/{methode}", data=daten if dateien else None,
                                 json=None if dateien else (daten or {}), files=dateien)
            antwort = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise TelegramFehler(f"{methode}: {type(e).__name__}") from None  # Adresse enthält den Schlüssel
        if not antwort.get("ok"):
            raise TelegramFehler(f"{methode}: {antwort.get('error_code')} {str(antwort.get('description'))[:150]}")
        return antwort["result"]

    def herunterladen(self, file_id: str, ziel: Path) -> Path:
        pfad = self("getFile", {"file_id": file_id})["file_path"]
        try:
            r = self.client.get(f"{self.dateien}/{pfad}")
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise TelegramFehler(f"Datei laden: {type(e).__name__}") from None
        ziel = ziel.with_suffix(Path(pfad).suffix or ziel.suffix)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(r.content)
        return ziel


def _als_ogg(datei: Path) -> Path | None:
    """Sprachnachrichten will Telegram als OGG/Opus."""
    ziel = datei.with_suffix(".ogg")
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(datei), "-c:a", "libopus", "-b:a", "32k",
                        str(ziel)], check=True, capture_output=True, timeout=60)
        return ziel
    except (OSError, subprocess.SubprocessError):
        return None


class TelegramChat:
    def __init__(self, api: Api, chat_id: int):
        self.api = api
        self.id = chat_id

    def accept(self) -> None:
        pass

    def send_text(self, text: str) -> Gesendet:
        text = text or " "
        erste = None
        for i in range(0, len(text), TEXT_MAX):
            r = self.api("sendMessage", {"chat_id": self.id, "text": text[i:i + TEXT_MAX]})
            erste = erste or r["message_id"]
        return Gesendet(erste)

    def send_message(self, text: str | None = None, file: str | None = None, viewtype: str | None = None) -> Gesendet:
        if file is None:
            return self.send_text(text or "")
        pfad = Path(file)
        if viewtype == SPRACHE:
            ogg = _als_ogg(pfad)
            if ogg is not None:
                # Text zuerst: auf ihn antwortet der Mensch („passt“); die Sprachnachricht hängt daran
                gesendet = self.send_text(text) if text else None
                with ogg.open("rb") as f:
                    r = self.api("sendVoice", {"chat_id": self.id}, {"voice": (ogg.name, f, "audio/ogg")})
                ogg.unlink(missing_ok=True)
                return gesendet or Gesendet(r["message_id"])
        daten = {"chat_id": self.id}
        if text:
            daten["caption"] = text[:UNTERTITEL_MAX]
        with pfad.open("rb") as f:
            r = self.api("sendDocument", daten, {"document": (pfad.name, f)})
        if text and len(text) > UNTERTITEL_MAX:
            self.send_text(text)
        return Gesendet(r["message_id"])


class TelegramKanal(Kanal):
    name = "telegram"

    def __init__(self, konfig, token: str, api: Api | None = None):
        self.konfig = konfig
        self.api = api or Api(token)
        self.stand_datei = Path(konfig.daten) / "telegram.json"
        self.tmp = Path(konfig.daten) / "tmp"

    # --- Stand: nächste Update-Nummer und Einladungscode ---
    def _stand(self) -> dict:
        try:
            return json.loads(self.stand_datei.read_text())
        except (FileNotFoundError, ValueError):
            return {}

    def _stand_setzen(self, **werte) -> None:
        d = {**self._stand(), **werte}
        tmp = self.stand_datei.with_suffix(".neu")
        tmp.write_text(json.dumps(d))
        tmp.replace(self.stand_datei)

    def einladungscode(self) -> str:
        code = self._stand().get("code")
        if not code:
            code = secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16]
            self._stand_setzen(code=code)
        return code

    def get_chat_by_id(self, chat_id):
        return TelegramChat(self.api, chat_id)

    # --- Empfangen ---
    def eingang(self, m: dict, gekoppelt: bool) -> Eingang | None:
        von = m.get("from") or {}
        chat = m.get("chat") or {}
        if chat.get("type") != "private" or von.get("is_bot"):
            return None
        text = m.get("text") or m.get("caption") or ""
        vertraut = False
        start = text.strip().split()
        if start and start[0] == "/start":
            code = start[1] if len(start) > 1 else ""
            vertraut = not gekoppelt and secrets.compare_digest(code, self.einladungscode())
            text = "Hallo"
        elif text.startswith("/"):
            text = text[1:]
        art, file_id, mime, name = "text", None, None, None
        if m.get("photo"):
            art, file_id, mime = "bild", m["photo"][-1]["file_id"], "image/jpeg"
        elif m.get("document"):
            d = m["document"]
            art, file_id, mime, name = "datei", d["file_id"], d.get("mime_type"), d.get("file_name")
            if (mime or "").startswith("image/"):
                art = "bild"
        elif m.get("voice") or m.get("audio"):
            d = m.get("voice") or m.get("audio")
            art, file_id, mime = "sprache", d["file_id"], d.get("mime_type") or "audio/ogg"
        elif not text:
            art = "sonst"
        e = Eingang(kontakt=von.get("id"), adresse=("@" + von["username"]) if von.get("username") else str(von.get("id")),
                    vertraut=vertraut, chat=TelegramChat(self.api, chat["id"]), art=art, text=text,
                    file_mime=mime, file_name=name,
                    zitiert=(m.get("reply_to_message") or {}).get("message_id"))
        if file_id:
            e.file = str(self.api.herunterladen(file_id, self.tmp / f"telegram-{m.get('message_id')}.bin"))
        return e

    def einmal_abholen(self, bote, wartezeit: int = 50) -> int:
        stand = self._stand()
        updates = self.api("getUpdates", {"offset": stand.get("naechste", 0), "timeout": wartezeit,
                                          "allowed_updates": ["message"]})
        for u in updates:
            self._stand_setzen(naechste=u["update_id"] + 1)  # vorher: eine kaputte Nachricht blockiert nicht ewig
            m = u.get("message")
            if not m:
                continue
            try:
                e = self.eingang(m, bote.besitzer.gekoppelt)
                if e is not None:
                    bote.bei_eingang(e)
            except Exception:
                log.exception("Telegram-Nachricht nicht verarbeitet")
        return len(updates)

    def starten(self, bote) -> None:
        ich = self.api("getMe")
        self.api("deleteWebhook", {"drop_pending_updates": False})
        log.info("Telegram-Bot @%s verbunden", ich.get("username"))
        bote._konto = self
        bote.nebenher_starten(self)
        if bote.besitzer.gekoppelt:
            bote._einladung_entfernen()
        else:
            link = f"https://t.me/{ich['username']}?start={self.einladungscode()}"
            einladung_ablegen(Path(self.konfig.daten), link)
            log.warning("NOCH NICHT GEKOPPELT. Einladung: einladung.txt im Datenordner "
                        "(python -m tools.einladung zeigt den QR-Code).")
        pause = 1
        while True:
            try:
                self.einmal_abholen(bote)
                pause = 1
            except TelegramFehler as e:
                log.warning("Telegram: %s – neuer Versuch in %s s", e, pause)
                time.sleep(pause)
                pause = min(pause * 2, 300)
