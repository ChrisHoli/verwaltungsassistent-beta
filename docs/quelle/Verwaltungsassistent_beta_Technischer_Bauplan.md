# Verwaltungsassistent beta

## Technischer Gesamtbauplan und Implementierungsspezifikation

**Projektstatus:** Konzept / Entwicklungsgrundlage\
**Produktname:** Verwaltungsassistent beta\
**Dokumentversion:** 1.0\
**Ziel:** Umsetzungsfähige Spezifikation für Claude Code oder Codex\
**Primäre Zielgruppe:** Zunächst ein einzelner Nutzer\
**Betriebsmodell:** Cloud-first, EU-Hosting\
**Clients:** Android, iOS und Weboberfläche für Computer\
**Bedienung:** Voice-first, zusätzlich vollständige Tastatureingabe und
barrierefreie Screenreader-Bedienung

------------------------------------------------------------------------

# 1. Produktvision

Der **Verwaltungsassistent beta** ist ein persönlicher, KI-gestützter
Verwaltungsassistent. Er nimmt Schriftstücke unterschiedlichster Art
entgegen, digitalisiert und versteht sie, ordnet sie in einer
nachvollziehbaren Dokumentenstruktur ein und unterstützt den Nutzer bei
allen daraus entstehenden Aufgaben.

Das Produkt ist ausdrücklich mehr als ein Dokumentenscanner oder
Chatbot. Es ist ein persönliches Verwaltungssystem, das Dokumente,
Vorgänge, Fristen, Aufgaben, Rechnungen und Kommunikation miteinander
verbindet.

Der Nutzer kann das System über Smartphone, Computer, Sprache oder
Tastatur bedienen. Die Bedienung muss auch für blinde und stark
sehbehinderte Menschen vollständig nutzbar sein.

## 1.1 Produktversprechen

-   Kein eingehendes Schreiben bleibt unbemerkt.
-   Dokumente werden auffindbar, verständlich und bearbeitbar.
-   Fristen und Handlungsbedarf werden erkannt und nachvollziehbar
    dargestellt.
-   Antworten und Anträge werden vorbereitet.
-   Der Nutzer behält jederzeit die Kontrolle über verbindliche
    Handlungen.

## 1.2 Leitprinzipien

1.  **Voice-first, aber nicht voice-only:** Sprache ist der bevorzugte
    Bedienweg. Jede Kernfunktion ist ebenso per Tastatur und
    barrierefreiem Screenreader erreichbar.
2.  **Ein zentrales Verwaltungsgedächtnis:** Dokumente, Vorgänge,
    Personen, Fristen, Aufgaben und Kommunikation sind miteinander
    verknüpft.
3.  **Kontrollierte Agentenlogik:** Python steuert Abläufe und
    Berechtigungen. Sprachmodelle liefern Interpretationen und
    Formulierungsvorschläge, führen aber keine unkontrollierten Aktionen
    aus.
4.  **Cloud-first:** Daten werden zentral und verschlüsselt in einer
    EU-Cloud verarbeitet und gespeichert.
5.  **Menschliche Freigabe:** Rechtlich oder finanziell relevante
    Aktionen benötigen eine konkrete, nachvollziehbare Freigabe.
6.  **Nachvollziehbarkeit:** Wichtige Aussagen und extrahierte Daten
    müssen auf die ursprüngliche Dokumentstelle zurückgeführt werden
    können.
7.  **Barrierefreiheit als Grundanforderung:** Nicht als spätere
    Zusatzfunktion, sondern als Architektur- und Abnahmekriterium.

------------------------------------------------------------------------

# 2. Zielgruppe und Nutzungsszenarien

## 2.1 Startkonfiguration

-   Zunächst ein einzelner Nutzer.
-   Persönliche Dokumente und Verwaltungsvorgänge.
-   Nutzung über Android, iOS und Webbrowser am Computer.
-   Vollständige Sprachbedienung.
-   Vollständige Tastatureingabe.
-   Unterstützung nativer Screenreader.
-   Cloudbasierter Betrieb mit EU-Datenhaltung.

Die Datenarchitektur soll bereits eine spätere Mehrbenutzerfähigkeit
ermöglichen. Die erste Produktversion muss jedoch keine
Mandantenverwaltung oder Familienkonten anbieten.

## 2.2 Unterstützte Dokumentarten

-   Briefe von Jobcenter, Sozialamt, Finanzamt und Stadtverwaltung
-   Bescheide, Aufforderungen und Erinnerungen
-   Rechnungen und Mahnungen
-   Mietverträge und Nebenkostenabrechnungen
-   Versicherungsunterlagen
-   Bankunterlagen
-   Gesundheits- und Krankenkassenunterlagen
-   Verträge und Kündigungen
-   Anträge und Formulare
-   E-Mails und E-Mail-Anhänge
-   Fotografierte, gescannte und digital erzeugte PDFs
-   Weitere Bild- und Office-Dokumente nach Prüfung der jeweiligen
    Importpipeline

## 2.3 Zentrale Nutzeranfragen

Beispiele:

-   „Lies mir den Brief vor."
-   „Was bedeutet dieses Schreiben?"
-   „Was muss ich jetzt tun?"
-   „Welche Frist steht in dem Brief?"
-   „Was ist diese Woche wichtig?"
-   „Such mir den letzten Bescheid vom Jobcenter."
-   „Welche Rechnungen sind noch offen?"
-   „Erstelle eine Antwort und lies sie mir vor."
-   „Ändere den zweiten Absatz."
-   „Zeig mir am Computer alle offenen Vorgänge."
-   „Ich möchte lieber tippen. Öffne eine neue Nachricht."

------------------------------------------------------------------------

# 3. Produktumfang und Abgrenzung

## 3.1 Funktionen der ersten nutzbaren Version

1.  Dokumente per Smartphone-Foto, Datei-Upload und Weboberfläche
    aufnehmen.
2.  PDFs und Bilder verarbeiten.
3.  OCR und Textextraktion durchführen.
4.  Dokumente klassifizieren und Metadaten extrahieren.
5.  Dokumente Vorgängen zuordnen.
6.  Dokumente über Sprache und Tastatur suchen.
7.  Dokumente vorlesen und verständlich zusammenfassen.
8.  Fristen und mögliche Aufgaben erkennen.
9.  Aufgaben und Erinnerungen verwalten.
10. Antwortentwürfe erstellen und bearbeiten.
11. Entwürfe vorlesen oder am Computer anzeigen.
12. Freigabeprozesse für sensible Aktionen anbieten.

## 3.2 Spätere Erweiterungen

-   E-Mail-Eingang und -Ausgang
-   Formularassistenz und vorausgefüllte Anträge
-   Zahlungsübersicht und Zahlungsdaten
-   Kalenderintegration
-   Versand über geeignete digitale Behördenkanäle
-   Mehrbenutzer- und Familienverwaltung
-   Erweiterte Dokumenten- und Vorgangsautomatisierung

