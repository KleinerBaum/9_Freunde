import { LoginSchema } from "../../../../lib/contracts";
import { dataMode, authenticateUser } from "../../../../lib/server/repository";
import { appendGoogleAuditEvent } from "../../../../lib/server/google-workspace";
import { safeErrorResponse } from "../../../../lib/server/http";
import {
  assertLoginAllowed,
  assertSameOrigin,
  productionAuthMode,
  recordLoginFailure,
  recordLoginSuccess
} from "../../../../lib/server/security";
import { sessionCookie } from "../../../../lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request): Promise<Response> {
  try {
    assertSameOrigin(request);
    if (dataMode() === "google" && productionAuthMode() !== "password") {
      return Response.json(
        { error: "Production access uses the approved Sites identity." },
        { status: 409, headers: { "cache-control": "no-store" } }
      );
    }
    const input = LoginSchema.parse(await request.json());
    assertLoginAllowed(input.email, request);
    const session = await authenticateUser(input.email, input.password);
    if (!session) {
      recordLoginFailure(input.email, request);
      if (dataMode() === "google") {
        await appendGoogleAuditEvent({
          actorEmail: input.email,
          actorRole: "unknown",
          action: "auth.password",
          resourceType: "session",
          outcome: "denied"
        });
      }
      return Response.json(
        { error: "E-Mail oder Passwort ist nicht korrekt." },
        { status: 401, headers: { "cache-control": "no-store" } }
      );
    }
    recordLoginSuccess(input.email, request);
    if (dataMode() === "google") {
      await appendGoogleAuditEvent({
        session,
        action: "auth.password",
        resourceType: "session",
        resourceId: session.sessionId,
        outcome: "success"
      });
    }
    return Response.json({ session }, {
      headers: {
        "set-cookie": sessionCookie(session),
        "cache-control": "no-store",
        "x-content-type-options": "nosniff"
      }
    });
  } catch (error) {
    return safeErrorResponse(error);
  }
}
