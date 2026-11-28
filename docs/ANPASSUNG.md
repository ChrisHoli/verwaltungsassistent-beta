# Momo – Bauplan (Verwaltungsassistent beta)

Stand: 27.11.2026 (vierte Fassung, V0 entschieden) · Quelle: `docs/quelle/Verwaltungsassistent_beta_Technischer_Bauplan.md` (ChatGPT-Konzept, unverändert abgelegt)

## Richtung

**Momo ist ein Delta-Chat-Bot.** Der Nutzer installiert nur **Delta Chat** (kostenlos, Android, iPhone, Windows, Mac, Linux), scannt einmal einen QR-Code und schreibt oder spricht mit Momo wie mit einem Menschen: Brief fotografieren, Sprachnachricht schicken, Antwort hören.

Der Bot ist **ein eigenständiges Paket** (ein Docker-Container), das überall laufen kann: auf einem Server, einem Raspberry Pi oder einem Computer. Keine Verbindung zu anderen Diensten. **KI** und **Speicherort** wählt, wer den Bot einrichtet.

**Momo** ist der Name des Bots. Erster Nutzer: ein Freund mit Legasthenie. **Thema sind Briefe und Dokumente aller Art** (Ämter, Krankenkasse, Ärzte, Versicherungen, Bank, Vermieter, Arbeit, Rechnungen, Verträge …), nicht nur das Jobcenter: Momo liest, erklärt, **sortiert und legt gut ab** und wird ein richtig guter Assistent für Papierkram (Richtung bestätigt 28.11.2026). Danach Vorlage für weitere Menschen: **ein Bot je Person**.

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

**Jede KI lässt sich einhängen** (seit 28.11.2026). Eine Schnittstelle `KiAnbieter` (`momo/ki/`), Auswahl über `MOMO_KI` in der `.env`; Momo selbst kennt keinen Anbieter:

1. **OpenAI-kompatibel** (`momo/ki/offen.py`), das Format, das fast alle sprechen. Voreinstellungen: `mistral` (EU, Hauptweg für echte Briefe), `openai`, `gemini`, `openrouter`, `groq`, `ollama` (lokal). Für alles andere `openai-kompatibel` mit `MOMO_KI_ADRESSE` (LM Studio, vLLM, IONOS, Scaleway, eigene Server).
2. **`anthropic`**: Claude über die API (`momo/ki/anthropic_api.py`, offizielles SDK, Standard `claude-opus-5-5`, Ersatzmodell bei Ablehnung serverseitig).
3. **`befehl`**: jedes Programm, das Text über die Standardeingabe nimmt und über die Standardausgabe antwortet (`momo/ki/befehl.py`), z. B. `ollama run …` oder ein eigenes Skript.
4. **`claude-abo`**: Claude Code mit Abo, nur zum Testen durch den Betreiber.

Gemeinsame Einstellungen: `MOMO_KI_MODELL`, `MOMO_KI_SCHLUESSEL`, `MOMO_KI_ADRESSE` (Übersicht in `.env.example`). Für echte Briefe zählt der Datenschutz: Mistral (EU) oder eine lokale KI; US-Anbieter nur mit Auftragsverarbeitungsvertrag und Einverständnis.

Nur der Text geht an die KI, keine Fotos. Momo merkt sich die letzten 12 Nachrichten (`daten/verlauf.json`). Ins Log kommen nur der Verbrauch (Tokens) und Fehlerarten, nie Inhalte. Fällt die KI aus, sagt Momo das in einfachen Worten.

DSGVO: Der Anbieter allein reicht nicht. Die Person muss wissen und einverstanden sein, dass ihre Briefe über den Bot und die KI laufen (vor V12 klären).

## Speicherort wählen

