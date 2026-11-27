"""Vorgänge und Fristen: Briefe bündeln, Fristen bestätigen lassen, rechtzeitig erinnern.

Gespeichert in daten/vorgaenge.json (bleibt im Container-Datenordner, nicht in der KI).
Eine Frist wird nur erinnert, wenn der Mensch sie bestätigt hat („Ja“ auf Momos Frage).
Rechtliche Fristen (Widerspruch) rechnet Momo nicht aus: Er bietet nur eine Wiedervorlage an.
"""

import json
import re
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .aufnahme import datum_lesbar

ZEITZONE = ZoneInfo("Europe/Berlin")
ERINNERN_TAGE = (7, 2, 0)  # Tage vorher
ERINNERN_AB_STUNDE = 9
WIEDERVORLAGE_TAGE = 21  # Widerspruch: meist ein Monat ab Bekanntgabe → nach drei Wochen nachfragen

# Ganze kurze Antwort, nicht nur der Anfang: „Bitte lies mir den Brief vor“ ist kein Ja.
JA = re.compile(r"^\s*(ja+|jo|jep|jawohl|klar|gerne?|ok(ay)?|genau|stimmt|richtig|mach (das|bitte)|bitte ja)"
                r"([\s,]+(bitte|danke|gerne?|klar|mach das))*[\s.!]*$", re.I)
NEIN = re.compile(r"^\s*(nein|nee+|ne|nö|lieber nicht|nicht nötig|brauch ich nicht)([\s,]+danke)?[\s.!]*$", re.I)
# Ohne Zitat nur das Wort „erledigt“ selbst; mit Zitat auf eine Erinnerung auch „hab ich gemacht“ usw.
ERLEDIGT = re.compile(r"\berledigt\b", re.I)
ERLEDIGT_ZITAT = re.compile(r"\b(erledigt|gemacht|abgeschickt|geschickt|bezahlt|überwiesen|war (schon )?da)\b", re.I)


def akte_von(aktenzeichen: str | None) -> str | None:
    """Gleiche Nummer = gleicher Vorgang, auch wenn Leerzeichen oder Striche anders sind."""
    if not aktenzeichen:
        return None
    norm = re.sub(r"[^0-9a-z]", "", aktenzeichen.lower())
    return norm or None


@dataclass
class Frage:
    """Was Momo als Nächstes auf ein Ja/Nein/Erledigt hin tun würde."""
    brief: int
    frist: int


