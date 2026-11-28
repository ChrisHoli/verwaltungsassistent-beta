"""Datenschutz in einfachen Worten: was Momo beim ersten Kontakt sagt, und „Lösch alles von mir“.

Der Hinweis wird aus der Einstellung gebaut, damit er immer stimmt: welche KI, welcher Speicherort, wer betreibt.
"""

import re

KI_BESCHREIBUNG = {
    "mistral": "an Mistral, eine Firma in Frankreich. Die Daten bleiben in der EU",
    "ollama": "an eine KI, die auf dem Server selbst läuft. Nichts geht nach draußen",
    "befehl": "an ein Programm, das der Betreiber eingerichtet hat",
    "openai-kompatibel": "an einen KI-Dienst, den der Betreiber eingerichtet hat",
    "openai": "an OpenAI, eine Firma in den USA",
    "gemini": "an Google, eine Firma in den USA",
    "anthropic": "an Anthropic, eine Firma in den USA",
    "claude-abo": "an Anthropic, eine Firma in den USA. Das ist nur zum Testen",
    "openrouter": "an OpenRouter, einen Vermittler in den USA",
    "groq": "an Groq, eine Firma in den USA",
}
ABLAGE_BESCHREIBUNG = {
    "rclone": "in einem eigenen Cloud-Ordner, den der Betreiber eingerichtet hat",
    "ordner": "in einem Ordner auf dem Server",
}

LOESCH_WUNSCH = re.compile(
    r"\b(lösch|lösche|loesch|entfern)\w*\b.{0,30}\b(alles|alle (meine )?(daten|briefe)|meine daten)\b", re.I)
LOESCH_JA = re.compile(r"^\s*ja,?\s*(alles\s+)?löschen[\s.!]*$", re.I)
DATENSCHUTZ_FRAGE = re.compile(
    r"\b(datenschutz|was passiert mit meinen (daten|briefen)|wer sieht meine (briefe|daten)|wo sind meine daten)\b",
    re.I)

LOESCH_FRAGE = ("Soll ich wirklich alles löschen? Das sind deine Briefe, Fristen, Antwortbriefe und unser Gespräch. "
                "Das geht nicht rückgängig. Wenn du das willst, antworte auf diese Nachricht mit: Ja, löschen.")
LOESCH_FERTIG = ("Ich habe alles gelöscht: deine Briefe, Fristen, Antwortbriefe, Einstellungen und unseren Chat bei mir. "
                 "Du kannst mir trotzdem weiter schreiben. Wenn du ganz aufhören willst, sag dem Betreiber Bescheid.")


def hinweis(ki: str, ablage: str, betreiber: str, aufheben_tage: int) -> str:
    wer = f"von {betreiber}" if betreiber else "vom Betreiber"
    ki_satz = ("Ich arbeite gerade ohne KI." if ki in ("", "keine") else
               f"Damit ich deinen Brief verstehe, schicke ich den Text {KI_BESCHREIBUNG.get(ki, 'an eine KI')}. "
               "Fotos schicke ich nicht.")
    return "\n".join([
        "Kurz zu deinen Daten:",
        f"Ich laufe auf einem Computer {wer}. Unser Chat ist verschlüsselt.",
        "Fotos und Sprachnachrichten lese ich auf diesem Computer. Zuhören und Vorlesen bleibt hier.",
        ki_satz,
        f"Deine Briefe lege ich {ABLAGE_BESCHREIBUNG.get(ablage, 'beim Betreiber')} ab.",
        "Was du mir über dich sagst, damit ich es mir merke, bleibt auf diesem Computer. Die KI sieht es nur, "
        "wenn ich einen Brief für dich schreibe.",
        f"Unseren Chat lösche ich bei mir nach {aufheben_tage} Tagen. Deine Briefe und Fristen bleiben, bis du sie löschen lässt.",
        "Wenn du willst, dass ich alles lösche, sag: Lösch alles von mir.",
    ])


# Was Momo im Datenordner über die Person weiß (Delta-Chat-Konto und Kopplung bleiben)
PERSONENDATEIEN = ("fakten.json", "mail_entwurf.eml", "vorgaenge.json", "verlauf.json", "einstellungen.json", "letzter_brief.json", "entwurf.json",
                   "absender.json", "app.json")
