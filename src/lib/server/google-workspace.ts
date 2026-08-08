import { createSign, randomUUID } from "node:crypto";

import {
  ALLOWED_PHOTO_TYPES,
  MAX_PHOTO_BYTES,
  type AppAction,
  type CalendarEvent,
  type Child,
  type CommunicationSend,
  type CommunicationSendResult,
  type ConsentRecord,
  type DashboardSnapshot,
  type ManagedDocument,
  type Parent,
  type Photo,
  type IntegrationCheckCode,
  type PrivacyRequest,
  type Role,
  type UserSession,
  canAdminister,
  canWriteRecords,
  isStaffRole,
  PARENT_CHILD_PATCH_FIELDS,
  PrivacyRequestSchema
} from "../contracts";
import { buildManagedDocumentPdf } from "../pdf";
import { sessionMetadata } from "../session";
import {
  createCurrentPasswordHash,
  verifyPasswordHash,
  type PasswordHashVerification
} from "./password-hash";
import {
  assertManagedStaffIdentity,
  parentAccessEnabled,
  pseudonymousId
} from "./security";

const WORKSPACE_GOOGLE_SCOPES = [
  "https://www.googleapis.com/auth/spreadsheets",
  "https://www.googleapis.com/auth/drive"
].join(" ");
const CALENDAR_GOOGLE_SCOPES = "https://www.googleapis.com/auth/calendar.events";
const GMAIL_GOOGLE_SCOPES = "https://www.googleapis.com/auth/gmail.send";

const TABS = {
  children: process.env.GOOGLE_CHILDREN_TAB || "children",
  parents: process.env.GOOGLE_PARENTS_TAB || "parents",
  users: process.env.GOOGLE_USERS_TAB || "users",
  documents: process.env.GOOGLE_DOCUMENTS_TAB || "documents",
  consents: process.env.GOOGLE_CONSENTS_TAB || "consents",
  audit: process.env.GOOGLE_AUDIT_TAB || "audit",
  privacyRequests: process.env.GOOGLE_PRIVACY_REQUESTS_TAB || "privacy_requests"
} as const;

type SheetRow = Record<string, string>;
type TokenCache = { value: string; expiresAt: number };
type GoogleAuthContext = "workspace" | "calendar" | "gmail";
type GoogleTokenCache = Record<string, TokenCache>;
const globalGoogle = globalThis as typeof globalThis & {
  __nineFriendsGoogleTokens?: GoogleTokenCache;
  __nineFriendsGoogleTokenRequests?: Record<string, Promise<string>>;
};

export type GoogleIntegrationCheckCode = IntegrationCheckCode;

export type GoogleIntegrationCheck = {
  ok: boolean;
  code: GoogleIntegrationCheckCode;
};

export type GoogleIntegrationHealth = {
  checkedAt: string;
  sheets: GoogleIntegrationCheck;
  drive: GoogleIntegrationCheck;
  calendar: GoogleIntegrationCheck;
  gmail: GoogleIntegrationCheck;
};

const REQUIRED_SHEET_HEADERS: Record<keyof typeof TABS, readonly string[]> = {
  children: [
    "child_id", "name", "birthdate", "start_date", "group", "status",
    "primary_parent_id", "parent_email", "allergies", "dietary",
    "languages_at_home", "care_hours_per_week", "care_fee_cents",
    "meal_fee_cents", "folder_id", "photo_folder_id", "photo_consent",
    "download_consent", "notes_parent_visible", "notes_internal", "updated_at"
  ],
  parents: [
    "parent_id", "name", "email", "phone", "phone2", "address",
    "preferred_language", "emergency_contact_name", "emergency_contact_phone",
    "notifications_opt_in", "child_ids", "updated_at"
  ],
  users: [
    "user_id", "email", "name", "role", "parent_id", "child_ids",
    "password_salt", "password_hash", "active", "session_version"
  ],
  documents: [
    "document_id", "child_id", "type", "status", "title", "number", "period",
    "care_fee_cents", "meal_fee_cents", "total_cents", "due_date",
    "created_at", "drive_file_id"
  ],
  consents: [
    "consent_id", "child_id", "purpose", "status", "scope",
    "document_version", "source", "evidence_ref", "recorded_at",
    "recorded_by", "withdrawn_at"
  ],
  audit: [
    "event_id", "occurred_at", "actor_ref", "actor_role", "action",
    "resource_type", "resource_ref", "outcome", "request_ref"
  ],
  privacyRequests: [
    "request_id", "type", "subject_type", "subject_ref", "status",
    "requested_at", "requested_by", "reviewed_at", "reviewed_by",
    "due_at", "confirmation"
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

class GoogleDriveTargetError extends Error {
  constructor(public readonly code: GoogleIntegrationCheckCode) {
    super("The configured Google Drive target is not ready.");
  }
}

class GoogleDriveResponseError extends Error {}

export class PhotoUploadError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string
  ) {
    super(message);
  }
}