Über **rclone** (eine Schnittstelle für alles): Google Drive, **iCloud Drive**, Nextcloud/WebDAV, OneDrive, Dropbox oder ein einfacher Ordner. Daten als lesbare Dateien (je Vorgang ein Ordner: Originale, Text, JSON, Antwortbriefe). Ohne Momo bleiben sie nutzbar; am Computer sieht man sie im jeweiligen Cloud-Ordner.

## Legasthenie und Papierkram

- **Antworten kurz und als Sprachnachricht** (Einstellung „immer vorlesen“), Text immer dazu.
- **Jeder Brief bekommt drei Sätze in Leichter Sprache:** Was ist das? Was musst du tun? Bis wann?
- **Sprechen statt tippen:** Sprachnachrichten werden verstanden (Whisper small, lokal, mit einer Liste von Amtswörtern); keine Befehle nötig, normale Sätze reichen („Was wollte das Jobcenter?“). Im Text steht oben, was Momo verstanden hat, damit ein Hörfehler auffällt. Selbst erledigt (`momo/saetze.py`): „Lies mir den Brief noch mal vor“, „Antworte immer mit Sprache“, „Antworte nur mit Text“ (gemerkt in `daten/einstellungen.json`).
- **Behördenwörter erklärt** aus fester Liste (`momo/woerter.py`: Anhörung, Erstattung, Leistungsminderung, Mitwirkungspflicht, Widerspruch, Bescheid …), höchstens zwei je Brief; Fragen wie „Was heißt Anhörung?“ beantwortet Momo direkt aus der Liste. Die Liste ist ein Entwurf und soll von einer Beratungsstelle geprüft werden.
- **Aktenzeichen und Zahlen** beim Vorlesen einzeln und langsam („neun, acht, sieben, De …“), Beträge als „1087 Euro und 40 Cent“.
- **„Bis wann?“ prüft Momo selbst:** Steht im Brief „bis zum …“ oder „spätestens …“ und die KI hat das Datum nicht sicher, sagt Momo „nicht sicher“ statt „keine Frist“. Fristen wie „innerhalb von 14 Tagen“ zitiert er wörtlich, rechnet aber nicht selbst.
- **Antworten schreiben (V9, `momo/antwortbrief.py`):** „Ich will dem Jobcenter antworten“ oder gleich „Schreib dem Jobcenter, dass …“ → Momo fragt einmal nach Name und Adresse (oder `MOMO_ABSENDER`) → die KI schreibt nur den Brieftext aus dem Gesagten; Absender, Aktenzeichen, Datum, Anrede und Gruß setzt Momo selbst. Die Anschrift der Behörde übernimmt er nur, wenn jede Zeile im Brief steht; Zahlen, die weder gesagt noch im Brief stehen, meldet er. Vorlage als Text und vorgelesen, Änderungen auf Zuruf (neue Vorlage, alte ungültig). PDF nur nach „passt“ als Antwort auf genau die letzte Vorlage; abgelegt unter `<Vorgang>/antwortbriefe/`. Momo versendet nichts selbst.
- **Fristen und Erinnerungen (V8):** Nach jedem Brief fragt Momo je Frist „Soll ich dich an den … erinnern?“. Erinnert wird nur, was mit Ja bestätigt ist (Antwort auf genau diese Nachricht; ohne Zitat gilt die letzte Frage der letzten 12 Stunden), 7 und 2 Tage vorher und am Tag selbst, ab 9 Uhr. Nach einem Ausfall kommt nur die jüngste Erinnerung, nicht alle verpassten. „erledigt“ beendet die Erinnerungen. Bei einem Bescheid mit Widerspruchsmöglichkeit rechnet Momo keine Frist aus, sondern bietet nach drei Wochen eine Wiedervorlage an. Briefe mit gleichem Aktenzeichen gehören zum selben Vorgang. Gespeichert in `daten/vorgaenge.json`, Übersicht als `Fristen.txt` im Speicherort.
- Bei Fristen und Widerspruch: Hinweis auf Beratungsstelle. Momo ist keine Rechtsberatung.

## Betrieb und Installation

