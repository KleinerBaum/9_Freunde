import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { POST } from "../src/app/api/communications/send/route";
import type { Role } from "../src/lib/contracts";
import { sessionCookie, sessionMetadata } from "../src/lib/session";

const originalEnvironment = { ...process.env };

function requestFor(role?: Role, origin?: string) {
  const headers = new Headers({ "content-type": "application/json" });
  if (origin) headers.set("origin", origin);
  if (role) {
    headers.set("cookie", sessionCookie({
      ...sessionMetadata("demo"),
      userId: `${role}-user`,
      email: `${role}@example.org`,
      name: role,
      role,
      ...(role === "parent"
        ? { parentId: "parent-1", childIds: ["child-1"] }
        : { childIds: [] }),
      expiresAt: Math.floor(Date.now() / 1000) + 3600
    }));
  }
  return new Request("https://portal.example/api/communications/send", {
    method: "POST",
    headers,
    body: JSON.stringify({
      kind: "announcement",
      audience: "all_parents",
      subject: "Fiktiver Hinweis",
      body: "Fiktiver Inhalt",
      confirmed: true
    })
  });
}

describe("communications send route", () => {
  beforeEach(() => {
    process.env.DATA_MODE = "demo";
    process.env.SESSION_SECRET = "test-session-secret-at-least-32-characters";
  });

  afterEach(() => {
    process.env = { ...originalEnvironment };
  });

  it("rejects unauthenticated callers", async () => {
    expect((await POST(requestFor())).status).toBe(401);
  });

  it.each(["staff_write", "staff_read"] as const)(
    "rejects the %s role",
    async (role) => {
      expect((await POST(requestFor(role))).status).toBe(403);
    }
  );

  it("rejects a disabled parent session", async () => {
    expect((await POST(requestFor("parent"))).status).toBe(401);
  });

  it("keeps sending disabled in demo mode", async () => {
    const response = await POST(requestFor("admin"));
    expect(response.status).toBe(409);
    expect(await response.json()).toEqual({
      error: "Communications require Google production mode."
    });
  });

  it("rejects cross-origin send attempts before authentication", async () => {
    process.env.DATA_MODE = "google";
    process.env.APP_BASE_URL = "https://portal.example";
    const response = await POST(requestFor(undefined, "https://attacker.example"));
    expect(response.status).toBe(403);
  });
});
