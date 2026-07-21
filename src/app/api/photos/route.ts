import { ALLOWED_PHOTO_TYPES, MAX_PHOTO_BYTES } from "../../../lib/contracts";
import { HttpError, requireSession, safeErrorResponse } from "../../../lib/server/http";
import { dataMode, getAppSnapshot } from "../../../lib/server/repository";
import { uploadGooglePhoto } from "../../../lib/server/google-workspace";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  try {
    const snapshot = await getAppSnapshot(requireSession(request));
    return Response.json({ photos: snapshot.photos }, { headers: { "cache-control": "no-store, private" } });
  } catch (error) {
    return safeErrorResponse(error);
  }
}

export async function POST(request: Request): Promise<Response> {
  try {
    const session = requireSession(request);
    if (dataMode() !== "google") throw new HttpError(409, "Demo mode uses illustration placeholders; connect Google Drive to upload photos.");
    const form = await request.formData();
    const childId = String(form.get("childId") ?? "");
    const file = form.get("file");
    if (!childId || !(file instanceof File)) throw new HttpError(400, "Child and image file are required.");
    if (!ALLOWED_PHOTO_TYPES.has(file.type)) throw new HttpError(415, "Only JPG, PNG and WebP images are accepted.");
    if (file.size > MAX_PHOTO_BYTES) throw new HttpError(413, "The image exceeds the 15 MB limit.");
    await uploadGooglePhoto(session, childId, file);
    const snapshot = await getAppSnapshot(session);
    return Response.json(snapshot, { headers: { "cache-control": "no-store, private" } });
  } catch (error) {
    return safeErrorResponse(error);
  }
}
