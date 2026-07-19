import { describe, expect, it } from "vitest";

import { authenticateDemoUser, demoSession, getDemoSnapshot, resetDemoStateForTests } from "@/lib/demo-data";
import { buildManagedDocumentPdf } from "@/lib/pdf";

describe("document PDF", () => {
  it("generates a readable PDF envelope for an authorized document", async () => {
    resetDemoStateForTests();
    const user = authenticateDemoUser("leitung@demo.9freunde.de", "willkommen")!;
    const snapshot = getDemoSnapshot(demoSession(user));
    const document = snapshot.documents[0]!;
    const child = snapshot.children.find((item) => item.id === document.childId)!;
    const parent = snapshot.parents.find((item) => item.id === child.primaryParentId);
    const bytes = await buildManagedDocumentPdf(document, child, parent);
    expect(Buffer.from(bytes).subarray(0, 4).toString()).toBe("%PDF");
    expect(bytes.byteLength).toBeGreaterThan(1_000);
  });
});