## 3.3 Nicht Bestandteil der ersten Version

-   Automatische Banküberweisungen
-   Unkontrollierter Versand von Schreiben
-   Automatische rechtliche Entscheidungen
-   Verbindliche Steuer- oder Rechtsberatung
-   Vollautomatische Anmeldung und Bearbeitung in Behördenportalen
-   Automatische Einlegung von Rechtsmitteln
-   Automatische Änderung oder Verlängerung behördlicher Fristen

------------------------------------------------------------------------

# 4. Gesamtarchitektur

## 4.1 Architekturentscheidung

Empfohlen wird ein modularer Monolith mit klar getrennten Fachmodulen
und Hintergrundprozessen.

Das ist für einen einzelnen Nutzer und eine erste Produktversion
wirtschaftlicher und einfacher zu betreiben als eine verteilte
Microservice-Architektur. Die Module müssen dennoch so gestaltet werden,
dass sie später unabhängig ausgelagert werden können.

## 4.2 Systemübersicht

``` mermaid
flowchart TD
    A[Flutter App Android / iOS] --> G[API Gateway / FastAPI]
    B[Web App Computer] --> G
    G --> H[Authentication & Authorization]
    G --> O[Agent Orchestrator]
    O --> D[Document Service]
    O --> C[Case Service]
    O --> T[Task & Deadline Service]
    O --> F[Finance Service]
    O --> M[Communication & Draft Service]
    O --> V[Voice Service]
    O --> P[Approval & Policy Engine]
    D --> DB[(PostgreSQL + pgvector)]
    C --> DB
    T --> DB
    F --> DB
    M --> DB
    P --> DB
    D --> S[(Encrypted Object Storage)]
    V --> AI[AI Provider Gateway]
    O --> AI
    D --> Q[Background Queue]
    Q --> W[Document Workers]
    W --> S
    W --> DB
    G --> N[Notifications]
```

## 4.3 Client-Anwendungen

### Mobile App

Technologie: Flutter.

Plattformen: - Android - iOS

Funktionen: - Kamera und Dokumentenscan - Datei- und PDF-Import -
Sprachaufnahme - Sprachausgabe - Tastatureingabe - Dokumentenansicht -
Vorgangs- und Aufgabenansicht - Push-Benachrichtigungen -
Screenreader-Unterstützung

### Weboberfläche für Computer

Die Weboberfläche ist ein vollwertiger Client und kein bloßes
Administrations-Dashboard.

Empfohlene Technologie: React mit TypeScript, beispielsweise Next.js.

Funktionen: - Anmeldung - Dashboard mit offenen Vorgängen und Aufgaben -
Dokumentenarchiv - Dokumentenansicht mit extrahiertem Text -
Vorgangsverwaltung - Fristen- und Aufgabenübersicht - Chat- und
Sprachassistent - Vollständige Tastatureingabe - Entwurfseditor -
Freigabeübersicht - Einstellungen und Datenschutzfunktionen

Die Weboberfläche muss mit Tastatur allein bedienbar sein. Alle
Bedienelemente benötigen sinnvolle Beschriftungen, sichtbare
Fokuszustände und eine logische Tab-Reihenfolge.

### Einheitliches Bedienmodell

Mobile App und Weboberfläche verwenden dieselbe Backend-API und dasselbe
Datenmodell. Nutzer können auf dem Smartphone ein Dokument aufnehmen und
es später am Computer weiterbearbeiten.

Der Bearbeitungszustand wird serverseitig gespeichert. Es darf keine
getrennten, voneinander abweichenden Dokumentenbestände geben.

------------------------------------------------------------------------

# 5. Technologie-Stack

  -----------------------------------------------------------------------
  Bereich                 Technologie             Zweck
  ----------------------- ----------------------- -----------------------
  Mobile App              Flutter / Dart          Android und iOS

  Weboberfläche           React / TypeScript      Computerbedienung

  Backend                 Python / FastAPI        Geschäftslogik und API

  Agentenlogik            Eigene                  Planung und Ausführung
                          Python-Orchestrierung   

  Datenbank               PostgreSQL              Strukturierte Daten

  Vektorsuche             pgvector                Semantische Suche

  Objektspeicher          S3-kompatibler          Originale und erzeugte
                          EU-Speicher             Dateien

  OCR                     PaddleOCR, optional     Texterkennung
                          Tesseract               

  PDF                     PyMuPDF                 PDF-Verarbeitung

  Hintergrundjobs         Redis + Celery          Asynchrone Verarbeitung

  Spracheingabe           Austauschbarer          Sprache zu Text
                          STT-Provider            

  Sprachausgabe           Austauschbarer          Text zu Sprache
                          TTS-Provider            

  KI                      Provider-Abstraktion    Dokumentenverständnis
                                                  und Dialog

  Deployment              Docker                  Reproduzierbarer
                                                  Betrieb

  Reverse Proxy           Caddy oder Nginx        TLS und Routing

  Monitoring              Sentry / OpenTelemetry  Fehler und
                                                  Laufzeitüberwachung
  -----------------------------------------------------------------------

Versionen sind bei Implementierungsbeginn auf aktuell unterstützte,
stabile Releases festzulegen und zu dokumentieren.

## 5.1 AI Provider Gateway

Alle KI-Aufrufe laufen über eine zentrale Abstraktionsschicht.
Fachmodule dürfen keine direkten, verstreuten Anbieteraufrufe enthalten.

Aufgaben: - Dokumentenverständnis - Klassifizierung - strukturierte
Datenextraktion - Zusammenfassung - Antwortentwürfe - Dialogplanung -
optionale Sprachverarbeitung

Anforderungen: - Provider austauschbar - Modell je Aufgabe
konfigurierbar - Kosten- und Tokenprotokollierung - Zeitlimits und
Wiederholungsregeln - Fehlerbehandlung - Datenminimierung - keine
Übermittlung unnötiger Dokumenteninhalte

------------------------------------------------------------------------

# 6. Datenmodell

## 6.1 Grundprinzip

Ein Dokument ist nicht gleich einem Vorgang.

Ein Vorgang bündelt mehrere Dokumente, Aufgaben, Fristen und
Kommunikationsschritte. Dokumente können über Verknüpfungen mehreren
Kontexten zugeordnet werden, ohne mehrfach gespeichert werden zu müssen.

## 6.2 Zentrale Entitäten

  Entität              Zweck
  -------------------- -----------------------------------------
  User                 Nutzerprofil und Einstellungen
  Contact              Behörden, Unternehmen und Personen
  Document             Dokumentstammdaten
  DocumentVersion      Originaldatei und Versionen
  DocumentExtraction   OCR-Text und strukturierte Extraktion
  DocumentPage         Seiteninformationen und Fundstellen
  Case                 Zusammenhängender Verwaltungsvorgang
  CaseDocument         Beziehung zwischen Vorgang und Dokument
  Task                 Konkrete Aufgabe
  Deadline             Frist und Fälligkeit
  Reminder             Erinnerungszeitpunkt und Zustellstatus
  Transaction          Rechnung und Zahlungsverpflichtung
  Draft                Antwort, E-Mail oder Antrag
  Communication        Ein- und ausgehende Kommunikation
  Conversation         Sprach- oder Textdialog
  Approval             Freigabe einer konkreten Aktion
  AuditLog             Nachvollziehbare Systemaktion
  Attachment           Anlagen zu Entwürfen und Kommunikation
  Notification         Benachrichtigungen

