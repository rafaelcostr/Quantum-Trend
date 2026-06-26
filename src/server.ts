import "./lib/error-capture";

import { consumeLastCapturedError } from "./lib/error-capture";
import { renderErrorPage } from "./lib/error-page";
import { buildResultsFromDisk, isResultsPath } from "./lib/atlas-disk-reports";

const ATLAS_API_ORIGIN = process.env.VITE_ATLAS_API_ORIGIN ?? "http://127.0.0.1:8000";

type ServerEntry = {
  fetch: (request: Request, env: unknown, ctx: unknown) => Promise<Response> | Response;
};

let serverEntryPromise: Promise<ServerEntry> | undefined;

async function getServerEntry(): Promise<ServerEntry> {
  if (!serverEntryPromise) {
    serverEntryPromise = import("@tanstack/react-start/server-entry").then(
      (m) => (m.default ?? m) as ServerEntry,
    );
  }
  return serverEntryPromise;
}

/** Repassa /atlas-api/* para FastAPI antes do handler SSR do TanStack Start. */
async function proxyAtlasApi(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const apiPath = url.pathname.replace(/^\/atlas-api/, "/api");
  const target = `${ATLAS_API_ORIGIN}${apiPath}${url.search}`;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("connection");

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual",
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    // Node fetch exige corpo materializado (stream exige duplex: "half")
    init.body = await request.arrayBuffer();
  }

  try {
    const upstream = await fetch(target, init);
    if (upstream.ok) {
      return upstream;
    }
    if (upstream.status === 404 && (request.method === "GET" || request.method === "HEAD")) {
      const resultsMatch = isResultsPath(apiPath);
      if (resultsMatch) {
        try {
          const payload = await buildResultsFromDisk(resultsMatch.strategy, resultsMatch.timeframe);
          return Response.json(payload);
        } catch {
          /* mantém 404 da API */
        }
      }
    }
    return upstream;
  } catch (error) {
    if (request.method === "GET" || request.method === "HEAD") {
      const resultsMatch = isResultsPath(apiPath);
      if (resultsMatch) {
        try {
          const payload = await buildResultsFromDisk(resultsMatch.strategy, resultsMatch.timeframe);
          return Response.json(payload);
        } catch {
          /* fall through */
        }
      }
    }
    const message = error instanceof Error ? error.message : "proxy failed";
    console.error("Atlas API proxy error:", error);
    return new Response(
      JSON.stringify({
        detail: `Não foi possível contactar a API Python (${message}). Execute: python -m atlas.cli api`,
      }),
      {
        status: 502,
        headers: { "content-type": "application/json; charset=utf-8" },
      },
    );
  }
}

// h3 swallows in-handler throws into a normal 500 Response with body
// {"unhandled":true,"message":"HTTPError"} — try/catch alone never fires for those.
async function normalizeCatastrophicSsrResponse(response: Response): Promise<Response> {
  if (response.status < 500) return response;
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return response;

  const body = await response.clone().text();
  if (!body.includes('"unhandled":true') || !body.includes('"message":"HTTPError"')) {
    return response;
  }

  console.error(consumeLastCapturedError() ?? new Error(`h3 swallowed SSR error: ${body}`));
  return new Response(renderErrorPage(), {
    status: 500,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

export default {
  async fetch(request: Request, env: unknown, ctx: unknown) {
    try {
      const url = new URL(request.url);
      if (url.pathname === "/atlas-api" || url.pathname.startsWith("/atlas-api/")) {
        return proxyAtlasApi(request);
      }

      const handler = await getServerEntry();
      const response = await handler.fetch(request, env, ctx);
      return await normalizeCatastrophicSsrResponse(response);
    } catch (error) {
      console.error(error);
      return new Response(renderErrorPage(), {
        status: 500,
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }
  },
};
