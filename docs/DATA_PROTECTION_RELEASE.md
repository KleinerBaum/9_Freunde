# Datenschutz- und Trägerfreigabe

Status: **Nicht freigegeben für Echtdaten oder weitere Nutzerkonten**

Dieses Dokument ist die verbindliche Freigabeakte für den ersten
Personal-Pilot. Technische Prüfungen allein setzen `REAL_DATA_APPROVED` nicht
auf `true`. Die Nachweise werden beim Träger außerhalb des Repositorys
aufbewahrt und nur über nicht personenbezogene Referenzen dokumentiert.

## Verantwortlichkeit und Beteiligte

| Funktion | Name/Organisation | Nachweisreferenz | Datum |
| --- | --- | --- | --- |
| Verantwortlicher Träger |  |  |  |
| Freigabeverantwortliche Person |  |  |  |
| Datenschutzbeauftragte Stelle |  |  |  |
| IT-Sicherheitsverantwortung |  |  |  |
| Betriebs-/Fachverantwortung |  |  |  |
| Örtliches Jugendamt, falls beteiligt |  |  |  |
| LVR/LWL, falls beteiligt |  |  |  |

## Verbindlicher Umfang

- erste Phase: ausschließlich namentlich freigegebenes Kita-Personal
- Elternzugänge: deaktiviert (`PARENT_ACCESS_ENABLED=false`)
- MCP/ChatGPT-Werkzeuge: deaktiviert (`MCP_ENABLED=false`)
- Hosting: Sites-Zugriffsmodus `custom`, keine Gruppen und nur einzeln
  bestätigte verwaltete Konten
- Identität: Sites-Authentifizierung und serverseitige Nutzerzuordnung;
  keine Tabellenpasswörter im Produktivbetrieb
- Daten: nur für den dokumentierten Betreuungs- und Verwaltungszweck
- Fotos: nur bei aktuell erteilter, revisionsfähig nachgewiesener Einwilligung

## Freigabegates

Alle Punkte müssen mit einem extern aufbewahrten Nachweis belegt sein.

- [ ] Verzeichnis der Verarbeitungstätigkeiten und Feld-Rechtsgrundlagen geprüft
- [ ] Datenschutz-Folgenabschätzung abgeschlossen und Restrisiko akzeptiert
- [ ] Datenschutzinformationen und Anbieterkennzeichnung vollständig
- [ ] AV-Verträge, Unterauftragsverarbeiter, Datenstandorte und
      Drittlandtransfers geprüft
- [ ] Technische und organisatorische Maßnahmen des Trägers und der Anbieter
      geprüft
- [ ] Rollenmatrix und Liste der Pilotkonten genehmigt
- [ ] Einwilligungsformular, Versionierung und Widerrufsprozess genehmigt
- [ ] Aufbewahrungs- und Löschplan genehmigt
- [ ] Backup und Wiederherstellung mit fiktiven Daten getestet
- [ ] Incident-Prozess einschließlich 72-Stunden-Bewertung getestet
- [ ] Auskunft, Berichtigung, Löschung und Zugriffsentzug als
      Datenschutzanfragen getestet
- [ ] Google Shared Drive und dediziertes verwaltetes Calendar-Konto geprüft
- [ ] Domain-wide Delegation ist auf `calendar.events` beschränkt
- [ ] Audit-Tabelle enthält keine Namen, E-Mail-Adressen oder fachlichen Inhalte
- [ ] Automatisierte Prüfungen, Build und Sicherheitstest sind erfolgreich
- [ ] Pilotstart, Reviewdatum, Abbruchkriterien und Rückfallversion festgelegt

## Technischer Nachweisstand

Der Quellstand stellt folgende Kontrollen bereit; ihre Wirksamkeit in der
veröffentlichten Umgebung ist vor Pilotbeginn gesondert nachzuweisen:

| Kontrolle | Im Quellstand | Noch extern/operativ zu prüfen |
| --- | --- | --- |
| Echtdaten-Sperre | Google-Modus benötigt Freigabeschalter und vollständiges technisches Gate | unterzeichnete Freigabe und korrekte Sites-Secrets |
| Rollen | `admin`, `staff_write`, `staff_read`, `parent`; serverseitige Schreib- und Adminprüfungen | Rollenmatrix, Pilotkonten und Rezertifizierung |
| Identität | Sites-Identität, verwaltete E-Mail-Domäne, 30-Minuten-Sitzung, serverseitiger Widerruf | Sites-Allowlist und MFA-Richtlinie im Identitätsanbieter |
| Einwilligung | versionierte Nachweise; Fotozugriff fällt bei fehlendem, eingeschränktem oder widerrufenem Stand geschlossen aus | Formular, Rechtsprüfung, Altbestandsmigration |
| Nachvollziehbarkeit | pseudonymisierte Anmelde-, Lese-, Änderungs-, Foto-, Dokument-, Rollen- und Cloud-Ereignisse | Aufbewahrungsfrist, Zugriff auf Audit-Tabelle, Monitoring |
| Betroffenenrechte | bestätigte, fällige Anfragen; kontrollierter Rollen-/Zugriffsentzug | Identitätsprüfung, Vier-Augen-Ausführung, Löschung in Backups |
| Web-Sicherheit | SameSite/HttpOnly/Secure, Origin-Prüfung, Login-Sperre, CSP/HSTS/Frame/Permissions-Header | unabhängiger Sicherheitstest und verwaltete MFA |
| Cloud | private serverseitige Zugriffe; Calendar nur `calendar.events`; persönliche Gmail-Organisatoren werden abgelehnt | AVV, Unterauftragnehmer, Transfer, Shared Drive und Restore |

Die Implementierung ersetzt weder DSFA, Vertragsprüfung noch schriftliche
Träger- und Datenschutzfreigabe. Solange ein Freigabegate offen ist, bleibt der
Status „nicht freigegeben“.

## Aktivierungsentscheidung

`REAL_DATA_APPROVED=true` darf erst nach vollständiger Unterzeichnung gesetzt
werden. Jede Änderung dieser Variablen, der Rollen, der Anbieter, der Zwecke,
der Datenkategorien oder der Cloud-Berechtigungen erfordert eine neue
Freigabeprüfung und anschließend eine neue Sites-Version.

```text
Freigabestatus: ABGELEHNT / BEFRISTET FREIGEGEBEN
Freigabereferenz:
Gültig ab:
Review spätestens:
Pilotkonten-Referenz:
Restrisikoentscheidung:
Träger-Unterschrift:
Datenschutz-Unterschrift:
IT-Sicherheits-Unterschrift:
```

## Abbruchkriterien

Der Pilot wird sofort beendet und der Zugriff eigentümerbeschränkt, wenn
unbefugter Zugriff, fehlende Einwilligungsdurchsetzung, personenbezogene Daten
in Logs, ein nicht verwaltetes Konto, eine unbekannte Datenübermittlung, ein
nicht behebbarer Integrationsfehler oder ein meldepflichtiger Vorfall vermutet
wird. Bis zur Bewertung werden externe Schreibvorgänge und Fotozugriffe
gesperrt.
