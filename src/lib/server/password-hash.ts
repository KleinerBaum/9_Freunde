import { timingSafeEqual } from "node:crypto";

export const CURRENT_PASSWORD_HASH_ITERATIONS = 210_000;
export const LEGACY_PASSWORD_HASH_ITERATIONS = 100_000;

const PASSWORD_HASH_SCHEME = "pbkdf2-sha256";
const PASSWORD_HASH_BYTES = 32;
const PASSWORD_SALT_BYTES = 18;
const BASE64URL_SALT = /^[A-Za-z0-9_-]{24}$/u;
const BASE64URL_DIGEST = /^[A-Za-z0-9_-]{43}$/u;
const VERSIONED_PASSWORD_HASH =
  /^pbkdf2-sha256\$(100000|210000)\$([A-Za-z0-9_-]{43})$/u;

type AllowedIterations =
  | typeof CURRENT_PASSWORD_HASH_ITERATIONS
  | typeof LEGACY_PASSWORD_HASH_ITERATIONS;

export type PasswordHashVerification =
  | { valid: false }
  | {
      valid: true;
      iterations: AllowedIterations;
      upgrade: "none" | "version" | "rehash";
      replacementHash?: string;
    };

function decodeDigest(value: string): Uint8Array | null {
  if (!BASE64URL_DIGEST.test(value)) return null;
  try {
    const decoded = Buffer.from(value, "base64url");
    if (
      decoded.length !== PASSWORD_HASH_BYTES ||
      decoded.toString("base64url") !== value
    ) {
      return null;
    }
    return new Uint8Array(decoded);
  } catch {
    return null;
  }
}

function isCanonicalSalt(value: string): boolean {
  if (!BASE64URL_SALT.test(value)) return false;
  try {
    const decoded = Buffer.from(value, "base64url");
    return decoded.length === PASSWORD_SALT_BYTES &&
      decoded.toString("base64url") === value;
  } catch {
    return false;
  }
}

async function derivePasswordDigest(
  password: string,
  salt: string,
  iterations: AllowedIterations
): Promise<Uint8Array> {
  const encoder = new TextEncoder();
  const key = await globalThis.crypto.subtle.importKey(
    "raw",
    encoder.encode(password),
    "PBKDF2",
    false,
    ["deriveBits"]
  );
  const bits = await globalThis.crypto.subtle.deriveBits(
    {
      name: "PBKDF2",
      hash: "SHA-256",
      salt: encoder.encode(salt),
      iterations
    },
    key,
    PASSWORD_HASH_BYTES * 8
  );
  return new Uint8Array(bits);
}

function digestMatches(actual: Uint8Array, expected: Uint8Array): boolean {
  return actual.length === expected.length &&
    timingSafeEqual(Buffer.from(actual), Buffer.from(expected));
}

function formatCurrentPasswordHash(digest: string): string {
  if (!decodeDigest(digest)) {
    throw new Error("Cannot format an invalid password digest.");
  }
  return `${PASSWORD_HASH_SCHEME}$${CURRENT_PASSWORD_HASH_ITERATIONS}$${digest}`;
}

async function matchesPassword(
  password: string,
  salt: string,
  iterations: AllowedIterations,
  expected: Uint8Array
): Promise<boolean> {
  const actual = await derivePasswordDigest(password, salt, iterations);
  return digestMatches(actual, expected);
}

export async function verifyPasswordHash(
  password: string,
  salt: string,
  storedHash: string
): Promise<PasswordHashVerification> {
  if (!isCanonicalSalt(salt)) return { valid: false };

  const versioned = VERSIONED_PASSWORD_HASH.exec(storedHash);
  if (versioned) {
    const iterations = Number(versioned[1]) as AllowedIterations;
    const digest = versioned[2];
    const expected = digest ? decodeDigest(digest) : null;
    if (!expected) return { valid: false };
    const valid = await matchesPassword(
      password,
      salt,
      iterations,
      expected
    );
    if (!valid) return { valid: false };
    return {
      valid: true,
      iterations,
      upgrade: iterations === CURRENT_PASSWORD_HASH_ITERATIONS
        ? "none"
        : "rehash"
    };
  }

  const expected = decodeDigest(storedHash);
  if (!expected) return { valid: false };

  if (await matchesPassword(
    password,
    salt,
    CURRENT_PASSWORD_HASH_ITERATIONS,
    expected
  )) {
    return {
      valid: true,
      iterations: CURRENT_PASSWORD_HASH_ITERATIONS,
      upgrade: "version",
      replacementHash: formatCurrentPasswordHash(storedHash)
    };
  }

  if (await matchesPassword(
    password,
    salt,
    LEGACY_PASSWORD_HASH_ITERATIONS,
    expected
  )) {
    return {
      valid: true,
      iterations: LEGACY_PASSWORD_HASH_ITERATIONS,
      upgrade: "rehash"
    };
  }

  return { valid: false };
}

export async function createCurrentPasswordHash(
  password: string
): Promise<{ passwordSalt: string; passwordHash: string }> {
  const saltBytes = new Uint8Array(PASSWORD_SALT_BYTES);
  globalThis.crypto.getRandomValues(saltBytes);
  const passwordSalt = Buffer.from(saltBytes).toString("base64url");
  const digest = await derivePasswordDigest(
    password,
    passwordSalt,
    CURRENT_PASSWORD_HASH_ITERATIONS
  );
  return {
    passwordSalt,
    passwordHash: formatCurrentPasswordHash(
      Buffer.from(digest).toString("base64url")
    )
  };
}
