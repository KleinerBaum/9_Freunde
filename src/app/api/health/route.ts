import { dataMode } from "@/lib/server/repository";
import { googleConfigurationStatus } from "@/lib/server/google-workspace";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function GET(): Response {
  const mode = dataMode();
  return Response.json({
    ok: true,
    service: "9-freunde-portal",
    mode,
    integrations: mode === "google"
      ? googleConfigurationStatus()
      : { sheets: false, drive: false, calendar: false },
    mcp: "/mcp"
  }, {
    headers: { "cache-control": "no-store", "x-content-type-options": "nosniff" }
  });
}
