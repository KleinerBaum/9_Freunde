import type { UserSession } from "../contracts";
import { sessionFromRequest } from "../session";
import { validateSession } from "./repository";

export function requireSession(request: Request): UserSession {
  const session = sessionFromRequest(request);
  if (!session) throw new HttpError(401, "Please sign in to continue.");
  return session;
}

export async function requireActiveSession(request: Request): Promise<UserSession> {
  const session = requireSession(request);
  if (!await validateSession(session)) {
    throw new HttpError(401, "Your session is no longer active. Please sign in again.");
  }
  return session;
}

export class HttpError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

export function safeErrorResponse(error: unknown): Response {
  const structuralStatus = error && typeof error === "object" && "status" in error
    ? Number((error as { status?: unknown }).status)
    : NaN;
  const status = error instanceof HttpError
    ? error.status
    : Number.isInteger(structuralStatus) && structuralStatus >= 400 && structuralStatus <= 599
      ? structuralStatus
      : 400;
  const message = error instanceof HttpError ||
    (Number.isInteger(structuralStatus) && error instanceof Error)
    ? error.message
    : "The request could not be completed.";
  const headers = new Headers(noStoreHeaders);
  if (status === 429 && error && typeof error === "object" && "retryAfter" in error) {
    headers.set("retry-after", String((error as { retryAfter: unknown }).retryAfter));
  }
  return Response.json({ error: message }, { status, headers });
}

export const noStoreHeaders = {
  "cache-control": "no-store, private",
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer"
};
