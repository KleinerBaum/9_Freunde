import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { GET } from "../src/app/api/admin/integrations/health/route";
import { sessionCookie, sessionMetadata } from "../src/lib/session";

const originalEnvironment = { ...process.env };

function requestFor(role: "admin" | "parent") {
  const cookie = sessionCookie({
    ...sessionMetadata("demo"),
    userId: `${role}-user`,
    email: `${role}@example.com`,
    name: role,
    role,
    ...(role === "parent" ? { parentId: "parent-1", childIds: ["child-1"] } : { childIds: [] }),
    expiresAt: Math.floor(Date.now() / 1000) + 3600
  });
  return new Request("https://portal.example/api/admin/integrations/health", {
    headers: { cookie }
  });
}

describe("protected integration health route", () => {
  beforeEach(() => {
    process.env.DATA_MODE = "demo";
    process.env.SESSION_SECRET = "test-session-secret-at-least-32-characters";
  });

  afterEach(() => {
    process.env = { ...originalEnvironment };
  });

  it("rejects unauthenticated callers", async () => {
    const response = await GET(new Request("https://portal.example/api/admin/integrations/health"));
    expect(response.status).toBe(401);
  });

  it("rejects parent sessions", async () => {
    const response = await GET(requestFor("parent"));
    expect(response.status).toBe(403);
  });

  it("returns sanitized demo-mode checks to administrators", async () => {
    const response = await GET(requestFor("admin"));
    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({
      mode: "demo",
      sheets: { ok: false, code: "not_configured" },
      drive: { ok: false, code: "not_configured" },
      calendar: { ok: false, code: "not_configured" }
    });
    expect(response.headers.get("cache-control")).toContain("no-store");
  });
});
