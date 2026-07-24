import { createSign, pbkdf2Sync, randomUUID, timingSafeEqual } from "node:crypto";

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
} from "../contracts";

const WORKSPACE_GOOGLE_SCOPES = [
  "https://www.googleapis.com/auth/spreadsheets",
  "https://www.googleapis.com/auth/drive"
].join(" ");
const CALENDAR_GOOGLE_SCOPES = "https://www.googleapis.com/auth/calendar.events";

const TABS = {
  children: process.env.GOOGLE_CHILDREN_TAB || "children",
  parents: process.env.GOOGLE_PARENTS_TAB || "parents",
  users: process.env.GOOGLE_USERS_TAB || "users",
  documents: process.env.GOOGLE_DOCUMENTS_TAB || "documents"
} as const;

type SheetRow = Record<string, string>;
type TokenCache = { value: string; expiresAt: number };
type GoogleAuthContext = "workspace" | "calendar";
type GoogleTokenCache = Record<string, TokenCache>;
const globalGoogle = globalThis as typeof globalThis & {
  __nineFriendsGoogleTokens?: GoogleTokenCache;
};

export type GoogleIntegrationCheckCode =
  | "ok"
  | "not_configured"
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "quota"
  | "schema"
  | "unavailable"
  | "unknown";

export type GoogleIntegrationCheck = {
  ok: boolean;
  code: GoogleIntegrationCheckCode;
};

export type GoogleIntegrationHealth = {
  checkedAt: string;
  sheets: GoogleIntegrationCheck;
  drive: GoogleIntegrationCheck;
  calendar: GoogleIntegrationCheck;
};

const REQUIRED_SHEET_HEADERS: Record<keyof typeof TABS, readonly string[]> = {
  children: [
    "child_id", "name", "birthdate", "start_date", "group", "status",
    "primary_parent_id", "parent_email", "allergies", "dietary",
    "languages_at_home", "care_hours_per_week", "care_fee_cents",
    "meal_fee_cents", "folder_id", "photo_consent", "download_consent",
    "notes_parent_visible", "notes_internal", "updated_at"
  ],
  parents: [
    "parent_id", "name", "email", "phone", "phone2", "address",
    "preferred_language", "emergency_contact_name", "emergency_contact_phone",
    "notifications_opt_in", "child_ids", "updated_at"
  ],
  users: [
    "user_id", "email", "name", "role", "parent_id", "child_ids",
    "password_salt", "password_hash", "active"
  ],
  documents: [
    "document_id", "child_id", "type", "status", "title", "number", "period",
    "care_fee_cents", "meal_fee_cents", "total_cents", "due_date",
    "created_at", "drive_file_id"
  ]
};

class GoogleWorkspaceRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly reason: string | undefined,
    message: string
  ) {
    super(message);
  }
}

class GoogleIntegrationSchemaError extends Error {}

