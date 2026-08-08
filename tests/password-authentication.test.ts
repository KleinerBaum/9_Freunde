import { execFileSync } from "node:child_process";
import { generateKeyPairSync } from "node:crypto";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  authenticateGoogleUser,
  resetGoogleTokenCacheForTests
} from "../src/lib/server/google-workspace";

const TEST_PASSWORD = "synthetic-long-password";
const TEST_SALT = "ZmljdGlvbmFsLXNhbHQtMDAx";
const LEGACY_100K_HASH = "mLW5dmNi_vfwPH17_f3Oiib2uGlMj2Tyey2sy7UVqVI";
const CURRENT_210K_HASH = "2_n9COhXWUcS5ANpG8aXbKFxg_k3z9a98bN---HDSV4";
const CURRENT_HASH_PREFIX = "pbkdf2-sha256$210000$";

const USER_HEADERS = [
  "user_id", "email", "name", "role", "parent_id", "child_ids",
  "password_salt", "password_hash", "active", "session_version"
];

const AUDIT_HEADERS = [
  "event_id", "occurred_at", "actor_ref", "actor_role", "action",
  "resource_type", "resource_ref", "outcome", "request_ref"
];

const originalEnvironment = { ...process.env };

function configureGoogleEnvironment() {
  const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL =
    "portal@example-project.iam.gserviceaccount.com";
  process.env.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY = privateKey.export({
    type: "pkcs8",
    format: "pem"
  }).toString();
  process.env.GOOGLE_SHEET_ID = "sheet-id";
  process.env.GOOGLE_WORKSPACE_DOMAIN = "example.com";
  process.env.MANAGED_STAFF_EMAIL_DOMAIN = "example.com";
  process.env.AUDIT_HASH_SECRET = "test-audit-secret-at-least-32-characters";
  process.env.PARENT_ACCESS_ENABLED = "false";
}

type SheetHarness = {
  user: Record<string, string>;
  decoy: Record<string, string>;
  passwordWrites: number;
  credentialWriteRanges: string[];
  auditAppends: number;
  auditRows: string[][];
};

function installSheetHarness(
  passwordHash: string,
  options: {
    concurrentAccessChange?: {
      active: string;
      role: string;
      sessionVersion: string;
    };
    failPasswordWrite?: boolean;
    salt?: string;
    userId?: string;
  } = {}
): SheetHarness {
  const state: SheetHarness = {
    user: {
      user_id: options.userId ?? "user-1",
      email: "leitung@example.com",
      name: "Fiktive Leitung",
      role: "admin",
      parent_id: "",
      child_ids: "",
      password_salt: options.salt ?? TEST_SALT,
      password_hash: passwordHash,
      active: "true",
      session_version: "7"
    },
    decoy: {
      user_id: "",
      email: "andere@example.com",
      name: "Fiktive andere Person",
      role: "staff_read",
      parent_id: "",
      child_ids: "",
      password_salt: TEST_SALT,
      password_hash: `${CURRENT_HASH_PREFIX}${CURRENT_210K_HASH}`,
      active: "true",
      session_version: "3"
    },
    passwordWrites: 0,
    credentialWriteRanges: [],
    auditAppends: 0,
    auditRows: []
  };

  vi.stubGlobal("fetch", vi.fn(async (
    input: string | URL | Request,
    init?: RequestInit
  ) => {
    const url = decodeURIComponent(
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url
    );
    const method = init?.method ?? "GET";

    if (url === "https://oauth2.googleapis.com/token") {
      return Response.json({ access_token: "token", expires_in: 3600 });
    }

    if (
      url.endsWith("/values:batchUpdate") &&
      method === "POST"
    ) {
      state.passwordWrites += 1;
      if (options.failPasswordWrite) {
        return Response.json({ error: "synthetic failure" }, { status: 503 });
      }
      if (options.concurrentAccessChange) {
        state.user.active = options.concurrentAccessChange.active;
        state.user.role = options.concurrentAccessChange.role;
        state.user.session_version = options.concurrentAccessChange.sessionVersion;
      }
      const body = JSON.parse(String(init?.body ?? "{}")) as {
        data?: Array<{ range?: string; values?: unknown[][] }>;
      };
      const data = body.data ?? [];
      state.credentialWriteRanges = data.flatMap((entry) =>
        entry.range ? [entry.range] : []
      );
      for (const entry of data) {
        const match = /^'users'!([A-Z]+)(\d+)$/u.exec(entry.range ?? "");
        if (!match) throw new Error("Unexpected credential range.");
        const columnName = match[1] ?? "";
        const rowNumber = Number(match[2] ?? "0");
        const columnIndex = [...columnName].reduce(
          (index, character) => index * 26 + character.charCodeAt(0) - 64,
          0
        ) - 1;
        const field = USER_HEADERS[columnIndex];
        const target = rowNumber === 3 ? state.user : state.decoy;
        if (!field || ![2, 3].includes(rowNumber)) {
          throw new Error("Unexpected credential cell.");
        }
        target[field] = String(entry.values?.[0]?.[0] ?? "");
      }
      return Response.json({ totalUpdatedCells: data.length });
    }

    if (url.includes("sheets.googleapis.com") && url.includes("'users'!")) {
      if (method === "PUT") {
        state.passwordWrites += 1;
        if (options.failPasswordWrite) {
          return Response.json({ error: "synthetic failure" }, { status: 503 });
        }
        const body = JSON.parse(String(init?.body ?? "{}")) as {
          values?: string[][];
        };
        const values = body.values?.[0] ?? [];
        const target = url.includes("'users'!A3:J3") ? "user" : "decoy";
        state[target] = Object.fromEntries(
          USER_HEADERS.map((header, index) => [header, String(values[index] ?? "")])
        );
        return Response.json({ updatedRows: 1 });
      }
      if (url.includes("!1:1")) {
        return Response.json({ values: [USER_HEADERS] });
      }
      return Response.json({
        values: [
          USER_HEADERS,
          USER_HEADERS.map((header) => state.decoy[header] ?? ""),
          USER_HEADERS.map((header) => state.user[header] ?? "")
        ]
      });
    }

    if (url.includes("sheets.googleapis.com") && url.includes("'audit'!")) {
      if (method === "POST" && url.includes(":append")) {
        state.auditAppends += 1;
        const body = JSON.parse(String(init?.body ?? "{}")) as {
          values?: string[][];
        };
        state.auditRows.push(...(body.values ?? []));
        return Response.json({ updates: { updatedRows: 1 } });
      }
      return Response.json({ values: [AUDIT_HEADERS] });
    }

    throw new Error(`Unexpected test URL: ${method} ${url}`);
  }));

  return state;
}

