# Datenschutz-Folgenabschätzung – 9 Freunde

Status: **offen; Produktivfreigabe gesperrt**

Die DSFA wird vorsorglich als erforderlich behandelt, weil Daten von Kindern,
Gesundheitsangaben, Fotos, systematische Verwaltung und mehrere Cloud-Dienste
zusammentreffen.

## Beschreibung und Notwendigkeit

- Verarbeitungszwecke und betroffene Gruppen: siehe
  `PROCESSING_REGISTER.md`
- Datenfluss: Browser → Sites-Zugriffskontrolle → serverseitige Anwendung →
  private Google-Workspace-Ressourcen
- normale Portalnutzung benötigt keine LLM-Verarbeitung
- Elternzugang und MCP bleiben im Personal-Pilot deaktiviert
- jede Datenkategorie muss für den angegebenen Zweck erforderlich sein;
  optionale Felder bleiben leer, wenn kein dokumentierter Bedarf besteht

## Risikobewertung

Bewertung: Eintritt `1–4`, Auswirkung `1–4`, Risiko = Produkt. Ab `8` ist eine
zusätzliche Maßnahme oder dokumentierte Restrisikoentscheidung erforderlich.

| Risiko | Betroffene Rechte | Ausgangsrisiko | Kontrollen | Restrisiko | Verantwortlich |
| --- | --- | ---: | --- | ---: | --- |
| Falsche Kind-/Elternzuordnung | Vertraulichkeit, Kindeswohl | 16 | serverseitige Zuordnung, negative Zugriffstests |  |  |
| Zu weitreichende Personalrolle | Vertraulichkeit, Integrität | 12 | `staff_read`, `staff_write`, `admin`, jährliche Rezertifizierung |  |  |
| Foto ohne gültige Einwilligung | Rechtmäßigkeit, Persönlichkeitsrecht | 16 | revisionsfähiger Nachweis, serverseitige Upload-/Anzeige-Sperre |  |  |
| Unbefugter Download/Screenshot | Kontrollverlust über Bilddaten | 16 | Elternpilot aus, Freigabe nur bei Download-Einwilligung, Schulung |  |  |
| Kontoübernahme | alle gespeicherten Daten | 16 | Sites-Identität, verwaltete Domain, MFA-Vorgabe, Login-Sperre |  |  |
| Session-/CSRF-Angriff | Vertraulichkeit, Integrität | 12 | kurze Sitzung, SameSite, Origin-Prüfung, Sicherheitsheader |  |  |
| Cloud-/Drittlandzugriff | Vertraulichkeit, Rechtsmäßigkeit | 16 | AVV, Transferprüfung, Unterauftragnehmerprüfung, private Ressourcen |  |  |
| Datenverlust | Verfügbarkeit, Betreuungssicherheit | 12 | Backup-/Restore-Test, Wiederanlaufplan |  |  |
| Personenbezug in Logs | Vertraulichkeit | 12 | HMAC-pseudonymisierte Referenzen, keine Freitextinhalte |  |  |
| Verspätete Vorfallreaktion | Betroffenenrechte | 12 | Incident-Eigner, 72-Stunden-Triage, Kontaktkette |  |  |
| Überlange Speicherung | Löschrecht, Datenminimierung | 12 | Löschplan, Datenschutzanfragen, regelmäßige Prüfung |  |  |
| Fehlkonfiguration Calendar/Drive | Offenlegung oder Fehlversand | 16 | Shared Drive, verwalteter Organisator, schmale Scopes, Health-Check |  |  |

## Konsultation und Entscheidung

Erforderliche Anhörungen: Träger, Datenschutzbeauftragte Stelle,
IT-Sicherheit, pädagogische Leitung und – sofern verlangt – zuständige
Jugendhilfeaufsicht. Bei verbleibendem hohen Risiko ist vor Beginn die
zuständige Datenschutzaufsicht zu konsultieren.

```text
DSFA-Version:
Bewertungsdatum:
Verantwortlicher:
Datenschutzbeauftragte Stelle:
Verbleibende hohe Risiken:
Zusätzliche Maßnahmen:
Freigabe / Ablehnung:
Nächste Überprüfung:
```

