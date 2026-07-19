import { z } from "zod";

export const RoleSchema = z.enum(["admin", "parent"]);
export type Role = z.infer<typeof RoleSchema>;

export const ChildStatusSchema = z.enum(["active", "onboarding", "paused", "archived"]);
export const ConsentSchema = z.enum(["granted", "restricted", "missing"]);
export const DocumentTypeSchema = z.enum(["invoice", "contract"]);
export const DocumentStatusSchema = z.enum([
  "draft",
  "sent",
  "signed",
  "paid",
  "overdue"
]);
export const EventAudienceSchema = z.enum(["all", "child"]);

export const UserSessionSchema = z.object({
  userId: z.string().min(1),
  email: z.string().email(),
  name: z.string().min(1),
  role: RoleSchema,
  parentId: z.string().optional(),
  childIds: z.array(z.string()).default([]),
  expiresAt: z.number().int().positive()
});
export type UserSession = z.infer<typeof UserSessionSchema>;

export const ParentSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  email: z.string().email(),
  phone: z.string().default(""),
  phoneSecondary: z.string().default(""),
  address: z.string().default(""),
  preferredLanguage: z.enum(["de", "en"]).default("de"),
  emergencyContactName: z.string().default(""),
  emergencyContactPhone: z.string().default(""),
  notificationsOptIn: z.boolean().default(true),
  childIds: z.array(z.string()).default([]),
  updatedAt: z.string()
});
export type Parent = z.infer<typeof ParentSchema>;

export const ChildSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  initials: z.string().min(1).max(4),
  birthDate: z.string(),
  careStart: z.string(),
  group: z.string(),
  status: ChildStatusSchema,
  primaryParentId: z.string(),
  primaryParentEmail: z.string().email(),
  allergies: z.string().default(""),
  dietary: z.string().default(""),
  languagesAtHome: z.string().default(""),
  careHoursPerWeek: z.number().nonnegative(),
  careFeeCents: z.number().int().nonnegative(),
  mealFeeCents: z.number().int().nonnegative(),
  photoFolderId: z.string().default(""),
  photoConsent: ConsentSchema,
  downloadConsent: ConsentSchema,
  notesParentVisible: z.string().default(""),
  notesInternal: z.string().default(""),
  updatedAt: z.string()
});
export type Child = z.infer<typeof ChildSchema>;

export const CalendarEventSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  description: z.string().default(""),
  start: z.string().datetime(),
  end: z.string().datetime(),
  location: z.string().default(""),
  audience: EventAudienceSchema,
  childId: z.string().optional(),
  attendeeEmails: z.array(z.string().email()).default([]),
  remindersMinutes: z.array(z.number().int().positive()).default([1440]),
  source: z.enum(["demo", "google"]).default("demo")
});
export type CalendarEvent = z.infer<typeof CalendarEventSchema>;

export const ManagedDocumentSchema = z.object({
  id: z.string().min(1),
  childId: z.string().min(1),
  type: DocumentTypeSchema,
  status: DocumentStatusSchema,
  title: z.string().min(1),
  number: z.string().min(1),
  period: z.string(),
  careFeeCents: z.number().int().nonnegative(),
  mealFeeCents: z.number().int().nonnegative(),
  totalCents: z.number().int().nonnegative(),
  dueDate: z.string(),
  createdAt: z.string(),
  driveFileId: z.string().optional()
});
export type ManagedDocument = z.infer<typeof ManagedDocumentSchema>;

export const PhotoSchema = z.object({
  id: z.string().min(1),
  childId: z.string().min(1),
  name: z.string().min(1),
  mimeType: z.string().min(1),
  createdAt: z.string(),
  previewUrl: z.string(),
  source: z.enum(["demo", "google"])
});
export type Photo = z.infer<typeof PhotoSchema>;

export const IntegrationStatusSchema = z.object({
  mode: z.enum(["demo", "google"]),
  sheets: z.boolean(),
  drive: z.boolean(),
  calendar: z.boolean(),
  mcp: z.boolean()
});

