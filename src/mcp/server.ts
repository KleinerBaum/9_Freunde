import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { RESOURCE_MIME_TYPE, registerAppResource, registerAppTool } from "@modelcontextprotocol/ext-apps/server";
import { z } from "zod";

import type { DashboardSnapshot, UserSession } from "@/lib/contracts";
import { getAppSnapshot, performAppAction } from "@/lib/server/repository";
import { dashboardWidgetHtml, WIDGET_URI } from "@/mcp/widget";

const overviewSchema = z.object({
  kind: z.literal("overview"),
  mode: z.enum(["demo", "google"]),
  stats: z.object({
    activeChildren: z.number().int().nonnegative(),
    openDocuments: z.number().int().nonnegative(),
    overdueInvoices: z.number().int().nonnegative(),
    upcomingEvents: z.number().int().nonnegative()
  }),
  events: z.array(z.object({ id: z.string(), title: z.string(), start: z.string(), location: z.string() })).max(5),
  tasks: z.array(z.string()).max(8),
  generatedAt: z.string()
});

type Overview = z.infer<typeof overviewSchema>;

const staffSession = (): UserSession => ({
  userId: "mcp-staff",
  email: (process.env.ADMIN_EMAILS?.split(",")[0] || "mcp-admin@demo.9freunde.de").trim(),
  name: "9 Freunde Leitung",
  role: "admin",
  childIds: [],
  expiresAt: Math.floor(Date.now() / 1000) + 3600
});

export function buildOverview(snapshot: DashboardSnapshot): Overview {
  const activeChildren = snapshot.children.filter((child) => child.status === "active").length;
  const openDocuments = snapshot.documents.filter((document) => ["draft", "sent", "overdue"].includes(document.status)).length;
  const overdueInvoices = snapshot.documents.filter((document) => document.type === "invoice" && document.status === "overdue").length;
  const now = Date.now();
  const events = snapshot.events
    .filter((event) => new Date(event.start).getTime() >= now)
    .sort((a, b) => a.start.localeCompare(b.start))
    .slice(0, 5)
    .map((event) => ({ id: event.id, title: event.title, start: event.start, location: event.location }));
  const missingConsents = snapshot.children.filter((child) => child.photoConsent === "missing").length;
  const onboarding = snapshot.children.filter((child) => child.status === "onboarding").length;
  const tasks = [
    ...(overdueInvoices ? [`${overdueInvoices} Rechnung(en) sind überfällig.`] : []),
    ...(missingConsents ? [`${missingConsents} Foto-Einwilligung(en) fehlen.`] : []),
    ...(onboarding ? [`${onboarding} Kind(er) befinden sich im Onboarding.`] : []),
    ...(openDocuments ? [`${openDocuments} Dokument(e) warten auf Bearbeitung.`] : [])
  ];
  return overviewSchema.parse({
    kind: "overview",
    mode: snapshot.integrations.mode,
    stats: { activeChildren, openDocuments, overdueInvoices, upcomingEvents: events.length },
    events,
    tasks,
    generatedAt: snapshot.generatedAt
  });
}

const renderMeta = {
  ui: { resourceUri: WIDGET_URI, visibility: ["model", "app"] as const },
  "openai/outputTemplate": WIDGET_URI,
  "openai/toolInvocation/invoking": "Dashboard wird vorbereitet…",
  "openai/toolInvocation/invoked": "Dashboard ist bereit"
};

const modelOnlyMeta = {
  ui: { visibility: ["model"] as const }
};

const calendarToolInput = {
  title: z.string().min(1).max(240),
  description: z.string().max(4000).default(""),
  start: z.string().datetime(),
  end: z.string().datetime(),
  location: z.string().max(500).default(""),
  audience: z.enum(["all", "child"]),
  childId: z.string().optional(),
  attendeeEmails: z.array(z.string().email()).max(100).default([]),
  remindersMinutes: z.array(z.number().int().min(5).max(40_320)).max(5).default([1440]),
  confirmed: z.boolean().describe("Must be true only after the user confirms the exact event details")
};

