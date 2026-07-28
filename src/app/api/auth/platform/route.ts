import { sessionCookie } from "../../../../lib/session";
import { appendGoogleAuditEvent } from "../../../../lib/server/google-workspace";
import { safeErrorResponse } from "../../../../lib/server/http";
import {
  authenticateSitesUser,
  dataMode
} from "../../../../lib/server/repository";
import {
  assertSameOrigin,
  productionAuthMode,
  sitesIdentity
} from "../../../../lib/server/security";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request): Promise<Response> {
  try {
    assertSameOrigin(request);
    if (dataMode() !== "google" || productionAuthMode() !== "sites") {
      return Response.json(
        { error: "Managed Sites identity is not enabled." },
        { status: 409, headers: { "cache-control": "no-store" } }
      );
    }
    const identity = sitesIdentity(request);
    if (!identity) {
      return Response.json(
        { error: "No authenticated Sites identity was provided." },
        { status: 401, headers: { "cache-control": "no-store" } }
      );
    }
    const session = await authenticateSitesUser(identity.email, identity.name);
    if (!session) {
      await appendGoogleAuditEvent({
        actorEmail: identity.email,
        actorRole: "unknown",
        action: "auth.sites",
        resourceType: "session",
        outcome: "denied"
      });
      return Response.json(
        { error: "This managed account is not approved for the portal." },
        { status: 403, headers: { "cache-control": "no-store" } }
      );
    }
    await appendGoogleAuditEvent({
      session,
      action: "auth.sites",
      resourceType: "session",
      resourceId: session.sessionId,
      outcome: "success"
    });
    return Response.json(
      { session },
      {
        headers: {
          "set-cookie": sessionCookie(session),
          "cache-control": "no-store",
          "x-content-type-options": "nosniff"
        }
      }
    );
  } catch (error) {
    return safeErrorResponse(error);
  }
}