const required = (name: string) => {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required server configuration: ${name}`);
  return value;
};

export function googleConfigurationStatus() {
  const hasCredentials = Boolean(
    process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL?.trim() &&
    process.env.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY?.trim()
  );
  return {
    sheets: hasCredentials && Boolean(process.env.GOOGLE_SHEET_ID?.trim()),
    drive: hasCredentials && Boolean(process.env.GOOGLE_DRIVE_PHOTOS_FOLDER_ID?.trim()),
    calendar: hasCredentials &&
      Boolean(process.env.GOOGLE_CALENDAR_ID?.trim()) &&
      Boolean(process.env.GOOGLE_CALENDAR_IMPERSONATED_USER_EMAIL?.trim())
  };
}

const base64url = (value: string) => Buffer.from(value).toString("base64url");

function authConfiguration(context: GoogleAuthContext) {
  const email = required("GOOGLE_SERVICE_ACCOUNT_EMAIL");
  if (context === "calendar") {
    return {
      email,
      scopes: CALENDAR_GOOGLE_SCOPES,
      subject: required("GOOGLE_CALENDAR_IMPERSONATED_USER_EMAIL")
    };
  }
  return { email, scopes: WORKSPACE_GOOGLE_SCOPES, subject: undefined };
}

export function buildGoogleJwtClaims(
  context: GoogleAuthContext,
  now = Math.floor(Date.now() / 1000)
) {
  const { email, scopes, subject } = authConfiguration(context);
  return {
    iss: email,
    scope: scopes,
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
    ...(subject ? { sub: subject } : {})
  };
}

function tokenCacheKey(context: GoogleAuthContext): string {
  const { email, scopes, subject } = authConfiguration(context);
  return [context, email, subject ?? "-", scopes].join("|");
}

export function resetGoogleTokenCacheForTests() {
  delete globalGoogle.__nineFriendsGoogleTokens;
}

function googleErrorReason(payload: unknown): string | undefined {
  if (!payload || typeof payload !== "object") return undefined;
  const error = (payload as { error?: unknown }).error;
  if (typeof error === "string") return error;
  if (!error || typeof error !== "object") return undefined;
  const errors = (error as { errors?: unknown }).errors;
  if (!Array.isArray(errors)) return undefined;
  const reason = (errors[0] as { reason?: unknown } | undefined)?.reason;
  return typeof reason === "string" ? reason : undefined;
}

export function classifyGoogleHttpError(
  status: number,
  reason?: string
): GoogleIntegrationCheckCode {
  if (
    status === 400 &&
    /invalid_grant|unauthorized_client|invalid_client/i.test(reason ?? "")
  ) {
    return "unauthorized";
  }
  if (status === 401) return "unauthorized";
  if (status === 403) {
    if (/quota|rateLimit/i.test(reason ?? "")) return "quota";
    return "forbidden";
  }
  if (status === 404) return "not_found";
  if (status === 429) return "quota";
  if (status >= 500) return "unavailable";
  return "unknown";
}

export function classifyGoogleIntegrationError(error: unknown): GoogleIntegrationCheckCode {
  if (error instanceof GoogleIntegrationSchemaError) return "schema";
  if (!(error instanceof GoogleWorkspaceRequestError)) return "unknown";
  return classifyGoogleHttpError(error.status, error.reason);
}

export async function getGoogleAccessToken(context: GoogleAuthContext): Promise<string> {
  const cacheKey = tokenCacheKey(context);
  const cached = globalGoogle.__nineFriendsGoogleTokens?.[cacheKey];
  if (cached && cached.expiresAt > Date.now() + 60_000) return cached.value;

  const privateKey = required("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY").replace(/\\n/g, "\n");
  const header = base64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claim = base64url(JSON.stringify(buildGoogleJwtClaims(context)));
  const unsigned = `${header}.${claim}`;
  const signer = createSign("RSA-SHA256");
  signer.update(unsigned);
  signer.end();
  const assertion = `${unsigned}.${signer.sign(privateKey).toString("base64url")}`;

  const response = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion
    })
  });
  const payload = await response.json().catch(() => ({})) as {
    access_token?: string;
    expires_in?: number;
  };
  if (!response.ok) {
    throw new GoogleWorkspaceRequestError(
      response.status,
      googleErrorReason(payload),
      `Google authentication failed (${response.status}).`
    );
  }
  if (!payload.access_token) {
    throw new GoogleWorkspaceRequestError(
      502,
      undefined,
      "Google authentication returned no access token."
    );
  }
  const tokens = globalGoogle.__nineFriendsGoogleTokens ?? {};
  tokens[cacheKey] = {
    value: payload.access_token,
    expiresAt: Date.now() + (payload.expires_in ?? 3600) * 1000
  };
  globalGoogle.__nineFriendsGoogleTokens = tokens;
  return payload.access_token;
}

async function googleFetch(
  url: string,
  init: RequestInit = {},
  context: GoogleAuthContext = "workspace"
): Promise<Response> {
  const token = await getGoogleAccessToken(context);
  const headers = new Headers(init.headers);
  headers.set("authorization", `Bearer ${token}`);
  const response = await fetch(url, { ...init, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new GoogleWorkspaceRequestError(
      response.status,
      googleErrorReason(payload),
      `Google Workspace request failed (${response.status}).`
    );
  }
  return response;
}

const sheetId = () => required("GOOGLE_SHEET_ID");
const encodeRange = (tab: string, range = "A:ZZ") => encodeURIComponent(`'${tab.replaceAll("'", "''")}'!${range}`);

async function getSheetHeader(tab: string): Promise<string[]> {
  const response = await googleFetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${sheetId()}/values/${encodeRange(tab, "1:1")}`
  );
  const payload = await response.json() as { values?: unknown[][] };
  return (payload.values?.[0] ?? []).map((value) => String(value).trim()).filter(Boolean);
}

async function checkSheetsIntegration() {
  for (const [tabKey, tabName] of Object.entries(TABS) as Array<[keyof typeof TABS, string]>) {
    const header = await getSheetHeader(tabName);
    const missing = REQUIRED_SHEET_HEADERS[tabKey].filter((field) => !header.includes(field));
    if (missing.length > 0) throw new GoogleIntegrationSchemaError("Required Sheet schema is incomplete.");
  }
}

async function checkDriveIntegration() {
  const folderId = encodeURIComponent(required("GOOGLE_DRIVE_PHOTOS_FOLDER_ID"));
  const url = new URL(`https://www.googleapis.com/drive/v3/files/${folderId}`);
  url.searchParams.set("supportsAllDrives", "true");
  url.searchParams.set("fields", "mimeType,trashed,capabilities(canAddChildren)");
  const response = await googleFetch(url.toString());
  const payload = await response.json() as {
    mimeType?: string;
    trashed?: boolean;
    capabilities?: { canAddChildren?: boolean };
  };
  if (
    payload.mimeType !== "application/vnd.google-apps.folder" ||
    payload.trashed ||
    payload.capabilities?.canAddChildren !== true
  ) {
    throw new GoogleWorkspaceRequestError(403, "insufficientFilePermissions", "Drive root is not writable.");
  }
}

async function checkCalendarIntegration() {
  const calendarId = encodeURIComponent(required("GOOGLE_CALENDAR_ID"));
  const url = new URL(`https://www.googleapis.com/calendar/v3/calendars/${calendarId}/events`);
  url.searchParams.set("maxResults", "1");
  url.searchParams.set("singleEvents", "true");
  url.searchParams.set("timeMin", new Date().toISOString());
  await googleFetch(url.toString(), {}, "calendar");
}

async function runIntegrationCheck(
  configured: boolean,
  check: () => Promise<void>
): Promise<GoogleIntegrationCheck> {
  if (!configured) return { ok: false, code: "not_configured" };
  try {
    await check();
    return { ok: true, code: "ok" };
  } catch (error) {
    return { ok: false, code: classifyGoogleIntegrationError(error) };
  }
}

export async function checkGoogleIntegrations(): Promise<GoogleIntegrationHealth> {
  const configuration = googleConfigurationStatus();
  const [sheets, drive, calendar] = await Promise.all([
    runIntegrationCheck(configuration.sheets, checkSheetsIntegration),
    runIntegrationCheck(configuration.drive, checkDriveIntegration),
    runIntegrationCheck(configuration.calendar, checkCalendarIntegration)
  ]);
  return {
    checkedAt: new Date().toISOString(),
    sheets,
    drive,
    calendar
  };
}

const columnName = (index: number) => {
  let result = "";
  let current = index + 1;
  while (current > 0) {
    current -= 1;
    result = String.fromCharCode(65 + (current % 26)) + result;
    current = Math.floor(current / 26);
  }
  return result;
};

async function getRows(tab: string): Promise<SheetRow[]> {
  const response = await googleFetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${sheetId()}/values/${encodeRange(tab)}`
  );
  const payload = await response.json() as { values?: unknown[][] };
  const values = payload.values ?? [];
  const header = (values[0] ?? []).map((value) => String(value).trim());
  return values.slice(1).map((row) => Object.fromEntries(
    header.map((key, index) => [key, String(row[index] ?? "")])
  ));
}

async function ensureHeader(tab: string, fields: string[]): Promise<string[]> {
  let existing: string[] = [];
  try {
    const response = await googleFetch(
      `https://sheets.googleapis.com/v4/spreadsheets/${sheetId()}/values/${encodeRange(tab, "1:1")}`
    );
    const payload = await response.json() as { values?: unknown[][] };
    existing = (payload.values?.[0] ?? []).map((value) => String(value).trim()).filter(Boolean);
  } catch {
    throw new Error(`Required Google Sheets tab "${tab}" is missing.`);
  }
  const merged = [...existing];
  for (const field of fields) if (!merged.includes(field)) merged.push(field);
  if (merged.length !== existing.length || existing.length === 0) {
    await googleFetch(
      `https://sheets.googleapis.com/v4/spreadsheets/${sheetId()}/values/${encodeRange(tab, `A1:${columnName(merged.length - 1)}1`)}?valueInputOption=RAW`,
      {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ values: [merged] })
      }
    );
  }
  return merged;
}