class Vorgaenge:
    def __init__(self, ordner: Path, uhr=time.time):
        self.datei = Path(ordner) / "vorgaenge.json"
        self.uhr = uhr
        self._sperre = threading.RLock()
        self.daten = self._laden()

    # --- Speichern ---
    def _laden(self) -> dict:
        try:
            d = json.loads(self.datei.read_text())
            if isinstance(d, dict) and isinstance(d.get("briefe"), list):
                d.setdefault("chat", None)
                return d
        except (FileNotFoundError, ValueError):
            pass
        return {"briefe": [], "chat": None}

    def _sichern(self) -> None:
        self.datei.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.datei.with_suffix(".neu")
        tmp.write_text(json.dumps(self.daten, ensure_ascii=False, indent=1))
        tmp.replace(self.datei)

    def _heute(self) -> date:
        return datetime.fromtimestamp(self.uhr(), ZEITZONE).date()

    @property
    def chat(self) -> int | None:
        return self.daten.get("chat")

    def chat_merken(self, chat_id: int) -> None:
        with self._sperre:
            if self.daten.get("chat") != chat_id:
                self.daten["chat"] = chat_id
                self._sichern()

    # --- Briefe ---
    def brief_eintragen(self, vorgang: str, e: dict) -> int:
        """Nimmt einen gelesenen Brief auf; gibt seine Nummer zurück. Fristen starten als „vorgeschlagen“."""
        wert = lambda feld: (e.get(feld) or {}).get("wert")  # noqa: E731
        heute = self._heute()
        fristen = [{"datum": f["wert"], "art": "frist", "ausschnitt": f["ausschnitt"], "status": "vorgeschlagen",
                    "erinnert": []}
                   for f in sorted(e.get("fristen", []), key=lambda f: f["wert"]) if f["wert"] >= heute.isoformat()]
        if e.get("widerspruch") and not e.get("verdacht_manipulation"):
            fristen.append({"datum": (heute + timedelta(days=WIEDERVORLAGE_TAGE)).isoformat(), "art": "wiedervorlage",
                            "ausschnitt": e["widerspruch"]["ausschnitt"], "status": "vorgeschlagen", "erinnert": []})
        if e.get("verdacht_manipulation"):
            fristen = []  # bei Verdacht keine Erinnerungen aus dem Brief
        brief = {
            "vorgang": vorgang, "eingang": heute.isoformat(), "absender": wert("absender"),
            "aktenzeichen": wert("aktenzeichen"), "akte": akte_von(wert("aktenzeichen")),
            "dokumenttyp": wert("dokumenttyp"), "was_ist_das": e.get("was_ist_das"),
            "was_tun": wert("handlungsbedarf"), "fristen": fristen, "fragen": {},
        }
        with self._sperre:
            self.daten["briefe"].append(brief)
            self._sichern()
            return len(self.daten["briefe"]) - 1

    def frueher_zur_akte(self, nummer: int) -> list[dict]:
        """Frühere Briefe mit derselben Nummer (gleicher Vorgang)."""
        briefe = self.daten["briefe"]
        akte = briefe[nummer].get("akte")
        return [b for i, b in enumerate(briefe) if akte and i != nummer and b.get("akte") == akte]

    # --- Fragen nach einer Frist (Antwort per Zitat oder direkt danach) ---
    def frage_merken(self, nummer: int, frist: int, nachricht_id: int) -> None:
        with self._sperre:
            self.daten["briefe"][nummer]["fragen"][str(nachricht_id)] = frist
            self.daten["letzte_frage"] = {"brief": nummer, "frist": frist, "zeit": self.uhr()}
            self._sichern()

    def frage_zu(self, zitiert: int | None) -> Frage | None:
        """Auf welche Frist bezieht sich ein Ja/Nein? Zitat zählt; ohne Zitat nur die letzte Frage der letzten 12 h."""
        with self._sperre:
            if zitiert is not None:
                for i, b in enumerate(self.daten["briefe"]):
                    if str(zitiert) in b.get("fragen", {}):
                        return Frage(i, b["fragen"][str(zitiert)])
                    for k, f in enumerate(b["fristen"]):
                        if zitiert in f.get("erinnerung_ids", []):
                            return Frage(i, k)
                return None
            letzte = self.daten.get("letzte_frage")
            if letzte and self.uhr() - letzte["zeit"] < 12 * 3600:
                return Frage(letzte["brief"], letzte["frist"])
            return None

    def bestaetigte(self) -> list[Frage]:
        """Alle bestätigten Fristen ab heute (für „erledigt“ ohne Zitat)."""
        heute = self._heute().isoformat()
        return [Frage(i, k) for i, b in enumerate(self.daten["briefe"]) for k, f in enumerate(b["fristen"])
                if f["status"] == "bestaetigt" and f["datum"] >= heute]

    def frist(self, frage: Frage) -> dict:
        return self.daten["briefe"][frage.brief]["fristen"][frage.frist]

    def setzen(self, frage: Frage, status: str) -> None:
        with self._sperre:
            self.frist(frage)["status"] = status
            if self.daten.get("letzte_frage", {}).get("brief") == frage.brief and \
                    self.daten["letzte_frage"].get("frist") == frage.frist:
                self.daten.pop("letzte_frage")
            self._sichern()

    # --- Erinnern ---
    def faellig(self) -> list[tuple[Frage, int]]:
        """(Frist, Tage vorher) für alle Erinnerungen, die jetzt dran sind. Verpasste werden nicht nachgeholt,
        nur die jüngste Stufe kommt (nach einem Ausfall also nicht dreimal hintereinander)."""
        jetzt = datetime.fromtimestamp(self.uhr(), ZEITZONE)
        heute = jetzt.date()
        ergebnis = []
        for i, b in enumerate(self.daten["briefe"]):
            for k, f in enumerate(b["fristen"]):
                if f["status"] != "bestaetigt":
                    continue
                tag = date.fromisoformat(f["datum"])
                if tag < heute:
                    continue
                tage = ERINNERN_TAGE if f["art"] == "frist" else (0,)  # Wiedervorlage: nur am Tag selbst
                stufen = [t for t in tage if tag - timedelta(days=t) <= heute]
                if not stufen or jetzt.hour < ERINNERN_AB_STUNDE:
                    continue
                stufe = min(stufen)
                if stufe not in f["erinnert"] and not any(s < stufe for s in f["erinnert"]):
                    ergebnis.append((Frage(i, k), stufe))
        return ergebnis

    def erinnert(self, frage: Frage, stufe: int, nachricht_id: int | None) -> None:
        with self._sperre:
            f = self.frist(frage)
            f["erinnert"] = sorted(set(f["erinnert"]) | {t for t in ERINNERN_TAGE if t >= stufe})
            if nachricht_id is not None:
                f.setdefault("erinnerung_ids", []).append(nachricht_id)
            self.daten["letzte_frage"] = {"brief": frage.brief, "frist": frage.frist, "zeit": self.uhr()}
            self._sichern()

    # --- Überblick ---
    def kommend(self, tage: int | None = 7) -> list[tuple[dict, dict]]:
        """(Brief, Frist) für offene Fristen ab heute, bestätigt oder noch nicht beantwortet."""
        heute = self._heute()
        bis = heute + timedelta(days=tage) if tage is not None else date.max
        liste = [(b, f) for b in self.daten["briefe"] for f in b["fristen"]
                 if f["status"] in ("bestaetigt", "vorgeschlagen") and heute <= date.fromisoformat(f["datum"]) <= bis]
        return sorted(liste, key=lambda bf: bf[1]["datum"])