const required = (name: string) => {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required server configuration: ${name}`);
  return value;
};

export function gmailIntegrationEnabled(): boolean {
  return process.env.GMAIL_ENABLED?.trim().toLowerCase() === "true";
}

function isManagedWorkspaceUser(email: string | undefined, domain: string | undefined) {
  return Boolean(
    domain &&
    email &&
    !email.endsWith("@gmail.com") &&
    email.endsWith(`@${domain}`)
  );
}

export function googleConfigurationStatus() {
  const hasCredentials = Boolean(
    process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL?.trim() &&
    process.env.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY?.trim()
  );
  const workspaceDomain = process.env.GOOGLE_WORKSPACE_DOMAIN?.trim().toLowerCase();
  const organizer = process.env.GOOGLE_CALENDAR_IMPERSONATED_USER_EMAIL?.trim().toLowerCase();
  const gmailSender = process.env.GOOGLE_GMAIL_IMPERSONATED_USER_EMAIL?.trim().toLowerCase();
  const hasManagedOrganizer = isManagedWorkspaceUser(organizer, workspaceDomain);
  const hasDedicatedManagedGmailSender =
    isManagedWorkspaceUser(gmailSender, workspaceDomain) &&
    gmailSender !== organizer;
  return {
    sheets: hasCredentials && Boolean(process.env.GOOGLE_SHEET_ID?.trim()),
    drive: hasCredentials &&
      Boolean(process.env.GOOGLE_DRIVE_SHARED_DRIVE_ID?.trim()) &&
      Boolean(process.env.GOOGLE_DRIVE_PHOTOS_FOLDER_ID?.trim()),
    calendar: hasCredentials &&
      Boolean(process.env.GOOGLE_CALENDAR_ID?.trim()) &&
      hasManagedOrganizer,
    gmail: gmailIntegrationEnabled() &&
      hasCredentials &&
      hasDedicatedManagedGmailSender
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
  if (context === "gmail") {
    return {
      email,
      scopes: GMAIL_GOOGLE_SCOPES,
      subject: required("GOOGLE_GMAIL_IMPERSONATED_USER_EMAIL")
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
  delete globalGoogle.__nineFriendsGoogleTokenRequests;
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
  if (error instanceof GoogleDriveTargetError) return error.code;
  if (error instanceof GoogleIntegrationSchemaError) return "schema";
  if (!(error instanceof GoogleWorkspaceRequestError)) return "unknown";
  return classifyGoogleHttpError(error.status, error.reason);
}

async function requestGoogleAccessToken(
  context: GoogleAuthContext,
  cacheKey: string
): Promise<string> {
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

export async function getGoogleAccessToken(context: GoogleAuthContext): Promise<string> {
  const cacheKey = tokenCacheKey(context);
  const cached = globalGoogle.__nineFriendsGoogleTokens?.[cacheKey];
  if (cached && cached.expiresAt > Date.now() + 60_000) return cached.value;

  const active = globalGoogle.__nineFriendsGoogleTokenRequests?.[cacheKey];
  if (active) return active;

  const request = requestGoogleAccessToken(context, cacheKey);
  const requests = globalGoogle.__nineFriendsGoogleTokenRequests ?? {};
  requests[cacheKey] = request;
  globalGoogle.__nineFriendsGoogleTokenRequests = requests;
  try {
    return await request;
  } finally {
    if (globalGoogle.__nineFriendsGoogleTokenRequests?.[cacheKey] === request) {
      delete globalGoogle.__nineFriendsGoogleTokenRequests[cacheKey];
    }
  }
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

export type DriveFolderMetadata = {
  id?: string;
  mimeType?: string;
  trashed?: boolean;
  driveId?: string;
  parents?: string[];
  capabilities?: { canAddChildren?: boolean };
};

export function validateDriveFolderMetadata(
  metadata: DriveFolderMetadata,
  expectedDriveId: string,
  expectedParentId?: string
): void {
  if (!metadata.driveId || metadata.driveId !== expectedDriveId) {
    throw new GoogleDriveTargetError("unsupported_storage");
  }
  if (
    !metadata.id ||
    metadata.mimeType !== "application/vnd.google-apps.folder"
  ) {
    throw new GoogleDriveTargetError("schema");
  }
  if (metadata.trashed) {
    throw new GoogleDriveTargetError("not_found");
  }
  if (
    expectedParentId &&
    !metadata.parents?.includes(expectedParentId)
  ) {
    throw new GoogleDriveTargetError("unsupported_storage");
  }
  if (metadata.capabilities?.canAddChildren !== true) {
    throw new GoogleDriveTargetError("forbidden");
  }
}

async function readDriveFolder(
  folderId: string,
  expectedDriveId: string,
  expectedParentId?: string
): Promise<DriveFolderMetadata> {
  const encodedFolderId = encodeURIComponent(folderId);
  const url = new URL(`https://www.googleapis.com/drive/v3/files/${encodedFolderId}`);
  url.searchParams.set("supportsAllDrives", "true");
  url.searchParams.set(
    "fields",
    "id,mimeType,trashed,driveId,parents,capabilities(canAddChildren)"
  );
  const response = await googleFetch(url.toString());
  const payload = await response.json() as DriveFolderMetadata;
  validateDriveFolderMetadata(payload, expectedDriveId, expectedParentId);
  return payload;
}

async function checkDriveIntegration(): Promise<void> {
  await readDriveFolder(
    required("GOOGLE_DRIVE_PHOTOS_FOLDER_ID"),
    required("GOOGLE_DRIVE_SHARED_DRIVE_ID")
  );
}

async function checkDriveChildFolders(children: Child[]): Promise<void> {
  const parentId = required("GOOGLE_DRIVE_PHOTOS_FOLDER_ID");
  const driveId = required("GOOGLE_DRIVE_SHARED_DRIVE_ID");
  await Promise.all(children.map(async (child) => {
    if (!child.photoFolderId) {
      throw new GoogleDriveTargetError("not_found");
    }
    await readDriveFolder(child.photoFolderId, driveId, parentId);
  }));
}

async function checkCalendarIntegration() {
  const calendarId = encodeURIComponent(required("GOOGLE_CALENDAR_ID"));
  const url = new URL(`https://www.googleapis.com/calendar/v3/calendars/${calendarId}/events`);
  url.searchParams.set("maxResults", "1");
  url.searchParams.set("singleEvents", "true");
  url.searchParams.set("timeMin", new Date().toISOString());
  await googleFetch(url.toString(), {}, "calendar");
}