async function appendRow(tab: string, row: SheetRow) {
  const header = await ensureHeader(tab, Object.keys(row));
  await googleFetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${sheetId()}/values/${encodeRange(tab, "A:ZZ")}:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ values: [header.map((key) => row[key] ?? "")] })
    }
  );
}

async function updateRow(tab: string, idField: string, id: string, patch: SheetRow) {
  const response = await googleFetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${sheetId()}/values/${encodeRange(tab)}`
  );
  const payload = await response.json() as { values?: unknown[][] };
  const values = payload.values ?? [];
  const currentHeader = (values[0] ?? []).map((value) => String(value).trim());
  const header = await ensureHeader(tab, Object.keys(patch));
  const idIndex = currentHeader.indexOf(idField);
  const rowIndex = values.findIndex((row, index) => index > 0 && String(row[idIndex] ?? "") === id);
  if (rowIndex < 1) throw new Error(`Record not found in ${tab}.`);
  const existing = Object.fromEntries(header.map((key, index) => [key, String(values[rowIndex]?.[index] ?? "")]));
  const next = { ...existing, ...patch };
  await googleFetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${sheetId()}/values/${encodeRange(tab, `A${rowIndex + 1}:${columnName(header.length - 1)}${rowIndex + 1}`)}?valueInputOption=RAW`,
    {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ values: [header.map((key) => next[key] ?? "")] })
    }
  );
}

