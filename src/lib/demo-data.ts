import { randomUUID } from "node:crypto";

import {
  type AppAction,
  type CalendarEvent,
  type Child,
  type DashboardSnapshot,
  type ManagedDocument,
  type Parent,
  type Photo,
  type UserSession,
  PARENT_CHILD_PATCH_FIELDS
} from "./contracts";

type DemoUser = {
  id: string;
  email: string;
  password: string;
  name: string;
  role: "admin" | "parent";
  parentId?: string;
  childIds: string[];
};

type DemoState = {
  children: Child[];
  parents: Parent[];
  events: CalendarEvent[];
  documents: ManagedDocument[];
  photos: Photo[];
};

const isoDay = (offset: number, hour = 9, minute = 0) => {
  const date = new Date();
  date.setDate(date.getDate() + offset);
  date.setHours(hour, minute, 0, 0);
  return date.toISOString();
};

const dateOnly = (offset: number) => isoDay(offset).slice(0, 10);
const updatedAt = new Date().toISOString();

export const DEMO_USERS: DemoUser[] = [
  {
    id: "user-admin",
    email: "leitung@demo.9freunde.de",
    password: "willkommen",
    name: "Mara Klein",
    role: "admin",
    childIds: []
  },
  {
    id: "user-parent",
    email: "eltern@demo.9freunde.de",
    password: "familie",
    name: "Samira Sommer",
    role: "parent",
    parentId: "parent-sommer",
    childIds: ["child-lina"]
  }
];

