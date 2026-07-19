import {
  AppActionSchema,
  DashboardSnapshotSchema,
  LoginSchema,
  type AppAction,
  type DashboardSnapshot,
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
  getGoogleSnapshot,
  performGoogleAction
} from "./google-workspace";

export const dataMode = () => process.env.DATA_MODE === "google" ? "google" as const : "demo" as const;

export async function authenticateUser(email: string, password: string): Promise<UserSession | null> {
  const input = LoginSchema.parse({ email, password });
  if (dataMode() === "google") return authenticateGoogleUser(input.email, input.password);
  const user = authenticateDemoUser(input.email, input.password);
  return user ? demoSession(user) : null;
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