## 6.3 Beziehungen

``` mermaid
erDiagram
    USER ||--o{ DOCUMENT : owns
    USER ||--o{ CASE : owns
    USER ||--o{ CONTACT : manages
    USER ||--o{ CONVERSATION : has
    CONTACT ||--o{ DOCUMENT : sends
    CASE ||--o{ CASE_DOCUMENT : contains
    DOCUMENT ||--o{ CASE_DOCUMENT : linked
    DOCUMENT ||--o{ DOCUMENT_VERSION : has
    DOCUMENT ||--o{ DOCUMENT_EXTRACTION : has
    DOCUMENT ||--o{ DOCUMENT_PAGE : contains
    CASE ||--o{ TASK : contains
    TASK ||--o{ DEADLINE : tracks
    TASK ||--o{ REMINDER : triggers
    DOCUMENT ||--o{ TRANSACTION : evidences
    CASE ||--o{ DRAFT : contains
    CASE ||--o{ COMMUNICATION : contains
    DRAFT ||--o{ APPROVAL : requires
    USER ||--o{ AUDIT_LOG : generates
```

## 6.4 Tabellen und Felder

Alle Tabellen erhalten UUID-Primärschlüssel sowie `created_at` und
`updated_at`, soweit fachlich sinnvoll. Personenbezogene Datensätze
werden mit einer `user_id` beziehungsweise einem klaren Eigentümerbezug
versehen.

### users

-   id
-   display_name
-   locale
-   timezone
-   accessibility_settings
-   notification_settings
-   created_at
-   updated_at

### contacts

-   id
-   user_id
-   name
-   category
-   postal_address
-   email
-   phone
-   notes

### documents

-   id
-   user_id
-   title
-   original_filename
-   mime_type
-   file_size
-   checksum_sha256
-   storage_key
-   document_type
-   sender_contact_id
-   document_date
-   received_at
-   reference_number
-   subject
-   processing_status
-   classification_confidence
-   review_required

### document_versions

-   id
-   document_id
-   version_number
-   storage_key
-   checksum_sha256
-   version_type
-   created_at

### document_extractions

-   id
-   document_id
-   extracted_text
-   structured_data_json
-   extraction_provider
-   extraction_model
-   confidence
-   processing_version
-   created_at

### document_pages

-   id
-   document_id
-   page_number
-   extracted_text
-   page_storage_key
-   quality_score

### cases

-   id
-   user_id
-   title
-   category
-   reference_number
-   responsible_contact_id
-   status
-   summary
-   opened_at
-   closed_at

### case_documents

-   case_id
-   document_id
-   relation_type
-   linked_at

### tasks

-   id
-   user_id
-   case_id
-   source_document_id
-   title
-   description
-   priority
-   status
-   due_at
-   completion_source
-   completed_at

### deadlines

-   id
-   task_id
-   source_document_id
-   date_value
-   deadline_type
-   confidence
-   source_excerpt
-   page_number
-   verification_status

### reminders

-   id
-   task_id
-   remind_at
-   channel
-   status
-   delivered_at

### transactions

-   id
-   user_id
-   document_id
-   case_id
-   payee
-   amount
-   currency
-   due_at
-   payment_reference
-   status
-   verification_status

### drafts

-   id
-   user_id
-   case_id
-   source_document_id
-   channel
-   recipient
-   subject
-   content
-   version
-   status
-   created_at

### communications

-   id
-   user_id
-   case_id
-   draft_id
-   direction
-   channel
-   recipient
-   subject
-   content_reference
-   sent_at
-   delivery_status
-   proof_reference

### conversations

-   id
-   user_id
-   channel
-   started_at
-   ended_at
-   summary
-   state_json

### approvals

-   id
-   user_id
-   action_type
-   target_type
-   target_id
-   payload_hash
-   payload_snapshot
-   status
-   created_at
-   expires_at
-   approved_at
-   executed_at

### audit_logs

-   id
-   user_id
-   actor_type
-   action
-   entity_type
-   entity_id
-   result
-   metadata_json
-   created_at

## 6.5 Datenqualität und Quellenbezug

Jede wichtige extrahierte Information soll einen Quellenbezug haben.

Beispiele: - Frist: Dokument-ID, Seite, Textausschnitt - Betrag:
Dokument-ID, Seite, Textausschnitt - Aktenzeichen: Dokument-ID, Seite,
Textausschnitt - Absender: Dokument-ID und erkannte Fundstelle

Unbekannte oder unsichere Werte bleiben `null` beziehungsweise erhalten
einen Prüfstatus. Die KI darf fehlende Daten nicht ergänzen, als wären
sie sicher bekannt.

## 6.6 Statusmodelle

Dokument: - uploaded - queued - processing - extracted - classified -
review_required - processed - archived - failed

Vorgang: - new - in_progress - waiting_for_user -
waiting_for_authority - waiting_for_third_party - ready_for_submission -
completed - archived

Aufgabe: - open - in_progress - waiting - completed - cancelled

Freigabe: - pending - approved - rejected - expired - revoked -
executed - failed

------------------------------------------------------------------------

# 7. Dokumentenverarbeitung

## 7.1 Eingangskanäle

-   Smartphone-Kamera
-   Smartphone-Dateiauswahl
-   Web-Upload
-   Drag-and-drop in der Weboberfläche
-   Später: E-Mail-Import

## 7.2 Verarbeitungspipeline

1.  Upload authentifizieren und autorisieren.
2.  Dateityp und Dateigröße prüfen.
3.  Malware- und Sicherheitsprüfung durchführen.
4.  Originaldatei verschlüsselt speichern.
5.  SHA-256-Prüfsumme bilden.
6.  Verarbeitung in Hintergrundwarteschlange stellen.
7.  PDF-Seiten beziehungsweise Bildseiten extrahieren.
8.  Bildqualität und Vollständigkeit prüfen.
9.  OCR durchführen.
10. Text und Seitenstruktur speichern.
11. Dokumenttyp und Absender ermitteln.
12. Metadaten strukturiert extrahieren.
13. Fristen, Beträge und Handlungsbedarf als Kandidaten erkennen.
14. Bestehenden Vorgang suchen.
15. Vorgang zuordnen oder neuen Vorgang vorschlagen.
16. Unsicherheiten und Prüfbedarf kennzeichnen.
17. Nutzer über Ergebnis informieren.

## 7.3 Dokumentenklassifizierung

Mögliche Kategorien: - authority_letter - official_notice - invoice -
reminder - contract - insurance - bank_document - medical_document -
application - certificate - email - other