const bool = (value: string, fallback = false) => {
  if (!value) return fallback;
  return ["true", "1", "yes", "ja", "on"].includes(value.trim().toLowerCase());
};
const int = (value: string) => Number.isFinite(Number(value)) ? Math.trunc(Number(value)) : 0;
const consent = (value: string): "granted" | "restricted" | "missing" => {
  if (["granted", "unpixelated", "true", "yes", "ja"].includes(value.toLowerCase())) return "granted";
  if (["restricted", "pixelated"].includes(value.toLowerCase())) return "restricted";
  return "missing";
};
const status = (value: string): Child["status"] =>
  ["active", "onboarding", "paused", "archived"].includes(value) ? value as Child["status"] : "active";
const initials = (name: string) => name.split(/\s+/u).filter(Boolean).map((part) => part[0]).join("").slice(0, 3).toUpperCase() || "?";

const parentFromRow = (row: SheetRow): Parent => ({
  id: row.parent_id || `parent-${randomUUID()}`,
  name: row.name || "Unbenannter Kontakt",
  email: row.email || "missing@example.invalid",
  phone: row.phone || "",
  phoneSecondary: row.phone2 || "",
  address: row.address || "",
  preferredLanguage: row.preferred_language === "en" ? "en" : "de",
  emergencyContactName: row.emergency_contact_name || "",
  emergencyContactPhone: row.emergency_contact_phone || "",
  notificationsOptIn: bool(row.notifications_opt_in || "", true),
  childIds: (row.child_ids || "").split(",").map((item) => item.trim()).filter(Boolean),
  updatedAt: row.updated_at || new Date().toISOString()
});

const childFromRow = (row: SheetRow, parents: Parent[]): Child => {
  const parent = parents.find((item) => item.email.toLowerCase() === row.parent_email?.toLowerCase());
  return {
    id: row.child_id || `child-${randomUUID()}`,
    name: row.name || "Unbenanntes Kind",
    initials: initials(row.name || "?"),
    birthDate: row.birthdate || "",
    careStart: row.start_date || "",
    group: row.group || "Ohne Gruppe",
    status: status(row.status || "active"),
    primaryParentId: row.primary_parent_id || parent?.id || "",
    primaryParentEmail: row.parent_email || parent?.email || "missing@example.invalid",
    allergies: row.allergies || "",
    dietary: row.dietary || "",
    languagesAtHome: row.languages_at_home || "",
    careHoursPerWeek: int(row.care_hours_per_week || ""),
    careFeeCents: int(row.care_fee_cents || ""),
    mealFeeCents: int(row.meal_fee_cents || ""),
    photoFolderId: row.folder_id || "",
    photoConsent: consent(row.photo_consent || ""),
    downloadConsent: consent(row.download_consent || ""),
    notesParentVisible: row.notes_parent_visible || "",
    notesInternal: row.notes_internal || "",
    updatedAt: row.updated_at || new Date().toISOString()
  };
};

