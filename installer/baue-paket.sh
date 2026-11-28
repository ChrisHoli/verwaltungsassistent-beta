#!/bin/sh
# Baut die Installationsdateien aus dem eingecheckten Stand (git HEAD):
#   momo-installieren.sh          Linux und macOS, eine Datei
#   Momo-Installation-Windows.zip Windows (Doppelklick auf Momo-installieren.cmd)
#   sh installer/baue-paket.sh [Zielordner]
set -eu
cd "$(dirname "$0")/.."
AUS="${1:-paket}"
mkdir -p "$AUS"
FASSUNG="$(date +%Y-%m-%d)-$(git rev-parse --short HEAD)"
[ -z "$(git status --porcelain -- momo tools Dockerfile docker-compose.yml einrichten.sh requirements.txt)" ] \
  || { FASSUNG="$FASSUNG+"; echo "Hinweis: nicht eingecheckte Änderungen sind dabei (Fassung $FASSUNG)." >&2; }

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
# Arbeitsstand: eingecheckte und neue Dateien, ohne Ignoriertes (.env, daten/ …), ohne Tests und Installer-Quellen
git ls-files -z --cached --others --exclude-standard -- . ':!tests' ':!installer' ':!docs/quelle' \
  | xargs -0 sh -c 'for f; do [ -f "$f" ] && printf "%s\0" "$f"; done' _ \
  | tar --null -T - -czf "$TMP/momo-programm.tar.gz"

sed "s/@FASSUNG@/$FASSUNG/" installer/kopf.sh > "$AUS/momo-installieren.sh"
cat "$TMP/momo-programm.tar.gz" >> "$AUS/momo-installieren.sh"
chmod +x "$AUS/momo-installieren.sh"

W="$TMP/Momo-Installation"; mkdir -p "$W"
printf '\357\273\277' > "$W/installieren.ps1"   # BOM: Windows PowerShell 5.1 liest sonst Umlaute falsch
sed "s/@FASSUNG@/$FASSUNG/" installer/installieren.ps1 | sed 's/$/\r/' >> "$W/installieren.ps1"
sed 's/$/\r/' installer/Momo-installieren.cmd > "$W/Momo-installieren.cmd"
cp "$TMP/momo-programm.tar.gz" "$W/"
rm -f "$AUS/Momo-Installation-Windows.zip"
(cd "$TMP" && zip -qr - Momo-Installation) > "$AUS/Momo-Installation-Windows.zip"

echo "Fassung $FASSUNG"
ls -lh "$AUS/momo-installieren.sh" "$AUS/Momo-Installation-Windows.zip"
