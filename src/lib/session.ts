import { createHmac, randomUUID, timingSafeEqual } from "node:crypto";

import { UserSessionSchema, type UserSession } from "./contracts";

export const SESSION_COOKIE = "nine_friends_session";
export const SESSION_TTL_SECONDS = 30 * 60;

function sessionSecret() {
  const configured = process.env.SESSION_SECRET?.trim();
  if (configured && configured.length >= 32) return configured;
  if ((process.env.DATA_MODE ?? "demo") === "demo") {
    return "demo-only-session-secret-never-use-with-real-data";
  }
  throw new Error("SESSION_SECRET must contain at least 32 characters in production mode.");
}

const sign = (value: string) =>
  createHmac("sha256", sessionSecret()).update(value).digest("base64url");

export function encodeSession(session: UserSession): string {
  const payload = Buffer.from(JSON.stringify(UserSessionSchema.parse(session))).toString("base64url");
  return `${payload}.${sign(payload)}`;
}

export function decodeSession(token: string | undefined): UserSession | null {
  if (!token) return null;
  const [payload, signature] = token.split(".");
  if (!payload || !signature) return null;
  const expected = sign(payload);
  const left = Buffer.from(signature);
  const right = Buffer.from(expected);
  if (left.length !== right.length || !timingSafeEqual(left, right)) return null;
  try {
    const parsed = UserSessionSchema.parse(
      JSON.parse(Buffer.from(payload, "base64url").toString("utf8"))
    );
    if (parsed.expiresAt <= Math.floor(Date.now() / 1000)) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function sessionFromRequest(request: Request): UserSession | null {
  const cookie = request.headers.get("cookie") ?? "";
  const value = cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${SESSION_COOKIE}=`))
    ?.slice(SESSION_COOKIE.length + 1);
  return decodeSession(value);
}

export function sessionCookie(session: UserSession): string {
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  const maxAge = Math.max(0, Math.min(
    SESSION_TTL_SECONDS,
    session.expiresAt - Math.floor(Date.now() / 1000)
  ));
  return `${SESSION_COOKIE}=${encodeSession(session)}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${maxAge}${secure}`;
}

export function expiredSessionCookie(): string {
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return `${SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0${secure}`;
}

export function sessionMetadata(
  authSource: UserSession["authSource"],
  sessionVersion = 0
): Pick<UserSession, "sessionId" | "sessionVersion" | "issuedAt" | "authSource" | "expiresAt"> {
  const now = Math.floor(Date.now() / 1000);
  return {
    sessionId: randomUUID(),
    sessionVersion,
    issuedAt: now,
    authSource,
    expiresAt: now + SESSION_TTL_SECONDS
  };
}
