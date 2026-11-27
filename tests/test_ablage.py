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
    assert a1.vorgang.startswith("Briefe/2027-01-15_")