const seedState: DemoState = {
  parents: [
    {
      id: "parent-sommer",
      name: "Samira Sommer",
      email: "eltern@demo.9freunde.de",
      phone: "+49 170 0000001",
      phoneSecondary: "",
      address: "Musterweg 7, Düsseldorf",
      preferredLanguage: "de",
      emergencyContactName: "Alex Sommer",
      emergencyContactPhone: "+49 170 0000002",
      notificationsOptIn: true,
      childIds: ["child-lina"],
      updatedAt
    },
    {
      id: "parent-noah",
      name: "Jonas Becker",
      email: "jonas.becker@example.test",
      phone: "+49 170 0000003",
      phoneSecondary: "",
      address: "Beispielstraße 14, Düsseldorf",
      preferredLanguage: "de",
      emergencyContactName: "Mina Becker",
      emergencyContactPhone: "+49 170 0000004",
      notificationsOptIn: true,
      childIds: ["child-noah"],
      updatedAt
    },
    {
      id: "parent-emma",
      name: "Lea Winter",
      email: "lea.winter@example.test",
      phone: "+49 170 0000005",
      phoneSecondary: "",
      address: "Testallee 3, Düsseldorf",
      preferredLanguage: "en",
      emergencyContactName: "Robin Winter",
      emergencyContactPhone: "+49 170 0000006",
      notificationsOptIn: false,
      childIds: ["child-emma"],
      updatedAt
    },
    {
      id: "parent-milo",
      name: "Aylin Demir",
      email: "aylin.demir@example.test",
      phone: "+49 170 0000007",
      phoneSecondary: "",
      address: "Demoplatz 2, Düsseldorf",
      preferredLanguage: "de",
      emergencyContactName: "Can Demir",
      emergencyContactPhone: "+49 170 0000008",
      notificationsOptIn: true,
      childIds: ["child-milo"],
      updatedAt
    }
  ],
  children: [
    {
      id: "child-lina",
      name: "Lina Sommer",
      initials: "LS",
      birthDate: "2024-04-18",
      careStart: "2026-03-01",
      group: "Sonnenkäfer",
      status: "active",
      primaryParentId: "parent-sommer",
      primaryParentEmail: "eltern@demo.9freunde.de",
      allergies: "Keine bekannt",
      dietary: "Vegetarisch",
      languagesAtHome: "Deutsch, Englisch",
      careHoursPerWeek: 35,
      careFeeCents: 0,
      mealFeeCents: 8500,
      photoFolderId: "demo-lina",
      photoConsent: "granted",
      downloadConsent: "restricted",
      notesParentVisible: "Lina liebt Bilderbücher und Musik.",
      notesInternal: "Demo-only note",
      updatedAt
    },
    {
      id: "child-noah",
      name: "Noah Becker",
      initials: "NB",
      birthDate: "2024-08-02",
      careStart: "2026-05-01",
      group: "Sonnenkäfer",
      status: "active",
      primaryParentId: "parent-noah",
      primaryParentEmail: "jonas.becker@example.test",
      allergies: "Haselnuss",
      dietary: "Nussfrei",
      languagesAtHome: "Deutsch",
      careHoursPerWeek: 40,
      careFeeCents: 0,
      mealFeeCents: 9500,
      photoFolderId: "demo-noah",
      photoConsent: "granted",
      downloadConsent: "granted",
      notesParentVisible: "Bitte Sonnenhut mitgeben.",
      notesInternal: "Demo-only note",
      updatedAt
    },
    {
      id: "child-emma",
      name: "Emma Winter",
      initials: "EW",
      birthDate: "2024-11-12",
      careStart: dateOnly(18),
      group: "Regenbogen",
      status: "onboarding",
      primaryParentId: "parent-emma",
      primaryParentEmail: "lea.winter@example.test",
      allergies: "",
      dietary: "",
      languagesAtHome: "Englisch, Deutsch",
      careHoursPerWeek: 30,
      careFeeCents: 0,
      mealFeeCents: 7500,
      photoFolderId: "",
      photoConsent: "missing",
      downloadConsent: "missing",
      notesParentVisible: "Eingewöhnung startet in Kürze.",
      notesInternal: "Consent nachfassen",
      updatedAt
    },
    {
      id: "child-milo",
      name: "Milo Demir",
      initials: "MD",
      birthDate: "2023-12-22",
      careStart: "2025-08-01",
      group: "Regenbogen",
      status: "active",
      primaryParentId: "parent-milo",
      primaryParentEmail: "aylin.demir@example.test",
      allergies: "",
      dietary: "Halal",
      languagesAtHome: "Deutsch, Türkisch",
      careHoursPerWeek: 35,
      careFeeCents: 0,
      mealFeeCents: 8500,
      photoFolderId: "demo-milo",
      photoConsent: "restricted",
      downloadConsent: "restricted",
      notesParentVisible: "Mittagsschlaf meist gegen 12:30 Uhr.",
      notesInternal: "Demo-only note",
      updatedAt
    }
  ],
  events: [
    {
      id: "event-summer",
      title: "Sommerfest im Garten",
      description: "Gemeinsamer Nachmittag mit allen Familien.",
      start: isoDay(4, 15, 30),
      end: isoDay(4, 18, 0),
      location: "9 Freunde · Garten",
      audience: "all",
      attendeeEmails: [],
      remindersMinutes: [1440, 120],
      source: "demo"
    },
    {
      id: "event-lina",
      title: "Entwicklungsgespräch Lina",
      description: "Kurzer Austausch zum Kita-Alltag.",
      start: isoDay(8, 16, 0),
      end: isoDay(8, 16, 30),
      location: "9 Freunde",
      audience: "child",
      childId: "child-lina",
      attendeeEmails: ["eltern@demo.9freunde.de"],
      remindersMinutes: [1440],
      source: "demo"
    },
    {
      id: "event-closed",
      title: "Teamtag · Betreuung geschlossen",
      description: "Bitte alternative Betreuung einplanen.",
      start: isoDay(16, 8, 0),
      end: isoDay(16, 17, 0),
      location: "",
      audience: "all",
      attendeeEmails: [],
      remindersMinutes: [10080, 1440],
      source: "demo"
    }
  ],
  documents: [
    {
      id: "doc-invoice-lina",
      childId: "child-lina",
      type: "invoice",
      status: "sent",
      title: "Verpflegungspauschale Juli",
      number: "R-2026-071",
      period: "2026-07",
      careFeeCents: 0,
      mealFeeCents: 8500,
      totalCents: 8500,
      dueDate: dateOnly(10),
      createdAt: dateOnly(-2)
    },
    {
      id: "doc-invoice-noah",
      childId: "child-noah",
      type: "invoice",
      status: "overdue",
      title: "Verpflegungspauschale Juni",
      number: "R-2026-062",
      period: "2026-06",
      careFeeCents: 0,
      mealFeeCents: 9500,
      totalCents: 9500,
      dueDate: dateOnly(-7),
      createdAt: dateOnly(-30)
    },
    {
      id: "doc-contract-emma",
      childId: "child-emma",
      type: "contract",
      status: "draft",
      title: "Betreuungsvertrag Emma",
      number: "V-2026-014",
      period: "ab 2026",
      careFeeCents: 0,
      mealFeeCents: 7500,
      totalCents: 7500,
      dueDate: dateOnly(8),
      createdAt: dateOnly(-1)
    },
    {
      id: "doc-contract-lina",
      childId: "child-lina",
      type: "contract",
      status: "signed",
      title: "Betreuungsvertrag Lina",
      number: "V-2026-003",
      period: "ab 2026",
      careFeeCents: 0,
      mealFeeCents: 8500,
      totalCents: 8500,
      dueDate: "2026-02-15",
      createdAt: "2026-02-01"
    }
  ],
  photos: [
    ["photo-1", "child-lina", "Malen am Fenster", "/demo/gallery-1.svg", -1],
    ["photo-2", "child-lina", "Gartenentdeckung", "/demo/gallery-2.svg", -3],
    ["photo-3", "child-lina", "Bausteinwelt", "/demo/gallery-3.svg", -7],
    ["photo-4", "child-noah", "Sommerfarben", "/demo/gallery-4.svg", -2],
    ["photo-5", "child-milo", "Musikzeit", "/demo/gallery-5.svg", -4],
    ["photo-6", "child-noah", "Kleine Künstler", "/demo/gallery-6.svg", -8]
  ].map(([id, childId, name, previewUrl, offset]) => ({
    id: String(id),
    childId: String(childId),
    name: String(name),
    mimeType: "image/svg+xml",
    createdAt: isoDay(Number(offset), 12),
    previewUrl: String(previewUrl),
    source: "demo" as const
  }))
};