async function checkGmailIntegration() {
  await getGoogleAccessToken("gmail");
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

export async function checkGoogleDriveIntegration(): Promise<GoogleIntegrationCheck> {
  return runIntegrationCheck(
    googleConfigurationStatus().drive,
    checkDriveIntegration
  );
}

export async function checkGoogleIntegrations(): Promise<GoogleIntegrationHealth> {
  const configuration = googleConfigurationStatus();
  const [sheets, drive, calendar, gmail] = await Promise.all([
    runIntegrationCheck(configuration.sheets, checkSheetsIntegration),
    checkGoogleDriveIntegration(),
    runIntegrationCheck(configuration.calendar, checkCalendarIntegration),
    runIntegrationCheck(configuration.gmail, checkGmailIntegration)
  ]);
  return {
    checkedAt: new Date().toISOString(),
    sheets,
    drive,
    calendar,
    gmail
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

export async function appendGoogleAuditEvent(input: {
  session?: UserSession;
  actorEmail?: string;
  actorRole?: Role | "unknown";
  action: string;
  resourceType: string;
  resourceId?: string;
  outcome: "success" | "denied" | "failure";
  requestId?: string;
}): Promise<void> {
  const actor = input.session?.email || input.actorEmail || "anonymous";
  await appendRow(TABS.audit, {
    event_id: `audit-${randomUUID()}`,
    occurred_at: new Date().toISOString(),
    actor_ref: pseudonymousId(actor),
    actor_role: input.session?.role || input.actorRole || "unknown",
    action: input.action,
    resource_type: input.resourceType,
    resource_ref: input.resourceId ? pseudonymousId(input.resourceId) : "",
    outcome: input.outcome,
    request_ref: input.requestId ? pseudonymousId(input.requestId) : ""
  });
}

export async function createGooglePrivacyRequest(
  session: UserSession,
  input: {
    type: PrivacyRequest["type"];
    subjectType: PrivacyRequest["subjectType"];
    subjectId: string;
    confirmation: true;
  }
): Promise<PrivacyRequest> {
  const now = new Date();
  const request: PrivacyRequest = {
    id: `privacy-${randomUUID()}`,
    type: input.type,
    subjectType: input.subjectType,
    subjectId: input.subjectId,
    status: "pending",
    requestedAt: now.toISOString(),
    requestedBy: pseudonymousId(session.email),
    dueAt: new Date(now.getTime() + 30 * 86_400_000).toISOString(),
    confirmation: input.confirmation
  };
  await appendRow(TABS.privacyRequests, {
    request_id: request.id,
    type: request.type,
    subject_type: request.subjectType,
    subject_ref: pseudonymousId(request.subjectId),
    status: request.status,
    requested_at: request.requestedAt,
    requested_by: request.requestedBy,
    reviewed_at: "",
    reviewed_by: "",
    due_at: request.dueAt,
    confirmation: "true"
  });
  await appendGoogleAuditEvent({
    session,
    action: `privacy_request.${request.type}`,
    resourceType: request.subjectType,
    resourceId: request.subjectId,
    outcome: "success"
  });
  return request;
}

export async function listGooglePrivacyRequests(): Promise<Array<Omit<PrivacyRequest, "subjectId"> & { subjectRef: string }>> {
  const rows = await getRows(TABS.privacyRequests);
  return rows.flatMap((row) => {
    if (!row.request_id || !row.type || !row.subject_type || !row.subject_ref) return [];
    const parsed = PrivacyRequestSchema.safeParse({
      id: row.request_id,
      type: row.type,
      subjectType: row.subject_type,
      subjectId: row.subject_ref,
      status: row.status || "pending",
      requestedAt: row.requested_at,
      requestedBy: row.requested_by,
      ...(row.reviewed_at ? { reviewedAt: row.reviewed_at } : {}),
      ...(row.reviewed_by ? { reviewedBy: row.reviewed_by } : {}),
      dueAt: row.due_at,
      confirmation: bool(row.confirmation ?? "")
    });
    if (!parsed.success) return [];
    const { subjectId: subjectRef, ...request } = parsed.data;
    return [{ ...request, subjectRef }];
  });
}

export async function updateGoogleUserAccess(
  session: UserSession,
  input: {
    userId: string;
    role: Role;
    active: boolean;
    confirmation: true;
  }
) {
  if (!canAdminister(session.role)) {
    throw new Error("Only administrators may change user access.");
  }
  const users = await getRows(TABS.users);
  const target = users.find((row) => row.user_id === input.userId);
  if (!target?.email) throw new Error("User record not found.");
  assertManagedStaffIdentity(target.email, input.role);
  const sessionVersion = int(target.session_version ?? "") + 1;
  await updateRow(TABS.users, "user_id", input.userId, {
    role: input.role,
    active: String(input.active),
    session_version: String(sessionVersion)
  });
  await appendGoogleAuditEvent({
    session,
    action: input.active ? "user.access_changed" : "user.access_revoked",
    resourceType: "user",
    resourceId: input.userId,
    outcome: "success"
  });
  return {
    userRef: pseudonymousId(input.userId),
    role: input.role,
    active: input.active,
    sessionVersion
  };
}

const bool = (value: string, fallback = false) => {
  if (!value) return fallback;
  return ["true", "1", "yes", "ja", "on"].includes(value.trim().toLowerCase());
};
const int = (value: string) => Number.isFinite(Number(value)) ? Math.trunc(Number(value)) : 0;
const consent = (value: string): Child["photoConsent"] => {
  if (["granted", "unpixelated", "true", "yes", "ja"].includes(value.toLowerCase())) return "granted";
  if (["restricted", "pixelated"].includes(value.toLowerCase())) return "restricted";
  if (["withdrawn", "revoked", "widerrufen"].includes(value.toLowerCase())) return "withdrawn";
  return "missing";
};
const roleFromRow = (value: string): Role | null =>
  ["admin", "staff_write", "staff_read", "parent"].includes(value)
    ? value as Role
    : null;
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

const photoFolderFromRow = (row: SheetRow): string => {
  const canonical = row.folder_id?.trim() || "";
  const compatibility = row.photo_folder_id?.trim() || "";
  if (!canonical || canonical !== compatibility) return "";
  return canonical;
};

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
    photoFolderId: photoFolderFromRow(row),
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

type GmailAttachment = {
  filename: string;
  mimeType: "application/pdf";
  bytes: Uint8Array;
};

type GmailMessage = {
  sender: string;
  recipient: string;
  subject: string;
  body: string;
  attachment?: GmailAttachment;
};

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/u;

function assertSafeHeader(value: string, label: string) {
  if (/[\r\n]/u.test(value)) {
    throw new Error(`${label} must not contain line breaks.`);
  }
}

function wrapBase64(value: Buffer): string {
  return value.toString("base64").match(/.{1,76}/gu)?.join("\r\n") ?? "";
}

export function buildGmailRawMessage(message: GmailMessage): string {
  assertSafeHeader(message.sender, "Sender");
  assertSafeHeader(message.recipient, "Recipient");
  assertSafeHeader(message.subject, "Subject");
  if (!EMAIL_PATTERN.test(message.sender) || !EMAIL_PATTERN.test(message.recipient)) {
    throw new Error("Gmail sender and recipient must be valid email addresses.");
  }

  const headers = [
    `From: ${message.sender}`,
    `To: ${message.recipient}`,
    `Subject: =?UTF-8?B?${Buffer.from(message.subject, "utf8").toString("base64")}?=`,
    "MIME-Version: 1.0"
  ];

  let mime: string;
  if (message.attachment) {
    const boundary = `nine-friends-${randomUUID()}`;
    const filename = message.attachment.filename
      .replace(/[^a-zA-Z0-9._-]/gu, "_")
      .slice(0, 100) || "document.pdf";
    mime = [
      ...headers,
      `Content-Type: multipart/mixed; boundary="${boundary}"`,
      "",
      `--${boundary}`,
      'Content-Type: text/plain; charset="UTF-8"',
      "Content-Transfer-Encoding: base64",
      "",
      wrapBase64(Buffer.from(message.body, "utf8")),
      `--${boundary}`,
      `Content-Type: ${message.attachment.mimeType}; name="${filename}"`,
      "Content-Transfer-Encoding: base64",
      `Content-Disposition: attachment; filename="${filename}"`,
      "",
      wrapBase64(Buffer.from(message.attachment.bytes)),
      `--${boundary}--`,
      ""
    ].join("\r\n");
  } else {
    mime = [
      ...headers,
      'Content-Type: text/plain; charset="UTF-8"',
      "Content-Transfer-Encoding: base64",
      "",
      wrapBase64(Buffer.from(message.body, "utf8")),
      ""
    ].join("\r\n");
  }
  return Buffer.from(mime, "utf8").toString("base64url");
}

function normalizedUniqueEmails(values: string[]): string[] {
  return [...new Set(values
    .map((value) => value.trim().toLowerCase())
    .filter((value) => EMAIL_PATTERN.test(value)))];
}

export function resolveAnnouncementRecipients(
  input: Extract<CommunicationSend, { kind: "announcement" }>,
  parents: Parent[],
  children: Child[]
): string[] {
  const optedInParents = parents.filter((parent) => parent.notificationsOptIn);
  const parentForChild = (child: Child) =>
    optedInParents.find((parent) => parent.id === child.primaryParentId) ??
    optedInParents.find((parent) =>
      parent.email.toLowerCase() === child.primaryParentEmail.toLowerCase()
    );

  let matchingParents: Parent[];
  if (input.audience === "all_parents") {
    matchingParents = optedInParents;
  } else {
    const matchingChildren = input.audience === "group"
      ? children.filter((child) =>
        child.group.trim().toLowerCase() === input.group?.trim().toLowerCase()
      )
      : children.filter((child) => child.id === input.childId);
    matchingParents = matchingChildren.flatMap((child) => {
      const parent = parentForChild(child);
      return parent ? [parent] : [];
    });
  }

  const recipients = normalizedUniqueEmails(
    matchingParents.map((parent) => parent.email)
  );
  if (recipients.length > 100) {
    const error = new Error("The recipient limit of 100 was exceeded.");
    Object.assign(error, { status: 400 });
    throw error;
  }
  return recipients;
}

export async function sendGmailBatch(
  recipients: string[],
  send: (recipient: string) => Promise<void>
): Promise<{ successCount: number; failureCount: number }> {
  const uniqueRecipients = normalizedUniqueEmails(recipients);
  if (uniqueRecipients.length > 100) {
    const error = new Error("The recipient limit of 100 was exceeded.");
    Object.assign(error, { status: 400 });
    throw error;
  }
  let successCount = 0;
  let failureCount = 0;
  for (const recipient of uniqueRecipients) {
    try {
      await send(recipient);
      successCount += 1;
    } catch {
      failureCount += 1;
    }
  }
  return { successCount, failureCount };
}

function configuredGmailSender(): string {
  const sender = required("GOOGLE_GMAIL_IMPERSONATED_USER_EMAIL")
    .trim()
    .toLowerCase();
  if (!googleConfigurationStatus().gmail) {
    const error = new Error("The dedicated managed Gmail sender is not configured.");
    Object.assign(error, { status: 503 });
    throw error;
  }
  return sender;
}

async function sendGmailMessage(
  recipient: string,
  subject: string,
  body: string,
  attachment?: GmailAttachment
) {
  const raw = buildGmailRawMessage({
    sender: configuredGmailSender(),
    recipient,
    subject,
    body,
    ...(attachment ? { attachment } : {})
  });
  await googleFetch(
    "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ raw })
    },
    "gmail"
  );
}

function communicationOutcome(result: {
  successCount: number;
  failureCount: number;
}): "success" | "failure" {
  return result.successCount > 0 && result.failureCount === 0
    ? "success"
    : "failure";
}

export async function sendGoogleCommunication(
  session: UserSession,
  input: CommunicationSend
): Promise<CommunicationSendResult> {
  if (!canAdminister(session.role)) {
    const error = new Error("Only administrators may send communications.");
    Object.assign(error, { status: 403 });
    throw error;
  }
  configuredGmailSender();

  const [parentRows, childRows, documentRows] = await Promise.all([
    getRows(TABS.parents),
    getRows(TABS.children),
    getRows(TABS.documents)
  ]);
  const parents = parentRows.map(parentFromRow);
  const children = childRows.map((row) => childFromRow(row, parents));

  if (input.kind === "announcement") {
    const recipients = resolveAnnouncementRecipients(input, parents, children);
    if (recipients.length === 0) {
      const error = new Error("No eligible opted-in recipients were found.");
      Object.assign(error, { status: 409 });
      throw error;
    }
    const result = await sendGmailBatch(
      recipients,
      (recipient) => sendGmailMessage(recipient, input.subject, input.body)
    );
    await appendGoogleAuditEvent({
      session,
      action: result.failureCount > 0
        ? "communication.announcement_partial"
        : "communication.announcement",
      resourceType: input.audience,
      resourceId: input.childId ?? input.group,
      outcome: communicationOutcome(result)
    });
    return { kind: "announcement", ...result };
  }

  const document = documentRows
    .map(documentFromRow)
    .find((item) => item.id === input.documentId);
  if (!document) {
    const error = new Error("Document not found.");
    Object.assign(error, { status: 404 });
    throw error;
  }
  if (document.status !== "draft") {
    const error = new Error("Only reviewed document drafts may be sent.");
    Object.assign(error, { status: 409 });
    throw error;
  }
  const child = children.find((item) => item.id === document.childId);
  if (!child) {
    const error = new Error("The document has no authorized child record.");
    Object.assign(error, { status: 409 });
    throw error;
  }
  const parent = parents.find((item) => item.id === child.primaryParentId) ??
    parents.find((item) =>
      item.email.toLowerCase() === child.primaryParentEmail.toLowerCase()
    );
  if (!parent) {
    const error = new Error("The document has no assigned primary contact.");
    Object.assign(error, { status: 409 });
    throw error;
  }

  const pdf = await buildManagedDocumentPdf(document, child, parent);
  const result = await sendGmailBatch([parent.email], (recipient) =>
    sendGmailMessage(
      recipient,
      `${document.title} · ${document.number}`,
      input.body,
      {
        filename: `${document.number}.pdf`,
        mimeType: "application/pdf",
        bytes: pdf
      }
    )
  );
  if (result.successCount === 0) {
    await appendGoogleAuditEvent({
      session,
      action: "communication.document",
      resourceType: "document",
      resourceId: document.id,
      outcome: "failure"
    });
    return {
      kind: "document",
      ...result,
      documentId: document.id,
      documentStatusUpdated: false
    };
  }

  let documentStatusUpdated = false;
  try {
    await updateRow(TABS.documents, "document_id", document.id, {
      status: "sent"
    });
    documentStatusUpdated = true;
  } finally {
    await appendGoogleAuditEvent({
      session,
      action: documentStatusUpdated
        ? "communication.document"
        : "communication.document_status_failed",
      resourceType: "document",
      resourceId: document.id,
      outcome: documentStatusUpdated ? "success" : "failure"
    });
  }
  return {
    kind: "document",
    ...result,
    documentId: document.id,
    documentStatusUpdated
  };
}

const consentFromRow = (row: SheetRow): ConsentRecord | null => {
  const purpose = row.purpose === "photo_processing" || row.purpose === "photo_download"
    ? row.purpose
    : null;
  const consentStatus = ["granted", "restricted", "withdrawn"].includes(row.status ?? "")
    ? row.status as ConsentRecord["status"]
    : null;
  const scope = ["staff_only", "parent_portal", "download"].includes(row.scope ?? "")
    ? row.scope as ConsentRecord["scope"]
    : null;
  const source = ["signed_form", "digital_form", "legacy_import"].includes(row.source ?? "")
    ? row.source as ConsentRecord["source"]
    : null;
  if (!row.consent_id || !row.child_id || !purpose || !consentStatus || !scope || !source) {
    return null;
  }
  return {
    id: row.consent_id,
    childId: row.child_id,
    purpose,
    status: consentStatus,
    scope,
    documentVersion: row.document_version || "unknown",
    source,
    ...(row.evidence_ref ? { evidenceRef: row.evidence_ref } : {}),
    recordedAt: row.recorded_at || new Date(0).toISOString(),
    recordedBy: row.recorded_by || "unknown",
    ...(row.withdrawn_at ? { withdrawnAt: row.withdrawn_at } : {})
  };
};

function latestConsent(
  records: ConsentRecord[],
  childId: string,
  purpose: ConsentRecord["purpose"]
): ConsentRecord | undefined {
  return records
    .filter((record) => record.childId === childId && record.purpose === purpose)
    .sort((left, right) => right.recordedAt.localeCompare(left.recordedAt))[0];
}

function applyConsentState(children: Child[], records: ConsentRecord[]): Child[] {
  return children.map((child) => ({
    ...child,
    photoConsent: latestConsent(records, child.id, "photo_processing")?.status ?? "missing",
    downloadConsent: latestConsent(records, child.id, "photo_download")?.status ?? "missing"
  }));
}

function photoAccessPermitted(
  records: ConsentRecord[],
  childId: string,
  role: Role
): boolean {
  const processing = latestConsent(records, childId, "photo_processing");
  if (processing?.status !== "granted") return false;
  if (isStaffRole(role)) return true;
  const download = latestConsent(records, childId, "photo_download");
  return processing.scope === "parent_portal" &&
    download?.status === "granted" &&
    download.scope === "download";
}

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
  const driveId = required("GOOGLE_DRIVE_SHARED_DRIVE_ID");
  await readDriveFolder(parentId, driveId);
  const response = await googleFetch("https://www.googleapis.com/drive/v3/files?supportsAllDrives=true&fields=id", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      name: `child_${pseudonymousId(childId)}`,
      mimeType: "application/vnd.google-apps.folder",
      parents: [parentId]
    })
  });
  const payload = await response.json() as { id?: string };
  if (!payload.id) {
    throw new GoogleDriveResponseError("Google Drive returned an invalid folder response.");
  }
  await readDriveFolder(payload.id, driveId, parentId);
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

