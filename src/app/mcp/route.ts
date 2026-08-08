import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";

import { safeErrorResponse } from "../../lib/server/http";
import { configuredDataMode, dataMode } from "../../lib/server/repository";
import { createNineFriendsMcpServer } from "../../mcp/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Authorization, Content-Type, MCP-Protocol-Version, MCP-Session-Id, Last-Event-ID",
  "Access-Control-Expose-Headers": "MCP-Protocol-Version, MCP-Session-Id",
  "Cache-Control": "no-store"
};

function authorizationStatus(request: Request): "allowed" | "disabled" | "denied" {
  if (configuredDataMode() !== "google") return "disabled";
  if (dataMode() !== "google") return "disabled";
  if (process.env.MCP_ENABLED?.trim().toLowerCase() !== "true") return "disabled";
  const expected = process.env.MCP_BEARER_TOKEN?.trim();
  if (!expected) return "disabled";
  return request.headers.get("authorization") === `Bearer ${expected}`
    ? "allowed"
    : "denied";
}

function withCors(response: Response): Response {
  const headers = new Headers(response.headers);
  for (const [key, value] of Object.entries(corsHeaders)) headers.set(key, value);
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers
  });
}

async function handleMcp(request: Request): Promise<Response> {
  try {
    const authorization = authorizationStatus(request);
    if (authorization === "disabled") {
      return Response.json({ error: "Not found" }, { status: 404, headers: corsHeaders });
    }
    if (authorization === "denied") {
      return Response.json({ error: "Unauthorized" }, { status: 401, headers: corsHeaders });
    }
    const transport = new WebStandardStreamableHTTPServerTransport({ sessionIdGenerator: undefined });
    const server = createNineFriendsMcpServer();
    await server.connect(transport);
    return withCors(await transport.handleRequest(request));
  } catch (error) {
    return withCors(safeErrorResponse(error));
  }
}

export const POST = handleMcp;
export const DELETE = handleMcp;
export function OPTIONS(request: Request): Response {
  try {
    return authorizationStatus(request) === "disabled"
      ? Response.json({ error: "Not found" }, { status: 404, headers: corsHeaders })
      : new Response(null, { status: 204, headers: corsHeaders });
  } catch (error) {
    return withCors(safeErrorResponse(error));
  }
}
