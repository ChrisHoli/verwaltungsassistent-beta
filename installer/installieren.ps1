# Momo installieren – Windows 10/11. Start per Doppelklick auf „Momo-installieren.cmd“.
# Noch einmal starten = Momo aktualisieren oder Einstellungen ändern.
# Briefe, Fristen, Gemerktes und die Kopplung ans Handy bleiben dabei erhalten.
param([string]$Ziel = (Join-Path $env:USERPROFILE "Momo"))

$Fassung = "@FASSUNG@"
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$Hier = Split-Path -Parent $MyInvocation.MyCommand.Path
$OhneBom = New-Object System.Text.UTF8Encoding $false

function Sag($t)   { Write-Host ""; Write-Host $t -ForegroundColor Cyan }
function Fehler($t) { Write-Host $t -ForegroundColor Red; exit 1 }
function Schreibe($pfad, $text) { [IO.File]::WriteAllText($pfad, ($text -replace "`r`n", "`n"), $OhneBom) }
function Docker-Laeuft { docker info *> $null; return ($LASTEXITCODE -eq 0) }

Sag "Momo $Fassung – Installation"
Write-Host "Ziel: $Ziel"

# ── 1. Docker ────────────────────────────────────────────────────────────
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Sag "1. Docker Desktop fehlt noch."
    Write-Host "Momo läuft in Docker. Docker Desktop wird jetzt installiert (Admin-Rechte, einige Minuten)."
    $a = Read-Host "Docker Desktop installieren? [J/n]"
    if ($a -match '^(n|nein)$') { Fehler "Ohne Docker geht es nicht. Abgebrochen." }
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
    } else {
        Start-Process "https://www.docker.com/products/docker-desktop/"
        Write-Host "Bitte Docker Desktop von der geöffneten Seite installieren."
    }
    Write-Host ""
    Write-Host "Jetzt bitte:" -ForegroundColor Yellow
    Write-Host "  1. Den Rechner neu starten."
    Write-Host "  2. Docker Desktop öffnen und die Einrichtung abschließen (ein Konto ist nicht nötig, „Skip“)."
    Write-Host "  3. Diese Installation noch einmal starten."
    Read-Host "Enter zum Beenden"
    exit 0
}
while (-not (Docker-Laeuft)) {
    Write-Host "Docker Desktop läuft noch nicht. Bitte starten und warten, bis unten links „Engine running“ steht." -ForegroundColor Yellow
    Start-Process "Docker Desktop" -ErrorAction SilentlyContinue
    Read-Host "Enter, wenn Docker läuft"
}
docker compose version *> $null
if ($LASTEXITCODE -ne 0) { Fehler "„docker compose“ fehlt. Bitte Docker Desktop aktualisieren." }
Write-Host "Docker ist da."

# ── 2. Momo auspacken ────────────────────────────────────────────────────
Sag "2. Momo auspacken"
New-Item -ItemType Directory -Force -Path $Ziel, (Join-Path $Ziel "daten"), (Join-Path $Ziel "Ablage") | Out-Null
# Nur Programmteile werden ersetzt; daten, Ablage, .env und eigene Anpassungen bleiben.
tar -xzf (Join-Path $Hier "momo-programm.tar.gz") -C $Ziel
if ($LASTEXITCODE -ne 0) { Fehler "Auspacken hat nicht geklappt." }
Set-Location $Ziel

if (-not (Test-Path "docker-compose.override.yml")) {
    Schreibe (Join-Path $Ziel "docker-compose.override.yml") @"
# Auf diesem Rechner: Briefe liegen sichtbar im Ordner „Ablage“ (darin „Briefe“).
services:
  momo:
    volumes:
      - ./Ablage:/daten/ablage
"@
}
$env_pfad = Join-Path $Ziel ".env"
if (-not (Test-Path $env_pfad) -or (Get-Item $env_pfad).Length -eq 0) {
    Schreibe $env_pfad "MOMO_MESSENGER=deltachat`nMOMO_ABLAGE=ordner`nMOMO_ABLAGE_ZIEL=/daten/ablage`nMOMO_KI=mistral`n"
}
Write-Host "Ausgepackt nach $Ziel"

