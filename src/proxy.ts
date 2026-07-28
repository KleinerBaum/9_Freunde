import { NextResponse } from "next/server";

import { browserSecurityHeaders } from "./lib/server/security";

export function proxy() {
  const response = NextResponse.next();
  for (const [key, value] of Object.entries(browserSecurityHeaders)) {
    response.headers.set(key, value);
  }
  if (process.env.NODE_ENV === "production") {
    response.headers.set(
      "strict-transport-security",
      "max-age=63072000; includeSubDomains; preload"
    );
  }
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"]
};
