import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { GET as health } from "@/app/api/health/route";
import {
  configuredDataMode,
  dataMode,
  runtimeConfigurationStatus
} from "@/lib/server/repository";
import {
  parentAccessEnabled,
  productionAuthMode
} from "@/lib/server/security";

const originalEnvironment = { ...process.env };

describe("runtime configuration contract", () => {
  beforeEach(() => {
    for (const key of [
      "DATA_MODE",
      "REAL_DATA_APPROVED",
      "AUTH_MODE",
      "PARENT_ACCESS_ENABLED",
      "MCP_ENABLED",
      "GMAIL_ENABLED"
    ]) delete process.env[key];
  });

  const configureCompleteGoogleRuntime = () => {
    process.env.DATA_MODE = "google";
    process.env.REAL_DATA_APPROVED = "true";
    process.env.AUTH_MODE = "sites";
    process.env.APP_BASE_URL = "https://portal.example";
    process.env.MANAGED_STAFF_EMAIL_DOMAIN = "kita.example";
    process.env.GOOGLE_WORKSPACE_DOMAIN = "kita.example";
    process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL =
      "portal@example-project.iam.gserviceaccount.com";
    process.env.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY = "synthetic-private-key";
    process.env.GOOGLE_SHEET_ID = "synthetic-sheet-id";
    process.env.GOOGLE_DRIVE_SHARED_DRIVE_ID = "synthetic-shared-drive-id";
    process.env.GOOGLE_DRIVE_PHOTOS_FOLDER_ID = "synthetic-photo-folder-id";
    process.env.GOOGLE_CALENDAR_ID = "calendar@kita.example";
    process.env.GOOGLE_CALENDAR_IMPERSONATED_USER_EMAIL =
      "calendar@kita.example";
    process.env.GMAIL_ENABLED = "true";
    process.env.GOOGLE_GMAIL_IMPERSONATED_USER_EMAIL = "mail@kita.example";
    process.env.PRIVACY_CONTROLLER_NAME = "Fictional Provider";
    process.env.PRIVACY_CONTROLLER_ADDRESS = "Example address";
    process.env.PRIVACY_CONTACT_EMAIL = "privacy@kita.example";
    process.env.PRIVACY_DPO_EMAIL = "dpo@kita.example";
    process.env.LEGAL_REPRESENTATIVE = "Fictional Representative";
    process.env.LEGAL_REGISTER = "Fictional Register";
    process.env.LEGAL_SUPERVISORY_AUTHORITY = "Fictional Authority";
  };

  afterEach(() => {
    process.env = { ...originalEnvironment };
  });

  it("defaults to a synthetic staff-only runtime", async () => {
    process.env.PARENT_ACCESS_ENABLED = "true";
    process.env.MCP_ENABLED = "true";
    process.env.GMAIL_ENABLED = "true";

    expect(configuredDataMode()).toBe("demo");
    expect(dataMode()).toBe("demo");
    expect(productionAuthMode()).toBe("password");
    expect(parentAccessEnabled()).toBe(false);

    const response = health();
    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({
      ok: true,
      mode: "demo",
      runtime: { ready: true, failedGates: [] },
      releaseGate: {
        configuredMode: "demo",
        realDataApproved: false,
        parentPilotDisabled: true,
        mcpPilotDisabled: true
      },
      integrations: {
        sheets: false,
        drive: false,
        calendar: false,
        gmail: false
      }
    });
  });

  it("accepts the exact demo value", async () => {
    process.env.DATA_MODE = "demo";

    expect(configuredDataMode()).toBe("demo");
    expect(dataMode()).toBe("demo");
    const response = health();
    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({
      ok: true,
      mode: "demo",
      runtime: { ready: true }
    });
  });

  it.each(["googl", "production"])(
    "fails closed for invalid DATA_MODE=%s",
    async (configured) => {
      process.env.DATA_MODE = configured;

      expect(configuredDataMode()).toBe("invalid");
      expect(runtimeConfigurationStatus()).toEqual({
        configuredMode: "invalid",
        effectiveMode: null,
        ready: false,
        failedGates: ["dataMode"]
      });
      expect(() => dataMode()).toThrow(/invalid or incomplete/u);

      const response = health();
      expect(response.status).toBe(503);
      expect(await response.json()).toMatchObject({
        ok: false,
        mode: "unavailable",
        runtime: {
          ready: false,
          code: "runtime_not_ready",
          failedGates: ["dataMode"]
        },
        releaseGate: { configuredMode: "invalid" }
      });
    }
  );

  it("reports an explained 503 for incomplete explicit Google mode", async () => {
    process.env.DATA_MODE = "google";
    process.env.AUTH_MODE = "sites";
    process.env.REAL_DATA_APPROVED = "false";

    expect(runtimeConfigurationStatus()).toMatchObject({
      configuredMode: "google",
      effectiveMode: null,
      ready: false,
      failedGates: expect.arrayContaining(["realDataApproval"])
    });
    expect(() => dataMode()).toThrow(/invalid or incomplete/u);

    const response = health();
    expect(response.status).toBe(503);
    expect(await response.json()).toMatchObject({
      ok: false,
      mode: "unavailable",
      runtime: {
        ready: false,
        code: "runtime_not_ready",
        failedGates: expect.arrayContaining(["realDataApproval"])
      },
      integrations: {
        sheets: false,
        drive: false,
        calendar: false,
        gmail: false
      }
    });
  });

  it("keeps a complete canonical Google configuration in Google mode", async () => {
    configureCompleteGoogleRuntime();

    expect(configuredDataMode()).toBe("google");
    expect(runtimeConfigurationStatus()).toMatchObject({
      configuredMode: "google",
      effectiveMode: "google",
      ready: true,
      failedGates: []
    });
    expect(dataMode()).toBe("google");

    const response = health();
    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({
      ok: true,
      mode: "google",
      runtime: { ready: true, failedGates: [] },
      integrations: {
        sheets: true,
        drive: true,
        calendar: true,
        gmail: true
      }
    });
  });
});
