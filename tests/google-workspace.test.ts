import { generateKeyPairSync } from "node:crypto";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildGoogleJwtClaims,
  checkGoogleIntegrations,
  classifyGoogleHttpError,
  getGoogleAccessToken,
  googleConfigurationStatus,
  resetGoogleTokenCacheForTests
} from "../src/lib/server/google-workspace";

const originalEnvironment = { ...process.env };

function configureGoogleEnvironment() {
  const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL = "portal@example-project.iam.gserviceaccount.com";
  process.env.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY = privateKey.export({
    type: "pkcs8",
    format: "pem"
  }).toString();
  process.env.GOOGLE_SHEET_ID = "sheet-id";
  process.env.GOOGLE_DRIVE_PHOTOS_FOLDER_ID = "folder-id";
  process.env.GOOGLE_CALENDAR_ID = "facility@example.com";
  process.env.GOOGLE_CALENDAR_IMPERSONATED_USER_EMAIL = "organizer@example.com";
  process.env.GMAIL_ENABLED = "true";
  process.env.GOOGLE_GMAIL_IMPERSONATED_USER_EMAIL = "portal-mail@example.com";
  process.env.GOOGLE_WORKSPACE_DOMAIN = "example.com";
}

function decodeAssertion(body: BodyInit | null | undefined) {
  const params = body instanceof URLSearchParams
    ? body
    : new URLSearchParams(String(body ?? ""));
  const assertion = params.get("assertion");
  if (!assertion) throw new Error("Missing assertion.");
  const payload = assertion.split(".")[1];
  if (!payload) throw new Error("Malformed assertion.");
  return JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as Record<string, unknown>;
}

