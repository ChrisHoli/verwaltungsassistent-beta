import pytest

from tools import einrichten as e


def frager(antworten, aus=None):
    folge = iter(antworten)

    def eingabe(_text):
        try:
            return next(folge)
        except StopIteration:
            raise EOFError from None

    return e.Frager(eingabe=eingabe, geheim=eingabe, aus=(aus.append if aus is not None else lambda *_: None))


def test_bisherige_werte_nur_momo():
    u = {"MOMO_KI": "mistral", "PATH": "/bin", "HOME": "/daten", "MISTRAL_API_KEY": "x", "MOMO_DATEN": "/daten",
         "RCLONE_CONFIG": "/daten/rclone.conf", "RCLONE_CONFIG_NEXTCLOUD_URL": "https://c/x"}
    assert e.bisherige_werte(u) == {"MOMO_KI": "mistral", "MISTRAL_API_KEY": "x",
                                    "RCLONE_CONFIG_NEXTCLOUD_URL": "https://c/x"}


def _compose_wert(roh: str) -> str:
    """So liest docker compose einen Wert aus der .env (für die Fälle, die _wert erzeugt)."""
    if roh.startswith("'") and roh.endswith("'"):
        return roh[1:-1]
    if roh.startswith('"') and roh.endswith('"'):
        innen = roh[1:-1].replace("$$", "\0")
        out, i = "", 0
        while i < len(innen):
            if innen[i] == "\\" and i + 1 < len(innen):
                out += innen[i + 1]
                i += 2
            else:
                out += innen[i]
                i += 1
        return out.replace("\0", "$")
    return roh


@pytest.mark.parametrize("wert", ["einfach", "mit Leerzeichen", "a#b$c", "it's", 'a"b$c\\d'])
def test_werte_rundlauf(wert):
    assert _compose_wert(e._wert(wert)) == wert


def test_env_text_gruppiert_und_vollständig():
    text = e.env_text({"MOMO_KI": "mistral", "MISTRAL_API_KEY": "k", "MOMO_ABLAGE": "rclone",
                       "MOMO_ABLAGE_ZIEL": "nextcloud:Momo", "RCLONE_CONFIG_NEXTCLOUD_URL": "https://c/d",
                       "MOMO_NAME": "Momo", "MOMO_XYZ": "1", "MOMO_KI_MODELL": ""})
    assert "# Speicherort\nMOMO_ABLAGE=rclone\nMOMO_ABLAGE_ZIEL=nextcloud:Momo\nRCLONE_CONFIG_NEXTCLOUD_URL=" in text
    assert "MOMO_XYZ=1" in text and "MOMO_KI_MODELL" not in text
    assert text.index("MOMO_NAME") < text.index("MOMO_KI=")


def test_mail_server():
    assert e.mail_server("a@GMX.de")[:2] == ("imap.gmx.net:993", "mail.gmx.net:465")
    assert e.mail_server("a@eigene-domain.de")[:2] == ("imap.eigene-domain.de:993", "smtp.eigene-domain.de:465")


def test_nextcloud_adresse():
    assert e.nextcloud_adresse("cloud.beispiel.de/", "momo") == "https://cloud.beispiel.de/remote.php/dav/files/momo"
    assert (e.nextcloud_adresse("https://c.de/index.php/apps/files/", "m")
            == "https://c.de/remote.php/dav/files/m")


def test_ablauf_ordner_ohne_ki_ohne_mail(tmp_path):
    w = e.ablauf(frager(["", "9", "1", "n", "Momo", "Christian", "j", "j"]), {}, pruefen=False)
    assert w["MOMO_KI"] == "keine" and w["MOMO_ABLAGE"] == "ordner" and w["MOMO_BETREIBER"] == "Christian"
    assert w["MOMO_VORLESEN"] == "immer" and "MOMO_MAIL_ADRESSE" not in w


def test_ablauf_mistral_behält_schlüssel_mit_enter():
    w = e.ablauf(frager(["", "", "", "", "", "", "n", "", "", "", "j"]),
                 {"MOMO_KI": "mistral", "MISTRAL_API_KEY": "geheim", "MOMO_BETREIBER": "C"}, pruefen=False)
    assert w["MOMO_KI"] == "mistral" and w["MISTRAL_API_KEY"] == "geheim" and w["MOMO_KI_MODELL"] == ""


def test_ablauf_mail_mit_senden():
    w = e.ablauf(frager(["", "9", "1", "j", "max@posteo.de", "pw", "", "j", "", "", "C", "", "j"]), {}, pruefen=False)
    assert w["MOMO_MAIL_IMAP"] == "posteo.de:993" and w["MOMO_MAIL_SMTP"] == "posteo.de:465"
    assert w["MOMO_MAIL_SENDEN"] == "ja"


