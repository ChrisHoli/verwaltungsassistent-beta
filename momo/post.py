"""E-Mail: Entwurf mit PDF im eigenen Postfach ablegen (IMAP), auf Bestätigung abschicken (SMTP).

So erscheint die E-Mail in jedem E-Mail-Programm der Person (Handy oder Computer) unter „Entwürfe“.
Zugang über MOMO_MAIL_* (am besten ein App-Passwort). Ohne Zugang gibt es keinen E-Mail-Weg.
Abschicken nur, wenn MOMO_MAIL_SENDEN=ja und die Person genau diese E-Mail bestätigt.
"""

import imaplib
import logging
import re
import smtplib
import ssl
import time
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

log = logging.getLogger(__name__)

ADRESSE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")


class PostFehler(RuntimeError):
    pass


@dataclass
class Zugang:
    adresse: str
    passwort: str
    imap: str
    smtp: str
    senden: bool = False

    @classmethod
    def aus_umgebung(cls, u) -> "Zugang | None":
        adresse = u.get("MOMO_MAIL_ADRESSE", "").strip()
        passwort = u.get("MOMO_MAIL_PASSWORT", "").strip()
        imap = u.get("MOMO_MAIL_IMAP", "").strip()
        if not (adresse and passwort and imap):
            return None
        return cls(adresse, passwort, imap, u.get("MOMO_MAIL_SMTP", "").strip(),
                   u.get("MOMO_MAIL_SENDEN", "").strip().lower() in ("ja", "1", "true"))


def _host_port(wert: str, standard: int) -> tuple[str, int]:
    host, _, port = wert.partition(":")
    return host, int(port) if port else standard


def adressen_im_text(text: str) -> list[str]:
    gesehen = []
    for a in ADRESSE.findall(text or ""):
        a = a.rstrip(".").lower()
        if a not in gesehen:
            gesehen.append(a)
    return gesehen


def adresse_aus_gesprochenem(text: str) -> str | None:
    """„max punkt muster at beispiel punkt de“ → max.muster@beispiel.de (Whisper schreibt E-Mails selten richtig)."""
    t = (text or "").lower()
    t = re.sub(r"\s+(at|ät|äd|klammeraffe)\s+", "@", t)
    t = re.sub(r"\s+(punkt|dot)\s+", ".", t)
    t = re.sub(r"\s+(minus|bindestrich|strich)\s+", "-", t)
    t = re.sub(r"\s+unterstrich\s+", "_", t)
    treffer = ADRESSE.search(t.replace(" @", "@").replace("@ ", "@"))
    return treffer.group(0).lower() if treffer else None


def nachricht_bauen(von_name: str, von: str, an: str, betreff: str, text: str,
                    anhang: tuple[str, bytes] | None) -> EmailMessage:
    m = EmailMessage()
    m["From"] = formataddr((von_name, von)) if von_name else von
    m["To"] = an
    m["Subject"] = betreff
    m["Date"] = formatdate(localtime=True)
    m["Message-ID"] = make_msgid(domain=von.rsplit("@", 1)[-1])
    m.set_content(text)
    if anhang:
        name, daten = anhang
        m.add_attachment(daten, maintype="application", subtype="pdf", filename=name)
    return m


def _ordner_mit(imap: imaplib.IMAP4, merkmal: str, ersatz: tuple[str, ...]) -> str:
    typ, liste = imap.list()
    namen = []
    for zeile in liste or []:
        z = zeile.decode(errors="replace") if isinstance(zeile, bytes) else str(zeile)
        m = re.match(r'\((?P<f>[^)]*)\) (?:"[^"]*"|NIL) (?P<n>.+)$', z)
        if not m:
            continue
        name = m.group("n").strip()
        namen.append(name)
        if merkmal.lower() in m.group("f").lower():
            return name
    for e in ersatz:
        for n in namen:
            if n.strip('"').lower() == e.lower():
                return n
    return ersatz[0]