const globalDemo = globalThis as typeof globalThis & { __nineFriendsDemoState?: DemoState };
const state = () => {
  globalDemo.__nineFriendsDemoState ??= structuredClone(seedState);
  return globalDemo.__nineFriendsDemoState;
};

export function authenticateDemoUser(email: string, password: string): DemoUser | null {
  const normalized = email.trim().toLowerCase();
  return DEMO_USERS.find((user) => user.email === normalized && user.password === password) ?? null;
}

export function demoSession(user: DemoUser): UserSession {
  return {
    userId: user.id,
    email: user.email,
    name: user.name,
    role: user.role,
    ...(user.parentId ? { parentId: user.parentId } : {}),
    childIds: user.childIds,
    expiresAt: Math.floor(Date.now() / 1000) + 60 * 60 * 12
  };
}

export function getDemoSnapshot(session: UserSession): DashboardSnapshot {
  const current = state();
  const childIds = new Set(session.childIds);
  const children = session.role === "admin"
    ? current.children
    : current.children.filter((child) => childIds.has(child.id));
  const visibleChildIds = new Set(children.map((child) => child.id));
  const parents = session.role === "admin"
    ? current.parents
    : current.parents.filter((parent) => parent.id === session.parentId);

  return {
    session,
    children: structuredClone(children),
    parents: structuredClone(parents),
    events: structuredClone(
      current.events.filter((event) => event.audience === "all" || (event.childId && visibleChildIds.has(event.childId)))
    ),
    documents: structuredClone(
      current.documents.filter((document) => session.role === "admin" || visibleChildIds.has(document.childId))
    ),
    photos: structuredClone(
      current.photos.filter((photo) => session.role === "admin" || visibleChildIds.has(photo.childId))
    ),
    integrations: { mode: "demo", sheets: false, drive: false, calendar: false, mcp: true },
    generatedAt: new Date().toISOString()
  };
}

const assertAdmin = (session: UserSession) => {
  if (session.role !== "admin") throw new Error("This action is available to staff only.");
};

const assertChildAccess = (session: UserSession, childId: string) => {
  if (session.role !== "admin" && !session.childIds.includes(childId)) {
    throw new Error("You do not have access to this child record.");
  }
};