describe("Google Workspace authentication", () => {
  beforeEach(() => {
    configureGoogleEnvironment();
    resetGoogleTokenCacheForTests();
  });

  afterEach(() => {
    process.env = { ...originalEnvironment };
    resetGoogleTokenCacheForTests();
    vi.unstubAllGlobals();
  });

  it("uses only the context-specific delegated subject and scope", () => {
    expect(buildGoogleJwtClaims("workspace", 1_700_000_000)).not.toHaveProperty("sub");
    expect(buildGoogleJwtClaims("calendar", 1_700_000_000)).toMatchObject({
      sub: "organizer@example.com",
      scope: "https://www.googleapis.com/auth/calendar.events"
    });
    expect(buildGoogleJwtClaims("gmail", 1_700_000_000)).toMatchObject({
      sub: "portal-mail@example.com",
      scope: "https://www.googleapis.com/auth/gmail.send"
    });
  });

  it("uses independent caches for Workspace, Calendar, and Gmail tokens", async () => {
    const assertions: Array<Record<string, unknown>> = [];
    let tokenNumber = 0;
    vi.stubGlobal("fetch", vi.fn(async (_input: string | URL | Request, init?: RequestInit) => {
      assertions.push(decodeAssertion(init?.body));
      tokenNumber += 1;
      return Response.json({ access_token: `token-${tokenNumber}`, expires_in: 3600 });
    }));

    expect(await getGoogleAccessToken("workspace")).toBe("token-1");
    expect(await getGoogleAccessToken("workspace")).toBe("token-1");
    expect(await getGoogleAccessToken("calendar")).toBe("token-2");
    expect(await getGoogleAccessToken("calendar")).toBe("token-2");
    expect(await getGoogleAccessToken("gmail")).toBe("token-3");
    expect(await getGoogleAccessToken("gmail")).toBe("token-3");

    expect(assertions).toHaveLength(3);
    expect(assertions[0]).not.toHaveProperty("sub");
    expect(assertions[1]).toHaveProperty("sub", "organizer@example.com");
    expect(assertions[2]).toHaveProperty("sub", "portal-mail@example.com");
  });

  it("requires the delegated Calendar user before reporting Calendar configured", () => {
    expect(googleConfigurationStatus()).toEqual({
      sheets: true,
      drive: true,
      calendar: true,
      gmail: true
    });
    delete process.env.GOOGLE_CALENDAR_IMPERSONATED_USER_EMAIL;
    expect(googleConfigurationStatus().calendar).toBe(false);
  });

  it("requires a distinct managed Gmail sender", () => {
    expect(googleConfigurationStatus().gmail).toBe(true);
    process.env.GOOGLE_GMAIL_IMPERSONATED_USER_EMAIL = "organizer@example.com";
    expect(googleConfigurationStatus().gmail).toBe(false);
    process.env.GOOGLE_GMAIL_IMPERSONATED_USER_EMAIL = "portal@gmail.com";
    expect(googleConfigurationStatus().gmail).toBe(false);
    process.env.GOOGLE_GMAIL_IMPERSONATED_USER_EMAIL = "portal-mail@other.example";
    expect(googleConfigurationStatus().gmail).toBe(false);
  });

  it("checks Gmail by delegated token issuance without sending a message", async () => {
    const sheetHeaders: Record<string, string[]> = {
      children: [
        "child_id", "name", "birthdate", "start_date", "group", "status",
        "primary_parent_id", "parent_email", "allergies", "dietary",
        "languages_at_home", "care_hours_per_week", "care_fee_cents",
        "meal_fee_cents", "folder_id", "photo_consent", "download_consent",
        "notes_parent_visible", "notes_internal", "updated_at"
      ],
      parents: [
        "parent_id", "name", "email", "phone", "phone2", "address",
        "preferred_language", "emergency_contact_name",
        "emergency_contact_phone", "notifications_opt_in", "child_ids",
        "updated_at"
      ],
      users: [
        "user_id", "email", "name", "role", "parent_id", "child_ids",
        "password_salt", "password_hash", "active", "session_version"
      ],
      documents: [
        "document_id", "child_id", "type", "status", "title", "number",
        "period", "care_fee_cents", "meal_fee_cents", "total_cents",
        "due_date", "created_at", "drive_file_id"
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
      privacy_requests: [
        "request_id", "type", "subject_type", "subject_ref", "status",
        "requested_at", "requested_by", "reviewed_at", "reviewed_by",
        "due_at", "confirmation"
      ]
    };
    const urls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (
      input: string | URL | Request
    ) => {
      const url = decodeURIComponent(
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url
      );
      urls.push(url);
      if (url === "https://oauth2.googleapis.com/token") {
        return Response.json({ access_token: "token", expires_in: 3600 });
      }
      if (url.includes("sheets.googleapis.com")) {
        const tab = Object.keys(sheetHeaders).find((name) =>
          url.includes(`'${name}'!1:1`)
        );
        if (!tab) throw new Error(`Unexpected Sheet URL: ${url}`);
        return Response.json({ values: [sheetHeaders[tab]] });
      }
      if (url.includes("www.googleapis.com/drive")) {
        return Response.json({
          mimeType: "application/vnd.google-apps.folder",
          trashed: false,
          capabilities: { canAddChildren: true }
        });
      }
      if (url.includes("www.googleapis.com/calendar")) {
        return Response.json({ items: [] });
      }
      throw new Error(`Unexpected integration URL: ${url}`);
    }));

    const health = await checkGoogleIntegrations();

    expect(health.gmail).toEqual({ ok: true, code: "ok" });
    expect(urls.some((url) => url.includes("gmail.googleapis.com"))).toBe(false);
    expect(urls.filter((url) =>
      url === "https://oauth2.googleapis.com/token"
    )).toHaveLength(3);
  });

  it.each([
    [401, undefined, "unauthorized"],
    [403, "insufficientPermissions", "forbidden"],
    [403, "storageQuotaExceeded", "quota"],
    [404, undefined, "not_found"],
    [429, undefined, "quota"],
    [503, undefined, "unavailable"]
  ] as const)("sanitizes Google status %s as %s", (status, reason, expected) => {
    expect(classifyGoogleHttpError(status, reason)).toBe(expected);
  });
});
