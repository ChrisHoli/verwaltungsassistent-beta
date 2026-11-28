"""Claude über die Anthropic-API (Schlüssel aus der Claude Console, Abrechnung nach Verbrauch).

Nutzt das offizielle SDK. Weigert sich das Modell aus Sicherheitsgründen, springt serverseitig das passende
Ersatzmodell ein (fallbacks="default"); weigert sich auch das, meldet Momo einen verständlichen Fehler."""

import logging

from . import KiAnbieter, KiFehler, Nachricht

log = logging.getLogger(__name__)


class AnthropicApi(KiAnbieter):
    name = "anthropic"

    def __init__(self, schluessel: str, modell: str, aufwand: str = "medium", client=None):
        self.schluessel = schluessel
        self.modell = modell
        self.aufwand = aufwand
        self._client = client

    def _verbinden(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.schluessel, timeout=180.0, max_retries=2)
        return self._client

    def fragen(self, anweisung: str, verlauf: list[Nachricht]) -> str:
        import anthropic

        if not self.schluessel:
            raise KiFehler("anmeldung", "ANTHROPIC_API_KEY fehlt")
        nachrichten = [{"role": "user" if n.rolle == "nutzer" else "assistant", "content": n.text}
                       for n in verlauf]
        try:
            antwort = self._verbinden().beta.messages.create(
                model=self.modell, max_tokens=16000, system=anweisung, messages=nachrichten,
                output_config={"effort": self.aufwand},
                betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            )
        except anthropic.AuthenticationError as e:
            raise KiFehler("anmeldung", f"401 {e.message[:200]}") from None
        except anthropic.PermissionDeniedError as e:
            raise KiFehler("anmeldung", f"403 {e.message[:200]}") from None
        except anthropic.RateLimitError as e:
            raise KiFehler("limit", f"429 {e.message[:200]}") from None
        except anthropic.APIStatusError as e:
            art = "voruebergehend" if e.status_code >= 500 else "sonstig"
            raise KiFehler(art, f"{e.status_code} {e.message[:200]}") from None
        except anthropic.APIConnectionError:
            raise KiFehler("voruebergehend", "Anthropic nicht erreichbar") from None
        if antwort.stop_reason == "refusal":
            raise KiFehler("sonstig", "Das Modell hat die Anfrage abgelehnt")
        nutzung = antwort.usage
        log.info("KI anthropic: Modell=%s, Eingabe=%s, Ausgabe=%s Tokens", antwort.model,
                 getattr(nutzung, "input_tokens", None), getattr(nutzung, "output_tokens", None))
        return "".join(b.text for b in antwort.content if b.type == "text").strip()
