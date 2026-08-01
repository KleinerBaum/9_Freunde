import { ALLOWED_PHOTO_TYPES, MAX_PHOTO_BYTES } from "../../../lib/contracts";
import type { UserSession } from "../../../lib/contracts";
import {
  HttpError,
  logSafeRouteError,
  requestIdFromRequest,
  requireActiveSession,
  safeErrorResponse
} from "../../../lib/server/http";
import { dataMode, getAppSnapshot } from "../../../lib/server/repository";
import {
  appendGoogleAuditEvent,
  auditGooglePhotoUploadFailure,
  uploadGooglePhoto
} from "../../../lib/server/google-workspace";
import { assertSameOrigin } from "../../../lib/server/security";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  try {
    const session = await requireActiveSession(request);
    const snapshot = await getAppSnapshot(session);
    if (dataMode() === "google") {
      await appendGoogleAuditEvent({
        session,
        action: "photo.list",
        resourceType: "photo",
        outcome: "success"
      });
    }
    return Response.json({ photos: snapshot.photos }, { headers: { "cache-control": "no-store, private" } });
  } catch (error) {
    return safeErrorResponse(error);
  }
}

export async function POST(request: Request): Promise<Response> {
  const requestId = requestIdFromRequest(request);
  let session: UserSession | undefined;
  try {
    assertSameOrigin(request);
    session = await requireActiveSession(request);
    if (dataMode() !== "google") {
      throw new HttpError(
        409,
        "Der Foto-Upload ist erst im freigegebenen Google-Modus verfügbar.",
        "google_mode_required"
      );
    }
    const form = await request.formData();
    const childId = String(form.get("childId") ?? "");
    const file = form.get("file");
    if (!childId || !(file instanceof File)) {
      throw new HttpError(
        400,
        "Kind und Bilddatei sind erforderlich.",
        "photo_input_required"
      );
    }
    if (!ALLOWED_PHOTO_TYPES.has(file.type)) {
      throw new HttpError(
        415,
        "Es sind nur JPG-, PNG- und WebP-Bilder erlaubt.",
        "photo_type_unsupported"
      );
    }
    if (file.size > MAX_PHOTO_BYTES) {
      throw new HttpError(
        413,
        "Das Bild überschreitet das Limit von 15 MB.",
        "photo_too_large"
      );
    }
    const snapshot = await uploadGooglePhoto(session, childId, file, requestId);
    return Response.json(snapshot, { headers: { "cache-control": "no-store, private" } });
  } catch (error) {
    if (session && dataMode() === "google") {
      await auditGooglePhotoUploadFailure(session, error, requestId).catch(() => undefined);
    }
    logSafeRouteError(error, requestId);
    return safeErrorResponse(error);
  }
}