Die Klassifizierung muss erweiterbar sein.

## 7.4 Fristenerkennung

Jede erkannte Frist benötigt: - Datum - Fristtyp - Beschreibung -
Fundstelle - Konfidenz - Prüfstatus

Unterscheidung: - ausdrücklich genanntes Datum - aus einer Formulierung
abgeleiteter Termin - vom System vorgeschlagene Wiedervorlage

Nur ausdrücklich nachvollziehbare und hinreichend geprüfte Angaben
dürfen als bestätigte Dokumentfristen dargestellt werden. Rechtliche
Fristberechnungen benötigen gesonderte, fachlich geprüfte Regeln.

## 7.5 Beispiel eines Extraktionsobjekts

``` json
{
  "document_type": "authority_letter",
  "sender": {
    "name": "Jobcenter Beispielstadt",
    "category": "authority"
  },
  "document_date": "2026-11-20",
  "reference_number": "BEISPIEL-123",
  "subject": "Aufforderung zur Mitwirkung",
  "deadlines": [
    {
      "date": "2026-12-10",
      "description": "Mietbescheinigung einreichen",
      "source_page": 2,
      "source_excerpt": "Bitte reichen Sie ... bis zum 10.12.2026 ein.",
      "confidence": 0.98,
      "verification_status": "review_required"
    }
  ],
  "required_actions": [
    {
      "type": "submit_document",
      "description": "Mietbescheinigung einreichen",
      "source_page": 2
    }
  ],
  "processing_status": "review_required"
}
```

Die Beispielwerte sind keine echten Nutzerdaten.

------------------------------------------------------------------------

# 8. Agentenarchitektur

## 8.1 Grundsatz

Der zentrale Orchestrator plant und koordiniert. Spezialisierte Module
übernehmen klar begrenzte Aufgaben. Die Agenten erhalten keine direkten,
unkontrollierten Datenbank- oder Versandberechtigungen.

Für die erste Version werden Agenten als Python-Module und kontrollierte
Workflows implementiert. Eigenständige, dauerhaft laufende
KI-Agenteninstanzen sind nicht erforderlich.

## 8.2 Administration Orchestrator

Verantwortlich für: - Eingabe verstehen - Nutzer- und Vorgangskontext
laden - Absicht bestimmen - Ablauf planen - benötigte Tools auswählen -
Berechtigungen prüfen lassen - Ergebnisse zusammenführen - Freigaben
anfordern - Antwort an Nutzer ausgeben

Beispiel:

``` python
class AdministrationOrchestrator:
    async def handle_request(self, user_id: str, request: str):
        context = await self.context_service.load(user_id)
        intent = await self.intent_service.detect(request, context)
        plan = await self.planner.create_plan(intent, context)
        result = await self.executor.execute(
            user_id=user_id,
            plan=plan
        )
        return await self.response_service.prepare(result)
```

## 8.3 Spezialisierte Module

### Document Agent

-   OCR-Ergebnisse auswerten
-   Dokumenttyp bestimmen
-   Metadaten extrahieren
-   Unsicherheiten markieren

### Archive Agent

-   Dokumente ablegen
-   Dokumente suchen
-   Dubletten erkennen
-   Beziehungen vorschlagen

### Case Agent

-   Vorgänge anlegen
-   Dokumente verknüpfen
-   Vorgangsstatus verwalten
-   Verlauf zusammenfassen

### Deadline Agent

-   Fristenkandidaten prüfen
-   Aufgaben erstellen
-   Erinnerungen planen
-   Überfälligkeiten melden

### Finance Agent

-   Rechnungsdaten extrahieren
-   Fälligkeiten verwalten
-   offene Verpflichtungen anzeigen
-   Zahlungsinformationen aufbereiten

Keine Überweisungen in der ersten Version.

### Communication Agent

-   Antwortentwürfe erstellen
-   E-Mails und Briefe formulieren
-   Anträge vorbereiten
-   Änderungen nach Diktat oder Tastatureingabe vornehmen

### Voice Agent

-   Sprache transkribieren
-   Dialogzustand verwalten
-   Antworten vorlesen
-   Unterbrechungen und Rückfragen unterstützen

### Compliance Agent

-   Quellen prüfen
-   Datenwidersprüche erkennen
-   Berechtigungen kontrollieren
-   Freigabepflicht feststellen
-   unsichere Aktionen blockieren

## 8.4 Agenten-Tool-Verträge

Jedes Tool erhält: - einen eindeutigen Namen - eine dokumentierte
Eingabestruktur - eine dokumentierte Ausgabestruktur - erforderliche
Berechtigungen - mögliche Fehlerzustände - Protokollierungsregeln

Beispiel:

``` python
async def search_documents(
    user_id: str,
    query: str,
    document_type: str | None = None,
    case_id: str | None = None
) -> list[DocumentSearchResult]:
    ...
```

Der `user_id` wird serverseitig aus der authentifizierten Sitzung
abgeleitet und darf nicht ungeprüft aus einer Modellantwort übernommen
werden.

------------------------------------------------------------------------

# 9. Voice-first und Tastaturbedienung

## 9.1 Einheitlicher Assistent

Der Nutzer kann denselben Assistenten über drei Wege bedienen:

1.  Sprache
2.  Tastatur
3.  Screenreader und assistive Technologien

Alle Eingaben führen in dieselbe Dialog- und Orchestrierungsschicht. Es
gibt keine getrennten Wissensbestände oder Funktionswelten.

## 9.2 Sprachfunktionen

-   Push-to-talk
-   Sprache zu Text
-   Text zu Sprache
-   Unterbrechung der Sprachausgabe
-   Wiederholung
-   Langsames Vorlesen
-   Zusammenfassungen
-   Buchstabieren von Aktenzeichen
-   Bestätigung wichtiger Daten
-   Dialogfortsetzung

Eine dauerhaft offene Mikrofonüberwachung ist in der ersten Version
nicht vorgesehen.

## 9.3 Tastatureingabe

Die Tastaturbedienung muss auf Smartphone und Computer funktionieren.

Anforderungen: - Textfeld für freie Anfragen - Senden per Enter,
Zeilenumbruch per Shift+Enter - sichtbarer Fokus - vollständige
Tab-Navigation - verständliche Fehlermeldungen - Eingabehistorie -
Bearbeitung und Korrektur von Nachrichten - Möglichkeit, Antworten zu
kopieren - Dokumente per Tastatur auswählen und hochladen - Entwürfe
vollständig im Editor bearbeiten - Sprach- und Tastatureingabe innerhalb
derselben Unterhaltung kombinieren

## 9.4 Dialogzustände

Beispielhafte Zustände: - idle - listening - transcribing - thinking -
reading_response - awaiting_user_input - awaiting_approval -
processing_document - error

Die Oberfläche muss den aktuellen Zustand sowohl visuell als auch
akustisch und für Screenreader erkennbar kommunizieren.

## 9.5 Barrierefreiheit

