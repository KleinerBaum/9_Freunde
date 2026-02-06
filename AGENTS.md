# Logikrollen ("Agenten") in der 9-Freunde App

Die Streamlit-App **9 Freunde** ist in mehrere modulare Logikkomponenten ("Agenten") unterteilt. Jeder Agent übernimmt klar definierte Aufgaben, was die Wartbarkeit und Sicherheit des Systems erhöht. Im Folgenden werden die wichtigsten Agenten und ihre Verantwortlichkeiten beschrieben:

## AuthAgent (Authentifizierung & Autorisierung)
Der **AuthAgent** kümmert sich um die sichere Anmeldung der Benutzer und die Unterscheidung zwischen **Eltern** und **Leitung** (Administrator). Seine Hauptaufgaben sind:
- **Benutzerauthentifizierung:** Prüft Anmeldedaten (E-Mail und Passwort) gegen die hinterlegten Berechtigungen. In einer produktiven Umgebung erfolgt dies über einen sicheren Authentifizierungsdienst (z. B. Firebase Auth); für das Prototyping können Anmeldedaten auch in der Konfiguration hinterlegt werden.
- **Sitzungsverwaltung:** Verwaltet angemeldete Sitzungen innerhalb der Streamlit-App (z. B. via `st.session_state`) und stellt sicher, dass nur authentifizierte Benutzer auf interne Bereiche zugreifen.
- **Rollensteuerung:** Unterscheidet anhand der angemeldeten E-Mail-Adresse oder hinterlegter Rollen, ob es sich um eine Leitungskraft (Admin) oder ein Elternteil handelt, und ermöglicht bzw. beschränkt Funktionen entsprechend. Admin-Benutzer erhalten Zugriff auf Verwaltungsfunktionen (Stammdatenpflege, Dokumentenerstellung, Foto-Upload, Kalenderpflege), während Eltern nur lesenden Zugriff auf für sie relevante Informationen (eigene Kinder, freigegebene Dokumente/Fotos, Termine) erhalten.

## DocumentAgent (Dokumentenerstellung)
Der **DocumentAgent** ist verantwortlich für das Generieren von Dokumenten und Berichten. Wesentliche Aspekte:
- **Texterstellung mit KI:** Nutzt die OpenAI API, um aus Stichpunkten oder strukturierten Daten automatisch Fließtexte zu generieren (z. B. Tagesberichte, Entwicklungsdokumentationen oder Elternbriefe). Dadurch wird die Leitung bei der Formulierung von Texten unterstützt.
- **Dokumentengenerierung:** Erstellt formatierte Dokumente (z. B. in Word-Format mittels `python-docx`) und kann diese bei Bedarf auch als PDF aufbereiten (z. B. mit `PyPDF2`). Dabei werden Stammdaten (Name des Kindes, Datum, etc.) automatisch eingefügt.
- **Integration mit Dateiablage:** Nach Generierung kann der DocumentAgent die fertigen Dokumente entweder zum direkten Download bereitstellen oder an den **DriveAgent** übergeben, um sie in der Google Drive Ablage abzulegen (etwa in einem Dokumente-Ordner pro Kind). So bleiben erstellte Berichte auch langfristig zugänglich.

## DriveAgent (Dateiablage auf Google Drive)
Der **DriveAgent** übernimmt die Anbindung an Google Drive für das Speichern und Abrufen von Dateien, insbesondere Fotos und generierte Dokumente:
- **Upload & Download:** Lädt Dateien (z. B. PDF/DOCX-Dokumente oder Fotos) in die Google Drive Ablagestruktur hoch und kann sie bei Bedarf wieder herunterladen. Er nutzt dazu die Google Drive API (über einen Service-Account), wodurch die App keine Dateien lokal speichern muss.
- **Ordnerstruktur verwalten:** Organisiert die Ablage in Drive, z. B. durch Anlage eines Hauptordners für die Großtagespflege und Unterordner pro Kind (für persönliche Dokumente und Fotos). Der DriveAgent kann automatisiert neue Unterordner erstellen, wenn neue Kinder angelegt werden.
- **Berechtigungen & Zugriff:** Sorgt dafür, dass nur berechtigte Benutzer Zugriff auf die jeweiligen Dateien haben. Z. B. können Foto-Ordner eines Kindes nur von der Leitung beschrieben und vom jeweiligen Elternteil gelesen werden. Die Daten verlassen nicht die Drive-Umgebung, was zur DSGVO-Konformität beiträgt (keine öffentliche Freigabe ohne Berechtigung).

