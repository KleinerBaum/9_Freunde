import { dataMode } from "../../../../../lib/server/repository";
import { checkGoogleIntegrations } from "../../../../../lib/server/google-workspace";
import {
  HttpError,
  noStoreHeaders,
  requireActiveSession,
  safeErrorResponse
} from "../../../../../lib/server/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  try {
    const session = await requireActiveSession(request);
    if (session.role !== "admin") {
      throw new HttpError(403, "This check is available to staff only.");
    }
    if (dataMode() !== "google") {
      return Response.json({
        mode: "demo",
        checkedAt: new Date().toISOString(),
        sheets: { ok: false, code: "not_configured" },
        drive: { ok: false, code: "not_configured" },
        calendar: { ok: false, code: "not_configured" }
      }, { headers: noStoreHeaders });
    }
    return Response.json(
      { mode: "google", ...await checkGoogleIntegrations() },
      { headers: noStoreHeaders }
    );
  } catch (error) {
    return safeErrorResponse(error);
  }
}
