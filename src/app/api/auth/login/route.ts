import { LoginSchema } from "@/lib/contracts";
import { authenticateUser } from "@/lib/server/repository";
import { safeErrorResponse } from "@/lib/server/http";
import { sessionCookie } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request): Promise<Response> {
  try {
    const input = LoginSchema.parse(await request.json());
    const session = await authenticateUser(input.email, input.password);
    if (!session) return Response.json({ error: "E-Mail oder Passwort ist nicht korrekt." }, { status: 401 });
    return Response.json({ session }, {
      headers: {
        "set-cookie": sessionCookie(session),
        "cache-control": "no-store",
        "x-content-type-options": "nosniff"
      }
    });
  } catch (error) {
    return safeErrorResponse(error);
  }
}
