#!/bin/sh
# Momo einrichten oder Einstellungen ändern. Einfach starten: ./einrichten.sh
# Baut das Abbild, fragt KI, Speicherort und Postfach ab, prüft sie, schreibt .env und startet Momo.
set -eu
cd "$(dirname "$0")"
umask 077

if docker info >/dev/null 2>&1; then D="docker"; else D="sudo docker"; fi
if ! $D compose version >/dev/null 2>&1; then
  echo "Docker mit „docker compose“ fehlt. Anleitung: docs/INSTALLATION.md" >&2; exit 1
fi
TTY=""; [ -t 0 ] || TTY="-T"   # ohne Terminal (z. B. Eingaben aus einer Datei)

[ -f .env ] || : > .env
mkdir -p daten

echo "Baue Momo. Beim ersten Mal dauert das 10 bis 20 Minuten …"
$D compose build -q </dev/null
$D compose run --rm --no-deps -T --user root --cap-add CHOWN momo sh -c '[ "$(stat -c %u /daten)" = 10001 ] || chown 10001 /daten' </dev/null

if ! $D compose run --rm --no-deps $TTY momo python -m tools.einrichten "$@"; then
  echo "Nichts geändert."; exit 1
fi
$D compose run --rm --no-deps -T momo cat /daten/einrichtung.env </dev/null > .env.neu
$D compose run --rm --no-deps -T momo rm -f /daten/einrichtung.env </dev/null
if [ ! -s .env.neu ]; then rm -f .env.neu; echo "Nichts geändert."; exit 1; fi
if [ -s .env ]; then cp .env ".env.bak-$(date +%Y%m%d-%H%M%S)"; fi
mv .env.neu .env

# Signal: eigener Dienst, einmal mit dem Handy verbinden
if grep -q '^MOMO_MESSENGER=signal' .env; then
  $D compose up -d signal </dev/null
  if ! $D compose run --rm --no-deps $TTY momo python -m tools.signal_verbinden; then
    echo "Signal ist noch nicht verbunden. Momo startet trotzdem; später ./einrichten.sh noch einmal."
  fi
fi

# Claude-Abo und Mistral Vibe brauchen ihr Programm im Abbild (MIT_CLAUDE=1 / MIT_VIBE=1 stehen dann in .env)
if grep -q '^MIT_CLAUDE=1\|^MIT_VIBE=1' .env; then
  echo "Baue das Programm für die KI ein …"; $D compose build -q </dev/null
  $D compose run --rm --no-deps -T momo python -m tools.einrichten --nur-ki </dev/null || true
fi

$D compose up -d </dev/null
echo "Momo läuft. Einladung wird vorbereitet (beim ersten Start bis zu zwei Minuten) …"
if $D compose exec -T momo python -m tools.einladung --warten 300 </dev/null; then
  # daten/ bleibt privat; das Blatt zum Ausdrucken kommt hierher
  $D compose exec -T momo sh -c 'cat /daten/einladung.pdf 2>/dev/null' </dev/null > einladung.pdf || true
  if [ -s einladung.pdf ]; then echo "Zum Ausdrucken: $(pwd)/einladung.pdf"; else rm -f einladung.pdf; fi
fi