# ── 3. Bauen ─────────────────────────────────────────────────────────────
Sag "3. Momo bauen – beim ersten Mal 10 bis 20 Minuten. Kaffee?"
docker compose build -q
if ($LASTEXITCODE -ne 0) { Fehler "Bauen hat nicht geklappt. Läuft Docker Desktop? Ist Internet da?" }
docker compose run --rm --no-deps -T --user root --cap-add CHOWN --cap-add FOWNER --cap-add DAC_OVERRIDE momo sh -c 'chown 10001 /daten /daten/ablage; chmod 755 /daten/ablage' | Out-Null

# ── 4. Einrichtungsassistent ─────────────────────────────────────────────
Sag "4. Einstellungen"
Write-Host "Gleich fragt der Assistent nach KI, Speicherort und E-Mail. Enter übernimmt den Vorschlag."
Write-Host "Tipp: beim Speicherort „Ordner auf diesem Rechner“ wählen – dann bleibt alles hier."
docker compose run --rm --no-deps momo python -m tools.einrichten
if ($LASTEXITCODE -ne 0) { Fehler "Nichts geändert." }
$neu = Join-Path $Ziel "daten\einrichtung.env"
if (-not (Test-Path $neu) -or (Get-Item $neu).Length -eq 0) { Fehler "Nichts geändert." }
if ((Test-Path $env_pfad) -and (Get-Item $env_pfad).Length -gt 0) {
    Copy-Item $env_pfad (Join-Path $Ziel (".env.bak-" + (Get-Date -Format "yyyyMMdd-HHmmss")))
}
Move-Item -Force $neu $env_pfad

if (Select-String -Path $env_pfad -Pattern '^(MIT_CLAUDE|MIT_VIBE)=1' -Quiet) {
    Write-Host "Baue das Programm für die KI ein …"
    docker compose build -q
    docker compose run --rm --no-deps -T momo python -m tools.einrichten --nur-ki
}

docker compose up -d
if ($LASTEXITCODE -ne 0) { Fehler "Momo startet nicht. Nachsehen: docker compose logs momo" }
Write-Host "Momo läuft. Einladung wird vorbereitet (beim ersten Start bis zu zwei Minuten) …"
docker compose exec -T momo python -m tools.einladung --warten 300
$blatt = Join-Path $Ziel "daten\einladung.pdf"
if (Test-Path $blatt) { Copy-Item -Force $blatt (Join-Path $Ziel "einladung.pdf") }

# ── 5. Fertig ────────────────────────────────────────────────────────────
Schreibe (Join-Path $Ziel "MOMO-HILFE.txt") @"
Momo $Fassung auf diesem Rechner
================================

Ordner:           $Ziel
Briefe:           $Ziel\Ablage\Briefe   (nach Bereichen sortiert)
Momos Gedächtnis: $Ziel\daten      (Fristen, Fakten, Kopplung – nicht löschen)
Einstellungen:    $Ziel\.env       (Schlüssel und Passwörter – nie weitergeben)

Momo startet nach einem Neustart von selbst, sobald Docker Desktop läuft.
In Docker Desktop unter Settings → General „Start Docker Desktop when you sign in“ eingeschaltet lassen.
Ist der Rechner aus oder im Ruhezustand, antwortet Momo nicht. Nachrichten gehen
nicht verloren: Momo beantwortet sie, sobald der Rechner wieder an ist.

Befehle in PowerShell, vorher:  cd "$Ziel"
  Läuft Momo?            docker compose ps
  Was macht Momo?        docker compose logs --tail 30 momo
  Einladung neu zeigen   docker compose exec momo python -m tools.einladung
  Neu koppeln            del daten\besitzer.json ; docker compose restart momo   (dann Einladung neu zeigen)
  Einstellungen ändern   Momo-installieren.cmd noch einmal starten
  Anhalten / Starten     docker compose stop   bzw.   docker compose up -d

Sichern: die Ordner Ablage und daten und die Datei .env regelmäßig auf eine
USB-Platte kopieren (Momo vorher anhalten).
"@
Sag "Fertig. Momo läuft."
Write-Host "Das Einladungsblatt zum Ausdrucken: $Ziel\einladung.pdf"
Write-Host "Auf dem Handy: Delta Chat installieren, QR-Code scannen, „Hallo“ schreiben."
Write-Host "Hilfe für später: $Ziel\MOMO-HILFE.txt"
if (Test-Path (Join-Path $Ziel "einladung.pdf")) { Start-Process (Join-Path $Ziel "einladung.pdf") }
Start-Process explorer.exe $Ziel
