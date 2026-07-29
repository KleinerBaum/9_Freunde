import { generateKeyPairSync } from "node:crypto";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { UserSession } from "../src/lib/contracts";
import {
  resetGoogleTokenCacheForTests,
  sendGoogleCommunication
} from "../src/lib/server/google-workspace";

const originalEnvironment = { ...process.env };

const session: UserSession = {
  sessionId: "session-fictional",
  userId: "admin-fictional",
  email: "admin@example.org",
  name: "Fiktive Leitung",
  role: "admin",
  childIds: [],
  sessionVersion: 0,
  issuedAt: 1_700_000_000,
  authSource: "sites",
  expiresAt: 2_000_000_000
};

const parents = [
  ["parent_id", "name", "email", "notifications_opt_in", "child_ids"],
  ["parent-1", "Fiktiver Kontakt", "parent@example.net", "true", "child-1"]
];
const children = [
  [
    "child_id", "name", "group", "primary_parent_id", "parent_email",
    "care_hours_per_week", "care_fee_cents", "meal_fee_cents"
  ],
  [
    "child-1", "Fiktives Kind", "Sonne", "parent-1", "parent@example.net",
    "30", "10000", "1000"
  ]
];
const documents = [
  [
    "document_id", "child_id", "type", "status", "title", "number",
    "period", "care_fee_cents", "meal_fee_cents", "total_cents",
    "due_date", "created_at", "drive_file_id"
  ],
  [
    "doc-1", "child-1", "invoice", "draft", "Fiktive Abrechnung",
    "R-2026-001", "2026-01", "10000", "1000", "11000",
    "2026-02-15", "2026-02-01", ""
  ]
];
const auditHeader = [[
  "event_id", "occurred_at", "actor_ref", "actor_role", "action",
  "resource_type", "resource_ref", "outcome", "request_ref"
]];

function configureEnvironment() {
  const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL =
    "portal@example-project.iam.gserviceaccount.com";
  process.env.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY = privateKey.export({
    type: "pkcs8",
    format: "pem"
  }).toString();
  process.env.GOOGLE_SHEET_ID = "sheet-id";
  process.env.GOOGLE_WORKSPACE_DOMAIN = "example.org";
  process.env.GOOGLE_CALENDAR_IMPERSONATED_USER_EMAIL = "calendar@example.org";
  process.env.GMAIL_ENABLED = "true";
  process.env.GOOGLE_GMAIL_IMPERSONATED_USER_EMAIL = "mail@example.org";
  process.env.AUDIT_HASH_SECRET = "test-audit-secret-at-least-32-characters";
}

function urlOf(input: string | URL | Request) {
  return decodeURIComponent(
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.toString()
        : input.url
  );
}

function mockGoogle(gmailSucceeds: boolean) {
  const calls: Array<{ url: string; method: string; body: string }> = [];
  vi.stubGlobal("fetch", vi.fn(async (
    input: string | URL | Request,
    init?: RequestInit
  ) => {
    const url = urlOf(input);
    const method = init?.method ?? "GET";
    const body = typeof init?.body === "string" ? init.body : "";
    calls.push({ url, method, body });

    if (url === "https://oauth2.googleapis.com/token") {
      return Response.json({ access_token: "token-fictional", expires_in: 3600 });
    }
    if (url.includes("gmail.googleapis.com")) {
      return gmailSucceeds
        ? Response.json({ id: "message-fictional" })
        : Response.json(
          { error: { errors: [{ reason: "backendError" }] } },
          { status: 503 }
        );
    }
    if (url.includes("'parents'!A:ZZ")) return Response.json({ values: parents });
    if (url.includes("'children'!A:ZZ")) return Response.json({ values: children });
    if (url.includes("'documents'!1:1")) {
      return Response.json({ values: [documents[0]] });
    }
    if (url.includes("'documents'!A:ZZ") && method === "GET") {
      return Response.json({ values: documents });
    }
    if (url.includes("'documents'!") && method === "PUT") {
      return Response.json({ updatedRows: 1 });
    }
    if (url.includes("'audit'!1:1")) return Response.json({ values: auditHeader });
    if (url.includes("'audit'!A:ZZ") && method === "POST") {
      return Response.json({ updates: { updatedRows: 1 } });
    }
    throw new Error(`Unexpected request: ${method} ${url}`);
  }));
  return calls;
}

describe("document delivery transaction order", () => {
  beforeEach(() => {
    configureEnvironment();
    resetGoogleTokenCacheForTests();
  });

  afterEach(() => {
    process.env = { ...originalEnvironment };
    resetGoogleTokenCacheForTests();
    vi.unstubAllGlobals();
  });

  it("keeps document status unchanged when Gmail delivery fails", async () => {
    const calls = mockGoogle(false);
    const result = await sendGoogleCommunication(session, {
      kind: "document",
      documentId: "doc-1",
      body: "Fiktiver Begleittext",
      reviewConfirmed: true,
      confirmed: true
    });

    expect(result).toMatchObject({
      successCount: 0,
      failureCount: 1,
      documentStatusUpdated: false
    });
    expect(calls.some((call) =>
      call.method === "PUT" && call.url.includes("'documents'!")
    )).toBe(false);
    const auditWrite = calls.find((call) =>
      call.method === "POST" && call.url.includes("'audit'!A:ZZ")
    );
    expect(auditWrite?.body).not.toContain("parent@example.net");
    expect(auditWrite?.body).not.toContain("Fiktiver Begleittext");
    expect(auditWrite?.body).not.toContain("Fiktive Abrechnung");
  });

  it("updates status only after a successful Gmail delivery", async () => {
    const calls = mockGoogle(true);
    const result = await sendGoogleCommunication(session, {
      kind: "document",
      documentId: "doc-1",
      body: "Fiktiver Begleittext",
      reviewConfirmed: true,
      confirmed: true
    });

    expect(result).toMatchObject({
      successCount: 1,
      failureCount: 0,
      documentStatusUpdated: true
    });
    const gmailIndex = calls.findIndex((call) =>
      call.url.includes("gmail.googleapis.com")
    );
    const statusIndex = calls.findIndex((call) =>
      call.method === "PUT" && call.url.includes("'documents'!")
    );
    expect(gmailIndex).toBeGreaterThan(-1);
    expect(statusIndex).toBeGreaterThan(gmailIndex);
  });
});