const documentStatus = (value: string): ManagedDocument["status"] =>
  ["draft", "sent", "signed", "paid", "overdue"].includes(value)
    ? value as ManagedDocument["status"]
    : "draft";

const documentFromRow = (row: SheetRow): ManagedDocument => ({
  id: row.document_id || `doc-${randomUUID()}`,
  childId: row.child_id || "",
  type: row.type === "contract" ? "contract" : "invoice",
  status: documentStatus(row.status || ""),
  title: row.title || "Dokument",
  number: row.number || "ENTWURF",
  period: row.period || "",
  careFeeCents: int(row.care_fee_cents || ""),
  mealFeeCents: int(row.meal_fee_cents || ""),
  totalCents: int(row.total_cents || ""),
  dueDate: row.due_date || "",
  createdAt: row.created_at || new Date().toISOString().slice(0, 10),
  ...(row.drive_file_id ? { driveFileId: row.drive_file_id } : {})
});

async function listCalendarEvents(): Promise<CalendarEvent[]> {
  if (!googleConfigurationStatus().calendar) return [];
  const calendarId = encodeURIComponent(required("GOOGLE_CALENDAR_ID"));
  const timeMin = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
  const timeMax = new Date(Date.now() + 180 * 24 * 60 * 60 * 1000).toISOString();
  const url = new URL(`https://www.googleapis.com/calendar/v3/calendars/${calendarId}/events`);
  url.searchParams.set("singleEvents", "true");
  url.searchParams.set("orderBy", "startTime");
  url.searchParams.set("timeMin", timeMin);
  url.searchParams.set("timeMax", timeMax);
  url.searchParams.set("maxResults", "100");
  const response = await googleFetch(url.toString(), {}, "calendar");
  const payload = await response.json() as { items?: Array<Record<string, unknown>> };
  return (payload.items ?? []).flatMap((item) => {
    const start = item.start as { dateTime?: string; date?: string } | undefined;
    const end = item.end as { dateTime?: string; date?: string } | undefined;
    const startValue = start?.dateTime ?? (start?.date ? `${start.date}T00:00:00.000Z` : "");
    const endValue = end?.dateTime ?? (end?.date ? `${end.date}T23:59:59.000Z` : "");
    if (!startValue || !endValue) return [];
    const privateProps = (item.extendedProperties as { private?: Record<string, string> } | undefined)?.private ?? {};
    const audience = privateProps.audience === "child" ? "child" as const : "all" as const;
    const attendees = Array.isArray(item.attendees)
      ? item.attendees.flatMap((attendee) => {
        const email = (attendee as { email?: string }).email;
        return email ? [email] : [];
      })
      : [];
    return [{
      id: String(item.id ?? randomUUID()),
      title: String(item.summary ?? "Termin"),
      description: String(item.description ?? ""),
      start: new Date(startValue).toISOString(),
      end: new Date(endValue).toISOString(),
      location: String(item.location ?? ""),
      audience,
      ...(audience === "child" && privateProps.childId ? { childId: privateProps.childId } : {}),
      attendeeEmails: attendees,
      remindersMinutes: [1440],
      source: "google" as const
    }];
  });
}

async function createCalendarEvent(input: Extract<AppAction, { type: "create_event" }>["payload"]) {
  const calendarId = encodeURIComponent(required("GOOGLE_CALENDAR_ID"));
  await googleFetch(`https://www.googleapis.com/calendar/v3/calendars/${calendarId}/events?sendUpdates=all`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      summary: input.title,
      description: input.description,
      location: input.location,
      start: { dateTime: input.start },
      end: { dateTime: input.end },
      attendees: input.attendeeEmails.map((email) => ({ email })),
      reminders: {
        useDefault: false,
        overrides: input.remindersMinutes.map((minutes) => ({ method: "email", minutes }))
      },
      extendedProperties: {
        private: {
          audience: input.audience,
          ...(input.childId ? { childId: input.childId } : {})
        }
      }
    })
  }, "calendar");
}

