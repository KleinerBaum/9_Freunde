import type { UserSession } from "../contracts";
import { sessionFromRequest } from "../session";

export function requireSession(request: Request): UserSession {
  const session = sessionFromRequest(request);
  if (!session) throw new HttpError(401, "Please sign in to continue.");
  return session;
}

export class HttpError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

export function safeErrorResponse(error: unknown): Response {
  const status = error instanceof HttpError ? error.status : 400;
  const message = error instanceof Error ? error.message : "The request could not be completed.";
  return Response.json({ error: message }, { status });
}

export const noStoreHeaders = {
  "cache-control": "no-store, private",
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer"
};
