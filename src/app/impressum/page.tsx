import Link from "next/link";

import { privacyConfiguration } from "../../lib/server/privacy-config";

export const dynamic = "force-dynamic";

const missing = "Vor der Produktivfreigabe durch den Träger einzutragen";

export default function ImprintPage() {
  const config = privacyConfiguration();
  return (
    <main className="legal-page">
      <article className="legal-card">
        <Link href="/">← Zum Familienportal</Link>
        <span className="eyebrow">Anbieterkennzeichnung</span>
        <h1>Impressum</h1>
        <h2>Diensteanbieter</h2>
        <p>{config.controllerName || missing}<br />{config.controllerAddress || missing}</p>
        <h2>Kontakt</h2>
        <p>{config.privacyEmail ? <a href={`mailto:${config.privacyEmail}`}>{config.privacyEmail}</a> : missing}</p>
        <h2>Vertretung und Register</h2>
        <p>Vertretungsberechtigte Person: {config.legalRepresentative || missing}</p>
        <p>Registerangaben: {config.legalRegister || missing}</p>
        <h2>Aufsicht</h2>
        <p>{config.supervisoryAuthority || missing}</p>
      </article>
    </main>
  );
}
