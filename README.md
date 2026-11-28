# Momo – Verwaltungsassistent beta

Ein Delta-Chat-Bot, der hilft, Behördenpost zu verstehen und zu beantworten – für Menschen, denen Lesen und Schreiben schwerfällt. Brief fotografieren oder eine Sprachnachricht schicken; Momo erklärt in einfachen Worten, liest vor, merkt sich Fristen und macht aus Gesprochenem einen korrekten Antwortbrief.

Nutzer brauchen nur Delta Chat (Android, iPhone, Computer). Der Bot läuft als Docker-Container auf einem Server, Raspberry Pi oder Computer; KI (ChatGPT, Claude, Mistral, lokal) und Speicherort (Google Drive, iCloud, Nextcloud, Ordner) sind wählbar.

- `docs/ANPASSUNG.md` – Bauplan, Schritte V0–V14
- `docs/quelle/` – ursprüngliches Konzept (Version 1.0)
- `CLAUDE.md` – Grundregeln für die Entwicklung

## Einrichten (Betreiber)

```sh
cp .env.example .env          # anpassen
mkdir -p daten && sudo chown 10001 daten
docker compose up -d --build
docker compose logs -f        # zeigt den Einladungslink
```

Der QR-Code liegt danach als `daten/einladung.svg` bereit. Die Person scannt ihn mit Delta Chat und schreibt „Hallo“. Wer zuerst verschlüsselt schreibt, wird Besitzer; alle anderen ignoriert Momo. Neu koppeln: `daten/besitzer.json` löschen und neu starten.

## Entwickeln

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest
```

Stand: V9 – Momo nimmt Fotos und PDFs von Briefen an, legt sie im gewählten Speicherort ab (Ordner oder rclone: Nextcloud, Drive, iCloud …), erkennt den Text lokal (tesseract) und zieht mit der KI Absender, Datum, Aktenzeichen, Fristen und Beträge heraus – jede Angabe mit Seite und wörtlichem Ausschnitt, von Momo nachgeprüft. Die Antwort beantwortet drei Fragen (Was ist das? Was musst du tun? Bis wann?), erklärt schwere Wörter aus einer festen Liste (`momo/woerter.py`) und liest Aktenzeichen Zeichen für Zeichen vor. Sprachnachrichten versteht Momo lokal mit Whisper (`MOMO_WHISPER`, Standard small); Wünsche wie „Lies mir den Brief noch mal vor“ oder „Antworte nur mit Text“ erledigt er ohne KI. Fristen aus Briefen fragt Momo nach („Soll ich dich erinnern?“ – Ja/Nein als Antwort auf die Nachricht) und erinnert 7 und 2 Tage vorher und am Tag selbst; „Was ist diese Woche wichtig?“ zeigt die nächsten Fristen (`daten/vorgaenge.json`, Übersicht als `Fristen.txt` im Speicherort). Antwortbriefe: frei sagen, was drinstehen soll → Momo schreibt den Brief (Absender, Anschrift nur wenn im Brief belegt, Aktenzeichen, Datum), liest ihn vor, ändert ihn auf Zuruf und macht erst nach „passt“ als Antwort auf genau diese Vorlage ein PDF (`MOMO_ABSENDER` oder einmal im Chat). Momo verschickt nichts. Abnahme: `python -m tools.pruefe_briefe` (zehn erfundene Briefe, mit `--zeigen` samt Antworttext).

Lizenz: MIT (siehe `LICENSE`).
