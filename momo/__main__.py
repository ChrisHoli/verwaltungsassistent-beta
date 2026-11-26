import logging

from .ablage import ablage_waehlen
from .bote import Bote
from .ki import anbieter_waehlen
from .konfig import Konfig
from .stimme import Stimme


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Delta-Chat-Ereignisse nicht im Einzelnen protokollieren (könnten Inhalte enthalten)
    logging.getLogger("deltachat_rpc_client").setLevel(logging.WARNING)
    konfig = Konfig.aus_umgebung()
    konfig.daten.mkdir(parents=True, exist_ok=True)
    ki = anbieter_waehlen(konfig.ki)
    ablage_waehlen(konfig.ablage, konfig.ablage_ziel)
    stimme = Stimme(konfig.stimme)
    logging.info("%s startet · KI: %s · Ablage: %s · Vorlesen: %s (Stimme %s)", konfig.name, ki.name,
                 konfig.ablage, konfig.vorlesen, "da" if stimme.verfuegbar else "fehlt")
    Bote(konfig, stimme).starten()


if __name__ == "__main__":
    main()
