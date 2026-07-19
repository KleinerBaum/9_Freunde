import { describe, expect, it } from "vitest";

import { authenticateDemoUser, demoSession, getDemoSnapshot, resetDemoStateForTests } from "@/lib/demo-data";
import { buildOverview } from "@/mcp/server";

describe("MCP overview", () => {
  it("returns concise model-visible operational data", () => {
    resetDemoStateForTests();
    const session = demoSession(authenticateDemoUser("leitung@demo.9freunde.de", "willkommen")!);
    const overview = buildOverview(getDemoSnapshot(session));
    expect(overview.kind).toBe("overview");
    expect(overview.stats.activeChildren).toBe(3);
    expect(overview.stats.overdueInvoices).toBe(1);
    expect(overview.events.length).toBeLessThanOrEqual(5);
    expect(overview.tasks.some((task) => task.includes("Foto-Einwilligung"))).toBe(true);
  });
});
