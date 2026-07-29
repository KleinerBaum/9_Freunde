import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AppActionSchema,
  CommunicationSendSchema,
  type Child,
  type Parent
} from "../src/lib/contracts";
import {
  buildGmailRawMessage,
  resolveAnnouncementRecipients,
  sendGmailBatch
} from "../src/lib/server/google-workspace";

const parent = (
  id: string,
  email: string,
  notificationsOptIn = true
): Parent => ({
  id,
  name: `Fiktiver Kontakt ${id}`,
  email,
  phone: "",
  phoneSecondary: "",
  address: "",
  preferredLanguage: "de",
  emergencyContactName: "",
  emergencyContactPhone: "",
  notificationsOptIn,
  childIds: [],
  updatedAt: "2026-01-01T00:00:00.000Z"
});

const child = (
  id: string,
  group: string,
  primaryParentId: string,
  primaryParentEmail: string
): Child => ({
  id,
  name: `Fiktives Kind ${id}`,
  initials: "FK",
  birthDate: "2020-01-01",
  careStart: "2026-01-01",
  group,
  status: "active",
  primaryParentId,
  primaryParentEmail,
  allergies: "",
  dietary: "",
  languagesAtHome: "",
  careHoursPerWeek: 30,
  careFeeCents: 0,
  mealFeeCents: 0,
  photoFolderId: "",
  photoConsent: "missing",
  downloadConsent: "missing",
  notesParentVisible: "",
  notesInternal: "",
  updatedAt: "2026-01-01T00:00:00.000Z"
});

describe("Gmail communications", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("builds UTF-8 base64url MIME with a PDF attachment", () => {
    const raw = buildGmailRawMessage({
      sender: "portal@example.org",
      recipient: "contact@example.net",
      subject: "Geprüfte Abrechnung",
      body: "Guten Tag – das PDF ist beigefügt.",
      attachment: {
        filename: "R-2026-001.pdf",
        mimeType: "application/pdf",
        bytes: Buffer.from("%PDF-fictional")
      }
    });
    const mime = Buffer.from(raw, "base64url").toString("utf8");

    expect(mime).toContain("From: portal@example.org");
    expect(mime).toContain("To: contact@example.net");
    expect(mime).toContain(
      `Subject: =?UTF-8?B?${Buffer.from("Geprüfte Abrechnung").toString("base64")}?=`
    );
    expect(mime).toContain("Content-Type: multipart/mixed");
    expect(mime).toContain('Content-Type: application/pdf; name="R-2026-001.pdf"');
    expect(mime).toContain(Buffer.from("%PDF-fictional").toString("base64"));
    expect(mime).toContain(
      Buffer.from("Guten Tag – das PDF ist beigefügt.").toString("base64")
    );
  });

  it("rejects MIME header injection", () => {
    expect(() => buildGmailRawMessage({
      sender: "portal@example.org",
      recipient: "contact@example.net",
      subject: "Hinweis\r\nBcc: hidden@example.net",
      body: "Fiktiver Text"
    })).toThrow(/line breaks/u);
  });

  it("resolves, deduplicates, and opt-in filters recipients server-side", () => {
    const parents = [
      parent("parent-1", "one@example.net"),
      parent("parent-2", "ONE@example.net"),
      parent("parent-3", "opted-out@example.net", false)
    ];
    const children = [
      child("child-1", "Sonne", "parent-1", "one@example.net"),
      child("child-2", "Sonne", "parent-2", "ONE@example.net"),
      child("child-3", "Mond", "parent-3", "opted-out@example.net")
    ];

    expect(resolveAnnouncementRecipients({
      kind: "announcement",
      audience: "group",
      group: "sonne",
      subject: "Fiktiver Hinweis",
      body: "Fiktiver Inhalt",
      confirmed: true
    }, parents, children)).toEqual(["one@example.net"]);

    expect(resolveAnnouncementRecipients({
      kind: "announcement",
      audience: "single_child",
      childId: "child-3",
      subject: "Fiktiver Hinweis",
      body: "Fiktiver Inhalt",
      confirmed: true
    }, parents, children)).toEqual([]);
  });

  it("reports partial provider failures without exposing provider details", async () => {
    const send = vi.fn(async (recipient: string) => {
      if (recipient.startsWith("fail")) {
        throw new Error("provider response contained private details");
      }
    });

    const result = await sendGmailBatch([
      "success@example.net",
      "FAIL@example.net",
      "success@example.net"
    ], send);

    expect(result).toEqual({ successCount: 1, failureCount: 1 });
    expect(send).toHaveBeenCalledTimes(2);
    expect(result).not.toHaveProperty("error");
  });

  it("enforces the 100-recipient limit before sending", async () => {
    const recipients = Array.from(
      { length: 101 },
      (_, index) => `fictional-${index}@example.net`
    );
    await expect(sendGmailBatch(recipients, vi.fn()))
      .rejects.toThrow(/limit of 100/u);
  });

  it("requires explicit send and document-review confirmations", () => {
    expect(CommunicationSendSchema.safeParse({
      kind: "announcement",
      audience: "all_parents",
      subject: "Fiktiver Hinweis",
      body: "Fiktiver Inhalt",
      confirmed: false
    }).success).toBe(false);
    expect(CommunicationSendSchema.safeParse({
      kind: "document",
      documentId: "doc-1",
      body: "Fiktiver Begleittext",
      reviewConfirmed: false,
      confirmed: true
    }).success).toBe(false);
    expect(CommunicationSendSchema.safeParse({
      kind: "announcement",
      audience: "all_parents",
      subject: "Fiktiver Hinweis",
      body: "Fiktiver Inhalt",
      recipient: "browser-supplied@example.net",
      confirmed: true
    }).success).toBe(false);
  });

  it("reserves the sent document status for the Gmail delivery path", () => {
    expect(AppActionSchema.safeParse({
      type: "update_document_status",
      documentId: "doc-1",
      status: "sent"
    }).success).toBe(false);
  });
});