async function updateCalendarEvent(
  eventId: string,
  input: Extract<AppAction, { type: "update_event" }>["payload"]
) {
  const calendarId = encodeURIComponent(required("GOOGLE_CALENDAR_ID"));
  await googleFetch(`https://www.googleapis.com/calendar/v3/calendars/${calendarId}/events/${encodeURIComponent(eventId)}?sendUpdates=all`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      summary: input.title,
      description: input.description,
      location: input.location,
      start: { dateTime: input.start },
      end: { dateTime: input.end },
      attendees: input.attendeeEmails.map((email) => ({ email })),
      reminders: {
        useDefault: false,
        overrides: input.remindersMinutes.map((minutes) => ({ method: "email", minutes }))
      },
      extendedProperties: {
        private: {
          audience: input.audience,
          ...(input.childId ? { childId: input.childId } : {})
        }
      }
    })
  }, "calendar");
}

async function createDriveFolder(childId: string): Promise<string> {
  const parentId = required("GOOGLE_DRIVE_PHOTOS_FOLDER_ID");
  const response = await googleFetch("https://www.googleapis.com/drive/v3/files?supportsAllDrives=true&fields=id", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      name: `child_${childId}`,
      mimeType: "application/vnd.google-apps.folder",
      parents: [parentId]
    })
  });
  const payload = await response.json() as { id?: string };
  if (!payload.id) throw new Error("Google Drive did not return the new child folder ID.");
  return payload.id;
}

async function listPhotosForChildren(children: Child[]): Promise<Photo[]> {
  if (!googleConfigurationStatus().drive) return [];
  const batches = await Promise.all(children.filter((child) => child.photoFolderId).map(async (child) => {
    const query = `'${child.photoFolderId.replaceAll("'", "\\'")}' in parents and trashed = false`;
    const url = new URL("https://www.googleapis.com/drive/v3/files");
    url.searchParams.set("q", query);
    url.searchParams.set("fields", "files(id,name,mimeType,createdTime)");
    url.searchParams.set("orderBy", "createdTime desc");
    url.searchParams.set("pageSize", "50");
    url.searchParams.set("supportsAllDrives", "true");
    url.searchParams.set("includeItemsFromAllDrives", "true");
    const response = await googleFetch(url.toString());
    const payload = await response.json() as { files?: Array<{ id: string; name: string; mimeType: string; createdTime?: string }> };
    return (payload.files ?? [])
      .filter((file) => ["image/jpeg", "image/png", "image/webp"].includes(file.mimeType))
      .map((file) => ({
        id: file.id,
        childId: child.id,
        name: file.name,
        mimeType: file.mimeType,
        createdAt: file.createdTime ?? new Date().toISOString(),
        previewUrl: `/api/photos/${encodeURIComponent(file.id)}`,
        source: "google" as const
      }));
  }));
  return batches.flat();
}

export async function authenticateGoogleUser(email: string, password: string): Promise<UserSession | null> {
  const normalized = email.trim().toLowerCase();
  const users = await getRows(TABS.users);
  const row = users.find((item) => item.email?.trim().toLowerCase() === normalized && item.active !== "false");
  if (!row?.password_hash || !row.password_salt) return null;
  const actual = pbkdf2Sync(password, row.password_salt, 210_000, 32, "sha256");
  const expected = Buffer.from(row.password_hash, "base64url");
  if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) return null;
  const role = row.role === "admin" ? "admin" as const : "parent" as const;
  return {
    userId: row.user_id || normalized,
    email: normalized,
    name: row.name || normalized.split("@")[0] || "Nutzer",
    role,
    ...(row.parent_id ? { parentId: row.parent_id } : {}),
    childIds: (row.child_ids || "").split(",").map((item) => item.trim()).filter(Boolean),
    expiresAt: Math.floor(Date.now() / 1000) + 60 * 60 * 12
  };
}

