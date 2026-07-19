import { expiredSessionCookie } from "@/lib/session";

export const runtime = "nodejs";

export function POST(): Response {
  return Response.json({ ok: true }, {
    headers: { "set-cookie": expiredSessionCookie(), "cache-control": "no-store" }
  });
}