# --- Texte (Leichte Sprache) ---

def _von(b: dict) -> str:
    return f" vom {b['absender']}" if b.get("absender") else ""


def frage_text(b: dict, f: dict) -> str:
    if f["art"] == "wiedervorlage":
        return (f"Gegen diesen Brief kannst du vielleicht Widerspruch einlegen. Soll ich dich am "
                f"{datum_lesbar(f['datum'])} daran erinnern? Dann hast du noch Zeit, mit einer Beratungsstelle "
                "zu sprechen. Antworte auf diese Nachricht mit Ja oder Nein.")
    return (f"Soll ich dich an den {datum_lesbar(f['datum'])} erinnern? Ich sage dir dann 7 Tage und 2 Tage vorher "
            "und am Tag selbst Bescheid. Antworte auf diese Nachricht mit Ja oder Nein.")


def erinnerung_text(b: dict, f: dict, stufe: int, heute: date) -> str:
    tag = datum_lesbar(f["datum"])
    wann = "Heute" if stufe == 0 else ("Morgen" if (date.fromisoformat(f["datum"]) - heute).days == 1
                                       else f"In {(date.fromisoformat(f['datum']) - heute).days} Tagen")
    if f["art"] == "wiedervorlage":
        return (f"Erinnerung: Du hast einen Brief{_von(b)} bekommen. Dagegen kannst du vielleicht Widerspruch "
                "einlegen. Wenn du das willst, sprich bald mit einer Beratungsstelle. "
                "Die genaue Frist steht am Ende vom Brief.")
    satz = [f"Erinnerung: {wann}, am {tag}, ist ein wichtiger Tag für deinen Brief{_von(b)}."]
    if b.get("was_tun"):
        satz.append(f"Das sollst du tun: {b['was_tun'].rstrip('.')}.")
    satz.append("Wenn du es schon erledigt hast, antworte auf diese Nachricht mit: erledigt.")
    return " ".join(satz)


def ueberblick_text(liste: list[tuple[dict, dict]], tage: int | None) -> str:
    zeitraum = "in den nächsten 7 Tagen" if tage == 7 else "demnächst"
    if not liste:
        return f"Ich kenne {zeitraum} keine Frist und keinen Termin von dir."
    zeilen = [f"Das ist {zeitraum} wichtig:"]
    for b, f in liste:
        art = "Erinnerung an Widerspruch" if f["art"] == "wiedervorlage" else "Frist oder Termin"
        offen = " (noch nicht bestätigt)" if f["status"] == "vorgeschlagen" else ""
        tun = f" {b['was_tun'].rstrip('.')}." if b.get("was_tun") and f["art"] != "wiedervorlage" else ""
        zeilen.append(f"{datum_lesbar(f['datum'])}: {art}{_von(b)}.{tun}{offen}")
    return "\n".join(zeilen)