Verbindliche Anforderungen: - WCAG 2.2 AA als Zielstandard für die
Weboberfläche - semantische HTML-Struktur - Screenreader-kompatible
Beschriftungen - sinnvolle Überschriftenhierarchie -
Tastaturbedienbarkeit aller Kernfunktionen - sichtbare
Fokusindikatoren - keine ausschließlich farbliche Statuskommunikation -
skalierbare Schrift - ausreichende Kontraste - verständliche
Statusmeldungen - keine zeitkritischen Interaktionen ohne
Verlängerungsmöglichkeit - VoiceOver- und TalkBack-Tests

Die App darf nicht voraussetzen, dass Nutzer Dokumente visuell lesen
oder visuelle Symbole interpretieren können.

------------------------------------------------------------------------

# 10. Weboberfläche für Computer

## 10.1 Technische Umsetzung

Empfohlen: - React - TypeScript - Next.js - barrierefreie Komponenten -
zentrale API-Anbindung - responsive Layouts

## 10.2 Hauptbereiche

### Dashboard

-   Begrüßung
-   offene Aufgaben
-   nächste Fristen
-   neue Dokumente
-   zuletzt bearbeitete Vorgänge
-   zentrale Assistenteneingabe

### Dokumente

-   Dokumentenliste
-   Filter
-   Volltextsuche
-   Dokumentdetails
-   Originaldatei
-   erkannter Text
-   Metadaten
-   Fundstellen
-   Verknüpfte Vorgänge

### Vorgänge

-   Vorgangsliste
-   Status
-   Dokumente
-   Aufgaben
-   Fristen
-   Kommunikation
-   Zusammenfassung

### Aufgaben

-   offene Aufgaben
-   erledigte Aufgaben
-   Prioritäten
-   Fälligkeiten
-   Erinnerungen

### Assistent

-   Chatverlauf
-   Texteingabe
-   optionales Mikrofon
-   Sprachausgabe
-   Quellenverweise
-   Aktionsvorschläge

### Entwürfe

-   Texteditor
-   Empfänger
-   Betreff
-   Anlagen
-   Versionen
-   Vorlesen
-   Freigabe

### Einstellungen

-   Sprache
-   Stimme
-   Sprechgeschwindigkeit
-   Tastaturverhalten
-   Screenreader-Einstellungen
-   Benachrichtigungen
-   Datenschutz
-   Datenexport und Löschung

## 10.3 Synchronisation

Alle Änderungen werden serverseitig gespeichert. Die Weboberfläche und
die mobilen Apps greifen auf denselben Datenbestand zu.

Für längere Bearbeitungsvorgänge sind Entwurfsversionen und
Konflikterkennung vorzusehen. Ein älterer Client darf keine neuere
Version unbemerkt überschreiben.

------------------------------------------------------------------------

# 11. API-Struktur

Alle Endpunkte werden unter `/api/v1/` versioniert.

## 11.1 Authentifizierung

-   `POST /auth/login`
-   `POST /auth/refresh`
-   `POST /auth/logout`
-   `GET /users/me`
-   `PATCH /users/me`

Authentifizierung über sichere, kurzlebige Zugriffstoken und geeignete
Erneuerungsmechanismen. Passkeys beziehungsweise starke
Mehr-Faktor-Authentifizierung sind zu bevorzugen.

## 11.2 Dokumente

-   `POST /documents/upload`
-   `GET /documents`
-   `GET /documents/{id}`
-   `GET /documents/{id}/content`
-   `GET /documents/{id}/extraction`
-   `POST /documents/{id}/reprocess`
-   `POST /documents/{id}/read`

## 11.3 Vorgänge

-   `POST /cases`
-   `GET /cases`
-   `GET /cases/{id}`
-   `PATCH /cases/{id}`
-   `POST /cases/{id}/documents`
-   `GET /cases/{id}/timeline`

## 11.4 Aufgaben und Fristen

-   `POST /tasks`
-   `GET /tasks`
-   `PATCH /tasks/{id}`
-   `POST /tasks/{id}/complete`
-   `GET /deadlines`
-   `POST /reminders`

## 11.5 Kommunikation und Entwürfe

-   `POST /drafts`
-   `GET /drafts`
-   `GET /drafts/{id}`
-   `PATCH /drafts/{id}`
-   `POST /drafts/{id}/revise`
-   `POST /communications/send`

Der Versandendpunkt ist durch die Policy Engine geschützt und darf nicht
direkt durch ein Sprachmodell aufgerufen werden.

## 11.6 Freigaben

-   `GET /approvals`
-   `GET /approvals/{id}`
-   `POST /approvals/{id}/confirm`
-   `POST /approvals/{id}/reject`
-   `POST /approvals/{id}/revoke`

## 11.7 Assistent

-   `POST /assistant/message`
-   `GET /assistant/conversations`
-   `GET /assistant/conversations/{id}`
-   `POST /assistant/conversations/{id}/continue`

## 11.8 Sprache

-   `POST /voice/transcribe`
-   `POST /voice/synthesize`
-   `POST /voice/sessions`
-   `DELETE /voice/sessions/{id}`

WebSocket kann für laufende Sprachsitzungen und Statusmeldungen
verwendet werden.

## 11.9 Beispiel einer Assistentenanfrage

``` json
{
  "message": "Welche Briefe vom Jobcenter sind noch offen?",
  "input_mode": "keyboard",
  "conversation_id": "uuid"
}
```

Mögliche Antwort:

``` json
{
  "response": "Es gibt zwei offene Vorgänge.",
  "conversation_id": "uuid",
  "actions": [
    {
      "type": "open_case",
      "case_id": "uuid"
    }
  ],
  "sources": [],
  "requires_approval": false
}
```

Die API liefert strukturierte Daten. Die Clients entscheiden, ob die
Antwort als Text angezeigt, vorgelesen oder beides wird.

------------------------------------------------------------------------

# 12. Freigabe- und Handlungssystem

## 12.1 Handlungsklassen

  -----------------------------------------------------------------------
  Klasse                  Beispiele               Regel
  ----------------------- ----------------------- -----------------------
  A                       Dokument sortieren,     Automatisch
                          Text zusammenfassen     

  B                       Fristkandidat erkennen, Automatisch mit
                          Aufgabe vorschlagen     Prüfstatus

  C                       Antwortbrief erstellen  Entwurf, Nutzerprüfung
                          und ändern              

  D                       E-Mail versenden,       Einzel-Freigabe
                          Antrag übermitteln,     
                          Zahlung auslösen        
  -----------------------------------------------------------------------

## 12.2 Freigabeprozess

``` mermaid
stateDiagram-v2
    [*] --> Prepared
    Prepared --> Validating
    Validating --> Rejected: Fehler
    Validating --> AwaitingApproval: Prüfung erfolgreich
    AwaitingApproval --> Approved: Nutzer bestätigt
    AwaitingApproval --> Cancelled: Nutzer lehnt ab
    Approved --> Executing
    Executing --> Completed: Erfolg bestätigt
    Executing --> Failed: Fehler
    Completed --> [*]
```

