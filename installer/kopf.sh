#!/bin/sh
# Momo installieren – Linux und macOS. Eine Datei, alles drin.
#
#   sh momo-installieren.sh            installiert nach ~/Momo
#   sh momo-installieren.sh /pfad      installiert woandershin
#
# Noch einmal starten = Momo aktualisieren oder Einstellungen ändern.
# Briefe, Fristen, Gemerktes und die Kopplung ans Handy bleiben dabei erhalten.
set -eu

ZIEL="${1:-$HOME/Momo}"
FASSUNG="@FASSUNG@"

EIN=/dev/tty; [ -t 0 ] || EIN=/dev/stdin   # ohne Terminal: Antworten aus der Eingabe (zum Testen)
sag()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
weiter() { printf '%s [Enter] ' "$1"; read -r _ <"$EIN"; }
frage_ja() {  # frage_ja "Text" → 0 bei ja (Vorgabe ja)
  printf '%s [J/n] ' "$1"; read -r a <"$EIN" || a=""
  case "$a" in n|N|nein|Nein) return 1 ;; *) return 0 ;; esac
}

sag "Momo $FASSUNG – Installation"
echo "Ziel: $ZIEL"

# ── 1. Docker ────────────────────────────────────────────────────────────
D=""
docker_finden() {
  if docker info >/dev/null 2>&1; then D="docker"
  elif command -v sudo >/dev/null 2>&1 && command -v docker >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then D="sudo docker"
  else D=""; fi
}
docker_finden
if [ -z "$D" ]; then
  case "$(uname -s)" in
    Linux)
      sag "1. Docker fehlt noch."
      echo "Momo läuft in Docker. Das wird jetzt installiert (braucht das Admin-Passwort, etwa 2 Minuten)."
      frage_ja "Docker installieren?" || { echo "Ohne Docker geht es nicht. Abgebrochen."; exit 1; }
      curl -fsSL https://get.docker.com | sudo sh
      sudo systemctl enable --now docker >/dev/null 2>&1 || true
      sudo usermod -aG docker "$(id -un)" 2>/dev/null || true
      docker_finden
      ;;
    Darwin)
      sag "1. Docker Desktop fehlt noch."
      echo "Bitte Docker Desktop installieren und einmal starten:"
      echo "  https://www.docker.com/products/docker-desktop/"
      echo "In Docker Desktop unter Einstellungen → General „Start Docker Desktop when you sign in“ einschalten,"
      echo "damit Momo nach jedem Neustart von selbst läuft."
      open "https://www.docker.com/products/docker-desktop/" 2>/dev/null || true
      while [ -z "$D" ]; do weiter "Wenn Docker Desktop läuft:"; docker_finden; done
      ;;
  esac
fi
[ -n "$D" ] || { echo "Docker läuft nicht. Bitte starten und dieses Skript noch einmal aufrufen." >&2; exit 1; }
$D compose version >/dev/null 2>&1 || { echo "„docker compose“ fehlt. Bitte Docker aktualisieren." >&2; exit 1; }
echo "Docker ist da."

# ── 2. Momo auspacken ────────────────────────────────────────────────────
sag "2. Momo auspacken"
mkdir -p "$ZIEL"
ZEILE=$(awk '/^__ARCHIV_FOLGT__$/ { print NR + 1; exit }' "$0")
# Nur Programmteile werden ersetzt; daten/, Ablage/, .env und eigene Anpassungen bleiben.
tail -n +"$ZEILE" "$0" | tar -xzf - -C "$ZIEL"
cd "$ZIEL"
mkdir -p daten Ablage
[ -O daten ] && chmod 700 daten || true   # gehört nach dem ersten Lauf Momo selbst

# Briefe in einem sichtbaren Ordner statt versteckt in daten/
if [ ! -f docker-compose.override.yml ]; then
  cat > docker-compose.override.yml <<'EOF'
# Auf diesem Rechner: Briefe liegen sichtbar im Ordner „Ablage“ (darin „Briefe“).
services:
  momo:
    volumes:
      - ./Ablage:/daten/ablage
EOF
fi
# Vorgaben für den Assistenten: Delta Chat, Briefe auf diesem Rechner, nichts in die Cloud
if [ ! -s .env ]; then
  umask 077
  printf 'MOMO_MESSENGER=deltachat\nMOMO_ABLAGE=ordner\nMOMO_ABLAGE_ZIEL=/daten/ablage\nMOMO_KI=mistral\n' > .env
  umask 022
fi
echo "Ausgepackt nach $ZIEL"

# ── 3. Bauen und Ordner vorbereiten ──────────────────────────────────────
sag "3. Momo bauen – beim ersten Mal 10 bis 20 Minuten. Kaffee?"
$D compose build -q </dev/null
# Momo läuft im Container ohne Root-Rechte (Benutzer 10001) und muss in beide Ordner schreiben dürfen
$D compose run --rm --no-deps -T --user root --cap-add CHOWN --cap-add FOWNER --cap-add DAC_OVERRIDE momo \
  sh -c 'chown 10001 /daten /daten/ablage && chmod 755 /daten/ablage' </dev/null

# ── 4. Einrichtungsassistent ─────────────────────────────────────────────
sag "4. Einstellungen"
echo "Gleich fragt der Assistent nach KI, Speicherort und E-Mail. Enter übernimmt den Vorschlag."
echo "Tipp: beim Speicherort „Ordner auf diesem Rechner“ wählen – dann bleibt alles hier."
sh ./einrichten.sh <"$EIN"

# ── 5. Fertig ────────────────────────────────────────────────────────────
cat > MOMO-HILFE.txt <<EOF
Momo $FASSUNG auf diesem Rechner
================================

Ordner:        $ZIEL
Briefe:        $ZIEL/Ablage/Briefe   (nach Bereichen sortiert)
Momos Gedächtnis: $ZIEL/daten        (Fristen, Fakten, Kopplung – nicht löschen)
Einstellungen: $ZIEL/.env            (Schlüssel und Passwörter – nie weitergeben)

Momo startet nach einem Neustart des Rechners von selbst, sobald Docker läuft.
Ist der Rechner aus oder im Ruhezustand, antwortet Momo nicht. Nachrichten gehen
nicht verloren: Momo beantwortet sie, sobald der Rechner wieder an ist.

Läuft Momo?            cd "$ZIEL" && $D compose ps
Was macht Momo?        cd "$ZIEL" && $D compose logs --tail 30 momo
Einladung neu zeigen   cd "$ZIEL" && $D compose exec momo python -m tools.einladung
Neu koppeln (neues Handy, andere Person):
                       rm "$ZIEL/daten/besitzer.json" && cd "$ZIEL" && $D compose restart momo
                       danach Einladung neu zeigen
Einstellungen ändern   cd "$ZIEL" && sh einrichten.sh
Aktualisieren          neue momo-installieren.sh herunterladen und starten
Anhalten / Starten     cd "$ZIEL" && $D compose stop   bzw.   $D compose up -d

Sichern: die Ordner Ablage und daten und die Datei .env regelmäßig auf eine
USB-Platte kopieren (Momo vorher anhalten).
EOF
sag "Fertig. Momo läuft."
echo "Das Einladungsblatt zum Ausdrucken: $ZIEL/einladung.pdf"
echo "Auf dem Handy: Delta Chat installieren, QR-Code scannen, „Hallo“ schreiben."
echo "Hilfe für später: $ZIEL/MOMO-HILFE.txt"
exit 0
__ARCHIV_FOLGT__
