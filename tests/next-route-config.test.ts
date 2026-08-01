import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

import { describe, expect, it } from "vitest";

const appRoot = join(process.cwd(), "src", "app");
const routeConfigNames = [
  "dynamic",
  "runtime",
  "revalidate",
  "preferredRegion",
  "maxDuration",
  "fetchCache"
];

function routeFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return routeFiles(path);
    return entry.name === "route.ts" ? [path] : [];
  });
}

describe("Next route segment configuration", () => {
  it("declares route configuration locally instead of re-exporting it", () => {
    const configAlternation = routeConfigNames.join("|");
    const reexportedConfig = new RegExp(
      `export\\s*\\{[^}]*\\b(?:${configAlternation})\\b[^}]*\\}\\s*from`,
      "m"
    );
    const offenders = routeFiles(appRoot)
      .filter((path) => reexportedConfig.test(readFileSync(path, "utf8")))
      .map((path) => relative(process.cwd(), path));

    expect(offenders).toEqual([]);
  });

  it("keeps the compatibility MCP route explicitly dynamic on Node.js", () => {
    const source = readFileSync(join(appRoot, "api", "mcp", "route.ts"), "utf8");

    expect(source).toContain('export const runtime = "nodejs";');
    expect(source).toContain('export const dynamic = "force-dynamic";');
  });
});