- **Nutzer (der Mensch, nicht Momo):** Delta Chat installieren → QR-Code scannen (bekommt er vom Betreiber) → „Hallo“ sagen. Fertig.
- **Betreiber (seit V11, 28.11.2026):** `./einrichten.sh`. Der Assistent (`tools/einrichten.py`, läuft im Container) fragt KI, Speicherort, Postfach, Name und Betreiber ab, prüft jeden Zugang (KI-Testfrage, Probedatei schreiben/lesen/löschen, Postfach-Anmeldung ohne Versand), schreibt `.env` (nur für den Besitzer lesbar, alte als `.env.bak-…`) und startet Momo. Der Einladungs-QR erscheint im Terminal und als `einladung.pdf` (drei Schritte in großer Schrift zum Ausdrucken); nach dem Koppeln löscht Momo beides. Nochmal starten ändert Einstellungen, Enter behält den alten Wert. Updates: `./aktualisieren.sh`, `daten/` bleibt. Anleitung auf einer Seite: `docs/INSTALLATION.md`. Warum nicht im Chat: Passwörter gehören nicht in Nachrichten, und die Person soll mit Technik nichts zu tun haben. Wer ihn zuerst verschlüsselt nutzt, wird Besitzer; danach ist Momo für alle anderen stumm. Zurücksetzen über eine Datei im Datenordner.
- **Wo läuft der Bot?** Für den Probelauf: auf holiwork-alpha in einem **eigenen Container ohne Zugriff auf die anderen Dienste dort**; Nextcloud nur über den eigenen Benutzer `momo`. Später auch auf einem Raspberry Pi bei der Person zu Hause.
- Ein Bot je Person: getrennte Daten, getrennter KI-Schlüssel, leicht übergebbar.

## Sortieren und Ablegen (seit 28.11.2026)

Jedes Dokument bekommt beim Lesen einen **Bereich** (Amt und Behörde, Gesundheit, Versicherung, Bank und Geld, Wohnen, Arbeit, Rechnungen und Verträge, Steuern, Familie und Schule, Sonstiges) und einen kurzen Betreff. Neue Fotos landen in `Briefe/Eingang/`, nach dem Lesen verschiebt Momo sie nach `Briefe/<Bereich>/<Absender>/<Datum> <Betreff>/` (Originale, Text, JSON, Antwortbriefe). Verdächtige Briefe kommen nach `Briefe/Zum Prüfen/`. Momo sagt dazu, wo er das Dokument abgelegt hat.

## Mini-App im Chat (V10)

`momo/app/` wird als webxdc-App (`momo.xdc`) in den Chat geschickt, beim ersten gelesenen Brief von selbst und auf „Zeig mir meine Briefe“ / „Übersicht“. Sie zeigt „Bald wichtig“ (Fristen der nächsten 30 Tage als große Kacheln) und „Meine Briefe“ nach Bereichen, je Brief: Was ist das? Was musst du tun? Abgelegt unter. Knöpfe: Vorlesen (Momo schickt die Sprachnachricht), Erinnern, Erledigt, Antworten (startet V9). Drei Schriften (Atkinson Hyperlegible, Lexend, OpenDyslexic, OFL, liegen bei) und Schriftgröße wählbar. Die App lädt nichts aus dem Netz; Stand und Bitten laufen als webxdc-Aktualisierungen im verschlüsselten Chat.

## Was Momo sich merkt (seit 28.11.2026)

Christian: „Es ist wichtig, dass Momo sich Fakten merken kann, die immer wieder gebraucht werden.“ `momo/fakten.py`, gespeichert in `daten/fakten.json`:
- „Merk dir, meine Versichertennummer ist …“ → die KI macht daraus Einträge (Bezeichnung, Wert); Momo übernimmt nur Werte, die wirklich gesagt wurden, und liest sie zur Kontrolle vor (Nummern Zeichen für Zeichen).
- „Was ist meine Versichertennummer?“, „Was weißt du über mich?“, „Vergiss meine Telefonnummer“ – ohne KI.
- Name und Adresse für Antwortbriefe kommen aus den Fakten. Beim Briefschreiben sieht die KI die Fakten als markierte Daten („nur verwenden, wenn der Brief es braucht“), sonst nie.

