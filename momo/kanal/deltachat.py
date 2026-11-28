"""Delta Chat: Ende-zu-Ende verschlüsselt, ohne Telefonnummer, über einen chatmail-Server. Mit Mini-App (webxdc)."""

import logging

from deltachat_rpc_client import Bot, DeltaChat, Rpc, events
from deltachat_rpc_client.const import EventType, ViewType

from . import Eingang, Kanal, einladung_ablegen

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


class DeltaChatKanal(Kanal):
    name = "deltachat"
    app_moeglich = True
    loescht_selbst = True

    def __init__(self, konfig):
        self.konfig = konfig
        self.konto = None

    def get_chat_by_id(self, chat_id):
        return self.konto.get_chat_by_id(chat_id)

    def get_message_by_id(self, nachricht_id):
        return self.konto.get_message_by_id(nachricht_id)

    def verlauf_loeschen(self, chat) -> bool:
        self.konto.delete_messages(chat.get_messages())
        return False  # beim Menschen bleibt der Chat, bis die Aufbewahrungsfrist greift

    @staticmethod
    def eingang(s) -> Eingang:
        absender = s.sender.get_snapshot()
        zitat = getattr(s, "quote", None) or {}
        return Eingang(
            kontakt=absender.id, adresse=absender.address, vertraut=bool(absender.is_key_contact), chat=s.chat,
            art=art_von(s.view_type), text=s.text or "", file=s.file or None,
            file_mime=getattr(s, "file_mime", None), file_name=getattr(s, "file_name", None),
            zitiert=zitat.get("message_id") if zitat.get("kind") == "WithMessage" else None)

    def _konto_einrichten(self, dc: DeltaChat):
        konten = dc.get_all_accounts()
        konto = konten[0] if konten else dc.add_account()
        if not konto.is_configured():
            log.info("Richte Delta-Chat-Konto ein über %s …", self.konfig.chatmail_qr)
            konto.set_config("bot", "1")
            konto.set_config("displayname", self.konfig.name)
            konto.add_transport_from_qr(self.konfig.chatmail_qr)
        # Chat (mit Fotos und Sprachnachrichten) bei Momo nach der Frist löschen; Briefe liegen im Speicherort
        konto.set_config("delete_device_after", str(self.konfig.aufheben_tage * 86400))
        return konto

    def starten(self, bote) -> None:
        self.konfig.dc_ordner.mkdir(parents=True, exist_ok=True)
        with Rpc(accounts_dir=str(self.konfig.dc_ordner / "konten")) as rpc:
            self.konto = self._konto_einrichten(DeltaChat(rpc))
            bote._konto = self
            haken = events.HookCollection()
            haken.on(events.NewMessage(is_info=False))(lambda e: bote.bei_eingang(self.eingang(e.message_snapshot)))
            haken.on(events.RawEvent(EventType.WEBXDC_STATUS_UPDATE))(bote._bei_app)
            bot = Bot(self.konto, haken)
            bote.nebenher_starten(self)
            if bote.besitzer.gekoppelt:
                log.info("Mit Besitzer gekoppelt (Kontakt %s).", bote.besitzer.kontakt_id)
                bote._einladung_entfernen()
            else:
                link, svg = self.konto.get_qr_code_svg()
                einladung_ablegen(self.konfig.daten, link, svg)
                log.warning("NOCH NICHT GEKOPPELT. QR-Code: einladung.svg im Datenordner. "
                            "Mit Delta Chat scannen und 'Hallo' schreiben. Link:\n\n    %s\n", link)
            bot.run_forever()