class Postfach:
    def __init__(self, zugang: Zugang, zeitlimit: int = 60):
        self.z = zugang
        self.zeitlimit = zeitlimit

    def _imap(self) -> imaplib.IMAP4:
        host, port = _host_port(self.z.imap, 993)
        try:
            imap = (imaplib.IMAP4_SSL(host, port, ssl_context=ssl.create_default_context(), timeout=self.zeitlimit)
                    if port == 993 else imaplib.IMAP4(host, port, timeout=self.zeitlimit))
            if port != 993:
                imap.starttls(ssl_context=ssl.create_default_context())
            imap.login(self.z.adresse, self.z.passwort)
            return imap
        except (OSError, imaplib.IMAP4.error) as e:
            raise PostFehler(f"IMAP: {type(e).__name__}: {str(e)[:150]}") from None

    def entwurf_ablegen(self, m: EmailMessage) -> str:
        """Legt die E-Mail bei den Entwürfen ab; gibt den Ordnernamen zurück."""
        imap = self._imap()
        try:
            ordner = _ordner_mit(imap, "\\Drafts", ("Drafts", "Entwürfe", "INBOX.Drafts", "Entwurf"))
            typ, antwort = imap.append(ordner, "(\\Draft \\Seen)", imaplib.Time2Internaldate(time.time()),
                                       m.as_bytes())
            if typ != "OK" and b"TRYCREATE" in b" ".join(x for x in antwort if isinstance(x, bytes)):
                imap.create(ordner)  # manche Postfächer haben noch keinen Entwürfe-Ordner
                typ, antwort = imap.append(ordner, "(\\Draft \\Seen)", imaplib.Time2Internaldate(time.time()),
                                           m.as_bytes())
            if typ != "OK":
                raise PostFehler(f"IMAP APPEND: {antwort!r}"[:200])
            return ordner.strip('"')
        except imaplib.IMAP4.error as e:
            raise PostFehler(f"IMAP: {str(e)[:150]}") from None
        finally:
            try:
                imap.logout()
            except Exception:
                pass

    def pruefen(self) -> str:
        """Anmelden (IMAP, bei eingeschaltetem Senden auch SMTP), nichts verschicken. Gibt den Entwürfe-Ordner zurück."""
        imap = self._imap()
        try:
            ordner = _ordner_mit(imap, "\\Drafts", ("Drafts", "Entwürfe", "INBOX.Drafts", "Entwurf")).strip('"')
        finally:
            try:
                imap.logout()
            except Exception:
                pass
        if self.z.senden:
            if not self.z.smtp:
                raise PostFehler("SMTP-Server fehlt (MOMO_MAIL_SMTP)")
            with self._smtp() as smtp:
                pass
        return ordner

    def _smtp(self) -> smtplib.SMTP:
        host, port = _host_port(self.z.smtp, 465)
        try:
            if port == 465:
                smtp = smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=self.zeitlimit)
            else:
                smtp = smtplib.SMTP(host, port, timeout=self.zeitlimit)
                smtp.starttls(context=ssl.create_default_context())
            smtp.login(self.z.adresse, self.z.passwort)
            return smtp
        except (OSError, smtplib.SMTPException) as e:
            raise PostFehler(f"SMTP: {type(e).__name__}: {str(e)[:150]}") from None

    def senden(self, m: EmailMessage) -> None:
        if not self.z.senden or not self.z.smtp:
            raise PostFehler("Abschicken ist nicht eingeschaltet (MOMO_MAIL_SENDEN, MOMO_MAIL_SMTP)")
        try:
            with self._smtp() as smtp:
                smtp.send_message(m)
        except (OSError, smtplib.SMTPException) as e:
            raise PostFehler(f"SMTP: {type(e).__name__}: {str(e)[:150]}") from None
        # Entwurf entfernen und eine Kopie bei „Gesendet“ ablegen (viele Anbieter tun das nicht selbst)
        try:
            imap = self._imap()
            try:
                entwuerfe = _ordner_mit(imap, "\\Drafts", ("Drafts", "Entwürfe", "INBOX.Drafts"))
                imap.select(entwuerfe)
                typ, ids = imap.search(None, "HEADER", "Message-ID", m["Message-ID"])
                for i in (ids[0].split() if typ == "OK" and ids and ids[0] else []):
                    imap.store(i, "+FLAGS", "\\Deleted")
                imap.expunge()
                gesendet = _ordner_mit(imap, "\\Sent", ("Sent", "Gesendet", "INBOX.Sent", "Gesendete Objekte"))
                imap.append(gesendet, "(\\Seen)", imaplib.Time2Internaldate(time.time()), m.as_bytes())
            finally:
                imap.logout()
        except (PostFehler, imaplib.IMAP4.error, OSError) as e:
            log.warning("Nach dem Senden: Entwurf/Gesendet nicht aufgeräumt: %s", str(e)[:150])
