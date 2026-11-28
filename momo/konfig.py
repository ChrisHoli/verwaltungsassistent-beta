"""Einstellungen aus Umgebungsvariablen (siehe .env.example)."""

import os
from dataclasses import dataclass
from pathlib import Path

VORLESEN_WERTE = ("immer", "nie")


@dataclass(frozen=True)
class Konfig:
    name: str
    daten: Path
    chatmail_qr: str
    besitzer_adressen: str
    vorlesen: str
    stimme: Path | None
    ki: str
    ablage: str
    ablage_ziel: str
    whisper: str = "small"
    absender: str = ""
    betreiber: str = ""
    aufheben_tage: int = 30

    @property
    def dc_ordner(self) -> Path:
        return self.daten / "deltachat"

    @classmethod
    def aus_umgebung(cls, umgebung: dict[str, str] | None = None) -> "Konfig":
        u = os.environ if umgebung is None else umgebung
        daten = Path(u.get("MOMO_DATEN", "/daten"))
        vorlesen = u.get("MOMO_VORLESEN", "immer").strip().lower()
        if vorlesen not in VORLESEN_WERTE:
            raise ValueError(f"MOMO_VORLESEN muss {' oder '.join(VORLESEN_WERTE)} sein, nicht {vorlesen!r}")
        stimme = u.get("MOMO_STIMME", "/app/stimmen/de_DE-thorsten-medium.onnx").strip()
        return cls(
            name=u.get("MOMO_NAME", "Momo").strip() or "Momo",
            daten=daten,
            chatmail_qr=u.get("MOMO_CHATMAIL_QR", "dcaccount:nine.testrun.org").strip(),
            besitzer_adressen=u.get("MOMO_BESITZER_ADRESSEN", ""),
            vorlesen=vorlesen,
            stimme=Path(stimme) if stimme else None,
            ki=u.get("MOMO_KI", "keine").strip().lower(),
            ablage=u.get("MOMO_ABLAGE", "ordner").strip().lower(),
            ablage_ziel=u.get("MOMO_ABLAGE_ZIEL", str(daten / "ablage")).strip(),
            whisper=u.get("MOMO_WHISPER", "small").strip() or "small",
            absender=u.get("MOMO_ABSENDER", "").strip(),
            betreiber=u.get("MOMO_BETREIBER", "").strip(),
            aufheben_tage=int(u.get("MOMO_AUFHEBEN_TAGE", "30").strip() or 30),
        )
