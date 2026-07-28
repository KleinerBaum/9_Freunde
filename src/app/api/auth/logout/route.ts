import { expiredSessionCookie } from "../../../../lib/session";
import { assertSameOrigin } from "../../../../lib/server/security";

export const runtime = "nodejs";

export function POST(request: Request): Response {
  try {
    assertSameOrigin(request);
    return Response.json({ ok: true }, {
      headers: { "set-cookie": expiredSessionCookie(), "cache-control": "no-store" }
    });
  } catch {
    return Response.json(
      { error: "Request origin is not allowed." },
      { status: 403, headers: { "cache-control": "no-store" } }
    );
  }
}