## 12.3 Freigabe muss konkret gebunden sein

Eine Freigabe bezieht sich immer auf: - Aktion - Empfänger -
vollständigen Inhalt - Anlagen - Versandweg - Zeitpunkt -
Nutzungsfrist - unveränderlichen Hash des freigegebenen Inhalts

Wird der Inhalt nach der Freigabe verändert, muss eine neue Freigabe
eingeholt werden.

Eine allgemeine Zustimmung wie „Ja" darf nicht versehentlich eine andere
Aktion bestätigen. Der Assistent muss die konkrete Handlung vorher
verständlich zusammenfassen.

## 12.4 Versandstatus

Unterscheiden: - Entwurf erstellt - Freigabe ausstehend - Freigegeben -
Versand angefordert - Versand durch Dienst bestätigt - Zustellung
bestätigt, sofern technisch verfügbar - Versand fehlgeschlagen

Eine vom Nutzer mündlich mitgeteilte Absendung ist kein technischer
Versandnachweis.

------------------------------------------------------------------------

# 13. Sicherheits- und Datenschutzkonzept

## 13.1 Technische Sicherheit

-   TLS für alle Verbindungen
-   Verschlüsselung ruhender Daten
-   sichere Schlüsselverwaltung
-   getrennte Zugriffsrechte
-   sichere Authentifizierung
-   Rate Limits
-   Upload-Validierung
-   Malware-Prüfung
-   sichere Backups
-   Audit-Protokollierung
-   regelmäßige Sicherheitsupdates
-   Schutz vor unberechtigtem Zugriff
-   dokumentierte Wiederherstellungstests

## 13.2 Prompt-Injection-Schutz

Dokumente sind nicht vertrauenswürdige Datenquellen.

Anweisungen in einem Dokument dürfen niemals als Systemanweisung
interpretiert werden.

Daher: - Dokumententext klar als nicht vertrauenswürdigen Inhalt
markieren. - Keine direkten Toolaufrufe aus Dokumentenanweisungen. -
Externe URLs nicht automatisch aufrufen. - Empfänger nicht ungeprüft aus
Dokumenten übernehmen. - Datenbankzugriffe ausschließlich über geprüfte
Services. - Tool-Berechtigungen serverseitig kontrollieren. -
Modellantworten vor Aktionen validieren.

## 13.3 KI-Datenminimierung

Ein zentraler AI Gateway entscheidet: - welche Daten ein Modell erhalten
darf - welche Dokumentenausschnitte erforderlich sind - welches Modell
für die Aufgabe eingesetzt wird - ob personenbezogene Daten minimiert
werden können - ob ein externer Dienst überhaupt zulässig ist

Keine Verwendung der Nutzerdokumente zum Modelltraining durch Anbieter.
Dies muss anhand der konkreten Vertrags- und Produkteinstellungen
geprüft werden.

## 13.4 Datenschutzrecht

Vor Produktivbetrieb sind insbesondere zu prüfen: -
DSGVO-Rechtsgrundlagen - Auftragsverarbeitungsverträge -
Drittlandübermittlungen - Lösch- und Aufbewahrungskonzept -
Datenexport - Datenschutz-Folgenabschätzung - technische und
organisatorische Maßnahmen - Anforderungen des EU AI Act -
Informationspflichten und Transparenz

Diese Spezifikation ersetzt keine rechtliche Prüfung.

------------------------------------------------------------------------

# 14. Benachrichtigungen und Erinnerungen

Der Reminder-Service verwaltet: - Fristerinnerungen -
Zahlungsfälligkeiten - offene Aufgaben - Wiedervorlagen - Rückfragen -
ausstehende Freigaben

Kanäle: - Push-Nachricht - In-App-Mitteilung - Sprachausgabe bei aktiver
Sitzung - später E-Mail

Erinnerungen müssen: - wiederholbar sein - als erledigt markiert werden
können - verschoben werden können - akustisch verständlich sein - einen
Bezug zum betreffenden Vorgang enthalten

Der Nutzer kann seine bevorzugten Zeiten und Häufigkeiten einstellen.

------------------------------------------------------------------------

# 15. Projekt- und Repository-Struktur

``` text
verwaltungsassistent-beta/
│
├── apps/
│   ├── mobile/
│   │   ├── lib/
│   │   │   ├── core/
│   │   │   │   ├── api/
│   │   │   │   ├── audio/
│   │   │   │   ├── accessibility/
│   │   │   │   └── auth/
│   │   │   ├── features/
│   │   │   │   ├── assistant/
│   │   │   │   ├── documents/
│   │   │   │   ├── cases/
│   │   │   │   ├── tasks/
│   │   │   │   ├── scanner/
│   │   │   │   └── settings/
│   │   │   └── main.dart
│   │   └── test/
│   │
│   └── web/
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   ├── features/
│       │   ├── hooks/
│       │   ├── services/
│       │   └── accessibility/
│       └── tests/
│
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── agents/
│   │   ├── services/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── workflows/
│   │   ├── tools/
│   │   ├── policies/
│   │   └── main.py
│   ├── migrations/
│   └── tests/
│
├── infrastructure/
│   ├── docker/
│   ├── reverse-proxy/
│   ├── monitoring/
│   ├── backups/
│   └── deployment/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── API.md
│   ├── AGENTS.md
│   ├── SECURITY.md
│   ├── ACCESSIBILITY.md
│   ├── WORKFLOWS.md
│   ├── DEVELOPMENT_ROADMAP.md
│   └── ACCEPTANCE_TESTS.md
│
├── scripts/
├── docker-compose.yml
├── .env.example
├── README.md
└── CHANGELOG.md
```

------------------------------------------------------------------------

# 16. Entwicklungsphasen

Die Zeitangaben sind grobe Planungswerte für eine konzentrierte
Entwicklung. Sie sind keine Liefergarantie.

## Phase 0: Projektfundament

Geschätzt: 3--5 Tage

-   Repository einrichten
-   Docker-Umgebung
-   FastAPI-Grundgerüst
-   PostgreSQL
-   Migrationen
-   Authentifizierung
-   Cloud-Speicher
-   CI/CD
-   Teststruktur

**Abnahme:** Backend startet reproduzierbar und ein authentifizierter
Nutzer kann eine geschützte API verwenden.

## Phase 1: Dokumentenerfassung

Geschätzt: 1--2 Wochen

-   Upload
-   Kamera- und Dateiimport
-   PDF-Verarbeitung
-   OCR
-   Hintergrundjobs
-   Klassifizierung
-   Extraktion
-   Statusmeldungen

**Abnahme:** Ein Foto oder PDF wird sicher gespeichert und strukturiert
verarbeitet.

## Phase 2: Dokumentengedächtnis

Geschätzt: 1--2 Wochen

