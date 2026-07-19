import { describe, expect, it } from "vitest";

import { decodeSession, encodeSession } from "@/lib/session";

describe("signed sessions", () => {
  it("round-trips a valid session", () => {
    const session = {
      userId: "user-test",
      email: "test@example.test",
      name: "Test User",
      role: "parent" as const,
      parentId: "parent-test",
      childIds: ["child-test"],
      expiresAt: Math.floor(Date.now() / 1000) + 3600
    };
    expect(decodeSession(encodeSession(session))).toEqual(session);
  });

  it("rejects a modified signature", () => {
    const token = encodeSession({
      userId: "user-test",
      email: "test@example.test",
      name: "Test User",
      role: "admin",
      childIds: [],
      expiresAt: Math.floor(Date.now() / 1000) + 3600
    });
    expect(decodeSession(`${token.slice(0, -2)}xx`)).toBeNull();
  });

  it("rejects an expired session", () => {
    const token = encodeSession({
      userId: "user-test",
      email: "test@example.test",
      name: "Test User",
      role: "admin",
      childIds: [],
      expiresAt: 1
    });
    expect(decodeSession(token)).toBeNull();
  });
});