type VerifiedPasswordHash = Extract<
  PasswordHashVerification,
  { valid: true }
>;

async function upgradeGooglePasswordHash(input: {
  row: SheetRow;
  normalizedEmail: string;
  password: string;
  verification: VerifiedPasswordHash;
  originalPasswordSalt: string;
  originalPasswordHash: string;
}): Promise<SheetRow> {
  if (input.verification.upgrade === "none") {
    throw new Error("Credential migration could not be completed safely.");
  }
  const nextCredential = input.verification.upgrade === "rehash"
    ? await createCurrentPasswordHash(input.password)
    : {
        passwordSalt: input.originalPasswordSalt,
        passwordHash: input.verification.replacementHash ?? ""
      };
  if (!nextCredential.passwordHash) {
    throw new Error("Credential migration could not be completed safely.");
  }

  const userId = input.row.user_id?.trim() ?? "";
  const idField = userId ? "user_id" : "email";
  const id = userId
    ? input.row.user_id ?? userId
    : input.row.email ?? input.normalizedEmail;
  const response = await googleFetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${sheetId()}/values/${encodeRange(TABS.users)}`
  );
  const payload = await response.json() as { values?: unknown[][] };
  const values = payload.values ?? [];
  const header = (values[0] ?? []).map((value) => String(value).trim());
  const idIndex = header.indexOf(idField);
  if (idIndex < 0) {
    throw new Error("Credential migration could not be completed safely.");
  }
  const rowIndex = values.findIndex((row, index) =>
    index > 0 && String(row[idIndex] ?? "") === id
  );
  if (rowIndex < 1) {
    throw new Error("Credential migration could not be completed safely.");
  }
  const existing = Object.fromEntries(
    header.map((key, index) => [key, String(values[rowIndex]?.[index] ?? "")])
  );
  const currentEmail = existing.email?.trim().toLowerCase();
  const currentRole = roleFromRow(existing.role ?? "");
  if (
    currentEmail !== input.normalizedEmail ||
    existing.user_id !== input.row.user_id ||
    existing.role !== input.row.role ||
    existing.active !== input.row.active ||
    existing.active === "false" ||
    existing.password_salt !== input.originalPasswordSalt ||
    existing.password_hash !== input.originalPasswordHash ||
    !currentRole ||
    (currentRole === "parent" && !parentAccessEnabled())
  ) {
    throw new Error("Credential migration could not be completed safely.");
  }
  assertManagedStaffIdentity(currentEmail, currentRole);

  const nextSessionVersion = Math.max(
    0,
    int(existing.session_version ?? "")
  ) + 1;
  const rowNumber = rowIndex + 1;
  const cells = [
    ["password_salt", nextCredential.passwordSalt],
    ["password_hash", nextCredential.passwordHash],
    ["session_version", String(nextSessionVersion)]
  ] as const;
  const data = cells.map(([field, value]) => {
    const columnIndex = header.indexOf(field);
    if (columnIndex < 0) {
      throw new Error("Credential migration could not be completed safely.");
    }
    const tab = TABS.users.replaceAll("'", "''");
    return {
      range: `'${tab}'!${columnName(columnIndex)}${rowNumber}`,
      majorDimension: "ROWS",
      values: [[value]]
    };
  });
  await googleFetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${sheetId()}/values:batchUpdate`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ valueInputOption: "RAW", data })
    }
  );

  const updatedUsers = await getRows(TABS.users);
  const updated = updatedUsers.find((row) =>
    row.email?.trim().toLowerCase() === input.normalizedEmail
  );
  if (!updated) {
    throw new Error("Credential migration could not be completed safely.");
  }
  const updatedEmail = updated.email?.trim().toLowerCase();
  const updatedRole = roleFromRow(updated.role ?? "");
  if (
    updatedEmail !== input.normalizedEmail ||
    updated.user_id !== existing.user_id ||
    updated.role !== existing.role ||
    updated.active !== existing.active ||
    updated.active === "false" ||
    updated.password_salt !== nextCredential.passwordSalt ||
    updated.password_hash !== nextCredential.passwordHash ||
    int(updated.session_version ?? "") !== nextSessionVersion ||
    !updatedRole ||
    (updatedRole === "parent" && !parentAccessEnabled())
  ) {
    throw new Error("Credential migration could not be completed safely.");
  }
  assertManagedStaffIdentity(updatedEmail, updatedRole);

  await appendGoogleAuditEvent({
    actorEmail: input.normalizedEmail,
    actorRole: updatedRole,
    action: "auth.password_hash_upgraded",
    resourceType: "user",
    resourceId: updated.user_id || input.normalizedEmail,
    outcome: "success"
  });
  return updated;
}

