import { MCP_ENDPOINT } from "../../../lib/contracts";
import {
  configuredDataMode,
  dataMode,
  productionBaseUrlConfigured,
  productionTechnicalGateReady,
  realDataApproved
} from "../../../lib/server/repository";
import {
  managedStaffDomain,
  parentAccessEnabled,
  productionAuthMode
} from "../../../lib/server/security";
import { privacyConfigurationReady } from "../../../lib/server/privacy-config";
import { googleConfigurationStatus } from "../../../lib/server/google-workspace";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function GET(): Response {
  const mode = dataMode();
  const configuredMode = configuredDataMode();
  const managedIdentity =
    productionAuthMode() === "sites" && Boolean(managedStaffDomain());
  const privacyNoticeConfigured = privacyConfigurationReady();
  const parentPilotDisabled = !parentAccessEnabled();
  const mcpPilotDisabled =
    process.env.MCP_ENABLED?.trim().toLowerCase() !== "true";
  const baseUrlConfigured = productionBaseUrlConfigured();
  return Response.json({
    ok: true,
    service: "9-freunde-portal",
    mode,
    releaseGate: {
      configuredMode,
      realDataApproved: realDataApproved(),
      managedIdentity,
      privacyNoticeConfigured,
      baseUrlConfigured,
      parentPilotDisabled,
      mcpPilotDisabled,
      readyForStaffPilot:
        configuredMode === "google" &&
        realDataApproved() &&
        productionTechnicalGateReady() &&
        parentPilotDisabled &&
        mcpPilotDisabled
    },
    integrations: mode === "google"
      ? googleConfigurationStatus()
      : { sheets: false, drive: false, calendar: false },
    mcp: MCP_ENDPOINT
  }, {
    headers: { "cache-control": "no-store", "x-content-type-options": "nosniff" }
  });
}
