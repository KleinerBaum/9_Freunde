import { generateKeyPairSync } from "node:crypto";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildGoogleJwtClaims,
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

  it("adds a delegated subject only to Calendar claims", () => {
    expect(buildGoogleJwtClaims("workspace", 1_700_000_000)).not.toHaveProperty("sub");
    expect(buildGoogleJwtClaims("calendar", 1_700_000_000)).toMatchObject({
      sub: "organizer@example.com",
      scope: "https://www.googleapis.com/auth/calendar.events"
    });
  });

  it("uses independent caches for Workspace and Calendar tokens", async () => {
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

    expect(assertions).toHaveLength(2);
    expect(assertions[0]).not.toHaveProperty("sub");
    expect(assertions[1]).toHaveProperty("sub", "organizer@example.com");
  });

  it("requires the delegated Calendar user before reporting Calendar configured", () => {
    expect(googleConfigurationStatus()).toEqual({
      sheets: true,
      drive: true,
      calendar: true
    });
    delete process.env.GOOGLE_CALENDAR_IMPERSONATED_USER_EMAIL;
    expect(googleConfigurationStatus().calendar).toBe(false);
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
