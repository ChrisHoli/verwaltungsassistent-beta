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

Stand: V4 – Momo antwortet mit KI (Mistral über die API oder Claude-Abo zum Testen) in Leichter Sprache, als Text und Sprachnachricht, und speichert Fotos und PDFs von Briefen im gewählten Speicherort (Ordner oder rclone: Nextcloud, Drive, iCloud …). Briefe lesen folgt in V5.

Lizenz: MIT (siehe `LICENSE`).