export async function authenticateGoogleUser(email: string, password: string): Promise<UserSession | null> {
  const normalized = email.trim().toLowerCase();
  const users = await getRows(TABS.users);
  let row = users.find((item) =>
    item.email?.trim().toLowerCase() === normalized &&
    item.active !== "false"
  );
  if (!row?.password_hash || !row.password_salt) return null;
  const originalPasswordSalt = row.password_salt;
  const originalPasswordHash = row.password_hash;
  const verification = await verifyPasswordHash(
    password,
    originalPasswordSalt,
    originalPasswordHash
  );
  if (!verification.valid) return null;
  let role = roleFromRow(row.role ?? "");
  if (!role || (role === "parent" && !parentAccessEnabled())) return null;
  assertManagedStaffIdentity(normalized, role);
  if (verification.upgrade !== "none") {
    row = await upgradeGooglePasswordHash({
      row,
      normalizedEmail: normalized,
      password,
      verification,
      originalPasswordSalt,
      originalPasswordHash
    });
    role = roleFromRow(row.role ?? "");
    if (
      row.active === "false" ||
      !role ||
      (role === "parent" && !parentAccessEnabled())
    ) {
      return null;
    }
    assertManagedStaffIdentity(normalized, role);
  }
  return {
    ...sessionMetadata("password", int(row.session_version || "")),
    userId: row.user_id || normalized,
    email: normalized,
    name: row.name || normalized.split("@")[0] || "Nutzer",
    role,
    ...(row.parent_id ? { parentId: row.parent_id } : {}),
    childIds: (row.child_ids || "").split(",").map((item) => item.trim()).filter(Boolean)
  };
}

