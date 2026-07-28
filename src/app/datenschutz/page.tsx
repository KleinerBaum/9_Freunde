import Link from "next/link";

import { privacyConfiguration } from "../../lib/server/privacy-config";

export const dynamic = "force-dynamic";

const missing = "Vor der Produktivfreigabe durch den Träger einzutragen";

export default function PrivacyPage() {
  const config = privacyConfiguration();
  return (
    <main className="legal-page">
      <article className="legal-card">
        <Link href="/">← Zum Familienportal</Link>
        <span className="eyebrow">Information nach Art. 13 DSGVO</span>
        <h1>Datenschutzhinweise</h1>
        <h2>Verantwortlicher</h2>
        <p>{config.controllerName || missing}<br />{config.controllerAddress || missing}</p>
        <p>Datenschutzkontakt: {config.privacyEmail ? <a href={`mailto:${config.privacyEmail}`}>{config.privacyEmail}</a> : missing}</p>
        <p>Datenschutzbeauftragte Stelle: {config.dpoEmail ? <a href={`mailto:${config.dpoEmail}`}>{config.dpoEmail}</a> : missing}</p>

        <h2>Zwecke und Datenarten</h2>
        <p>Das Portal unterstützt die vertragliche und gesetzliche Verwaltung der Kindertageseinrichtung, die Betreuungskommunikation, Dokumente, Termine und – nur bei nachgewiesener Einwilligung – private Fotos. Verarbeitet werden ausschließlich die hierfür freigegebenen Stamm-, Kontakt-, Betreuungs-, Abrechnungs-, Gesundheits-, Einwilligungs- und Nutzungsdaten.</p>

        <h2>Rechtsgrundlagen und Empfänger</h2>
        <p>Die konkrete Rechtsgrundlage wird je Verarbeitung im Verzeichnis der Verarbeitungstätigkeiten festgelegt. Gesundheitsdaten und Fotos werden gesondert bewertet. Technische Empfänger dürfen ausschließlich vertraglich gebundene Auftragsverarbeiter und ausdrücklich berechtigte Beschäftigte sein. Öffentliche Freigabelinks sind ausgeschlossen.</p>

        <h2>Speicherdauer</h2>
        <p>Daten werden nach dem freigegebenen Aufbewahrungs- und Löschplan gelöscht oder anonymisiert. Widerrufene Fotoeinwilligungen sperren zukünftige Verarbeitung unverzüglich; die weitere Behandlung vorhandener Aufnahmen wird dokumentiert geprüft.</p>

        <h2>Ihre Rechte</h2>
        <p>Betroffene Personen können Auskunft, Berichtigung, Löschung, Einschränkung, Datenübertragbarkeit und – soweit anwendbar – Widerspruch oder Widerruf verlangen. Anfragen richten Sie an den oben genannten Datenschutzkontakt. Zusätzlich besteht ein Beschwerderecht bei der zuständigen Datenschutzaufsicht.</p>

        <h2>Sicherheit und Vorfälle</h2>
        <p>Das Portal nutzt rollenbasierte Zugriffe, verwaltete Identitäten, private Ablagen und eine pseudonymisierte Nachvollziehbarkeit sicherheitsrelevanter Vorgänge. Datenschutzvorfälle werden nach dem freigegebenen Incident-Verfahren bewertet und erforderlichenfalls fristgerecht gemeldet.</p>
      </article>
    </main>
  );
}
