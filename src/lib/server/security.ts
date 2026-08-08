import { createHmac } from "node:crypto";

import type { Role } from "../contracts";

export const SITES_USER_EMAIL_HEADER = "oai-authenticated-user-email";
export const SITES_USER_NAME_HEADER = "oai-authenticated-user-full-name";
export const SITES_USER_NAME_ENCODING_HEADER =
  "oai-authenticated-user-full-name-encoding";

type LoginAttempt = {
  failures: number;
  windowStartedAt: number;
  blockedUntil: number;
};

const securityState = globalThis as typeof globalThis & {
  __nineFriendsLoginAttempts?: Map<string, LoginAttempt>;
};

const loginAttempts = () => {
  securityState.__nineFriendsLoginAttempts ??= new Map();
  return securityState.__nineFriendsLoginAttempts;
};

const securitySecret = () =>
  process.env.AUDIT_HASH_SECRET?.trim() ||
  process.env.SESSION_SECRET?.trim() ||
  "demo-only-security-hash-secret";

const googleModeConfigured = () =>
  process.env.DATA_MODE?.trim().toLowerCase() === "google";

export function pseudonymousId(value: string): string {
  return createHmac("sha256", securitySecret())
    .update(value.trim().toLowerCase())
    .digest("base64url")
    .slice(0, 32);
}

export function productionAuthMode(): "sites" | "password" {
  const configured = process.env.AUTH_MODE?.trim().toLowerCase();
  if (configured === "password" || configured === "sites") return configured;
  return "password";
}

export function parentAccessEnabled(): boolean {
  return googleModeConfigured() &&
    process.env.PARENT_ACCESS_ENABLED?.trim().toLowerCase() === "true";
}

export function managedStaffDomain(): string | null {
  const value = (
    process.env.MANAGED_STAFF_EMAIL_DOMAIN ||
    process.env.GOOGLE_WORKSPACE_DOMAIN
  )?.trim().toLowerCase();
  return value ? value.replace(/^@/u, "") : null;
}

export function assertManagedStaffIdentity(email: string, role: Role): void {
  if (role === "parent") return;
  const domain = managedStaffDomain();
  if (!domain || !email.toLowerCase().endsWith(`@${domain}`)) {
    throw new Error("Staff access requires an approved managed Workspace account.");
  }
}

export function sitesIdentity(request: Request): {
  email: string;
  name?: string;
} | null {
  const email = request.headers.get(SITES_USER_EMAIL_HEADER)?.trim().toLowerCase();
  if (!email) return null;
  const encodedName = request.headers.get(SITES_USER_NAME_HEADER)?.trim();
  const encoding = request.headers.get(SITES_USER_NAME_ENCODING_HEADER);
  if (!encodedName || encoding !== "percent-encoded-utf-8") return { email };
  try {
    const name = decodeURIComponent(encodedName).trim();
    return name ? { email, name } : { email };
  } catch {
    return { email };
  }
}

function loginKey(email: string, request: Request): string {
  const forwarded = request.headers.get("cf-connecting-ip") ||
    request.headers.get("x-forwarded-for")?.split(",")[0] ||
    "unknown";
  return pseudonymousId(`${email}|${forwarded}`);
}

export function assertLoginAllowed(email: string, request: Request): void {
  const key = loginKey(email, request);
  const attempt = loginAttempts().get(key);
  if (!attempt) return;
  const now = Date.now();
  if (attempt.blockedUntil > now) {
    const error = new Error("Too many sign-in attempts. Try again later.");
    Object.assign(error, { status: 429, retryAfter: Math.ceil((attempt.blockedUntil - now) / 1000) });
    throw error;
  }
  if (now - attempt.windowStartedAt > 15 * 60_000) loginAttempts().delete(key);
}

export function recordLoginFailure(email: string, request: Request): void {
  const key = loginKey(email, request);
  const now = Date.now();
  const previous = loginAttempts().get(key);
  const current = !previous || now - previous.windowStartedAt > 15 * 60_000
    ? { failures: 0, windowStartedAt: now, blockedUntil: 0 }
    : previous;
  current.failures += 1;
  if (current.failures >= 5) current.blockedUntil = now + 30 * 60_000;
  loginAttempts().set(key, current);
}

export function recordLoginSuccess(email: string, request: Request): void {
  loginAttempts().delete(loginKey(email, request));
}

export function assertSameOrigin(request: Request): void {
  if (!["POST", "PUT", "PATCH", "DELETE"].includes(request.method)) return;
  const origin = request.headers.get("origin");
  if (!origin) {
    if (process.env.NODE_ENV === "test" || !googleModeConfigured()) return;
    const error = new Error("Missing request origin.");
    Object.assign(error, { status: 403 });
    throw error;
  }
  const configuredBaseUrl = process.env.APP_BASE_URL?.trim();
  if (googleModeConfigured() && !configuredBaseUrl) {
    const error = new Error("Production base URL is not configured.");
    Object.assign(error, { status: 503 });
    throw error;
  }
  const expected = new URL(configuredBaseUrl || request.url).origin;
  if (origin !== expected) {
    const error = new Error("Request origin is not allowed.");
    Object.assign(error, { status: 403 });
    throw error;
  }
}

export const browserSecurityHeaders = {
  "content-security-policy": [
    "default-src 'self'",
    "base-uri 'self'",
    "connect-src 'self'",
    "font-src 'self' data:",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "img-src 'self' data: blob:",
    "object-src 'none'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'"
  ].join("; "),
  "cross-origin-opener-policy": "same-origin",
  "cross-origin-resource-policy": "same-origin",
  "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
  "referrer-policy": "no-referrer",
  "x-content-type-options": "nosniff",
  "x-frame-options": "DENY"
} as const;

export function resetSecurityStateForTests(): void {
  securityState.__nineFriendsLoginAttempts = new Map();
}
