"""Zeigt den Einladungs-QR im Terminal (zum Scannen mit Delta Chat). Wartet, bis Momo ihn erzeugt hat.

    python -m tools.einladung [--warten 300]
"""

import argparse
import sys
import time
from pathlib import Path


SCHRITTE = {
    "deltachat": [
        ("1", "Delta Chat holen", "Im App Store oder bei Google Play „Delta Chat“ suchen und installieren. "
         "Beim Öffnen „Ich bin neu“ wählen, einen Namen eingeben, fertig."),
        ("2", "Diesen Code scannen", "In Delta Chat auf das QR-Zeichen tippen (oder im Menü „QR-Code scannen“) und "
         "die Kamera auf den Code halten. Dann bestätigen."),
        ("3", "Hallo sagen", "Schreib „Hallo“ oder schick eine Sprachnachricht. Danach kannst du {name} einfach "
         "Fotos von Briefen schicken."),
    ],
    "telegram": [
        ("1", "Telegram holen", "Im App Store oder bei Google Play „Telegram“ suchen, installieren und mit deiner "
         "Handynummer anmelden."),
        ("2", "Diesen Code scannen", "Die Kamera deines Handys auf den Code halten und den Link öffnen. "
         "Er öffnet Telegram."),
        ("3", "Auf „Starten“ tippen", "Unten erscheint der Knopf „Starten“. Tipp darauf. Danach kannst du {name} "
         "Fotos von Briefen schicken oder Sprachnachrichten."),
    ],
    "signal": [
        ("1", "Signal holen", "Im App Store oder bei Google Play „Signal“ suchen, installieren und mit deiner "
         "Handynummer anmelden."),
        ("2", "Diesen Code scannen", "Die Kamera deines Handys auf den Code halten und den Link öffnen. "
         "Er öffnet den Chat mit {name} in Signal."),
        ("3", "Hallo sagen", "Schreib „Hallo“ oder schick eine Sprachnachricht. Danach kannst du {name} einfach "
         "Fotos von Briefen schicken."),
    ],
}


def blatt(link: str, ziel: Path, name: str = "Momo", messenger: str = "deltachat") -> None:
    """Einladung zum Ausdrucken: drei Schritte in großer Schrift und der QR-Code."""
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    schrift, fett = "Helvetica", "Helvetica-Bold"
    dejavu = Path("/usr/share/fonts/truetype/dejavu")
    if (dejavu / "DejaVuSans.ttf").exists():
        pdfmetrics.registerFont(TTFont("DejaVu", str(dejavu / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(dejavu / "DejaVuSans-Bold.ttf")))
        schrift, fett = "DejaVu", "DejaVu-Bold"
    breite, hoehe = A4
    links = 22 * mm
    c = canvas.Canvas(str(ziel), pagesize=A4)
    c.setTitle(f"So erreichst du {name}")
    c.setFont(fett, 30)
    c.drawString(links, hoehe - 32 * mm, f"So erreichst du {name}")
    y = hoehe - 52 * mm
    for nummer, titel, text in SCHRITTE.get(messenger, SCHRITTE["deltachat"]):
        text = text.format(name=name)
        c.setFillColorRGB(0.16, 0.36, 0.55)
        c.circle(links + 7 * mm, y - 2 * mm, 7 * mm, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont(fett, 22)
        c.drawCentredString(links + 7 * mm, y - 5 * mm, nummer)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(links + 19 * mm, y - 4 * mm, titel)
        c.setFont(schrift, 15)
        zeilen = simpleSplit(text, schrift, 15, breite - links - 19 * mm - 20 * mm)
        for i, z in enumerate(zeilen):
            c.drawString(links + 19 * mm, y - 13 * mm - i * 7 * mm, z)
        y -= 22 * mm + len(zeilen) * 7 * mm
    groesse = min(95 * mm, y - 30 * mm)
    qr = QrCodeWidget(link, barLevel="M")
    x1, y1, x2, y2 = qr.getBounds()
    d = Drawing(groesse, groesse, transform=[groesse / (x2 - x1), 0, 0, groesse / (y2 - y1), 0, 0])
    d.add(qr)
    renderPDF.draw(d, c, (breite - groesse) / 2, y - groesse - 4 * mm)
    c.setFont(schrift, 12)
    c.drawCentredString(breite / 2, 20 * mm, f"Nur du kannst mit {name} schreiben. Der Code gilt für eine Person.")
    c.showPage()
    c.save()


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--daten", default="/daten")
    p.add_argument("--warten", type=int, default=300, help="höchstens so viele Sekunden warten")
    a = p.parse_args(argv)
    daten = Path(a.daten)
    ende = time.time() + a.warten
    while time.time() < ende:
        if (daten / "einladung.txt").exists():
            break
        if (daten / "besitzer.json").exists():
            print("Momo ist schon mit einer Person gekoppelt. Neu koppeln: daten/besitzer.json löschen, neu starten.")
            return 0
        time.sleep(3)
    else:
        print("Noch keine Einladung da. Nachsehen mit: docker compose logs momo")
        return 1
    link = (daten / "einladung.txt").read_text().strip()
    import os

    import segno

    messenger = os.environ.get("MOMO_MESSENGER", "deltachat") or "deltachat"
    print("\nMit Delta Chat scannen: auf das QR-Zeichen tippen (oder Menü → QR-Code scannen).\n" if messenger == "deltachat"
          else "\nMit der Handykamera scannen und den Link öffnen.\n")
    segno.make(link, error="m").terminal(compact=True)
    try:
        blatt(link, daten / "einladung.pdf", os.environ.get("MOMO_NAME", "Momo") or "Momo",
              os.environ.get("MOMO_MESSENGER", "deltachat") or "deltachat")
        print("\nEinladungsblatt mit drei Schritten in großer Schrift ist erstellt.")
    except Exception as e:  # noqa: BLE001 – das Blatt ist eine Zugabe
        print(f"\n(Einladungsblatt nicht erstellt: {str(e)[:120]})")
    print("Danach „Starten“ tippen.\n" if messenger == "telegram" else "Danach „Hallo“ an Momo schreiben.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
