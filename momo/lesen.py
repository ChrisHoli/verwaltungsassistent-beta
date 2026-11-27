"""Texterkennung: Fotos und PDFs → Text je Seite (tesseract deu, pdftotext/pdftoppm). Alles lokal."""

import logging
import re
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

PDF_SEITEN_MAX = 10
SEITE_MINDESTLAENGE = 25   # darunter gilt eine Seite als unlesbar
BRIEF_MINDESTLAENGE = 80   # darunter bitten wir um ein neues Foto
BILDENDUNGEN = {"jpg", "jpeg", "png", "webp", "heic", "tif", "tiff", "bmp"}


def _lauf(befehl: list[str], zeit: int = 120) -> str:
    try:
        ergebnis = subprocess.run(befehl, capture_output=True, timeout=zeit)
        return ergebnis.stdout.decode("utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("%s fehlgeschlagen: %s", befehl[0], type(e).__name__)
        return ""


def _ocr_bild(pfad: Path) -> str:
    return _lauf(["tesseract", str(pfad), "stdout", "-l", "deu", "--psm", "1"])


def _pdf_seiten(pfad: Path, ordner: Path) -> list[str]:
    """Textlage bevorzugen; nur unlesbare Seiten per OCR nachholen."""
    voll = _lauf(["pdftotext", "-layout", "-l", str(PDF_SEITEN_MAX), str(pfad), "-"])
    seiten = voll.split("\f")
    while seiten and not seiten[-1].strip():
        seiten.pop()
    if seiten and all(len(s.strip()) >= SEITE_MINDESTLAENGE for s in seiten):
        return seiten
    _lauf(["pdftoppm", "-r", "300", "-gray", "-l", str(PDF_SEITEN_MAX), "-png", str(pfad),
           str(ordner / "seite")], zeit=180)
    bilder = sorted(ordner.glob("seite*.png"))
    if not seiten:
        return [_ocr_bild(b) for b in bilder]
    ergebnis = []
    for i, text in enumerate(seiten):
        if len(text.strip()) < SEITE_MINDESTLAENGE and i < len(bilder):
            text = _ocr_bild(bilder[i])
        ergebnis.append(text)
    return ergebnis


def seiten_lesen(teile: list[tuple[bytes, str]]) -> list[str]:
    """teile: (Daten, Endung) in Reihenfolge. Rückgabe: Text je Seite (ein PDF kann mehrere haben)."""
    seiten: list[str] = []
    for daten, endung in teile:
        endung = endung.lower().lstrip(".")
        with tempfile.TemporaryDirectory(prefix="momo-lesen-") as tmp:
            ordner = Path(tmp)
            pfad = ordner / f"teil.{endung}"
            pfad.write_bytes(daten)
            if endung == "pdf":
                seiten.extend(_pdf_seiten(pfad, ordner))
            elif endung in BILDENDUNGEN:
                seiten.append(_ocr_bild(pfad))
            else:
                seiten.append("")
    return [s.strip() for s in seiten]


def _anteil_woerter(text: str) -> float:
    """Anteil der Stücke, die wie echte Wörter oder Zahlen aussehen (Rest = Texterkennungs-Müll)."""
    stuecke = text.split()
    if not stuecke:
        return 0.0
    gut = sum(1 for w in stuecke
              if re.fullmatch(r"[(„\"]?[A-Za-zÄÖÜäöüß]{2,}(-[A-Za-zÄÖÜäöüß]+)*[.,:;!?)“\"]*", w)
              or re.fullmatch(r"[\d.,:/€%§-]+", w) or w in ("-", "–", "·", "&", "§§"))
    return gut / len(stuecke)


def brief_ist_schlecht(seiten: list[str]) -> bool:
    text = "\n".join(seiten)
    return len(text.strip()) < BRIEF_MINDESTLAENGE or _anteil_woerter(text) < 0.5