-   Datenmodell
-   Archiv
-   Vorgänge
-   Dokumentenverknüpfungen
-   Volltextsuche
-   semantische Suche
-   Quellenverweise

**Abnahme:** Dokumente können zuverlässig gefunden und Vorgängen
zugeordnet werden.

## Phase 3: Agentenlogik

Geschätzt: 1--2 Wochen

-   Orchestrator
-   Document Agent
-   Archive Agent
-   Case Agent
-   Tool-Verträge
-   AI Provider Gateway
-   Fehler- und Unsicherheitsbehandlung

**Abnahme:** Sprach- oder Textanfragen lösen kontrollierte,
nachvollziehbare Workflows aus.

## Phase 4: Mobile App und Weboberfläche

Geschätzt: 2--3 Wochen

-   Flutter-App
-   React-Weboberfläche
-   Anmeldung
-   Dokumentenaufnahme
-   Dokumentenarchiv
-   Vorgänge
-   Dashboard
-   Tastatureingabe
-   responsive Bedienung
-   Screenreader-Unterstützung

**Abnahme:** Die Kernfunktionen sind auf Android, iOS und am Computer
verfügbar.

## Phase 5: Voice Assistant

Geschätzt: 1--2 Wochen

-   Speech-to-Text
-   Text-to-Speech
-   Dialogzustände
-   Unterbrechungen
-   Vorlesen
-   Sprachsteuerung
-   Kombination von Sprache und Tastatur

**Abnahme:** Alle Kernfunktionen sind sprachlich erreichbar.

## Phase 6: Aufgaben und Fristen

Geschätzt: 1--2 Wochen

-   Fristenerkennung
-   Aufgaben
-   Erinnerungen
-   Wiedervorlagen
-   offene Angelegenheiten
-   Statusübersicht

**Abnahme:** Erkannter Handlungsbedarf wird nachvollziehbar in Aufgaben
überführt.

## Phase 7: Schreibassistent und Freigaben

Geschätzt: 1--2 Wochen

-   Antwortentwürfe
-   E-Mail-Entwürfe
-   Dokumentenerstellung
-   Diktierte Korrekturen
-   Tastaturkorrekturen
-   Versionierung
-   Freigabeprozess
-   Aktionsprotokoll

**Abnahme:** Ein Antwortschreiben kann erstellt, bearbeitet, vorgelesen
und sicher zur Freigabe vorgelegt werden.

## Phase 8: Integration und Produktivhärtung

Geschätzt: 2--3 Wochen

-   E-Mail-Integration
-   Benachrichtigungen
-   Sicherheitsprüfungen
-   Datenschutzprüfung
-   Barrierefreiheitstests
-   Last- und Fehlertests
-   Backup-Wiederherstellung
-   Praxistests mit blinden Nutzern

**Abnahme:** Ein belastbarer erster Produktivbetrieb ist möglich.

Gesamtschätzung: etwa 11--17 Wochen bei konzentrierter Entwicklung.
Parallelisierung, Teamgröße und externe Abhängigkeiten können die Dauer
verändern.

------------------------------------------------------------------------

# 17. Qualitäts- und Abnahmekriterien

  -----------------------------------------------------------------------
  Bereich                             Ziel
  ----------------------------------- -----------------------------------
  Dokumentenaufnahme                  Gängige Foto- und PDF-Formate

  OCR                                 Zielwert mindestens 98 % bei gut
                                      lesbaren Testdokumenten, gemessen
                                      auf Zeichenebene

  Klassifizierung                     Zielwert mindestens 95 % auf
                                      definierter Testmenge

  Fristenerkennung                    Jede Frist mit Fundstelle und
                                      Prüfstatus

  Suche                               Zielwert mindestens 95 %
                                      Trefferquote auf definierten
                                      Testanfragen

  Voice                               Alle Kernfunktionen ohne visuelle
                                      Bedienung erreichbar

  Tastatur                            Alle Web-Kernfunktionen ohne Maus
                                      erreichbar

  Screenreader                        Tests mit VoiceOver und TalkBack

  Freigabe                            Keine sensible externe Aktion ohne
                                      gültige Einzel-Freigabe

  Datenschutz                         Verschlüsselte Speicherung und
                                      Übertragung

  Betrieb                             Erfolgreicher
                                      Backup-Wiederherstellungstest
  -----------------------------------------------------------------------

Die Prozentwerte sind Entwicklungsziele und müssen anhand einer
repräsentativen Testmenge gemessen werden.

## 17.1 Pflicht-Testfälle

-   Schlecht fotografierte Schreiben
-   Mehrseitige Briefe
-   Fehlende Seiten
-   Doppelte Seiten
-   Handschriftliche Ergänzungen
-   Tabellen und Beträge
-   Mehrdeutige Datumsangaben
-   Mehrere ähnliche Aktenzeichen
-   Widersprüchliche Dokumente
-   Manipulative Anweisungen in Dokumenten
-   Abgebrochene Uploads
-   Netzwerkunterbrechungen
-   Veraltete App-Sitzungen
-   Gleichzeitige Bearbeitung auf Web und Smartphone
-   Freigabe eines anschließend veränderten Entwurfs
-   Screenreader-Navigation
-   vollständige Tastaturnavigation

------------------------------------------------------------------------

# 18. Kostenplanung

Grobe monatliche Betriebsschätzung für einen einzelnen Nutzer:

  Kostenposition                       Planungswert
  --------------------------------- ---------------
  Cloud-Server                             15--30 €
  Datenbank, Speicher, Backups              5--15 €
  KI-API                                   10--40 €
  Spracheingabe und Sprachausgabe           5--20 €
  Monitoring und sonstige Dienste           0--10 €
  **Gesamt**                          **35--115 €**

Die Werte sind unverbindliche Planungsgrößen. Sie hängen von
Dokumentenvolumen, Audioverbrauch, Modellwahl, Speicherbedarf und
Anbieter ab.

Eine GPU ist für den ersten Betrieb nicht zwingend notwendig. OCR und
Backend können auf einer CPU-Instanz laufen. Die
Sprachmodellverarbeitung erfolgt zunächst über externe APIs.

------------------------------------------------------------------------

# 19. Verbindliche Entwicklungsregeln für Claude Code oder Codex

Diese Regeln gelten für alle Implementierungsphasen:

1.  Vor jeder größeren Änderung die vorhandene Architektur und
    Dokumentation lesen.
2.  Keine Architekturentscheidungen stillschweigend verändern.
3.  Änderungen an Datenmodell und API dokumentieren.
4.  Datenbankmigrationen versionieren.
5.  Keine direkten Datenbankzugriffe aus Agentenprompts.
6.  Alle Agentenwerkzeuge mit Eingabe- und Ausgabeschemas versehen.
7.  Benutzeridentität ausschließlich serverseitig aus der Sitzung
    ableiten.
8.  Alle sensiblen Aktionen durch die Policy Engine prüfen.
9.  KI-generierte Informationen mit Quellen und Unsicherheiten versehen.
10. Keine unbelegten Fristen, Beträge, Empfänger oder Aktenzeichen
    erfinden.
