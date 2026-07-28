# Aufbewahrung, Löschung, Backup und Datenschutzvorfälle

Status: **Fristen und Verantwortliche müssen vor Produktivfreigabe genehmigt
werden.**

## Löschregeln

| Kategorie | Auslöser | Sofortmaßnahme | Endgültige Löschung |
| --- | --- | --- | --- |
| aktive Stammdaten | Ende Betreuung/Vertrag | Zugriff auf erforderliche Verwaltung begrenzen | nach genehmigter gesetzlicher/vertraglicher Frist |
| Gesundheits-/Notfallangaben | Zweckende oder Berichtigung | nicht mehr benötigte Anzeige sperren | unverzüglich, sofern keine Pflicht entgegensteht |
| Fotos | Widerruf, Zweckende, Betreuungsende | Anzeige und Upload sofort sperren | nach dokumentierter Rechtsprüfung und aus Drive/Backups gemäß Plan |
| Einwilligungsnachweis | Ersatz/Widerruf | neuen Status sofort wirksam machen | als Rechenschaftsnachweis nach genehmigter Frist |
| Dokumente/Rechnungen | Vertrags-/Geschäftsjahresende | Schreibschutz | nach bestätigter handels-/steuerrechtlicher Frist |
| Calendar-Termine | Termin-/Zweckende | Empfängerzugriff beenden | nach genehmigter kurzer Betriebsfrist |
| Auditdaten | Ablauf Sicherheitsnachweisfrist | Zugriff auf IT/DSB begrenzen | nach genehmigter Auditfrist |
| Datenschutzanfragen | Abschluss | Zugriff auf DSB/Administration begrenzen | nach genehmigter Nachweisfrist |

Eine automatische irreversible Löschung ist erst zulässig, wenn Abhängigkeiten,
gesetzliche Sperren, Identität und Sorgeberechtigung geprüft wurden. Bis dahin
wird über `/api/admin/privacy/requests` ein bestätigter, fälliger Workflow
angelegt. Direkte Löschung bleibt bewusst außerhalb eines Ein-Klick-Vorgangs.

## Backup und Wiederherstellung

1. Verantwortliche Person, Turnus, Verschlüsselung, Speicherort und
   Aufbewahrung extern festlegen.
2. Sheets, private Drive-Struktur, Calendar-Konfiguration und notwendige
   Konfigurationsmetadaten einbeziehen; Secrets separat sichern.
3. Restore mindestens vor Pilotstart und danach im genehmigten Turnus mit
   fiktiven Datensätzen testen.
4. Prüfen, dass gelöschte oder widerrufene Daten nicht unkontrolliert aus
   Backups in den aktiven Bestand zurückkehren.
5. Ergebnis, Dauer, Datenverlustfenster und Abweichungen nur mit
   nicht-personenbezogenen Referenzen dokumentieren.

## Incident-Prozess

1. **Erkennen und sichern:** Zeitpunkt, System, Art und Umfang erfassen; keine
   personenbezogenen Inhalte in Tickets oder Logs kopieren.
2. **Eindämmen:** Sites-Zugriff eigentümerbeschränkt lassen/setzen,
   `REAL_DATA_APPROVED=false`, MCP deaktivieren, betroffene Konten und Sessions
   über `active=false` beziehungsweise erhöhte `session_version` widerrufen.
3. **Bewerten:** Datenschutz und IT-Sicherheit unverzüglich beteiligen;
   Vertraulichkeit, Integrität, Verfügbarkeit, Kinderbezug und mögliche Folgen
   bewerten.
4. **Fristen:** Entscheidung über Meldung an Aufsicht und Benachrichtigung
   Betroffener so organisieren, dass die DSGVO-Fristen eingehalten werden.
5. **Beheben und verifizieren:** Ursache schließen, Zugriffe und Auditdaten
   prüfen, Restore nur kontrolliert durchführen.
6. **Wiederfreigabe:** nur mit dokumentierter Träger-, Datenschutz- und
   IT-Sicherheitsentscheidung sowie neuer technischer Abnahme.

```text
Incident-Eigner:
Datenschutzkontakt:
IT-Sicherheitskontakt:
Träger-Eskalation:
Anbieter-Eskalation Sites/Google:
Aufsichtsbehörde:
Kommunikationsvertretung:
```

