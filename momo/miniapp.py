"""Mini-App im Chat (webxdc): Briefe nach Bereichen, Fristen als große Kacheln, Vorlesen und Antworten per Knopf.

Momo schickt den Stand als Aktualisierung an die App; die App schickt Bitten zurück („vorlesen“, „erledigt“ …).
Beides bleibt im verschlüsselten Chat. Die App lädt nichts aus dem Netz; die Schriften liegen bei.
"""

import io
import zipfile
from pathlib import Path

APP_ORDNER = Path(__file__).parent / "app"
BITTEN = {"vorlesen", "erledigt", "bestaetigen", "antworten"}


def xdc_bauen(ziel: Path) -> Path:
    """Packt momo/app/ als .xdc (ZIP) zusammen."""
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as z:
        for datei in sorted(APP_ORDNER.rglob("*")):
            if datei.is_file():
                z.write(datei, datei.relative_to(APP_ORDNER).as_posix())
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(puffer.getvalue())
    return ziel


def stand(vorgaenge, hoechstens: int = 200) -> dict:
    """Was die App zeigt. Nur das Nötige, keine Brieftexte."""
    briefe = vorgaenge.daten["briefe"]
    start = max(0, len(briefe) - hoechstens)
    ausgabe, fristen = [], []
    for i, b in enumerate(briefe):
        ordner = b.get("vorgang", "")
        teile = ordner.split("/")
        ausgabe.append({
            "kategorie": "Zum Prüfen" if b.get("verdacht") else (b.get("kategorie") or "Sonstiges"),
            "absender": b.get("absender"), "datum": b.get("datum"), "eingang": b.get("eingang"),
            "was_ist_das": b.get("was_ist_das"), "was_tun": b.get("was_tun"), "betreff": b.get("betreff"),
            "aktenzeichen": b.get("aktenzeichen"), "verdacht": bool(b.get("verdacht")),
            "pruefen": bool(b.get("pruefen")),
            "ordner": " › ".join(teile[1:3]) if len(teile) > 3 and teile[1] != "Eingang" else "Eingang",
        } if i >= start else {"kategorie": "_alt"})
        if i >= start:
            for k, f in enumerate(b.get("fristen", [])):
                if f["status"] in ("vorgeschlagen", "bestaetigt"):
                    fristen.append({"brief": i, "frist": k, "datum": f["datum"], "art": f["art"],
                                    "status": f["status"]})
    fristen.sort(key=lambda f: f["datum"])
    return {"typ": "stand", "briefe": ausgabe, "fristen": fristen}


def bitten(updates: list[dict]) -> list[dict]:
    """Nur gültige Bitten aus der App, alles andere (auch Momos eigene Stände) fällt heraus."""
    ergebnis = []
    for u in updates:
        p = u.get("payload") if isinstance(u, dict) else None
        if isinstance(p, dict) and p.get("typ") == "bitte" and p.get("was") in BITTEN \
                and isinstance(p.get("brief"), int) and not isinstance(p.get("brief"), bool):
            frist = p.get("frist")
            ergebnis.append({"was": p["was"], "brief": p["brief"],
                             "frist": frist if isinstance(frist, int) and not isinstance(frist, bool) else None})
    return ergebnis