## CalendarAgent (Kalenderverwaltung)
Der **CalendarAgent** verbindet die Anwendung mit dem Google Kalender der Einrichtung. Aufgaben im Überblick:
- **Terminerstellung und -pflege:** Ermöglicht der Leitung, wichtige Termine (Eingewöhnungen, Ausflüge, Schließtage, Elternabende etc.) über die App in einem zentralen Google Kalender einzutragen. Dies geschieht über die Google Calendar API.
- **Anzeige von Terminen:** Stellt für Eltern eine lesbare Liste oder Kalenderansicht der relevanten Termine bereit. Eltern sehen nur allgemeine Termine der Einrichtung oder individuelle Termine, die ihr Kind betreffen.
- **Synchronisation:** Da ein echter Google Kalender verwendet wird, können Eltern optional diesen Kalender abonnieren oder automatisch Benachrichtigungen erhalten. Der CalendarAgent stellt in der App sicher, dass er stets die aktuellen Events aus dem Kalender abruft (ggf. mit Zwischenspeicherung, um Performance zu verbessern).

## StammdatenManager (Verwaltung der Stammdaten)
Die Verwaltung der Grunddaten aller betreuten Kinder erfolgt durch den **StammdatenManager**:
- **Datenhaltung:** Speichert und lädt Stammdaten der Kinder, Erziehungsberechtigten und ggf. Betreuer. Typische Stammdaten sind Name und Geburtsdatum des Kindes, Kontaktdaten der Eltern, Zugehörigkeit der Elternkonten zu Kindern, Gesundheitsinformationen usw. Diese Daten werden in einer sicheren Datenbank (z. B. Firebase Firestore über `firebase-admin`) oder ersatzweise in einer lokalen Datei/einem Streamlit-Session-State gehalten.
- **CRUD-Funktionen:** Bietet der Leitung Funktionen, um Kinder und zugehörige Daten anzulegen, zu bearbeiten oder zu archivieren (Create, Read, Update, Delete). Änderungen werden in Echtzeit übernommen, so dass z. B. neu angelegte Kinder sofort in anderen Bereichen (Dokumente, Fotos) zur Verfügung stehen.
- **Integrität & Zugriff:** Stellt sicher, dass Stammdaten nur von autorisierten Personen (Leitung) geändert werden können. Eltern haben nur Leserechte auf die Stammdaten ihres eigenen Kindes (z. B. könnten sie die hinterlegten Kontaktdaten oder Allergien ihres Kindes einsehen, aber nicht eigenständig ändern).

## PhotoAgent (Fotoverwaltung & DSGVO-Konformität)
Der **PhotoAgent** ist zuständig für den Umgang mit Fotos unter Wahrung der Privatsphäre:
- **Foto-Upload und -Speicherung:** Ermöglicht der Leitung, Fotos der Kinder hochzuladen. Hochgeladene Bilder werden vom PhotoAgent entgegengenommen und mithilfe des DriveAgent in der Google Drive Ablage im entsprechenden Ordner gespeichert.
- **Gesichtserkennung:** Die Bibliothek `face_recognition` kommt zum Einsatz, um automatisch Gesichter auf Fotos zu erkennen. Dadurch kann die App identifizieren, welche Kinder auf einem Foto abgebildet sind. Anhand zuvor hinterlegter Referenzbilder der Kinder (z. B. ein Profilfoto pro Kind zur Registrierung) werden Gesichtsembeddings erzeugt. Bei jedem neuen Foto vergleicht der PhotoAgent erkannte Gesichter mit den bekannten Embeddings der Kinder.
- **Zugriffsbeschränkung:** Basierend auf der Gesichtserkennung oder manueller Zuordnung taggt der PhotoAgent jedes Foto mit dem entsprechenden Kind bzw. den Kindern. Eltern sehen in ihrer Ansicht nur Fotos, auf denen ausschließlich ihr eigenes Kind zu sehen ist. Fotos von Gruppen oder fremden Kindern werden entweder für sie ausgeblendet oder es werden Gesichter fremder Kinder automatisch unkenntlich gemacht (z. B. durch Verpixelung), um die Privatsphäre zu schützen.
- **Performance & Cache:** Da Bildverarbeitung rechenintensiv ist, werden erkannte Gesichtsembeddings zwischengespeichert (`@st.cache_data`), und Operationen wie das Laden von Vorschaubildern erfolgen optimiert (z. B. reduzierte Auflösung für die Anzeige in der App). Dies stellt sicher, dass auch bei vielen Fotos die App flüssig bleibt.

Alle diese Agenten arbeiten zusammen, um ein ganzheitliches System zu bilden: **AuthAgent** regelt den Zugang, **StammdatenManager** liefert Kontext, **DocumentAgent** und **PhotoAgent** erstellen Inhalte, während **DriveAgent** und **CalendarAgent** die externe Integration zu Google-Diensten handhaben. Durch diese klare Trennung der Logikrollen bleibt der Code übersichtlich, erweiterbar und sicher.
