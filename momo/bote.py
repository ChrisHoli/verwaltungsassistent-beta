"""Delta-Chat-Anbindung: Konto einrichten, Einladung zeigen, Besitzer prüfen, antworten.

Muster aus einer bewährten Delta-Chat-Brücke übernommen. Im Log nie Nachrichteninhalte.
"""

import logging
import threading
import time
from pathlib import Path

from deltachat_rpc_client import Bot, DeltaChat, Rpc, events
from deltachat_rpc_client.const import ViewType

from .ablage import AblageFehler
from .antworten import (BRIEF_ERSTE_SEITE, BRIEF_FEHLER, BRIEF_WEITERE_SEITE, DATEI_UNBEKANNT,
                        Antwort)
from .briefe import Briefablage, endung_fuer
from .aufnahme import SCHLECHTES_FOTO, aufnehmen
from .erklaeren import erklaerung
from .besitzer import Besitzer
from .gespraech import FEHLER, Gespraech
from .ki import KiFehler
from .lesen import brief_ist_schlecht, seiten_lesen
from .konfig import Konfig
from .stimme import Stimme

log = logging.getLogger(__name__)

LESEN_NACH_SEKUNDEN = 45

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
    def __init__(self, konfig: Konfig, stimme: Stimme, gespraech: Gespraech, briefe: Briefablage):
        self.konfig = konfig
        self.stimme = stimme
        self.gespraech = gespraech
        self.briefe = briefe
        self._lese_uhr: threading.Timer | None = None
        self._lese_sperre = threading.Lock()
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
        if art in ("bild", "datei") and s.file:
            antwort = self._brief_aufnehmen(s)
            if neu:
                self._senden(s.chat, self.gespraech.antworten("text", "Hallo", True))
            self._senden(s.chat, antwort)
            return
        self._senden(s.chat, self.gespraech.antworten(art, s.text or "", neu))

    def _brief_aufnehmen(self, s) -> Antwort:
        endung = endung_fuer(getattr(s, "file_mime", None), getattr(s, "file_name", None))
        if endung is None:
            log.info("Datei nicht verwendbar (Typ %s)", getattr(s, "file_mime", "?"))
            return Antwort(DATEI_UNBEKANNT)
        try:
            daten = Path(s.file).read_bytes()
            aufnahme = self.briefe.aufnehmen(daten, endung)
        except (OSError, AblageFehler) as e:
            log.error("Brief nicht gespeichert: %s", str(e)[:200])
            return Antwort(BRIEF_FEHLER)
        log.info("Brief gespeichert: %s Seite %s (%s KB)", aufnahme.vorgang, aufnahme.seite, len(daten) // 1024)
        self._lesen_planen(s.chat, aufnahme.vorgang)
        if aufnahme.seite == 1:
            return Antwort(BRIEF_ERSTE_SEITE)
        return Antwort(BRIEF_WEITERE_SEITE.format(seite=aufnahme.seite))

    # --- Brief lesen (nach kurzer Pause, damit alle Seiten da sind) ---
    def _lesen_planen(self, chat, vorgang: str) -> None:
        if self._lese_uhr is not None:
            self._lese_uhr.cancel()
        self._lese_uhr = threading.Timer(LESEN_NACH_SEKUNDEN, self._brief_lesen, args=(chat, vorgang))
        self._lese_uhr.daemon = True
        self._lese_uhr.start()

    def _brief_lesen(self, chat, vorgang: str) -> None:
        with self._lese_sperre:
            try:
                seiten = seiten_lesen(self.briefe.originale(vorgang))
                log.info("Texterkennung %s: %s Seiten, %s Zeichen", vorgang, len(seiten),
                         sum(len(s) for s in seiten))
                if brief_ist_schlecht(seiten):
                    self.briefe.ergebnis_ablegen(vorgang, seiten, None)
                    self._senden(chat, Antwort(SCHLECHTES_FOTO))
                    return
                try:
                    ergebnis = aufnehmen(self.gespraech.ki, seiten)
                except KiFehler as e:
                    log.error("KI beim Lesen: %s (%s)", e.art, str(e)[:200])
                    self.briefe.ergebnis_ablegen(vorgang, seiten, None)
                    self._senden(chat, Antwort(FEHLER.get(e.art, FEHLER["sonstig"])))
                    return
                self.briefe.ergebnis_ablegen(vorgang, seiten, ergebnis)
                log.info("Brief gelesen %s: pruefen=%s, verdacht=%s, fristen=%s", vorgang, ergebnis["pruefen"],
                         ergebnis["verdacht_manipulation"], len(ergebnis["fristen"]))
                antwort = erklaerung(ergebnis, seiten)
                self.gespraech.merken("momo", antwort.text)
                self._senden(chat, antwort)
            except Exception:
                log.exception("Brief lesen fehlgeschlagen (%s)", vorgang)
                self._senden(chat, Antwort(FEHLER["sonstig"]))

    # --- Senden ---
    def _senden(self, chat, antwort: Antwort) -> None:
        datei = None
        if antwort.vorlesen and self.konfig.vorlesen == "immer":
            datei = self.stimme.sprechen(antwort.zum_vorlesen, self.tmp)
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