11. Dokumenteninhalte grundsätzlich als nicht vertrauenswürdige Daten
    behandeln.
12. Tests für neue Funktionen verpflichtend ergänzen.
13. Fehlerzustände und Wiederholungen explizit behandeln.
14. Keine Secrets in das Repository einchecken.
15. `.env.example` pflegen.
16. Barrierefreiheit bei jeder Oberfläche mitprüfen.
17. Tastaturbedienung auf der Weboberfläche verbindlich testen.
18. Vor jeder Phase eine funktionierende, getestete Version sichern.
19. Keine externen Handlungen ohne die definierte Freigabe.
20. Nach jedem Sprint eine kurze technische Dokumentation und einen
    Änderungsbericht erstellen.

## 19.1 Arbeitsweise des Coding-Agenten

Der Coding-Agent soll in kleinen, überprüfbaren Arbeitspaketen arbeiten:

1.  Anforderungen lesen.
2.  Betroffene Module identifizieren.
3.  Implementierungsplan formulieren.
4.  Änderungen umsetzen.
5.  Tests ausführen.
6.  Fehler beheben.
7.  Dokumentation aktualisieren.
8.  Ergebnis und offene Punkte berichten.

Der Coding-Agent darf nicht eigenständig den Umfang einer Freigabe- oder
Sicherheitsregel reduzieren.

------------------------------------------------------------------------

# 20. Erste konkrete Arbeitspakete

Die Implementierung beginnt mit diesen Aufgaben in genau dieser
Reihenfolge:

### Arbeitspaket 1: Repository und Infrastruktur

-   Projektverzeichnis erstellen
-   Git einrichten
-   Docker Compose erstellen
-   FastAPI starten
-   PostgreSQL verbinden
-   Health-Check implementieren
-   Konfiguration über Umgebungsvariablen

### Arbeitspaket 2: Nutzer und Sicherheit

-   User-Modell
-   Authentifizierung
-   geschützte API
-   Berechtigungsprüfung
-   Audit-Log-Grundlage

### Arbeitspaket 3: Dokumentenmodell und Speicher

-   Dokumententabellen
-   Versionierung
-   S3-Speicher
-   Upload-Endpunkt
-   Prüfsummen
-   sichere Dateizugriffe

### Arbeitspaket 4: OCR und Verarbeitung

-   Hintergrundwarteschlange
-   PDF- und Bildverarbeitung
-   OCR
-   Extraktionsschema
-   Dokumentenstatus
-   Fehlerbehandlung

### Arbeitspaket 5: Agentenbasis

-   AI Provider Gateway
-   Orchestrator
-   Document Agent
-   Archive Agent
-   Tool-Verträge
-   Quellenverweise

### Arbeitspaket 6: Clients

-   Flutter-Grundgerüst
-   React-Web-Grundgerüst
-   Anmeldung
-   Upload
-   Dokumentenliste
-   Tastatureingabe
-   Barrierefreiheitsbasis

------------------------------------------------------------------------

# 21. Definition of Done für die erste Beta

Der erste Beta-Stand gilt als erreicht, wenn folgende Kette zuverlässig
funktioniert:

1.  Nutzer meldet sich auf Smartphone oder Computer an.
2.  Nutzer fotografiert ein Schreiben oder lädt eine Datei hoch.
3.  Das Original wird sicher gespeichert.
4.  OCR extrahiert den Inhalt.
5.  Die KI erkennt Dokumenttyp, Absender und wesentliche Angaben.
6.  Das Dokument wird einem Vorgang zugeordnet oder ein neuer Vorgang
    wird vorgeschlagen.
7.  Der Nutzer kann den Inhalt per Sprache oder Tastatur abfragen.
8.  Der Assistent liest den Inhalt vor und erklärt ihn.
9.  Der Assistent erkennt mögliche Aufgaben und Fristen mit
    Quellenbezug.
10. Der Nutzer kann eine Aufgabe bestätigen.
11. Der Assistent kann einen Antwortentwurf erstellen.
12. Der Nutzer kann den Entwurf per Sprache oder Tastatur ändern.
13. Der Entwurf kann vorgelesen und zur Freigabe vorgelegt werden.
14. Die App und Weboberfläche zeigen denselben Bearbeitungsstand.
15. Alle sensiblen Aktionen sind nachvollziehbar und geschützt.

------------------------------------------------------------------------

# 22. Produkt-Roadmap nach der Beta

Nach erfolgreicher Beta können folgende Erweiterungen priorisiert
werden:

**Ausbaustufe A: Kommunikation** - E-Mail-Postfach anbinden - Anhänge
automatisch importieren - Antwortentwürfe im E-Mail-Kontext -
Versandnachweise archivieren

**Ausbaustufe B: Formulare** - Formulare erkennen - fehlende Angaben
erfragen - vorhandene Angaben wiederverwenden - Formulare vorausfüllen -
Anlagen zusammenstellen

**Ausbaustufe C: Finanzverwaltung** - wiederkehrende Rechnungen
erkennen - Zahlungsübersicht - Mahnungen priorisieren -
Zahlungsvorbereitung - später kontrollierte Bankintegration nach
gesonderter Sicherheitsprüfung

**Ausbaustufe D: Erweiterte Verwaltungsassistenz** - langfristige
Vorgangshistorie - automatische Wiedervorlagen - proaktive Hinweise -
Zusammenfassungen offener Angelegenheiten - zusätzliche Behörden- und
Dienstschnittstellen

**Ausbaustufe E: Mehrbenutzerprodukt** - weitere Nutzerkonten -
getrennte Datenräume - Rollen und Berechtigungen - Familien- oder
Betreuungskonstellationen nur mit klaren Einwilligungs- und
Vertretungsregeln

------------------------------------------------------------------------

# 23. Abschließende Architekturentscheidung

Der **Verwaltungsassistent beta** wird als cloudbasierte, modulare und
barrierefreie Verwaltungsplattform entwickelt.

Die primären Bedienwege sind:

-   Smartphone mit Sprache und Kamera
-   Smartphone mit Tastatureingabe
-   Weboberfläche am Computer mit Tastatur
-   Screenreader auf allen geeigneten Plattformen

Die technische Grundlage bilden Flutter, React, Python/FastAPI,
PostgreSQL, pgvector, verschlüsselter Objektspeicher und eine eigene
Agenten-Orchestrierung.

Das System soll Dokumente nicht nur speichern, sondern sie in einen
nachvollziehbaren Verwaltungszusammenhang bringen. Es soll verstehen,
was zu tun ist, Aufgaben vorbereiten und Kommunikation formulieren. Die
Entscheidung und Freigabe verbindlicher Handlungen bleiben beim Nutzer.

**Das Ziel der Beta ist ein zuverlässiger persönlicher
Verwaltungsassistent, der Menschen hilft, ihren Schriftverkehr
selbstständig, verständlich und barrierefrei zu bewältigen.**
