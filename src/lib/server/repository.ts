import {
  AppActionSchema,
  CommunicationSendSchema,
  CreatePrivacyRequestSchema,
  DashboardSnapshotSchema,
  LoginSchema,
  UpdateUserAccessSchema,
  type AppAction,
  type CommunicationSendResult,
  type DashboardSnapshot,
  type PrivacyRequest,
  type UserSession
} from "../contracts";
import {
  authenticateDemoUser,
  demoSession,
  getDemoSnapshot,
  performDemoAction
} from "../demo-data";
import {
  authenticateGoogleUser,
  authenticateGoogleSitesUser,
  createGooglePrivacyRequest,
  getGoogleSnapshot,
  gmailIntegrationEnabled,
  listGooglePrivacyRequests,
  sendGoogleCommunication,
  validateGoogleSession,
  performGoogleAction,
  googleConfigurationStatus,
  updateGoogleUserAccess
} from "./google-workspace";
import { privacyConfigurationReady } from "./privacy-config";
import {
  managedStaffDomain,
  parentAccessEnabled,
  productionAuthMode
} from "./security";

export const configuredDataMode = () => {
  const configured = process.env.DATA_MODE?.trim();
  if (!configured || configured === "demo") return "demo" as const;
  if (configured === "google") return "google" as const;
  return "invalid" as const;
};

export const realDataApproved = () =>
  process.env.REAL_DATA_APPROVED?.trim().toLowerCase() === "true";

export const productionBaseUrlConfigured = () => {
  try {
    return new URL(process.env.APP_BASE_URL?.trim() || "").protocol === "https:";
  } catch {
    return false;
  }
};

export const productionTechnicalGateStatus = () => {
  const google = googleConfigurationStatus();
  return {
    managedSitesIdentity: productionAuthMode() === "sites" &&
      Boolean(managedStaffDomain()),
    privacyConfiguration: privacyConfigurationReady(),
    httpsBaseUrl: productionBaseUrlConfigured(),
    googleSheets: google.sheets,
    googleDrive: google.drive,
    googleCalendar: google.calendar,
    googleGmail: gmailIntegrationEnabled() && google.gmail
  } as const;
};

export const productionTechnicalGateReady = () =>
  Object.values(productionTechnicalGateStatus()).every(Boolean);

export const runtimeConfigurationStatus = () => {
  const configuredMode = configuredDataMode();
  if (configuredMode === "demo") {
    return {
      configuredMode,
      effectiveMode: "demo" as const,
      ready: true,
      failedGates: [] as string[]
    };
  }
  if (configuredMode === "invalid") {
    return {
      configuredMode,
      effectiveMode: null,
      ready: false,
      failedGates: ["dataMode"]
    };
  }

  const gates = {
    realDataApproval: realDataApproved(),
    ...productionTechnicalGateStatus()
  };
  const failedGates = Object.entries(gates)
    .filter(([, ready]) => !ready)
    .map(([gate]) => gate);
  return {
    configuredMode,
    effectiveMode: failedGates.length === 0 ? "google" as const : null,
    ready: failedGates.length === 0,
    failedGates
  };
};

class RuntimeConfigurationError extends Error {
  readonly status = 503;
  readonly code = "runtime_not_ready";
}

export const dataMode = () => {
  const status = runtimeConfigurationStatus();
  if (!status.ready || !status.effectiveMode) {
    throw new RuntimeConfigurationError(
      "Runtime configuration is invalid or incomplete."
    );
  }
  return status.effectiveMode;
};

export async function authenticateUser(email: string, password: string): Promise<UserSession | null> {
  const input = LoginSchema.parse({ email, password });
  if (dataMode() === "google") return authenticateGoogleUser(input.email, input.password);
  const user = authenticateDemoUser(input.email, input.password);
  return user && (user.role !== "parent" || parentAccessEnabled())
    ? demoSession(user)
    : null;
}

export async function authenticateSitesUser(
  email: string,
  name?: string
): Promise<UserSession | null> {
  if (dataMode() !== "google") return null;
  return authenticateGoogleSitesUser(email, name);
}

export async function validateSession(session: UserSession): Promise<boolean> {
  if (session.role === "parent" && !parentAccessEnabled()) return false;
  if (dataMode() === "demo") return true;
  return validateGoogleSession(session);
}

export async function getAppSnapshot(session: UserSession): Promise<DashboardSnapshot> {
  const snapshot = dataMode() === "google"
    ? await getGoogleSnapshot(session)
    : getDemoSnapshot(session);
  return DashboardSnapshotSchema.parse(snapshot);
}

export async function performAppAction(session: UserSession, rawAction: unknown): Promise<DashboardSnapshot> {
  const action: AppAction = AppActionSchema.parse(rawAction);
  const snapshot = dataMode() === "google"
    ? await performGoogleAction(session, action)
    : performDemoAction(session, action);
  return DashboardSnapshotSchema.parse(snapshot);
}

export async function sendCommunication(
  session: UserSession,
  rawInput: unknown
): Promise<CommunicationSendResult> {
  if (dataMode() !== "google") {
    const error = new Error("Communications require Google production mode.");
    Object.assign(error, { status: 409 });
    throw error;
  }
  return sendGoogleCommunication(
    session,
    CommunicationSendSchema.parse(rawInput)
  );
}

export async function createPrivacyRequest(
  session: UserSession,
  rawInput: unknown
): Promise<PrivacyRequest> {
  if (dataMode() !== "google") throw new Error("Privacy requests require Google production mode.");
  const input = CreatePrivacyRequestSchema.parse(rawInput);
  return createGooglePrivacyRequest(session, input);
}

export async function listPrivacyRequests() {
  if (dataMode() !== "google") return [];
  return listGooglePrivacyRequests();
}

export async function updateUserAccess(
  session: UserSession,
  rawInput: unknown
) {
  if (dataMode() !== "google") {
    throw new Error("User access changes require Google production mode.");
  }
  return updateGoogleUserAccess(session, UpdateUserAccessSchema.parse(rawInput));
}
