"use client";

import {
  type CSSProperties,
  type ChangeEvent,
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react";

import type {
  AppAction,
  CalendarEvent,
  Child,
  DashboardSnapshot,
  ManagedDocument,
  Parent
} from "../lib/contracts";
import { Icon, type IconName } from "./icon";

type View = "overview" | "children" | "documents" | "calendar" | "photos" | "profile" | "settings";
type ModalName = "child" | "event" | "document" | null;

const ADMIN_NAV: Array<{ id: View; label: string; icon: IconName }> = [
  { id: "overview", label: "Tagesblick", icon: "home" },
  { id: "children", label: "Kinder & Familien", icon: "children" },
  { id: "documents", label: "Dokumente", icon: "document" },
  { id: "calendar", label: "Kalender", icon: "calendar" },
  { id: "photos", label: "Fotomomente", icon: "photo" },
  { id: "settings", label: "Einstellungen", icon: "settings" }
];

const PARENT_NAV: Array<{ id: View; label: string; icon: IconName }> = [
  { id: "overview", label: "Start", icon: "home" },
  { id: "children", label: "Mein Kind", icon: "heart" },
  { id: "calendar", label: "Termine", icon: "calendar" },
  { id: "photos", label: "Fotomomente", icon: "photo" },
  { id: "documents", label: "Dokumente", icon: "document" },
  { id: "profile", label: "Mein Profil", icon: "profile" }
];

const VIEW_COPY: Record<View, { title: string; eyebrow: string }> = {
  overview: { title: "Schön, dass du da bist.", eyebrow: "Heute bei 9 Freunde" },
  children: { title: "Kinder & Familien", eyebrow: "Alles Wichtige an einem Ort" },
  documents: { title: "Verträge & Abrechnungen", eyebrow: "Vorbereiten, prüfen, fertig" },
  calendar: { title: "Gemeinsam gut geplant", eyebrow: "Termine & Erinnerungen" },
  photos: { title: "Kleine Momente, sicher geteilt", eyebrow: "Geschützte Fotogalerie" },
  profile: { title: "Meine Angaben", eyebrow: "Kontaktdaten aktuell halten" },
  settings: { title: "System & Datenschutz", eyebrow: "Verbindungen und Zugriffe" }
};

const money = (cents: number) => new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(cents / 100);
const day = (value: string) => new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "short" }).format(new Date(value));
const dateTime = (value: string) => new Intl.DateTimeFormat("de-DE", { weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
const fullDate = (value: string) => value ? new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "long", year: "numeric" }).format(new Date(value)) : "—";

const STATUS_LABELS: Record<string, string> = {
  active: "Aktiv",
  onboarding: "Eingewöhnung",
  paused: "Pausiert",
  archived: "Archiviert",
  draft: "Entwurf",
  sent: "Versendet",
  signed: "Unterzeichnet",
  paid: "Bezahlt",
  overdue: "Überfällig",
  granted: "Erteilt",
  restricted: "Eingeschränkt",
  missing: "Fehlt"
};

