#!/bin/sh
# Momo auf den neuesten Stand bringen. Briefe, Fristen, Fakten und Kopplung (Ordner daten/) bleiben.
set -eu
cd "$(dirname "$0")"
if docker info >/dev/null 2>&1; then D="docker"; else D="sudo docker"; fi
git pull --ff-only
$D compose build -q
$D compose up -d
echo "Aktualisiert. Nachsehen: $D compose logs --tail 20 momo"
