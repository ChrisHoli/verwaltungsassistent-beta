import os
import shutil
from pathlib import Path

import pytest

from momo.ablage import AblageFehler, OrdnerAblage, ablage_waehlen
from momo.ablage.rclone import RcloneAblage
from momo.briefe import Briefablage, endung_fuer

RCLONE = os.environ.get("MOMO_RCLONE") or shutil.which("rclone")


@pytest.mark.skipif(not RCLONE, reason="rclone nicht installiert")
def test_rclone_ablage_lokal(tmp_path):
    a = RcloneAblage(f":local:{tmp_path}/wolke", befehl=RCLONE)
    (tmp_path / "wolke").mkdir()
    a.pruefen()
    a.schreiben("Briefe/x/original/seite-01.jpg", b"\xff\xd8bild")
    assert (tmp_path / "wolke/Briefe/x/original/seite-01.jpg").read_bytes() == b"\xff\xd8bild"
    assert a.lesen("Briefe/x/original/seite-01.jpg") == b"\xff\xd8bild"
    assert a.liste() == ["Briefe/x/original/seite-01.jpg"]
    assert a.liste("Briefe/x") == ["Briefe/x/original/seite-01.jpg"]
    assert a.liste("gibtsnicht") == []
    with pytest.raises(ValueError):
        a.schreiben("../raus", b"x")


def test_rclone_fehler(tmp_path):
    with pytest.raises(AblageFehler):
        RcloneAblage("x:", befehl=str(tmp_path / "fehlt")).schreiben("a", b"b")
    with pytest.raises(ValueError):
        RcloneAblage("ohne-doppelpunkt")
    assert isinstance(ablage_waehlen("rclone", "nextcloud:"), RcloneAblage)
    assert RcloneAblage("nextcloud:")._pfad("Briefe/a") == "nextcloud:Briefe/a"
    assert RcloneAblage("drive:Momo/")._pfad("a") == "drive:Momo/a"


def test_endung():
    assert endung_fuer("image/jpeg", None) == "jpg"
    assert endung_fuer(None, "Brief.PDF") == "pdf"
    assert endung_fuer("application/zip", "x.zip") is None


def test_briefablage_buendelt_seiten(tmp_path):
    uhr = [1_800_000_000.0]
    b = Briefablage(OrdnerAblage(tmp_path), uhr=lambda: uhr[0])
    a1 = b.aufnehmen(b"1", "jpg")
    uhr[0] += 60
    a2 = b.aufnehmen(b"2", "jpg")
    uhr[0] += 600
    a3 = b.aufnehmen(b"3", "pdf")
    assert a1.vorgang == a2.vorgang != a3.vorgang
    assert (a1.seite, a2.seite, a3.seite) == (1, 2, 1)
    assert a2.pfad.endswith("/original/seite-02.jpg")
    assert (tmp_path / a3.pfad).read_bytes() == b"3"
    assert a1.vorgang.startswith("Briefe/Eingang/2027-01-15_")


def test_einsortieren(tmp_path):
    from momo.aufnahme import kategorie, ordnername

    b = Briefablage(OrdnerAblage(tmp_path))
    a = b.aufnehmen(b"1", "jpg")
    ziel = b.einsortieren(a.vorgang, "Gesundheit", "AOK Plus / Die Gesundheitskasse", "2026-11-20", "Rechnung: 2/26")
    assert ziel == "Briefe/Gesundheit/AOK Plus Die Gesundheitskasse/2026-11-20 Rechnung 2 26"
    assert (tmp_path / ziel / "original" / "seite-01.jpg").read_bytes() == b"1"
    assert not (tmp_path / a.vorgang).exists()
    a2 = b.aufnehmen(b"2", "jpg")  # neuer Vorgang, nicht in den einsortierten Ordner
    assert a2.vorgang.startswith("Briefe/Eingang/")
    zweit = b.einsortieren(a2.vorgang, "Gesundheit", "AOK Plus / Die Gesundheitskasse", "2026-11-20", "Rechnung: 2/26")
    assert zweit.endswith("(2)")
    assert kategorie("gesundheit") == "Gesundheit" and kategorie("Quatsch") == "Sonstiges"
    assert kategorie({"wert": "Bank & Geld"}) == "Bank und Geld"
    assert ordnername("../../etc") == "etc" and ordnername("") is None