export const DashboardSnapshotSchema = z.object({
  session: UserSessionSchema,
  children: z.array(ChildSchema),
  parents: z.array(ParentSchema),
  events: z.array(CalendarEventSchema),
  documents: z.array(ManagedDocumentSchema),
  photos: z.array(PhotoSchema),
  integrations: IntegrationStatusSchema,
  generatedAt: z.string().datetime()
});
export type DashboardSnapshot = z.infer<typeof DashboardSnapshotSchema>;

const ParentEditableChildPatchSchema = z.object({
  allergies: z.string().max(1000).optional(),
  dietary: z.string().max(1000).optional(),
  languagesAtHome: z.string().max(500).optional(),
  notesParentVisible: z.string().max(2000).optional()
});

const AdminEditableChildPatchSchema = ParentEditableChildPatchSchema.extend({
  name: z.string().min(1).max(160).optional(),
  birthDate: z.string().optional(),
  careStart: z.string().optional(),
  group: z.string().max(100).optional(),
  status: ChildStatusSchema.optional(),
  careHoursPerWeek: z.number().min(0).max(80).optional(),
  careFeeCents: z.number().int().min(0).max(500_000).optional(),
  mealFeeCents: z.number().int().min(0).max(100_000).optional(),
  photoConsent: ConsentSchema.optional(),
  downloadConsent: ConsentSchema.optional(),
  notesInternal: z.string().max(4000).optional()
});

export const ParentProfilePatchSchema = z.object({
  phone: z.string().max(80).optional(),
  phoneSecondary: z.string().max(80).optional(),
  address: z.string().max(500).optional(),
  preferredLanguage: z.enum(["de", "en"]).optional(),
  emergencyContactName: z.string().max(160).optional(),
  emergencyContactPhone: z.string().max(80).optional(),
  notificationsOptIn: z.boolean().optional()
});

export const CreateChildSchema = z.object({
  name: z.string().min(1).max(160),
  birthDate: z.string(),
  careStart: z.string(),
  group: z.string().min(1).max(100),
  parentName: z.string().min(1).max(160),
  parentEmail: z.string().email(),
  parentPhone: z.string().max(80).default(""),
  careHoursPerWeek: z.number().min(0).max(80).default(35),
  careFeeCents: z.number().int().min(0).max(500_000).default(0),
  mealFeeCents: z.number().int().min(0).max(100_000).default(0)
});

export const CreateEventSchema = z.object({
  title: z.string().min(1).max(240),
  description: z.string().max(4000).default(""),
  start: z.string().datetime(),
  end: z.string().datetime(),
  location: z.string().max(500).default(""),
  audience: EventAudienceSchema,
  childId: z.string().optional(),
  attendeeEmails: z.array(z.string().email()).max(100).default([]),
  remindersMinutes: z.array(z.number().int().min(5).max(40_320)).max(5).default([1440])
});

export const AppActionSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("create_child"),
    payload: CreateChildSchema
  }),
  z.object({
    type: z.literal("update_child"),
    childId: z.string().min(1),
    payload: AdminEditableChildPatchSchema
  }),
  z.object({
    type: z.literal("update_parent_profile"),
    parentId: z.string().min(1),
    payload: ParentProfilePatchSchema
  }),
  z.object({
    type: z.literal("create_event"),
    payload: CreateEventSchema
  }),
  z.object({
    type: z.literal("update_event"),
    eventId: z.string().min(1),
    payload: CreateEventSchema
  }),
  z.object({
    type: z.literal("generate_document"),
    childId: z.string().min(1),
    documentType: DocumentTypeSchema,
    period: z.string().min(1).max(40)
  }),
  z.object({
    type: z.literal("update_document_status"),
    documentId: z.string().min(1),
    status: DocumentStatusSchema
  })
]);
export type AppAction = z.infer<typeof AppActionSchema>;

export const LoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6).max(200)
});

export const PARENT_CHILD_PATCH_FIELDS = new Set(
  Object.keys(ParentEditableChildPatchSchema.shape)
);

export const APP_NAME = "9 Freunde";
export const MCP_WIDGET_URI = "ui://9-freunde/dashboard-v1.html";
export const MAX_PHOTO_BYTES = 15 * 1024 * 1024;
export const ALLOWED_PHOTO_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
