"""Signal über signal-cli-rest-api (eigener Container `signal`, nur im internen Docker-Netz erreichbar).

Signal hat keine offizielle Bot-Schnittstelle. Momo braucht deshalb eine eigene Signal-Nummer: Auf einem Handy mit
dieser Nummer läuft Signal, und Momo wird dort als „verknüpftes Gerät“ hinzugefügt (der Assistent zeigt den Code).
Ende-zu-Ende verschlüsselt; die Schlüssel liegen im Container `signal` auf dem Server.

Koppeln: Ist MOMO_BESITZER_ADRESSEN gesetzt (Telefonnummer der Person), nur diese Nummer. Sonst wird Besitzer,
wer zuerst schreibt – die Nummer von Momo also erst weitergeben, wenn alles eingerichtet ist.
Nachrichten-IDs sind bei Signal Zeitstempel (Millisekunden); ein Zitat verweist auf den Zeitstempel.
"""

import base64
import logging
import mimetypes
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from . import Eingang, Gesendet, Kanal, einladung_ablegen

log = logging.getLogger(__name__)


class SignalFehler(RuntimeError):
    pass


class Api:
    def __init__(self, adresse: str, nummer: str, client: httpx.Client | None = None):
        if not nummer:
            raise ValueError("MOMO_SIGNAL_NUMMER fehlt (Momos eigene Signal-Nummer, z. B. +4915112345678)")
        self.adresse = adresse.rstrip("/")
        self.nummer = nummer
        self.client = client or httpx.Client(timeout=90)

    def _pruefen(self, r: httpx.Response):
        if r.status_code >= 400:
            try:
                fehler = r.json().get("error", "")
            except ValueError:
                fehler = r.text
            raise SignalFehler(f"{r.request.method} {r.request.url.path.split('/')[2]}: {r.status_code} "
                               f"{str(fehler)[:150]}")
        return r

    def empfangen(self, wartezeit: int = 30) -> list[dict]:
        try:
            r = self.client.get(f"{self.adresse}/v1/receive/{quote(self.nummer)}",
                                params={"timeout": str(wartezeit), "ignore_stories": "true"}, timeout=wartezeit + 30)
        except httpx.HTTPError as e:
            raise SignalFehler(f"empfangen: {type(e).__name__}") from None
        return self._pruefen(r).json() or []

    def anhang(self, anhang_id: str) -> bytes:
        try:
            return self._pruefen(self.client.get(f"{self.adresse}/v1/attachments/{quote(anhang_id)}")).content
        except httpx.HTTPError as e:
            raise SignalFehler(f"Anhang: {type(e).__name__}") from None

    def senden(self, empfaenger: str, text: str, anhaenge: list[Path] | None = None) -> int:
        daten = {"number": self.nummer, "recipients": [empfaenger], "message": text or ""}
        if anhaenge:
            daten["base64_attachments"] = [
                f"data:{mimetypes.guess_type(p.name)[0] or 'application/octet-stream'};filename={p.name};base64,"
                + base64.b64encode(p.read_bytes()).decode() for p in anhaenge]
        try:
            antwort = self._pruefen(self.client.post(f"{self.adresse}/v2/send", json=daten)).json()
        except httpx.HTTPError as e:
            raise SignalFehler(f"senden: {type(e).__name__}") from None
        if isinstance(antwort, list):
            antwort = antwort[0] if antwort else {}
        return int(antwort.get("timestamp") or 0)

    def verbinden_link(self, geraetename: str = "Momo") -> str:
        r = self.client.get(f"{self.adresse}/v1/qrcodelink/raw", params={"device_name": geraetename})
        return self._pruefen(r).json()["device_link_uri"]

    def konten(self) -> list[str]:
        r = self.client.get(f"{self.adresse}/v1/accounts")
        if r.status_code >= 400 and "accounts list" in r.text:
            return []  # frisch eingerichtet: noch gar kein Konto
        return self._pruefen(r).json() or []


class SignalChat:
    def __init__(self, api: Api, empfaenger: str):
        self.api = api
        self.id = empfaenger  # Telefonnummer oder UUID der Person

    def accept(self) -> None:
        pass

    def send_text(self, text: str) -> Gesendet:
        return Gesendet(self.api.senden(self.id, text))

    def send_message(self, text: str | None = None, file: str | None = None, viewtype: str | None = None) -> Gesendet:
        return Gesendet(self.api.senden(self.id, text or "", [Path(file)] if file else None))


class SignalKanal(Kanal):
    name = "signal"

    def __init__(self, konfig, nummer: str, adresse: str = "http://signal:8080", api: Api | None = None):
        self.konfig = konfig
        self.api = api or Api(adresse, nummer)
        self.tmp = Path(konfig.daten) / "tmp"

    def get_chat_by_id(self, chat_id):
        return SignalChat(self.api, chat_id)

    def eingang(self, umschlag: dict) -> Eingang | None:
        u = umschlag.get("envelope") or {}
        d = u.get("dataMessage")
        if not d or d.get("groupInfo") or d.get("groupV2"):
            return None  # Lesebestätigungen, Tippen, eigene Geräte, Gruppen
        absender = u.get("sourceUuid") or u.get("sourceNumber") or u.get("source")
        if not absender:
            return None
        nummer = u.get("sourceNumber") or u.get("source") or ""
        text = d.get("message") or ""
        art, file, mime, name = ("text" if text else "sonst"), None, None, None
        for a in d.get("attachments") or []:
            mime = a.get("contentType") or ""
            name = a.get("filename")
            endung = mimetypes.guess_extension(mime) or ".bin"
            ziel = self.tmp / f"signal-{a.get('id', 'anhang')}"
            ziel = ziel.with_suffix(endung) if not ziel.suffix else ziel
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_bytes(self.api.anhang(a["id"]))
            file = str(ziel)
            art = ("bild" if mime.startswith("image/") else "sprache" if mime.startswith("audio/") else "datei")
            break  # mehrere Fotos kommen bei Signal als eigene Nachrichten nicht vor; nur das erste zählt
        zitat = d.get("quote") or {}
        return Eingang(kontakt=absender, adresse=nummer, vertraut=True,
                       chat=SignalChat(self.api, nummer or absender), art=art, text=text,
                       file=file, file_mime=mime, file_name=name, zitiert=zitat.get("id"))

    def einmal_abholen(self, bote, wartezeit: int = 30) -> int:
        umschlaege = self.api.empfangen(wartezeit)
        for u in umschlaege:
            try:
                e = self.eingang(u)
                if e is not None:
                    bote.bei_eingang(e)
            except Exception:
                log.exception("Signal-Nachricht nicht verarbeitet")
        return len(umschlaege)

    def starten(self, bote) -> None:
        bote._konto = self
        bote.nebenher_starten(self)
        if bote.besitzer.gekoppelt:
            bote._einladung_entfernen()
        else:
            einladung_ablegen(Path(self.konfig.daten), f"https://signal.me/#p/{self.api.nummer}")
            log.warning("NOCH NICHT GEKOPPELT. Die Person schreibt „Hallo“ an %s… (Einladung: einladung.txt).",
                        self.api.nummer[:6])
        pause = 1
        while True:
            try:
                self.einmal_abholen(bote)
                pause = 1
            except SignalFehler as e:
                log.warning("Signal: %s – neuer Versuch in %s s", e, pause)
                time.sleep(pause)
                pause = min(pause * 2, 300)

