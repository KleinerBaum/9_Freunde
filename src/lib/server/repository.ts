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
import { managedStaffDomain, productionAuthMode } from "./security";

export const configuredDataMode = () =>
  process.env.DATA_MODE === "google" ? "google" as const : "demo" as const;

export const realDataApproved = () =>
  process.env.REAL_DATA_APPROVED?.trim().toLowerCase() === "true";

export const productionBaseUrlConfigured = () => {
  try {
    return new URL(process.env.APP_BASE_URL?.trim() || "").protocol === "https:";
  } catch {
    return false;
  }
};

export const productionTechnicalGateReady = () => {
  const google = googleConfigurationStatus();
  return productionAuthMode() === "sites" &&
    Boolean(managedStaffDomain()) &&
    privacyConfigurationReady() &&
    productionBaseUrlConfigured() &&
    google.sheets &&
    google.drive &&
    google.calendar &&
    gmailIntegrationEnabled() &&
    google.gmail;
};

export const dataMode = () =>
  configuredDataMode() === "google" &&
    realDataApproved() &&
    productionTechnicalGateReady()
    ? "google" as const
    : "demo" as const;

export async function authenticateUser(email: string, password: string): Promise<UserSession | null> {
  const input = LoginSchema.parse({ email, password });
  if (dataMode() === "google") return authenticateGoogleUser(input.email, input.password);
  const user = authenticateDemoUser(input.email, input.password);
  return user ? demoSession(user) : null;
}

export async function authenticateSitesUser(
  email: string,
  name?: string
): Promise<UserSession | null> {
  if (dataMode() !== "google") return null;
  return authenticateGoogleSitesUser(email, name);
}

export async function validateSession(session: UserSession): Promise<boolean> {
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
