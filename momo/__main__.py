import logging
from pathlib import Path

from .ablage import ablage_waehlen
from .bote import Bote
from .briefe import Briefablage
from .gespraech import Gespraech
from .ki import anbieter_waehlen
from .konfig import Konfig
from .stimme import Stimme
from .zuhoeren import Ohr
from . import post


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Delta-Chat-Ereignisse nicht im Einzelnen protokollieren (könnten Inhalte enthalten)
    logging.getLogger("deltachat_rpc_client").setLevel(logging.WARNING)
    # httpx schreibt jede Adresse ins Log; bei Telegram steht der Zugangsschlüssel darin
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    konfig = Konfig.aus_umgebung()
    konfig.daten.mkdir(parents=True, exist_ok=True)
    ki = anbieter_waehlen(konfig.ki)
    ablage = ablage_waehlen(konfig.ablage, konfig.ablage_ziel)
    try:
        ablage.pruefen()
        ablage_ok = "erreichbar"
    except Exception as e:  # Start nicht verhindern, aber deutlich melden
        ablage_ok = f"NICHT erreichbar ({str(e)[:120]})"
    stimme = Stimme(konfig.stimme, prozent=konfig.sprechtempo)
    ohr = Ohr(konfig.whisper, Path("/app/whisper"))
    logging.info("%s startet · KI: %s · Ablage: %s %s · Vorlesen: %s (Stimme %s) · Zuhören: %s (%s)", konfig.name,
                 ki.name, konfig.ablage, ablage_ok, konfig.vorlesen, "da" if stimme.verfuegbar else "fehlt",
                 "da" if ohr.verfuegbar else "fehlt", konfig.whisper)
    gespraech = Gespraech(ki, konfig.name, konfig.daten / "verlauf.json")
    import os

    zugang = post.Zugang.aus_umgebung(os.environ)
    logging.info("E-Mail: %s", "nicht eingerichtet" if zugang is None else
                 f"Entwürfe ins Postfach, Abschicken {'nach Bestätigung' if zugang.senden else 'aus'}")
    from .kanal import kanal_waehlen

    kanal = kanal_waehlen(konfig.messenger, konfig)
    logging.info("Messenger: %s", kanal.name)
    Bote(konfig, stimme, gespraech, Briefablage(ablage), ohr, post.Postfach(zugang) if zugang else None,
         kanal).starten()


if __name__ == "__main__":
    main()