export async function authenticateGoogleSitesUser(
  email: string,
  forwardedName?: string
): Promise<UserSession | null> {
  const normalized = email.trim().toLowerCase();
  const users = await getRows(TABS.users);
  const row = users.find((item) =>
    item.email?.trim().toLowerCase() === normalized && item.active !== "false"
  );
  if (!row) return null;
  const role = roleFromRow(row.role ?? "");
  if (!role || (role === "parent" && !parentAccessEnabled())) return null;
  assertManagedStaffIdentity(normalized, role);
  return {
    ...sessionMetadata("sites", int(row.session_version || "")),
    userId: row.user_id || normalized,
    email: normalized,
    name: forwardedName || row.name || normalized.split("@")[0] || "Nutzer",
    role,
    ...(row.parent_id ? { parentId: row.parent_id } : {}),
    childIds: (row.child_ids || "").split(",").map((item) => item.trim()).filter(Boolean)
  };
}

export async function validateGoogleSession(session: UserSession): Promise<boolean> {
  const users = await getRows(TABS.users);
  const row = users.find((item) =>
    (item.user_id === session.userId ||
      item.email?.trim().toLowerCase() === session.email.toLowerCase()) &&
    item.active !== "false"
  );
  if (!row) return false;
  const role = roleFromRow(row.role ?? "");
  if (!role || role !== session.role) return false;
  if (role === "parent" && !parentAccessEnabled()) return false;
  if (int(row.session_version || "") !== session.sessionVersion) return false;
  try {
    assertManagedStaffIdentity(session.email, role);
  } catch {
    return false;
  }
  return true;
}

export async function getGoogleSnapshot(session: UserSession): Promise<DashboardSnapshot> {
  const [parentRows, childRows, documentRows, consentRows, events] = await Promise.all([
    getRows(TABS.parents),
    getRows(TABS.children),
    getRows(TABS.documents),
    getRows(TABS.consents),
    listCalendarEvents()
  ]);
  const allParents = parentRows.map(parentFromRow);
  const allConsents = consentRows.flatMap((row) => {
    const record = consentFromRow(row);
    return record ? [record] : [];
  });
  const allChildren = applyConsentState(
    childRows.map((row) => childFromRow(row, allParents)),
    allConsents
  );
  const allowedIds = new Set(session.childIds);
  const children = isStaffRole(session.role)
    ? allChildren
    : allChildren.filter((child) => allowedIds.has(child.id));
  const visibleIds = new Set(children.map((child) => child.id));
  const parents = isStaffRole(session.role)
    ? allParents
    : allParents.filter((parent) => parent.id === session.parentId);
  const photoChildren = children.filter((child) =>
    photoAccessPermitted(allConsents, child.id, session.role)
  );
  const configuration = googleConfigurationStatus();
  let photos: Photo[] = [];
  const driveCheck = await runIntegrationCheck(configuration.drive, async () => {
    await checkDriveIntegration();
    await checkDriveChildFolders(children);
    photos = await listPhotosForChildren(photoChildren);
  });
  return {
    session,
    children,
    parents,
    events: events.filter((event) => event.audience === "all" || (event.childId && visibleIds.has(event.childId))),
    documents: documentRows.map(documentFromRow).filter((document) => isStaffRole(session.role) || visibleIds.has(document.childId)),
    photos,
    consents: session.role === "admin"
      ? allConsents.filter((record) => visibleIds.has(record.childId))
      : [],
    integrations: {
      mode: "google",
      ...configuration,
      drive: driveCheck.ok,
      driveStatus: driveCheck.code,
      mcp: process.env.MCP_ENABLED?.trim().toLowerCase() === "true" &&
        Boolean(process.env.MCP_BEARER_TOKEN?.trim())
    },
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
    notesParentVisible: "notes_parent_visible",
    notesInternal: "notes_internal"
  };
  return Object.fromEntries(Object.entries(patch).flatMap(([key, value]) => {
    const target = mapping[key];
    return target ? [[target, String(value ?? "")]] : [];
  }));
};

async function recordGoogleConsent(
  session: UserSession,
  input: Extract<AppAction, { type: "record_consent" }>["payload"]
): Promise<void> {
  if (!canAdminister(session.role)) {
    throw new Error("Only administrators may record or withdraw consent.");
  }
  const childRows = await getRows(TABS.children);
  if (!childRows.some((row) => row.child_id === input.childId)) {
    throw new Error("Child record not found.");
  }
  const now = new Date().toISOString();
  await appendRow(TABS.consents, {
    consent_id: `consent-${randomUUID()}`,
    child_id: input.childId,
    purpose: input.purpose,
    status: input.status,
    scope: input.scope,
    document_version: input.documentVersion,
    source: input.source,
    evidence_ref: input.evidenceRef || "",
    recorded_at: now,
    recorded_by: pseudonymousId(session.email),
    withdrawn_at: input.status === "withdrawn" ? now : ""
  });
  await appendGoogleAuditEvent({
    session,
    action: `consent.${input.status}`,
    resourceType: input.purpose,
    resourceId: input.childId,
    outcome: "success"
  });
}

