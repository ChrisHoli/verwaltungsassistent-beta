"""Telegram und Signal gegen nachgebaute Server (httpx.MockTransport): koppeln, Fotos, Sprache, Zitate, Senden."""

import base64
import json
import shutil

import httpx
import pytest

from momo.kanal import SPRACHE, kanal_waehlen
from momo.kanal import signal as sg
from momo.kanal import telegram as tg
from momo.konfig import Konfig

from test_sprechen import _bote


class TelegramServer:
    def __init__(self):
        self.updates, self.gesendet, self.naechste_id = [], [], 500

    def __call__(self, request: httpx.Request) -> httpx.Response:
        teile = request.url.path.split("/")
        if teile[1] == "file":
            return httpx.Response(200, content=b"\xff\xd8 foto")
        methode = teile[-1]
        if methode == "getMe":
            return httpx.Response(200, json={"ok": True, "result": {"username": "momo_test_bot"}})
        if methode == "deleteWebhook":
            return httpx.Response(200, json={"ok": True, "result": True})
        if methode == "getUpdates":
            u, self.updates = self.updates, []
            return httpx.Response(200, json={"ok": True, "result": u})
        if methode == "getFile":
            return httpx.Response(200, json={"ok": True, "result": {"file_path": "photos/file_1.jpg"}})
        self.naechste_id += 1
        inhalt = request.content.decode(errors="replace")
        self.gesendet.append((methode, inhalt))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": self.naechste_id}})


def _telegram(tmp_path):
    server = TelegramServer()
    api = tg.Api("123:geheim", httpx.Client(transport=httpx.MockTransport(server)))
    k = Konfig.aus_umgebung({"MOMO_DATEN": str(tmp_path), "MOMO_MESSENGER": "telegram"})
    return tg.TelegramKanal(k, "", api), server


def _nachricht(i, text=None, **mehr):
    m = {"message_id": i, "from": {"id": 42, "username": "max"}, "chat": {"id": 42, "type": "private"}}
    if text is not None:
        m["text"] = text
    m.update(mehr)
    return {"update_id": i, "message": m}


def test_telegram_koppeln_nur_mit_code(tmp_path):
    kanal, server = _telegram(tmp_path)
    b = _bote(tmp_path)
    b.kanal = kanal
    server.updates = [_nachricht(1, "Hallo"), _nachricht(2, "/start falsch")]
    kanal.einmal_abholen(b, 0)
    assert not b.besitzer.gekoppelt and server.gesendet == []
    server.updates = [_nachricht(3, f"/start {kanal.einladungscode()}")]
    kanal.einmal_abholen(b, 0)
    assert b.besitzer.gekoppelt and b.besitzer.kontakt_id == 42
    texte = " ".join(i for _, i in server.gesendet)
    assert "Momo" in texte and "Telegram kann mitlesen" in texte  # Begrüßung und ehrlicher Datenschutz-Hinweis
    # Ein Fremder mit dem alten Code kommt nicht mehr hinein
    fremd = _nachricht(4, f"/start {kanal.einladungscode()}")
    fremd["message"]["from"]["id"] = 99
    fremd["message"]["chat"]["id"] = 99
    vorher = len(server.gesendet)
    server.updates = [fremd]
    kanal.einmal_abholen(b, 0)
    assert len(server.gesendet) == vorher
    assert json.loads((tmp_path / "telegram.json").read_text())["naechste"] == 5


def test_telegram_foto_wird_abgelegt_und_zitat_kommt_an(tmp_path):
    kanal, server = _telegram(tmp_path)
    e = kanal.eingang(_nachricht(7, None, photo=[{"file_id": "klein"}, {"file_id": "gross"}],
                                 reply_to_message={"message_id": 501})["message"], True)
    assert e.art == "bild" and e.file.endswith(".jpg") and open(e.file, "rb").read().startswith(b"\xff\xd8")
    assert e.zitiert == 501 and e.file_mime == "image/jpeg"
    b = _bote(tmp_path)
    b.kanal = kanal
    b.besitzer.pruefen(42, "@max", True)
    b.bei_eingang(e)
    assert b.briefe.ablage.liste("Briefe/Eingang")  # Brief liegt im Speicherort
    b._lese_uhr.cancel()


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg fehlt")
def test_telegram_sprachnachricht_als_ogg(tmp_path):
    kanal, server = _telegram(tmp_path)
    m4a = tmp_path / "a.m4a"
    import subprocess

    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=duration=0.3", str(m4a)], check=True)
    g = kanal.get_chat_by_id(42).send_message(text="Hallo", file=str(m4a), viewtype=SPRACHE)
    assert [m for m, _ in server.gesendet] == ["sendMessage", "sendVoice"] and g.id == 501


