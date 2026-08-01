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
  constructor(
    public readonly status: number,
    message: string,
    public readonly code?: string
  ) {
    super(message);
  }
}

const SAFE_ERROR_CODE = /^[a-z0-9_]{1,64}$/u;
const SAFE_REQUEST_ID = /^[A-Za-z0-9._:-]{1,128}$/u;

export function safeErrorMetadata(error: unknown): {
  status: number;
  code: string;
} {
  const structuralStatus = error && typeof error === "object" && "status" in error
    ? Number((error as { status?: unknown }).status)
    : NaN;
  const structuralCode = error && typeof error === "object" && "code" in error
    ? String((error as { code?: unknown }).code ?? "")
    : "";
  return {
    status: error instanceof HttpError
      ? error.status
      : Number.isInteger(structuralStatus) && structuralStatus >= 400 && structuralStatus <= 599
        ? structuralStatus
        : 400,
    code: SAFE_ERROR_CODE.test(structuralCode) ? structuralCode : "request_failed"
  };
}

export function requestIdFromRequest(request: Request): string {
  const candidate =
    request.headers.get("cf-ray") ||
    request.headers.get("x-request-id") ||
    "";
  return SAFE_REQUEST_ID.test(candidate) ? candidate : "unavailable";
}

export function logSafeRouteError(error: unknown, requestId: string): void {
  const metadata = safeErrorMetadata(error);
  const safeRequestId = SAFE_REQUEST_ID.test(requestId) ? requestId : "unavailable";
  console.error(JSON.stringify({ ...metadata, requestId: safeRequestId }));
}

export function safeErrorResponse(error: unknown): Response {
  const { status, code } = safeErrorMetadata(error);
  const hasExplicitCode = error && typeof error === "object" && "code" in error &&
    SAFE_ERROR_CODE.test(String((error as { code?: unknown }).code ?? ""));
  const structuralStatus = error && typeof error === "object" && "status" in error
    ? Number((error as { status?: unknown }).status)
    : NaN;
  const message = error instanceof HttpError ||
    (Number.isInteger(structuralStatus) && error instanceof Error)
    ? error.message
    : "The request could not be completed.";
  const headers = new Headers(noStoreHeaders);
  if (status === 429 && error && typeof error === "object" && "retryAfter" in error) {
    headers.set("retry-after", String((error as { retryAfter: unknown }).retryAfter));
  }
  return Response.json(
    hasExplicitCode ? { error: message, code } : { error: message },
    { status, headers }
  );
}

export const noStoreHeaders = {
  "cache-control": "no-store, private",
  "x-content-type-options": "nosniff",
  "referrer-policy": "no-referrer"
};
