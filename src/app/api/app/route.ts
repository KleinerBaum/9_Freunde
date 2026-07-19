import { requireSession, safeErrorResponse, noStoreHeaders } from "@/lib/server/http";
import { getAppSnapshot } from "@/lib/server/repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  try {
    const snapshot = await getAppSnapshot(requireSession(request));
    return Response.json(snapshot, { headers: noStoreHeaders });
  } catch (error) {
    return safeErrorResponse(error);
  }
}
