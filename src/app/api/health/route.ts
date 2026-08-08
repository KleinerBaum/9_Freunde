import { MCP_ENDPOINT } from "../../../lib/contracts";
import {
  configuredDataMode,
  productionBaseUrlConfigured,
  productionTechnicalGateReady,
  realDataApproved,
  runtimeConfigurationStatus
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
  const runtimeStatus = runtimeConfigurationStatus();
  const mode = runtimeStatus.effectiveMode ?? "unavailable";
  const configuredMode = configuredDataMode();
  const managedIdentity =
    productionAuthMode() === "sites" && Boolean(managedStaffDomain());
  const privacyNoticeConfigured = privacyConfigurationReady();
  const parentPilotDisabled = !parentAccessEnabled();
  const mcpPilotDisabled =
    configuredMode === "demo" ||
    process.env.MCP_ENABLED?.trim().toLowerCase() !== "true";
  const baseUrlConfigured = productionBaseUrlConfigured();
  return Response.json({
    ok: runtimeStatus.ready,
    service: "9-freunde-portal",
    mode,
    runtime: runtimeStatus.ready
      ? { ready: true, failedGates: [] }
      : {
          ready: false,
          code: "runtime_not_ready",
          message: "Runtime configuration is invalid or incomplete.",
          failedGates: runtimeStatus.failedGates
        },
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
      : { sheets: false, drive: false, calendar: false, gmail: false },
    mcp: MCP_ENDPOINT
  }, {
    status: runtimeStatus.ready ? 200 : 503,
    headers: { "cache-control": "no-store", "x-content-type-options": "nosniff" }
  });
}
