# Momo – Bauplan (Verwaltungsassistent beta)

Stand: 27.11.2026 (vierte Fassung, V0 entschieden) · Quelle: `docs/quelle/Verwaltungsassistent_beta_Technischer_Bauplan.md` (ChatGPT-Konzept, unverändert abgelegt)

## Richtung

**Momo ist ein Delta-Chat-Bot.** Der Nutzer installiert nur **Delta Chat** (kostenlos, Android, iPhone, Windows, Mac, Linux), scannt einmal einen QR-Code und schreibt oder spricht mit Momo wie mit einem Menschen: Brief fotografieren, Sprachnachricht schicken, Antwort hören.

Der Bot ist **ein eigenständiges Paket** (ein Docker-Container), das überall laufen kann: auf einem Server, einem Raspberry Pi oder einem Computer. Keine Verbindung zu anderen Diensten. **KI** und **Speicherort** wählt, wer den Bot einrichtet.

**Momo** ist der Name des Bots. Erster Nutzer: ein Freund mit Legasthenie, Thema **Post vom Jobcenter und anderen Behörden**. Danach Vorlage für weitere Menschen: **ein Bot je Person**.

Vorher geprüft und verworfen: Web-App mit Server, eigene Flutter-App (siehe V14).

## Warum Delta Chat

- **Keine eigene App bauen:** Android, iPhone und Computer sind sofort abgedeckt. Kein APK, kein Apple-Entwicklerkonto (99 €/Jahr), kein App-Store.
- **Ende-zu-Ende-verschlüsselt, ohne Telefonnummer.** Behördenpost ist Sozialdaten; Telegram-Bots wären nicht verschlüsselt.
- **Kann alles, was Momo braucht:** Fotos, PDFs, Sprachnachrichten in beide Richtungen, Dateien zurück, Benachrichtigungen auf dem Handy, Zitat-Antworten.
- **Bewährt:** Ein bestehender Delta-Chat-Bot des Betreibers (`deltachat-rpc-client` 2.66, Kopplung über Einladungslink, Besitzer-Prüfung) ist das Vorbild; sein Muster wird übernommen, nicht sein Code verknüpft.

## Gesamtbild

```
Delta Chat (Handy / Computer)
  Foto · PDF · Sprachnachricht · Text
          │  verschlüsselt (chatmail)
          ▼
  Momo-Bot (ein Container, je Person)
   Texterkennung (tesseract) · Umschrift (Whisper) · Vorlesen (Piper)
   Vorgänge · Fristen · Erinnerungen · Antwortbriefe
          │                    │
          ▼                    ▼
   gewählte KI           gewählter Speicher (rclone)
   ChatGPT-Abo* /        Google Drive · iCloud Drive · Nextcloud ·
   API-Schlüssel /       OneDrive · Dropbox · Ordner
   lokale KI
```
\* falls „Mit ChatGPT anmelden“ für Momo nutzbar ist (V3)

## Was vom ChatGPT-Konzept bleibt

- Vorgang ≠ Dokument; Vorgänge bündeln Briefe, Fristen, Aufgaben.
- Jede Frist, jeder Betrag, jedes Aktenzeichen mit Fundstelle (Seite, Textausschnitt) und Prüfstatus.
- Dokumente sind nicht vertrauenswürdig (Prompt-Injection-Schutz, §13.2).
- Kein Versand, keine Zahlung; rechtliche Fristen (z. B. Widerspruch) nur als vorgeschlagene Wiedervorlage.
- KI hinter einer austauschbaren Schnittstelle (§5.1); Python-Orchestrierung ohne freie Agenten (§8).

## Was sich ändert