def test_ablauf_claude_abo_setzt_mit_claude():
    w = e.ablauf(frager(["", "8", "tok", "", "1", "n", "", "C", "", "j"]), {}, pruefen=False)
    assert w["MIT_CLAUDE"] == "1" and w["CLAUDE_CODE_OAUTH_TOKEN"] == "tok"


def test_abbruch_bei_ende_der_eingabe():
    with pytest.raises(e.Abbruch):
        e.ablauf(frager(["9"]), {}, pruefen=False)


def test_nein_beim_speichern_bricht_ab():
    with pytest.raises(e.Abbruch):
        e.ablauf(frager(["", "9", "1", "n", "", "C", "", "n"]), {}, pruefen=False)


def test_prüfung_ordner_und_ohne_ki(tmp_path):
    w = {"MOMO_KI": "keine", "MOMO_ABLAGE": "ordner", "MOMO_ABLAGE_ZIEL": str(tmp_path / "ablage")}
    assert e.ki_pruefen(w) == "ohne KI"
    assert "gelöscht" in e.ablage_pruefen(w)
    assert list((tmp_path / "ablage").iterdir()) == []


def test_fehlschlag_wird_gemeldet_und_neu_gefragt(tmp_path):
    aus = []
    versuche = []

    def pruefung(w):
        versuche.append(1)
        if len(versuche) == 1:
            raise RuntimeError("401 Unauthorized")
        return "klappt"

    e._pruefen_bis_ok(frager(["1"], aus), "die KI", pruefung, {}, lambda: None)
    assert any("401" in z for z in aus) and any("✓ klappt" in z for z in aus)


def test_main_schreibt_datei_nur_für_besitzer(tmp_path, monkeypatch):
    antworten = iter(["", "9", "1", "n", "", "C", "", "j"])
    monkeypatch.setattr("builtins.input", lambda _t: next(antworten))
    for k in list(__import__("os").environ):
        if e.EIGENE.match(k):
            monkeypatch.delenv(k)
    ziel = tmp_path / "e.env"
    assert e.main(["--ziel", str(ziel), "--ohne-pruefung"]) == 0
    assert "MOMO_KI=keine" in ziel.read_text()
    assert oct(ziel.stat().st_mode & 0o777) == "0o600"


def test_fehler_verständlich():
    from momo.ki import KiFehler
    assert e.verstaendlich(KiFehler("anmeldung", "401 Invalid")).startswith("Der Schlüssel wird nicht angenommen")
    assert "App-Passwort" in e.verstaendlich(RuntimeError("IMAP: error: b'[AUTHENTICATIONFAILED] Invalid'"))
    assert e.verstaendlich(RuntimeError("sonstwas")) == "sonstwas"


def test_messenger_telegram_und_signal():
    w = e.ablauf(frager(["3", "123:abc", "9", "1", "n", "", "C", "", "j"]), {}, pruefen=False)
    assert w["MOMO_MESSENGER"] == "telegram" and w["MOMO_TELEGRAM_TOKEN"] == "123:abc"
    w = e.ablauf(frager(["2", "0151 1234 5678", "0171/9876543", "9", "1", "n", "", "C", "", "j"]), {}, pruefen=False)
    assert w["MOMO_SIGNAL_NUMMER"] == "+4915112345678" and w["MOMO_BESITZER_ADRESSEN"] == "+491719876543"
    assert w["COMPOSE_PROFILES"] == "signal"
    # zurück zu Delta Chat: Signal-Profil und Telefonnummer als Besitzer fallen weg
    w = e.ablauf(frager(["1", "9", "1", "n", "", "C", "", "j"]), w, pruefen=False)
    assert "COMPOSE_PROFILES" not in w and "MOMO_BESITZER_ADRESSEN" not in w


def test_signal_nummer_wird_geprüft():
    with pytest.raises(ValueError):
        e.messenger_pruefen({"MOMO_MESSENGER": "signal", "MOMO_SIGNAL_NUMMER": "0151"})
    assert "gut" in e.messenger_pruefen({"MOMO_MESSENGER": "signal", "MOMO_SIGNAL_NUMMER": "+4915112345678"})


def test_telegram_schlüssel_fehler_verständlich():
    from momo.kanal.telegram import TelegramFehler
    assert "BotFather" in e.verstaendlich(TelegramFehler("getMe: 401 Unauthorized"))