export async function getGoogleSnapshot(session: UserSession): Promise<DashboardSnapshot> {
  const [parentRows, childRows, documentRows, events] = await Promise.all([
    getRows(TABS.parents),
    getRows(TABS.children),
    getRows(TABS.documents),
    listCalendarEvents()
  ]);
  const allParents = parentRows.map(parentFromRow);
  const allChildren = childRows.map((row) => childFromRow(row, allParents));
  const allowedIds = new Set(session.childIds);
  const children = session.role === "admin" ? allChildren : allChildren.filter((child) => allowedIds.has(child.id));
  const visibleIds = new Set(children.map((child) => child.id));
  const parents = session.role === "admin" ? allParents : allParents.filter((parent) => parent.id === session.parentId);
  const photos = await listPhotosForChildren(children);
  const configuration = googleConfigurationStatus();
  return {
    session,
    children,
    parents,
    events: events.filter((event) => event.audience === "all" || (event.childId && visibleIds.has(event.childId))),
    documents: documentRows.map(documentFromRow).filter((document) => session.role === "admin" || visibleIds.has(document.childId)),
    photos,
    integrations: { mode: "google", ...configuration, mcp: Boolean(process.env.MCP_BEARER_TOKEN?.trim()) },
    generatedAt: new Date().toISOString()
  };
}

const childPatchToRow = (patch: Record<string, unknown>): SheetRow => {
  const mapping: Record<string, string> = {
    name: "name",
    birthDate: "birthdate",
    careStart: "start_date",
    group: "group",
    status: "status",
    allergies: "allergies",
    dietary: "dietary",
    languagesAtHome: "languages_at_home",
    careHoursPerWeek: "care_hours_per_week",
    careFeeCents: "care_fee_cents",
    mealFeeCents: "meal_fee_cents",
    photoConsent: "photo_consent",
    downloadConsent: "download_consent",
    notesParentVisible: "notes_parent_visible",
    notesInternal: "notes_internal"
  };
  return Object.fromEntries(Object.entries(patch).flatMap(([key, value]) => {
    const target = mapping[key];
    return target ? [[target, String(value ?? "")]] : [];
  }));
};

export async function performGoogleAction(session: UserSession, action: AppAction): Promise<DashboardSnapshot> {
  const now = new Date().toISOString();
  if (action.type === "create_child") {
    if (session.role !== "admin") throw new Error("This action is available to staff only.");
    const childId = `child-${randomUUID()}`;
    const parentId = `parent-${randomUUID()}`;
    const folderId = googleConfigurationStatus().drive ? await createDriveFolder(childId) : "";
    await appendRow(TABS.parents, {
      parent_id: parentId,
      email: action.payload.parentEmail.toLowerCase(),
      name: action.payload.parentName,
      phone: action.payload.parentPhone,
      child_ids: childId,
      notifications_opt_in: "true",
      updated_at: now
    });
    await appendRow(TABS.children, {
      child_id: childId,
      name: action.payload.name,
      parent_email: action.payload.parentEmail.toLowerCase(),
      primary_parent_id: parentId,
      folder_id: folderId,
      birthdate: action.payload.birthDate,
      start_date: action.payload.careStart,
      group: action.payload.group,
      status: "onboarding",
      care_hours_per_week: String(action.payload.careHoursPerWeek),
      care_fee_cents: String(action.payload.careFeeCents),
      meal_fee_cents: String(action.payload.mealFeeCents),
      photo_consent: "missing",
      download_consent: "missing",
      updated_at: now
    });
  }
  if (action.type === "update_child") {
    if (session.role !== "admin" && !session.childIds.includes(action.childId)) {
      throw new Error("You do not have access to this child record.");
    }
    const patch = { ...action.payload } as Record<string, unknown>;
    if (session.role === "parent") {
      for (const key of Object.keys(patch)) if (!PARENT_CHILD_PATCH_FIELDS.has(key)) delete patch[key];
    }
    await updateRow(TABS.children, "child_id", action.childId, {
      ...childPatchToRow(patch),
      updated_at: now
    });
  }
  if (action.type === "update_parent_profile") {
    if (session.role !== "admin" && session.parentId !== action.parentId) {
      throw new Error("You can only update your own profile.");
    }
    const mapping: Record<string, string> = {
      phone: "phone",
      phoneSecondary: "phone2",
      address: "address",
      preferredLanguage: "preferred_language",
      emergencyContactName: "emergency_contact_name",
      emergencyContactPhone: "emergency_contact_phone",
      notificationsOptIn: "notifications_opt_in"
    };
    const patch = Object.fromEntries(Object.entries(action.payload).map(([key, value]) => [mapping[key] ?? key, String(value)]));
    await updateRow(TABS.parents, "parent_id", action.parentId, { ...patch, updated_at: now });
  }
  if (action.type === "create_event") {
    if (session.role !== "admin") throw new Error("This action is available to staff only.");
    await createCalendarEvent(action.payload);
  }
  if (action.type === "update_event") {
    if (session.role !== "admin") throw new Error("This action is available to staff only.");
    await updateCalendarEvent(action.eventId, action.payload);
  }
  if (action.type === "generate_document") {
    if (session.role !== "admin") throw new Error("This action is available to staff only.");
    const snapshot = await getGoogleSnapshot(session);
    const child = snapshot.children.find((item) => item.id === action.childId);
    if (!child) throw new Error("Child record not found.");
    const count = snapshot.documents.length + 1;
    const prefix = action.documentType === "invoice" ? "R" : "V";
    await appendRow(TABS.documents, {
      document_id: `doc-${randomUUID()}`,
      child_id: child.id,
      type: action.documentType,
      status: "draft",
      title: action.documentType === "invoice" ? `Monatsabrechnung ${action.period}` : `Betreuungsvertrag ${child.name}`,
      number: `${prefix}-${new Date().getFullYear()}-${String(count).padStart(3, "0")}`,
      period: action.period,
      care_fee_cents: String(child.careFeeCents),
      meal_fee_cents: String(child.mealFeeCents),
      total_cents: String(child.careFeeCents + child.mealFeeCents),
      due_date: new Date(Date.now() + 14 * 86_400_000).toISOString().slice(0, 10),
      created_at: now.slice(0, 10)
    });
  }
  if (action.type === "update_document_status") {
    if (session.role !== "admin") throw new Error("This action is available to staff only.");
    await updateRow(TABS.documents, "document_id", action.documentId, { status: action.status });
  }
  return getGoogleSnapshot(session);
}