const canonicalUrl = (id: string) => {
  const base = (process.env.APP_BASE_URL || "https://9-freunde.local").replace(/\/$/u, "");
  return `${base}/?focus=${encodeURIComponent(id)}`;
};

async function snapshot() {
  return getAppSnapshot(staffSession());
}

export function createNineFriendsMcpServer(): McpServer {
  const server = new McpServer({ name: "nine-friends-management", version: "0.1.0" });

  registerAppResource(
    server,
    "9 Freunde management dashboard",
    WIDGET_URI,
    {
      description: "Compact staff overview for children, documents, and appointments.",
      _meta: {
        ui: { prefersBorder: true, csp: { connectDomains: [], resourceDomains: [] } },
        "openai/widgetDescription": "Shows the current 9 Freunde staff KPIs, upcoming appointments, and operational tasks."
      }
    },
    async () => ({
      contents: [{
        uri: WIDGET_URI,
        mimeType: RESOURCE_MIME_TYPE,
        text: dashboardWidgetHtml(),
        _meta: {
          ui: { prefersBorder: true, csp: { connectDomains: [], resourceDomains: [] } },
          "openai/widgetDescription": "Shows the current 9 Freunde staff KPIs, upcoming appointments, and operational tasks."
        }
      }]
    })
  );

  registerAppTool(
    server,
    "search",
    {
      title: "Search 9 Freunde records",
      description: "Use this when staff need to find a child, parent, document, or calendar event by a short query.",
      inputSchema: { query: z.string().min(1).max(200) },
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      _meta: modelOnlyMeta
    },
    async ({ query }) => {
      const data = await snapshot();
      const needle = query.trim().toLocaleLowerCase("de");
      const results = [
        ...data.children.map((child) => ({ id: `child:${child.id}`, title: child.name, haystack: `${child.name} ${child.group} ${child.status}` })),
        ...data.parents.map((parent) => ({ id: `parent:${parent.id}`, title: parent.name, haystack: `${parent.name} ${parent.email}` })),
        ...data.documents.map((document) => ({ id: `document:${document.id}`, title: document.title, haystack: `${document.title} ${document.number} ${document.status}` })),
        ...data.events.map((event) => ({ id: `event:${event.id}`, title: event.title, haystack: `${event.title} ${event.description} ${event.location}` }))
      ]
        .filter((item) => item.haystack.toLocaleLowerCase("de").includes(needle))
        .slice(0, 20)
        .map(({ id, title }) => ({ id, title, url: canonicalUrl(id) }));
      return { content: [{ type: "text" as const, text: JSON.stringify({ results }) }] };
    }
  );

  registerAppTool(
    server,
    "fetch",
    {
      title: "Fetch a 9 Freunde record",
      description: "Use this when a prior search returned a record ID and staff need its complete, authorized details.",
      inputSchema: { id: z.string().min(1).max(240) },
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      _meta: modelOnlyMeta
    },
    async ({ id }) => {
      const data = await snapshot();
      const [kind, value] = id.split(":", 2);
      const record = kind === "child" ? data.children.find((item) => item.id === value)
        : kind === "parent" ? data.parents.find((item) => item.id === value)
          : kind === "document" ? data.documents.find((item) => item.id === value)
            : kind === "event" ? data.events.find((item) => item.id === value)
              : undefined;
      if (!record) return { isError: true as const, content: [{ type: "text" as const, text: "Record not found." }] };
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({ id, title: "name" in record ? record.name : record.title, text: JSON.stringify(record), url: canonicalUrl(id), metadata: { kind } })
        }]
      };
    }
  );

  registerAppTool(
    server,
    "get_overview",
    {
      title: "Get the staff overview",
      description: "Use this when staff ask what needs attention today or request current management KPIs. Call this before render_overview.",
      inputSchema: {},
      outputSchema: overviewSchema,
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      _meta: {
        ui: { visibility: ["model", "app"] },
        "openai/toolInvocation/invoking": "Aktuelle Daten werden geladen…",
        "openai/toolInvocation/invoked": "Aktuelle Daten sind bereit"
      }
    },
    async () => {
      const result = buildOverview(await snapshot());
      return {
        content: [{ type: "text" as const, text: `There are ${result.stats.activeChildren} active children and ${result.tasks.length} operational task(s).` }],
        structuredContent: result
      };
    }
  );

  registerAppTool(
    server,
    "render_overview",
    {
      title: "Render the staff dashboard",
      description: "Use this when get_overview has returned current KPIs and the user wants the interactive dashboard.",
      inputSchema: overviewSchema,
      outputSchema: overviewSchema,
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      _meta: renderMeta
    },
    async (input) => ({
      content: [{ type: "text" as const, text: "Showing the current 9 Freunde management overview." }],
      structuredContent: overviewSchema.parse(input)
    })
  );

  registerAppTool(
    server,
    "draft_document",
    {
      title: "Draft an invoice or contract",
      description: "Use this when staff want a deterministic, reviewable invoice or contract draft for one child without saving it yet.",
      inputSchema: {
        childId: z.string().min(1),
        documentType: z.enum(["invoice", "contract"]),
        period: z.string().min(1).max(40)
      },
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      _meta: modelOnlyMeta
    },
    async ({ childId, documentType, period }) => {
      const data = await snapshot();
      const child = data.children.find((item) => item.id === childId);
      if (!child) return { isError: true as const, content: [{ type: "text" as const, text: "Child record not found." }] };
      const draft = {
        documentType,
        childId,
        childName: child.name,
        period,
        careFeeCents: child.careFeeCents,
        mealFeeCents: child.mealFeeCents,
        totalCents: child.careFeeCents + child.mealFeeCents,
        status: "draft",
        reviewRequired: true
      };
      return { content: [{ type: "text" as const, text: `Drafted a ${documentType} for ${child.name}. Legal and factual review is required before sending.` }], structuredContent: draft };
    }
  );

  registerAppTool(
    server,
    "create_calendar_event",
    {
      title: "Create a Google Calendar event",
      description: "Use this when staff have confirmed the exact title, time, audience, attendees, and reminders for an event. This sends Google Calendar invitations.",
      inputSchema: calendarToolInput,
      annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: true },
      _meta: modelOnlyMeta
    },
    async ({ confirmed, ...payload }) => {
      if (!confirmed) return { isError: true as const, content: [{ type: "text" as const, text: "Please confirm the exact event details before creating invitations." }] };
      await performAppAction(staffSession(), { type: "create_event", payload });
      return { content: [{ type: "text" as const, text: `Created “${payload.title}” and sent updates to ${payload.attendeeEmails.length} attendee(s).` }], structuredContent: { created: true, title: payload.title, start: payload.start } };
    }
  );

  registerAppTool(
    server,
    "update_calendar_event",
    {
      title: "Update a Google Calendar event",
      description: "Use this after staff confirm the exact replacement details for an existing event. Google Calendar sends the update to attendees.",
      inputSchema: {
        eventId: z.string().min(1),
        ...calendarToolInput
      },
      annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true },
      _meta: modelOnlyMeta
    },
    async ({ eventId, confirmed, ...payload }) => {
      if (!confirmed) return { isError: true as const, content: [{ type: "text" as const, text: "Please confirm the exact event details before sending updates." }] };
      await performAppAction(staffSession(), { type: "update_event", eventId, payload });
      return { content: [{ type: "text" as const, text: `Updated “${payload.title}” and sent changes to ${payload.attendeeEmails.length} attendee(s).` }], structuredContent: { updated: true, eventId, title: payload.title, start: payload.start } };
    }
  );

  return server;
}
