import {
  HttpError,
  noStoreHeaders,
  requireActiveSession,
  safeErrorResponse
} from "../../../../../lib/server/http";
import {
  createPrivacyRequest,
  listPrivacyRequests
} from "../../../../../lib/server/repository";
import { assertSameOrigin } from "../../../../../lib/server/security";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  try {
    const session = await requireActiveSession(request);
    if (session.role !== "admin") {
      throw new HttpError(403, "Only administrators may review privacy requests.");
    }
    return Response.json(
      { requests: await listPrivacyRequests() },
      { headers: noStoreHeaders }
    );
  } catch (error) {
    return safeErrorResponse(error);
  }
}

export async function POST(request: Request): Promise<Response> {
  try {
    assertSameOrigin(request);
    const session = await requireActiveSession(request);
    if (session.role !== "admin") {
      throw new HttpError(403, "Only administrators may create privacy requests.");
    }
    const created = await createPrivacyRequest(session, await request.json());
    return Response.json(
      {
        request: {
          ...created,
          subjectId: undefined
        }
      },
      { status: 201, headers: noStoreHeaders }
    );
  } catch (error) {
    return safeErrorResponse(error);
  }
}