export function performDemoAction(session: UserSession, action: AppAction): DashboardSnapshot {
  const current = state();
  const now = new Date().toISOString();

  if (action.type === "create_child") {
    assertAdmin(session);
    const childId = `child-${randomUUID()}`;
    const parentId = `parent-${randomUUID()}`;
    const initials = action.payload.name
      .split(/\s+/u)
      .filter(Boolean)
      .map((part) => part[0])
      .join("")
      .slice(0, 3)
      .toUpperCase();
    current.parents.push({
      id: parentId,
      name: action.payload.parentName,
      email: action.payload.parentEmail.toLowerCase(),
      phone: action.payload.parentPhone,
      phoneSecondary: "",
      address: "",
      preferredLanguage: "de",
      emergencyContactName: "",
      emergencyContactPhone: "",
      notificationsOptIn: true,
      childIds: [childId],
      updatedAt: now
    });
    current.children.push({
      id: childId,
      name: action.payload.name,
      initials: initials || "?",
      birthDate: action.payload.birthDate,
      careStart: action.payload.careStart,
      group: action.payload.group,
      status: "onboarding",
      primaryParentId: parentId,
      primaryParentEmail: action.payload.parentEmail.toLowerCase(),
      allergies: "",
      dietary: "",
      languagesAtHome: "",
      careHoursPerWeek: action.payload.careHoursPerWeek,
      careFeeCents: action.payload.careFeeCents,
      mealFeeCents: action.payload.mealFeeCents,
      photoFolderId: "",
      photoConsent: "missing",
      downloadConsent: "missing",
      notesParentVisible: "",
      notesInternal: "",
      updatedAt: now
    });
  }

  if (action.type === "update_child") {
    assertChildAccess(session, action.childId);
    const child = current.children.find((item) => item.id === action.childId);
    if (!child) throw new Error("Child record not found.");
    const patch = { ...action.payload } as Record<string, unknown>;
    if (session.role === "parent") {
      for (const key of Object.keys(patch)) {
        if (!PARENT_CHILD_PATCH_FIELDS.has(key)) delete patch[key];
      }
    }
    Object.assign(child, patch, { updatedAt: now });
  }

  if (action.type === "update_parent_profile") {
    if (session.role !== "admin" && session.parentId !== action.parentId) {
      throw new Error("You can only update your own profile.");
    }
    const parent = current.parents.find((item) => item.id === action.parentId);
    if (!parent) throw new Error("Parent profile not found.");
    Object.assign(parent, action.payload, { updatedAt: now });
  }

  if (action.type === "create_event") {
    assertAdmin(session);
    if (new Date(action.payload.end) <= new Date(action.payload.start)) {
      throw new Error("The end time must be after the start time.");
    }
    current.events.push({
      id: `event-${randomUUID()}`,
      ...action.payload,
      ...(action.payload.audience === "child" && action.payload.childId
        ? { childId: action.payload.childId }
        : {}),
      source: "demo"
    });
  }

  if (action.type === "update_event") {
    assertAdmin(session);
    if (new Date(action.payload.end) <= new Date(action.payload.start)) {
      throw new Error("The end time must be after the start time.");
    }
    const event = current.events.find((item) => item.id === action.eventId);
    if (!event) throw new Error("Calendar event not found.");
    Object.assign(event, action.payload, {
      childId: action.payload.audience === "child" ? action.payload.childId : undefined
    });
  }

  if (action.type === "generate_document") {
    assertAdmin(session);
    const child = current.children.find((item) => item.id === action.childId);
    if (!child) throw new Error("Child record not found.");
    const sequence = current.documents.length + 1;
    const prefix = action.documentType === "invoice" ? "R" : "V";
    current.documents.push({
      id: `doc-${randomUUID()}`,
      childId: child.id,
      type: action.documentType,
      status: "draft",
      title: action.documentType === "invoice"
        ? `Monatsabrechnung ${action.period}`
        : `Betreuungsvertrag ${child.name}`,
      number: `${prefix}-${new Date().getFullYear()}-${String(sequence).padStart(3, "0")}`,
      period: action.period,
      careFeeCents: child.careFeeCents,
      mealFeeCents: child.mealFeeCents,
      totalCents: child.careFeeCents + child.mealFeeCents,
      dueDate: dateOnly(14),
      createdAt: now.slice(0, 10)
    });
  }

  if (action.type === "update_document_status") {
    assertAdmin(session);
    const document = current.documents.find((item) => item.id === action.documentId);
    if (!document) throw new Error("Document not found.");
    document.status = action.status;
  }

  return getDemoSnapshot(session);
}

export function resetDemoStateForTests() {
  globalDemo.__nineFriendsDemoState = structuredClone(seedState);
}
