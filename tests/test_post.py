from momo import post

from test_antwortbrief import SEITE, Schreiber
from test_sprechen import _bote
from test_vorgaenge import BRIEF, Chat, uhr


def test_adressen():
    assert post.adressen_im_text("Fragen an service@jobcenter-musterstadt.de. Oder info@x.de.") == \
        ["service@jobcenter-musterstadt.de", "info@x.de"]
    assert post.adresse_aus_gesprochenem("max punkt muster ät beispiel punkt de") == "max.muster@beispiel.de"
    assert post.adresse_aus_gesprochenem("Max.Muster@Beispiel.de") == "max.muster@beispiel.de"
    assert post.adresse_aus_gesprochenem("keine ahnung") is None
    z = post.Zugang.aus_umgebung({"MOMO_MAIL_ADRESSE": "a@b.de", "MOMO_MAIL_PASSWORT": "p", "MOMO_MAIL_IMAP": "imap.b.de"})
    assert z and not z.senden
    assert post.Zugang.aus_umgebung({}) is None


def test_nachricht_mit_pdf():
    m = post.nachricht_bauen("Max", "max@b.de", "amt@c.de", "Betreff", "Text", ("Antwort.pdf", b"%PDF-1.4"))
    teile = [t.get_filename() for t in m.iter_attachments()]
    assert teile == ["Antwort.pdf"] and m["To"] == "amt@c.de" and m["Message-ID"]


class FalschesPostfach:
    def __init__(self, senden=True):
        self.z = post.Zugang("max@b.de", "p", "imap", "smtp", senden)
        self.entwuerfe, self.gesendet = [], []

    def entwurf_ablegen(self, m):
        self.entwuerfe.append(m)
        return "Drafts"

    def senden(self, m):
        self.gesendet.append(m)


def _mit_antwortbrief(tmp_path, seite):
    b = _bote(tmp_path)
    b.gespraech.ki = Schreiber()
    b.vorgaenge.uhr = uhr("2026-11-15")
    b.vorgaenge.brief_eintragen("Briefe/a", BRIEF)
    b.briefe.ablage.schreiben("Briefe/a/text/seite-01.txt", seite.encode())
    b.entwuerfe.absender = ["Max Beispiel", "Lindenweg 7", "12345 Musterstadt"]
    b.postfach = FalschesPostfach()
    chat = Chat()
    b._chat = chat
    vorlage = b._senden(chat, b.antworten_auf("text", "Schreib dem Jobcenter, dass ich die Unterlagen schicke", False))
    pdf = b.antworten_auf("text", "passt", False, zitiert=vorlage.id)
    assert "Als E-Mail" in pdf.text
    return b, chat


def test_mail_entwurf_und_bestaetigung(tmp_path):
    b, chat = _mit_antwortbrief(tmp_path, SEITE + "\nFragen? service@jobcenter-musterstadt.de")
    a = b.antworten_auf("text", "Schick das bitte als E-Mail", False)
    assert "service@jobcenter-musterstadt.de" in a.text and "Die Adresse steht im Brief" in a.text
    assert a.merken_als == "mail_frage" and "ät" in a.sprechtext
    m = b.postfach.entwuerfe[0]
    assert [t.get_filename() for t in m.iter_attachments()][0].endswith(".pdf")
    assert "Aktenzeichen: 987D 654321" in m["Subject"]
    frage = b._senden(chat, a)
    assert "direkt auf meine Nachricht" in b.antworten_auf("text", "Ja, abschicken", False).text
    assert not b.postfach.gesendet
    fertig = b.antworten_auf("text", "Ja, abschicken", False, zitiert=frage.id)
    assert "abgeschickt" in fertig.text and b.postfach.gesendet[0]["Message-ID"] == m["Message-ID"]
    assert "keine E-Mail zum Abschicken" in b.antworten_auf("text", "Ja, abschicken", False, zitiert=frage.id).text


def test_mail_ohne_adresse_im_brief(tmp_path):
    b, chat = _mit_antwortbrief(tmp_path, SEITE)
    assert "keine E-Mail-Adresse" in b.antworten_auf("text", "als E-Mail bitte", False).text
    a = b.antworten_auf("text", "amt punkt muster ät beispiel punkt de", False)
    assert "amt.muster@beispiel.de" in a.text and "hast du mir gesagt" in a.text


def test_mail_ohne_zugang(tmp_path):
    b = _bote(tmp_path)
    assert "Zugang zu deinem E-Mail-Postfach" in b.antworten_auf("text", "Schick das als E-Mail", False).text
