import {
  HttpError,
  noStoreHeaders,
  requireActiveSession,
  safeErrorResponse
} from "../../../../../lib/server/http";
import { updateUserAccess } from "../../../../../lib/server/repository";
import { assertSameOrigin } from "../../../../../lib/server/security";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function PATCH(request: Request): Promise<Response> {
  try {
    assertSameOrigin(request);
    const session = await requireActiveSession(request);
    if (session.role !== "admin") {
      throw new HttpError(403, "Only administrators may change user access.");
    }
    const result = await updateUserAccess(session, await request.json());
    return Response.json({ access: result }, { headers: noStoreHeaders });
  } catch (error) {
    return safeErrorResponse(error);
  }
}