describe("versioned password authentication", () => {
  beforeEach(() => {
    configureGoogleEnvironment();
    resetGoogleTokenCacheForTests();
  });

  afterEach(() => {
    process.env = { ...originalEnvironment };
    resetGoogleTokenCacheForTests();
    vi.unstubAllGlobals();
  });

  it("accepts a known unversioned 100k legacy hash and upgrades it exactly once", async () => {
    const state = installSheetHarness(LEGACY_100K_HASH);

    const first = await authenticateGoogleUser(
      "leitung@example.com",
      TEST_PASSWORD
    );

    expect(first).toMatchObject({
      userId: "user-1",
      role: "admin",
      sessionVersion: 8
    });
    expect(state.passwordWrites).toBe(1);
    expect(state.auditAppends).toBe(1);
    expect(state.user.password_salt).not.toBe(TEST_SALT);
    expect(state.user.password_hash).toMatch(
      /^pbkdf2-sha256\$210000\$[A-Za-z0-9_-]{43}$/u
    );
    expect(state.auditRows[0]?.[4]).toBe("auth.password_hash_upgraded");

    const second = await authenticateGoogleUser(
      "leitung@example.com",
      TEST_PASSWORD
    );

    expect(second).toMatchObject({ sessionVersion: 8 });
    expect(state.passwordWrites).toBe(1);
    expect(state.auditAppends).toBe(1);
  });

  it("rehashes an explicitly versioned 100k hash as legacy", async () => {
    const state = installSheetHarness(`pbkdf2-sha256$100000$${LEGACY_100K_HASH}`);

    const session = await authenticateGoogleUser(
      "leitung@example.com",
      TEST_PASSWORD
    );

    expect(session).toMatchObject({ sessionVersion: 8 });
    expect(state.passwordWrites).toBe(1);
    expect(state.auditAppends).toBe(1);
    expect(state.user.password_salt).not.toBe(TEST_SALT);
    expect(state.user.password_hash).toMatch(/^pbkdf2-sha256\$210000\$[A-Za-z0-9_-]{43}$/u);
  });

  it("migrates an unversioned 210k hash to the versioned format", async () => {
    const state = installSheetHarness(CURRENT_210K_HASH);

    const session = await authenticateGoogleUser(
      "leitung@example.com",
      TEST_PASSWORD
    );

    expect(session).toMatchObject({ sessionVersion: 8 });
    expect(state.passwordWrites).toBe(1);
    expect(state.user.password_salt).toBe(TEST_SALT);
    expect(state.user.password_hash).toBe(`${CURRENT_HASH_PREFIX}${CURRENT_210K_HASH}`);
  });

  it("uses canonical email when the migrating user_id is empty", async () => {
    const state = installSheetHarness(CURRENT_210K_HASH, { userId: "" });

    const session = await authenticateGoogleUser(
      "leitung@example.com",
      TEST_PASSWORD
    );

    expect(session).toMatchObject({
      userId: "leitung@example.com",
      sessionVersion: 8
    });
    expect(state.passwordWrites).toBe(1);
    expect(state.user.password_hash).toBe(`${CURRENT_HASH_PREFIX}${CURRENT_210K_HASH}`);
    expect(state.decoy.session_version).toBe("3");
  });

  it("accepts a versioned 210k hash without rewriting it", async () => {
    const state = installSheetHarness(`${CURRENT_HASH_PREFIX}${CURRENT_210K_HASH}`);

    const session = await authenticateGoogleUser(
      "leitung@example.com",
      TEST_PASSWORD
    );

    expect(session).toMatchObject({ sessionVersion: 7 });
    expect(state.passwordWrites).toBe(0);
    expect(state.auditAppends).toBe(0);
  });

  it("rejects a wrong password for an unversioned legacy hash without upgrading", async () => {
    const state = installSheetHarness(LEGACY_100K_HASH);

    await expect(authenticateGoogleUser(
      "leitung@example.com",
      "definitely-wrong-password"
    )).resolves.toBeNull();

    expect(state.passwordWrites).toBe(0);
    expect(state.auditAppends).toBe(0);
  });

  it.each([
    ["short", "too-short"],
    ["malformed", "!!!!!!!!!!!!!!!!!!!!!!!!"],
    ["oversized", "A".repeat(10_000)]
  ])("rejects a %s salt before key derivation", async (_label, salt) => {
    const state = installSheetHarness(
      `${CURRENT_HASH_PREFIX}${CURRENT_210K_HASH}`,
      { salt }
    );

    await expect(authenticateGoogleUser(
      "leitung@example.com",
      TEST_PASSWORD
    )).resolves.toBeNull();

    expect(state.passwordWrites).toBe(0);
    expect(state.auditAppends).toBe(0);
  });

  it.each([99_999, 100_001, 209_999, 210_001, 999_999])(
    "rejects the attacker-controlled iteration count %i",
    async (iterations) => {
      const state = installSheetHarness(
        `pbkdf2-sha256$${iterations}$${CURRENT_210K_HASH}`
      );

      await expect(authenticateGoogleUser(
        "leitung@example.com",
        TEST_PASSWORD
      )).resolves.toBeNull();

      expect(state.passwordWrites).toBe(0);
      expect(state.auditAppends).toBe(0);
    }
  );

  it("fails closed when the legacy credential upgrade cannot be written", async () => {
    const state = installSheetHarness(LEGACY_100K_HASH, {
      failPasswordWrite: true
    });

    await expect(authenticateGoogleUser(
      "leitung@example.com",
      TEST_PASSWORD
    )).rejects.toThrow(/Google Workspace request failed \(503\)/u);

    expect(state.passwordWrites).toBe(1);
    expect(state.auditAppends).toBe(0);
  });

  it("preserves a concurrent access change and returns no session", async () => {
    const state = installSheetHarness(LEGACY_100K_HASH, {
      concurrentAccessChange: {
        active: "false",
        role: "staff_read",
        sessionVersion: "8"
      }
    });

    await expect(authenticateGoogleUser(
      "leitung@example.com",
      TEST_PASSWORD
    )).rejects.toThrow(/Credential migration could not be completed safely/u);

    expect(state.credentialWriteRanges).toEqual([
      "'users'!G3",
      "'users'!H3",
      "'users'!J3"
    ]);
    expect(state.user.role).toBe("staff_read");
    expect(state.user.active).toBe("false");
    expect(state.auditAppends).toBe(0);
  });

  it("keeps the CLI generator on versioned 210k hashes", () => {
    const output = JSON.parse(execFileSync(
      process.execPath,
      ["scripts/hash-password.mjs", TEST_PASSWORD],
      { encoding: "utf8" }
    )) as { password_salt?: string; password_hash?: string };

    expect(output.password_salt).toMatch(/^[A-Za-z0-9_-]{24}$/u);
    expect(output.password_hash).toMatch(
      /^pbkdf2-sha256\$210000\$[A-Za-z0-9_-]{43}$/u
    );
    expect(output.password_hash).not.toContain("$100000$");
  });
});
