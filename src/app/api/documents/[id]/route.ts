import { buildManagedDocumentPdf } from "../../../../lib/pdf";
import { HttpError, requireActiveSession, safeErrorResponse } from "../../../../lib/server/http";
import { appendGoogleAuditEvent } from "../../../../lib/server/google-workspace";
import { dataMode } from "../../../../lib/server/repository";
import { getAppSnapshot } from "../../../../lib/server/repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ id: string }> }): Promise<Response> {
  try {
    const session = await requireActiveSession(request);
    const { id } = await context.params;
    const snapshot = await getAppSnapshot(session);
    const document = snapshot.documents.find((item) => item.id === id);
    if (!document) throw new HttpError(404, "Document not found or access denied.");
    const child = snapshot.children.find((item) => item.id === document.childId);
    if (!child) throw new HttpError(404, "Child record not found.");
    const parent = snapshot.parents.find((item) => item.id === child.primaryParentId);
    const pdf = await buildManagedDocumentPdf(document, child, parent);
    if (dataMode() === "google") {
      await appendGoogleAuditEvent({
        session,
        action: "document.export",
        resourceType: "document",
        resourceId: document.id,
        outcome: "success"
      });
    }
    return new Response(Buffer.from(pdf), {
      headers: {
        "content-type": "application/pdf",
        "content-disposition": `attachment; filename="${document.number.replace(/[^a-zA-Z0-9_-]/gu, "_")}.pdf"`,
        "cache-control": "no-store, private",
        "x-content-type-options": "nosniff"
      }
    });
  } catch (error) {
    return safeErrorResponse(error);
  }
}