async function readJson<T>(response: Response): Promise<T> {
  const payload = await response.json() as T & { error?: string };
  if (!response.ok) throw new Error(payload.error || "Die Anfrage konnte nicht abgeschlossen werden.");
  return payload;
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand-lockup ${compact ? "brand-lockup--compact" : ""}`}>
      <span className="brand-mark"><span>9</span><i>♥</i></span>
      <span className="brand-copy"><strong>Freunde</strong><small>Kinderbetreuung mit Liebe</small></span>
    </div>
  );
}

function Avatar({ name, tone = 0, large = false }: { name: string; tone?: number; large?: boolean }) {
  const initials = name.split(/\s+/u).filter(Boolean).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  return <span className={`avatar avatar--${tone % 5} ${large ? "avatar--large" : ""}`}>{initials || "?"}</span>;
}

function Pill({ value }: { value: string }) {
  return <span className={`pill pill--${value}`}>{STATUS_LABELS[value] ?? value}</span>;
}

function Empty({ icon, title, copy }: { icon: IconName; title: string; copy: string }) {
  return <div className="empty"><span><Icon name={icon} /></span><strong>{title}</strong><p>{copy}</p></div>;
}

function Modal({ title, eyebrow, children, onClose }: { title: string; eyebrow: string; children: ReactNode; onClose: () => void }) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}>
      <section className="modal" role="dialog" aria-modal="true" aria-label={title}>
        <header><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div><button className="icon-button" type="button" onClick={onClose} aria-label="Schließen"><Icon name="close" /></button></header>
        {children}
      </section>
    </div>
  );
}

function Login({ onLogin }: { onLogin: (email: string, password: string) => Promise<void> }) {
  const [email, setEmail] = useState("leitung@demo.9freunde.de");
  const [password, setPassword] = useState("willkommen");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setPending(true); setError("");
    try { await onLogin(email, password); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Anmeldung fehlgeschlagen."); }
    finally { setPending(false); }
  };

  const chooseDemo = (role: "admin" | "parent") => {
    if (role === "admin") { setEmail("leitung@demo.9freunde.de"); setPassword("willkommen"); }
    else { setEmail("eltern@demo.9freunde.de"); setPassword("familie"); }
  };

  return (
    <main className="login-page">
      <section className="login-story">
        <Brand />
        <div className="login-message">
          <span className="eyebrow">Mehr Zeit für das, was zählt</span>
          <h1>Verwaltung kann sich <em>leicht</em> anfühlen.</h1>
          <p>Ein ruhiger Ort für Stammdaten, Verträge, Abrechnungen, Termine und die besonderen kleinen Momente.</p>
          <div className="story-points">
            <span><Icon name="shield" /> Rollenbasierter Schutz</span>
            <span><Icon name="drive" /> Private Drive-Galerien</span>
            <span><Icon name="calendar" /> Calendar-Einladungen</span>
          </div>
        </div>
        <div className="login-orbit login-orbit--one">♥</div><div className="login-orbit login-orbit--two">✦</div>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <div className="login-card__intro"><span className="eyebrow">Familienportal</span><h2>Willkommen zurück</h2><p>Melde dich mit deinem persönlichen Zugang an.</p></div>
          <div className="demo-switch" aria-label="Demo-Zugang wählen">
            <button type="button" onClick={() => chooseDemo("admin")} className={email.startsWith("leitung") ? "active" : ""}><Icon name="spark" /> Leitung</button>
            <button type="button" onClick={() => chooseDemo("parent")} className={email.startsWith("eltern") ? "active" : ""}><Icon name="heart" /> Eltern</button>
          </div>
          <form onSubmit={submit} className="form-stack">
            <label><span>E-Mail-Adresse</span><span className="input-wrap"><Icon name="mail" /><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></span></label>
            <label><span>Passwort</span><span className="input-wrap"><Icon name="shield" /><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required minLength={6} /></span></label>
            {error ? <p className="form-error"><Icon name="warning" />{error}</p> : null}
            <button className="primary-button primary-button--wide" type="submit" disabled={pending}>{pending ? "Anmeldung läuft…" : "Sicher anmelden"}<Icon name="arrow" /></button>
          </form>
          <p className="demo-note"><Icon name="spark" /> Diese Vorschau nutzt ausschließlich erfundene Demodaten.</p>
        </div>
      </section>
    </main>
  );
}

function Sidebar({ snapshot, view, onView, onLogout, open, onClose }: { snapshot: DashboardSnapshot; view: View; onView: (view: View) => void; onLogout: () => void; open: boolean; onClose: () => void }) {
  const nav = snapshot.session.role === "admin" ? ADMIN_NAV : PARENT_NAV;
  return (
    <aside className={`sidebar ${open ? "sidebar--open" : ""}`}>
      <div className="sidebar__head"><Brand compact /><button className="icon-button sidebar__close" type="button" onClick={onClose} aria-label="Navigation schließen"><Icon name="close" /></button></div>
      <nav aria-label="Hauptnavigation">
        <span className="nav-label">Arbeitsbereich</span>
        {nav.map((item) => <button type="button" key={item.id} className={view === item.id ? "active" : ""} onClick={() => { onView(item.id); onClose(); }}><Icon name={item.icon} /><span>{item.label}</span>{view === item.id ? <i /> : null}</button>)}
      </nav>
      <div className="sidebar__bottom">
        <div className="privacy-chip"><Icon name="shield" /><span><strong>Privater Bereich</strong><small>{snapshot.integrations.mode === "demo" ? "Fiktionale Daten" : "Google Workspace"}</small></span></div>
        <div className="user-chip"><Avatar name={snapshot.session.name} tone={4} /><span><strong>{snapshot.session.name}</strong><small>{snapshot.session.role === "admin" ? "Leitung" : "Elternzugang"}</small></span><button type="button" onClick={onLogout} aria-label="Abmelden"><Icon name="logout" /></button></div>
      </div>
    </aside>
  );
}

function Topbar({ snapshot, onMenu, onNavigate }: { snapshot: DashboardSnapshot; onMenu: () => void; onNavigate: (view: View, focus?: string) => void }) {
  const [query, setQuery] = useState("");
  const results = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("de");
    if (needle.length < 2) return [];
    return [
      ...snapshot.children.map((child) => ({ kind: "Kind", title: child.name, detail: child.group, view: "children" as View, focus: child.id })),
      ...snapshot.documents.map((document) => ({ kind: "Dokument", title: document.title, detail: document.number, view: "documents" as View, focus: document.id })),
      ...snapshot.events.map((event) => ({ kind: "Termin", title: event.title, detail: dateTime(event.start), view: "calendar" as View, focus: event.id }))
    ].filter((item) => `${item.title} ${item.detail}`.toLocaleLowerCase("de").includes(needle)).slice(0, 6);
  }, [query, snapshot]);
  return (
    <header className="topbar">
      <button className="icon-button menu-button" type="button" onClick={onMenu} aria-label="Navigation öffnen"><Icon name="menu" /></button>
      <div className="search-box"><Icon name="search" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Kind, Dokument oder Termin suchen…" aria-label="Suchen" />
        {results.length ? <div className="search-results">{results.map((item) => <button type="button" key={`${item.kind}-${item.focus}`} onClick={() => { onNavigate(item.view, item.focus); setQuery(""); }}><span>{item.kind}</span><strong>{item.title}</strong><small>{item.detail}</small></button>)}</div> : null}
      </div>
      <div className="topbar__right"><span className={`mode-badge mode-badge--${snapshot.integrations.mode}`}><i />{snapshot.integrations.mode === "demo" ? "Demo-Modus" : "Live verbunden"}</span><Avatar name={snapshot.session.name} tone={3} /></div>
    </header>
  );
}

function PageIntro({ view, snapshot, action }: { view: View; snapshot: DashboardSnapshot; action?: ReactNode }) {
  const copy = view === "overview" && snapshot.session.role === "parent"
    ? { eyebrow: "Dein Familienbereich", title: `Hallo ${snapshot.session.name.split(" ")[0] || ""}, schön dass du da bist.` }
    : VIEW_COPY[view];
  return <div className="page-intro"><div><span className="eyebrow">{copy.eyebrow}</span><h1>{copy.title}</h1></div>{action}</div>;
}

function KpiCard({ icon, label, value, note, tone }: { icon: IconName; label: string; value: string | number; note: string; tone: string }) {
  return <article className={`kpi-card kpi-card--${tone}`}><span className="kpi-card__icon"><Icon name={icon} /></span><div><span>{label}</span><strong>{value}</strong><small>{note}</small></div></article>;
}

function AdminOverview({ snapshot, onModal, onNavigate }: { snapshot: DashboardSnapshot; onModal: (name: Exclude<ModalName, null>) => void; onNavigate: (view: View, focus?: string) => void }) {
  const active = snapshot.children.filter((child) => child.status === "active").length;
  const openDocs = snapshot.documents.filter((document) => ["draft", "sent", "overdue"].includes(document.status)).length;
  const overdue = snapshot.documents.filter((document) => document.status === "overdue").length;
  const upcoming = snapshot.events.filter((event) => new Date(event.start) >= new Date()).sort((a, b) => a.start.localeCompare(b.start));
  const attention = [
    ...snapshot.children.filter((child) => child.photoConsent === "missing").map((child) => ({ icon: "warning" as IconName, title: `Foto-Einwilligung fehlt`, detail: child.name, view: "children" as View, focus: child.id, tone: "amber" })),
    ...snapshot.documents.filter((document) => document.status === "overdue").map((document) => ({ icon: "document" as IconName, title: "Rechnung überfällig", detail: document.number, view: "documents" as View, focus: document.id, tone: "coral" })),
    ...snapshot.children.filter((child) => child.status === "onboarding").map((child) => ({ icon: "clock" as IconName, title: "Eingewöhnung vorbereiten", detail: child.name, view: "children" as View, focus: child.id, tone: "blue" }))
  ].slice(0, 4);
  return <>
    <PageIntro view="overview" snapshot={snapshot} action={<span className="today-chip"><Icon name="calendar" />{new Intl.DateTimeFormat("de-DE", { weekday: "long", day: "2-digit", month: "long" }).format(new Date())}</span>} />
    <section className="kpi-grid">
      <KpiCard icon="children" label="Aktive Kinder" value={active} note={`${snapshot.children.length - active} in Vorbereitung`} tone="sun" />
      <KpiCard icon="document" label="Dokumente offen" value={openDocs} note="Entwürfe & Rückläufe" tone="coral" />
      <KpiCard icon="warning" label="Überfällige Rechnungen" value={overdue} note={overdue ? "Bitte prüfen" : "Alles im Plan"} tone="mint" />
      <KpiCard icon="calendar" label="Nächste Termine" value={upcoming.length} note="In den nächsten 6 Monaten" tone="blue" />
    </section>
    <section className="dashboard-grid">
      <article className="panel panel--wide welcome-panel"><div className="welcome-panel__copy"><span className="eyebrow">Mit einem Klick starten</span><h2>Weniger klicken.<br /><em>Mehr begleiten.</em></h2><p>Die häufigsten Aufgaben sind hier direkt erreichbar.</p><div className="quick-actions"><button type="button" onClick={() => onModal("child")}><Icon name="plus" /> Kind aufnehmen</button><button type="button" onClick={() => onModal("document")}><Icon name="document" /> Dokument erstellen</button><button type="button" onClick={() => onModal("event")}><Icon name="calendar" /> Termin planen</button></div></div><div className="welcome-art" aria-hidden="true"><span className="sun-shape" /><span className="rainbow-shape" /><span className="heart-shape">♥</span><span className="flower-shape">✿</span></div></article>
      <article className="panel attention-panel"><header className="panel__head"><div><span className="eyebrow">Aufmerksamkeit</span><h2>Das ist als Nächstes dran</h2></div><button className="text-button" type="button" onClick={() => onNavigate("documents")}>Alle ansehen <Icon name="arrow" /></button></header>{attention.length ? <div className="attention-list">{attention.map((item) => <button type="button" onClick={() => onNavigate(item.view, item.focus)} key={`${item.title}-${item.focus}`}><span className={`attention-icon attention-icon--${item.tone}`}><Icon name={item.icon} /></span><span><strong>{item.title}</strong><small>{item.detail}</small></span><Icon name="chevron" /></button>)}</div> : <Empty icon="check" title="Alles im grünen Bereich" copy="Aktuell sind keine dringenden Aufgaben offen." />}</article>
      <article className="panel appointments-panel"><header className="panel__head"><div><span className="eyebrow">Kommende Termine</span><h2>Was diese Woche passiert</h2></div><button className="round-add" type="button" onClick={() => onModal("event")} aria-label="Termin hinzufügen"><Icon name="plus" /></button></header><div className="timeline">{upcoming.slice(0, 4).map((event, index) => <button type="button" onClick={() => onNavigate("calendar", event.id)} className="timeline-item" key={event.id}><span className={`timeline-date timeline-date--${index % 4}`}><strong>{day(event.start).split(" ")[0]}</strong><small>{day(event.start).split(" ")[1]}</small></span><span className="timeline-copy"><strong>{event.title}</strong><small><Icon name="clock" />{new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit" }).format(new Date(event.start))}{event.location ? ` · ${event.location}` : ""}</small></span><Icon name="chevron" /></button>)}</div>{!upcoming.length ? <Empty icon="calendar" title="Noch keine Termine" copy="Plane den nächsten Elternabend oder Ausflug." /> : null}</article>
      <article className="panel occupancy-panel"><div><span className="eyebrow">Auslastung</span><h2>Gruppen im Blick</h2></div><div className="occupancy-chart"><div className="donut" style={{ "--value": `${Math.min(100, active / 9 * 100)}%` } as CSSProperties}><span><strong>{active}</strong><small>von 9</small></span></div><div className="legend">{Array.from(new Set(snapshot.children.map((child) => child.group))).map((group, index) => <span key={group}><i className={`legend-dot legend-dot--${index}`} />{group}<strong>{snapshot.children.filter((child) => child.group === group && child.status === "active").length}</strong></span>)}</div></div><button className="secondary-button secondary-button--wide" type="button" onClick={() => onNavigate("children")}>Kinderübersicht öffnen <Icon name="arrow" /></button></article>
    </section>
  </>;
}

function ParentOverview({ snapshot, onNavigate }: { snapshot: DashboardSnapshot; onNavigate: (view: View, focus?: string) => void }) {
  const child = snapshot.children[0];
  const upcoming = snapshot.events.filter((event) => new Date(event.start) >= new Date()).sort((a, b) => a.start.localeCompare(b.start));
  const photos = snapshot.photos.filter((photo) => photo.childId === child?.id).slice(0, 3);
  return <>
    <PageIntro view="overview" snapshot={snapshot} />
    {child ? <section className="parent-hero"><div className="parent-hero__content"><Avatar name={child.name} tone={1} large /><div><span className="eyebrow">Heute gut aufgehoben</span><h2>{child.name}</h2><p>{child.notesParentVisible || "Alle wichtigen Informationen rund um den Betreuungsalltag."}</p><button className="light-button" type="button" onClick={() => onNavigate("children", child.id)}>Angaben ansehen <Icon name="arrow" /></button></div></div><div className="parent-hero__facts"><span><small>Gruppe</small><strong>{child.group}</strong></span><span><small>Betreuung</small><strong>{child.careHoursPerWeek} Std./Woche</strong></span><span><small>Foto-Einwilligung</small><strong>{STATUS_LABELS[child.photoConsent]}</strong></span></div></section> : null}
    <section className="parent-grid">
      <article className="panel"><header className="panel__head"><div><span className="eyebrow">Nächste Termine</span><h2>Gut vorbereitet</h2></div><button className="text-button" type="button" onClick={() => onNavigate("calendar")}>Alle <Icon name="arrow" /></button></header><div className="parent-event-list">{upcoming.slice(0, 3).map((event) => <button key={event.id} type="button" onClick={() => onNavigate("calendar", event.id)}><span><strong>{day(event.start)}</strong><small>{new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit" }).format(new Date(event.start))}</small></span><div><strong>{event.title}</strong><small>{event.location || "9 Freunde"}</small></div><Icon name="chevron" /></button>)}</div></article>
      <article className="panel"><header className="panel__head"><div><span className="eyebrow">Fotomomente</span><h2>Neu aus dem Alltag</h2></div><button className="text-button" type="button" onClick={() => onNavigate("photos")}>Galerie <Icon name="arrow" /></button></header><div className="photo-preview">{photos.map((photo) => <button type="button" key={photo.id} onClick={() => onNavigate("photos")} style={{ backgroundImage: `url(${photo.previewUrl})` }} aria-label={photo.name} />)}</div>{!photos.length ? <Empty icon="photo" title="Noch keine Fotos" copy="Neue Momente erscheinen hier nach der Freigabe." /> : null}</article>
      <article className="panel parent-message"><span className="message-icon"><Icon name="mail" /></span><div><span className="eyebrow">Hinweis der Betreuung</span><h2>Sommerfest: Bitte Sonnenhut mitbringen</h2><p>Wir freuen uns auf einen schönen Nachmittag mit allen Familien.</p></div></article>
    </section>
  </>;
}

function ChildrenView({ snapshot, focusId, onAction, onAdd }: { snapshot: DashboardSnapshot; focusId?: string; onAction: (action: AppAction, message: string) => Promise<void>; onAdd: () => void }) {
  const [selectedId, setSelectedId] = useState(focusId || snapshot.children[0]?.id || "");
  const [filter, setFilter] = useState("all");
  const children = snapshot.children.filter((child) => filter === "all" || child.status === filter);
  const selected = snapshot.children.find((child) => child.id === selectedId) ?? children[0];
  const parent = snapshot.parents.find((item) => item.id === selected?.primaryParentId);
  const isAdmin = snapshot.session.role === "admin";
  return <>
    <PageIntro view="children" snapshot={snapshot} action={isAdmin ? <button className="primary-button" type="button" onClick={onAdd}><Icon name="plus" /> Kind aufnehmen</button> : undefined} />
    <div className={`children-layout ${!isAdmin ? "children-layout--parent" : ""}`}>
      {isAdmin ? <section className="panel children-list"><header><div className="segmented"><button type="button" className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>Alle</button><button type="button" className={filter === "active" ? "active" : ""} onClick={() => setFilter("active")}>Aktiv</button><button type="button" className={filter === "onboarding" ? "active" : ""} onClick={() => setFilter("onboarding")}>Startet bald</button></div><span>{children.length} Einträge</span></header><div className="child-rows">{children.map((child, index) => <button type="button" className={selected?.id === child.id ? "active" : ""} onClick={() => setSelectedId(child.id)} key={child.id}><Avatar name={child.name} tone={index} /><span><strong>{child.name}</strong><small>{child.group}</small></span><Pill value={child.status} /><Icon name="chevron" /></button>)}</div></section> : null}
      {selected ? <ChildDetail key={`${selected.id}-${selected.updatedAt}`} child={selected} parent={parent} isAdmin={isAdmin} onAction={onAction} /> : <Empty icon="children" title="Kein Kind ausgewählt" copy="Wähle links einen Datensatz aus." />}
    </div>
  </>;
}

function ChildDetail({ child, parent, isAdmin, onAction }: { child: Child; parent?: Parent; isAdmin: boolean; onAction: (action: AppAction, message: string) => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [pending, setPending] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setPending(true);
    const data = new FormData(event.currentTarget);
    const payload = {
      ...(isAdmin ? {
        name: String(data.get("name") ?? ""), group: String(data.get("group") ?? ""), status: String(data.get("status") ?? "active") as Child["status"],
        careHoursPerWeek: Number(data.get("hours") ?? 0), mealFeeCents: Math.round(Number(data.get("mealFee") ?? 0) * 100),
        photoConsent: String(data.get("photoConsent") ?? "missing") as Child["photoConsent"], downloadConsent: String(data.get("downloadConsent") ?? "missing") as Child["downloadConsent"],
        notesInternal: String(data.get("notesInternal") ?? "")
      } : {}),
      allergies: String(data.get("allergies") ?? ""), dietary: String(data.get("dietary") ?? ""), languagesAtHome: String(data.get("languages") ?? ""), notesParentVisible: String(data.get("notesParent") ?? "")
    };
    try { await onAction({ type: "update_child", childId: child.id, payload }, "Angaben wurden sicher gespeichert."); setEditing(false); }
    finally { setPending(false); }
  };
  return <section className="panel child-detail"><header className="child-detail__hero"><div className="child-person"><Avatar name={child.name} tone={2} large /><div><div className="name-line"><h2>{child.name}</h2><Pill value={child.status} /></div><p>{child.group} · seit {fullDate(child.careStart)}</p></div></div><button className="secondary-button" type="button" onClick={() => setEditing((value) => !value)}><Icon name={editing ? "close" : "edit"} />{editing ? "Abbrechen" : "Bearbeiten"}</button></header>
    {editing ? <form className="detail-form" onSubmit={submit}>
      {isAdmin ? <div className="form-grid"><label><span>Name</span><input name="name" defaultValue={child.name} required /></label><label><span>Gruppe</span><input name="group" defaultValue={child.group} required /></label><label><span>Status</span><select name="status" defaultValue={child.status}><option value="active">Aktiv</option><option value="onboarding">Eingewöhnung</option><option value="paused">Pausiert</option><option value="archived">Archiviert</option></select></label><label><span>Stunden / Woche</span><input name="hours" type="number" min="0" max="80" defaultValue={child.careHoursPerWeek} /></label><label><span>Verpflegung / Monat (€)</span><input name="mealFee" type="number" min="0" step="0.01" defaultValue={child.mealFeeCents / 100} /></label><label><span>Foto-Einwilligung</span><select name="photoConsent" defaultValue={child.photoConsent}><option value="granted">Erteilt</option><option value="restricted">Eingeschränkt</option><option value="missing">Fehlt</option></select></label><label><span>Download-Einwilligung</span><select name="downloadConsent" defaultValue={child.downloadConsent}><option value="granted">Erteilt</option><option value="restricted">Eingeschränkt</option><option value="missing">Fehlt</option></select></label></div> : null}
      <div className="form-grid"><label><span>Allergien</span><input name="allergies" defaultValue={child.allergies} /></label><label><span>Ernährung</span><input name="dietary" defaultValue={child.dietary} /></label><label><span>Sprachen zuhause</span><input name="languages" defaultValue={child.languagesAtHome} /></label></div>
      <label><span>Hinweis für Eltern</span><textarea name="notesParent" rows={3} defaultValue={child.notesParentVisible} /></label>
      {isAdmin ? <label><span>Interne Notiz · nicht für Eltern sichtbar</span><textarea name="notesInternal" rows={3} defaultValue={child.notesInternal} /></label> : null}
      <div className="form-actions"><button className="primary-button" type="submit" disabled={pending}><Icon name="check" />{pending ? "Speichert…" : "Änderungen speichern"}</button></div>
    </form> : <div className="detail-content">
      <div className="detail-section"><span className="section-icon section-icon--sun"><Icon name="profile" /></span><div><span className="eyebrow">Stammdaten</span><div className="fact-grid"><span><small>Geburtsdatum</small><strong>{fullDate(child.birthDate)}</strong></span><span><small>Betreuungsumfang</small><strong>{child.careHoursPerWeek} Std. / Woche</strong></span><span><small>Ernährung</small><strong>{child.dietary || "Keine Angabe"}</strong></span><span><small>Sprachen zuhause</small><strong>{child.languagesAtHome || "Keine Angabe"}</strong></span></div></div></div>
      <div className="detail-section"><span className="section-icon section-icon--mint"><Icon name="heart" /></span><div><span className="eyebrow">Gesundheit & Alltag</span><div className="fact-grid"><span><small>Allergien</small><strong>{child.allergies || "Keine bekannt"}</strong></span><span><small>Hinweis</small><strong>{child.notesParentVisible || "Keine Hinweise"}</strong></span></div></div></div>
      <div className="detail-section"><span className="section-icon section-icon--blue"><Icon name="profile" /></span><div><span className="eyebrow">Familienkontakt</span><div className="contact-card"><Avatar name={parent?.name ?? child.primaryParentEmail} tone={4} /><span><strong>{parent?.name ?? "Primärkontakt"}</strong><small>{parent?.email ?? child.primaryParentEmail}</small><small>{parent?.phone || "Keine Telefonnummer"}</small></span></div></div></div>
      <div className="consent-row"><span><small>Foto-Einwilligung</small><Pill value={child.photoConsent} /></span><span><small>Download-Freigabe</small><Pill value={child.downloadConsent} /></span><span><small>Drive-Ordner</small><Pill value={child.photoFolderId ? "granted" : "missing"} /></span></div>
    </div>}
  </section>;
}

function DocumentsView({ snapshot, focusId, onGenerate, onAction }: { snapshot: DashboardSnapshot; focusId?: string; onGenerate: () => void; onAction: (action: AppAction, message: string) => Promise<void> }) {
  const [type, setType] = useState<"all" | "invoice" | "contract">("all");
  const documents = snapshot.documents.filter((document) => type === "all" || document.type === type).sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const childName = (id: string) => snapshot.children.find((child) => child.id === id)?.name ?? "Unbekannt";
  return <>
    <PageIntro view="documents" snapshot={snapshot} action={snapshot.session.role === "admin" ? <button className="primary-button" type="button" onClick={onGenerate}><Icon name="plus" /> Neues Dokument</button> : undefined} />
    <section className="panel documents-panel"><header className="list-toolbar"><div className="segmented"><button type="button" className={type === "all" ? "active" : ""} onClick={() => setType("all")}>Alle</button><button type="button" className={type === "invoice" ? "active" : ""} onClick={() => setType("invoice")}>Abrechnungen</button><button type="button" className={type === "contract" ? "active" : ""} onClick={() => setType("contract")}>Verträge</button></div><span>{documents.length} Dokumente</span></header>
      <div className="document-table"><div className="document-table__head"><span>Dokument</span><span>Kind</span><span>Datum</span><span>Betrag</span><span>Status</span><span /></div>{documents.map((document) => <div className={`document-row ${focusId === document.id ? "document-row--focus" : ""}`} key={document.id}><span className={`doc-icon doc-icon--${document.type}`}><Icon name="document" /></span><span className="doc-title"><strong>{document.title}</strong><small>{document.number}</small></span><span>{childName(document.childId)}</span><span>{fullDate(document.createdAt)}</span><span>{document.type === "invoice" ? money(document.totalCents) : "—"}</span><span><Pill value={document.status} /></span><span className="row-actions"><a href={`/api/documents/${encodeURIComponent(document.id)}`} title="PDF herunterladen"><Icon name="download" /></a>{snapshot.session.role === "admin" ? <select aria-label="Dokumentstatus" value={document.status} onChange={(event) => void onAction({ type: "update_document_status", documentId: document.id, status: event.target.value as ManagedDocument["status"] }, "Dokumentstatus aktualisiert.")}><option value="draft">Entwurf</option><option value="sent">Versendet</option><option value="signed">Unterzeichnet</option><option value="paid">Bezahlt</option><option value="overdue">Überfällig</option></select> : null}</span></div>)}</div>
      {!documents.length ? <Empty icon="document" title="Noch keine Dokumente" copy="Erstelle eine Abrechnung oder einen Vertragsentwurf." /> : null}
    </section>
    <aside className="legal-note"><Icon name="shield" /><span><strong>Prüfung bleibt Pflicht</strong><small>Automatisch erstellte Verträge sind Entwürfe und müssen vor Versand fachlich und rechtlich geprüft werden.</small></span></aside>
  </>;
}

function CalendarView({ snapshot, focusId, onAdd, onEdit }: { snapshot: DashboardSnapshot; focusId?: string; onAdd: () => void; onEdit: (event: CalendarEvent) => void }) {
  const events = [...snapshot.events].sort((a, b) => a.start.localeCompare(b.start));
  const grouped = events.reduce<Record<string, CalendarEvent[]>>((acc, event) => { const key = new Intl.DateTimeFormat("de-DE", { month: "long", year: "numeric" }).format(new Date(event.start)); (acc[key] ??= []).push(event); return acc; }, {});
  return <>
    <PageIntro view="calendar" snapshot={snapshot} action={snapshot.session.role === "admin" ? <button className="primary-button" type="button" onClick={onAdd}><Icon name="plus" /> Termin planen</button> : undefined} />
    <section className="calendar-layout"><article className="panel calendar-list">{Object.entries(grouped).map(([month, monthEvents]) => <div className="month-group" key={month}><h2>{month}</h2>{monthEvents.map((event) => <div className={`calendar-event ${focusId === event.id ? "calendar-event--focus" : ""}`} key={event.id}><div className="calendar-event__date"><strong>{new Intl.DateTimeFormat("de-DE", { day: "2-digit" }).format(new Date(event.start))}</strong><small>{new Intl.DateTimeFormat("de-DE", { weekday: "short" }).format(new Date(event.start))}</small></div><div className="calendar-event__bar" /><div className="calendar-event__copy"><div><strong>{event.title}</strong><Pill value={event.audience === "all" ? "granted" : "restricted"} /></div><p>{event.description}</p><span><Icon name="clock" />{dateTime(event.start)} – {new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit" }).format(new Date(event.end))}</span>{event.location ? <span><Icon name="location" />{event.location}</span> : null}{snapshot.session.role === "admin" ? <button className="calendar-event__edit" type="button" onClick={() => onEdit(event)} aria-label={`Termin ${event.title} bearbeiten`}><Icon name="edit" /> Bearbeiten</button> : null}</div></div>)}</div>)}</article>
      <aside className="panel reminder-card"><span className="reminder-art"><Icon name="calendar" /></span><span className="eyebrow">Automatische Erinnerungen</span><h2>Niemand muss Termine im Kopf behalten.</h2><p>Google Calendar sendet Einladungen und Aktualisierungen an die ausgewählten Familien.</p><div className="integration-mini"><i className={snapshot.integrations.calendar ? "connected" : ""} /><span><strong>Google Calendar</strong><small>{snapshot.integrations.calendar ? "Verbunden" : "Im Demo-Modus simuliert"}</small></span></div></aside>
    </section>
  </>;
}

function PhotosView({ snapshot, onSnapshot, showToast }: { snapshot: DashboardSnapshot; onSnapshot: (snapshot: DashboardSnapshot) => void; showToast: (message: string, error?: boolean) => void }) {
  const [childId, setChildId] = useState(snapshot.children[0]?.id || "");
  const [uploading, setUploading] = useState(false);
  const photos = snapshot.photos.filter((photo) => photo.childId === childId);
  const child = snapshot.children.find((item) => item.id === childId);
  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; if (!file) return;
    setUploading(true);
    try { const form = new FormData(); form.set("childId", childId); form.set("file", file); const next = await readJson<DashboardSnapshot>(await fetch("/api/photos", { method: "POST", body: form })); onSnapshot(next); showToast("Foto wurde geschützt in Google Drive gespeichert."); }
    catch (caught) { showToast(caught instanceof Error ? caught.message : "Upload fehlgeschlagen.", true); }
    finally { setUploading(false); event.target.value = ""; }
  };
  return <>
    <PageIntro view="photos" snapshot={snapshot} action={snapshot.session.role === "admin" ? <label className={`primary-button upload-button ${uploading ? "disabled" : ""}`}><Icon name="upload" />{uploading ? "Lädt hoch…" : "Foto hochladen"}<input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => void upload(event)} disabled={uploading} /></label> : undefined} />
    <section className="photo-toolbar panel"><div><span className="eyebrow">Galerie für</span><select value={childId} onChange={(event) => setChildId(event.target.value)}>{snapshot.children.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div><div className="consent-summary"><Icon name="shield" /><span><strong>{child ? STATUS_LABELS[child.photoConsent] : "—"}</strong><small>Foto-Einwilligung</small></span></div><div className="consent-summary"><Icon name="download" /><span><strong>{child ? STATUS_LABELS[child.downloadConsent] : "—"}</strong><small>Download-Freigabe</small></span></div></section>
    {snapshot.integrations.mode === "demo" ? <div className="demo-banner"><Icon name="spark" /><span><strong>Behutsame Demo-Illustrationen</strong><small>Es werden keine echten Kinderfotos ausgeliefert. Im Google-Modus kommen Bilder ausschließlich aus privaten Kind-Ordnern.</small></span></div> : null}
    <section className="photo-grid">{photos.map((photo, index) => <article className={`photo-card photo-card--${index % 5}`} key={photo.id}><div style={{ backgroundImage: `url(${photo.previewUrl})` }} role="img" aria-label={photo.name} /><footer><span><strong>{photo.name}</strong><small>{fullDate(photo.createdAt)}</small></span><button type="button" aria-label="Mehr Optionen"><Icon name="more" /></button></footer></article>)}</section>
    {!photos.length ? <Empty icon="photo" title="Noch keine Fotomomente" copy="Sobald ein Bild freigegeben ist, erscheint es geschützt in dieser Galerie." /> : null}
  </>;
}

function ProfileView({ snapshot, onAction }: { snapshot: DashboardSnapshot; onAction: (action: AppAction, message: string) => Promise<void> }) {
  const parent = snapshot.parents[0];
  const [pending, setPending] = useState(false);
  if (!parent) return <><PageIntro view="profile" snapshot={snapshot} /><Empty icon="profile" title="Kein Profil gefunden" copy="Bitte wende dich an die Leitung." /></>;
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); setPending(true); const data = new FormData(event.currentTarget); try { await onAction({ type: "update_parent_profile", parentId: parent.id, payload: { phone: String(data.get("phone") ?? ""), phoneSecondary: String(data.get("phone2") ?? ""), address: String(data.get("address") ?? ""), preferredLanguage: String(data.get("language") ?? "de") as "de" | "en", emergencyContactName: String(data.get("emergencyName") ?? ""), emergencyContactPhone: String(data.get("emergencyPhone") ?? ""), notificationsOptIn: data.get("notifications") === "on" } }, "Profil wurde aktualisiert."); } finally { setPending(false); } };
  return <><PageIntro view="profile" snapshot={snapshot} /><section className="profile-layout"><form className="panel profile-form" onSubmit={submit}><header><Avatar name={parent.name} tone={4} large /><div><h2>{parent.name}</h2><p>{parent.email}</p></div></header><div className="form-grid"><label><span>Telefon</span><input name="phone" defaultValue={parent.phone} /></label><label><span>Telefon 2</span><input name="phone2" defaultValue={parent.phoneSecondary} /></label><label className="span-2"><span>Adresse</span><input name="address" defaultValue={parent.address} /></label><label><span>Bevorzugte Sprache</span><select name="language" defaultValue={parent.preferredLanguage}><option value="de">Deutsch</option><option value="en">English</option></select></label><label><span>Notfallkontakt</span><input name="emergencyName" defaultValue={parent.emergencyContactName} /></label><label><span>Telefon Notfallkontakt</span><input name="emergencyPhone" defaultValue={parent.emergencyContactPhone} /></label></div><label className="toggle-row"><input type="checkbox" name="notifications" defaultChecked={parent.notificationsOptIn} /><span><strong>Benachrichtigungen erhalten</strong><small>Terminupdates und wichtige Hinweise per E-Mail.</small></span></label><div className="form-actions"><button className="primary-button" type="submit" disabled={pending}><Icon name="check" />{pending ? "Speichert…" : "Profil speichern"}</button></div></form><aside className="panel profile-note"><span><Icon name="shield" /></span><h2>Du entscheidest über deine Daten.</h2><p>Änderungen sind nur für dich und die Leitung sichtbar. Interne Betreuungsnotizen werden Eltern niemals über diese Ansicht offengelegt.</p></aside></section></>;
}

function SettingsView({ snapshot }: { snapshot: DashboardSnapshot }) {
  const integrations = [{ name: "Google Sheets", copy: "Zentrale Stammdaten", active: snapshot.integrations.sheets, icon: "document" as IconName }, { name: "Google Drive", copy: "Private Foto-Ordner", active: snapshot.integrations.drive, icon: "drive" as IconName }, { name: "Google Calendar", copy: "Einladungen & Erinnerungen", active: snapshot.integrations.calendar, icon: "calendar" as IconName }, { name: "ChatGPT App", copy: "MCP Management-Tools", active: snapshot.integrations.mcp, icon: "spark" as IconName }];
  return <><PageIntro view="settings" snapshot={snapshot} /><section className="settings-grid"><article className="panel integrations-card"><header><span className="eyebrow">Verbindungen</span><h2>Google Workspace & ChatGPT</h2></header><div>{integrations.map((item) => <div className="integration-row" key={item.name}><span><Icon name={item.icon} /></span><div><strong>{item.name}</strong><small>{item.copy}</small></div><Pill value={item.active ? "granted" : "missing"} /></div>)}</div></article><article className="panel privacy-card"><span className="privacy-illustration"><Icon name="shield" /></span><span className="eyebrow">Privacy by default</span><h2>Fotos bleiben privat. Rollen bleiben klar.</h2><ul><li><Icon name="check" /> Eltern sehen nur ihre zugeordneten Kinder.</li><li><Icon name="check" /> Fotos werden nie öffentlich freigegeben.</li><li><Icon name="check" /> Interne Notizen bleiben intern.</li><li><Icon name="check" /> Tool-Aktionen sind nach Wirkung markiert.</li></ul></article><article className="panel mode-card"><div><span className={`mode-light ${snapshot.integrations.mode}`} /><span><strong>{snapshot.integrations.mode === "demo" ? "Fiktionaler Demo-Modus" : "Google Produktionsmodus"}</strong><small>{snapshot.integrations.mode === "demo" ? "Sicher zum Erkunden · nicht persistent" : "Konfiguration serverseitig aktiv"}</small></span></div><p>{snapshot.integrations.mode === "demo" ? "Alle Namen, Kontakte, Dokumente und Bilder dieser Vorschau sind erfunden. Für echte Daten müssen zuerst die Google-Ressourcen, Rollen und Secrets eingerichtet werden." : "Die Live-Verbindungen sind konfiguriert. Prüfe regelmäßig Freigaben, Einwilligungen und den Audit-Trail."}</p></article></section></>;
}

function CreateChildForm({ onAction, onClose }: { onAction: (action: AppAction, message: string) => Promise<void>; onClose: () => void }) {
  const [pending, setPending] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); setPending(true); const data = new FormData(event.currentTarget); try { await onAction({ type: "create_child", payload: { name: String(data.get("name")), birthDate: String(data.get("birthDate")), careStart: String(data.get("careStart")), group: String(data.get("group")), parentName: String(data.get("parentName")), parentEmail: String(data.get("parentEmail")), parentPhone: String(data.get("parentPhone") ?? ""), careHoursPerWeek: Number(data.get("hours") ?? 35), careFeeCents: 0, mealFeeCents: Math.round(Number(data.get("mealFee") ?? 0) * 100) } }, "Kind und Familienkontakt wurden angelegt."); onClose(); } finally { setPending(false); } };
  return <form className="modal-form" onSubmit={submit}><div className="form-grid"><label><span>Name des Kindes</span><input name="name" required autoFocus /></label><label><span>Geburtsdatum</span><input name="birthDate" type="date" required /></label><label><span>Betreuungsstart</span><input name="careStart" type="date" required /></label><label><span>Gruppe</span><select name="group" defaultValue="Sonnenkäfer"><option>Sonnenkäfer</option><option>Regenbogen</option></select></label><label><span>Stunden / Woche</span><input name="hours" type="number" min="1" max="80" defaultValue="35" /></label><label><span>Verpflegung / Monat (€)</span><input name="mealFee" type="number" min="0" step="0.01" defaultValue="85" /></label></div><hr /><span className="form-section-label">Primärer Familienkontakt</span><div className="form-grid"><label><span>Name</span><input name="parentName" required /></label><label><span>E-Mail</span><input name="parentEmail" type="email" required /></label><label><span>Telefon</span><input name="parentPhone" /></label></div><div className="modal-actions"><button className="secondary-button" type="button" onClick={onClose}>Abbrechen</button><button className="primary-button" type="submit" disabled={pending}><Icon name="plus" />{pending ? "Wird angelegt…" : "Kind aufnehmen"}</button></div></form>;
}

function CreateEventForm({ snapshot, event, onAction, onClose }: { snapshot: DashboardSnapshot; event?: CalendarEvent; onAction: (action: AppAction, message: string) => Promise<void>; onClose: () => void }) {
  const [pending, setPending] = useState(false); const [audience, setAudience] = useState<"all" | "child">(event?.audience ?? "all");
  const defaultStart = event ? new Date(event.start) : new Date(); if (!event) defaultStart.setDate(defaultStart.getDate() + 1); defaultStart.setMinutes(0, 0, 0);
  const localValue = (date: Date) => new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
  const submit = async (formEvent: FormEvent<HTMLFormElement>) => { formEvent.preventDefault(); setPending(true); const data = new FormData(formEvent.currentTarget); const childId = String(data.get("childId") ?? ""); const child = snapshot.children.find((item) => item.id === childId); const payload = { title: String(data.get("title")), description: String(data.get("description") ?? ""), start: new Date(String(data.get("start"))).toISOString(), end: new Date(String(data.get("end"))).toISOString(), location: String(data.get("location") ?? ""), audience, ...(audience === "child" && childId ? { childId } : {}), attendeeEmails: audience === "all" ? snapshot.parents.filter((parent) => parent.notificationsOptIn).map((parent) => parent.email) : child ? [child.primaryParentEmail] : [], remindersMinutes: [1440, 120] }; const action: AppAction = event ? { type: "update_event", eventId: event.id, payload } : { type: "create_event", payload }; try { await onAction(action, event ? "Termin wurde aktualisiert und Änderungen versendet." : "Termin wurde erstellt und Einladungen vorbereitet."); onClose(); } finally { setPending(false); } };
  const defaultEnd = event ? new Date(event.end) : new Date(defaultStart.getTime() + 60 * 60 * 1000);
  return <form className="modal-form" onSubmit={submit}><label><span>Titel</span><input name="title" required autoFocus placeholder="z. B. Elternabend" defaultValue={event?.title} /></label><div className="form-grid"><label><span>Beginn</span><input name="start" type="datetime-local" defaultValue={localValue(defaultStart)} required /></label><label><span>Ende</span><input name="end" type="datetime-local" defaultValue={localValue(defaultEnd)} required /></label><label><span>Ort</span><input name="location" defaultValue={event?.location || "9 Freunde"} /></label><label><span>Zielgruppe</span><select value={audience} onChange={(changeEvent) => setAudience(changeEvent.target.value as "all" | "child")}><option value="all">Alle Familien</option><option value="child">Einzelnes Kind</option></select></label>{audience === "child" ? <label><span>Kind</span><select name="childId" required defaultValue={event?.childId}>{snapshot.children.map((child) => <option key={child.id} value={child.id}>{child.name}</option>)}</select></label> : null}</div><label><span>Beschreibung</span><textarea name="description" rows={3} defaultValue={event?.description} /></label><p className="form-hint"><Icon name="mail" /> Empfänger:innen erhalten eine Google Calendar-Einladung und Erinnerungen 24 Stunden sowie 2 Stunden vorher.</p><div className="modal-actions"><button className="secondary-button" type="button" onClick={onClose}>Abbrechen</button><button className="primary-button" type="submit" disabled={pending}><Icon name="calendar" />{pending ? "Wird gespeichert…" : event ? "Änderungen versenden" : "Termin verbindlich erstellen"}</button></div></form>;
}

function CreateDocumentForm({ snapshot, onAction, onClose }: { snapshot: DashboardSnapshot; onAction: (action: AppAction, message: string) => Promise<void>; onClose: () => void }) {
  const [pending, setPending] = useState(false);
  const month = new Date().toISOString().slice(0, 7);
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); setPending(true); const data = new FormData(event.currentTarget); try { await onAction({ type: "generate_document", childId: String(data.get("childId")), documentType: String(data.get("documentType")) as "invoice" | "contract", period: String(data.get("period")) }, "Dokumententwurf wurde erstellt."); onClose(); } finally { setPending(false); } };
  return <form className="modal-form" onSubmit={submit}><div className="document-choice"><label><input type="radio" name="documentType" value="invoice" defaultChecked /><span><Icon name="document" /><strong>Monatsabrechnung</strong><small>Pauschalen automatisch einsetzen</small></span></label><label><input type="radio" name="documentType" value="contract" /><span><Icon name="shield" /><strong>Betreuungsvertrag</strong><small>Prüfbaren Entwurf vorbereiten</small></span></label></div><div className="form-grid"><label><span>Kind</span><select name="childId" required>{snapshot.children.map((child) => <option key={child.id} value={child.id}>{child.name}</option>)}</select></label><label><span>Zeitraum</span><input name="period" defaultValue={month} required /></label></div><p className="form-hint"><Icon name="shield" /> Personen- und Betragsdaten werden aus dem zentralen Datensatz übernommen. Vor Versand ist eine manuelle Prüfung erforderlich.</p><div className="modal-actions"><button className="secondary-button" type="button" onClick={onClose}>Abbrechen</button><button className="primary-button" type="submit" disabled={pending}><Icon name="spark" />{pending ? "Wird erstellt…" : "Entwurf erstellen"}</button></div></form>;
}

export function Portal() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<View>("overview");
  const [focusId, setFocusId] = useState<string>();
  const [modal, setModal] = useState<ModalName>(null);
  const [editingEvent, setEditingEvent] = useState<CalendarEvent>();
  const [menuOpen, setMenuOpen] = useState(false);
  const [toast, setToast] = useState<{ message: string; error: boolean } | null>(null);

  const showToast = useCallback((message: string, error = false) => setToast({ message, error }), []);
  useEffect(() => { if (!toast) return; const timer = window.setTimeout(() => setToast(null), 4200); return () => window.clearTimeout(timer); }, [toast]);

  const load = useCallback(async () => {
    try { setSnapshot(await readJson<DashboardSnapshot>(await fetch("/api/app", { cache: "no-store" }))); }
    catch { setSnapshot(null); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { const timer = window.setTimeout(() => { void load(); }, 0); return () => window.clearTimeout(timer); }, [load]);
  useEffect(() => { const timer = window.setTimeout(() => { const focus = new URLSearchParams(window.location.search).get("focus"); if (!focus) return; const [kind, id] = focus.split(":", 2); const target: Record<string, View> = { child: "children", parent: "children", document: "documents", event: "calendar" }; const nextView = kind ? target[kind] : undefined; if (nextView && id) { setView(nextView); setFocusId(id); } }, 0); return () => window.clearTimeout(timer); }, []);

  const login = async (email: string, password: string) => { await readJson(await fetch("/api/auth/login", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ email, password }) })); await load(); };
  const logout = async () => { await fetch("/api/auth/logout", { method: "POST" }); setSnapshot(null); setView("overview"); };
  const action = async (input: AppAction, message: string) => { try { const next = await readJson<DashboardSnapshot>(await fetch("/api/actions", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(input) })); setSnapshot(next); showToast(message); } catch (caught) { const messageText = caught instanceof Error ? caught.message : "Aktion fehlgeschlagen."; showToast(messageText, true); throw caught; } };
  const navigate = (next: View, focus?: string) => { setView(next); setFocusId(focus); window.scrollTo({ top: 0, behavior: "smooth" }); };

  if (loading) return <div className="app-loader"><Brand /><span className="loader-dots"><i /><i /><i /></span><p>Der Familienbereich wird vorbereitet…</p></div>;
  if (!snapshot) return <Login onLogin={login} />;

  return <div className="portal-shell">
    <Sidebar snapshot={snapshot} view={view} onView={(next) => navigate(next)} onLogout={() => void logout()} open={menuOpen} onClose={() => setMenuOpen(false)} />
    {menuOpen ? <button className="sidebar-scrim" type="button" aria-label="Navigation schließen" onClick={() => setMenuOpen(false)} /> : null}
    <div className="portal-main"><Topbar snapshot={snapshot} onMenu={() => setMenuOpen(true)} onNavigate={navigate} /><main className="page-content">
      {view === "overview" ? snapshot.session.role === "admin" ? <AdminOverview snapshot={snapshot} onModal={(name) => setModal(name)} onNavigate={navigate} /> : <ParentOverview snapshot={snapshot} onNavigate={navigate} /> : null}
      {view === "children" ? <ChildrenView key={focusId || "children"} snapshot={snapshot} focusId={focusId} onAction={action} onAdd={() => setModal("child")} /> : null}
      {view === "documents" ? <DocumentsView snapshot={snapshot} focusId={focusId} onGenerate={() => setModal("document")} onAction={action} /> : null}
      {view === "calendar" ? <CalendarView snapshot={snapshot} focusId={focusId} onAdd={() => setModal("event")} onEdit={setEditingEvent} /> : null}
      {view === "photos" ? <PhotosView snapshot={snapshot} onSnapshot={setSnapshot} showToast={showToast} /> : null}
      {view === "profile" ? <ProfileView snapshot={snapshot} onAction={action} /> : null}
      {view === "settings" ? <SettingsView snapshot={snapshot} /> : null}
    </main></div>
    {modal === "child" ? <Modal title="Neues Kind aufnehmen" eyebrow="Schritt für Schritt" onClose={() => setModal(null)}><CreateChildForm onAction={action} onClose={() => setModal(null)} /></Modal> : null}
    {modal === "event" ? <Modal title="Termin planen" eyebrow="Google Calendar" onClose={() => setModal(null)}><CreateEventForm snapshot={snapshot} onAction={action} onClose={() => setModal(null)} /></Modal> : null}
    {editingEvent ? <Modal title="Termin bearbeiten" eyebrow="Google Calendar Update" onClose={() => setEditingEvent(undefined)}><CreateEventForm snapshot={snapshot} event={editingEvent} onAction={action} onClose={() => setEditingEvent(undefined)} /></Modal> : null}
    {modal === "document" ? <Modal title="Dokument vorbereiten" eyebrow="Deterministische Vorlage" onClose={() => setModal(null)}><CreateDocumentForm snapshot={snapshot} onAction={action} onClose={() => setModal(null)} /></Modal> : null}
    {toast ? <div className={`toast ${toast.error ? "toast--error" : ""}`} role="status"><Icon name={toast.error ? "warning" : "check"} /><span>{toast.message}</span><button type="button" onClick={() => setToast(null)} aria-label="Hinweis schließen"><Icon name="close" /></button></div> : null}
  </div>;
}
