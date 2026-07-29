import {
  HttpError,
  noStoreHeaders,
  requireActiveSession,
  safeErrorResponse
} from "../../../../lib/server/http";
import {
  dataMode,
  getAppSnapshot,
  sendCommunication
} from "../../../../lib/server/repository";
import { assertSameOrigin } from "../../../../lib/server/security";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request): Promise<Response> {
  try {
    assertSameOrigin(request);
    const session = await requireActiveSession(request);
    if (session.role !== "admin") {
      throw new HttpError(403, "Only administrators may send communications.");
    }
    if (dataMode() !== "google") {
      throw new HttpError(409, "Communications require Google production mode.");
    }
    const result = await sendCommunication(session, await request.json());
    const snapshot = await getAppSnapshot(session);
    return Response.json({ result, snapshot }, { headers: noStoreHeaders });
  } catch (error) {
    return safeErrorResponse(error);
  }
}
