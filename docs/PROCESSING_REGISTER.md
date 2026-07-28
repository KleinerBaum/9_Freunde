# Verzeichnis der Verarbeitungstätigkeiten – Arbeitsfassung

Diese Arbeitsfassung muss vom Verantwortlichen und der
Datenschutzbeauftragten Stelle bestätigt werden. Sie legt keine Rechtsgrundlage
eigenständig fest.

## Verarbeitung

**Bezeichnung:** 9 Freunde Familien- und Verwaltungsportal  
**Zwecke:** Vertrags- und Stammdatenverwaltung, Betreuungskommunikation,
Abrechnung, Terminorganisation sowie private Fotoverwaltung bei gesondertem
Nachweis.  
**Betroffene:** Kinder, Sorgeberechtigte, Abholberechtigte und Beschäftigte.  
**Systeme:** ChatGPT Sites/Cloudflare Runtime, Google Workspace Sheets, Shared
Drive und Calendar.  
**Keine Standardverarbeitung:** öffentliche Fotolinks, Gesichtserkennung,
automatische Kind-Tags oder LLM-Auswertung von Kinderdaten.

## Feld- und Zweckmatrix

| Kategorie/Felder | Zweck | Schutzklasse | Rechtsgrundlage durch DSB zu bestätigen | Zugriff |
| --- | --- | --- | --- | --- |
| Kind-ID, Name, Geburtstag, Start, Gruppe, Status, Betreuungsumfang | Betreuung und Vertragsdurchführung | hoch | KiBiz/Vertrag/gesetzliche Pflicht | zuständiges Personal |
| Eltern-ID, Name, Anschrift, Kontakt | Vertrag, Erreichbarkeit, Notfallkommunikation | hoch | KiBiz/Vertrag/gesetzliche Pflicht | zuständiges Personal |
| Allergien, Ernährung, Gesundheits-/Notfallhinweise | sichere Betreuung | besonders hoch, Art. 9 | Art.-9-Ausnahme und Erforderlichkeit schriftlich festlegen | eng begrenztes Betreuungspersonal |
| Familiensprache | pädagogische Förderung und KiBiz-Aufgabe | hoch | Erforderlichkeit nach KiBiz festlegen | pädagogisches Personal |
| Gebühren, Rechnungen, Verträge | Abrechnung und Nachweis | hoch | Vertrag und gesetzliche Aufbewahrung | Leitung/Verwaltung |
| Termine und Empfängeradressen | Organisation und Einladung | hoch | Vertrag/Aufgabe oder Einwilligung je Terminart | schreibberechtigtes Personal |
| Fotos und private Galerie | Dokumentation/Elternkommunikation | besonders hoch | gesonderte, freiwillige und widerrufliche Einwilligung | gemäß Einwilligungsumfang |
| Einwilligungsnachweise | Rechenschaft und Widerruf | besonders hoch | rechtliche Verpflichtung/Rechenschaft | Administrator/DSB |
| Pseudonymisierte Auditereignisse | Sicherheit und Nachweis | hoch | berechtigtes Interesse/rechtliche Pflicht prüfen | Administrator/IT/DSB |
| Datenschutzanfragen | Betroffenenrechte | besonders hoch | DSGVO-Pflicht | Administrator/DSB |

## Empfänger und Auftragsverarbeiter

Vor Freigabe sind je Anbieter Vertrag, Rolle, Unterauftragnehmer,
Verarbeitungsorte, Transfermechanismus, Löschung, Unterstützung bei
Betroffenenrechten, Incident-Fristen und Sicherheitsnachweis zu dokumentieren:

| Anbieter | Rolle/Zweck | AVV-Referenz | Unterauftragnehmer geprüft | Transfer geprüft | TOM-Nachweis |
| --- | --- | --- | --- | --- | --- |
| OpenAI / ChatGPT Sites | Hosting und Zugangskontrolle |  |  |  |  |
| Cloudflare | Laufzeit/Netzwerk im Sites-Dienst |  |  |  |  |
| Google Workspace | Sheets, Shared Drive, Calendar |  |  |  |  |

## Löschung und Rechte

Die konkrete Frist je Kategorie wird im freigegebenen Löschplan geführt.
Technisch werden Datenschutzanfragen mit pseudonymisierter Subjektreferenz,
Fälligkeit und Vier-Augen-Prüfung erfasst. Eine Anfrage löscht nicht
automatisch: gesetzliche Aufbewahrung, Sorgeberechtigung, Identitätsprüfung,
Backups und abhängige Systeme müssen vor der bestätigten Ausführung geprüft
werden.

