"""Delta-Chat-Anbindung: Konto einrichten, Einladung zeigen, Besitzer prüfen, antworten.

Muster aus einer bewährten Delta-Chat-Brücke übernommen. Im Log nie Nachrichteninhalte.
"""

import logging
import re
from datetime import datetime
import threading
import time
from pathlib import Path

from deltachat_rpc_client import Bot, DeltaChat, Rpc, events
from deltachat_rpc_client.const import EventType, ViewType

from .ablage import AblageFehler
from . import saetze
from .antworten import (BRIEF_ERSTE_SEITE, BRIEF_FEHLER, BRIEF_WEITERE_SEITE, DATEI_UNBEKANNT, KEIN_BRIEF,
                        NICHT_VERSTANDEN, NOCH_NICHT, SPRACHE_AN, SPRACHE_AUS, Antwort)
from . import antwortbrief as ab
from . import datenschutz, miniapp
from . import fakten as fk
from . import post
from .erklaeren import zeichenweise
from .einstellungen import Einstellungen
from .woerter import frage_nach_wort
from .vorgaenge import ZEITZONE, ERLEDIGT, ERLEDIGT_ZITAT, JA, NEIN, Vorgaenge, erinnerung_text, frage_text, ueberblick_text
from .zuhoeren import Ohr, ZuhoerFehler
from .briefe import Briefablage, endung_fuer
from .aufnahme import SCHLECHTES_FOTO, aufnehmen, datum_lesbar
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
    def __init__(self, konfig: Konfig, stimme: Stimme, gespraech: Gespraech, briefe: Briefablage,
                 ohr: Ohr | None = None, postfach: "post.Postfach | None" = None):
        self.konfig = konfig
        self.stimme = stimme
        self.ohr = ohr
        self.postfach = postfach
        self.mail_datei = konfig.daten / "mail_entwurf.eml"
        self.einstellungen = Einstellungen(konfig.daten, konfig.vorlesen)
        self.vorgaenge = Vorgaenge(konfig.daten)
        self.fakten = fk.Fakten(konfig.daten)
        self.entwuerfe = ab.Entwuerfe(konfig.daten, konfig.absender, self.fakten)
        self._chat = None  # Chat der laufenden Nachricht, für Zwischenmeldungen und das PDF
        self._konto = None
        self.app_datei = konfig.daten / "app.json"
        self._app_sperre = threading.Lock()
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
        self.vorgaenge.chat_merken(s.chat.id)
        self._chat = s.chat
        zitat = getattr(s, "quote", None) or {}
        zitiert = zitat.get("message_id") if zitat.get("kind") == "WithMessage" else None
        if art in ("bild", "datei") and s.file:
            antwort = self._brief_aufnehmen(s)
            if neu:
                self._senden(s.chat, self.gespraech.antworten("text", "Hallo", True))
            self._senden(s.chat, antwort)
            return
        if art == "sprache" and s.file and not neu:
            self._senden(s.chat, self._zuhoeren(Path(s.file)))
            return
        self._senden(s.chat, self.antworten_auf(art, s.text or "", neu, zitiert))
        self._datenschutz_einmal(s.chat)

    def _datenschutz_hinweis(self) -> Antwort:
        k = self.konfig
        return Antwort(datenschutz.hinweis(k.ki, k.ablage, k.betreiber, k.aufheben_tage))

    def _datenschutz_einmal(self, chat) -> None:
        if not self.einstellungen.wert("datenschutz_gesagt"):
            self._senden(chat, self._datenschutz_hinweis())
            self.einstellungen.setzen("datenschutz_gesagt", True)

    # --- Sprechen statt tippen ---
    def _zuhoeren(self, datei: Path) -> Antwort:
        if self.ohr is None:
            return Antwort(NOCH_NICHT["sprache"])
        try:
            text = self.ohr.umschreiben(datei)
        except ZuhoerFehler as e:
            log.error("Zuhören fehlgeschlagen: %s", e)
            return Antwort(NICHT_VERSTANDEN)
        if len(text) < 2:
            return Antwort(NICHT_VERSTANDEN)
        antwort = self.antworten_auf("text", text, False)
        # Im Text steht dazu, was Momo verstanden hat – so fällt ein Hörfehler auf. Vorgelesen wird nur die Antwort.
        return Antwort(f"Ich habe verstanden: „{text}“\n\n{antwort.text}", vorlesen=antwort.vorlesen,
                       sprechtext=antwort.zum_vorlesen)

    def antworten_auf(self, art: str, text: str, neu: bool, zitiert: int | None = None) -> Antwort:
        """Wünsche wie „Lies mir den Brief noch mal vor“ erledigt Momo selbst, alles andere das Gespräch."""
        if art == "text" and not neu:
            antwort = self._datenschutz_antwort(text, zitiert)
            if antwort is not None:
                return antwort
        if art == "text" and not neu:
            antwort = self._frist_antwort(text, zitiert)
            if antwort is not None:
                return self._gemerkt(text, antwort)
        if art == "text" and not neu:
            antwort = self._fakten_antwort(text)
            if antwort is not None:
                return antwort
        if art == "text" and not neu:
            antwort = self._mail_antwort(text, zitiert)
            if antwort is not None:
                return antwort
        wunsch = saetze.erkennen(text) if art == "text" and not neu else None
        if art == "text" and not neu:
            aktiv = bool(self.entwuerfe.zustand())
            entwurf = self.entwuerfe.entwurf() if aktiv else None
            if entwurf is not None and wunsch == saetze.NOCHMAL:
                return self._gemerkt(text, self._vorlage_schicken(entwurf))
            if (aktiv and wunsch not in (saetze.SPRACHE_AN, saetze.SPRACHE_AUS)) or ab.ist_briefwunsch(text):
                antwort = self._antwortbrief(text, zitiert)
                if antwort is not None:
                    return antwort
        if wunsch == saetze.APP:
            gesendet = self._app_schicken(self._chat)
            return self._gemerkt(text, Antwort(
                "Hier ist deine Übersicht. Tipp sie an. Dort siehst du deine Briefe nach Bereichen sortiert "
                "und was bald wichtig ist." if gesendet else "Die Übersicht kann ich gerade nicht schicken."))
        if wunsch in (saetze.WOCHE, saetze.FRISTEN):
            tage = 7 if wunsch == saetze.WOCHE else None
            return self._gemerkt(text, Antwort(ueberblick_text(self.vorgaenge.kommend(tage), tage)))
        if wunsch == saetze.SPRACHE_AN:
            self.einstellungen.vorlesen = "immer"
            log.info("Einstellung: Vorlesen immer")
            return self._gemerkt(text, Antwort(SPRACHE_AN))
        if wunsch == saetze.SPRACHE_AUS:
            self.einstellungen.vorlesen = "nie"
            log.info("Einstellung: Vorlesen nie")
            return self._gemerkt(text, Antwort(SPRACHE_AUS))
        if wunsch == saetze.NOCHMAL:
            brief = self.einstellungen.letzter_brief()
            if brief is None:
                return self._gemerkt(text, Antwort(KEIN_BRIEF))
            # Nochmal vorlesen heißt: wirklich vorlesen, auch wenn sonst nur Text eingestellt ist
            return self._gemerkt(text, Antwort(brief.text, sprechtext=brief.sprechtext, immer_vorlesen=True))
        return self.gespraech.antworten(art, text, neu)

    def _frist_antwort(self, text: str, zitiert: int | None) -> Antwort | None:
        """Ja / Nein / erledigt auf Momos Frage nach einer Frist oder auf eine Erinnerung."""
        kurz = len(text.strip()) <= 60
        erledigt = ERLEDIGT_ZITAT if zitiert is not None else ERLEDIGT
        art = ("erledigt" if erledigt.search(text) else "ja" if JA.match(text) else
               "nein" if NEIN.match(text) else None) if kurz else None
        if art is None:
            return None
        frage = self.vorgaenge.frage_zu(zitiert)
        if frage is None and art == "erledigt" and zitiert is None:
            offen = self.vorgaenge.bestaetigte()
            if len(offen) == 1:
                frage = offen[0]
            elif offen:
                return Antwort("Ich erinnere dich an mehrere Dinge. Welches hast du erledigt? "
                               "Antworte bitte direkt auf meine Erinnerung dazu.")
        if frage is None:
            return None
        f = self.vorgaenge.frist(frage)
        tag = datum_lesbar(f["datum"])
        if art == "erledigt":
            self.vorgaenge.setzen(frage, "erledigt")
            self._app_auffrischen()
            log.info("Frist erledigt")
            return Antwort("Super, das hast du gut gemacht. Ich erinnere dich nicht mehr daran.")
        if art == "nein":
            if f["status"] == "bestaetigt":
                return Antwort(f"In Ordnung. Ich erinnere dich trotzdem noch einmal vor dem {tag}. "
                               "Wenn du es erledigt hast, sag: erledigt.")
            self.vorgaenge.setzen(frage, "abgelehnt")
            self._app_auffrischen()
            log.info("Frist abgelehnt")
            return Antwort("In Ordnung. Daran erinnere ich dich nicht.")
        if f["status"] == "bestaetigt":
            return Antwort(f"Gut. Ich denke an den {tag}.")
        self.vorgaenge.setzen(frage, "bestaetigt")
        self._app_auffrischen()
        self._uebersicht_ablegen()
        log.info("Frist bestätigt")
        if f["art"] == "wiedervorlage":
            return Antwort(f"Gut. Ich erinnere dich am {tag} an den Widerspruch.")
        return Antwort(f"Gut. Ich erinnere dich an den {tag}.")

    # --- Antwortbriefe (V9) ---
    def _brieftext(self, brief: dict) -> str:
        pfade = sorted(p for p in self.briefe.ablage.liste(f"{brief['vorgang']}/text") if p.endswith(".txt"))
        return "\n\n".join(f"=== Seite {i} ===\n" + self.briefe.ablage.lesen(p).decode(errors="replace")
                            for i, p in enumerate(pfade, start=1))

    def _welcher_brief(self, text: str) -> int | None:
        briefe = self.vorgaenge.daten["briefe"]
        klein = text.lower()
        for i in range(len(briefe) - 1, -1, -1):
            woerter = [w for w in re.findall(r"\w{4,}", (briefe[i].get("absender") or "").lower())]
            if any(w in klein for w in woerter):
                return i
        return len(briefe) - 1 if briefe else None

    def _zwischen(self, text: str) -> None:
        if self._chat is not None:
            try:
                self._chat.send_text(text)
            except Exception:
                log.warning("Zwischenmeldung nicht gesendet")

    def _vorlage_schicken(self, e: ab.Entwurf) -> Antwort:
        brief = self.vorgaenge.daten["briefe"][e.brief]
        text, sprechen = ab.vorlage(e, ab.teile(e, brief, self.entwuerfe.absender))
        self.entwuerfe.merken(e)
        return Antwort(text, sprechtext=sprechen, vorlage=True)

    def _entwerfen(self, nummer: int, wunsch: str, entwurf: ab.Entwurf | None = None) -> Antwort:
        brief = self.vorgaenge.daten["briefe"][nummer]
        self._zwischen("Ich schreibe deinen Brief. Das dauert einen Moment.")
        try:
            brieftext = self._brieftext(brief)
            gemerkt = self.fakten.als_text()
            e = (ab.aendern(self.gespraech.ki, entwurf, brief, brieftext, wunsch, gemerkt) if entwurf
                 else ab.entwerfen(self.gespraech.ki, brief, brieftext, wunsch, nummer, gemerkt))
        except KiFehler as f:
            log.error("KI beim Briefschreiben: %s", f.art)
            return Antwort(FEHLER.get(f.art, FEHLER["sonstig"]))
        except (ValueError, AblageFehler) as f:
            log.error("Brief schreiben fehlgeschlagen: %s", str(f)[:150])
            return Antwort("Das hat nicht geklappt. Sag mir bitte noch einmal, was im Brief stehen soll.")
        log.info("Antwortbrief entworfen (%s Zeichen, Anschrift sicher: %s)", len(e.text), e.anschrift_sicher)
        return self._vorlage_schicken(e)

    def _pdf_machen(self, e: ab.Entwurf) -> Antwort:
        brief = self.vorgaenge.daten["briefe"][e.brief]
        t = ab.teile(e, brief, self.entwuerfe.absender)
        stempel = datetime.now(ZEITZONE).strftime("%Y-%m-%d_%H%M")
        self.tmp.mkdir(parents=True, exist_ok=True)
        datei = ab.pdf(t, self.tmp / f"Antwort-{stempel}.pdf")
        try:
            self.briefe.ablage.schreiben(f"{brief['vorgang']}/antwortbriefe/antwort-{stempel}.pdf", datei.read_bytes())
        except AblageFehler as f:
            log.warning("Antwortbrief nicht in der Ablage: %s", str(f)[:150])
        self.entwuerfe.leeren()
        self.einstellungen.setzen("letzter_antwortbrief", {
            "brief": e.brief, "pdf": datei.name, "pdf_ablage": f"{brief['vorgang']}/antwortbriefe/antwort-{stempel}.pdf",
            "betreff": t["betreff"], "bezug": t["bezug"],
            "text": "\n\n".join([t["anrede"], t["text"], t["gruss"] + "\n" + t["name"]]), "zeit": time.time()})
        log.info("Antwortbrief als PDF fertig")
        hinweis = ("Hier ist dein Brief als PDF. Du kannst ihn ausdrucken, unterschreiben und abschicken. "
                   "Oder du lädst ihn hoch.")
        if self.postfach is not None:
            hinweis += " Ich kann ihn auch als E-Mail vorbereiten. Dann sag: Als E-Mail."
        if not e.anschrift_sicher:
            hinweis += " Denk daran: Die Adresse vom Amt musst du noch dazuschreiben."
        return Antwort(hinweis, datei=str(datei))

    def _antwortbrief(self, text: str, zitiert: int | None) -> Antwort | None:
        """Alles rund um Antwortbriefe. None = nicht zuständig."""
        z = self.entwuerfe.zustand()
        if z.get("warte") == "absender":
            zeilen = ab.absender_lesen(text)
            if zeilen is None:
                return self._gemerkt(text, Antwort(ab.ABSENDER_NOCHMAL))
            self.entwuerfe.absender = zeilen
            self.gespraech.merken("nutzer", text)
            if z.get("wunsch"):
                return self._entwerfen(z["brief"], z["wunsch"])
            self.entwuerfe.warten("inhalt", z["brief"])
            return Antwort("Danke. Jetzt sag mir, was im Brief stehen soll. Du kannst ganz normal sprechen.")
        if z.get("warte") == "inhalt":
            if ab.ABBRECHEN.match(text):
                self.entwuerfe.leeren()
                return self._gemerkt(text, Antwort("In Ordnung. Ich schreibe keinen Brief."))
            self.gespraech.merken("nutzer", text)
            return self._entwerfen(z["brief"], text)
        entwurf = self.entwuerfe.entwurf()
        if entwurf is not None:
            if ab.FREIGABE.match(text):
                if zitiert is None or zitiert != entwurf.vorlage_id:
                    return self._gemerkt(text, Antwort(
                        "Damit ich sicher weiß, welche Fassung du meinst: Antworte bitte direkt auf den Brief. "
                        "Halte die Nachricht mit dem Brief gedrückt und tipp auf Antworten. Dann sag: passt."))
                return self._gemerkt(text, self._pdf_machen(entwurf))
            if ab.ABBRECHEN.match(text):
                self.entwuerfe.leeren()
                return self._gemerkt(text, Antwort("In Ordnung. Den Brief lasse ich weg."))
            if zitiert == entwurf.vorlage_id or (zitiert is None and not text.rstrip().endswith("?")
                                                  and frage_nach_wort(text) is None):
                self.gespraech.merken("nutzer", text)
                return self._entwerfen(entwurf.brief, text, entwurf)
        if ab.ist_briefwunsch(text):
            nummer = self._welcher_brief(text)
            if nummer is None:
                return self._gemerkt(text, Antwort(
                    "Schick mir zuerst ein Foto von dem Brief, auf den du antworten willst."))
            if self.vorgaenge.daten["briefe"][nummer].get("verdacht"):
                return self._gemerkt(text, Antwort(
                    "Bei diesem Brief stimmt etwas nicht. Darauf schreibe ich keine Antwort. Zeig ihn bitte zuerst "
                    "einem Menschen, dem du vertraust, oder einer Beratungsstelle. Und überweise kein Geld."))
            inhalt = text if len(text.split()) > 6 and re.search(r"\b(dass|weil|ob)\b", text, re.I) else ""
            if not self.entwuerfe.absender:
                self.entwuerfe.warten("absender", nummer, inhalt)
                return self._gemerkt(text, Antwort(ab.ABSENDER_FRAGE))
            if inhalt:
                self.gespraech.merken("nutzer", text)
                return self._entwerfen(nummer, inhalt)
            self.entwuerfe.warten("inhalt", nummer)
            absender = self.vorgaenge.daten["briefe"][nummer].get("absender") or "das Amt"
            return self._gemerkt(text, Antwort(f"Gut. Ich schreibe eine Antwort an {absender}. Sag mir einfach, "
                                               "was drinstehen soll. Du kannst ganz normal sprechen."))
        return None

    # --- Mini-App (V10) ---
    def _app_lesen(self) -> dict:
        import json

        try:
            return json.loads(self.app_datei.read_text())
        except (FileNotFoundError, ValueError):
            return {}

    def _app_schreiben(self, d: dict) -> None:
        import json

        tmp = self.app_datei.with_suffix(".neu")
        tmp.write_text(json.dumps(d))
        tmp.replace(self.app_datei)

    def _app_id(self) -> int | None:
        return self._app_lesen().get("nachricht")

    def _app_schicken(self, chat) -> bool:
        if chat is None:
            return False
        try:
            datei = miniapp.xdc_bauen(self.tmp / "momo.xdc")
            nachricht = chat.send_message(file=str(datei))
            self._app_schreiben({"nachricht": nachricht.id, "serial": 0})
            nachricht.send_webxdc_status_update({"payload": miniapp.stand(self.vorgaenge)}, "")
            log.info("Mini-App geschickt")
            return True
        except Exception:
            log.exception("Mini-App nicht geschickt")
            return False

    def _app_auffrischen(self) -> None:
        app = self._app_id()
        if app is None or self._konto is None:
            return
        try:
            self._konto.get_message_by_id(app).send_webxdc_status_update({"payload": miniapp.stand(self.vorgaenge)}, "")
        except Exception as e:
            # z. B. nach der Aufbewahrungsfrist gelöscht: beim nächsten Brief schickt Momo eine neue
            log.warning("Mini-App nicht aufgefrischt, wird neu geschickt: %s", str(e)[:150])
            self.app_datei.unlink(missing_ok=True)

    def _bei_app(self, ereignis) -> None:
        """Bitten aus der Mini-App: vorlesen, erledigt, bestätigen, antworten."""
        app = self._app_lesen()
        if not app or ereignis.msg_id != app.get("nachricht"):
            return
        with self._app_sperre:
            nachricht = self._konto.get_message_by_id(app["nachricht"])
            updates = nachricht.get_webxdc_status_updates(app.get("serial", 0))
            if not updates:
                return
            app["serial"] = max(u.get("serial", 0) for u in updates)
            self._app_schreiben(app)
        chat = nachricht.get_snapshot().chat
        geaendert = False
        for b in miniapp.bitten(updates):
            briefe = self.vorgaenge.daten["briefe"]
            if not 0 <= b["brief"] < len(briefe):
                continue
            brief = briefe[b["brief"]]
            log.info("Bitte aus der Mini-App: %s", b["was"])
            if b["was"] == "vorlesen":
                e = brief.get("erklaerung") or {}
                if e.get("text"):
                    self._senden(chat, Antwort(e["text"], sprechtext=e.get("sprechtext"), immer_vorlesen=True))
            elif b["was"] == "antworten":
                if not brief.get("verdacht"):
                    self.entwuerfe.warten("absender" if not self.entwuerfe.absender else "inhalt", b["brief"])
                    self._senden(chat, Antwort(ab.ABSENDER_FRAGE if not self.entwuerfe.absender else
                                               f"Gut. Ich schreibe eine Antwort an {brief.get('absender') or 'das Amt'}. "
                                               "Sag mir einfach, was drinstehen soll."))
            elif b["was"] in ("erledigt", "bestaetigen") and b["frist"] is not None \
                    and 0 <= b["frist"] < len(brief["fristen"]):
                from .vorgaenge import Frage

                self.vorgaenge.setzen(Frage(b["brief"], b["frist"]),
                                      "erledigt" if b["was"] == "erledigt" else "bestaetigt")
                geaendert = True
        if geaendert:
            self._uebersicht_ablegen()
            self._app_auffrischen()

    def _uebersicht_ablegen(self) -> None:
        """Fristen als einfache Textdatei in den Speicherort, damit auch Helfer sie sehen."""
        try:
            text = ueberblick_text(self.vorgaenge.kommend(None), None) + "\n"
            self.briefe.ablage.schreiben("Fristen.txt", text.encode())
        except Exception as e:  # nicht wichtig genug, um etwas anderes aufzuhalten
            log.warning("Fristen-Übersicht nicht gespeichert: %s", str(e)[:150])

    # --- E-Mail: Entwurf ins Postfach, Abschicken nur nach Bestätigung ---
    MAIL_WUNSCH = re.compile(r"\b(als|per)\s+e-?mail\b|\b(e-?mail|mail)\b.{0,25}\b(schick|vorbereit|schreib|mach)"
                             r"|\bmail(e|en)?\s+(das|den brief|ihn)\b", re.I)
    ABSCHICKEN = re.compile(r"^\s*ja,?\s*(abschicken|absenden|senden|schick (sie|es|die mail) ab)[\s.!]*$", re.I)

    @staticmethod
    def _adresse_sprechbar(adresse: str) -> str:
        return (adresse.replace("@", " ät ").replace(".", " Punkt ").replace("-", " Strich ")
                .replace("_", " Unterstrich "))

    def _mail_antwort(self, text: str, zitiert: int | None) -> Antwort | None:
        zustand = self.einstellungen.wert("mail") or {}
        if self.ABSCHICKEN.match(text):
            frage = self.einstellungen.wert("mail_frage") or {}
            if not frage or not self.mail_datei.exists() or time.time() - frage.get("zeit", 0) > 86400:
                return Antwort("Ich habe gerade keine E-Mail zum Abschicken.")
            if zitiert != frage.get("id"):
                return self._gemerkt(text, Antwort(
                    "Damit ich sicher bin, welche E-Mail du meinst: Antworte bitte direkt auf meine Nachricht zur "
                    "E-Mail. Halte sie gedrückt, tipp auf Antworten und sag: Ja, abschicken."))
            from email import message_from_bytes, policy

            m = message_from_bytes(self.mail_datei.read_bytes(), policy=policy.default)
            try:
                self.postfach.senden(m)
            except post.PostFehler as f:
                log.error("E-Mail nicht gesendet: %s", str(f)[:200])
                return Antwort("Die E-Mail konnte ich nicht abschicken. Sie liegt weiter bei deinen Entwürfen. "
                               "Du kannst sie dort selbst abschicken.")
            self.mail_datei.unlink(missing_ok=True)
            self.einstellungen.setzen("mail_frage", None)
            log.info("E-Mail nach Bestätigung gesendet")
            return self._gemerkt(text, Antwort(f"Die E-Mail an {m['To']} ist abgeschickt.",
                                               sprechtext=f"Die E-Mail an {self._adresse_sprechbar(str(m['To']))} "
                                                          "ist abgeschickt."))
        if zustand.get("warte") == "empfaenger" and time.time() - zustand.get("zeit", 0) < 3600:
            if ab.ABBRECHEN.match(text):
                self.einstellungen.setzen("mail", None)
                return self._gemerkt(text, Antwort("In Ordnung. Keine E-Mail."))
            kandidaten = zustand.get("kandidaten") or []
            zahl = re.search(r"\b(\d|eins|zwei|drei|vier|fünf)\b", text.lower())
            zahlen = {"eins": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5}
            adresse = post.adresse_aus_gesprochenem(text)
            if adresse is None and zahl and kandidaten:
                n = int(zahl.group(1)) if zahl.group(1).isdigit() else zahlen[zahl.group(1)]
                if 1 <= n <= len(kandidaten):
                    adresse = kandidaten[n - 1]
            if adresse is None:
                return self._gemerkt(text, Antwort("Die Adresse habe ich nicht verstanden. Sag sie bitte so: "
                                                   "max punkt muster ät beispiel punkt de. Oder schreib sie mir."))
            self.einstellungen.setzen("mail", None)
            return self._gemerkt(text, self._mail_entwerfen(adresse, adresse in kandidaten))
        if not self.MAIL_WUNSCH.search(text):
            return None
        if self.postfach is None:
            return self._gemerkt(text, Antwort(
                "Für E-Mails brauche ich Zugang zu deinem E-Mail-Postfach. Den richtet der Betreiber ein. "
                "Bis dahin kannst du den PDF-Brief selbst an eine E-Mail anhängen."))
        letzter = self.einstellungen.wert("letzter_antwortbrief") or {}
        if not letzter or time.time() - letzter.get("zeit", 0) > 7 * 86400:
            return self._gemerkt(text, Antwort("Zuerst schreiben wir zusammen einen Brief. Sag zum Beispiel: "
                                               "Ich will der Versicherung antworten."))
        brief = self.vorgaenge.daten["briefe"][letzter["brief"]]
        try:
            kandidaten = post.adressen_im_text(self._brieftext(brief))
        except AblageFehler:
            kandidaten = []
        kandidaten = [k for k in kandidaten if k != (self.postfach.z.adresse or "").lower()][:5]
        if len(kandidaten) == 1:
            return self._gemerkt(text, self._mail_entwerfen(kandidaten[0], True))
        self.einstellungen.setzen("mail", {"warte": "empfaenger", "kandidaten": kandidaten, "zeit": time.time()})
        if kandidaten:
            liste = "\n".join(f"{i}. {k}" for i, k in enumerate(kandidaten, start=1))
            return self._gemerkt(text, Antwort(
                f"Im Brief stehen mehrere E-Mail-Adressen:\n{liste}\nWelche soll es sein? Sag die Nummer.",
                sprechtext="Im Brief stehen mehrere E-Mail-Adressen. " + " ".join(
                    f"Nummer {i}: {self._adresse_sprechbar(k)}." for i, k in enumerate(kandidaten, start=1))
                + " Welche soll es sein? Sag die Nummer."))
        return self._gemerkt(text, Antwort("Im Brief steht keine E-Mail-Adresse. An welche Adresse soll die E-Mail "
                                           "gehen? Sag sie mir oder schreib sie."))

    def _mail_entwerfen(self, an: str, aus_dem_brief: bool) -> Antwort:
        letzter = self.einstellungen.wert("letzter_antwortbrief") or {}
        name = self.fakten.wert("Name") or ""
        betreff = letzter.get("betreff", "Mein Schreiben")
        if letzter.get("bezug"):
            betreff += " – " + "; ".join(letzter["bezug"])
        try:
            pdf = self.briefe.ablage.lesen(letzter["pdf_ablage"])
        except (AblageFehler, KeyError):
            pdf = None
        text = letzter.get("text", "") + ("\n\nAnlage: mein Schreiben als PDF" if pdf else "")
        m = post.nachricht_bauen(name, self.postfach.z.adresse, an, betreff, text,
                                 (letzter.get("pdf", "Antwort.pdf"), pdf) if pdf else None)
        try:
            ordner = self.postfach.entwurf_ablegen(m)
        except post.PostFehler as f:
            log.error("E-Mail-Entwurf nicht abgelegt: %s", str(f)[:200])
            return Antwort("Ich komme gerade nicht an dein E-Mail-Postfach. Bitte versuch es später noch einmal.")
        self.mail_datei.write_bytes(m.as_bytes())
        log.info("E-Mail-Entwurf abgelegt (mit PDF: %s)", bool(pdf))
        herkunft = "Die Adresse steht im Brief." if aus_dem_brief else "Die Adresse hast du mir gesagt."
        satz = (f"Die E-Mail an {an} liegt jetzt in deinem Postfach bei „{ordner}“"
                + (", mit dem Brief als PDF." if pdf else ".") + f" {herkunft} Du kannst sie dort ansehen und "
                "selbst abschicken.")
        sprechen = (f"Die E-Mail an {self._adresse_sprechbar(an)} liegt jetzt in deinem Postfach bei den Entwürfen"
                    + (", mit dem Brief als PDF." if pdf else ".") + f" {herkunft} Du kannst sie dort ansehen und "
                    "selbst abschicken.")
        if self.postfach.z.senden:
            frage = (" Oder ich schicke sie für dich ab. Prüf vorher die Adresse. Wenn sie stimmt, antworte auf diese "
                     "Nachricht mit: Ja, abschicken.")
            return Antwort(satz + frage, sprechtext=sprechen + frage, merken_als="mail_frage")
        return Antwort(satz, sprechtext=sprechen)

    # --- Fakten über die Person ---
    @staticmethod
    def _sprechbar(wert: str) -> str:
        return zeichenweise(wert) if re.search(r"\d", wert) and "@" not in wert else wert

    def _fakten_antwort(self, text: str) -> Antwort | None:
        if fk.ALLES_ZEIGEN.search(text):
            alle = list(self.fakten.alle().values())
            if not alle:
                return self._gemerkt(text, Antwort("Ich habe mir noch nichts über dich gemerkt. Sag zum Beispiel: "
                                                   "Merk dir, meine Telefonnummer ist …"))
            zeilen = [f"{e['bezeichnung']}: {e['wert']}" for e in alle]
            return self._gemerkt(text, Antwort(
                "Das habe ich mir gemerkt:\n" + "\n".join(zeilen),
                sprechtext="Das habe ich mir gemerkt. " + " ".join(
                    f"{e['bezeichnung']}: {self._sprechbar(e['wert'])}." for e in alle)))
        v = fk.VERGESSEN.search(text)
        if v:
            e = self.fakten.finden(v.group(3))
            if e:
                self.fakten.vergessen(e["bezeichnung"])
                return self._gemerkt(text, Antwort(f"In Ordnung. {e['bezeichnung']} habe ich vergessen."))
        if fk.MERKEN.search(text) and len(text) > 12:
            try:
                eintraege = fk.aus_satz(self.gespraech.ki, text)
            except KiFehler as f:
                return Antwort(FEHLER.get(f.art, FEHLER["sonstig"]))
            self.gespraech.merken("nutzer", "(Momo soll sich etwas merken)")
            if not eintraege:
                return Antwort("Was soll ich mir merken? Sag zum Beispiel: Merk dir, meine Versichertennummer ist "
                               "A 1 2 3 4 5 6 7 8 9.")
            for b, w in eintraege:
                self.fakten.setzen(b, w)
            log.info("Fakten gemerkt: %s", len(eintraege))
            text_ = "Ich habe mir gemerkt:\n" + "\n".join(f"{b}: {w}" for b, w in eintraege)
            sprechen = "Ich habe mir gemerkt. " + " ".join(f"{b}: {self._sprechbar(w)}." for b, w in eintraege)
            schluss = " Wenn etwas falsch ist, sag es mir noch einmal richtig."
            return Antwort(text_ + "\n" + schluss.strip(), sprechtext=sprechen + schluss)
        f = fk.FRAGE.search(text)
        if f:
            e = self.fakten.finden(f.group(5))
            if e:
                return self._gemerkt(text, Antwort(f"{e['bezeichnung']}: {e['wert']}",
                                                   sprechtext=f"{e['bezeichnung']}: {self._sprechbar(e['wert'])}."))
        return None

    # --- Datenschutz: Hinweis und „Lösch alles von mir“ ---
    def _datenschutz_antwort(self, text: str, zitiert: int | None) -> Antwort | None:
        if datenschutz.LOESCH_JA.match(text):
            frage = self.einstellungen.wert("loesch_frage") or {}
            if not frage or time.time() - frage.get("zeit", 0) > 3600:
                return Antwort("Ich weiß nicht, was ich löschen soll. Wenn du alles löschen willst, sag: "
                               "Lösch alles von mir.")
            if zitiert != frage.get("id"):
                return Antwort("Damit ich sicher bin: Antworte bitte direkt auf meine Frage zum Löschen. "
                               "Halte sie gedrückt, tipp auf Antworten und sag: Ja, löschen.")
            self.alles_loeschen()
            return Antwort(datenschutz.LOESCH_FERTIG)
        if datenschutz.LOESCH_WUNSCH.search(text):
            self.gespraech.merken("nutzer", text)
            return Antwort(datenschutz.LOESCH_FRAGE, merken_als="loesch_frage")
        if datenschutz.DATENSCHUTZ_FRAGE.search(text):
            return self._gemerkt(text, self._datenschutz_hinweis())
        return None

    def alles_loeschen(self) -> None:
        """Briefe, Fristen, Entwürfe, Gespräch und Chatverlauf bei Momo löschen. Kopplung und Konto bleiben."""
        import shutil

        for pfad in ("Briefe", "Fristen.txt"):
            try:
                self.briefe.ablage.loeschen(pfad)
            except AblageFehler as e:
                log.error("Löschen im Speicherort unvollständig: %s", str(e)[:150])
        for name in datenschutz.PERSONENDATEIEN:
            (self.konfig.daten / name).unlink(missing_ok=True)
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.vorgaenge.daten = {"briefe": [], "chat": self.vorgaenge.chat}
        self.vorgaenge._sichern()
        self.gespraech.verlauf = []
        self.gespraech._sichern()
        self.einstellungen.setzen("datenschutz_gesagt", True)
        if self._chat is not None and self._konto is not None:
            try:
                self._konto.delete_messages(self._chat.get_messages())
            except Exception as e:
                log.warning("Chatverlauf bei Momo nicht gelöscht: %s", str(e)[:150])
        log.info("Alle Daten der Person gelöscht")

    def _gemerkt(self, frage: str, antwort: Antwort) -> Antwort:
        self.gespraech.merken("nutzer", frage)
        self.gespraech.merken("momo", antwort.text.split("\n")[0])
        return antwort

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
                log.info("Brief gelesen %s: pruefen=%s, verdacht=%s, fristen=%s", vorgang, ergebnis["pruefen"],
                         ergebnis["verdacht_manipulation"], len(ergebnis["fristen"]))
                bereich = "Zum Prüfen" if ergebnis["verdacht_manipulation"] else ergebnis["kategorie"]
                try:
                    vorgang = self.briefe.einsortieren(
                        vorgang, bereich, (ergebnis.get("absender") or {}).get("wert"),
                        (ergebnis.get("datum") or {}).get("wert"), ergebnis.get("betreff_kurz"))
                    ergebnis["ablage"] = vorgang
                    log.info("Brief einsortiert")  # Pfad nicht ins Log: er enthält Absender und Betreff
                except AblageFehler as e:
                    log.warning("Einsortieren fehlgeschlagen, bleibt im Eingang: %s", str(e)[:150])
                self.briefe.ergebnis_ablegen(vorgang, seiten, ergebnis)
                antwort = erklaerung(ergebnis, seiten)
                nummer = self.vorgaenge.brief_eintragen(vorgang, ergebnis)
                frueher = self.vorgaenge.frueher_zur_akte(nummer)
                if frueher:
                    zusatz = (f"Zu dieser Nummer hast du mir schon {len(frueher)} Brief geschickt." if len(frueher) == 1
                              else f"Zu dieser Nummer hast du mir schon {len(frueher)} Briefe geschickt.")
                    antwort = Antwort(antwort.text + "\n" + zusatz, sprechtext=antwort.zum_vorlesen + " " + zusatz)
                self.gespraech.merken("momo", antwort.text)
                self.einstellungen.brief_merken(antwort)
                self.vorgaenge.erklaerung_merken(nummer, antwort.text, antwort.sprechtext)
                self._senden(chat, antwort)
                self._fristen_fragen(chat, nummer)
                if self._app_id() is None:
                    if self._app_schicken(chat):
                        self._senden(chat, Antwort("Ich habe dir auch eine Übersicht geschickt. Tipp sie an. "
                                                   "Dort findest du alle deine Briefe, nach Bereichen sortiert."))
                else:
                    self._app_auffrischen()
            except Exception:
                log.exception("Brief lesen fehlgeschlagen (%s)", vorgang)
                self._senden(chat, Antwort(FEHLER["sonstig"]))

    def _fristen_fragen(self, chat, nummer: int) -> None:
        brief = self.vorgaenge.daten["briefe"][nummer]
        for k, f in enumerate(brief["fristen"][:3]):
            nachricht = self._senden(chat, Antwort(frage_text(brief, f)))
            if nachricht is not None:
                self.vorgaenge.frage_merken(nummer, k, nachricht.id)
        if brief["fristen"]:
            self._uebersicht_ablegen()

    # --- Erinnern (eigener Faden, schaut alle fünf Minuten) ---
    def _erinnern(self, konto) -> None:
        if self.vorgaenge.chat is None:
            return
        for frage, stufe in self.vorgaenge.faellig():
            brief = self.vorgaenge.daten["briefe"][frage.brief]
            heute = self.vorgaenge._heute()
            text = erinnerung_text(brief, self.vorgaenge.frist(frage), stufe, heute)
            nachricht = self._senden(konto.get_chat_by_id(self.vorgaenge.chat), Antwort(text))
            self.vorgaenge.erinnert(frage, stufe, nachricht.id if nachricht is not None else None)
            log.info("Erinnerung geschickt (%s Tage vorher)", stufe)

    def _erinnern_schleife(self, konto, halt: threading.Event) -> None:
        warten = 60  # kurz nach dem Start einmal nachsehen, dann alle fünf Minuten
        while not halt.wait(warten):
            warten = 300
            try:
                self._erinnern(konto)
            except Exception:
                log.exception("Erinnern fehlgeschlagen")

    # --- Senden ---
    def _senden(self, chat, antwort: Antwort):
        datei = None
        if antwort.vorlesen and (antwort.immer_vorlesen or self.einstellungen.vorlesen == "immer"):
            datei = self.stimme.sprechen(antwort.zum_vorlesen, self.tmp)
        if datei:
            nachricht = chat.send_message(text=antwort.text, file=str(datei), viewtype=ViewType.VOICE)
        else:
            nachricht = chat.send_text(antwort.text)
        if antwort.datei:
            chat.send_message(file=antwort.datei)
        if antwort.merken_als and nachricht is not None:
            self.einstellungen.setzen(antwort.merken_als, {"id": nachricht.id, "zeit": time.time()})
        if antwort.vorlage and nachricht is not None:
            e = self.entwuerfe.entwurf()
            if e is not None:
                e.vorlage_id = nachricht.id
                self.entwuerfe.merken(e)
        return nachricht

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
        # Chat (mit Fotos und Sprachnachrichten) bei Momo nach der Frist löschen; Briefe liegen im Speicherort
        konto.set_config("delete_device_after", str(self.konfig.aufheben_tage * 86400))
        return konto

    def _einladung_entfernen(self) -> None:
        for name in ("einladung.txt", "einladung.svg", "einladung.pdf"):
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
            self._konto = konto
            haken = events.HookCollection()
            haken.on(events.NewMessage(is_info=False))(self._bei_nachricht)
            haken.on(events.RawEvent(EventType.WEBXDC_STATUS_UPDATE))(self._bei_app)
            bot = Bot(konto, haken)
            halt = threading.Event()
            threading.Thread(target=self._erinnern_schleife, args=(konto, halt), daemon=True,
                             name="erinnern").start()
            if self.besitzer.gekoppelt:
                log.info("Mit Besitzer gekoppelt (Kontakt %s).", self.besitzer.kontakt_id)
                self._einladung_entfernen()
            else:
                self._einladung_zeigen(konto)
            bot.run_forever()