| Konzept | Momo | Grund |
|---|---|---|
| Flutter-App + Web-App | **Delta Chat** als Oberfläche | nichts zu bauen, alle Geräte |
| FastAPI, PostgreSQL, S3, Redis | **ein Python-Bot**, Dateien + lokaler Suchindex | ein Container |
| Login, Passkeys | **Kopplung per QR-Code**; danach antwortet Momo nur diesem Kontakt (verschlüsselt) | kein Passwort |
| STT/TTS-Anbieter | **Whisper** und **Piper** im Container (kostenlos, lokal) | Daten bleiben beim Bot |
| Freigabe-Knöpfe | **Antwort auf die Vorlage** („passt“, „nein“, oder die Änderung) | Delta Chat hat keine Knöpfe; Zitat bindet die Freigabe an genau diese Nachricht |
| Push-Dienst | Momo **schreibt** zur Erinnerung; Delta Chat benachrichtigt | nichts Eigenes |
| Dashboard | später **Mini-App im Chat** (webxdc) mit großen Knöpfen | läuft in Delta Chat auf allen Geräten |

## KI wählen

Eine Schnittstelle `KiAnbieter` (`momo/ki/`), Auswahl über `MOMO_KI` in der `.env`:

1. **`mistral` – Mistral über die API (Hauptweg, seit 27.11.2026).** Französischer Anbieter, Verarbeitung in der EU, Schlüssel aus Mistral Studio, Abrechnung nach Verbrauch (Cent-Beträge). Training in der Konsole abschalten; auf Wunsch Zero Data Retention.
2. **`claude-abo` – Claude über ein Abo** (Claude Code, `claude -p`, setup-token). Zum Testen durch den Betreiber. Claude Code läuft ohne Werkzeuge, Einstellungen und MCP. Bild mit `MIT_CLAUDE=1` bauen.
3. Später möglich: weitere OpenAI-kompatible Adressen, lokale KI (Ollama), ChatGPT-Abo („Mit ChatGPT anmelden“, bisher nur Partner und Open-Source-Vorschau – zurückgestellt zugunsten Mistral).

Nur der Text geht an die KI, keine Fotos. Momo merkt sich die letzten 12 Nachrichten (`daten/verlauf.json`). Ins Log kommen nur der Verbrauch (Tokens) und Fehlerarten, nie Inhalte. Fällt die KI aus, sagt Momo das in einfachen Worten.

DSGVO: Der Anbieter allein reicht nicht. Die Person muss wissen und einverstanden sein, dass ihre Briefe über den Bot und die KI laufen (vor V12 klären).

## Speicherort wählen

Über **rclone** (eine Schnittstelle für alles): Google Drive, **iCloud Drive**, Nextcloud/WebDAV, OneDrive, Dropbox oder ein einfacher Ordner. Daten als lesbare Dateien (je Vorgang ein Ordner: Originale, Text, JSON, Antwortbriefe). Ohne Momo bleiben sie nutzbar; am Computer sieht man sie im jeweiligen Cloud-Ordner.

## Legasthenie und Behördenpost

