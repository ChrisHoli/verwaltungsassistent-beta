# Momo installieren

Eine Seite für die Person, die Momo betreibt. Für jeden Menschen, der Momo nutzt, läuft ein eigener Momo.

## Was du brauchst

- Einen Rechner, der immer an ist: einen kleinen Server, einen alten PC mit mindestens 4 GB Arbeitsspeicher und etwa 6 GB Platz. Ein Raspberry Pi 4/5 sollte gehen, ist aber noch nicht ausprobiert.
- Linux mit Docker: `curl -fsSL https://get.docker.com | sh` (auf Debian, Ubuntu und Raspberry Pi OS).
- Eine KI mit Zugangsschlüssel. Der Assistent fragt danach (siehe „Welche KI?“ unten).
- Optional: einen Speicherort in der Cloud (Nextcloud, Google Drive, iCloud Drive, OneDrive, Dropbox) und ein Postfach mit App-Passwort.

## Einrichten

```sh
git clone https://github.com/ChrisHoli/verwaltungsassistent-beta.git momo
cd momo
./einrichten.sh
```

Der Assistent baut Momo (beim ersten Mal 10 bis 20 Minuten) und fragt dann der Reihe nach:

1. **Welche KI?** Danach den Schlüssel und das Modell.
2. **Wo sollen die Briefe liegen?** Zur Wahl stehen ein Ordner auf dem Rechner, eine Nextcloud oder eine andere Cloud.
3. **E-Mail?** Das ist freiwillig. Gefragt werden Adresse und App-Passwort und ob Momo nach Bestätigung selbst abschicken darf.
4. **Name im Chat, wer Momo betreibt, Sprachnachrichten ja oder nein.**

Jeden Zugang prüft er sofort:

- Die KI bekommt eine Testfrage.
- In den Speicherort schreibt er eine Probedatei und löscht sie wieder.
- Beim Postfach meldet er sich nur an, er schickt nichts.

Klappt etwas nicht, sagt er, woran es liegt. Dann gibst du die Angaben neu ein, übernimmst sie trotzdem oder brichst ab. Bei Abbruch bleibt alles, wie es war.

Am Ende schreibt er die Datei `.env`, startet Momo und zeigt den **Einladungs-QR** im Terminal. Zum Ausdrucken liegt er als `einladung.pdf` im Momo-Ordner bereit, mit drei Schritten in großer Schrift. Das Blatt gibst du der Person. Sie installiert den Messenger, scannt den Code und schreibt „Hallo“ (bei Telegram: „Starten“). Wer zuerst schreibt, wird Besitzer. Alle anderen ignoriert Momo.

Passwörter und Schlüssel stehen nur in `.env` auf diesem Rechner. Die Datei kann nur ihr Besitzer lesen. Sie gehört nie in einen Chat oder ins Repo.

## Welcher Messenger?

| Wahl | Gut | Bedenken |
|---|---|---|
| **Delta Chat** (empfohlen) | verschlüsselt, keine Telefonnummer, Übersicht als Mini-App im Chat, löscht den Chat nach 30 Tagen auf beiden Seiten | die Person muss eine neue App lernen |
| Signal | verschlüsselt, viele kennen es | Momo braucht eine eigene Handynummer (z. B. Prepaid-Karte); auf dem Handy mit dieser Nummer wird Momo als „verknüpftes Gerät“ hinzugefügt – der Assistent zeigt den Code. Übersicht als Text statt Mini-App |
| Telegram | verbreitet, in fünf Minuten eingerichtet (@BotFather → /newbot) | **Telegram kann mitlesen**, auch die Fotos der Briefe. Übersicht als Text |

WhatsApp geht nicht: Meta lässt Programme nur über die Business-Schnittstelle zu. Dafür braucht es ein Firmenkonto, eine eigene Nummer und einen Server, der aus dem Internet erreichbar ist; Erinnerungen kosten Geld und brauchen vorab genehmigte Vorlagen. Inoffizielle Wege verstoßen gegen die Regeln von WhatsApp, die Nummer kann gesperrt werden.

Bei Signal liegen die Schlüssel im Docker-Volume `signal` – beim Sichern mitnehmen.

## Welche KI?

| Wahl | Wofür | Daten |
|---|---|---|
| **Mistral** (empfohlen) | gute Erklärungen, günstig | EU (Frankreich) |
| Mistral Vibe | wie Mistral, aber über ein Le-Chat-Abo statt Abrechnung pro Brief | EU (Frankreich) |
| Claude (Anthropic) | die besten Antwortbriefe | USA |
| ChatGPT, Gemini | geht auch | USA |
| Ollama | ohne Cloud, braucht einen starken Rechner | bleibt im Haus |
| Anderer Dienst | alles mit OpenAI-Schnittstelle (IONOS, Scaleway, OpenRouter, LM Studio …) | je nach Dienst |
| Keine KI | Momo legt ab und liest vor, erklärt aber nicht | – |

Die KI bekommt immer nur den Text, nie Fotos. Persönliche Angaben wie die Adresse sieht sie nur beim Schreiben eines Antwortbriefs. Mehr dazu und alle Einstellungen: `.env.example` und `docs/ANPASSUNG.md`.

## Später

- **Etwas ändern** (andere KI, Postfach dazu): `./einrichten.sh` noch einmal starten. Enter behält den bisherigen Wert. Die alte `.env` wird vorher gesichert.
- **Aktualisieren:** `./aktualisieren.sh`. Briefe, Fristen, Gemerktes und die Kopplung im Ordner `daten/` bleiben.
- **Nachsehen, ob alles läuft:** `docker compose logs --tail 20 momo`. Die erste Zeile nach dem Start nennt KI, Speicherort, Stimme und E-Mail.
- **Neu koppeln** (neues Handy, andere Person): `daten/besitzer.json` löschen, `docker compose restart momo`, dann `./einrichten.sh` (Enter bei allem) oder `docker compose exec momo python -m tools.einladung`.
- **Sichern:** den ganzen Ordner `daten/` und die `.env` regelmäßig sichern, zum Beispiel mit restic.
- **Alles über die Person löschen:** Sie sagt im Chat „Lösch alles von mir“ und bestätigt das.
