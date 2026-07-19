import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";

import { dataMode } from "../../lib/server/repository";
import { createNineFriendsMcpServer } from "../../mcp/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Authorization, Content-Type, MCP-Protocol-Version, MCP-Session-Id, Last-Event-ID",
  "Access-Control-Expose-Headers": "MCP-Protocol-Version, MCP-Session-Id",
  "Cache-Control": "no-store"
};

function authorized(request: Request) {
  if (dataMode() === "demo") return true;
  const expected = process.env.MCP_BEARER_TOKEN?.trim();
  return Boolean(expected && request.headers.get("authorization") === `Bearer ${expected}`);
}

async function handleMcp(request: Request): Promise<Response> {
  if (!authorized(request)) return Response.json({ error: "Unauthorized" }, { status: 401, headers: corsHeaders });
  const transport = new WebStandardStreamableHTTPServerTransport({ sessionIdGenerator: undefined });
  const server = createNineFriendsMcpServer();
  await server.connect(transport);
  const response = await transport.handleRequest(request);
  const headers = new Headers(response.headers);
  for (const [key, value] of Object.entries(corsHeaders)) headers.set(key, value);
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

export const GET = handleMcp;
export const POST = handleMcp;
export const DELETE = handleMcp;
export function OPTIONS(): Response { return new Response(null, { status: 204, headers: corsHeaders }); }
