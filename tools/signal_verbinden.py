"""Momo mit Signal verbinden: als „verknüpftes Gerät“ des Handys mit Momos Signal-Nummer.

    python -m tools.signal_verbinden      (startet ./einrichten.sh, wenn MOMO_MESSENGER=signal)
"""

import os
import sys
import time


def main() -> int:
    from momo.kanal.signal import Api, SignalFehler

    nummer = os.environ.get("MOMO_SIGNAL_NUMMER", "").strip()
    api = Api(os.environ.get("MOMO_SIGNAL_API", "http://signal:8080"), nummer)
    for _ in range(30):  # der Signal-Dienst braucht nach dem Start einen Moment
        try:
            konten = api.konten()
            break
        except Exception:  # noqa: BLE001
            time.sleep(2)
    else:
        print("Der Signal-Dienst antwortet nicht. Nachsehen: docker compose logs signal")
        return 1
    if nummer in konten:
        print(f"Signal ist schon verbunden ({nummer[:6]}…).")
        return 0
    try:
        link = api.verbinden_link("Momo")
    except SignalFehler as e:
        print(f"Kein Verbindungscode: {e}")
        return 1
    import segno

    print("\nAuf dem Handy mit Momos Nummer: Signal → Einstellungen → Verknüpfte Geräte → „+“ → diesen Code scannen.\n")
    segno.make(link, error="l").terminal(compact=True)
    print("\nIch warte, bis das Handy bestätigt hat (bis zu 5 Minuten) …")
    ende = time.time() + 300
    while time.time() < ende:
        time.sleep(3)
        try:
            konten = api.konten()
        except SignalFehler:
            continue
        if nummer in konten:
            print("✓ Signal ist verbunden.")
            return 0
        if konten:
            print(f"Verbunden ist eine andere Nummer ({', '.join(k[:6] + '…' for k in konten)}). "
                  "Stimmt MOMO_SIGNAL_NUMMER? Dann ./einrichten.sh noch einmal starten.")
            return 1
    print("Nicht bestätigt. ./einrichten.sh noch einmal starten, dann gibt es einen neuen Code.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