def test_telegram_pdf_und_langer_text(tmp_path):
    kanal, server = _telegram(tmp_path)
    pdf = tmp_path / "Antwort.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    chat = kanal.get_chat_by_id(42)
    chat.send_message(file=str(pdf))
    chat.send_text("x" * 9000)
    assert [m for m, _ in server.gesendet] == ["sendDocument", "sendMessage", "sendMessage", "sendMessage"]


def test_telegram_fehler_verrät_keinen_schlüssel():
    def kaputt(request):
        raise httpx.ConnectError("nicht erreichbar", request=request)

    api = tg.Api("123:geheim", httpx.Client(transport=httpx.MockTransport(kaputt)))
    with pytest.raises(tg.TelegramFehler) as f:
        api("getMe")
    assert "geheim" not in str(f.value)


class SignalServer:
    def __init__(self):
        self.umschlaege, self.gesendet = [], []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        p = request.url.path
        if p.startswith("/v1/receive/"):
            u, self.umschlaege = self.umschlaege, []
            return httpx.Response(200, json=u)
        if p.startswith("/v1/attachments/"):
            return httpx.Response(200, content=b"%PDF-1.4 brief")
        if p == "/v2/send":
            self.gesendet.append(json.loads(request.content))
            return httpx.Response(201, json={"timestamp": str(1700000000000 + len(self.gesendet))})
        return httpx.Response(404, json={"error": "unbekannt"})


def _signal(tmp_path):
    server = SignalServer()
    api = sg.Api("http://signal:8080", "+4915100000000", httpx.Client(transport=httpx.MockTransport(server)))
    k = Konfig.aus_umgebung({"MOMO_DATEN": str(tmp_path), "MOMO_MESSENGER": "signal"})
    return sg.SignalKanal(k, "", api=api), server


def _umschlag(ts, **daten):
    return {"envelope": {"source": "+491711111111", "sourceNumber": "+491711111111", "sourceUuid": "uuid-max",
                         "timestamp": ts, "dataMessage": {"timestamp": ts, **daten}}}


def test_signal_koppeln_antworten_und_zitat(tmp_path):
    kanal, server = _signal(tmp_path)
    b = _bote(tmp_path)
    b.kanal = kanal
    b.besitzer.adressen = {"+491711111111"}
    fremd = _umschlag(1, message="Hallo")
    fremd["envelope"].update(sourceNumber="+499999", source="+499999", sourceUuid="uuid-fremd")
    server.umschlaege = [fremd, {"envelope": {"source": "+491711111111", "receiptMessage": {}}}]
    kanal.einmal_abholen(b, 0)
    assert not b.besitzer.gekoppelt and server.gesendet == []
    server.umschlaege = [_umschlag(2, message="Hallo")]
    kanal.einmal_abholen(b, 0)
    assert b.besitzer.kontakt_id == "uuid-max"
    assert server.gesendet[0]["recipients"] == ["+491711111111"] and server.gesendet[0]["number"] == "+4915100000000"
    assert "Nur du und ich" in " ".join(g["message"] for g in server.gesendet)
    e = kanal.eingang(_umschlag(3, message="passt", quote={"id": 1700000000001, "author": "+4915100000000"}))
    assert e.zitiert == 1700000000001 and e.art == "text"


def test_signal_anhang_und_senden_mit_datei(tmp_path):
    kanal, server = _signal(tmp_path)
    e = kanal.eingang(_umschlag(5, attachments=[{"id": "abc.pdf", "contentType": "application/pdf",
                                                  "filename": "Brief.pdf"}]))
    assert e.art == "datei" and e.file_mime == "application/pdf" and open(e.file, "rb").read().startswith(b"%PDF")
    pdf = tmp_path / "Antwort.pdf"
    pdf.write_bytes(b"%PDF-1.4 x")
    g = kanal.get_chat_by_id("+491711111111").send_message(text="Dein Brief", file=str(pdf))
    anhang = server.gesendet[-1]["base64_attachments"][0]
    assert anhang.startswith("data:application/pdf;filename=Antwort.pdf;base64,")
    assert base64.b64decode(anhang.split(",", 1)[1]) == b"%PDF-1.4 x" and g.id == 1700000000001


def test_kanal_waehlen(tmp_path):
    k = Konfig.aus_umgebung({"MOMO_DATEN": str(tmp_path)})
    assert kanal_waehlen("deltachat", k).name == "deltachat"
    with pytest.raises(ValueError):
        kanal_waehlen("telegram", k, {})  # ohne Zugangsschlüssel
    with pytest.raises(ValueError):
        kanal_waehlen("whatsapp", k, {})
