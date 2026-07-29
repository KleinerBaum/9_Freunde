import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { dataMode } from "@/lib/server/repository";
import { UpdateUserAccessSchema } from "@/lib/contracts";
import { POST as MCP_POST } from "@/app/mcp/route";
import {
  assertLoginAllowed,
  assertManagedStaffIdentity,
  assertSameOrigin,
  browserSecurityHeaders,
  recordLoginFailure,
  resetSecurityStateForTests,
  sitesIdentity
} from "@/lib/server/security";

const originalEnvironment = { ...process.env };

describe("production security gates", () => {
  beforeEach(() => {
    process.env.DATA_MODE = "google";
    process.env.REAL_DATA_APPROVED = "false";
    process.env.AUTH_MODE = "sites";
    process.env.APP_BASE_URL = "https://portal.example";
    process.env.MANAGED_STAFF_EMAIL_DOMAIN = "kita.example";
    process.env.GOOGLE_WORKSPACE_DOMAIN = "kita.example";
    process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL =
      "portal@example-project.iam.gserviceaccount.com";
    process.env.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY = "test-private-key";
    process.env.GOOGLE_SHEET_ID = "sheet-id";
    process.env.GOOGLE_DRIVE_PHOTOS_FOLDER_ID = "drive-id";
    process.env.GOOGLE_CALENDAR_ID = "calendar-id";
    process.env.GOOGLE_CALENDAR_IMPERSONATED_USER_EMAIL =
      "calendar@kita.example";
    process.env.GMAIL_ENABLED = "true";
    process.env.GOOGLE_GMAIL_IMPERSONATED_USER_EMAIL =
      "mail@kita.example";
    process.env.PRIVACY_CONTROLLER_NAME = "Fictional Provider";
    process.env.PRIVACY_CONTROLLER_ADDRESS = "Example address";
    process.env.PRIVACY_CONTACT_EMAIL = "privacy@kita.example";
    process.env.PRIVACY_DPO_EMAIL = "dpo@kita.example";
    process.env.LEGAL_REPRESENTATIVE = "Fictional Representative";
    process.env.LEGAL_REGISTER = "Fictional Register";
    process.env.LEGAL_SUPERVISORY_AUTHORITY = "Fictional Authority";
    process.env.SESSION_SECRET = "test-session-secret-at-least-32-characters";
    process.env.AUDIT_HASH_SECRET = "test-audit-secret-at-least-32-characters";
    resetSecurityStateForTests();
  });

  afterEach(() => {
    process.env = { ...originalEnvironment };
    resetSecurityStateForTests();
  });

  it("falls back to fictional demo data without signed real-data approval", () => {
    expect(dataMode()).toBe("demo");
    process.env.REAL_DATA_APPROVED = "true";
    expect(dataMode()).toBe("google");
    process.env.GMAIL_ENABLED = "false";
    expect(dataMode()).toBe("demo");
  });

  it("accepts only staff accounts from the managed domain", () => {
    expect(() =>
      assertManagedStaffIdentity("leitung@kita.example", "staff_write")
    ).not.toThrow();
    expect(() =>
      assertManagedStaffIdentity("leitung@gmail.com", "admin")
    ).toThrow(/managed Workspace account/u);
  });

  it("reads the trusted Sites identity and decodes its display name", () => {
    const identity = sitesIdentity(new Request("https://portal.example", {
      headers: {
        "oai-authenticated-user-email": "LEITUNG@KITA.EXAMPLE",
        "oai-authenticated-user-full-name": "Mara%20Klein",
        "oai-authenticated-user-full-name-encoding": "percent-encoded-utf-8"
      }
    }));
    expect(identity).toEqual({
      email: "leitung@kita.example",
      name: "Mara Klein"
    });
  });

  it("rejects cross-origin unsafe requests", () => {
    const request = new Request("https://portal.example/api/app/actions", {
      method: "POST",
      headers: { origin: "https://attacker.example" }
    });
    expect(() => assertSameOrigin(request)).toThrow(/not allowed/u);
  });

  it("locks an identity and address after repeated failures", () => {
    const request = new Request("https://portal.example/api/auth/login", {
      method: "POST",
      headers: { "cf-connecting-ip": "192.0.2.10" }
    });
    for (let index = 0; index < 5; index += 1) {
      recordLoginFailure("leitung@kita.example", request);
    }
    expect(() =>
      assertLoginAllowed("leitung@kita.example", request)
    ).toThrow(/Too many sign-in attempts/u);
  });

  it("defines clickjacking, MIME, permission, and CSP protections", () => {
    expect(browserSecurityHeaders["x-frame-options"]).toBe("DENY");
    expect(browserSecurityHeaders["x-content-type-options"]).toBe("nosniff");
    expect(browserSecurityHeaders["permissions-policy"]).toContain("camera=()");
    expect(browserSecurityHeaders["content-security-policy"]).toContain(
      "frame-ancestors 'none'"
    );
  });

  it("requires confirmation for role and access changes", () => {
    expect(UpdateUserAccessSchema.safeParse({
      userId: "user-1",
      role: "staff_read",
      active: true,
      confirmation: false
    }).success).toBe(false);
  });

  it("hides the MCP endpoint during the browser-only staff pilot", async () => {
    process.env.REAL_DATA_APPROVED = "true";
    process.env.MCP_ENABLED = "false";
    const response = await MCP_POST(new Request(
      "https://portal.example/api/mcp",
      { method: "POST" }
    ));
    expect(response.status).toBe(404);
  });
});