export async function performGoogleAction(session: UserSession, action: AppAction): Promise<DashboardSnapshot> {
  const now = new Date().toISOString();
  if (action.type === "create_child") {
    if (!canWriteRecords(session.role)) throw new Error("This action requires write access.");
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
      birthdate: action.payload.birthDate,
      start_date: action.payload.careStart,
      group: action.payload.group,
      status: "onboarding",
      care_hours_per_week: String(action.payload.careHoursPerWeek),
      care_fee_cents: String(action.payload.careFeeCents),
      meal_fee_cents: String(action.payload.mealFeeCents),
      photo_consent: "missing",
      download_consent: "missing",
      folder_id: folderId,
      photo_folder_id: folderId,
      updated_at: now
    });
  }
  if (action.type === "update_child") {
    if (session.role === "staff_read") throw new Error("This action requires write access.");
    if (!isStaffRole(session.role) && !session.childIds.includes(action.childId)) {
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
    if (session.role === "staff_read") throw new Error("This action requires write access.");
    if (!isStaffRole(session.role) && session.parentId !== action.parentId) {
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
    if (!canWriteRecords(session.role)) throw new Error("This action requires write access.");
    await createCalendarEvent(action.payload);
  }
  if (action.type === "update_event") {
    if (!canWriteRecords(session.role)) throw new Error("This action requires write access.");
    await updateCalendarEvent(action.eventId, action.payload);
  }
  if (action.type === "generate_document") {
    if (!canWriteRecords(session.role)) throw new Error("This action requires write access.");
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
    if (!canWriteRecords(session.role)) throw new Error("This action requires write access.");
    await updateRow(TABS.documents, "document_id", action.documentId, { status: action.status });
  }
  if (action.type === "record_consent") {
    await recordGoogleConsent(session, action.payload);
  }
  if (action.type !== "record_consent") {
    const resourceId =
      "childId" in action ? action.childId
        : "parentId" in action ? action.parentId
          : "eventId" in action ? action.eventId
            : "documentId" in action ? action.documentId
              : undefined;
    await appendGoogleAuditEvent({
      session,
      action: action.type,
      resourceType: action.type.split("_").at(-1) || "record",
      ...(resourceId ? { resourceId } : {}),
      outcome: "success"
    });
  }
  return getGoogleSnapshot(session);
}

export function photoSignatureMatches(bytes: Uint8Array, mimeType: string): boolean {
  if (mimeType === "image/jpeg") return bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
  if (mimeType === "image/png") return bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47;
  if (mimeType === "image/webp") {
    return bytes[0] === 0x52 &&
      bytes[1] === 0x49 &&
      bytes[2] === 0x46 &&
      bytes[3] === 0x46 &&
      bytes[8] === 0x57 &&
      bytes[9] === 0x45 &&
      bytes[10] === 0x42 &&
      bytes[11] === 0x50;
  }
  return false;
}

const PHOTO_EXTENSION: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp"
};

const concatenateBytes = (
  parts: Array<Uint8Array<ArrayBufferLike>>
): Uint8Array<ArrayBuffer> => {
  const result = new Uint8Array(parts.reduce((sum, part) => sum + part.byteLength, 0));
  let offset = 0;
  for (const part of parts) {
    result.set(part, offset);
    offset += part.byteLength;
  }
  return result;
};

export function buildGoogleDrivePhotoMultipart(input: {
  bytes: Uint8Array;
  mimeType: string;
  parentId: string;
  fileName: string;
  boundary: string;
}): Uint8Array<ArrayBuffer> {
  const encoder = new TextEncoder();
  const metadata = JSON.stringify({
    name: input.fileName,
    mimeType: input.mimeType,
    parents: [input.parentId]
  });
  const prefix = encoder.encode(
    `--${input.boundary}\r\n` +
    "Content-Type: application/json; charset=UTF-8\r\n\r\n" +
    `${metadata}\r\n` +
    `--${input.boundary}\r\n` +
    `Content-Type: ${input.mimeType}\r\n` +
    "Content-Transfer-Encoding: binary\r\n\r\n"
  );
  const suffix = encoder.encode(`\r\n--${input.boundary}--\r\n`);
  return concatenateBytes([prefix, input.bytes, suffix]);
}

export function normalizePhotoUploadError(error: unknown): PhotoUploadError {
  if (error instanceof PhotoUploadError) return error;
  if (
    error instanceof Error &&
    error &&
    typeof error === "object" &&
    "status" in error &&
    "code" in error
  ) {
    const status = Number((error as { status?: unknown }).status);
    const code = String((error as { code?: unknown }).code ?? "");
    if (
      Number.isInteger(status) &&
      status >= 400 &&
      status <= 599 &&
      /^[a-z0-9_]{1,64}$/u.test(code)
    ) {
      return new PhotoUploadError(status, code, error.message);
    }
  }
  if (error instanceof GoogleDriveTargetError) {
    if (error.code === "unsupported_storage") {
      return new PhotoUploadError(
        409,
        "unsupported_storage",
        "Der Fotoordner liegt nicht in der freigegebenen Workspace Shared Drive."
      );
    }
    if (error.code === "forbidden") {
      return new PhotoUploadError(
        503,
        "drive_not_writable",
        "Google Drive ist für Foto-Uploads derzeit nicht schreibbereit."
      );
    }
    return new PhotoUploadError(
      409,
      "drive_target_invalid",
      "Der private Fotoordner ist nicht korrekt der Shared Drive zugeordnet."
    );
  }
  if (error instanceof GoogleDriveResponseError) {
    return new PhotoUploadError(
      502,
      "drive_upload_unverified",
      "Google Drive hat den Upload nicht eindeutig bestätigt. Es wurde kein Erfolg gemeldet."
    );
  }
  if (error instanceof GoogleWorkspaceRequestError) {
    const providerCode = classifyGoogleHttpError(error.status, error.reason);
    if (["unauthorized", "forbidden", "not_found", "quota", "unavailable"].includes(providerCode)) {
      return new PhotoUploadError(
        503,
        "drive_provider_unavailable",
        "Google Drive konnte den geschützten Upload derzeit nicht bestätigen."
      );
    }
    return new PhotoUploadError(
      502,
      "drive_provider_error",
      "Google Drive hat eine ungültige Antwort auf den Upload geliefert."
    );
  }
  if (error instanceof TypeError) {
    return new PhotoUploadError(
      503,
      "drive_provider_unavailable",
      "Google Drive ist für Foto-Uploads derzeit nicht erreichbar."
    );
  }
  return new PhotoUploadError(
    502,
    "drive_upload_unverified",
    "Der Foto-Upload konnte nicht sicher bestätigt werden."
  );
}

export function photoUploadFailureAuditFields(
  error: unknown,
  requestId?: string
): {
  action: string;
  resourceType: string;
  outcome: "denied" | "failure";
  requestId?: string;
} {
  const normalized = normalizePhotoUploadError(error);
  return {
    action: `photo.upload.error.${normalized.code}.${normalized.status}`,
    resourceType: "photo",
    outcome: normalized.status === 403 ? "denied" : "failure",
    ...(requestId ? { requestId } : {})
  };
}

export async function auditGooglePhotoUploadFailure(
  session: UserSession,
  error: unknown,
  requestId?: string
): Promise<void> {
  await appendGoogleAuditEvent({
    session,
    ...photoUploadFailureAuditFields(error, requestId)
  });
}

