"""Abnahme V5: die zehn erfundenen Briefe gegen die eingestellte KI (MOMO_KI) laufen lassen.

    docker compose exec momo python -m tools.pruefe_briefe
"""

import sys

from momo.aufnahme import aufnehmen
from momo.ki import anbieter_waehlen
from tools.testbriefe import BRIEFE, bewerten


def main() -> int:
    import os

    ki = anbieter_waehlen(os.environ.get("MOMO_KI", "keine"))
    bestanden = 0
    for brief in BRIEFE:
        ergebnis = aufnehmen(ki, brief["seiten"])
        fehler = bewerten(ergebnis, brief["erwartet"])
        status = "ok " if not fehler else "FEHLER"
        bestanden += not fehler
        print(f"{status} {brief['name']}: pruefen={ergebnis['pruefen']} "
              f"verdacht={ergebnis['verdacht_manipulation']} {'; '.join(fehler)}")
    print(f"\n{bestanden}/{len(BRIEFE)} bestanden")
    return 0 if bestanden == len(BRIEFE) else 1


if __name__ == "__main__":
    sys.exit(main())