- **Antworten kurz und als Sprachnachricht** (Einstellung „immer vorlesen“), Text immer dazu.
- **Jeder Brief bekommt drei Sätze in Leichter Sprache:** Was ist das? Was musst du tun? Bis wann?
- **Sprechen statt tippen:** Sprachnachrichten werden verstanden (Whisper small, lokal, mit einer Liste von Amtswörtern); keine Befehle nötig, normale Sätze reichen („Was wollte das Jobcenter?“). Im Text steht oben, was Momo verstanden hat, damit ein Hörfehler auffällt. Selbst erledigt (`momo/saetze.py`): „Lies mir den Brief noch mal vor“, „Antworte immer mit Sprache“, „Antworte nur mit Text“ (gemerkt in `daten/einstellungen.json`).
- **Behördenwörter erklärt** aus fester Liste (`momo/woerter.py`: Anhörung, Erstattung, Leistungsminderung, Mitwirkungspflicht, Widerspruch, Bescheid …), höchstens zwei je Brief; Fragen wie „Was heißt Anhörung?“ beantwortet Momo direkt aus der Liste. Die Liste ist ein Entwurf und soll von einer Beratungsstelle geprüft werden.
- **Aktenzeichen und Zahlen** beim Vorlesen einzeln und langsam („neun, acht, sieben, De …“), Beträge als „1087 Euro und 40 Cent“.
- **„Bis wann?“ prüft Momo selbst:** Steht im Brief „bis zum …“ oder „spätestens …“ und die KI hat das Datum nicht sicher, sagt Momo „nicht sicher“ statt „keine Frist“. Fristen wie „innerhalb von 14 Tagen“ zitiert er wörtlich, rechnet aber nicht selbst.
- **Antworten schreiben:** frei sprechen → Momo macht einen korrekten Brief mit Aktenzeichen → liest ihn vor → schickt ihn als PDF in den Chat zum Drucken, Mailen, Hochladen. Momo versendet nichts selbst.
- **Fristen und Erinnerungen (V8):** Nach jedem Brief fragt Momo je Frist „Soll ich dich an den … erinnern?“. Erinnert wird nur, was mit Ja bestätigt ist (Antwort auf genau diese Nachricht; ohne Zitat gilt die letzte Frage der letzten 12 Stunden), 7 und 2 Tage vorher und am Tag selbst, ab 9 Uhr. Nach einem Ausfall kommt nur die jüngste Erinnerung, nicht alle verpassten. „erledigt“ beendet die Erinnerungen. Bei einem Bescheid mit Widerspruchsmöglichkeit rechnet Momo keine Frist aus, sondern bietet nach drei Wochen eine Wiedervorlage an. Briefe mit gleichem Aktenzeichen gehören zum selben Vorgang. Gespeichert in `daten/vorgaenge.json`, Übersicht als `Fristen.txt` im Speicherort.
- Bei Fristen und Widerspruch: Hinweis auf Beratungsstelle. Momo ist keine Rechtsberatung.

## Betrieb und Installation

- **Nutzer (der Mensch, nicht Momo):** Delta Chat installieren → QR-Code scannen (bekommt er vom Betreiber) → „Hallo“ sagen. Fertig.
- **Betreiber:** `docker compose up` mit einer `.env` (KI-Schlüssel, Speicher). Beim ersten Start zeigt Momo den Einladungs-QR. Wer ihn zuerst verschlüsselt nutzt, wird Besitzer; danach ist Momo für alle anderen stumm. Zurücksetzen über eine Datei im Datenordner.
- **Wo läuft der Bot?** Für den Probelauf: auf holiwork-alpha in einem **eigenen Container ohne Zugriff auf die anderen Dienste dort**; Nextcloud nur über den eigenen Benutzer `momo`. Später auch auf einem Raspberry Pi bei der Person zu Hause.
- Ein Bot je Person: getrennte Daten, getrennter KI-Schlüssel, leicht übergebbar.

## Kosten

Delta Chat und chatmail kostenlos. KI: ChatGPT Go 8 €/Monat (falls der Abo-Weg klappt) oder API-Cent-Beträge. Speicher: vorhandene Cloud. Bot: vorhandener Server oder Raspberry Pi (einmalig ~80 €).

## Schritte

V0 Klären · V1 Repo und Grundregeln · V2 Grundgerüst Bot · V3 KI-Anschluss · V4 Speicherort · V5 Brief aufnehmen und lesen · V6 Erklären und Vorlesen · V7 Sprechen statt Tippen · V8 Vorgänge, Fristen, Erinnerungen · V9 Antwortschreiben · V10 Mini-App im Chat · V11 Einfache Installation · V12 Probelauf mit dem Freund · V13 Härtung und Vorlage für weitere · V14 Eigene App (zurückgestellt)

## Entscheidungen (V0, 27.11.2026)

1. **Wo läuft der Bot:** auf holiwork-alpha, eigener Container, ohne Zugriff auf die anderen Dienste dort.
2. **KI:** zum Testen das Claude-Abo des Betreibers; für den Betrieb Mistral über die API (EU, DSGVO). Entschieden am 27.11.2026.
3. **Speicherort:** Nextcloud, über rclone/WebDAV mit eigenem Benutzer `momo` und App-Passwort – Momo sieht nur seinen eigenen Ordner.
4. **Open Source:** ja, Lizenz MIT. Öffnet auch den Weg zur Open-Source-Vorschau von „Mit ChatGPT anmelden“ (V3).
5. **Der Freund** installiert Delta Chat und scannt Momos QR-Code (V12).
