import { AppActionSchema } from "@/lib/contracts";
import { HttpError, requireSession, safeErrorResponse, noStoreHeaders } from "@/lib/server/http";
import { performAppAction } from "@/lib/server/repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ADMIN_ONLY_ACTIONS = new Set([
  "create_child",
  "create_event",
  "update_event",
  "generate_document",
  "update_document_status"
]);

export async function POST(request: Request): Promise<Response> {
  try {
    const session = requireSession(request);
    const action = AppActionSchema.parse(await request.json());
    if (session.role === "parent" && ADMIN_ONLY_ACTIONS.has(action.type)) {
      throw new HttpError(403, "This action is available to staff only.");
    }
    if (session.role === "parent" && action.type === "update_child" && !session.childIds.includes(action.childId)) {
      throw new HttpError(403, "You do not have access to this child record.");
    }
    if (session.role === "parent" && action.type === "update_parent_profile" && session.parentId !== action.parentId) {
      throw new HttpError(403, "You can only update your own profile.");
    }
    const snapshot = await performAppAction(session, action);
    return Response.json(snapshot, { headers: noStoreHeaders });
  } catch (error) {
    return safeErrorResponse(error);
  }
}
