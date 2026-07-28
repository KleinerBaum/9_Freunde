import { requireActiveSession, safeErrorResponse, noStoreHeaders } from "../../../lib/server/http";
import { appendGoogleAuditEvent } from "../../../lib/server/google-workspace";
import { dataMode, getAppSnapshot } from "../../../lib/server/repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  try {
    const session = await requireActiveSession(request);
    const snapshot = await getAppSnapshot(session);
    if (dataMode() === "google") {
      await appendGoogleAuditEvent({
        session,
        action: "data.snapshot.read",
        resourceType: "portal",
        outcome: "success"
      });
    }
    return Response.json(snapshot, { headers: noStoreHeaders });
  } catch (error) {
    return safeErrorResponse(error);
  }
}