export async function createVerifiedGoogleDrivePhoto(input: {
  childId: string;
  folderId: string;
  bytes: Uint8Array;
  mimeType: string;
  now?: Date;
}): Promise<Photo> {
  try {
    if (!googleConfigurationStatus().drive) {
      throw new GoogleDriveTargetError("unsupported_storage");
    }
    if (!ALLOWED_PHOTO_TYPES.has(input.mimeType)) {
      throw new PhotoUploadError(
        415,
        "photo_type_unsupported",
        "Es sind nur JPG-, PNG- und WebP-Bilder erlaubt."
      );
    }
    if (input.bytes.byteLength > MAX_PHOTO_BYTES) {
      throw new PhotoUploadError(
        413,
        "photo_too_large",
        "Das Bild überschreitet das Limit von 15 MB."
      );
    }
    if (!photoSignatureMatches(input.bytes, input.mimeType)) {
      throw new PhotoUploadError(
        415,
        "photo_signature_invalid",
        "Der Bildinhalt passt nicht zum angegebenen Dateityp."
      );
    }
    const parentId = required("GOOGLE_DRIVE_PHOTOS_FOLDER_ID");
    const driveId = required("GOOGLE_DRIVE_SHARED_DRIVE_ID");
    await readDriveFolder(parentId, driveId);
    await readDriveFolder(input.folderId, driveId, parentId);

    const now = input.now ?? new Date();
    const extension = PHOTO_EXTENSION[input.mimeType];
    const timestamp = now.toISOString().replace(/\D/gu, "").slice(0, 14);
    const fileName =
      `photo_${timestamp}_${randomUUID().replaceAll("-", "").slice(0, 12)}.${extension}`;
    const boundary = `nine-friends-${randomUUID()}`;
    const body = buildGoogleDrivePhotoMultipart({
      bytes: input.bytes,
      mimeType: input.mimeType,
      parentId: input.folderId,
      fileName,
      boundary
    });
    const url = new URL("https://www.googleapis.com/upload/drive/v3/files");
    url.searchParams.set("uploadType", "multipart");
    url.searchParams.set("supportsAllDrives", "true");
    url.searchParams.set(
      "fields",
      "id,name,mimeType,createdTime,parents,driveId"
    );
    const response = await googleFetch(url.toString(), {
      method: "POST",
      headers: { "content-type": `multipart/related; boundary=${boundary}` },
      body
    });
    const payload = await response.json().catch(() => {
      throw new GoogleDriveResponseError("Google Drive returned unreadable upload metadata.");
    }) as {
      id?: string;
      name?: string;
      mimeType?: string;
      createdTime?: string;
      parents?: string[];
      driveId?: string;
    };
    if (
      !payload.id ||
      payload.name !== fileName ||
      payload.mimeType !== input.mimeType ||
      payload.driveId !== driveId ||
      !payload.parents?.includes(input.folderId)
    ) {
      throw new GoogleDriveResponseError("Google Drive returned mismatched upload metadata.");
    }
    return {
      id: payload.id,
      childId: input.childId,
      name: fileName,
      mimeType: input.mimeType,
      createdAt: payload.createdTime ?? now.toISOString(),
      previewUrl: `/api/photos/${encodeURIComponent(payload.id)}`,
      source: "google"
    };
  } catch (error) {
    throw normalizePhotoUploadError(error);
  }
}

export function assertGooglePhotoUploadRole(session: UserSession): void {
  if (!canWriteRecords(session.role)) {
    throw new PhotoUploadError(
      403,
      "photo_role_forbidden",
      "Für den Foto-Upload fehlt die erforderliche Berechtigung."
    );
  }
}

export function assertGooglePhotoUploadChild(
  child: Child | undefined
): asserts child is Child {
  if (!child) {
    throw new PhotoUploadError(
      403,
      "photo_child_forbidden",
      "Für dieses Kind besteht kein Upload-Zugriff."
    );
  }
  if (!child.photoFolderId) {
    throw normalizePhotoUploadError(new GoogleDriveTargetError("not_found"));
  }
  if (child.photoConsent !== "granted") {
    throw new PhotoUploadError(
      403,
      "photo_consent_required",
      "Vor dem Upload ist eine gültige Foto-Einwilligung erforderlich."
    );
  }
}

export async function uploadGooglePhoto(
  session: UserSession,
  childId: string,
  file: File,
  requestId?: string
): Promise<DashboardSnapshot> {
  try {
    assertGooglePhotoUploadRole(session);
    if (!ALLOWED_PHOTO_TYPES.has(file.type)) {
      throw new PhotoUploadError(
        415,
        "photo_type_unsupported",
        "Es sind nur JPG-, PNG- und WebP-Bilder erlaubt."
      );
    }
    if (file.size > MAX_PHOTO_BYTES) {
      throw new PhotoUploadError(
        413,
        "photo_too_large",
        "Das Bild überschreitet das Limit von 15 MB."
      );
    }
    const snapshot = await getGoogleSnapshot(session);
    if (!snapshot.integrations.drive) {
      if (snapshot.integrations.driveStatus === "unsupported_storage") {
        throw new GoogleDriveTargetError("unsupported_storage");
      }
      if (
        snapshot.integrations.driveStatus === "not_configured" ||
        snapshot.integrations.driveStatus === "not_found" ||
        snapshot.integrations.driveStatus === "schema"
      ) {
        throw new GoogleDriveTargetError("schema");
      }
      throw new GoogleDriveTargetError("forbidden");
    }
    const child = snapshot.children.find((item) => item.id === childId);
    assertGooglePhotoUploadChild(child);
    const bytes = new Uint8Array(await file.arrayBuffer());
    const photo = await createVerifiedGoogleDrivePhoto({
      childId,
      folderId: child.photoFolderId,
      bytes,
      mimeType: file.type
    });
    await appendGoogleAuditEvent({
      session,
      action: "photo.upload",
      resourceType: "photo",
      resourceId: photo.id,
      outcome: "success",
      ...(requestId ? { requestId } : {})
    });
    return {
      ...snapshot,
      photos: [photo, ...snapshot.photos.filter((item) => item.id !== photo.id)],
      generatedAt: new Date().toISOString()
    };
  } catch (error) {
    throw normalizePhotoUploadError(error);
  }
}

export async function downloadGooglePhoto(session: UserSession, fileId: string): Promise<{ bytes: ArrayBuffer; mimeType: string }> {
  const snapshot = await getGoogleSnapshot(session);
  const photo = snapshot.photos.find((item) => item.id === fileId);
  if (!photo) throw new Error("Photo not found or access denied.");
  const response = await googleFetch(`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(fileId)}?alt=media&supportsAllDrives=true`);
  await appendGoogleAuditEvent({
    session,
    action: "photo.read",
    resourceType: "photo",
    resourceId: fileId,
    outcome: "success"
  });
  return { bytes: await response.arrayBuffer(), mimeType: photo.mimeType };
}