## E-Mail (seit 28.11.2026)

Christian: „… die Möglichkeit, dass Momo einen Emailentwurf direkt in einem Emailprogramm aufmachen kann. Und eventuell eine pdf mit anhängen kann. Abschicken könnte auf Bestätigung hin funktionieren.“ `momo/post.py`:
- Nach dem fertigen Antwortbrief: „Als E-Mail“ → Momo legt die E-Mail mit dem PDF über IMAP bei den **Entwürfen im Postfach der Person** ab (fehlt der Ordner, legt er ihn an). So erscheint sie in jedem E-Mail-Programm, Handy oder Computer. Ein `mailto:`-Link scheidet aus: Delta Chat fängt ihn selbst ab, und Anhänge gehen damit nicht.
- Empfänger: steht genau eine Adresse im Brief, nimmt Momo sie (und sagt das); bei mehreren fragt er nach der Nummer, sonst nach der Adresse (gesprochen „max punkt muster ät beispiel punkt de“ geht).
- **Abschicken** nur mit `MOMO_MAIL_SENDEN=ja` und wenn die Person auf genau diese Nachricht mit „Ja, abschicken“ antwortet (24 Stunden gültig). Momo schickt genau die E-Mail, die im Entwurf liegt, räumt den Entwurf weg und legt eine Kopie bei „Gesendet“ ab.
- Zugang: `MOMO_MAIL_ADRESSE`, `MOMO_MAIL_PASSWORT` (App-Passwort), `MOMO_MAIL_IMAP`, `MOMO_MAIL_SMTP`.

## Datenschutz und Sicherung (seit 28.11.2026)

- **Hinweis beim ersten Kontakt** (`momo/datenschutz.py`): Momo sagt einmal in einfachen Worten, wo er läuft (`MOMO_BETREIBER`), dass der Chat verschlüsselt ist, dass Fotos und Sprache auf dem Gerät bleiben, an welche KI der Text geht (aus `MOMO_KI` gebaut, mit Land), wo die Briefe liegen und wie man alles löschen lässt. Auf „Was passiert mit meinen Daten?“ wiederholt er ihn.
- **Aufbewahrung:** Den Chat mit Fotos und Sprachnachrichten löscht Momo bei sich nach `MOMO_AUFHEBEN_TAGE` (Standard 30; Delta-Chat-Einstellung `delete_device_after`). Die Briefe im Speicherort bleiben, bis die Person sie löschen lässt. Das Gespräch für die KI umfasst ohnehin nur die letzten 12 Nachrichten.
- **„Lösch alles von mir“:** Momo fragt nach und löscht erst, wenn die Person direkt auf diese Frage mit „Ja, löschen“ antwortet (innerhalb einer Stunde): Briefe und `Fristen.txt` im Speicherort, Fristen, Entwürfe, Absender, Einstellungen, Gesprächsverlauf und den Chat bei Momo. Kopplung und Konto bleiben, damit die Person weiter schreiben kann.
- **Sicherung:** Zu sichern sind der Datenordner `daten/` (darin das Delta-Chat-Konto mit Momos Schlüssel: ohne ihn muss neu gekoppelt werden) und der Speicherort. Wiederherstellen: Container stoppen, `daten/` zurückkopieren, starten. Auf holiwork-alpha erfasst die nächtliche restic-Sicherung `/home/christian` (also `~/momo/daten`) und die Nextcloud; die Wiederherstellung wurde am 28.11.2026 geprobt (Datenbank heil, Schlüssel vorhanden).
- Vor dem Probelauf (V12) mit echten Briefen: Einverständnis der Person zu diesem Hinweis einholen.

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