function photoSignatureMatches(bytes: Uint8Array, mimeType: string) {
  if (mimeType === "image/jpeg") return bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
  if (mimeType === "image/png") return bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47;
  if (mimeType === "image/webp") return Buffer.from(bytes.slice(0, 4)).toString() === "RIFF" && Buffer.from(bytes.slice(8, 12)).toString() === "WEBP";
  return false;
}

export async function uploadGooglePhoto(session: UserSession, childId: string, file: File) {
  if (session.role !== "admin") throw new Error("Only staff can upload photos.");
  const snapshot = await getGoogleSnapshot(session);
  const child = snapshot.children.find((item) => item.id === childId);
  if (!child?.photoFolderId) throw new Error("The child has no private Drive folder.");
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (!photoSignatureMatches(bytes, file.type)) throw new Error("The image contents do not match the selected file type.");
  const boundary = `nine-friends-${randomUUID()}`;
  const metadata = JSON.stringify({
    name: `photo_${new Date().toISOString().replace(/[-:.TZ]/gu, "")}_${randomUUID().slice(0, 8)}`,
    parents: [child.photoFolderId]
  });
  const prefix = Buffer.from(`--${boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${metadata}\r\n--${boundary}\r\nContent-Type: ${file.type}\r\n\r\n`);
  const suffix = Buffer.from(`\r\n--${boundary}--`);
  const body = Buffer.concat([prefix, Buffer.from(bytes), suffix]);
  await googleFetch("https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true&fields=id", {
    method: "POST",
    headers: { "content-type": `multipart/related; boundary=${boundary}` },
    body
  });
}

export async function downloadGooglePhoto(session: UserSession, fileId: string): Promise<{ bytes: ArrayBuffer; mimeType: string }> {
  const snapshot = await getGoogleSnapshot(session);
  const photo = snapshot.photos.find((item) => item.id === fileId);
  if (!photo) throw new Error("Photo not found or access denied.");
  const response = await googleFetch(`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(fileId)}?alt=media&supportsAllDrives=true`);
  return { bytes: await response.arrayBuffer(), mimeType: photo.mimeType };
}
