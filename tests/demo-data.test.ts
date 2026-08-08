import { beforeEach, describe, expect, it } from "vitest";

import {
  authenticateDemoUser,
  demoSession,
  getDemoSnapshot,
  performDemoAction,
  resetDemoStateForTests
} from "@/lib/demo-data";

describe("demo data access", () => {
  beforeEach(() => resetDemoStateForTests());

  it("keeps parent snapshots scoped to their own child", () => {
    const user = authenticateDemoUser("eltern@demo.9freunde.de", "familie");
    expect(user).not.toBeNull();
    const snapshot = getDemoSnapshot(demoSession(user!));
    expect(snapshot.session.role).toBe("parent");
    expect(snapshot.children.map((child) => child.id)).toEqual(["child-lina"]);
    expect(snapshot.parents.map((parent) => parent.id)).toEqual(["parent-sommer"]);
    expect(snapshot.documents.every((document) => document.childId === "child-lina")).toBe(true);
    expect(snapshot.photos.every((photo) => photo.childId === "child-lina")).toBe(true);
    expect(snapshot.integrations).toMatchObject({
      mode: "demo",
      sheets: false,
      drive: false,
      calendar: false,
      gmail: false,
      mcp: false
    });
  });

  it("rejects a parent update for another child", () => {
    const user = authenticateDemoUser("eltern@demo.9freunde.de", "familie")!;
    const session = demoSession(user);
    expect(() => performDemoAction(session, {
      type: "update_child",
      childId: "child-noah",
      payload: { allergies: "Test" }
    })).toThrow(/access/u);
  });

  it("strips admin-only fields from a parent child update", () => {
    const user = authenticateDemoUser("eltern@demo.9freunde.de", "familie")!;
    const session = demoSession(user);
    const snapshot = performDemoAction(session, {
      type: "update_child",
      childId: "child-lina",
      payload: { name: "Should not change", allergies: "Neue Angabe" }
    });
    expect(snapshot.children[0]?.name).toBe("Lina Sommer");
    expect(snapshot.children[0]?.allergies).toBe("Neue Angabe");
  });

  it("lets staff create a deterministic invoice draft", () => {
    const user = authenticateDemoUser("leitung@demo.9freunde.de", "willkommen")!;
    const session = demoSession(user);
    const before = getDemoSnapshot(session).documents.length;
    const snapshot = performDemoAction(session, {
      type: "generate_document",
      childId: "child-lina",
      documentType: "invoice",
      period: "2026-07"
    });
    expect(snapshot.documents).toHaveLength(before + 1);
    expect(snapshot.documents.at(-1)).toMatchObject({
      childId: "child-lina",
      type: "invoice",
      status: "draft",
      totalCents: 8500
    });
  });

  it("lets staff update an event while preserving its identity", () => {
    const user = authenticateDemoUser("leitung@demo.9freunde.de", "willkommen")!;
    const session = demoSession(user);
    const existing = getDemoSnapshot(session).events[0]!;
    const snapshot = performDemoAction(session, {
      type: "update_event",
      eventId: existing.id,
      payload: {
        title: "Aktualisierter Termin",
        description: "Neue Details",
        start: existing.start,
        end: existing.end,
        location: "Neuer Ort",
        audience: "all",
        attendeeEmails: [],
        remindersMinutes: [120]
      }
    });
    expect(snapshot.events.find((event) => event.id === existing.id)).toMatchObject({
      title: "Aktualisierter Termin",
      location: "Neuer Ort",
      remindersMinutes: [120]
    });
  });

  it("enforces read-only and write staff roles", () => {
    const admin = demoSession(
      authenticateDemoUser("leitung@demo.9freunde.de", "willkommen")!
    );
    const readSession = { ...admin, role: "staff_read" as const };
    const writeSession = { ...admin, role: "staff_write" as const };

    expect(() => performDemoAction(readSession, {
      type: "update_child",
      childId: "child-lina",
      payload: { allergies: "Darf nicht gespeichert werden" }
    })).toThrow(/write access/u);

    const snapshot = performDemoAction(writeSession, {
      type: "generate_document",
      childId: "child-lina",
      documentType: "invoice",
      period: "2026-08"
    });
    expect(snapshot.documents.at(-1)).toMatchObject({
      childId: "child-lina",
      type: "invoice"
    });
  });

  it("applies the latest consent record before exposing photos", () => {
    const session = demoSession(
      authenticateDemoUser("leitung@demo.9freunde.de", "willkommen")!
    );
    expect(getDemoSnapshot(session).photos.some((photo) =>
      photo.childId === "child-lina"
    )).toBe(true);

    const snapshot = performDemoAction(session, {
      type: "record_consent",
      payload: {
        childId: "child-lina",
        purpose: "photo_processing",
        status: "withdrawn",
        scope: "staff_only",
        documentVersion: "demo-2",
        source: "signed_form",
        evidenceRef: "fictional-withdrawal"
      }
    });

    expect(snapshot.photos.some((photo) => photo.childId === "child-lina")).toBe(false);
    expect(snapshot.children.find((child) => child.id === "child-lina")?.photoConsent)
      .toBe("withdrawn");
  });

  it("requires download consent before a parent can see a photo", () => {
    const parentSession = demoSession(
      authenticateDemoUser("eltern@demo.9freunde.de", "familie")!
    );
    const adminSession = demoSession(
      authenticateDemoUser("leitung@demo.9freunde.de", "willkommen")!
    );
    expect(getDemoSnapshot(parentSession).photos).toEqual([]);

    performDemoAction(adminSession, {
      type: "record_consent",
      payload: {
        childId: "child-lina",
        purpose: "photo_download",
        status: "granted",
        scope: "download",
        documentVersion: "demo-2",
        source: "signed_form",
        evidenceRef: "fictional-download-consent"
      }
    });

    expect(getDemoSnapshot(parentSession).photos.length).toBeGreaterThan(0);
    expect(getDemoSnapshot(parentSession).consents).toEqual([]);
  });
});
