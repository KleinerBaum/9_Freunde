import { HttpError, requireActiveSession, safeErrorResponse } from "../../../../lib/server/http";
import { dataMode } from "../../../../lib/server/repository";
import { downloadGooglePhoto } from "../../../../lib/server/google-workspace";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ id: string }> }): Promise<Response> {
  try {
    if (dataMode() !== "google") throw new HttpError(404, "Photo not found.");
    const session = await requireActiveSession(request);
    const { id } = await context.params;
    const photo = await downloadGooglePhoto(session, id);
    return new Response(photo.bytes, {
      headers: {
        "content-type": photo.mimeType,
        "cache-control": "private, max-age=300",
        "content-security-policy": "default-src 'none'",
        "x-content-type-options": "nosniff"
      }
    });
  } catch (error) {
    return safeErrorResponse(error);
  }
}
