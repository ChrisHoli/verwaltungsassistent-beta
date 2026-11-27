"""Delta-Chat-Anbindung: Konto einrichten, Einladung zeigen, Besitzer prüfen, antworten.

Muster aus einer bewährten Delta-Chat-Brücke übernommen. Im Log nie Nachrichteninhalte.
"""

import logging
import time
from pathlib import Path

from deltachat_rpc_client import Bot, DeltaChat, Rpc, events
from deltachat_rpc_client.const import ViewType

from .antworten import Antwort
from .besitzer import Besitzer
from .gespraech import Gespraech
from .konfig import Konfig
from .stimme import Stimme

log = logging.getLogger(__name__)

ARTEN = {
    ViewType.TEXT: "text",
    ViewType.IMAGE: "bild",
    ViewType.GIF: "bild",
    ViewType.FILE: "datei",
    ViewType.VOICE: "sprache",
    ViewType.AUDIO: "sprache",
}


def art_von(view_type) -> str:
    try:
        return ARTEN.get(ViewType(view_type), "sonst")
    except ValueError:
        return "sonst"


class Bote:
    def __init__(self, konfig: Konfig, stimme: Stimme, gespraech: Gespraech):
        self.konfig = konfig
        self.stimme = stimme
        self.gespraech = gespraech
        self.besitzer = Besitzer(konfig.besitzer_adressen, konfig.daten / "besitzer.json")
        self.tmp = konfig.daten / "tmp"

    # --- Empfangen ---
    def _bei_nachricht(self, ereignis) -> None:
        s = ereignis.message_snapshot
        absender = s.sender.get_snapshot()
        erlaubt, neu = self.besitzer.pruefen(
            kontakt_id=absender.id,
            adresse=absender.address,
            verschluesselt=bool(absender.is_key_contact),
        )
        if not erlaubt:
            log.warning("Nachricht von fremdem Kontakt ignoriert (Kontakt %s, verschlüsselt: %s)",
                        absender.id, bool(absender.is_key_contact))
            return
        s.chat.accept()
        art = art_von(s.view_type)
        if neu:
            log.info("Besitzer gekoppelt (Kontakt %s).", absender.id)
            self._einladung_entfernen()
        log.info("Nachricht vom Besitzer: Art %s", art)
        self._senden(s.chat, self.gespraech.antworten(art, s.text or "", neu))

    # --- Senden ---
    def _senden(self, chat, antwort: Antwort) -> None:
        datei = None
        if antwort.vorlesen and self.konfig.vorlesen == "immer":
            datei = self.stimme.sprechen(antwort.text, self.tmp)
        if datei:
            chat.send_message(text=antwort.text, file=str(datei), viewtype=ViewType.VOICE)
        else:
            chat.send_text(antwort.text)

    # --- Start ---
    def _aufraeumen(self) -> None:
        if not self.tmp.exists():
            return
        grenze = time.time() - 86400
        for p in self.tmp.iterdir():
            if p.is_file() and p.stat().st_mtime < grenze:
                p.unlink(missing_ok=True)

    def _konto_einrichten(self, dc: DeltaChat):
        konten = dc.get_all_accounts()
        konto = konten[0] if konten else dc.add_account()
        if not konto.is_configured():
            log.info("Richte Delta-Chat-Konto ein über %s …", self.konfig.chatmail_qr)
            konto.set_config("bot", "1")
            konto.set_config("displayname", self.konfig.name)
            konto.add_transport_from_qr(self.konfig.chatmail_qr)
        return konto

    def _einladung_entfernen(self) -> None:
        for name in ("einladung.txt", "einladung.svg"):
            (self.konfig.daten / name).unlink(missing_ok=True)

    def _einladung_zeigen(self, konto) -> None:
        link, svg = konto.get_qr_code_svg()
        (self.konfig.daten / "einladung.txt").write_text(link + "\n")
        (self.konfig.daten / "einladung.svg").write_text(svg)
        log.warning(
            "NOCH NICHT GEKOPPELT. QR-Code: einladung.svg im Datenordner. "
            "Mit Delta Chat scannen und 'Hallo' schreiben. Link:\n\n    %s\n", link)

    def starten(self) -> None:
        self.konfig.dc_ordner.mkdir(parents=True, exist_ok=True)
        self._aufraeumen()
        with Rpc(accounts_dir=str(self.konfig.dc_ordner / "konten")) as rpc:
            konto = self._konto_einrichten(DeltaChat(rpc))
            haken = events.HookCollection()
            haken.on(events.NewMessage(is_info=False))(self._bei_nachricht)
            bot = Bot(konto, haken)
            if self.besitzer.gekoppelt:
                log.info("Mit Besitzer gekoppelt (Kontakt %s).", self.besitzer.kontakt_id)
                self._einladung_entfernen()
            else:
                self._einladung_zeigen(konto)
            bot.run_forever()
